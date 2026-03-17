from __future__ import annotations

from fastapi import HTTPException

from ...domain import EducationFilter, ExperienceFilter, SearchQueryInput
from ..schemas import SearchRequest


def validate_search_request(payload: SearchRequest) -> None:
    if (
        payload.experience_min_months is not None
        and payload.experience_max_months is not None
        and payload.experience_min_months > payload.experience_max_months
    ):
        raise HTTPException(status_code=422, detail="experience_min_months must be <= experience_max_months")
    if (
        payload.education_min_rank is not None
        and payload.education_max_rank is not None
        and payload.education_min_rank > payload.education_max_rank
    ):
        raise HTTPException(status_code=422, detail="education_min_rank must be <= education_max_rank")


def to_search_input(payload: SearchRequest) -> SearchQueryInput:
    return SearchQueryInput(
        query_text=payload.query_text,
        requested_locations=[value.strip() for value in payload.locations if value.strip()],
        requested_skill_terms=[value.strip() for value in payload.skill_terms if value.strip()],
        requested_occupation_terms=[value.strip() for value in payload.occupation_terms if value.strip()],
        requested_industry_terms=[value.strip() for value in payload.industry_terms if value.strip()],
        requested_experience=ExperienceFilter(
            min_months=payload.experience_min_months,
            max_months=payload.experience_max_months,
        ),
        requested_education=EducationFilter(
            min_rank=payload.education_min_rank,
            max_rank=payload.education_max_rank,
        ),
    )

