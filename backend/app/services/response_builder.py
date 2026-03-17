from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..domain import ConflictCheckResult, RerankHit, RetrievalPipelineOutput


@dataclass(slots=True)
class ResponseBuilderService:
    def build(self, conflict: ConflictCheckResult, reranked_hits: Sequence[RerankHit]) -> RetrievalPipelineOutput:
        if conflict.retry_required:
            return RetrievalPipelineOutput(
                retry_required=True,
                conflict_fields=list(conflict.conflict_fields),
                conflict_reason=conflict.conflict_reason,
                results=[],
            )

        return RetrievalPipelineOutput(
            retry_required=False,
            conflict_fields=list(conflict.conflict_fields),
            conflict_reason=conflict.conflict_reason,
            results=list(reranked_hits),
        )
