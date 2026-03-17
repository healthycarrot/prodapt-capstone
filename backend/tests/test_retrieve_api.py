from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.core import get_esco_lexical_repository, get_retrieval_pipeline_service
from app.domain import RerankHit, RetrievalPipelineOutput, SearchQueryInput
from app.main import app
from app.services.query_normalizer import RepoMatch


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


class _StubEscoLexicalRepository:
    def __init__(self) -> None:
        self._exact: dict[str, set[str]] = {
            "skill": {"string"},
            "occupation": {"string"},
            "industry": {"string"},
        }

    def find_exact(self, domain: str, term: str, limit: int = 5) -> list[RepoMatch]:
        normalized = term.strip().lower()
        if normalized and normalized in self._exact.get(domain, set()):
            return [RepoMatch(esco_id=f"{domain}-exact", label=term.strip(), score=0.98)]
        return []

    def find_alt(self, domain: str, term: str, limit: int = 5) -> list[RepoMatch]:
        return []

    def find_fuzzy(self, domain: str, term: str, limit: int = 5) -> list[RepoMatch]:
        return []


class RetrieveApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stub_pipeline = _StubPipeline()
        self.stub_lexical_repo = _StubEscoLexicalRepository()
        app.dependency_overrides[get_retrieval_pipeline_service] = lambda: self.stub_pipeline
        app.dependency_overrides[get_esco_lexical_repository] = lambda: self.stub_lexical_repo
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_retrieve_returns_200_with_expected_payload(self) -> None:
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

        response = self.client.post("/retrieve", json=payload)
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(body["retry_required"], False)
        self.assertEqual(body["conflict_fields"], [])
        self.assertEqual(body["conflict_reason"], "no conflict")
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(body["results"][0]["candidate_id"], "cand-001")
        self.assertNotIn("raw_candidates", body)

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

    def test_retrieve_returns_422_when_experience_range_is_invalid(self) -> None:
        payload = {
            "query_text": "string",
            "experience_min_months": 12,
            "experience_max_months": 1,
            "education_min_rank": 5,
            "education_max_rank": 5,
            "limit": 20,
        }
        response = self.client.post("/retrieve", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "experience_min_months must be <= experience_max_months")

    def test_retrieve_returns_422_when_education_range_is_invalid(self) -> None:
        payload = {
            "query_text": "string",
            "experience_min_months": 0,
            "experience_max_months": 0,
            "education_min_rank": 5,
            "education_max_rank": 3,
            "limit": 20,
        }
        response = self.client.post("/retrieve", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "education_min_rank must be <= education_max_rank")

    def test_retrieve_returns_422_when_filter_label_is_not_in_esco(self) -> None:
        payload = {
            "query_text": "string",
            "skill_terms": ["invalid-skill"],
            "limit": 20,
        }
        response = self.client.post("/retrieve", json=payload)
        self.assertEqual(response.status_code, 422)
        detail = response.json()["detail"]
        self.assertIn("invalid ESCO labels", detail)
        self.assertIn("skill_terms=['invalid-skill']", detail)

    def test_retrieve_accepts_request_without_skill_or_occupation_terms(self) -> None:
        payload = {
            "query_text": "software engineer frontend",
            "limit": 10,
        }

        response = self.client.post("/retrieve", json=payload)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(self.stub_pipeline.calls), 1)
        search_input, result_limit = self.stub_pipeline.calls[0]
        self.assertEqual(result_limit, 10)
        self.assertEqual(search_input.requested_skill_terms, [])
        self.assertEqual(search_input.requested_occupation_terms, [])


if __name__ == "__main__":
    unittest.main()
