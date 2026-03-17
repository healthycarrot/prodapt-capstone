from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.routes.search import get_retrieval_pipeline_service
from app.domain import RerankHit, RetrievalPipelineOutput, SearchQueryInput
from app.main import app


class _StubPipeline:
    def __init__(self) -> None:
        self.calls: list[tuple[SearchQueryInput, int | None]] = []

    def run(self, search_input: SearchQueryInput, result_limit: int | None = None) -> RetrievalPipelineOutput:
        self.calls.append((search_input, result_limit))
        return RetrievalPipelineOutput(
            retry_required=False,
            conflict_fields=[],
            conflict_reason="no conflict",
            results=[
                RerankHit(
                    candidate_id="cand-001",
                    keyword_score=0.5,
                    vector_score=0.7,
                    fusion_score=0.6,
                    cross_encoder_score=0.8,
                    final_score=0.74,
                )
            ],
        )


class SearchApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stub_pipeline = _StubPipeline()
        app.dependency_overrides[get_retrieval_pipeline_service] = lambda: self.stub_pipeline
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    @patch("app.api.routes.search.fetch_normalized_candidates_raw", return_value=[])
    def test_search_returns_200_with_expected_payload(self, _mock_raw_candidates) -> None:
        payload = {
            "query_text": "string",
            "skill_terms": ["string"],
            "occupation_terms": ["string"],
            "industry_terms": ["string"],
            "experience_min_months": 0,
            "experience_max_months": 0,
            "education_min_rank": 5,
            "education_max_rank": 5,
            "locations": ["string"],
            "limit": 20,
        }

        response = self.client.post("/search", json=payload)
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(body["retry_required"], False)
        self.assertEqual(body["conflict_fields"], [])
        self.assertEqual(body["conflict_reason"], "no conflict")
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(body["results"][0]["candidate_id"], "cand-001")
        self.assertEqual(body["raw_candidates"], [])

        self.assertEqual(len(self.stub_pipeline.calls), 1)
        search_input, result_limit = self.stub_pipeline.calls[0]
        self.assertEqual(result_limit, 20)
        self.assertEqual(search_input.query_text, "string")
        self.assertEqual(search_input.requested_skill_terms, ["string"])
        self.assertEqual(search_input.requested_occupation_terms, ["string"])
        self.assertEqual(search_input.requested_industry_terms, ["string"])
        self.assertEqual(search_input.requested_experience.min_months, 0)
        self.assertEqual(search_input.requested_experience.max_months, 0)
        self.assertEqual(search_input.requested_education.min_rank, 5)
        self.assertEqual(search_input.requested_education.max_rank, 5)
        self.assertEqual(search_input.requested_locations, ["string"])

    def test_search_returns_422_when_experience_range_is_invalid(self) -> None:
        payload = {
            "query_text": "string",
            "experience_min_months": 12,
            "experience_max_months": 1,
            "education_min_rank": 5,
            "education_max_rank": 5,
            "limit": 20,
        }
        response = self.client.post("/search", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "experience_min_months must be <= experience_max_months")

    def test_search_returns_422_when_education_range_is_invalid(self) -> None:
        payload = {
            "query_text": "string",
            "experience_min_months": 0,
            "experience_max_months": 0,
            "education_min_rank": 5,
            "education_max_rank": 3,
            "limit": 20,
        }
        response = self.client.post("/search", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "education_min_rank must be <= education_max_rank")
