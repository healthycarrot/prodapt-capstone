from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from ..models import (
    AgentCandidateScore,
    AgentExecutionResult,
    CandidateProfile,
    SkillBatchOutput,
)
from ..error_utils import format_exception
from ..prompt_templates import SKILL_MATCH_INSTRUCTIONS, build_skill_input
from ..runtime import AgentRuntime
from .common import (
    default_zero_result,
    ensure_candidate_coverage,
    profile_to_payload,
    recompute_skill_score,
)


@dataclass(slots=True)
class SkillMatchAgentService:
    runtime: AgentRuntime

    async def evaluate(
        self,
        *,
        query_text: str,
        profiles: Mapping[str, CandidateProfile],
        candidate_ids: Sequence[str],
        weight: float,
        match_weight: float,
        depth_weight: float,
        management_weight: float,
    ) -> AgentExecutionResult:
        if not candidate_ids:
            return AgentExecutionResult(
                name="skill_match",
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
                name="skill_match",
                weight=weight,
                reason="candidate profile is unavailable",
                candidate_ids=candidate_ids,
            )

        try:
            output = await self.runtime.run_structured(
                name="SkillMatchAgent",
                instructions=SKILL_MATCH_INSTRUCTIONS,
                input_text=build_skill_input(
                    query_text=query_text,
                    candidates=candidates,
                    match_weight=match_weight,
                    depth_weight=depth_weight,
                    management_weight=management_weight,
                ),
                output_type=SkillBatchOutput,
            )
        except Exception as exc:
            return default_zero_result(
                name="skill_match",
                weight=weight,
                reason=f"skill agent failed: {format_exception(exc)}",
                candidate_ids=candidate_ids,
            )

        raw_scores: dict[str, AgentCandidateScore] = {}
        for item in output.candidates:
            server_score = recompute_skill_score(
                match_score=item.match_score,
                skill_depth_score=item.skill_depth_score,
                management_score=item.management_score,
                match_weight=match_weight,
                depth_weight=depth_weight,
                management_weight=management_weight,
            )
            raw_scores[item.candidate_id] = AgentCandidateScore(
                candidate_id=item.candidate_id,
                score=server_score,
                breakdown={
                    "match_score": item.match_score,
                    "skill_depth_score": item.skill_depth_score,
                    "management_score": item.management_score,
                },
                reason=item.reason,
                major_gaps=list(item.major_gaps),
                details={
                    "matched_skills": list(item.matched_skills),
                    "transferable_skills": list(item.transferable_skills),
                },
            )

        covered = ensure_candidate_coverage(
            raw_scores=raw_scores,
            candidate_ids=candidate_ids,
            fallback_reason="skill agent returned no score for this candidate",
        )
        return AgentExecutionResult(
            name="skill_match",
            weight=weight,
            executed=True,
            succeeded=True,
            reason="ok",
            scores_by_candidate=covered,
        )
