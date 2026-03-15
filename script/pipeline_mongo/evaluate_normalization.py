from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pymongo import MongoClient


CATEGORY_ALIAS_PHRASES: dict[str, list[str]] = {
    "HR": ["human resources", "personnel", "recruiter", "talent acquisition"],
    "INFORMATION-TECHNOLOGY": ["information technology", "software", "systems", "developer", "it"],
    "AVIATION": ["aviation", "aircraft", "airline", "flight", "pilot", "aerospace"],
    "CONSULTANT": ["consultant", "advisor", "adviser", "analyst", "consulting"],
    "BUSINESS-DEVELOPMENT": ["business development", "sales", "account management"],
    "HEALTHCARE": ["healthcare", "medical", "clinical", "hospital", "nursing"],
    "CONSTRUCTION": ["construction", "civil", "building", "site"],
    "FINANCE": ["finance", "financial", "accounting", "accountant", "audit"],
    "DESIGNER": ["designer", "design", "graphic", "ui", "ux"],
    "SALES": ["sales", "account executive", "business development"],
    "TEACHER": ["teacher", "teaching", "education", "lecturer", "instructor"],
    "CHEF": ["chef", "cook", "culinary", "kitchen"],
    "FITNESS": ["fitness", "trainer", "coach", "wellness", "gym"],
}


DEFAULT_FILL_FIELDS = [
    "category",
    "resume_text",
    "current_location",
    "extraction_confidence",
    "occupation_candidates",
    "skill_candidates",
    "experiences",
    "educations",
    "llm_handoff",
    "matching_debug",
    "candidate_id",
]


GOLD_ID_KEYS = ["source_record_id", "record_id", "id", "source_id"]
GOLD_OCC_KEYS = [
    "occupation_esco_id",
    "occupation_esco_ids",
    "occ_esco_id",
    "occ_esco_ids",
    "occupation_id",
    "occupation_ids",
]
GOLD_SKILL_KEYS = [
    "skill_esco_id",
    "skill_esco_ids",
    "skl_esco_id",
    "skl_esco_ids",
    "skill_id",
    "skill_ids",
]


