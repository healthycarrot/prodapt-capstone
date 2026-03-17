from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

from ..domain import CrossEncoderResult, FusionHit, KeywordHit, NormalizedEscoOutput, RerankHit, VectorHit


class CandidateEscoRepo(Protocol):
    def fetch_candidate_esco_ids(self, candidate_ids: Sequence[str]) -> Mapping[str, Sequence[str]]:
        ...


@dataclass(slots=True)
class RerankService:
    candidate_esco_repo: CandidateEscoRepo | None = None
    default_top_k: int = 20
    cross_weight: float = 0.6
    fusion_weight: float = 0.3
    medium_weight: float = 0.1
    fallback_fusion_weight: float = 0.9
    fallback_medium_weight: float = 0.1

    def rerank(
        self,
        *,
        fusion_hits: Sequence[FusionHit],
        cross_result: CrossEncoderResult,
        vector_hits: Sequence[VectorHit],
        keyword_hits: Sequence[KeywordHit],
        normalized: NormalizedEscoOutput,
        top_k: int | None = None,
    ) -> list[RerankHit]:
        limit = top_k or self.default_top_k

        fusion_by_id = {hit.candidate_id: hit for hit in fusion_hits}
        vector_by_id = {hit.candidate_id: hit for hit in vector_hits}
        keyword_by_id = {hit.candidate_id: hit for hit in keyword_hits}
        cross_by_id = {hit.candidate_id: hit for hit in cross_result.hits}
        candidate_ids = list(dict.fromkeys([hit.candidate_id for hit in cross_result.hits]))
        if not candidate_ids:
            candidate_ids = list(dict.fromkeys([hit.candidate_id for hit in fusion_hits]))

        medium_ids = _medium_esco_ids(normalized)
        medium_scores = self._compute_medium_scores(candidate_ids, medium_ids)

        ranked: list[RerankHit] = []
        for candidate_id in candidate_ids:
            fusion_score = fusion_by_id.get(candidate_id).fusion_score if candidate_id in fusion_by_id else 0.0
            vector_score = vector_by_id.get(candidate_id).vector_score if candidate_id in vector_by_id else 0.0
            keyword_score = keyword_by_id.get(candidate_id).keyword_score if candidate_id in keyword_by_id else 0.0
            cross_score = cross_by_id.get(candidate_id).cross_encoder_score if candidate_id in cross_by_id else 0.0
            medium_score = medium_scores.get(candidate_id, 0.0)

            if cross_result.cross_encoder_applied:
                final_score = (
                    self.cross_weight * cross_score
                    + self.fusion_weight * fusion_score
                    + self.medium_weight * medium_score
                )
            else:
                final_score = (self.fallback_fusion_weight * fusion_score) + (
                    self.fallback_medium_weight * medium_score
                )

            ranked.append(
                RerankHit(
                    candidate_id=candidate_id,
                    keyword_score=keyword_score,
                    vector_score=vector_score,
                    fusion_score=fusion_score,
                    cross_encoder_score=cross_score,
                    medium_esco_match_score=medium_score,
                    final_score=final_score,
                )
            )

        ranked.sort(
            key=lambda hit: (
                -hit.final_score,
                -hit.cross_encoder_score,
                -hit.fusion_score,
                -hit.vector_score,
                -hit.keyword_score,
                hit.candidate_id,
            )
        )
        return ranked[:limit]

    def _compute_medium_scores(
        self,
        candidate_ids: list[str],
        medium_ids: set[str],
    ) -> dict[str, float]:
        if not candidate_ids or not medium_ids or self.candidate_esco_repo is None:
            return {}
        metadata = self.candidate_esco_repo.fetch_candidate_esco_ids(candidate_ids)
        denominator = float(len(medium_ids))
        scores: dict[str, float] = {}
        for candidate_id in candidate_ids:
            candidate_esco_ids = set(metadata.get(candidate_id, []))
            overlap = len(candidate_esco_ids & medium_ids)
            scores[candidate_id] = overlap / denominator
        return scores


def _medium_esco_ids(normalized: NormalizedEscoOutput) -> set[str]:
    candidates = (
        normalized.skill_candidates + normalized.occupation_candidates + normalized.industry_candidates
    )
    return {candidate.esco_id for candidate in candidates if candidate.band == "medium"}
