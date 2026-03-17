from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...core import get_esco_lexical_repository
from ...repositories import EscoLexicalMongoRepository
from ..schemas import EscoDomainParam, EscoSuggestItem, EscoSuggestResponse

router = APIRouter(prefix="/esco", tags=["esco"])


@router.get("/suggest", response_model=EscoSuggestResponse)
def suggest_esco(
    domain: EscoDomainParam = Query(...),
    q: str = Query(default=""),
    limit: int = Query(default=10, ge=1, le=20),
    repo: EscoLexicalMongoRepository = Depends(get_esco_lexical_repository),
) -> EscoSuggestResponse:
    query = q.strip()
    if len(query) < 2:
        return EscoSuggestResponse(domain=domain, query=query, results=[])

    suggestions = repo.suggest(domain, query, limit=limit)
    return EscoSuggestResponse(
        domain=domain,
        query=query,
        results=[
            EscoSuggestItem(
                esco_id=item.esco_id,
                label=item.label,
            )
            for item in suggestions
        ],
    )
