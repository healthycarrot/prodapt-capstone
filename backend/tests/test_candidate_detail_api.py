from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.core import get_mongo_repository
from app.main import app


class _StubMongoRepository:
    def __init__(self) -> None:
        self.records = {
            "49cbb2bd-a850-4e45-97f7-a24883a7ad96": {
                "candidate_id": "49cbb2bd-a850-4e45-97f7-a24883a7ad96",
                "source_dataset": "1st_data",
                "source_record_id": "123",
                "current_location": "Tokyo",
                "category": "data engineer",
                "resume_text": "Experienced data engineer...",
                "occupation_candidates": [{"esco_id": "occ-1", "preferred_label": "Data Engineer"}],
                "skill_candidates": [{"esco_id": "skill-1", "preferred_label": "Python"}],
                "experiences": [{"title": "Data Engineer", "duration_months": 24}],
                "educations": [{"degree": "Bachelor", "field_of_study": "Computer Science"}],
            }
        }

    def fetch_candidate_detail(self, candidate_id: str):  # noqa: ANN001 - test stub
        return self.records.get(candidate_id)

    def fetch_candidate_resume_raw(self, candidate_id: str):  # noqa: ANN001 - test stub
        record = self.records.get(candidate_id)
        if record is None:
            return None
        return {
            "candidate_id": record["candidate_id"],
            "source_dataset": record["source_dataset"],
            "source_record_id": record["source_record_id"],
            "resume_text": record["resume_text"],
        }


class CandidateDetailApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stub_repo = _StubMongoRepository()
        app.dependency_overrides[get_mongo_repository] = lambda: self.stub_repo
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_get_candidate_detail_returns_200(self) -> None:
        response = self.client.get("/candidates/49cbb2bd-a850-4e45-97f7-a24883a7ad96")
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(body["candidate_id"], "49cbb2bd-a850-4e45-97f7-a24883a7ad96")
        self.assertEqual(body["source_dataset"], "1st_data")
        self.assertEqual(body["source_record_id"], "123")
        self.assertEqual(body["current_location"], "Tokyo")
        self.assertEqual(body["category"], "data engineer")
        self.assertIn("occupation_candidates", body)
        self.assertIn("skill_candidates", body)
        self.assertIn("experiences", body)
        self.assertIn("educations", body)

    def test_get_candidate_detail_returns_404_when_missing(self) -> None:
        response = self.client.get("/candidates/e6cd8668-bb1e-4dc4-ab62-b783b329b9f4")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "candidate not found")

    def test_get_candidate_detail_returns_422_on_invalid_candidate_id(self) -> None:
        response = self.client.get("/candidates/not-a-uuid")
        self.assertEqual(response.status_code, 422)

    def test_get_candidate_resume_raw_returns_200(self) -> None:
        response = self.client.get("/candidates/49cbb2bd-a850-4e45-97f7-a24883a7ad96/resume")
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(body["candidate_id"], "49cbb2bd-a850-4e45-97f7-a24883a7ad96")
        self.assertEqual(body["source_dataset"], "1st_data")
        self.assertEqual(body["source_record_id"], "123")
        self.assertEqual(body["resume_text"], "Experienced data engineer...")

    def test_get_candidate_resume_raw_returns_404_when_missing(self) -> None:
        response = self.client.get("/candidates/e6cd8668-bb1e-4dc4-ab62-b783b329b9f4/resume")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "candidate not found")

    def test_get_candidate_resume_raw_returns_422_on_invalid_candidate_id(self) -> None:
        response = self.client.get("/candidates/not-a-uuid/resume")
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
