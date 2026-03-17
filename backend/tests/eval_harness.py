from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from deepeval.metrics import (
    AnswerRelevancyMetric,
    BiasMetric,
    ContextualPrecisionMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
    GEval,
)
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from fastapi.testclient import TestClient

from app.core import get_settings
from app.main import app
from app.repositories.mongo_repo import MongoRepository


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "search_eval_cases.json"


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _dedupe_preserve_order(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        value = str(raw).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


@dataclass(frozen=True, slots=True)
class EvalCase:
    name: str
    request: dict[str, Any]
    expected_output: str
    required_skills: tuple[str, ...]
    preferred_skills: tuple[str, ...]
    experience_expectations: tuple[str, ...]
    top_k: int
    top_search_results: int


@dataclass(frozen=True, slots=True)
class EvalHarnessSettings:
    enabled: bool
    enforce_thresholds: bool
    model: str
    case_limit: int
    retrieval_top_k: int
    search_result_top_n: int
    resume_max_chars: int
    experience_items: int
    skill_limit: int
    occupation_limit: int
    faithfulness_threshold: float
    answer_relevancy_threshold: float
    contextual_precision_threshold: float
    contextual_relevancy_threshold: float
    skill_coverage_threshold: float
    experience_fit_threshold: float
    bias_threshold: float


@dataclass(frozen=True, slots=True)
class MetricEvaluation:
    name: str
    score: float
    success: bool
    threshold: float
    reason: str


def _coerce_eval_case(raw: Mapping[str, Any]) -> EvalCase:
    request = dict(raw.get("request") or {})
    if not request:
        raise ValueError("Each eval case must include a non-empty request payload.")

    return EvalCase(
        name=str(raw.get("name") or "").strip(),
        request=request,
        expected_output=str(raw.get("expected_output") or "").strip(),
        required_skills=tuple(_dedupe_preserve_order(list(raw.get("required_skills") or []))),
        preferred_skills=tuple(_dedupe_preserve_order(list(raw.get("preferred_skills") or []))),
        experience_expectations=tuple(_dedupe_preserve_order(list(raw.get("experience_expectations") or []))),
        top_k=max(1, int(raw.get("top_k") or 5)),
        top_search_results=max(1, int(raw.get("top_search_results") or 2)),
    )


@lru_cache(maxsize=1)
def load_eval_cases() -> tuple[EvalCase, ...]:
    rows = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    return tuple(_coerce_eval_case(row) for row in rows)


@lru_cache(maxsize=1)
def get_eval_harness_settings() -> EvalHarnessSettings:
    settings = get_settings()
    default_model = (
        os.getenv("EVAL_MODEL")
        or settings.openai_model_agent_scoring
        or settings.openai_model_query_understanding
        or "gpt-4.1-mini"
    )
    return EvalHarnessSettings(
        enabled=_get_bool("RUN_LIVE_EVALS", False),
        enforce_thresholds=_get_bool("EVAL_ENFORCE_THRESHOLDS", False),
        model=default_model,
        case_limit=max(1, _get_int("EVAL_CASE_LIMIT", 1)),
        retrieval_top_k=max(1, _get_int("EVAL_RETRIEVAL_TOPK", 5)),
        search_result_top_n=max(1, _get_int("EVAL_SEARCH_RESULT_TOPN", 1)),
        resume_max_chars=max(200, _get_int("EVAL_RESUME_MAX_CHARS", 2000)),
        experience_items=max(1, _get_int("EVAL_EXPERIENCE_ITEMS", 4)),
        skill_limit=max(1, _get_int("EVAL_SKILL_LIMIT", 24)),
        occupation_limit=max(1, _get_int("EVAL_OCCUPATION_LIMIT", 12)),
        faithfulness_threshold=_get_float("EVAL_FAITHFULNESS_THRESHOLD", 0.60),
        answer_relevancy_threshold=_get_float("EVAL_ANSWER_RELEVANCY_THRESHOLD", 0.50),
        contextual_precision_threshold=_get_float("EVAL_CONTEXTUAL_PRECISION_THRESHOLD", 0.50),
        contextual_relevancy_threshold=_get_float("EVAL_CONTEXTUAL_RELEVANCY_THRESHOLD", 0.50),
        skill_coverage_threshold=_get_float("EVAL_SKILL_COVERAGE_THRESHOLD", 0.50),
        experience_fit_threshold=_get_float("EVAL_EXPERIENCE_FIT_THRESHOLD", 0.50),
        bias_threshold=_get_float("EVAL_BIAS_THRESHOLD", 0.30),
    )


def get_live_eval_skip_reason() -> str | None:
    settings = get_settings()
    harness = get_eval_harness_settings()
    if not harness.enabled:
        return "Live evals are disabled. Set RUN_LIVE_EVALS=1 to enable."
    if not settings.openai_configured:
        return "OpenAI API key is not configured for DeepEval."
    if not settings.mongo_configured:
        return "MongoDB settings are not configured for candidate evidence lookup."
    if not settings.milvus_configured:
        return "Milvus settings are not configured for live retrieval/search evaluation."
    return None


def create_test_client() -> TestClient:
    return TestClient(app)


def create_mongo_repository() -> MongoRepository:
    return MongoRepository(settings=get_settings())


def select_eval_cases(harness: EvalHarnessSettings | None = None) -> tuple[EvalCase, ...]:
    cfg = harness or get_eval_harness_settings()
    cases = load_eval_cases()
    if cfg.case_limit <= 0 or cfg.case_limit >= len(cases):
        return cases
    return cases[: cfg.case_limit]


def serialize_request(payload: Mapping[str, Any]) -> str:
    lines = [f"query_text: {str(payload.get('query_text') or '').strip()}"]
    for key in (
        "skill_terms",
        "occupation_terms",
        "industry_terms",
        "experience_min_months",
        "experience_max_months",
        "education_min_rank",
        "education_max_rank",
        "locations",
        "limit",
    ):
        value = payload.get(key)
        if value in (None, "", [], {}):
            continue
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    return "\n".join(lines)


def build_candidate_context(profile: Mapping[str, Any], harness: EvalHarnessSettings | None = None) -> list[str]:
    cfg = harness or get_eval_harness_settings()
    chunks: list[str] = []

    occupation_labels = [
        str(value).strip() for value in list(profile.get("occupation_labels") or []) if str(value).strip()
    ]
    if occupation_labels:
        chunks.append("Occupations: " + ", ".join(occupation_labels[: cfg.occupation_limit]))

    skill_labels = [str(value).strip() for value in list(profile.get("skill_labels") or []) if str(value).strip()]
    if skill_labels:
        chunks.append("Skills: " + ", ".join(skill_labels[: cfg.skill_limit]))

    experiences = [
        dict(item)
        for item in list(profile.get("experiences") or [])
        if isinstance(item, Mapping)
    ]
    for exp in experiences[: cfg.experience_items]:
        parts: list[str] = []
        for key in ("title", "company_name", "summary", "description_raw"):
            value = str(exp.get(key) or "").strip()
            if value:
                parts.append(value)
        duration_months = exp.get("duration_months")
        if isinstance(duration_months, (int, float)) and duration_months > 0:
            parts.append(f"duration_months={int(duration_months)}")
        if parts:
            chunks.append("Experience: " + " | ".join(parts)[:900])

    educations = [
        dict(item)
        for item in list(profile.get("educations") or [])
        if isinstance(item, Mapping)
    ]
    for edu in educations[:3]:
        parts = [
            str(edu.get("degree") or "").strip(),
            str(edu.get("field_of_study") or "").strip(),
            str(edu.get("school_name") or "").strip(),
        ]
        parts = [part for part in parts if part]
        if parts:
            chunks.append("Education: " + " | ".join(parts)[:400])

    resume_text = str(profile.get("resume_text") or "").strip()
    if resume_text:
        chunks.append("Resume excerpt: " + resume_text[: cfg.resume_max_chars])

    if not chunks:
        chunks.append("No supporting candidate profile context was available.")
    return chunks


def build_ranked_retrieval_context(
    results: Sequence[Mapping[str, Any]],
    profiles: Mapping[str, Mapping[str, Any]],
    harness: EvalHarnessSettings | None = None,
    *,
    top_k: int,
) -> list[str]:
    cfg = harness or get_eval_harness_settings()
    contexts: list[str] = []
    for index, item in enumerate(list(results)[:top_k], start=1):
        candidate_id = str(item.get("candidate_id") or "").strip()
        if not candidate_id:
            continue
        profile = profiles.get(candidate_id, {})
        score = float(item.get("final_score", 0.0))
        detail = " || ".join(build_candidate_context(profile, cfg))
        contexts.append(f"Rank {index} | candidate_id={candidate_id} | final_score={score:.4f} || {detail}")
    if not contexts:
        contexts.append("No retrieval context was available.")
    return contexts


def build_retrieve_test_case(
    case: EvalCase,
    results: Sequence[Mapping[str, Any]],
    profiles: Mapping[str, Mapping[str, Any]],
    harness: EvalHarnessSettings | None = None,
) -> LLMTestCase:
    cfg = harness or get_eval_harness_settings()
    top_k = max(1, min(case.top_k, cfg.retrieval_top_k))
    return LLMTestCase(
        name=f"retrieve::{case.name}",
        input=serialize_request(case.request),
        expected_output=case.expected_output,
        retrieval_context=build_ranked_retrieval_context(results, profiles, cfg, top_k=top_k),
    )


def build_search_test_case(
    case: EvalCase,
    result_row: Mapping[str, Any],
    profile: Mapping[str, Any],
    harness: EvalHarnessSettings | None = None,
) -> LLMTestCase:
    cfg = harness or get_eval_harness_settings()
    candidate_id = str(result_row.get("candidate_id") or "").strip()
    return LLMTestCase(
        name=f"search::{case.name}::{candidate_id or 'unknown'}",
        input=serialize_request(case.request),
        actual_output=str(result_row.get("recommendation_summary") or "").strip(),
        expected_output=case.expected_output,
        retrieval_context=build_candidate_context(profile, cfg),
    )


def _search_eval_params() -> list[LLMTestCaseParams]:
    return [
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT,
        LLMTestCaseParams.RETRIEVAL_CONTEXT,
    ]


def build_search_metric_factories(
    harness: EvalHarnessSettings | None = None,
) -> tuple[tuple[str, Callable[[], Any]], ...]:
    cfg = harness or get_eval_harness_settings()
    return (
        (
            "faithfulness",
            lambda: FaithfulnessMetric(
                threshold=cfg.faithfulness_threshold,
                model=cfg.model,
                include_reason=True,
                async_mode=False,
                verbose_mode=False,
                penalize_ambiguous_claims=True,
            ),
        ),
        (
            "answer_relevancy",
            lambda: AnswerRelevancyMetric(
                threshold=cfg.answer_relevancy_threshold,
                model=cfg.model,
                include_reason=True,
                async_mode=False,
                verbose_mode=False,
            ),
        ),
        (
            "skill_coverage",
            lambda: GEval(
                name="skill_coverage",
                evaluation_params=_search_eval_params(),
                criteria=(
                    "Evaluate whether the actual_output explains the candidate's skill fit against the search "
                    "requirements in expected_output. Reward explicit mention of must-have skills, credible "
                    "transferable skills grounded in retrieval_context, and honest mention of important gaps. "
                    "Penalize generic praise, missing must-have skills, and unsupported claims."
                ),
                model=cfg.model,
                threshold=cfg.skill_coverage_threshold,
                async_mode=False,
                verbose_mode=False,
            ),
        ),
        (
            "experience_fit",
            lambda: GEval(
                name="experience_fit",
                evaluation_params=_search_eval_params(),
                criteria=(
                    "Evaluate whether the actual_output accurately explains the candidate's experience fit "
                    "relative to expected_output and retrieval_context. Reward correct mention of relevant "
                    "experience, seniority, and recency when supported. Penalize inflated seniority, incorrect "
                    "experience claims, and omission of important mismatches."
                ),
                model=cfg.model,
                threshold=cfg.experience_fit_threshold,
                async_mode=False,
                verbose_mode=False,
            ),
        ),
        (
            "bias",
            lambda: BiasMetric(
                threshold=cfg.bias_threshold,
                model=cfg.model,
                include_reason=True,
                async_mode=False,
                verbose_mode=False,
            ),
        ),
    )


def build_retrieve_metric_factories(
    harness: EvalHarnessSettings | None = None,
) -> tuple[tuple[str, Callable[[], Any]], ...]:
    cfg = harness or get_eval_harness_settings()
    return (
        (
            "contextual_precision",
            lambda: ContextualPrecisionMetric(
                threshold=cfg.contextual_precision_threshold,
                model=cfg.model,
                include_reason=True,
                async_mode=False,
                verbose_mode=False,
            ),
        ),
        (
            "contextual_relevancy",
            lambda: ContextualRelevancyMetric(
                threshold=cfg.contextual_relevancy_threshold,
                model=cfg.model,
                include_reason=True,
                async_mode=False,
                verbose_mode=False,
            ),
        ),
    )


def run_metric(name: str, metric: Any, test_case: LLMTestCase) -> MetricEvaluation:
    metric.measure(
        test_case,
        _show_indicator=False,
        _log_metric_to_confident=False,
    )
    reason = str(getattr(metric, "reason", "") or "").strip()
    return MetricEvaluation(
        name=name,
        score=float(getattr(metric, "score", 0.0) or 0.0),
        success=bool(metric.is_successful()),
        threshold=float(getattr(metric, "threshold", 0.0) or 0.0),
        reason=reason,
    )


def format_metric_failure(
    evaluation: MetricEvaluation,
    *,
    case_name: str,
    candidate_id: str | None = None,
) -> str:
    parts = [f"case={case_name}", f"metric={evaluation.name}", f"score={evaluation.score:.2f}"]
    parts.append(f"threshold={evaluation.threshold:.2f}")
    if candidate_id:
        parts.append(f"candidate_id={candidate_id}")
    if evaluation.reason:
        parts.append(f"reason={evaluation.reason}")
    return " | ".join(parts)
