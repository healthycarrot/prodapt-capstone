from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ...domain import RerankHit
from .models import AggregatedCandidateScore, OrchestratorOutput, normalize_weights


@dataclass(slots=True)
class IntegratedSearchCandidate:
    candidate_id: str
    rank: int
    keyword_score: float
    vector_score: float
    fusion_score: float
    cross_encoder_score: float
    retrieval_final_score: float
    fr04_overall_score: float
    integrated_final_score: float
    recommendation_summary: str
    aggregated: AggregatedCandidateScore


@dataclass(slots=True)
class AgentScoreAggregatorService:
    retrieval_weight: float = 0.60
    fr04_weight: float = 0.40

    def aggregate(
        self,
        *,
        retrieval_hits: Sequence[RerankHit],
        orchestrator_output: OrchestratorOutput,
    ) -> list[IntegratedSearchCandidate]:
        rows: list[IntegratedSearchCandidate] = []
        use_fallback = not orchestrator_output.any_agent_succeeded
        blend = normalize_weights(
            {
                "retrieval": self.retrieval_weight,
                "fr04": self.fr04_weight,
            }
        )
        retrieval_weight = blend.get("retrieval", 1.0)
        fr04_weight = blend.get("fr04", 0.0)

        for hit in retrieval_hits:
            aggregated = orchestrator_output.candidate_scores.get(
                hit.candidate_id,
                AggregatedCandidateScore(
                    candidate_id=hit.candidate_id,
                    fr04_overall_score=0.0,
                    recommendation_summary="FR-04 agent evidence is unavailable. Retrieval score is used as fallback.",
                ),
            )
            if use_fallback:
                final_score = hit.final_score
                fr04_score = 0.0
            else:
                fr04_score = aggregated.fr04_overall_score
                final_score = (retrieval_weight * hit.final_score) + (fr04_weight * fr04_score)
            rows.append(
                IntegratedSearchCandidate(
                    candidate_id=hit.candidate_id,
                    rank=0,
                    keyword_score=hit.keyword_score,
                    vector_score=hit.vector_score,
                    fusion_score=hit.fusion_score,
                    cross_encoder_score=hit.cross_encoder_score,
                    retrieval_final_score=hit.final_score,
                    fr04_overall_score=fr04_score,
                    integrated_final_score=final_score,
                    recommendation_summary=aggregated.recommendation_summary,
                    aggregated=aggregated,
                )
            )

        rows.sort(
            key=lambda item: (
                -item.integrated_final_score,
                -item.retrieval_final_score,
                -item.cross_encoder_score,
                -item.fusion_score,
                -item.vector_score,
                -item.keyword_score,
                item.candidate_id,
            )
        )
        for index, row in enumerate(rows, start=1):
            row.rank = index
        return rows
