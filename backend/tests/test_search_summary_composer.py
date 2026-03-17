from __future__ import annotations

import unittest

from app.services.agent_scoring.aggregator import IntegratedSearchCandidate
from app.services.agent_scoring.models import AgentCandidateScore, AggregatedCandidateScore, CandidateProfile
from app.services.search_orchestration import _compose_grounded_summary, _map_integrated_row


class SearchSummaryComposerTests(unittest.TestCase):
    def test_compose_grounded_summary_prefers_structured_evidence(self) -> None:
        summary = _compose_grounded_summary(
            fallback_summary="skill_match: strong communication and leadership in agile teams",
            profile=CandidateProfile(
                candidate_id="cand-1",
                resume_text="",
                occupation_labels=["web developer", "software developer"],
                skill_labels=["JavaScript", "TypeScript", "CSS"],
            ),
            skill_matches=["JavaScript", "TypeScript", "JavaScript"],
            transferable_skills=["React"],
            experience_matches=["frontend web applications", "component-based UI delivery"],
            major_gaps=["React not explicit", "GraphQL not explicit"],
        )

        self.assertEqual(
            summary,
            "Matched skills: JavaScript, TypeScript. Relevant experience: frontend web applications, component-based UI delivery. Gaps to review: React not explicit, GraphQL not explicit.",
        )

    def test_compose_grounded_summary_falls_back_to_occupation_when_experience_is_missing(self) -> None:
        summary = _compose_grounded_summary(
            fallback_summary="freeform agent reason",
            profile=CandidateProfile(
                candidate_id="cand-2",
                resume_text="",
                occupation_labels=["accountant", "financial controller"],
            ),
            skill_matches=[],
            transferable_skills=["financial analysis"],
            experience_matches=[],
            major_gaps=[],
        )

        self.assertEqual(
            summary,
            "Transferable skills: financial analysis. Role alignment: accountant, financial controller.",
        )

    def test_compose_grounded_summary_uses_fallback_when_structured_evidence_is_empty(self) -> None:
        summary = _compose_grounded_summary(
            fallback_summary="skill_match: strong backend experience",
            profile=None,
            skill_matches=[],
            transferable_skills=[],
            experience_matches=[],
            major_gaps=[],
        )

        self.assertEqual(summary, "skill_match: strong backend experience")

    def test_map_integrated_row_rewrites_summary_from_structured_fields(self) -> None:
        row = IntegratedSearchCandidate(
            candidate_id="cand-3",
            rank=1,
            keyword_score=0.4,
            vector_score=0.8,
            fusion_score=0.7,
            cross_encoder_score=0.85,
            retrieval_final_score=0.81,
            fr04_overall_score=0.76,
            integrated_final_score=0.79,
            recommendation_summary="skill_match: mentions leadership and teamwork",
            aggregated=AggregatedCandidateScore(
                candidate_id="cand-3",
                fr04_overall_score=0.76,
                recommendation_summary="skill_match: mentions leadership and teamwork",
                major_gaps=["Kubernetes not explicit"],
                agent_scores={
                    "skill_match": AgentCandidateScore(
                        candidate_id="cand-3",
                        score=0.82,
                        breakdown={"match_score": 0.9},
                        reason="mentions leadership and teamwork",
                        details={
                            "matched_skills": ["Python", "SQL"],
                            "transferable_skills": ["Django"],
                        },
                    ),
                    "experience_match": AgentCandidateScore(
                        candidate_id="cand-3",
                        score=0.71,
                        breakdown={"industry_match_score": 0.7},
                        reason="mentions seniority",
                        details={
                            "experience_matches": ["backend service development"],
                        },
                    ),
                },
            ),
        )

        result = _map_integrated_row(
            row,
            profile=CandidateProfile(
                candidate_id="cand-3",
                resume_text="",
                occupation_labels=["software developer"],
                skill_labels=["Python", "SQL"],
            ),
        )

        self.assertEqual(
            result.recommendation_summary,
            "Matched skills: Python, SQL. Relevant experience: backend service development. Gaps to review: Kubernetes not explicit.",
        )


if __name__ == "__main__":
    unittest.main()
