from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tests.eval_harness import (
    build_retrieve_metric_factories,
    build_retrieve_test_case,
    build_search_metric_factories,
    build_search_test_case,
    create_mongo_repository,
    create_test_client,
    get_eval_harness_settings,
    get_live_eval_skip_reason,
    run_metric,
    select_eval_cases,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export live DeepEval report for /retrieve and /search.")
    parser.add_argument("--json-out", required=True, help="Output path for JSON report.")
    parser.add_argument("--md-out", required=True, help="Output path for Markdown report.")
    parser.add_argument("--case-limit", type=int, default=None, help="Override EVAL_CASE_LIMIT.")
    parser.add_argument("--retrieval-top-k", type=int, default=None, help="Override EVAL_RETRIEVAL_TOPK.")
    parser.add_argument("--search-result-top-n", type=int, default=None, help="Override EVAL_SEARCH_RESULT_TOPN.")
    parser.add_argument("--model", default=None, help="Override EVAL_MODEL.")
    return parser.parse_args()


def _apply_overrides(args: argparse.Namespace) -> None:
    os.environ["RUN_LIVE_EVALS"] = "1"
    if args.case_limit is not None:
        os.environ["EVAL_CASE_LIMIT"] = str(max(1, args.case_limit))
    if args.retrieval_top_k is not None:
        os.environ["EVAL_RETRIEVAL_TOPK"] = str(max(1, args.retrieval_top_k))
    if args.search_result_top_n is not None:
        os.environ["EVAL_SEARCH_RESULT_TOPN"] = str(max(1, args.search_result_top_n))
    if args.model:
        os.environ["EVAL_MODEL"] = args.model.strip()
    get_eval_harness_settings.cache_clear()


def _safe_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _safe_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_json(item) for item in value]
    return value


