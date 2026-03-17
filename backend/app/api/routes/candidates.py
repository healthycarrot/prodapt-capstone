from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from ...core import get_mongo_repository
from ...repositories import MongoRepository
from ..schemas import CandidateDetailResponse, CandidateResumeRawResponse

router = APIRouter(tags=["candidates"])


@router.get("/candidates/{candidate_id}", response_model=CandidateDetailResponse)
def get_candidate_detail(
    candidate_id: UUID,
    repo: MongoRepository = Depends(get_mongo_repository),
) -> CandidateDetailResponse:
    record = repo.fetch_candidate_detail(str(candidate_id))
    if record is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    return CandidateDetailResponse(**record)


@router.get("/candidates/{candidate_id}/resume", response_model=CandidateResumeRawResponse)
def get_candidate_resume_raw(
    candidate_id: UUID,
    repo: MongoRepository = Depends(get_mongo_repository),
) -> CandidateResumeRawResponse:
    record = repo.fetch_candidate_resume_raw(str(candidate_id))
    if record is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    return CandidateResumeRawResponse(**record)
