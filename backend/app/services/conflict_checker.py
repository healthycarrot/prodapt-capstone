from __future__ import annotations

from dataclasses import dataclass

from ..domain import ConflictCheckResult, EducationFilter, ExperienceFilter, QueryUnderstandingOutput, SearchQueryInput


@dataclass(slots=True)
class ConflictCheckerService:
    """FR-01-02 conflict checker."""

    def check(self, search_input: SearchQueryInput, understood: QueryUnderstandingOutput) -> ConflictCheckResult:
        conflict_fields: list[str] = []
        reasons: list[str] = []

        if _has_term_conflict(search_input.requested_skill_terms, understood.skill_terms):
            conflict_fields.append("skill_terms")
            reasons.append("requested_skill_terms and extracted skill_terms have no overlap")

        if _has_term_conflict(search_input.requested_occupation_terms, understood.occupation_terms):
            conflict_fields.append("occupation_terms")
            reasons.append("requested_occupation_terms and extracted occupation_terms have no overlap")

        if _has_term_conflict(search_input.requested_industry_terms, understood.industry_terms):
            conflict_fields.append("industry_terms")
            reasons.append("requested_industry_terms and extracted industry_terms have no overlap")

        if _has_range_conflict(search_input.requested_experience, understood.experience, "min_months", "max_months"):
            conflict_fields.append("experience")
            reasons.append("requested_experience and extracted experience ranges do not overlap")

        if _has_range_conflict(search_input.requested_education, understood.education, "min_rank", "max_rank"):
            conflict_fields.append("education")
            reasons.append("requested_education and extracted education ranges do not overlap")

        retry_required = bool(conflict_fields)
        return ConflictCheckResult(
            retry_required=retry_required,
            conflict_fields=conflict_fields,
            conflict_reason="; ".join(reasons) if reasons else "no conflict",
        )


def _has_term_conflict(requested: list[str], extracted: list[str]) -> bool:
    if not requested or not extracted:
        return False
    requested_set = {value.strip().lower() for value in requested if value.strip()}
    extracted_set = {value.strip().lower() for value in extracted if value.strip()}
    if not requested_set or not extracted_set:
        return False
    return requested_set.isdisjoint(extracted_set)


def _has_range_conflict(
    requested: ExperienceFilter | EducationFilter,
    extracted: ExperienceFilter | EducationFilter,
    min_name: str,
    max_name: str,
) -> bool:
    req_min = getattr(requested, min_name)
    req_max = getattr(requested, max_name)
    ext_min = getattr(extracted, min_name)
    ext_max = getattr(extracted, max_name)

    lower = max(value for value in (req_min, ext_min) if value is not None) if (req_min is not None or ext_min is not None) else None
    upper = min(value for value in (req_max, ext_max) if value is not None) if (req_max is not None or ext_max is not None) else None

    if lower is None or upper is None:
        return False
    return lower > upper
