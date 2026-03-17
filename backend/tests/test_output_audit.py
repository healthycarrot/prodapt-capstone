from __future__ import annotations

import unittest

from app.services.output_audit import OutputAuditService


class OutputAuditServiceTests(unittest.TestCase):
    def test_summary_only_violation_triggers_sanitize_without_ranking_fallback(self) -> None:
        service = OutputAuditService(
            prohibited_terms_csv="gender",
            safe_summary_template="SAFE_SUMMARY",
            safe_reason_template="SAFE_REASON",
        )
        result = service.audit(
            request_id="req-1",
            candidate_rows=[
                {
                    "candidate_id": "cand-1",
                    "recommendation_summary": "This candidate is a good gender fit.",
                    "agent_scores": {"skill_match": {"reason": "Strong Python skill"}},
                }
            ],
        )

        self.assertEqual(result.ranking_fallback_candidate_ids, [])
        self.assertEqual(len(result.sanitize_targets), 1)
        self.assertEqual(result.sanitize_targets[0].field, "recommendation_summary")
        self.assertEqual(result.sanitize_targets[0].replacement_text, "SAFE_SUMMARY")
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(result.warnings[0].code, "output_audit_explanation_sanitized")
        self.assertEqual(len(result.logs), 1)
        self.assertEqual(result.logs[0].action, "sanitize_explanation")

    def test_agent_reason_violation_triggers_ranking_fallback_and_reason_sanitize(self) -> None:
        service = OutputAuditService(
            prohibited_terms_csv="gender",
            safe_summary_template="SAFE_SUMMARY",
            safe_reason_template="SAFE_REASON",
        )
        result = service.audit(
            request_id="req-2",
            candidate_rows=[
                {
                    "candidate_id": "cand-1",
                    "recommendation_summary": "Strong overall fit",
                    "agent_scores": {
                        "skill_match": {"reason": "gender-aligned background"},
                        "experience_match": {"reason": "Good industry depth"},
                    },
                }
            ],
        )

        self.assertEqual(result.ranking_fallback_candidate_ids, ["cand-1"])
        fields = {item.field for item in result.sanitize_targets}
        self.assertIn("agent_scores.skill_match.reason", fields)
        self.assertNotIn("agent_scores.experience_match.reason", fields)
        warning_codes = {item.code for item in result.warnings}
        self.assertIn("output_audit_ranking_fallback", warning_codes)
        self.assertEqual(len(result.logs), 1)
        self.assertEqual(result.logs[0].action, "fallback_to_retrieval_ranking")


if __name__ == "__main__":
    unittest.main()

