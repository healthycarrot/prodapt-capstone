from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def normalize_weights(values: dict[str, float]) -> dict[str, float]:
    sanitized = {key: max(0.0, float(value)) for key, value in values.items()}
    total = sum(sanitized.values())
    if total <= 0.0:
        if not sanitized:
            return {}
        uniform = 1.0 / float(len(sanitized))
        return {key: uniform for key in sanitized}
    return {key: value / total for key, value in sanitized.items()}


@dataclass(slots=True)
class CandidateProfile:
    candidate_id: str
    resume_text: str
    occupation_labels: list[str] = field(default_factory=list)
    skill_labels: list[str] = field(default_factory=list)
    experiences: list[dict[str, Any]] = field(default_factory=list)
    educations: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class Fr04AgentWeights:
    skill: float = 0.40
    experience: float = 0.35
    education: float = 0.10
    career_progression: float = 0.075
    soft_skill: float = 0.075

    def to_dict(self) -> dict[str, float]:
        return {
            "skill_match": self.skill,
            "experience_match": self.experience,
            "education_match": self.education,
            "career_progression": self.career_progression,
            "soft_skill": self.soft_skill,
        }


class QueryAnalysisOutput(BaseModel):
    run_education_agent: bool = False
    skill_weight_match: float = Field(default=0.50, ge=0.0, le=1.0)
    skill_weight_depth: float = Field(default=0.25, ge=0.0, le=1.0)
    skill_weight_management: float = Field(default=0.25, ge=0.0, le=1.0)
    experience_weight_industry: float = Field(default=0.50, ge=0.0, le=1.0)
    experience_weight_level: float = Field(default=0.50, ge=0.0, le=1.0)
    reason: str = ""


class SkillCandidateOutput(BaseModel):
    candidate_id: str
    score: float = Field(ge=0.0, le=1.0)
    match_score: float = Field(ge=0.0, le=1.0)
    skill_depth_score: float = Field(ge=0.0, le=1.0)
    management_score: float = Field(ge=0.0, le=1.0)
    reason: str = ""
    matched_skills: list[str] = Field(default_factory=list)
    transferable_skills: list[str] = Field(default_factory=list)
    major_gaps: list[str] = Field(default_factory=list)


class SkillBatchOutput(BaseModel):
    candidates: list[SkillCandidateOutput] = Field(default_factory=list)


class ExperienceCandidateOutput(BaseModel):
    candidate_id: str
    score: float = Field(ge=0.0, le=1.0)
    industry_match_score: float = Field(ge=0.0, le=1.0)
    experience_level_match_score: float = Field(ge=0.0, le=1.0)
    recency_score: float = Field(ge=0.0, le=1.0)
    reason: str = ""
    experience_matches: list[str] = Field(default_factory=list)
    major_gaps: list[str] = Field(default_factory=list)


class ExperienceBatchOutput(BaseModel):
    candidates: list[ExperienceCandidateOutput] = Field(default_factory=list)


class EducationCandidateOutput(BaseModel):
    candidate_id: str
    score: float = Field(ge=0.0, le=1.0)
    education_match_score: float = Field(ge=0.0, le=1.0)
    reason: str = ""
    major_gaps: list[str] = Field(default_factory=list)


class EducationBatchOutput(BaseModel):
    candidates: list[EducationCandidateOutput] = Field(default_factory=list)


class CareerCandidateOutput(BaseModel):
    candidate_id: str
    score: float = Field(ge=0.0, le=1.0)
    vertical_growth_score: float = Field(ge=0.0, le=1.0)
    scope_expansion_score: float = Field(ge=0.0, le=1.0)
    reason: str = ""


class CareerBatchOutput(BaseModel):
    candidates: list[CareerCandidateOutput] = Field(default_factory=list)


class SoftSkillCandidateOutput(BaseModel):
    candidate_id: str
    score: float = Field(ge=0.0, le=1.0)
    communication_score: float = Field(ge=0.0, le=1.0)
    teamwork_score: float = Field(ge=0.0, le=1.0)
    adaptability_score: float = Field(ge=0.0, le=1.0)
    reason: str = ""


class SoftSkillBatchOutput(BaseModel):
    candidates: list[SoftSkillCandidateOutput] = Field(default_factory=list)


@dataclass(slots=True)
class AgentCandidateScore:
    candidate_id: str
    score: float
    breakdown: dict[str, float]
    reason: str
    major_gaps: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentExecutionResult:
    name: str
    weight: float
    executed: bool
    succeeded: bool
    reason: str
    scores_by_candidate: dict[str, AgentCandidateScore] = field(default_factory=dict)
    error: str | None = None


@dataclass(slots=True)
class AggregatedCandidateScore:
    candidate_id: str
    fr04_overall_score: float
    recommendation_summary: str
    agent_scores: dict[str, AgentCandidateScore] = field(default_factory=dict)
    major_gaps: list[str] = field(default_factory=list)
    agent_errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OrchestratorOutput:
    query_analysis: QueryAnalysisOutput
    agent_results: dict[str, AgentExecutionResult]
    candidate_scores: dict[str, AggregatedCandidateScore]
    any_agent_succeeded: bool

