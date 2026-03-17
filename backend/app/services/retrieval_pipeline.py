from __future__ import annotations

from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait
from dataclasses import dataclass, field

from ..domain import (
    ConflictCheckResult,
    HardFilterCompiled,
    HardFilterInput,
    InputGuardrailResult,
    KeywordHit,
    QueryBuilderOutput,
    RetrievalPipelineOutput,
    SearchQueryInput,
    StageCaps,
    VectorHit,
)
from .conflict_checker import ConflictCheckerService
from .cross_encoder import CrossEncoderService
from .fusion import FusionService
from .hard_filter_compiler import HardFilterCompilerService
from .input_guardrail import InputGuardrailService
from .keyword_search import KeywordSearchService
from .query_builder import QueryBuilderService
from .query_normalizer import QueryNormalizerService
from .query_understanding import QueryUnderstandingService
from .rerank import RerankService
from .response_builder import ResponseBuilderService
from .vector_search import VectorSearchService


@dataclass(slots=True)
class RetrievalPipelineService:
    input_guardrail: InputGuardrailService
    query_understanding: QueryUnderstandingService
    query_normalizer: QueryNormalizerService
    conflict_checker: ConflictCheckerService
    hard_filter_compiler: HardFilterCompilerService
    query_builder: QueryBuilderService
    vector_search: VectorSearchService
    keyword_search: KeywordSearchService
    fusion: FusionService
    cross_encoder: CrossEncoderService
    rerank: RerankService
    response_builder: ResponseBuilderService
    stage_caps: StageCaps = field(default_factory=StageCaps)

    def run(self, search_input: SearchQueryInput, result_limit: int | None = None) -> RetrievalPipelineOutput:
        pre_guardrail = self.input_guardrail.evaluate(search_input, understood=None)
        if pre_guardrail.retry_required:
            return self.response_builder.build(_to_conflict(pre_guardrail), [])

        understood = self.query_understanding.extract(search_input)
        post_guardrail = self.input_guardrail.evaluate(search_input, understood=understood)
        if post_guardrail.retry_required:
            return self.response_builder.build(_to_conflict(post_guardrail), [])

        conflict = self.conflict_checker.check(search_input, understood)
        if conflict.retry_required:
            return self.response_builder.build(conflict, [])

        normalization_input = _compose_normalization_input(search_input, understood)
        normalized = self.query_normalizer.normalize(normalization_input)
        hard_filter_input = HardFilterInput(
            skill_esco_ids_high=[item.esco_id for item in normalized.skill_candidates if item.band == "high"],
            occupation_esco_ids_high=[
                item.esco_id for item in normalized.occupation_candidates if item.band == "high"
            ],
            industry_esco_ids_high=[item.esco_id for item in normalized.industry_candidates if item.band == "high"],
            experience=_prefer_requested_experience(search_input, understood),
            education=_prefer_requested_education(search_input, understood),
            locations=list(search_input.requested_locations),
        )
        compiled_filter = self.hard_filter_compiler.compile(hard_filter_input)

        query_bundle = self.query_builder.build(search_input, normalization_input, normalized)
        vector_hits, keyword_hits = _run_parallel_retrieval(
            vector_search=self.vector_search,
            keyword_search=self.keyword_search,
            query_bundle=query_bundle,
            compiled_filter=compiled_filter,
            stage_caps=self.stage_caps,
        )
        fusion_hits = self.fusion.fuse(
            vector_hits=vector_hits,
            keyword_hits=keyword_hits,
            top_k=self.stage_caps.fusion_top_k,
        )
        cross_result = self.cross_encoder.rerank(
            query_text=search_input.query_text,
            fusion_hits=fusion_hits,
            top_k=self.stage_caps.cross_encoder_top_k,
        )
        reranked = self.rerank.rerank(
            fusion_hits=fusion_hits,
            cross_result=cross_result,
            vector_hits=vector_hits,
            keyword_hits=keyword_hits,
            normalized=normalized,
            top_k=_resolve_result_limit(self.stage_caps, result_limit),
        )
        return self.response_builder.build(conflict, reranked)


def _compose_normalization_input(search_input: SearchQueryInput, understood):
    return type(understood)(
        original_query=understood.original_query,
        skill_terms=_prefer_requested_terms(search_input.requested_skill_terms, understood.skill_terms),
        occupation_terms=_prefer_requested_terms(
            search_input.requested_occupation_terms,
            understood.occupation_terms,
        ),
        industry_terms=_prefer_requested_terms(search_input.requested_industry_terms, understood.industry_terms),
        experience=understood.experience,
        education=understood.education,
    )


def _to_conflict(result: InputGuardrailResult) -> ConflictCheckResult:
    return ConflictCheckResult(
        retry_required=bool(result.retry_required),
        conflict_fields=list(result.conflict_fields),
        conflict_reason=result.conflict_reason,
    )


def _prefer_requested_terms(requested: list[str], extracted: list[str]) -> list[str]:
    if not requested:
        return _dedupe_terms(extracted)
    requested_norm = {item.strip().lower() for item in requested if item.strip()}
    merged = [item.strip() for item in requested if item.strip()]
    merged.extend(
        item.strip() for item in extracted if item.strip() and item.strip().lower() not in requested_norm
    )
    return _dedupe_terms(merged)


def _dedupe_terms(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(value.strip())
    return out


def _prefer_requested_experience(search_input: SearchQueryInput, understood):
    req = search_input.requested_experience
    if req.min_months is not None or req.max_months is not None:
        return req
    return understood.experience


def _prefer_requested_education(search_input: SearchQueryInput, understood):
    req = search_input.requested_education
    if req.min_rank is not None or req.max_rank is not None:
        return req
    return understood.education


def _resolve_result_limit(stage_caps: StageCaps, result_limit: int | None) -> int:
    max_allowed = min(stage_caps.fusion_top_k, stage_caps.cross_encoder_top_k, 50)
    if result_limit is None:
        return min(stage_caps.rerank_top_k, max_allowed)
    return max(1, min(int(result_limit), max_allowed))


def _run_parallel_retrieval(
    *,
    vector_search: VectorSearchService,
    keyword_search: KeywordSearchService,
    query_bundle: QueryBuilderOutput,
    compiled_filter: HardFilterCompiled,
    stage_caps: StageCaps,
) -> tuple[list[VectorHit], list[KeywordHit]]:
    with ThreadPoolExecutor(max_workers=2) as executor:
        vector_future = executor.submit(
            vector_search.search,
            query_bundle,
            compiled_filter,
            stage_caps.vector_top_k,
        )
        keyword_future = executor.submit(
            keyword_search.search,
            query_bundle.keyword_query,
            compiled_filter,
            stage_caps.keyword_top_k,
        )

        done, _ = wait({vector_future, keyword_future}, return_when=FIRST_EXCEPTION)
        for future in done:
            if future.exception() is None:
                continue
            vector_future.cancel()
            keyword_future.cancel()
            # Re-raise with original traceback.
            future.result()

        return vector_future.result(), keyword_future.result()
