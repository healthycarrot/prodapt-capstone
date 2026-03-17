from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from ..domain import EducationFilter, ExperienceFilter, QueryUnderstandingOutput, SearchQueryInput

_YEARS_PATTERN = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE)
_MONTHS_PATTERN = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*\+?\s*months?", re.IGNORECASE)
_RANGE_YEARS_PATTERN = re.compile(
    r"(?P<low>\d+(?:\.\d+)?)\s*[-~to]+\s*(?P<high>\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
    re.IGNORECASE,
)
_RANGE_MONTHS_PATTERN = re.compile(
    r"(?P<low>\d+(?:\.\d+)?)\s*[-~to]+\s*(?P<high>\d+(?:\.\d+)?)\s*months?",
    re.IGNORECASE,
)

_EDUCATION_KEYWORDS: tuple[tuple[str, int], ...] = (
    ("doctorate", 5),
    ("phd", 5),
    ("md", 5),
    ("jd", 5),
    ("master", 4),
    ("mba", 4),
    ("bachelor", 3),
    ("associate", 2),
    ("diploma", 2),
    ("certificate", 2),
    ("high school", 1),
    ("secondary", 1),
)


class QueryUnderstandingLLMClient(Protocol):
    """Minimal LLM protocol for few-shot extraction."""

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        ...


@dataclass(slots=True)
class QueryUnderstandingService:
    llm_client: QueryUnderstandingLLMClient | None = None

    def extract(self, search_input: SearchQueryInput) -> QueryUnderstandingOutput:
        llm_output = self._extract_with_llm(search_input.query_text)

        # Query understanding returns extraction-only output.
        # API explicit filters stay in SearchQueryInput and are merged in retrieval pipeline
        # with explicit-priority semantics.
        skill_terms = _dedupe_preserve_order(_read_string_list(llm_output, "skill_terms"))
        occupation_terms = _dedupe_preserve_order(_read_string_list(llm_output, "occupation_terms"))
        industry_terms = _dedupe_preserve_order(_read_string_list(llm_output, "industry_terms"))
        experience = _merge_extracted_experience(
            _parse_experience_from_llm(llm_output),
            _parse_experience_from_text(search_input.query_text),
        )
        education = _merge_extracted_education(
            _parse_education_from_llm(llm_output),
            _parse_education_from_text(search_input.query_text),
        )

        return QueryUnderstandingOutput(
            original_query=search_input.query_text,
            skill_terms=skill_terms,
            occupation_terms=occupation_terms,
            industry_terms=industry_terms,
            experience=experience,
            education=education,
        )

    def _extract_with_llm(self, query_text: str) -> dict[str, Any]:
        if self.llm_client is None:
            return {}

        try:
            return self.llm_client.complete_json(
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=_USER_PROMPT_TEMPLATE.format(query_text=query_text),
                temperature=0.0,
            )
        except Exception:
            return {}


def _merge_extracted_experience(*values: ExperienceFilter) -> ExperienceFilter:
    mins = [v.min_months for v in values if v.min_months is not None]
    maxes = [v.max_months for v in values if v.max_months is not None]
    return ExperienceFilter(
        min_months=max(mins) if mins else None,
        max_months=min(maxes) if maxes else None,
    )


def _merge_extracted_education(*values: EducationFilter) -> EducationFilter:
    mins = [v.min_rank for v in values if v.min_rank is not None]
    maxes = [v.max_rank for v in values if v.max_rank is not None]
    return EducationFilter(
        min_rank=max(mins) if mins else None,
        max_rank=min(maxes) if maxes else None,
    )


def _read_string_list(payload: dict[str, Any], key: str) -> list[str]:
    raw = payload.get(key)
    if not isinstance(raw, list):
        return []
    return [item.strip() for item in raw if isinstance(item, str) and item.strip()]


def _parse_experience_from_llm(payload: dict[str, Any]) -> ExperienceFilter:
    experience = payload.get("experience")
    if not isinstance(experience, dict):
        return ExperienceFilter()
    return ExperienceFilter(
        min_months=_as_int(experience.get("min_months")),
        max_months=_as_int(experience.get("max_months")),
    )


def _parse_experience_from_text(query_text: str) -> ExperienceFilter:
    lowered = query_text.lower()
    years_range = _RANGE_YEARS_PATTERN.search(lowered)
    if years_range:
        return ExperienceFilter(
            min_months=int(float(years_range.group("low")) * 12),
            max_months=int(float(years_range.group("high")) * 12),
        )

    months_range = _RANGE_MONTHS_PATTERN.search(lowered)
    if months_range:
        return ExperienceFilter(
            min_months=int(float(months_range.group("low"))),
            max_months=int(float(months_range.group("high"))),
        )

    years_match = _YEARS_PATTERN.search(lowered)
    if years_match:
        months = int(float(years_match.group("num")) * 12)
        return ExperienceFilter(min_months=months)

    months_match = _MONTHS_PATTERN.search(lowered)
    if months_match:
        months = int(float(months_match.group("num")))
        return ExperienceFilter(min_months=months)

    return ExperienceFilter()


def _parse_education_from_llm(payload: dict[str, Any]) -> EducationFilter:
    education = payload.get("education")
    if not isinstance(education, dict):
        return EducationFilter()
    return EducationFilter(
        min_rank=_as_int(education.get("min_rank")),
        max_rank=_as_int(education.get("max_rank")),
    )


def _parse_education_from_text(query_text: str) -> EducationFilter:
    lowered = query_text.lower()
    for keyword, rank in _EDUCATION_KEYWORDS:
        if keyword in lowered:
            return EducationFilter(min_rank=rank)
    return EducationFilter()


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return int(float(value))
        except ValueError:
            return None
    return None


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value.strip())
    return result


_SYSTEM_PROMPT = """\
You extract structured fields from a hiring query.
Return strict JSON only.
Fields:
- skill_terms: list[str]
- occupation_terms: list[str]
- industry_terms: list[str]
- experience: {min_months: int|null, max_months: int|null}
- education: {min_rank: int|null, max_rank: int|null}
Education rank map: 0 unknown, 1 secondary/high school, 2 associate/diploma/certificate, 3 bachelor, 4 master/MBA, 5 doctorate/PhD/MD/JD.
"""

_USER_PROMPT_TEMPLATE = """\
Extract terms that likely map to ESCO preferred labels.
Return compact JSON only.

Examples:
Input: "Need a backend engineer with Python and FastAPI, 3+ years, bachelor or above."
Output: {{"skill_terms":["Python","FastAPI"],"occupation_terms":["backend engineer"],"industry_terms":[],"experience":{{"min_months":36,"max_months":null}},"education":{{"min_rank":3,"max_rank":null}}}}

Input: "Hiring finance manager in manufacturing, 5-7 years exp, MBA preferred."
Output: {{"skill_terms":[],"occupation_terms":["finance manager"],"industry_terms":["manufacturing"],"experience":{{"min_months":60,"max_months":84}},"education":{{"min_rank":4,"max_rank":null}}}}

Input: "{query_text}"
Output:
"""


def parse_llm_json(content: str) -> dict[str, Any]:
    """Helper for adapter implementations that get raw text from an LLM."""
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return {}
    return {}
