from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CandidateDetailResponse(BaseModel):
    candidate_id: str
    source_dataset: str
    source_record_id: str
    current_location: str
    category: str
    resume_text: str
    occupation_candidates: list[dict[str, Any]] = Field(default_factory=list)
    skill_candidates: list[dict[str, Any]] = Field(default_factory=list)
    experiences: list[dict[str, Any]] = Field(default_factory=list)
    educations: list[dict[str, Any]] = Field(default_factory=list)


class CandidateResumeRawResponse(BaseModel):
    candidate_id: str
    source_dataset: str
    source_record_id: str
    resume_text: str
