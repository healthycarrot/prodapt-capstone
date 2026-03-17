from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.core import get_esco_lexical_repository, get_search_orchestration_service
from app.domain import SearchQueryInput
from app.main import app
from app.services.query_normalizer import RepoMatch
from app.services.search_orchestration import SearchOrchestrationOutput, SearchOrchestrationResultItem


class _StubSearchOrchestrationService:
    def __init__(self) -> None:
        self.calls: list[tuple[SearchQueryInput, int | None]] = []

    def run(self, search_input: SearchQueryInput, result_limit: int | None = None) -> SearchOrchestrationOutput:
        self.calls.append((search_input, result_limit))
        return SearchOrchestrationOutput(
            retry_required=False,
            conflict_fields=[],
            conflict_reason="no conflict",
            results=[
                SearchOrchestrationResultItem(
                    candidate_id="cand-001",
                    rank=1,
                    keyword_score=0.5,
                    vector_score=0.7,
                    fusion_score=0.6,
                    cross_encoder_score=0.8,
                    retrieval_final_score=0.74,
                    fr04_overall_score=0.67,
                    final_score=0.71,
                    recommendation_summary="skill_match: strong backend experience",
                    skill_matches=["python", "fastapi"],
                    transferable_skills=["django"],
                    experience_matches=["backend service development"],
                    major_gaps=["kubernetes"],
                    agent_scores={
                        "skill_match": {
                            "score": 0.72,
                            "breakdown": {
                                "match_score": 0.80,
                                "skill_depth_score": 0.65,
                                "management_score": 0.60,
                            },
                            "reason": "core skills align",
                        }
                    },
                    agent_errors=[],
                )
            ],
        )


class _StubEscoLexicalRepository:
    def __init__(self) -> None:
        self._exact: dict[str, set[str]] = {
            "skill": {"string", "python", "fastapi"},
            "occupation": {"string", "backend developer"},
            "industry": {"string", "information technology"},
        }
        self._alt: dict[str, set[str]] = {
            "skill": {"py"},
            "occupation": {"backend engineer"},
            "industry": {"it"},
        }

    def find_exact(self, domain: str, term: str, limit: int = 5) -> list[RepoMatch]:
        normalized = term.strip().lower()
        if normalized and normalized in self._exact.get(domain, set()):
            return [RepoMatch(esco_id=f"{domain}-exact", label=term.strip(), score=0.98)]
        return []

    def find_alt(self, domain: str, term: str, limit: int = 5) -> list[RepoMatch]:
        normalized = term.strip().lower()
        if normalized and normalized in self._alt.get(domain, set()):
            return [RepoMatch(esco_id=f"{domain}-alt", label=term.strip(), score=0.87)]
        return []

    def find_fuzzy(self, domain: str, term: str, limit: int = 5) -> list[RepoMatch]:
        return []


class SearchApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stub_service = _StubSearchOrchestrationService()
        self.stub_lexical_repo = _StubEscoLexicalRepository()
        app.dependency_overrides[get_search_orchestration_service] = lambda: self.stub_service
        app.dependency_overrides[get_esco_lexical_repository] = lambda: self.stub_lexical_repo
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_search_returns_200_with_expected_payload(self) -> None:
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

        first = body["results"][0]
        self.assertEqual(first["candidate_id"], "cand-001")
        self.assertEqual(first["rank"], 1)
        self.assertGreater(first["final_score"], 0.0)
        self.assertGreater(first["retrieval_final_score"], 0.0)
        self.assertGreater(first["fr04_overall_score"], 0.0)
        self.assertIn("skill_match", first["agent_scores"])
        self.assertEqual(first["major_gaps"], ["kubernetes"])

        self.assertEqual(len(self.stub_service.calls), 1)
        search_input, result_limit = self.stub_service.calls[0]
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

    def test_search_returns_422_when_filter_label_is_not_in_esco(self) -> None:
        payload = {
            "query_text": "string",
            "skill_terms": ["not-an-esco-skill"],
            "occupation_terms": ["string"],
            "industry_terms": ["string"],
            "limit": 20,
        }
        response = self.client.post("/search", json=payload)
        self.assertEqual(response.status_code, 422)
        detail = response.json()["detail"]
        self.assertIn("invalid ESCO labels", detail)
        self.assertIn("skill_terms=['not-an-esco-skill']", detail)

    def test_search_accepts_request_without_skill_or_occupation_terms(self) -> None:
        payload = {
            "query_text": "software engineer frontend",
            "limit": 10,
        }

        response = self.client.post("/search", json=payload)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(self.stub_service.calls), 1)
        search_input, result_limit = self.stub_service.calls[0]
        self.assertEqual(result_limit, 10)
        self.assertEqual(search_input.requested_skill_terms, [])
        self.assertEqual(search_input.requested_occupation_terms, [])


if __name__ == "__main__":
    unittest.main()
