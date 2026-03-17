from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...core import get_retrieval_pipeline_service
from ...domain import EducationFilter, ExperienceFilter, SearchQueryInput
from ...services import RetrievalPipelineService
from ..schemas import SearchRequest, SearchResponse, SearchResultItem
from .temp import fetch_normalized_candidates_raw

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search_candidates(
    payload: SearchRequest,
    pipeline: RetrievalPipelineService = Depends(get_retrieval_pipeline_service),
) -> SearchResponse:
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

    search_input = SearchQueryInput(
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

    output = pipeline.run(search_input, result_limit=payload.limit)
    candidate_ids = [item.candidate_id for item in output.results]
    candidate_final_scores = {item.candidate_id: item.final_score for item in output.results}
    raw_candidates = fetch_normalized_candidates_raw(
        candidate_ids,
        candidate_final_scores=candidate_final_scores,
        top_k=5,
    )
    return SearchResponse(
        retry_required=output.retry_required,
        conflict_fields=list(output.conflict_fields),
        conflict_reason=output.conflict_reason,
        results=[
            SearchResultItem(
                candidate_id=item.candidate_id,
                keyword_score=item.keyword_score,
                vector_score=item.vector_score,
                fusion_score=item.fusion_score,
                cross_encoder_score=item.cross_encoder_score,
                final_score=item.final_score,
            )
            for item in output.results
        ],
        raw_candidates=raw_candidates,
    )
