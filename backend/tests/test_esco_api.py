from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.core import get_esco_lexical_repository
from app.main import app
from app.services.query_normalizer import RepoMatch


class _StubEscoLexicalRepository:
    def suggest(self, domain: str, query: str, limit: int = 10) -> list[RepoMatch]:
        if domain == "occupation" and query.strip().lower().startswith("data"):
            return [
                RepoMatch(
                    esco_id="http://data.europa.eu/esco/occupation/data-engineer",
                    label="data engineer",
                    score=0.98,
                ),
                RepoMatch(
                    esco_id="http://data.europa.eu/esco/occupation/data-scientist",
                    label="data scientist",
                    score=0.92,
                ),
            ][:limit]
        return []

    def find_exact(self, domain: str, term: str, limit: int = 5) -> list[RepoMatch]:
        return []

    def find_alt(self, domain: str, term: str, limit: int = 5) -> list[RepoMatch]:
        return []

    def find_fuzzy(self, domain: str, term: str, limit: int = 5) -> list[RepoMatch]:
        return []


class EscoApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stub_repo = _StubEscoLexicalRepository()
        app.dependency_overrides[get_esco_lexical_repository] = lambda: self.stub_repo
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_suggest_returns_esco_candidates(self) -> None:
        response = self.client.get("/esco/suggest", params={"domain": "occupation", "q": "data", "limit": 5})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["domain"], "occupation")
        self.assertEqual(body["query"], "data")
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["results"][0]["label"], "data engineer")
        self.assertIn("esco_id", body["results"][0])

    def test_suggest_returns_empty_when_query_is_too_short(self) -> None:
        response = self.client.get("/esco/suggest", params={"domain": "skill", "q": "d", "limit": 10})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["results"], [])

    def test_suggest_rejects_invalid_domain(self) -> None:
        response = self.client.get("/esco/suggest", params={"domain": "invalid", "q": "data", "limit": 10})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
