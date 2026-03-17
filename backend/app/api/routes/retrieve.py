from __future__ import annotations

from fastapi import APIRouter, Depends

from ...core import get_esco_lexical_repository, get_retrieval_pipeline_service
from ...repositories import EscoLexicalMongoRepository
from ...services import RetrievalPipelineService
from ..schemas import RetrieveResponse, RetrieveResultItem, SearchRequest
from ._request_mapper import to_search_input, validate_search_request

router = APIRouter(tags=["search"])


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve_candidates(
    payload: SearchRequest,
    pipeline: RetrievalPipelineService = Depends(get_retrieval_pipeline_service),
    lexical_repo: EscoLexicalMongoRepository = Depends(get_esco_lexical_repository),
) -> RetrieveResponse:
    validate_search_request(payload, lexical_repo=lexical_repo)
    search_input = to_search_input(payload)
    output = pipeline.run(search_input, result_limit=payload.limit)
    return RetrieveResponse(
        retry_required=output.retry_required,
        conflict_fields=list(output.conflict_fields),
        conflict_reason=output.conflict_reason,
        results=[
            RetrieveResultItem(
                candidate_id=item.candidate_id,
                keyword_score=item.keyword_score,
                vector_score=item.vector_score,
                fusion_score=item.fusion_score,
                cross_encoder_score=item.cross_encoder_score,
                final_score=item.final_score,
            )
            for item in output.results
        ],
    )
