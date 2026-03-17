from __future__ import annotations

import unittest

from tests.eval_harness import (
    build_search_metric_factories,
    build_search_test_case,
    create_mongo_repository,
    create_test_client,
    format_metric_failure,
    get_eval_harness_settings,
    get_live_eval_skip_reason,
    run_metric,
    select_eval_cases,
)


@unittest.skipUnless(get_live_eval_skip_reason() is None, get_live_eval_skip_reason() or "Live evals are disabled.")
class SearchQualityEvalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = create_test_client()
        cls.repo = create_mongo_repository()
        cls.harness = get_eval_harness_settings()

    def test_search_metrics_run_for_top_ranked_results(self) -> None:
        for case in select_eval_cases(self.harness):
            response = self.client.post("/search", json=case.request)
            self.assertEqual(response.status_code, 200, msg=f"case={case.name}")

            body = response.json()
            self.assertFalse(body.get("retry_required"), msg=f"case={case.name} | conflict={body.get('conflict_reason')}")
            results = list(body.get("results", []))
            self.assertGreater(len(results), 0, msg=f"case={case.name} | no search results returned")

            top_n = max(1, min(case.top_search_results, self.harness.search_result_top_n, len(results)))
            top_results = results[:top_n]
            candidate_ids = [str(item.get("candidate_id") or "").strip() for item in top_results]
            profiles = self.repo.fetch_candidate_profiles(candidate_ids)

            for row in top_results:
                candidate_id = str(row.get("candidate_id") or "").strip()
                summary = str(row.get("recommendation_summary") or "").strip()
                self.assertTrue(summary, msg=f"case={case.name} | candidate_id={candidate_id} | missing summary")

                test_case = build_search_test_case(
                    case=case,
                    result_row=row,
                    profile=profiles.get(candidate_id, {}),
                    harness=self.harness,
                )

                for metric_name, metric_factory in build_search_metric_factories(self.harness):
                    with self.subTest(case=case.name, candidate_id=candidate_id, metric=metric_name):
                        evaluation = run_metric(metric_name, metric_factory(), test_case)
                        self.assertGreaterEqual(evaluation.score, 0.0)
                        self.assertLessEqual(evaluation.score, 1.0)
                        if self.harness.enforce_thresholds:
                            self.assertTrue(
                                evaluation.success,
                                msg=format_metric_failure(
                                    evaluation,
                                    case_name=case.name,
                                    candidate_id=candidate_id,
                                ),
                            )


if __name__ == "__main__":
    unittest.main()
