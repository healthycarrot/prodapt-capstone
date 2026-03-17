from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from ..domain import HardFilterCompiled, KeywordHit


@dataclass(slots=True)
class KeywordRepoHit:
    candidate_id: str
    text_score: float


class KeywordSearchRepo(Protocol):
    def search(
        self,
        query: str,
        *,
        top_k: int,
        mongo_filter: dict[str, object] | None = None,
    ) -> Sequence[KeywordRepoHit]:
        ...


@dataclass(slots=True)
class KeywordSearchService:
    repo: KeywordSearchRepo
    default_top_k: int = 100
    clip_lower_percentile: float = 5.0
    clip_upper_percentile: float = 95.0

    def search(
        self,
        query: str,
        compiled_filter: HardFilterCompiled,
        top_k: int | None = None,
    ) -> list[KeywordHit]:
        limit = top_k or self.default_top_k
        raw_hits = self.repo.search(
            query=query,
            top_k=limit,
            mongo_filter=compiled_filter.mongo_filter,
        )
        normalized_scores = _percentile_clip_minmax(
            [hit.text_score for hit in raw_hits],
            lower=self.clip_lower_percentile,
            upper=self.clip_upper_percentile,
        )
        results: list[KeywordHit] = []
        for index, hit in enumerate(raw_hits):
            results.append(
                KeywordHit(
                    candidate_id=hit.candidate_id,
                    keyword_score_raw=hit.text_score,
                    keyword_score=normalized_scores[index],
                )
            )
        return sorted(results, key=lambda item: (-item.keyword_score, -item.keyword_score_raw, item.candidate_id))[:limit]


def _percentile_clip_minmax(scores: list[float], *, lower: float, upper: float) -> list[float]:
    if not scores:
        return []
    if len(scores) == 1:
        return [1.0]

    sorted_scores = sorted(scores)
    low = _percentile(sorted_scores, lower)
    high = _percentile(sorted_scores, upper)

    if high < low:
        low, high = high, low

    clipped = [min(max(score, low), high) for score in scores]
    minimum = min(clipped)
    maximum = max(clipped)
    if minimum == maximum:
        return [1.0 for _ in clipped]
    denominator = maximum - minimum
    return [max(0.0, min(1.0, (value - minimum) / denominator)) for value in clipped]


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        return 0.0
    if percentile <= 0:
        return sorted_values[0]
    if percentile >= 100:
        return sorted_values[-1]
    rank = (percentile / 100.0) * (len(sorted_values) - 1)
    low_index = int(rank)
    high_index = min(low_index + 1, len(sorted_values) - 1)
    fraction = rank - low_index
    low_value = sorted_values[low_index]
    high_value = sorted_values[high_index]
    return low_value + (high_value - low_value) * fraction
