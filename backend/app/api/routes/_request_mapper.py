from __future__ import annotations

from fastapi import HTTPException

from ...domain import EducationFilter, EscoDomain, ExperienceFilter, SearchQueryInput
from ...services.query_normalizer import EscoLexicalRepo
from ..schemas import SearchRequest


def validate_search_request(payload: SearchRequest, *, lexical_repo: EscoLexicalRepo | None = None) -> None:
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
    if lexical_repo is None:
        return

    invalid_by_field = _collect_invalid_esco_terms(payload, lexical_repo)
    if invalid_by_field:
        field_messages = [f"{field}={values}" for field, values in invalid_by_field.items()]
        raise HTTPException(status_code=422, detail=f"invalid ESCO labels: {'; '.join(field_messages)}")


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


def _collect_invalid_esco_terms(payload: SearchRequest, lexical_repo: EscoLexicalRepo) -> dict[str, list[str]]:
    invalid: dict[str, list[str]] = {}
    for field_name, domain, values in (
        ("skill_terms", "skill", payload.skill_terms),
        ("occupation_terms", "occupation", payload.occupation_terms),
        ("industry_terms", "industry", payload.industry_terms),
    ):
        invalid_values = _invalid_terms_for_domain(values, domain, lexical_repo)
        if invalid_values:
            invalid[field_name] = invalid_values
    return invalid


def _invalid_terms_for_domain(values: list[str], domain: EscoDomain, lexical_repo: EscoLexicalRepo) -> list[str]:
    invalid: list[str] = []
    seen: set[str] = set()
    for value in values:
        trimmed = value.strip()
        key = trimmed.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        has_exact = bool(lexical_repo.find_exact(domain, trimmed, limit=1))
        has_alt = bool(lexical_repo.find_alt(domain, trimmed, limit=1))
        if has_exact or has_alt:
            continue
        invalid.append(trimmed)
    return invalid
