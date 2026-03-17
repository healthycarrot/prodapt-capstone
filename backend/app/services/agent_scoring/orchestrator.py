from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from .agents import (
    CareerProgressionAgentService,
    EducationMatchAgentService,
    ExperienceMatchAgentService,
    SkillMatchAgentService,
    SoftSkillMatchAgentService,
)
from .models import (
    AgentCandidateScore,
    AggregatedCandidateScore,
    AgentExecutionResult,
    CandidateProfile,
    Fr04AgentWeights,
    OrchestratorOutput,
    QueryAnalysisOutput,
    normalize_weights,
)
from .error_utils import format_exception
from .prompt_templates import QUERY_ANALYSIS_INSTRUCTIONS, build_query_analysis_input
from .runtime import AgentRuntime

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class OrchestratorAgentService:
    runtime: AgentRuntime
    max_parallel: int = 4
    orchestrator_timeout_sec: float = 45.0
    default_agent_weights: Fr04AgentWeights = field(default_factory=Fr04AgentWeights)
    _skill_agent: SkillMatchAgentService = field(init=False, repr=False)
    _experience_agent: ExperienceMatchAgentService = field(init=False, repr=False)
    _education_agent: EducationMatchAgentService = field(init=False, repr=False)
    _career_agent: CareerProgressionAgentService = field(init=False, repr=False)
    _soft_skill_agent: SoftSkillMatchAgentService = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._skill_agent = SkillMatchAgentService(runtime=self.runtime)
        self._experience_agent = ExperienceMatchAgentService(runtime=self.runtime)
        self._education_agent = EducationMatchAgentService(runtime=self.runtime)
        self._career_agent = CareerProgressionAgentService(runtime=self.runtime)
        self._soft_skill_agent = SoftSkillMatchAgentService(runtime=self.runtime)

    async def run(
        self,
        *,
        query_text: str,
        profiles: Mapping[str, CandidateProfile],
        candidate_ids: Sequence[str],
    ) -> OrchestratorOutput:
        ordered_ids = list(dict.fromkeys(candidate_ids))
        query_analysis = await self._analyze_query(query_text)
        agent_weights = normalize_weights(self.default_agent_weights.to_dict())

        if not ordered_ids:
            return OrchestratorOutput(
                query_analysis=query_analysis,
                agent_results={},
                candidate_scores={},
                any_agent_succeeded=False,
            )

        coroutines: dict[str, object] = {}
        coroutines["skill_match"] = self._skill_agent.evaluate(
            query_text=query_text,
            profiles=profiles,
            candidate_ids=ordered_ids,
            weight=agent_weights.get("skill_match", 0.0),
            match_weight=query_analysis.skill_weight_match,
            depth_weight=query_analysis.skill_weight_depth,
            management_weight=query_analysis.skill_weight_management,
        )
        coroutines["experience_match"] = self._experience_agent.evaluate(
            query_text=query_text,
            profiles=profiles,
            candidate_ids=ordered_ids,
            weight=agent_weights.get("experience_match", 0.0),
            industry_weight=query_analysis.experience_weight_industry,
            level_weight=query_analysis.experience_weight_level,
        )
        coroutines["career_progression"] = self._career_agent.evaluate(
            query_text=query_text,
            profiles=profiles,
            candidate_ids=ordered_ids,
            weight=agent_weights.get("career_progression", 0.0),
        )
        coroutines["soft_skill"] = self._soft_skill_agent.evaluate(
            query_text=query_text,
            profiles=profiles,
            candidate_ids=ordered_ids,
            weight=agent_weights.get("soft_skill", 0.0),
        )
        if query_analysis.run_education_agent:
            coroutines["education_match"] = self._education_agent.evaluate(
                query_text=query_text,
                profiles=profiles,
                candidate_ids=ordered_ids,
                weight=agent_weights.get("education_match", 0.0),
            )

        agent_results = await self._execute_in_parallel(
            coroutines=coroutines,
            agent_weights=agent_weights,
        )
        if not query_analysis.run_education_agent:
            agent_results["education_match"] = AgentExecutionResult(
                name="education_match",
                weight=agent_weights.get("education_match", 0.0),
                executed=False,
                succeeded=False,
                reason="education requirement not detected by orchestrator",
                scores_by_candidate={},
            )

        candidate_scores: dict[str, AggregatedCandidateScore] = {}
        any_agent_succeeded = any(result.succeeded for result in agent_results.values())
        for candidate_id in ordered_ids:
            available_weights: dict[str, float] = {}
            available_scores: dict[str, float] = {}
            agent_scores: dict[str, AgentCandidateScore] = {}
            agent_errors: list[str] = []
            major_gaps: list[str] = []

            for name, result in agent_results.items():
                if not result.executed:
                    continue
                if not result.succeeded:
                    if result.error:
                        agent_errors.append(f"{name}: {result.error}")
                    continue
                score = result.scores_by_candidate.get(candidate_id)
                if score is None:
                    continue
                available_weights[name] = max(0.0, result.weight)
                available_scores[name] = score.score
                agent_scores[name] = score
                major_gaps.extend(score.major_gaps)

            normalized = normalize_weights(available_weights)
            fr04_overall = 0.0
            for name, weight in normalized.items():
                fr04_overall += weight * available_scores.get(name, 0.0)

            dedup_gaps = _dedupe_strings(major_gaps)
            recommendation_summary = _compose_summary(agent_scores)
            if not recommendation_summary:
                recommendation_summary = "FR-04 agent evidence is unavailable. Retrieval score is used as fallback."

            candidate_scores[candidate_id] = AggregatedCandidateScore(
                candidate_id=candidate_id,
                fr04_overall_score=fr04_overall,
                recommendation_summary=recommendation_summary,
                agent_scores=agent_scores,
                major_gaps=dedup_gaps,
                agent_errors=agent_errors,
            )

        return OrchestratorOutput(
            query_analysis=query_analysis,
            agent_results=agent_results,
            candidate_scores=candidate_scores,
            any_agent_succeeded=any_agent_succeeded,
        )

    async def _analyze_query(self, query_text: str) -> QueryAnalysisOutput:
        default = QueryAnalysisOutput()
        try:
            output = await self.runtime.run_structured(
                name="OrchestratorQueryAnalysisAgent",
                instructions=QUERY_ANALYSIS_INSTRUCTIONS,
                input_text=build_query_analysis_input(query_text),
                output_type=QueryAnalysisOutput,
            )
        except Exception as exc:
            logger.exception(
                "Orchestrator query analysis failed. Fallback defaults are used. error=%s",
                format_exception(exc),
            )
            output = default
        return _normalize_query_analysis(output)

    async def _execute_in_parallel(
        self,
        *,
        coroutines,
        agent_weights: Mapping[str, float],
    ) -> dict[str, AgentExecutionResult]:
        semaphore = asyncio.Semaphore(max(1, self.max_parallel))

        async def _guarded(name: str, coro) -> AgentExecutionResult:
            async with semaphore:
                try:
                    return await asyncio.wait_for(coro, timeout=self.orchestrator_timeout_sec)
                except asyncio.TimeoutError:
                    return AgentExecutionResult(
                        name=name,
                        weight=agent_weights.get(name, 0.0),
                        executed=True,
                        succeeded=False,
                        reason=f"{name} timed out",
                        scores_by_candidate={},
                        error="orchestrator timeout",
                    )
                except Exception as exc:
                    return AgentExecutionResult(
                        name=name,
                        weight=agent_weights.get(name, 0.0),
                        executed=True,
                        succeeded=False,
                        reason=f"{name} failed",
                        scores_by_candidate={},
                        error=format_exception(exc),
                    )

        if not coroutines:
            return {}

        collected = await asyncio.gather(
            *[_guarded(name, coro) for name, coro in coroutines.items()],
            return_exceptions=False,
        )
        results = {result.name: result for result in collected}
        return results


