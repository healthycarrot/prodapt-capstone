from __future__ import annotations

import unittest
from difflib import SequenceMatcher

import app.repositories.esco_lexical_repo as lexical_repo
from app.services.query_normalizer import RepoMatch


class EscoLexicalRepoTests(unittest.TestCase):
    def test_fuzzy_score_is_not_inflated_by_lexical_base_score(self) -> None:
        values = [
            (
                "python",
                RepoMatch(
                    esco_id="esco-python",
                    label="Python (computer programming)",
                    score=0.98,
                ),
            )
        ]
        query = "pytohn"  # typo

        original_process = lexical_repo.process
        original_fuzz = lexical_repo.fuzz
        lexical_repo.process = None
        lexical_repo.fuzz = None
        try:
            result = lexical_repo._fuzzy_search(
                query=query,
                values=values,
                limit=5,
                min_score=0.0,
            )
        finally:
            lexical_repo.process = original_process
            lexical_repo.fuzz = original_fuzz

        self.assertEqual(len(result), 1)
        expected_confidence = SequenceMatcher(a=query, b="python").ratio()
        self.assertAlmostEqual(result[0].score, expected_confidence, places=6)
        self.assertLess(result[0].score, 0.98)

    def test_fuzzy_score_respects_alt_label_cap(self) -> None:
        values = [
            (
                "backend engineer",
                RepoMatch(
                    esco_id="esco-backend",
                    label="Backend engineer",
                    score=0.87,
                ),
            )
        ]
        query = "backend engineer"

        original_process = lexical_repo.process
        original_fuzz = lexical_repo.fuzz
        lexical_repo.process = None
        lexical_repo.fuzz = None
        try:
            result = lexical_repo._fuzzy_search(
                query=query,
                values=values,
                limit=5,
                min_score=0.0,
            )
        finally:
            lexical_repo.process = original_process
            lexical_repo.fuzz = original_fuzz

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0].score, 0.87, places=6)

    def test_suggest_prioritizes_exact_then_alt_then_partial(self) -> None:
        repo = lexical_repo.EscoLexicalMongoRepository()
        repo._index_cache["occupation"] = lexical_repo._build_index(
            [
                {
                    "esco_id": "occupation-1",
                    "preferred_label": "data engineer",
                    "alt_labels": ["etl engineer"],
                },
                {
                    "esco_id": "occupation-2",
                    "preferred_label": "analytics engineer",
                    "alt_labels": ["data engineer"],
                },
                {
                    "esco_id": "occupation-3",
                    "preferred_label": "senior data engineer",
                },
            ]
        )

        result = repo.suggest("occupation", "data engineer", limit=10)
        ids = [item.esco_id for item in result]
        self.assertEqual(ids[0], "occupation-1")
        self.assertEqual(ids[1], "occupation-2")
        self.assertIn("occupation-3", ids)

    def test_suggest_respects_limit_and_deduplicates(self) -> None:
        repo = lexical_repo.EscoLexicalMongoRepository()
        repo._index_cache["skill"] = lexical_repo._build_index(
            [
                {
                    "esco_id": "skill-1",
                    "preferred_label": "python",
                    "alt_labels": ["python", "py"],
                },
                {
                    "esco_id": "skill-2",
                    "preferred_label": "python programming",
                },
                {
                    "esco_id": "skill-3",
                    "preferred_label": "python scripting",
                },
            ]
        )

        result = repo.suggest("skill", "python", limit=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(len({item.esco_id for item in result}), 2)


if __name__ == "__main__":
    unittest.main()
