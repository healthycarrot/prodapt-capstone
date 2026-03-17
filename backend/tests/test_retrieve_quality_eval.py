from __future__ import annotations

import unittest

from tests.eval_harness import (
    build_retrieve_metric_factories,
    build_retrieve_test_case,
    create_mongo_repository,
    create_test_client,
    format_metric_failure,
    get_eval_harness_settings,
    get_live_eval_skip_reason,
    run_metric,
    select_eval_cases,
)


@unittest.skipUnless(get_live_eval_skip_reason() is None, get_live_eval_skip_reason() or "Live evals are disabled.")
class RetrieveQualityEvalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = create_test_client()
        cls.repo = create_mongo_repository()
        cls.harness = get_eval_harness_settings()

    def test_retrieve_metrics_run_for_all_cases(self) -> None:
        for case in select_eval_cases(self.harness):
            response = self.client.post("/retrieve", json=case.request)
            self.assertEqual(response.status_code, 200, msg=f"case={case.name}")

            body = response.json()
            self.assertFalse(body.get("retry_required"), msg=f"case={case.name} | conflict={body.get('conflict_reason')}")
            results = list(body.get("results", []))
            self.assertGreater(len(results), 0, msg=f"case={case.name} | no retrieval results returned")

            top_k = max(1, min(case.top_k, self.harness.retrieval_top_k, len(results)))
            candidate_ids = [str(item.get("candidate_id") or "").strip() for item in results[:top_k]]
            profiles = self.repo.fetch_candidate_profiles(candidate_ids)
            test_case = build_retrieve_test_case(case, results, profiles, self.harness)

            for metric_name, metric_factory in build_retrieve_metric_factories(self.harness):
                with self.subTest(case=case.name, metric=metric_name):
                    evaluation = run_metric(metric_name, metric_factory(), test_case)
                    self.assertGreaterEqual(evaluation.score, 0.0)
                    self.assertLessEqual(evaluation.score, 1.0)
                    if self.harness.enforce_thresholds:
                        self.assertTrue(
                            evaluation.success,
                            msg=format_metric_failure(evaluation, case_name=case.name),
                        )


if __name__ == "__main__":
    unittest.main()
