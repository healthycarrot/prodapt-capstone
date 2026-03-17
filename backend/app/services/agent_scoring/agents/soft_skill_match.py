from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from ..models import (
    AgentCandidateScore,
    AgentExecutionResult,
    CandidateProfile,
    SoftSkillBatchOutput,
)
from ..error_utils import format_exception
from ..prompt_templates import SOFT_SKILL_INSTRUCTIONS, build_soft_skill_input
from ..runtime import AgentRuntime
from .common import (
    default_zero_result,
    ensure_candidate_coverage,
    profile_to_payload,
    recompute_soft_skill_score,
)


@dataclass(slots=True)
class SoftSkillMatchAgentService:
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
                name="soft_skill",
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
                name="soft_skill",
                weight=weight,
                reason="candidate profile is unavailable",
                candidate_ids=candidate_ids,
            )

        try:
            output = await self.runtime.run_structured(
                name="SoftSkillAgent",
                instructions=SOFT_SKILL_INSTRUCTIONS,
                input_text=build_soft_skill_input(query_text=query_text, candidates=candidates),
                output_type=SoftSkillBatchOutput,
            )
        except Exception as exc:
            return default_zero_result(
                name="soft_skill",
                weight=weight,
                reason=f"soft skill agent failed: {format_exception(exc)}",
                candidate_ids=candidate_ids,
            )

        raw_scores: dict[str, AgentCandidateScore] = {}
        for item in output.candidates:
            raw_scores[item.candidate_id] = AgentCandidateScore(
                candidate_id=item.candidate_id,
                score=recompute_soft_skill_score(
                    communication_score=item.communication_score,
                    teamwork_score=item.teamwork_score,
                    adaptability_score=item.adaptability_score,
                ),
                breakdown={
                    "communication_score": item.communication_score,
                    "teamwork_score": item.teamwork_score,
                    "adaptability_score": item.adaptability_score,
                },
                reason=item.reason,
                major_gaps=[],
                details={},
            )

        covered = ensure_candidate_coverage(
            raw_scores=raw_scores,
            candidate_ids=candidate_ids,
            fallback_reason="soft skill agent returned no score for this candidate",
        )
        return AgentExecutionResult(
            name="soft_skill",
            weight=weight,
            executed=True,
            succeeded=True,
            reason="ok",
            scores_by_candidate=covered,
        )
