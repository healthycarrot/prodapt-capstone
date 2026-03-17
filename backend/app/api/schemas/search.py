from __future__ import annotations

from typing import Any

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


class SearchResultItem(BaseModel):
    candidate_id: str
    keyword_score: float
    vector_score: float
    fusion_score: float
    cross_encoder_score: float
    final_score: float


class SearchResponse(BaseModel):
    retry_required: bool
    conflict_fields: list[str]
    conflict_reason: str
    results: list[SearchResultItem] = Field(default_factory=list)
    raw_candidates: list[dict[str, Any]] = Field(default_factory=list)
