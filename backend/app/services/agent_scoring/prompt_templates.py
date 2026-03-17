from __future__ import annotations

import json
from typing import Any


QUERY_ANALYSIS_INSTRUCTIONS = """\
You are an orchestration analyst for hiring search.
Decide:
1) whether an education requirement is present in the user query
2) dynamic weights for skill and experience internal breakdowns
Return only the structured schema.

Weight rules:
- keep each group normalized to 1.0
- if not enough signal, use defaults
  - skill: match=0.50 depth=0.25 management=0.25
  - experience: industry=0.50 level=0.50
"""


SKILL_MATCH_INSTRUCTIONS = """\
Score each candidate for skill fit.
Use query requirement and candidate skill/experience/education evidence.

Required behavior:
- score range is 0..1
- support transferable skills when explicit exact match is weak
- infer skill depth and management level from experience context
- internal weighted score = match/depth/management
- if explicit skills are weak in query, infer likely skills from role context
- include short reason and major gaps
- include matched_skills and transferable_skills for explainability
"""


EXPERIENCE_MATCH_INSTRUCTIONS = """\
Score each candidate for experience fit.
Use query requirement and candidate experiences.

Required behavior:
- score range is 0..1
- internal weighted score = industry_match + experience_level_match
- recency should follow linear decay
- when date evidence is missing, do not add recency bonus
- if query lacks clear industry/experience constraints, subjective scoring is allowed
  but must be explicit in reason
- include short reason and major gaps
"""


EDUCATION_MATCH_INSTRUCTIONS = """\
Score each candidate for education fit against query requirements.

Required behavior:
- score range is 0..1
- output education_match_score and final score
- if evidence is sparse, use resume_text context conservatively
- include short reason and major gaps
"""


CAREER_PROGRESSION_INSTRUCTIONS = """\
Score each candidate for absolute career progression quality.
Do not compare with query requirements.

Required behavior:
- score range is 0..1
- split into vertical_growth_score and scope_expansion_score
- combine as 50:50
- include short reason
"""


SOFT_SKILL_INSTRUCTIONS = """\
Score each candidate for absolute soft-skill indicators.
Do not compare with query requirements.

Required behavior:
- score range is 0..1
- split into communication/teamwork/adaptability
- combine as average
- include short reason
"""


def build_query_analysis_input(query_text: str) -> str:
    return json.dumps({"query_text": query_text}, ensure_ascii=False)


def build_skill_input(
    *,
    query_text: str,
    candidates: list[dict[str, Any]],
    match_weight: float,
    depth_weight: float,
    management_weight: float,
) -> str:
    payload = {
        "query_text": query_text,
        "weights": {
            "match_weight": match_weight,
            "skill_depth_weight": depth_weight,
            "management_weight": management_weight,
        },
        "candidates": candidates,
    }
    return json.dumps(payload, ensure_ascii=False)


def build_experience_input(
    *,
    query_text: str,
    candidates: list[dict[str, Any]],
    industry_weight: float,
    level_weight: float,
) -> str:
    payload = {
        "query_text": query_text,
        "weights": {
            "industry_weight": industry_weight,
            "experience_level_weight": level_weight,
        },
        "candidates": candidates,
    }
    return json.dumps(payload, ensure_ascii=False)


def build_education_input(*, query_text: str, candidates: list[dict[str, Any]]) -> str:
    payload = {"query_text": query_text, "candidates": candidates}
    return json.dumps(payload, ensure_ascii=False)


def build_career_input(*, query_text: str, candidates: list[dict[str, Any]]) -> str:
    payload = {"query_text": query_text, "candidates": candidates}
    return json.dumps(payload, ensure_ascii=False)


def build_soft_skill_input(*, query_text: str, candidates: list[dict[str, Any]]) -> str:
    payload = {"query_text": query_text, "candidates": candidates}
    return json.dumps(payload, ensure_ascii=False)

