from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from ..models import (
    AgentCandidateScore,
    AgentExecutionResult,
    CandidateProfile,
    ExperienceBatchOutput,
)
from ..error_utils import format_exception
from ..prompt_templates import EXPERIENCE_MATCH_INSTRUCTIONS, build_experience_input
from ..runtime import AgentRuntime
from .common import (
    default_zero_result,
    ensure_candidate_coverage,
    profile_to_payload,
    recompute_experience_score,
)


@dataclass(slots=True)
class ExperienceMatchAgentService:
    runtime: AgentRuntime

    async def evaluate(
        self,
        *,
        query_text: str,
        profiles: Mapping[str, CandidateProfile],
        candidate_ids: Sequence[str],
        weight: float,
        industry_weight: float,
        level_weight: float,
    ) -> AgentExecutionResult:
        if not candidate_ids:
            return AgentExecutionResult(
                name="experience_match",
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
                name="experience_match",
                weight=weight,
                reason="candidate profile is unavailable",
                candidate_ids=candidate_ids,
            )

        try:
            output = await self.runtime.run_structured(
                name="ExperienceMatchAgent",
                instructions=EXPERIENCE_MATCH_INSTRUCTIONS,
                input_text=build_experience_input(
                    query_text=query_text,
                    candidates=candidates,
                    industry_weight=industry_weight,
                    level_weight=level_weight,
                ),
                output_type=ExperienceBatchOutput,
            )
        except Exception as exc:
            return default_zero_result(
                name="experience_match",
                weight=weight,
                reason=f"experience agent failed: {format_exception(exc)}",
                candidate_ids=candidate_ids,
            )

        raw_scores: dict[str, AgentCandidateScore] = {}
        for item in output.candidates:
            server_score = recompute_experience_score(
                industry_match_score=item.industry_match_score,
                experience_level_match_score=item.experience_level_match_score,
                recency_score=item.recency_score,
                industry_weight=industry_weight,
                level_weight=level_weight,
            )
            raw_scores[item.candidate_id] = AgentCandidateScore(
                candidate_id=item.candidate_id,
                score=server_score,
                breakdown={
                    "industry_match_score": item.industry_match_score,
                    "experience_level_match_score": item.experience_level_match_score,
                    "recency_score": item.recency_score,
                },
                reason=item.reason,
                major_gaps=list(item.major_gaps),
                details={
                    "experience_matches": list(item.experience_matches),
                },
            )

        covered = ensure_candidate_coverage(
            raw_scores=raw_scores,
            candidate_ids=candidate_ids,
            fallback_reason="experience agent returned no score for this candidate",
        )
        return AgentExecutionResult(
            name="experience_match",
            weight=weight,
            executed=True,
            succeeded=True,
            reason="ok",
            scores_by_candidate=covered,
        )
