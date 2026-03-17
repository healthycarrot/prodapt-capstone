from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from ..models import (
    AgentCandidateScore,
    AgentExecutionResult,
    CandidateProfile,
    EducationBatchOutput,
)
from ..error_utils import format_exception
from ..prompt_templates import EDUCATION_MATCH_INSTRUCTIONS, build_education_input
from ..runtime import AgentRuntime
from .common import (
    default_zero_result,
    ensure_candidate_coverage,
    profile_to_payload,
    recompute_education_score,
)


@dataclass(slots=True)
class EducationMatchAgentService:
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
                name="education_match",
                weight=weight,
                executed=False,
                succeeded=True,
                reason="no candidates",
                scores_by_candidate={},
            )

        candidates = [
            profile_to_payload(profiles[candidate_id], include_education=True)
            for candidate_id in candidate_ids
            if candidate_id in profiles
        ]
        if not candidates:
            return default_zero_result(
                name="education_match",
                weight=weight,
                reason="candidate profile is unavailable",
                candidate_ids=candidate_ids,
            )

        try:
            output = await self.runtime.run_structured(
                name="EducationMatchAgent",
                instructions=EDUCATION_MATCH_INSTRUCTIONS,
                input_text=build_education_input(query_text=query_text, candidates=candidates),
                output_type=EducationBatchOutput,
            )
        except Exception as exc:
            return default_zero_result(
                name="education_match",
                weight=weight,
                reason=f"education agent failed: {format_exception(exc)}",
                candidate_ids=candidate_ids,
            )

        raw_scores: dict[str, AgentCandidateScore] = {}
        for item in output.candidates:
            raw_scores[item.candidate_id] = AgentCandidateScore(
                candidate_id=item.candidate_id,
                score=recompute_education_score(education_match_score=item.education_match_score),
                breakdown={
                    "education_match_score": item.education_match_score,
                },
                reason=item.reason,
                major_gaps=list(item.major_gaps),
                details={},
            )

        covered = ensure_candidate_coverage(
            raw_scores=raw_scores,
            candidate_ids=candidate_ids,
            fallback_reason="education agent returned no score for this candidate",
        )
        return AgentExecutionResult(
            name="education_match",
            weight=weight,
            executed=True,
            succeeded=True,
            reason="ok",
            scores_by_candidate=covered,
        )
