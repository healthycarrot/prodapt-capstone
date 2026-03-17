from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from ..domain import FusionHit, KeywordHit, VectorHit

FusionStrategy = Literal["weighted_sum", "rrf"]


@dataclass(slots=True)
class FusionService:
    strategy: FusionStrategy = "weighted_sum"
    vector_weight: float = 0.5
    keyword_weight: float = 0.5
    rrf_k: int = 60
    default_top_k: int = 50

    def fuse(
        self,
        vector_hits: Sequence[VectorHit],
        keyword_hits: Sequence[KeywordHit],
        top_k: int | None = None,
    ) -> list[FusionHit]:
        limit = top_k or self.default_top_k

        vector_by_id = {hit.candidate_id: hit for hit in vector_hits}
        keyword_by_id = {hit.candidate_id: hit for hit in keyword_hits}
        all_ids = list(dict.fromkeys([*vector_by_id.keys(), *keyword_by_id.keys()]))

        rank_vector = {hit.candidate_id: rank + 1 for rank, hit in enumerate(vector_hits)}
        rank_keyword = {hit.candidate_id: rank + 1 for rank, hit in enumerate(keyword_hits)}

        fused: list[FusionHit] = []
        for candidate_id in all_ids:
            vector_score = vector_by_id.get(candidate_id).vector_score if candidate_id in vector_by_id else 0.0
            keyword_score = keyword_by_id.get(candidate_id).keyword_score if candidate_id in keyword_by_id else 0.0

            if self.strategy == "rrf":
                fusion_score = _rrf_score(
                    rank_vector.get(candidate_id),
                    rank_keyword.get(candidate_id),
                    self.rrf_k,
                )
            else:
                fusion_score = (self.vector_weight * vector_score) + (self.keyword_weight * keyword_score)

            fused.append(
                FusionHit(
                    candidate_id=candidate_id,
                    vector_score=vector_score,
                    keyword_score=keyword_score,
                    fusion_score=fusion_score,
                )
            )

        fused.sort(key=lambda item: (-item.fusion_score, -item.vector_score, -item.keyword_score, item.candidate_id))
        return fused[:limit]


def _rrf_score(rank_vector: int | None, rank_keyword: int | None, rrf_k: int) -> float:
    score = 0.0
    if rank_vector is not None:
        score += 1.0 / (rrf_k + rank_vector)
    if rank_keyword is not None:
        score += 1.0 / (rrf_k + rank_keyword)
    return score
