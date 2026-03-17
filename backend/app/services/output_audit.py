from __future__ import annotations

import hashlib
from datetime import datetime, timezone
import re
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from ..domain import (
    GuardrailAction,
    GuardrailWarning,
    OutputAuditLogEntry,
    OutputAuditResult,
    OutputSanitizeTarget,
)


_DEFAULT_PROHIBITED_TERMS: tuple[str, ...] = (
    "gender",
    "male",
    "female",
    "age",
    "young",
    "old",
    "nationality",
    "citizenship",
    "race",
    "ethnicity",
    "religion",
    "marital status",
    "single",
    "married",
    "性別",
    "男性",
    "女性",
    "年齢",
    "若い",
    "国籍",
    "人種",
    "民族",
    "宗教",
    "婚姻",
)
_SPACE_RE = re.compile(r"\s+")


class GuardrailAuditLogRepo(Protocol):
    """Persistence contract for FR-07-04 review logs."""

    def insert_guardrail_audit_logs(self, rows: Sequence[Mapping[str, Any]]) -> int:
        ...


@dataclass(slots=True)
class OutputAuditService:
    """
    FR-07-04 output audit service contract.
    Step 1 keeps behavior no-op and only fixes I/O surface.
    """

    enabled: bool = True
    safe_summary_template: str = "This recommendation was generated from job-relevant evidence."
    safe_reason_template: str = "Details were sanitized by output guardrail policy."
    prohibited_terms_csv: str = ""
    rule_id: str = "prohibited_attribute_or_proxy"

    def audit(
        self,
        *,
        request_id: str,
        candidate_rows: Sequence[Mapping[str, Any]],
    ) -> OutputAuditResult:
        if not self.enabled:
            return OutputAuditResult()

        warnings: list[GuardrailWarning] = []
        logs: list[OutputAuditLogEntry] = []
        sanitize_targets: list[OutputSanitizeTarget] = []
        fallback_candidate_ids: list[str] = []
        prohibited_terms = _build_prohibited_terms(self.prohibited_terms_csv)

        for row in candidate_rows:
            candidate_id = str(row.get("candidate_id") or "").strip()
            if not candidate_id:
                continue

            summary = str(row.get("recommendation_summary") or "")
            summary_hit = _find_hit(summary, prohibited_terms)
            if summary_hit is not None:
                warnings.append(
                    GuardrailWarning(
                        code="output_audit_explanation_sanitized",
                        message="Recommendation summary was sanitized by output guardrail policy.",
                        candidate_id=candidate_id,
                        field="recommendation_summary",
                    )
                )
                sanitize_targets.append(
                    OutputSanitizeTarget(
                        candidate_id=candidate_id,
                        field="recommendation_summary",
                        replacement_text=self.safe_summary_template,
                    )
                )
                logs.append(
                    _build_log_entry(
                        request_id=request_id,
                        candidate_id=candidate_id,
                        action="sanitize_explanation",
                        rule_id=self.rule_id,
                        raw_text=summary,
                        field="recommendation_summary",
                        matched_term=summary_hit,
                    )
                )

            reason_hits = _collect_reason_hits(row.get("agent_scores"), prohibited_terms)
            if reason_hits:
                fallback_candidate_ids.append(candidate_id)
                warnings.append(
                    GuardrailWarning(
                        code="output_audit_ranking_fallback",
                        message="Ranking rationale was flagged; retrieval ranking fallback was applied.",
                        candidate_id=candidate_id,
                        field="agent_scores",
                    )
                )
                for field_path, reason_text, hit_term in reason_hits:
                    sanitize_targets.append(
                        OutputSanitizeTarget(
                            candidate_id=candidate_id,
                            field=field_path,
                            replacement_text=self.safe_reason_template,
                        )
                    )
                    logs.append(
                        _build_log_entry(
                            request_id=request_id,
                            candidate_id=candidate_id,
                            action="fallback_to_retrieval_ranking",
                            rule_id=self.rule_id,
                            raw_text=reason_text,
                            field=field_path,
                            matched_term=hit_term,
                        )
                    )

        return OutputAuditResult(
            warnings=warnings,
            ranking_fallback_candidate_ids=_dedupe_preserve_order(fallback_candidate_ids),
            sanitize_targets=sanitize_targets,
            logs=logs,
        )


def _build_prohibited_terms(prohibited_terms_csv: str) -> tuple[str, ...]:
    extra = [item.strip().lower() for item in prohibited_terms_csv.split(",") if item.strip()]
    merged = list(_DEFAULT_PROHIBITED_TERMS) + extra
    seen: set[str] = set()
    ordered: list[str] = []
    for term in merged:
        key = term.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return tuple(ordered)


def _find_hit(text: str, prohibited_terms: Sequence[str]) -> str | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None
    for term in prohibited_terms:
        if not term:
            continue
        if _contains_cjk(term):
            if term in normalized:
                return term
            continue
        if re.search(rf"\b{re.escape(term)}\b", normalized):
            return term
    return None


def _collect_reason_hits(
    agent_scores: Any,
    prohibited_terms: Sequence[str],
) -> list[tuple[str, str, str]]:
    if not isinstance(agent_scores, Mapping):
        return []
    hits: list[tuple[str, str, str]] = []
    for agent_name, payload in agent_scores.items():
        if not isinstance(payload, Mapping):
            continue
        reason = str(payload.get("reason") or "")
        hit = _find_hit(reason, prohibited_terms)
        if hit is None:
            continue
        hits.append((f"agent_scores.{agent_name}.reason", reason, hit))
    return hits


def _build_log_entry(
    *,
    request_id: str,
    candidate_id: str,
    action: GuardrailAction,
    rule_id: str,
    raw_text: str,
    field: str,
    matched_term: str,
) -> OutputAuditLogEntry:
    return OutputAuditLogEntry(
        request_id=request_id,
        candidate_id=candidate_id,
        rule_id=rule_id,
        detected_text_hash=_hash_text(raw_text),
        action=action,
        timestamp_iso=datetime.now(timezone.utc).isoformat(),
        metadata={
            "field": field,
            "matched_term": matched_term,
        },
    )


def _hash_text(text: str) -> str:
    value = text.strip().lower().encode("utf-8", errors="ignore")
    return hashlib.sha256(value).hexdigest()


def _normalize_text(text: str) -> str:
    lowered = text.strip().lower()
    if not lowered:
        return ""
    return _SPACE_RE.sub(" ", lowered)


def _contains_cjk(text: str) -> bool:
    return any(
        ("\u3040" <= ch <= "\u30ff") or ("\u3400" <= ch <= "\u9fff")
        for ch in text
    )


def _dedupe_preserve_order(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        key = value.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out
