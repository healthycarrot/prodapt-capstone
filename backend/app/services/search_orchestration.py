from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence
from uuid import uuid4

from ..domain import OutputAuditResult, SearchQueryInput
from .agent_scoring import (
    AgentScoreAggregatorService,
    CandidateProfile,
    IntegratedSearchCandidate,
    OrchestratorAgentService,
    QueryAnalysisOutput,
)
from .output_audit import GuardrailAuditLogRepo, OutputAuditService
from .retrieval_pipeline import RetrievalPipelineService


class CandidateProfileRepo(Protocol):
    def fetch_candidate_profiles(self, candidate_ids: Sequence[str]) -> Mapping[str, dict[str, Any]]:
        ...


@dataclass(slots=True)
class SearchOrchestrationResultItem:
    candidate_id: str
    rank: int
    keyword_score: float
    vector_score: float
    fusion_score: float
    cross_encoder_score: float
    retrieval_final_score: float
    fr04_overall_score: float
    final_score: float
    recommendation_summary: str
    skill_matches: list[str] = field(default_factory=list)
    transferable_skills: list[str] = field(default_factory=list)
    experience_matches: list[str] = field(default_factory=list)
    major_gaps: list[str] = field(default_factory=list)
    agent_scores: dict[str, dict[str, object]] = field(default_factory=dict)
    agent_errors: list[str] = field(default_factory=list)
    warnings: list[dict[str, object]] = field(default_factory=list)


@dataclass(slots=True)
class SearchOrchestrationOutput:
    retry_required: bool
    conflict_fields: list[str]
    conflict_reason: str
    warnings: list[dict[str, object]] = field(default_factory=list)
    results: list[SearchOrchestrationResultItem] = field(default_factory=list)
    query_analysis: QueryAnalysisOutput = field(default_factory=QueryAnalysisOutput)


@dataclass(slots=True)
class SearchOrchestrationService:
    retrieval_pipeline: RetrievalPipelineService
    candidate_profile_repo: CandidateProfileRepo
    orchestrator: OrchestratorAgentService
    aggregator: AgentScoreAggregatorService
    output_audit: OutputAuditService
    audit_log_repo: GuardrailAuditLogRepo | None = None
    candidate_top_n: int = 20

    def run(self, search_input: SearchQueryInput, result_limit: int | None = None) -> SearchOrchestrationOutput:
        retrieval_output = self.retrieval_pipeline.run(search_input, result_limit=result_limit)
        if retrieval_output.retry_required:
            return SearchOrchestrationOutput(
                retry_required=True,
                conflict_fields=list(retrieval_output.conflict_fields),
                conflict_reason=retrieval_output.conflict_reason,
                results=[],
            )
        if not retrieval_output.results:
            return SearchOrchestrationOutput(
                retry_required=False,
                conflict_fields=list(retrieval_output.conflict_fields),
                conflict_reason=retrieval_output.conflict_reason,
                results=[],
            )

        limit = _resolve_limit(result_limit, default_limit=self.candidate_top_n, max_limit=self.candidate_top_n)
        retrieval_hits = list(retrieval_output.results)[:limit]
        candidate_ids = [hit.candidate_id for hit in retrieval_hits]
        raw_profiles = self.candidate_profile_repo.fetch_candidate_profiles(candidate_ids)
        profiles = _coerce_profiles(raw_profiles, candidate_ids)

        orchestrator_output = _run_async(
            self.orchestrator.run(
                query_text=search_input.query_text,
                profiles=profiles,
                candidate_ids=candidate_ids,
            )
        )
        integrated = self.aggregator.aggregate(
            retrieval_hits=retrieval_hits,
            orchestrator_output=orchestrator_output,
        )
        result_rows = [_map_integrated_row(row) for row in integrated[:limit]]
        request_id = uuid4().hex
        audit_result = self.output_audit.audit(
            request_id=request_id,
            candidate_rows=[_to_audit_row(item) for item in result_rows],
        )
        _apply_output_audit(result_rows, audit_result)
        extra_global_warnings: list[dict[str, object]] = []
        if audit_result.logs and self.audit_log_repo is not None:
            try:
                self.audit_log_repo.insert_guardrail_audit_logs(
                    rows=[_log_to_dict(item) for item in audit_result.logs]
                )
            except Exception as exc:
                extra_global_warnings.append(
                    {
                        "code": "output_audit_log_write_failed",
                        "message": "Audit log persistence failed.",
                        "severity": "warning",
                        "candidate_id": None,
                        "field": "audit_logs",
                        "detail": str(exc),
                    }
                )
        return SearchOrchestrationOutput(
            retry_required=False,
            conflict_fields=list(retrieval_output.conflict_fields),
            conflict_reason=retrieval_output.conflict_reason,
            warnings=[_warning_to_dict(item) for item in audit_result.warnings if item.candidate_id is None]
            + extra_global_warnings,
            results=result_rows,
            query_analysis=orchestrator_output.query_analysis,
        )