def _normalize_query_analysis(output: QueryAnalysisOutput) -> QueryAnalysisOutput:
    skill_weights = normalize_weights(
        {
            "match": output.skill_weight_match,
            "depth": output.skill_weight_depth,
            "management": output.skill_weight_management,
        }
    )
    exp_weights = normalize_weights(
        {
            "industry": output.experience_weight_industry,
            "level": output.experience_weight_level,
        }
    )
    return QueryAnalysisOutput(
        run_education_agent=bool(output.run_education_agent),
        skill_weight_match=skill_weights.get("match", 0.5),
        skill_weight_depth=skill_weights.get("depth", 0.25),
        skill_weight_management=skill_weights.get("management", 0.25),
        experience_weight_industry=exp_weights.get("industry", 0.5),
        experience_weight_level=exp_weights.get("level", 0.5),
        reason=output.reason,
    )


def _compose_summary(agent_scores: Mapping[str, AgentCandidateScore]) -> str:
    ranked = sorted(
        ((name, score) for name, score in agent_scores.items()),
        key=lambda item: -item[1].score,
    )
    segments: list[str] = []
    for name, score in ranked[:2]:
        if score.reason.strip():
            segments.append(f"{name}: {score.reason.strip()}")
    return " | ".join(segments)[:500]


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(value.strip())
    return out