def _summarize_metric_rows(metric_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for endpoint in ("retrieve", "search"):
        endpoint_rows = [row for row in metric_rows if row["endpoint"] == endpoint]
        endpoint_summary: dict[str, Any] = {}
        for metric in sorted({row["metric"] for row in endpoint_rows}):
            rows = [row for row in endpoint_rows if row["metric"] == metric]
            if not rows:
                continue
            scores = [float(row["score"]) for row in rows]
            sorted_rows = sorted(rows, key=lambda row: (row["score"], row["case"], str(row.get("candidate_id") or "")))
            endpoint_summary[metric] = {
                "count": len(rows),
                "threshold": float(rows[0]["threshold"]),
                "avg": sum(scores) / len(scores),
                "median": statistics.median(scores),
                "min": min(scores),
                "max": max(scores),
                "below_threshold_count": sum(1 for row in rows if not row["success"]),
                "bottom_cases": [
                    {
                        "case": row["case"],
                        "candidate_id": row.get("candidate_id"),
                        "rank": row.get("rank"),
                        "score": row["score"],
                        "reason": row["reason"],
                    }
                    for row in sorted_rows[:3]
                ],
                "top_cases": [
                    {
                        "case": row["case"],
                        "candidate_id": row.get("candidate_id"),
                        "rank": row.get("rank"),
                        "score": row["score"],
                    }
                    for row in sorted_rows[-3:]
                ],
            }
        summary[endpoint] = endpoint_summary
    return summary


def _build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# FR-08 Live Eval Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): {report['generated_at_utc']}")
    lines.append(f"- Model: {report['settings']['model']}")
    lines.append(f"- Case limit: {report['settings']['case_limit']}")
    lines.append(f"- Retrieval top-k: {report['settings']['retrieval_top_k']}")
    lines.append(f"- Search result top-n: {report['settings']['search_result_top_n']}")
    lines.append("")
    lines.append("## Selected Cases")
    for name in report["selected_cases"]:
        lines.append(f"- `{name}`")
    lines.append("")
    lines.append("## Execution Overview")
    lines.append("")
    lines.append("| Case | /retrieve | /search | Notes |")
    lines.append("|---|---:|---:|---|")
    for case in report["case_results"]:
        retrieve = case["retrieve"]
        search = case["search"]
        retrieve_state = f"{retrieve['status_code']} / {retrieve['results_count']} results"
        search_state = f"{search['status_code']} / {search['results_count']} results"
        notes: list[str] = []
        if retrieve.get("error_detail"):
            notes.append(f"retrieve: {retrieve['error_detail']}")
        if search.get("error_detail"):
            notes.append(f"search: {search['error_detail']}")
        if search["results_count"] == 0 and search["status_code"] == 200:
            notes.append("search returned no ranked results")
        lines.append(f"| `{case['name']}` | {retrieve_state} | {search_state} | {'; '.join(notes) or '-'} |")

    for endpoint in ("retrieve", "search"):
        endpoint_summary = report["summary"].get(endpoint, {})
        lines.append("")
        lines.append(f"## {endpoint.title()} Metric Summary")
        lines.append("")
        lines.append("| Metric | Count | Avg | Median | Min | Max | Threshold | Below Threshold |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        for metric_name, metric_summary in endpoint_summary.items():
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{metric_name}`",
                        str(metric_summary["count"]),
                        f"{metric_summary['avg']:.3f}",
                        f"{metric_summary['median']:.3f}",
                        f"{metric_summary['min']:.3f}",
                        f"{metric_summary['max']:.3f}",
                        f"{metric_summary['threshold']:.2f}",
                        str(metric_summary["below_threshold_count"]),
                    ]
                )
                + " |"
            )

        lines.append("")
        lines.append(f"## {endpoint.title()} Lowest Scoring Cases")
        for metric_name, metric_summary in endpoint_summary.items():
            lines.append("")
            lines.append(f"### `{metric_name}`")
            for row in metric_summary["bottom_cases"]:
                target = f"candidate_id={row['candidate_id']}" if row.get("candidate_id") else "aggregate retrieval context"
                lines.append(
                    f"- `{row['case']}` ({target}) score={row['score']:.3f}: {row['reason'] or 'No reason returned.'}"
                )

    return "\n".join(lines) + "\n"


def main() -> int:
    args = _parse_args()
    _apply_overrides(args)

    skip_reason = get_live_eval_skip_reason()
    if skip_reason is not None:
        print(skip_reason, file=sys.stderr)
        return 1

    harness = get_eval_harness_settings()
    client = create_test_client()
    repo = create_mongo_repository()
    cases = select_eval_cases(harness)

    case_results: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []

    for case in cases:
        retrieve_response = client.post("/retrieve", json=case.request)
        retrieve_body: dict[str, Any] = {}
        try:
            retrieve_body = dict(retrieve_response.json())
        except Exception:
            retrieve_body = {}
        retrieve_results = list(retrieve_body.get("results", []))

        retrieve_case_result = {
            "status_code": int(retrieve_response.status_code),
            "retry_required": bool(retrieve_body.get("retry_required", False)) if retrieve_response.status_code == 200 else None,
            "conflict_reason": retrieve_body.get("conflict_reason"),
            "results_count": len(retrieve_results),
            "error_detail": retrieve_body.get("detail"),
        }

        if retrieve_response.status_code == 200 and not retrieve_case_result["retry_required"] and retrieve_results:
            top_k = max(1, min(case.top_k, harness.retrieval_top_k, len(retrieve_results)))
            retrieve_ids = [str(item.get("candidate_id") or "").strip() for item in retrieve_results[:top_k]]
            retrieve_profiles = repo.fetch_candidate_profiles(retrieve_ids)
            retrieve_test_case = build_retrieve_test_case(case, retrieve_results, retrieve_profiles, harness)
            for metric_name, metric_factory in build_retrieve_metric_factories(harness):
                evaluation = run_metric(metric_name, metric_factory(), retrieve_test_case)
                metric_rows.append(
                    {
                        "endpoint": "retrieve",
                        "case": case.name,
                        "candidate_id": None,
                        "rank": None,
                        "metric": metric_name,
                        "score": evaluation.score,
                        "threshold": evaluation.threshold,
                        "success": evaluation.success,
                        "reason": evaluation.reason,
                    }
                )

        search_response = client.post("/search", json=case.request)
        search_body: dict[str, Any] = {}
        try:
            search_body = dict(search_response.json())
        except Exception:
            search_body = {}
        search_results = list(search_body.get("results", []))
        search_case_result = {
            "status_code": int(search_response.status_code),
            "retry_required": bool(search_body.get("retry_required", False)) if search_response.status_code == 200 else None,
            "conflict_reason": search_body.get("conflict_reason"),
            "results_count": len(search_results),
            "error_detail": search_body.get("detail"),
        }

        if search_response.status_code == 200 and not search_case_result["retry_required"] and search_results:
            top_n = max(1, min(case.top_search_results, harness.search_result_top_n, len(search_results)))
            top_results = search_results[:top_n]
            search_ids = [str(item.get("candidate_id") or "").strip() for item in top_results]
            search_profiles = repo.fetch_candidate_profiles(search_ids)
            for rank, row in enumerate(top_results, start=1):
                candidate_id = str(row.get("candidate_id") or "").strip()
                test_case = build_search_test_case(
                    case=case,
                    result_row=row,
                    profile=search_profiles.get(candidate_id, {}),
                    harness=harness,
                )
                for metric_name, metric_factory in build_search_metric_factories(harness):
                    evaluation = run_metric(metric_name, metric_factory(), test_case)
                    metric_rows.append(
                        {
                            "endpoint": "search",
                            "case": case.name,
                            "candidate_id": candidate_id,
                            "rank": rank,
                            "metric": metric_name,
                            "score": evaluation.score,
                            "threshold": evaluation.threshold,
                            "success": evaluation.success,
                            "reason": evaluation.reason,
                        }
                    )

        case_results.append(
            {
                "name": case.name,
                "request": _safe_json(case.request),
                "expected_output": case.expected_output,
                "retrieve": retrieve_case_result,
                "search": search_case_result,
            }
        )

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "settings": {
            "enabled": harness.enabled,
            "enforce_thresholds": harness.enforce_thresholds,
            "model": harness.model,
            "case_limit": harness.case_limit,
            "retrieval_top_k": harness.retrieval_top_k,
            "search_result_top_n": harness.search_result_top_n,
            "resume_max_chars": harness.resume_max_chars,
            "experience_items": harness.experience_items,
            "skill_limit": harness.skill_limit,
            "occupation_limit": harness.occupation_limit,
        },
        "thresholds": {
            "faithfulness": harness.faithfulness_threshold,
            "answer_relevancy": harness.answer_relevancy_threshold,
            "contextual_precision": harness.contextual_precision_threshold,
            "contextual_relevancy": harness.contextual_relevancy_threshold,
            "skill_coverage": harness.skill_coverage_threshold,
            "experience_fit": harness.experience_fit_threshold,
            "bias": harness.bias_threshold,
        },
        "selected_cases": [case.name for case in cases],
        "case_results": case_results,
        "metric_rows": metric_rows,
        "summary": _summarize_metric_rows(metric_rows),
    }

    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(_build_markdown(report), encoding="utf-8")
    print(f"Wrote JSON report to {json_out}")
    print(f"Wrote Markdown report to {md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
