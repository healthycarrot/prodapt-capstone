from __future__ import annotations

import unittest

from app.domain import HardFilterInput
from app.services.hard_filter_compiler import HardFilterCompilerService


class HardFilterCompilerTests(unittest.TestCase):
    def test_compile_uses_nested_mongo_fields_for_skill_and_occupation(self) -> None:
        compiled = HardFilterCompilerService().compile(
            HardFilterInput(
                skill_esco_ids_high=["skill-1", "skill-1", "skill-2"],
                occupation_esco_ids_high=["occ-1"],
                industry_esco_ids_high=["ind-1"],
            )
        )

        self.assertIn('json_contains_any(skill_esco_ids_json, ["skill-1", "skill-2"])', compiled.milvus_expr)
        self.assertIn('json_contains_any(occupation_esco_ids_json, ["occ-1"])', compiled.milvus_expr)
        self.assertIn('json_contains_any(industry_esco_ids_json, ["ind-1"])', compiled.milvus_expr)
        self.assertEqual(
            compiled.mongo_filter,
            {
                "$and": [
                    {"skill_candidates.esco_id": {"$in": ["skill-1", "skill-2"]}},
                    {"occupation_candidates.esco_id": {"$in": ["occ-1"]}},
                    {"occupation_candidates.hierarchy_json.id": {"$in": ["ind-1"]}},
                ]
            },
        )

    def test_compile_returns_single_mongo_clause_without_and(self) -> None:
        compiled = HardFilterCompilerService().compile(
            HardFilterInput(skill_esco_ids_high=["skill-1"])
        )

        self.assertEqual(compiled.mongo_filter, {"skill_candidates.esco_id": {"$in": ["skill-1"]}})


if __name__ == "__main__":
    unittest.main()
