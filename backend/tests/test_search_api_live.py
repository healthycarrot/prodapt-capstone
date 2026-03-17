from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from app.main import app


def _is_live_enabled() -> bool:
    return os.getenv("RUN_LIVE_SEARCH_TEST", "").strip().lower() in {"1", "true", "yes", "on"}


@unittest.skipUnless(
    _is_live_enabled(),
    "Live /search integration test is disabled. Set RUN_LIVE_SEARCH_TEST=1 to enable.",
)
class SearchApiLiveIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_live_search_returns_scored_results_with_thresholds(self) -> None:
        payload = {
            "query_text": "frontend engineer",
            "skill_terms": ["JavaScript", "CSS"],
            "occupation_terms": ["web developer"],
            "limit": 20,
        }

        response = self.client.post("/search", json=payload)
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(body.get("retry_required"), False)
        self.assertEqual(body.get("conflict_fields"), [])
        self.assertEqual(body.get("conflict_reason"), "no conflict")

        results = body.get("results", [])
        self.assertGreater(len(results), 0)

        keyword_scores = [float(item.get("keyword_score", 0.0)) for item in results]
        vector_scores = [float(item.get("vector_score", 0.0)) for item in results]
        final_scores = [float(item.get("final_score", 0.0)) for item in results]

        # Threshold checks for retrieval quality guardrails.
        self.assertGreater(max(keyword_scores), 0.0)
        self.assertGreaterEqual(max(keyword_scores), 0.30)
        self.assertGreaterEqual(max(vector_scores), 0.20)
        self.assertGreaterEqual(max(final_scores), 0.45)

        raw_candidates = body.get("raw_candidates", [])
        self.assertGreater(len(raw_candidates), 0)


if __name__ == "__main__":
    unittest.main()
