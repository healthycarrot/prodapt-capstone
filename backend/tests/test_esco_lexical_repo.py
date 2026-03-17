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


if __name__ == "__main__":
    unittest.main()
