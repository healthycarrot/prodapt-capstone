from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from ..domain import HardFilterCompiled, QueryBuilderOutput, VectorHit


@dataclass(slots=True)
class VectorRepoHit:
    candidate_id: str
    score: float


class CandidateVectorRepo(Protocol):
    def search_skill(self, query: str, *, top_k: int, filter_expr: str) -> Sequence[VectorRepoHit]:
        ...

    def search_occupation(self, query: str, *, top_k: int, filter_expr: str) -> Sequence[VectorRepoHit]:
        ...


@dataclass(slots=True)
class VectorSearchService:
    repo: CandidateVectorRepo
    default_top_k: int = 100
    higher_is_better: bool = True
    skill_weight: float = 0.5
    occupation_weight: float = 0.5

    def search(
        self,
        query: QueryBuilderOutput,
        compiled_filter: HardFilterCompiled,
        top_k: int | None = None,
    ) -> list[VectorHit]:
        limit = top_k or self.default_top_k
        skill_hits = (
            self.repo.search_skill(query.skill_vector_query, top_k=limit, filter_expr=compiled_filter.milvus_expr)
            if query.skill_vector_query.strip()
            else []
        )
        occupation_hits = (
            self.repo.search_occupation(
                query.occupation_vector_query,
                top_k=limit,
                filter_expr=compiled_filter.milvus_expr,
            )
            if query.occupation_vector_query.strip()
            else []
        )

        skill_norm = _normalize(skill_hits, higher_is_better=self.higher_is_better)
        occupation_norm = _normalize(occupation_hits, higher_is_better=self.higher_is_better)

        merged: dict[str, VectorHit] = {}
        for hit in skill_hits:
            item = merged.setdefault(hit.candidate_id, VectorHit(candidate_id=hit.candidate_id))
            item.skill_vector_score_raw = hit.score
            item.skill_vector_score_norm = skill_norm[hit.candidate_id]
        for hit in occupation_hits:
            item = merged.setdefault(hit.candidate_id, VectorHit(candidate_id=hit.candidate_id))
            item.occupation_vector_score_raw = hit.score
            item.occupation_vector_score_norm = occupation_norm[hit.candidate_id]

        for item in merged.values():
            skill = item.skill_vector_score_norm
            occupation = item.occupation_vector_score_norm
            if skill is not None and occupation is not None:
                item.vector_score = (self.skill_weight * skill) + (self.occupation_weight * occupation)
            elif skill is not None:
                item.vector_score = skill
            elif occupation is not None:
                item.vector_score = occupation
            else:
                item.vector_score = 0.0

        ordered = sorted(
            merged.values(),
            key=lambda hit: (
                -hit.vector_score,
                -(hit.skill_vector_score_norm or 0.0),
                -(hit.occupation_vector_score_norm or 0.0),
                hit.candidate_id,
            ),
        )
        return ordered[:limit]


def _normalize(hits: Sequence[VectorRepoHit], *, higher_is_better: bool) -> dict[str, float]:
    if not hits:
        return {}
    scores = [hit.score for hit in hits]
    minimum = min(scores)
    maximum = max(scores)
    if minimum == maximum:
        return {hit.candidate_id: 1.0 for hit in hits}

    normalized: dict[str, float] = {}
    denominator = maximum - minimum
    for hit in hits:
        if higher_is_better:
            value = (hit.score - minimum) / denominator
        else:
            value = (maximum - hit.score) / denominator
        normalized[hit.candidate_id] = max(0.0, min(1.0, value))
    return normalized
