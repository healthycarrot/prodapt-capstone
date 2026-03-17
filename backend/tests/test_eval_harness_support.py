from __future__ import annotations

import unittest

from tests.eval_harness import (
    build_candidate_context,
    build_ranked_retrieval_context,
    get_eval_harness_settings,
    load_eval_cases,
    select_eval_cases,
    serialize_request,
)


class EvalHarnessSupportTests(unittest.TestCase):
    def test_load_eval_cases_returns_named_cases(self) -> None:
        cases = load_eval_cases()
        self.assertGreaterEqual(len(cases), 30)
        self.assertTrue(all(case.name for case in cases))
        self.assertTrue(all(case.expected_output for case in cases))

    def test_select_eval_cases_applies_limit(self) -> None:
        harness = get_eval_harness_settings()
        selected = select_eval_cases(harness)
        self.assertGreaterEqual(len(selected), 1)
        self.assertLessEqual(len(selected), harness.case_limit)

    def test_serialize_request_keeps_non_empty_fields(self) -> None:
        payload = {
            "query_text": "backend engineer",
            "skill_terms": ["Python"],
            "occupation_terms": ["software engineer"],
            "limit": 5,
            "industry_terms": [],
        }
        text = serialize_request(payload)
        self.assertIn("query_text: backend engineer", text)
        self.assertIn("skill_terms", text)
        self.assertIn("occupation_terms", text)
        self.assertNotIn("industry_terms", text)

    def test_build_candidate_context_prefers_structured_fields(self) -> None:
        profile = {
            "occupation_labels": ["web developer"],
            "skill_labels": ["JavaScript", "CSS"],
            "experiences": [
                {
                    "title": "Frontend Engineer",
                    "company_name": "Example Co",
                    "description_raw": "Built interactive web applications.",
                    "duration_months": 24,
                }
            ],
            "educations": [
                {
                    "degree": "Bachelor of Science",
                    "field_of_study": "Computer Science",
                    "school_name": "Example University",
                }
            ],
            "resume_text": "Longer resume text that should still be included as the final evidence chunk.",
        }
        chunks = build_candidate_context(profile)
        joined = "\n".join(chunks)
        self.assertIn("Occupations: web developer", joined)
        self.assertIn("Skills: JavaScript, CSS", joined)
        self.assertIn("Experience: Frontend Engineer | Example Co", joined)
        self.assertIn("Education: Bachelor of Science | Computer Science | Example University", joined)
        self.assertIn("Resume excerpt:", joined)

    def test_build_ranked_retrieval_context_preserves_order(self) -> None:
        results = [
            {"candidate_id": "cand-001", "final_score": 0.92},
            {"candidate_id": "cand-002", "final_score": 0.71},
        ]
        profiles = {
            "cand-001": {"skill_labels": ["Python"], "occupation_labels": ["software engineer"]},
            "cand-002": {"skill_labels": ["SQL"], "occupation_labels": ["data analyst"]},
        }
        contexts = build_ranked_retrieval_context(results, profiles, top_k=2)
        self.assertEqual(len(contexts), 2)
        self.assertIn("Rank 1 | candidate_id=cand-001", contexts[0])
        self.assertIn("Rank 2 | candidate_id=cand-002", contexts[1])


if __name__ == "__main__":
    unittest.main()
