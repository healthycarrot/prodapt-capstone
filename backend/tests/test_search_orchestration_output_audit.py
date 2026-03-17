from __future__ import annotations

import unittest

from app.domain import RetrievalPipelineOutput, RerankHit, SearchQueryInput
from app.services.agent_scoring.aggregator import IntegratedSearchCandidate
from app.services.agent_scoring.models import (
    AgentCandidateScore,
    AggregatedCandidateScore,
    OrchestratorOutput,
    QueryAnalysisOutput,
)
from app.services.output_audit import OutputAuditService
from app.services.search_orchestration import SearchOrchestrationService


class _StubRetrievalPipeline:
    def run(self, search_input: SearchQueryInput, result_limit: int | None = None) -> RetrievalPipelineOutput:
        return RetrievalPipelineOutput(
            retry_required=False,
            conflict_fields=[],
            conflict_reason="no conflict",
            results=[
                RerankHit(
                    candidate_id="cand-1",
                    keyword_score=0.4,
                    vector_score=0.8,
                    fusion_score=0.7,
                    cross_encoder_score=0.8,
                    final_score=0.60,
                ),
                RerankHit(
                    candidate_id="cand-2",
                    keyword_score=0.5,
                    vector_score=0.7,
                    fusion_score=0.65,
                    cross_encoder_score=0.75,
                    final_score=0.55,
                ),
            ],
        )


class _StubCandidateRepo:
    def fetch_candidate_profiles(self, candidate_ids):
        return {candidate_id: {"candidate_id": candidate_id} for candidate_id in candidate_ids}


class _StubOrchestrator:
    async def run(self, *, query_text, profiles, candidate_ids):
        return OrchestratorOutput(
            query_analysis=QueryAnalysisOutput(),
            agent_results={},
            candidate_scores={},
            any_agent_succeeded=True,
        )


class _StubAggregator:
    def aggregate(self, *, retrieval_hits, orchestrator_output):
        row_1 = IntegratedSearchCandidate(
            candidate_id="cand-1",
            rank=1,
            keyword_score=0.4,
            vector_score=0.8,
            fusion_score=0.7,
            cross_encoder_score=0.8,
            retrieval_final_score=0.60,
            fr04_overall_score=0.95,
            integrated_final_score=0.90,
            recommendation_summary="excellent candidate",
            aggregated=AggregatedCandidateScore(
                candidate_id="cand-1",
                fr04_overall_score=0.95,
                recommendation_summary="excellent candidate",
                agent_scores={
                    "skill_match": AgentCandidateScore(
                        candidate_id="cand-1",
                        score=0.95,
                        breakdown={"match_score": 0.95},
                        reason="gender alignment is strong",
                    )
                },
            ),
        )
        row_2 = IntegratedSearchCandidate(
            candidate_id="cand-2",
            rank=2,
            keyword_score=0.5,
            vector_score=0.7,
            fusion_score=0.65,
            cross_encoder_score=0.75,
            retrieval_final_score=0.55,
            fr04_overall_score=0.70,
            integrated_final_score=0.82,
            recommendation_summary="good candidate",
            aggregated=AggregatedCandidateScore(
                candidate_id="cand-2",
                fr04_overall_score=0.70,
                recommendation_summary="good candidate",
                agent_scores={
                    "skill_match": AgentCandidateScore(
                        candidate_id="cand-2",
                        score=0.7,
                        breakdown={"match_score": 0.7},
                        reason="strong backend skill coverage",
                    )
                },
            ),
        )
        return [row_1, row_2]


class SearchOrchestrationOutputAuditTests(unittest.TestCase):
    def test_output_audit_applies_ranking_fallback_and_reranks(self) -> None:
        service = SearchOrchestrationService(
            retrieval_pipeline=_StubRetrievalPipeline(),
            candidate_profile_repo=_StubCandidateRepo(),
            orchestrator=_StubOrchestrator(),
            aggregator=_StubAggregator(),
            output_audit=OutputAuditService(prohibited_terms_csv="gender"),
            audit_log_repo=None,
            candidate_top_n=20,
        )

        output = service.run(SearchQueryInput(query_text="backend engineer with python"))

        self.assertFalse(output.retry_required)
        self.assertEqual(len(output.results), 2)
        # cand-1 is fallbacked to retrieval score=0.60, so cand-2 (0.82) should become rank1.
        self.assertEqual(output.results[0].candidate_id, "cand-2")
        self.assertEqual(output.results[0].rank, 1)
        self.assertEqual(output.results[1].candidate_id, "cand-1")
        self.assertEqual(output.results[1].rank, 2)
        self.assertEqual(output.results[1].final_score, 0.60)
        self.assertEqual(output.results[1].fr04_overall_score, 0.0)
        self.assertIn("output_audit_retrieval_fallback_applied", output.results[1].agent_errors)
        self.assertEqual(output.results[1].agent_scores["skill_match"]["reason"], service.output_audit.safe_reason_template)
        self.assertTrue(any(w["code"] == "output_audit_ranking_fallback" for w in output.results[1].warnings))


if __name__ == "__main__":
    unittest.main()

