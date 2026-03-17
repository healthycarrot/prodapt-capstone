from __future__ import annotations

from fastapi import APIRouter, Depends

from ...core import get_esco_lexical_repository, get_search_orchestration_service
from ...repositories import EscoLexicalMongoRepository
from ...services import SearchOrchestrationService
from ..schemas import AgentScoreCard, GuardrailWarning, SearchRequest, SearchResponse, SearchResultItem
from ._request_mapper import to_search_input, validate_search_request

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search_candidates(
    payload: SearchRequest,
    service: SearchOrchestrationService = Depends(get_search_orchestration_service),
    lexical_repo: EscoLexicalMongoRepository = Depends(get_esco_lexical_repository),
) -> SearchResponse:
    validate_search_request(payload, lexical_repo=lexical_repo)
    search_input = to_search_input(payload)
    output = service.run(search_input, result_limit=payload.limit)
    return SearchResponse(
        retry_required=output.retry_required,
        conflict_fields=list(output.conflict_fields),
        conflict_reason=output.conflict_reason,
        warnings=[
            GuardrailWarning(
                code=str(item.get("code") or "output_audit_warning"),
                message=str(item.get("message") or ""),
                severity=str(item.get("severity") or "warning"),
                candidate_id=str(item.get("candidate_id")) if item.get("candidate_id") is not None else None,
                field=str(item.get("field")) if item.get("field") is not None else None,
            )
            for item in output.warnings
        ],
        results=[
            SearchResultItem(
                candidate_id=item.candidate_id,
                rank=item.rank,
                keyword_score=item.keyword_score,
                vector_score=item.vector_score,
                fusion_score=item.fusion_score,
                cross_encoder_score=item.cross_encoder_score,
                retrieval_final_score=item.retrieval_final_score,
                fr04_overall_score=item.fr04_overall_score,
                final_score=item.final_score,
                recommendation_summary=item.recommendation_summary,
                skill_matches=list(item.skill_matches),
                transferable_skills=list(item.transferable_skills),
                experience_matches=list(item.experience_matches),
                major_gaps=list(item.major_gaps),
                agent_scores={
                    name: AgentScoreCard(
                        score=float((value.get("score") or 0.0)),
                        breakdown={k: float(v) for k, v in dict(value.get("breakdown") or {}).items()},
                        reason=str(value.get("reason") or ""),
                    )
                    for name, value in item.agent_scores.items()
                },
                agent_errors=list(item.agent_errors),
                warnings=[
                    GuardrailWarning(
                        code=str(warn.get("code") or "output_audit_warning"),
                        message=str(warn.get("message") or ""),
                        severity=str(warn.get("severity") or "warning"),
                        candidate_id=(
                            str(warn.get("candidate_id")) if warn.get("candidate_id") is not None else None
                        ),
                        field=str(warn.get("field")) if warn.get("field") is not None else None,
                    )
                    for warn in item.warnings
                ],
            )
            for item in output.results
        ],
    )
