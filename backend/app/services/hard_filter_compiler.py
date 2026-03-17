from __future__ import annotations

import json
from dataclasses import dataclass

from ..domain import HardFilterCompiled, HardFilterInput


@dataclass(slots=True)
class HardFilterCompilerService:
    """
    Compile FR-01 hard filters for Milvus and Mongo.
    Milvus filters use flattened JSON ID arrays, while Mongo filters target
    normalized candidate fields.
    """

    def compile(self, hard_filter: HardFilterInput) -> HardFilterCompiled:
        milvus_parts: list[str] = []
        mongo_clauses: list[dict[str, object]] = []

        self._append_esco_any(
            milvus_field="skill_esco_ids_json",
            mongo_field="skill_candidates.esco_id",
            values=hard_filter.skill_esco_ids_high,
            milvus_parts=milvus_parts,
            mongo_clauses=mongo_clauses,
        )
        self._append_esco_any(
            milvus_field="occupation_esco_ids_json",
            mongo_field="occupation_candidates.esco_id",
            values=hard_filter.occupation_esco_ids_high,
            milvus_parts=milvus_parts,
            mongo_clauses=mongo_clauses,
        )
        self._append_esco_any(
            milvus_field="industry_esco_ids_json",
            mongo_field="occupation_candidates.hierarchy_json.id",
            values=hard_filter.industry_esco_ids_high,
            milvus_parts=milvus_parts,
            mongo_clauses=mongo_clauses,
        )

        if hard_filter.experience.min_months is not None:
            milvus_parts.append(f"experience_months_total >= {hard_filter.experience.min_months}")
        if hard_filter.experience.max_months is not None:
            milvus_parts.append(f"experience_months_total <= {hard_filter.experience.max_months}")

        if hard_filter.education.min_rank is not None:
            milvus_parts.append(f"highest_education_level_rank >= {hard_filter.education.min_rank}")
        if hard_filter.education.max_rank is not None:
            milvus_parts.append(f"highest_education_level_rank <= {hard_filter.education.max_rank}")
        # NOTE:
        # - For current serving schema, experience/education scalar fields are available in Milvus.
        # - The Mongo keyword source (`normalized_candidates`) does not store these scalar fields.
        # - Therefore, we apply experience/education hard filters only on Milvus side to avoid
        #   keyword path false-zero results caused by missing Mongo fields.

        if hard_filter.locations:
            escaped_locations = ",".join(json.dumps(value) for value in hard_filter.locations)
            milvus_parts.append(f"current_location in [{escaped_locations}]")
            mongo_clauses.append({"current_location": {"$in": list(hard_filter.locations)}})

        milvus_expr = " and ".join(milvus_parts)
        mongo_filter = _merge_mongo_clauses(mongo_clauses)
        return HardFilterCompiled(milvus_expr=milvus_expr, mongo_filter=mongo_filter)

    @staticmethod
    def _append_esco_any(
        *,
        milvus_field: str,
        mongo_field: str,
        values: list[str],
        milvus_parts: list[str],
        mongo_clauses: list[dict[str, object]],
    ) -> None:
        if not values:
            return
        distinct_values = _dedupe(values)
        escaped_json = json.dumps(distinct_values)
        milvus_parts.append(f"json_contains_any({milvus_field}, {escaped_json})")
        mongo_clauses.append({mongo_field: {"$in": distinct_values}})


def _merge_mongo_clauses(clauses: list[dict[str, object]]) -> dict[str, object]:
    if not clauses:
        return {}
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result