@dataclass
class TargetMetricsAccumulator:
    docs_total: int = 0
    docs_evaluated: int = 0
    docs_with_results: int = 0
    p1_sum: float = 0.0
    p5_sum: float = 0.0
    mrr_sum: float = 0.0
    map_sum: float = 0.0
    coverage_hits: int = 0

    def to_dict(self, k: int) -> dict[str, Any]:
        denom = self.docs_evaluated if self.docs_evaluated > 0 else 1
        return {
            "docs_total": self.docs_total,
            "docs_evaluated": self.docs_evaluated,
            "docs_with_results": self.docs_with_results,
            "label_coverage_rate": round(self.docs_evaluated / self.docs_total, 4) if self.docs_total else 0.0,
            "p_at_1": round(self.p1_sum / denom, 4),
            "p_at_5": round(self.p5_sum / denom, 4),
            f"mrr_at_{k}": round(self.mrr_sum / denom, 4),
            f"map_at_{k}": round(self.map_sum / denom, 4),
            f"coverage_at_{k}": round(self.coverage_hits / denom, 4),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Issue #13 normalization evaluation runner")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db-name", default="prodapt_capstone")
    parser.add_argument("--collection", default="normalized_candidates")
    parser.add_argument("--source-dataset", default="1st_data")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--mode", choices=["auto", "weak", "gold"], default="auto")
    parser.add_argument("--gold-file", default="")
    parser.add_argument("--weak-coverage-threshold", type=float, default=0.40)
    parser.add_argument("--top-categories", type=int, default=10)
    parser.add_argument(
        "--fill-fields",
        default=",".join(DEFAULT_FILL_FIELDS),
        help="Comma-separated fields for non-null rate calculation.",
    )
    parser.add_argument("--baseline-json", default="")
    parser.add_argument("--output-json", default="script/pipeline_mongo/eval_issue13_report.json")
    parser.add_argument("--output-md", default="docs/Eval-Normalization-Issue13.md")
    return parser.parse_args()


def normalize_spaces(value: str | None) -> str:
    return " ".join((value or "").split())


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def unique_strings(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = normalize_spaces(value)
        key = normalize_text(text)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def category_anchor_phrases(category: str | None) -> list[str]:
    normalized_category = normalize_spaces(category or "")
    upper_category = normalized_category.upper()
    phrases: list[str] = []
    phrases.extend(CATEGORY_ALIAS_PHRASES.get(upper_category, []))
    phrases.extend([tok for tok in normalize_text(normalized_category).split() if len(tok) >= 3])
    return unique_strings(phrases)


def label_matches_category(label: str | None, category: str | None) -> bool:
    label_norm = normalize_text(label)
    if not label_norm:
        return False
    for anchor in category_anchor_phrases(category):
        anchor_norm = normalize_text(anchor)
        if anchor_norm and anchor_norm in label_norm:
            return True
    return False


def parse_multi_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(parse_multi_values(item))
        return out
    if isinstance(value, (set, tuple)):
        out: list[str] = []
        for item in value:
            out.extend(parse_multi_values(item))
        return out
    text = normalize_spaces(str(value))
    if not text:
        return []
    parts = [p.strip() for p in re.split(r"[;,|]", text)]
    vals = [p for p in parts if p]
    return vals if vals else [text]


def _resolve_first_key(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def load_gold_labels(path_str: str) -> dict[str, dict[str, set[str]]]:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"Gold file not found: {path}")

    out: dict[str, dict[str, set[str]]] = {}

    def ensure_row(record_id: str) -> dict[str, set[str]]:
        if record_id not in out:
            out[record_id] = {"occupation": set(), "skill": set()}
        return out[record_id]

    def ingest_row(raw_row: dict[str, Any]) -> None:
        rid_raw = _resolve_first_key(raw_row, GOLD_ID_KEYS)
        if rid_raw is None:
            return
        rid = normalize_spaces(str(rid_raw))
        if not rid:
            return
        row = ensure_row(rid)

        occ_raw = _resolve_first_key(raw_row, GOLD_OCC_KEYS)
        for value in parse_multi_values(occ_raw):
            norm = normalize_spaces(value)
            if norm:
                row["occupation"].add(norm)

        skill_raw = _resolve_first_key(raw_row, GOLD_SKILL_KEYS)
        for value in parse_multi_values(skill_raw):
            norm = normalize_spaces(value)
            if norm:
                row["skill"].add(norm)

    if path.suffix.lower() in {".json", ".jsonl"}:
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".jsonl":
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if isinstance(row, dict):
                    ingest_row(row)
        else:
            data = json.loads(text)
            if isinstance(data, dict):
                # {"<source_record_id>": {"occupation_esco_ids":[...], ...}}
                for key, val in data.items():
                    if not isinstance(val, dict):
                        continue
                    merged = dict(val)
                    merged["source_record_id"] = key
                    ingest_row(merged)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        ingest_row(item)
    else:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ingest_row(dict(row))

    return out


def resolve_mode(mode: str, gold_file: str) -> str:
    if mode == "auto":
        return "gold" if gold_file else "weak"
    return mode


def get_candidates(doc: dict[str, Any], target: str) -> list[dict[str, Any]]:
    key = "occupation_candidates" if target == "occupation" else "skill_candidates"
    rows = doc.get(key)
    if not isinstance(rows, list):
        return []
    out = [r for r in rows if isinstance(r, dict)]
    return out


def is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def average_precision_at_k(rels: list[int], total_relevant: int, k: int) -> float:
    if total_relevant <= 0:
        return 0.0
    hits = 0
    sum_precision = 0.0
    for idx, rel in enumerate(rels[:k], start=1):
        if rel:
            hits += 1
            sum_precision += hits / float(idx)
    denom = min(total_relevant, k)
    if denom <= 0:
        return 0.0
    return sum_precision / float(denom)


def evaluate_target_metrics(
    docs: list[dict[str, Any]],
    target: str,
    mode: str,
    gold_labels: dict[str, dict[str, set[str]]],
    k: int,
) -> dict[str, Any]:
    acc = TargetMetricsAccumulator(docs_total=len(docs))
    k5 = 5

    for doc in docs:
        cands = get_candidates(doc, target)
        record_id = normalize_spaces(str(doc.get("source_record_id") or ""))

        if mode == "gold":
            target_gold = gold_labels.get(record_id, {}).get(target, set())
            if not target_gold:
                continue
            total_relevant = len(target_gold)

            def is_relevant(row: dict[str, Any]) -> bool:
                return normalize_spaces(str(row.get("esco_id") or "")) in target_gold

        else:
            category = normalize_spaces(str(doc.get("category") or ""))

            def is_relevant(row: dict[str, Any]) -> bool:
                return label_matches_category(str(row.get("preferred_label") or ""), category)

            total_relevant = sum(1 for row in cands if is_relevant(row))

        acc.docs_evaluated += 1
        if cands:
            acc.docs_with_results += 1

        topk = cands[:k]
        rels = [1 if is_relevant(row) else 0 for row in topk]

        p1 = rels[0] if rels else 0
        p5 = sum(rels[:k5]) / float(k5)
        rr = 0.0
        for idx, rel in enumerate(rels, start=1):
            if rel:
                rr = 1.0 / float(idx)
                break
        ap = average_precision_at_k(rels, total_relevant, k)
        cov = 1 if any(rels) else 0

        acc.p1_sum += p1
        acc.p5_sum += p5
        acc.mrr_sum += rr
        acc.map_sum += ap
        acc.coverage_hits += cov

    return acc.to_dict(k)


def evaluate_rankings(
    docs: list[dict[str, Any]],
    mode: str,
    gold_labels: dict[str, dict[str, set[str]]],
    k: int,
) -> dict[str, Any]:
    return {
        "doc_count": len(docs),
        "occupation": evaluate_target_metrics(docs, "occupation", mode, gold_labels, k),
        "skill": evaluate_target_metrics(docs, "skill", mode, gold_labels, k),
    }


def summarize_match_methods(docs: list[dict[str, Any]], target: str) -> dict[str, Any]:
    all_counts: Counter[str] = Counter()
    top1_counts: Counter[str] = Counter()
    docs_with_candidates = 0

    for doc in docs:
        cands = get_candidates(doc, target)
        if cands:
            docs_with_candidates += 1
            top1_counts[str(cands[0].get("match_method") or "unknown")] += 1
        for row in cands:
            all_counts[str(row.get("match_method") or "unknown")] += 1

    top1_rates = {
        key: round(value / docs_with_candidates, 4) if docs_with_candidates else 0.0
        for key, value in sorted(top1_counts.items())
    }
    return {
        "docs_with_candidates": docs_with_candidates,
        "top1_counts": dict(sorted(top1_counts.items())),
        "top1_rates": top1_rates,
        "all_candidate_counts": dict(sorted(all_counts.items())),
    }


def field_fill_rates(docs: list[dict[str, Any]], fields: list[str]) -> dict[str, Any]:
    total = len(docs)
    rates: dict[str, Any] = {}
    for field in fields:
        filled = sum(1 for doc in docs if is_filled(doc.get(field)))
        rate = (filled / total) if total else 0.0
        rates[field] = {
            "filled_docs": filled,
            "total_docs": total,
            "rate": round(rate, 4),
        }
    return rates


def build_diff(current: dict[str, Any], baseline: dict[str, Any], k: int) -> dict[str, Any]:
    metric_keys = ["p_at_1", "p_at_5", f"mrr_at_{k}", f"map_at_{k}", f"coverage_at_{k}"]
    rows: list[dict[str, Any]] = []

    for target in ["occupation", "skill"]:
        cur_target = current.get("rankings", {}).get("overall", {}).get(target, {})
        base_target = baseline.get("rankings", {}).get("overall", {}).get(target, {})
        for metric in metric_keys:
            cur_val = cur_target.get(metric)
            base_val = base_target.get(metric)
            if not isinstance(cur_val, (int, float)) or not isinstance(base_val, (int, float)):
                continue
            delta = cur_val - base_val
            rel_delta = (delta / abs(base_val)) if base_val else None
            rows.append(
                {
                    "scope": target,
                    "metric": metric,
                    "before": round(float(base_val), 6),
                    "after": round(float(cur_val), 6),
                    "delta": round(float(delta), 6),
                    "relative_delta": round(float(rel_delta), 6) if rel_delta is not None else None,
                }
            )

    op_pairs = [
        ("llm_rerank_trigger_rate", "operational.llm_handoff.rerank_trigger_rate"),
        ("llm_extraction_trigger_rate", "operational.llm_handoff.extraction_trigger_rate"),
        ("embedding_b1_top1_rate", "operational.embedding_b1.top1_rate"),
        ("embedding_b1_any_rate", "operational.embedding_b1.any_rate"),
    ]

    def deep_get(row: dict[str, Any], dotted: str) -> Any:
        cur: Any = row
        for key in dotted.split("."):
            if not isinstance(cur, dict):
                return None
            cur = cur.get(key)
        return cur

    for label, path in op_pairs:
        cur_val = deep_get(current, path)
        base_val = deep_get(baseline, path)
        if not isinstance(cur_val, (int, float)) or not isinstance(base_val, (int, float)):
            continue
        delta = cur_val - base_val
        rel_delta = (delta / abs(base_val)) if base_val else None
        rows.append(
            {
                "scope": "operational",
                "metric": label,
                "before": round(float(base_val), 6),
                "after": round(float(cur_val), 6),
                "delta": round(float(delta), 6),
                "relative_delta": round(float(rel_delta), 6) if rel_delta is not None else None,
            }
        )

    return {"k": k, "rows": rows}


def render_markdown(report: dict[str, Any], baseline: dict[str, Any] | None = None) -> str:
    lines: list[str] = []
    lines.append("# Normalization Evaluation Report (Issue #13)")
    lines.append("")
    lines.append(f"- Generated at (UTC): {report.get('generated_at_utc')}")
    lines.append(f"- Mode: {report.get('mode')}")
    lines.append(f"- K: {report.get('k')}")
    lines.append(f"- Collection: {report.get('collection')}")
    lines.append(f"- Docs: {report.get('doc_count')}")
    lines.append("")

    status_counts = report.get("status_counts", {})
    if status_counts:
        lines.append("## Status Distribution")
        for key, val in status_counts.items():
            lines.append(f"- {key}: {val}")
        lines.append("")

    lines.append("## Overall Ranking Metrics")
    lines.append("| target | docs_evaluated | p@1 | p@5 | mrr@k | map@k | coverage@k |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    k = int(report.get("k") or 10)
    for target in ["occupation", "skill"]:
        row = report.get("rankings", {}).get("overall", {}).get(target, {})
        lines.append(
            f"| {target} | {row.get('docs_evaluated', 0)} | "
            f"{row.get('p_at_1', 0):.4f} | {row.get('p_at_5', 0):.4f} | "
            f"{row.get(f'mrr_at_{k}', 0):.4f} | {row.get(f'map_at_{k}', 0):.4f} | "
            f"{row.get(f'coverage_at_{k}', 0):.4f} |"
        )
    lines.append("")

    lines.append("## LLM Cohorts")
    llm = report.get("operational", {}).get("llm_handoff", {})
    lines.append(f"- rerank_trigger_docs: {llm.get('rerank_trigger_docs', 0)} ({llm.get('rerank_trigger_rate', 0):.4f})")
    lines.append(
        f"- extraction_trigger_docs: {llm.get('extraction_trigger_docs', 0)} "
        f"({llm.get('extraction_trigger_rate', 0):.4f})"
    )
    lines.append("")

    emb = report.get("operational", {}).get("embedding_b1", {})
    lines.append("## Embedding B1 Adoption")
    lines.append(f"- top1_docs: {emb.get('top1_docs', 0)} (rate={emb.get('top1_rate', 0):.4f})")
    lines.append(f"- any_docs: {emb.get('any_docs', 0)} (rate={emb.get('any_rate', 0):.4f})")
    lines.append("")

    lines.append("## Top Partial/Failed Categories")
    for row in report.get("category_segments", {}).get("top_partial_failed_categories", []):
        lines.append(f"- {row.get('category')}: {row.get('count')}")
    lines.append("")

    warnings = report.get("warnings", [])
    if warnings:
        lines.append("## Warnings")
        for row in warnings:
            lines.append(f"- {row}")
        lines.append("")

    if baseline and report.get("diff_vs_baseline"):
        lines.append("## A/B Diff (vs baseline)")
        lines.append("| scope | metric | before | after | delta | relative_delta |")
        lines.append("|---|---|---:|---:|---:|---:|")
        for row in report["diff_vs_baseline"].get("rows", []):
            rel = row.get("relative_delta")
            rel_text = f"{rel:.6f}" if isinstance(rel, (float, int)) else "null"
            lines.append(
                f"| {row.get('scope')} | {row.get('metric')} | {row.get('before')} | "
                f"{row.get('after')} | {row.get('delta')} | {rel_text} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    mode = resolve_mode(args.mode, args.gold_file)
    if mode == "gold" and not args.gold_file:
        raise ValueError("mode=gold requires --gold-file")

    fill_fields = [normalize_spaces(v) for v in args.fill_fields.split(",")]
    fill_fields = [v for v in fill_fields if v]

    gold_labels: dict[str, dict[str, set[str]]] = {}
    if mode == "gold":
        gold_labels = load_gold_labels(args.gold_file)

    client = MongoClient(args.mongo_uri)
    col = client[args.db_name][args.collection]

    query: dict[str, Any] = {}
    if args.source_dataset:
        query["source_dataset"] = args.source_dataset

    projection = {
        "_id": 0,
        "candidate_id": 1,
        "source_dataset": 1,
        "source_record_id": 1,
        "category": 1,
        "resume_text": 1,
        "current_location": 1,
        "extraction_confidence": 1,
        "occupation_candidates": 1,
        "skill_candidates": 1,
        "experiences": 1,
        "educations": 1,
        "llm_handoff": 1,
        "matching_debug": 1,
        "normalization_status": 1,
    }
    cursor = col.find(query, projection).sort("source_record_id", 1)
    if args.limit and args.limit > 0:
        cursor = cursor.limit(args.limit)
    docs = list(cursor)

    status_counts = Counter(str(doc.get("normalization_status") or "unknown") for doc in docs)

    key_counts = Counter(
        (
            normalize_spaces(str(doc.get("source_dataset") or "")),
            normalize_spaces(str(doc.get("source_record_id") or "")),
        )
        for doc in docs
    )
    duplicate_source_keys = sum(1 for _, count in key_counts.items() if count > 1)
    missing_candidate_id_docs = sum(1 for doc in docs if not is_filled(doc.get("candidate_id")))

    llm_rerank_docs = sum(1 for doc in docs if bool((doc.get("llm_handoff") or {}).get("rerank_trigger")))
    llm_extraction_docs = sum(1 for doc in docs if bool((doc.get("llm_handoff") or {}).get("extraction_trigger")))

    occ_method_summary = summarize_match_methods(docs, "occupation")
    skill_method_summary = summarize_match_methods(docs, "skill")

    occ_any_embedding_b1 = 0
    occ_top1_embedding_b1 = 0
    for doc in docs:
        occ_rows = get_candidates(doc, "occupation")
        if not occ_rows:
            continue
        if any(str(row.get("match_method") or "") == "embedding_b1" for row in occ_rows):
            occ_any_embedding_b1 += 1
        if str(occ_rows[0].get("match_method") or "") == "embedding_b1":
            occ_top1_embedding_b1 += 1

    rankings_overall = evaluate_rankings(docs, mode, gold_labels, args.k)

    by_status: dict[str, Any] = {}
    for status in sorted(status_counts.keys()):
        subset = [doc for doc in docs if str(doc.get("normalization_status") or "unknown") == status]
        by_status[status] = evaluate_rankings(subset, mode, gold_labels, args.k)

    rerank_true_docs = [doc for doc in docs if bool((doc.get("llm_handoff") or {}).get("rerank_trigger"))]
    rerank_false_docs = [doc for doc in docs if not bool((doc.get("llm_handoff") or {}).get("rerank_trigger"))]
    extraction_true_docs = [doc for doc in docs if bool((doc.get("llm_handoff") or {}).get("extraction_trigger"))]
    extraction_false_docs = [doc for doc in docs if not bool((doc.get("llm_handoff") or {}).get("extraction_trigger"))]
    by_llm_handoff = {
        "rerank_trigger_true": evaluate_rankings(rerank_true_docs, mode, gold_labels, args.k),
        "rerank_trigger_false": evaluate_rankings(rerank_false_docs, mode, gold_labels, args.k),
        "extraction_trigger_true": evaluate_rankings(extraction_true_docs, mode, gold_labels, args.k),
        "extraction_trigger_false": evaluate_rankings(extraction_false_docs, mode, gold_labels, args.k),
    }

    fill_overall = field_fill_rates(docs, fill_fields)
    fill_by_status: dict[str, Any] = {}
    for status in sorted(status_counts.keys()):
        subset = [doc for doc in docs if str(doc.get("normalization_status") or "unknown") == status]
        fill_by_status[status] = field_fill_rates(subset, fill_fields)

    category_counter = Counter(
        normalize_spaces(str(doc.get("category") or "UNKNOWN")) or "UNKNOWN"
        for doc in docs
        if str(doc.get("normalization_status") or "unknown") in {"partial", "failed"}
    )
    top_partial_failed_categories = [
        {"category": key, "count": value}
        for key, value in category_counter.most_common(max(1, args.top_categories))
    ]

    report: dict[str, Any] = {
        "generated_at_utc": datetime.utcnow().isoformat(),
        "mode": mode,
        "k": args.k,
        "mongo_uri": args.mongo_uri,
        "db_name": args.db_name,
        "collection": args.collection,
        "source_dataset": args.source_dataset,
        "limit": args.limit,
        "doc_count": len(docs),
        "status_counts": dict(status_counts),
        "integrity": {
            "duplicate_source_keys": duplicate_source_keys,
            "missing_candidate_id_docs": missing_candidate_id_docs,
        },
        "operational": {
            "llm_handoff": {
                "rerank_trigger_docs": llm_rerank_docs,
                "rerank_trigger_rate": round(llm_rerank_docs / len(docs), 4) if docs else 0.0,
                "extraction_trigger_docs": llm_extraction_docs,
                "extraction_trigger_rate": round(llm_extraction_docs / len(docs), 4) if docs else 0.0,
            },
            "embedding_b1": {
                "top1_docs": occ_top1_embedding_b1,
                "top1_rate": round(occ_top1_embedding_b1 / len(docs), 4) if docs else 0.0,
                "any_docs": occ_any_embedding_b1,
                "any_rate": round(occ_any_embedding_b1 / len(docs), 4) if docs else 0.0,
            },
        },
        "match_method": {
            "occupation": occ_method_summary,
            "skill": skill_method_summary,
        },
        "field_fill_rate": {
            "fields": fill_fields,
            "overall": fill_overall,
            "by_status": fill_by_status,
        },
        "rankings": {
            "overall": rankings_overall,
            "by_status": by_status,
            "by_llm_handoff": by_llm_handoff,
        },
        "category_segments": {
            "top_partial_failed_categories": top_partial_failed_categories,
        },
        "warnings": [],
    }

    cov_key = f"coverage_at_{args.k}"
    if mode == "weak":
        occ_cov = report["rankings"]["overall"]["occupation"].get(cov_key, 0.0)
        skill_cov = report["rankings"]["overall"]["skill"].get(cov_key, 0.0)
        if occ_cov < args.weak_coverage_threshold:
            report["warnings"].append(
                f"weak occupation {cov_key}={occ_cov:.4f} < threshold {args.weak_coverage_threshold:.4f}"
            )
        if skill_cov < args.weak_coverage_threshold:
            report["warnings"].append(
                f"weak skill {cov_key}={skill_cov:.4f} < threshold {args.weak_coverage_threshold:.4f}"
            )

    baseline: dict[str, Any] | None = None
    if args.baseline_json:
        base_path = Path(args.baseline_json)
        if base_path.exists():
            baseline = json.loads(base_path.read_text(encoding="utf-8"))
            report["diff_vs_baseline"] = build_diff(report, baseline, args.k)
        else:
            report["warnings"].append(f"baseline_json not found: {base_path}")

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    out_md = Path(args.output_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_markdown(report, baseline), encoding="utf-8")

    summary = {
        "mode": mode,
        "k": args.k,
        "doc_count": len(docs),
        "output_json": str(out_json),
        "output_md": str(out_md),
        "overall_occupation": report["rankings"]["overall"]["occupation"],
        "overall_skill": report["rankings"]["overall"]["skill"],
        "warnings": report["warnings"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
