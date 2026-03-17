from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

from ..domain import CrossEncoderHit, CrossEncoderResult, FusionHit


class CandidateTextRepo(Protocol):
    def fetch_rerank_text(self, candidate_ids: Sequence[str]) -> Mapping[str, str]:
        ...


class CrossEncoderModel(Protocol):
    def score(self, query_text: str, candidate_texts: Sequence[str]) -> Sequence[float]:
        ...


@dataclass(slots=True)
class CrossEncoderService:
    text_repo: CandidateTextRepo
    model: CrossEncoderModel | None = None
    default_top_k: int = 50

    def rerank(
        self,
        query_text: str,
        fusion_hits: Sequence[FusionHit],
        top_k: int | None = None,
    ) -> CrossEncoderResult:
        limit = top_k or self.default_top_k
        selected = list(fusion_hits[:limit])
        if not selected:
            return CrossEncoderResult(cross_encoder_applied=True, fallback_reason=None, hits=[])

        if self.model is None:
            return _fallback(selected, "cross_encoder_not_configured")

        candidate_ids = [hit.candidate_id for hit in selected]
        try:
            candidate_text_map = self.text_repo.fetch_rerank_text(candidate_ids)
            texts = [candidate_text_map.get(candidate_id, "") for candidate_id in candidate_ids]
            scores = list(self.model.score(query_text, texts))
            if len(scores) != len(selected):
                return _fallback(selected, "cross_encoder_output_size_mismatch")

            hits = [
                CrossEncoderHit(
                    candidate_id=selected[index].candidate_id,
                    fusion_score=selected[index].fusion_score,
                    cross_encoder_score=_clamp01(scores[index]),
                )
                for index in range(len(selected))
            ]
            hits.sort(key=lambda item: (-item.cross_encoder_score, -item.fusion_score, item.candidate_id))
            return CrossEncoderResult(cross_encoder_applied=True, fallback_reason=None, hits=hits)
        except Exception as exc:
            return _fallback(selected, f"cross_encoder_error:{exc.__class__.__name__}")


def _fallback(fusion_hits: list[FusionHit], reason: str) -> CrossEncoderResult:
    hits = [
        CrossEncoderHit(
            candidate_id=hit.candidate_id,
            fusion_score=hit.fusion_score,
            cross_encoder_score=0.0,
        )
        for hit in fusion_hits
    ]
    return CrossEncoderResult(
        cross_encoder_applied=False,
        fallback_reason=reason,
        hits=hits,
    )


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value
