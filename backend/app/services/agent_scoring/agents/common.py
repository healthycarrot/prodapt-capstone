from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..models import AgentCandidateScore, AgentExecutionResult, CandidateProfile, clamp01, normalize_weights

_EXPERIENCE_RECENCY_BONUS_CAP = 0.20


def profile_to_payload(profile: CandidateProfile, *, include_education: bool = True) -> dict[str, Any]:
    include_resume_fallback = _needs_resume_fallback(profile, include_education=include_education)
    payload: dict[str, Any] = {
        "candidate_id": profile.candidate_id,
        "occupation_labels": profile.occupation_labels[:12],
        "skill_labels": profile.skill_labels[:24],
        "experiences": [_compact_experience(item) for item in profile.experiences[:6]],
        # Include resume text only when structured evidence is sparse.
        "resume_text": (profile.resume_text or "")[:900] if include_resume_fallback else "",
    }
    if include_education:
        payload["educations"] = [_compact_education(item) for item in profile.educations[:4]]
    return payload


def _compact_experience(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": str(item.get("title") or ""),
        "company": str(item.get("company") or ""),
        "start_date": str(item.get("start_date") or ""),
        "end_date": str(item.get("end_date") or ""),
        "is_current": bool(item.get("is_current") or False),
        "duration_months": int(item.get("duration_months") or 0),
        "description_raw": str(item.get("description_raw") or "")[:280],
    }


def _compact_education(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "institution": str(item.get("institution") or ""),
        "degree": str(item.get("degree") or ""),
        "field_of_study": str(item.get("field_of_study") or ""),
        "graduation_year": str(item.get("graduation_year") or ""),
        "start_date": str(item.get("start_date") or ""),
        "end_date": str(item.get("end_date") or ""),
    }


def _needs_resume_fallback(profile: CandidateProfile, *, include_education: bool) -> bool:
    has_skills = any((skill or "").strip() for skill in profile.skill_labels)
    has_experiences = bool(profile.experiences)
    has_education = bool(profile.educations) if include_education else False
    return not (has_skills or has_experiences or has_education)


def recompute_skill_score(
    *,
    match_score: float,
    skill_depth_score: float,
    management_score: float,
    match_weight: float,
    depth_weight: float,
    management_weight: float,
) -> float:
    weights = normalize_weights(
        {
            "match": match_weight,
            "depth": depth_weight,
            "management": management_weight,
        }
    )
    return clamp01(
        (weights.get("match", 0.0) * clamp01(match_score))
        + (weights.get("depth", 0.0) * clamp01(skill_depth_score))
        + (weights.get("management", 0.0) * clamp01(management_score))
    )


def recompute_experience_score(
    *,
    industry_match_score: float,
    experience_level_match_score: float,
    recency_score: float,
    industry_weight: float,
    level_weight: float,
) -> float:
    weights = normalize_weights(
        {
            "industry": industry_weight,
            "level": level_weight,
        }
    )
    base_score = (
        (weights.get("industry", 0.0) * clamp01(industry_match_score))
        + (weights.get("level", 0.0) * clamp01(experience_level_match_score))
    )
    recency_bonus = (1.0 - base_score) * clamp01(recency_score) * _EXPERIENCE_RECENCY_BONUS_CAP
    return clamp01(base_score + recency_bonus)


def recompute_education_score(*, education_match_score: float) -> float:
    return clamp01(education_match_score)


def recompute_career_score(*, vertical_growth_score: float, scope_expansion_score: float) -> float:
    return clamp01((clamp01(vertical_growth_score) + clamp01(scope_expansion_score)) / 2.0)


def recompute_soft_skill_score(
    *,
    communication_score: float,
    teamwork_score: float,
    adaptability_score: float,
) -> float:
    return clamp01(
        (clamp01(communication_score) + clamp01(teamwork_score) + clamp01(adaptability_score)) / 3.0
    )


def default_zero_result(
    *,
    name: str,
    weight: float,
    reason: str,
    candidate_ids: Sequence[str],
) -> AgentExecutionResult:
    scores = {
        candidate_id: AgentCandidateScore(
            candidate_id=candidate_id,
            score=0.0,
            breakdown={},
            reason=reason,
            major_gaps=[],
            details={},
        )
        for candidate_id in candidate_ids
    }
    return AgentExecutionResult(
        name=name,
        weight=weight,
        executed=True,
        succeeded=False,
        reason=reason,
        scores_by_candidate=scores,
        error=reason,
    )


def ensure_candidate_coverage(
    *,
    raw_scores: Mapping[str, AgentCandidateScore],
    candidate_ids: Sequence[str],
    fallback_reason: str,
) -> dict[str, AgentCandidateScore]:
    covered: dict[str, AgentCandidateScore] = {}
    for candidate_id in candidate_ids:
        if candidate_id in raw_scores:
            score = raw_scores[candidate_id]
            covered[candidate_id] = AgentCandidateScore(
                candidate_id=score.candidate_id,
                score=clamp01(score.score),
                breakdown={key: clamp01(float(value)) for key, value in score.breakdown.items()},
                reason=score.reason,
                major_gaps=list(score.major_gaps),
                details=dict(score.details),
            )
            continue
        covered[candidate_id] = AgentCandidateScore(
            candidate_id=candidate_id,
            score=0.0,
            breakdown={},
            reason=fallback_reason,
            major_gaps=[],
            details={},
        )
    return covered
