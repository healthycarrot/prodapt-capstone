from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from ..models import (
    AgentCandidateScore,
    AgentExecutionResult,
    CandidateProfile,
    CareerBatchOutput,
)
from ..error_utils import format_exception
from ..prompt_templates import CAREER_PROGRESSION_INSTRUCTIONS, build_career_input
from ..runtime import AgentRuntime
from .common import (
    default_zero_result,
    ensure_candidate_coverage,
    profile_to_payload,
    recompute_career_score,
)


@dataclass(slots=True)
class CareerProgressionAgentService:
    runtime: AgentRuntime

    async def evaluate(
        self,
        *,
        query_text: str,
        profiles: Mapping[str, CandidateProfile],
        candidate_ids: Sequence[str],
        weight: float,
    ) -> AgentExecutionResult:
        if not candidate_ids:
            return AgentExecutionResult(
                name="career_progression",
                weight=weight,
                executed=False,
                succeeded=True,
                reason="no candidates",
                scores_by_candidate={},
            )

        candidates = [
            profile_to_payload(profiles[candidate_id], include_education=False)
            for candidate_id in candidate_ids
            if candidate_id in profiles
        ]
        if not candidates:
            return default_zero_result(
                name="career_progression",
                weight=weight,
                reason="candidate profile is unavailable",
                candidate_ids=candidate_ids,
            )

        try:
            output = await self.runtime.run_structured(
                name="CareerProgressionAgent",
                instructions=CAREER_PROGRESSION_INSTRUCTIONS,
                input_text=build_career_input(query_text=query_text, candidates=candidates),
                output_type=CareerBatchOutput,
            )
        except Exception as exc:
            return default_zero_result(
                name="career_progression",
                weight=weight,
                reason=f"career progression agent failed: {format_exception(exc)}",
                candidate_ids=candidate_ids,
            )

        raw_scores: dict[str, AgentCandidateScore] = {}
        for item in output.candidates:
            raw_scores[item.candidate_id] = AgentCandidateScore(
                candidate_id=item.candidate_id,
                score=recompute_career_score(
                    vertical_growth_score=item.vertical_growth_score,
                    scope_expansion_score=item.scope_expansion_score,
                ),
                breakdown={
                    "vertical_growth_score": item.vertical_growth_score,
                    "scope_expansion_score": item.scope_expansion_score,
                },
                reason=item.reason,
                major_gaps=[],
                details={},
            )

        covered = ensure_candidate_coverage(
            raw_scores=raw_scores,
            candidate_ids=candidate_ids,
            fallback_reason="career progression agent returned no score for this candidate",
        )
        return AgentExecutionResult(
            name="career_progression",
            weight=weight,
            executed=True,
            succeeded=True,
            reason="ok",
            scores_by_candidate=covered,
        )