def _map_integrated_row(row: IntegratedSearchCandidate) -> SearchOrchestrationResultItem:
    skill = row.aggregated.agent_scores.get("skill_match")
    experience = row.aggregated.agent_scores.get("experience_match")
    agent_scores: dict[str, dict[str, object]] = {}
    for name, score in row.aggregated.agent_scores.items():
        agent_scores[name] = {
            "score": score.score,
            "breakdown": dict(score.breakdown),
            "reason": score.reason,
        }
    return SearchOrchestrationResultItem(
        candidate_id=row.candidate_id,
        rank=row.rank,
        keyword_score=row.keyword_score,
        vector_score=row.vector_score,
        fusion_score=row.fusion_score,
        cross_encoder_score=row.cross_encoder_score,
        retrieval_final_score=row.retrieval_final_score,
        fr04_overall_score=row.fr04_overall_score,
        final_score=row.integrated_final_score,
        recommendation_summary=row.recommendation_summary,
        skill_matches=list((skill.details.get("matched_skills") if skill else []) or []),
        transferable_skills=list((skill.details.get("transferable_skills") if skill else []) or []),
        experience_matches=list((experience.details.get("experience_matches") if experience else []) or []),
        major_gaps=list(row.aggregated.major_gaps),
        agent_scores=agent_scores,
        agent_errors=list(row.aggregated.agent_errors),
    )


def _to_audit_row(row: SearchOrchestrationResultItem) -> dict[str, Any]:
    return {
        "candidate_id": row.candidate_id,
        "recommendation_summary": row.recommendation_summary,
        "agent_scores": row.agent_scores,
    }


def _warning_to_dict(item) -> dict[str, object]:
    if isinstance(item, dict):
        return dict(item)
    return {
        "code": item.code,
        "message": item.message,
        "severity": item.severity,
        "candidate_id": item.candidate_id,
        "field": item.field,
    }


def _log_to_dict(item) -> dict[str, object]:
    return {
        "request_id": item.request_id,
        "candidate_id": item.candidate_id,
        "rule_id": item.rule_id,
        "detected_text_hash": item.detected_text_hash,
        "action": item.action,
        "timestamp": item.timestamp_iso,
        "metadata": dict(item.metadata),
    }


def _apply_output_audit(rows: list[SearchOrchestrationResultItem], audit_result: OutputAuditResult) -> None:
    row_map = {row.candidate_id: row for row in rows}
    for target in audit_result.sanitize_targets:
        row = row_map.get(target.candidate_id)
        if row is None:
            continue
        if target.field == "recommendation_summary":
            row.recommendation_summary = target.replacement_text
            continue
        if target.field.startswith("agent_scores.") and target.field.endswith(".reason"):
            agent_name = target.field[len("agent_scores.") : -len(".reason")]
            payload = row.agent_scores.get(agent_name)
            if isinstance(payload, dict):
                payload["reason"] = target.replacement_text

    fallback_ids = set(audit_result.ranking_fallback_candidate_ids)
    for candidate_id in fallback_ids:
        row = row_map.get(candidate_id)
        if row is None:
            continue
        row.fr04_overall_score = 0.0
        row.final_score = row.retrieval_final_score
        if "output_audit_retrieval_fallback_applied" not in row.agent_errors:
            row.agent_errors.append("output_audit_retrieval_fallback_applied")

    warnings_by_candidate: dict[str, list[dict[str, object]]] = {}
    for warning in audit_result.warnings:
        if warning.candidate_id is None:
            continue
        warnings_by_candidate.setdefault(warning.candidate_id, []).append(_warning_to_dict(warning))
    for row in rows:
        row.warnings = warnings_by_candidate.get(row.candidate_id, [])

    if fallback_ids:
        rows.sort(
            key=lambda item: (
                -item.final_score,
                -item.retrieval_final_score,
                -item.cross_encoder_score,
                -item.fusion_score,
                -item.vector_score,
                -item.keyword_score,
                item.candidate_id,
            )
        )
        for index, row in enumerate(rows, start=1):
            row.rank = index


def _resolve_limit(limit: int | None, *, default_limit: int, max_limit: int) -> int:
    if limit is None:
        return max(1, min(default_limit, max_limit))
    return max(1, min(limit, max_limit))


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    # FastAPI async context fallback: run orchestration event loop in a worker thread.
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()


def _coerce_profiles(
    raw_profiles: Mapping[str, dict[str, Any]],
    candidate_ids: Sequence[str],
) -> dict[str, CandidateProfile]:
    profiles: dict[str, CandidateProfile] = {}
    for candidate_id in candidate_ids:
        row = raw_profiles.get(candidate_id, {})
        profiles[candidate_id] = CandidateProfile(
            candidate_id=candidate_id,
            resume_text=str(row.get("resume_text") or ""),
            occupation_labels=[
                str(value).strip()
                for value in list(row.get("occupation_labels") or [])
                if str(value).strip()
            ],
            skill_labels=[
                str(value).strip()
                for value in list(row.get("skill_labels") or [])
                if str(value).strip()
            ],
            experiences=[
                dict(value)
                for value in list(row.get("experiences") or [])
                if isinstance(value, dict)
            ],
            educations=[
                dict(value)
                for value in list(row.get("educations") or [])
                if isinstance(value, dict)
            ],
        )
    return profiles
