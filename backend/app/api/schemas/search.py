from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query_text: str = Field(min_length=1)
    skill_terms: list[str] = Field(default_factory=list)
    occupation_terms: list[str] = Field(default_factory=list)
    industry_terms: list[str] = Field(default_factory=list)
    experience_min_months: int | None = Field(default=None, ge=0)
    experience_max_months: int | None = Field(default=None, ge=0)
    education_min_rank: int | None = Field(default=None, ge=0, le=5)
    education_max_rank: int | None = Field(default=None, ge=0, le=5)
    locations: list[str] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=50)


class RetrieveResultItem(BaseModel):
    candidate_id: str
    keyword_score: float
    vector_score: float
    fusion_score: float
    cross_encoder_score: float
    final_score: float


class RetrieveResponse(BaseModel):
    retry_required: bool
    conflict_fields: list[str]
    conflict_reason: str
    results: list[RetrieveResultItem] = Field(default_factory=list)


class AgentScoreCard(BaseModel):
    score: float
    breakdown: dict[str, float] = Field(default_factory=dict)
    reason: str


class SearchResultItem(BaseModel):
    candidate_id: str
    rank: int
    keyword_score: float
    vector_score: float
    fusion_score: float
    cross_encoder_score: float
    retrieval_final_score: float
    fr04_overall_score: float
    final_score: float
    recommendation_summary: str
    skill_matches: list[str] = Field(default_factory=list)
    transferable_skills: list[str] = Field(default_factory=list)
    experience_matches: list[str] = Field(default_factory=list)
    major_gaps: list[str] = Field(default_factory=list)
    agent_scores: dict[str, AgentScoreCard] = Field(default_factory=dict)
    agent_errors: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    retry_required: bool
    conflict_fields: list[str]
    conflict_reason: str
    results: list[SearchResultItem] = Field(default_factory=list)

