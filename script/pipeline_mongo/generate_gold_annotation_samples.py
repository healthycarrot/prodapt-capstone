from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from pymongo import MongoClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate gold-annotation CSV templates from normalized_candidates."
    )
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db-name", default="prodapt_capstone")
    parser.add_argument("--collection", default="normalized_candidates")
    parser.add_argument("--source-dataset", default="1st_data")
    parser.add_argument("--template-size", type=int, default=50)
    parser.add_argument("--stratified-size", type=int, default=200)
    parser.add_argument("--top-occ", type=int, default=5)
    parser.add_argument("--top-skill", type=int, default=10)
    parser.add_argument("--resume-max-chars", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out-template-csv",
        default="script/pipeline_mongo/gold_annotation_template_50.csv",
    )
    parser.add_argument(
        "--out-stratified-csv",
        default="script/pipeline_mongo/gold_annotation_sample_200_stratified.csv",
    )
    parser.add_argument(
        "--out-summary-json",
        default="script/pipeline_mongo/gold_annotation_sampling_summary.json",
    )
    return parser.parse_args()


def normalize_spaces(value: str | None) -> str:
    return " ".join((value or "").split())


def format_candidate_list(rows: list[dict[str, Any]], top_n: int) -> str:
    out: list[str] = []
    for idx, row in enumerate(rows[:top_n], start=1):
        label = normalize_spaces(str(row.get("preferred_label") or ""))
        esco_id = normalize_spaces(str(row.get("esco_id") or ""))
        method = normalize_spaces(str(row.get("match_method") or ""))
        conf = row.get("confidence")
        if isinstance(conf, (int, float)):
            conf_text = f"{float(conf):.4f}"
        else:
            conf_text = ""
        out.append(f"{idx}:{label} [{esco_id}] ({method},{conf_text})")
    return " || ".join(out)


def doc_to_csv_row(
    doc: dict[str, Any],
    top_occ: int,
    top_skill: int,
    resume_max_chars: int,
) -> dict[str, Any]:
    occupation_candidates = doc.get("occupation_candidates") if isinstance(doc.get("occupation_candidates"), list) else []
    skill_candidates = doc.get("skill_candidates") if isinstance(doc.get("skill_candidates"), list) else []
    resume_excerpt = normalize_spaces(str(doc.get("resume_text") or ""))[:resume_max_chars]

    return {
        "source_record_id": normalize_spaces(str(doc.get("source_record_id") or "")),
        "category": normalize_spaces(str(doc.get("category") or "UNKNOWN")) or "UNKNOWN",
        "normalization_status": normalize_spaces(str(doc.get("normalization_status") or "unknown")) or "unknown",
        "resume_excerpt": resume_excerpt,
        "top_occ_candidates": format_candidate_list(occupation_candidates, top_occ),
        "top_skill_candidates": format_candidate_list(skill_candidates, top_skill),
        # gold annotation targets (fill manually)
        "occupation_esco_id": "",
        "skill_esco_id": "",
        "annotator_notes": "",
    }


def allocate_stratified_quotas(counts: dict[str, int], sample_size: int) -> dict[str, int]:
    if sample_size <= 0 or not counts:
        return {}

    categories = sorted(counts.keys())
    total_docs = sum(counts.values())
    if total_docs <= 0:
        return {}

    min_one = 1 if len(categories) <= sample_size else 0
    quotas: dict[str, int] = {cat: min(min_one, counts[cat]) for cat in categories}
    used = sum(quotas.values())
    remaining = max(0, sample_size - used)
    if remaining == 0:
        return quotas

    fractions: list[tuple[float, str]] = []
    for cat in categories:
        if quotas[cat] >= counts[cat]:
            continue
        share = (counts[cat] / float(total_docs)) * remaining
        base = int(share)
        can_take = counts[cat] - quotas[cat]
        take = min(base, can_take)
        quotas[cat] += take
        frac = share - base
        fractions.append((frac, cat))

    used = sum(quotas.values())
    leftover = max(0, sample_size - used)
    if leftover > 0:
        fractions.sort(key=lambda x: (-x[0], x[1]))
        idx = 0
        while leftover > 0 and fractions:
            _, cat = fractions[idx % len(fractions)]
            if quotas[cat] < counts[cat]:
                quotas[cat] += 1
                leftover -= 1
            idx += 1
            if idx > len(fractions) * 5 and leftover > 0:
                break

    used = sum(quotas.values())
    if used < sample_size:
        needed = sample_size - used
        for cat in sorted(categories, key=lambda c: counts[c] - quotas[c], reverse=True):
            if needed <= 0:
                break
            room = counts[cat] - quotas[cat]
            if room <= 0:
                continue
            take = min(room, needed)
            quotas[cat] += take
            needed -= take

    return quotas


def stratified_sample_docs(docs: list[dict[str, Any]], sample_size: int, seed: int) -> list[dict[str, Any]]:
    if sample_size <= 0 or not docs:
        return []
    sample_size = min(sample_size, len(docs))

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for doc in docs:
        category = normalize_spaces(str(doc.get("category") or "UNKNOWN")) or "UNKNOWN"
        grouped[category].append(doc)

    counts = {cat: len(rows) for cat, rows in grouped.items()}
    quotas = allocate_stratified_quotas(counts, sample_size)
    rng = random.Random(seed)

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    for cat in sorted(grouped.keys()):
        rows = grouped[cat][:]
        rng.shuffle(rows)
        take = min(quotas.get(cat, 0), len(rows))
        for doc in rows[:take]:
            rid = normalize_spaces(str(doc.get("source_record_id") or ""))
            if rid and rid not in selected_ids:
                selected_ids.add(rid)
                selected.append(doc)

    if len(selected) < sample_size:
        remaining_docs = []
        for doc in docs:
            rid = normalize_spaces(str(doc.get("source_record_id") or ""))
            if rid and rid not in selected_ids:
                remaining_docs.append(doc)
        rng.shuffle(remaining_docs)
        selected.extend(remaining_docs[: sample_size - len(selected)])

    selected.sort(key=lambda d: normalize_spaces(str(d.get("source_record_id") or "")))
    return selected[:sample_size]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_record_id",
        "category",
        "normalization_status",
        "resume_excerpt",
        "top_occ_candidates",
        "top_skill_candidates",
        "occupation_esco_id",
        "skill_esco_id",
        "annotator_notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(row.get("normalization_status", "unknown") for row in rows)
    category_counts = Counter(row.get("category", "UNKNOWN") for row in rows)
    return {
        "row_count": len(rows),
        "status_counts": dict(status_counts),
        "top_categories": [
            {"category": cat, "count": cnt}
            for cat, cnt in category_counts.most_common(15)
        ],
    }


def main() -> None:
    args = parse_args()
    client = MongoClient(args.mongo_uri)
    col = client[args.db_name][args.collection]

    query: dict[str, Any] = {}
    if args.source_dataset:
        query["source_dataset"] = args.source_dataset

    projection = {
        "_id": 0,
        "source_record_id": 1,
        "category": 1,
        "normalization_status": 1,
        "resume_text": 1,
        "occupation_candidates": 1,
        "skill_candidates": 1,
    }
    docs = list(col.find(query, projection))
    if not docs:
        raise RuntimeError("No documents found in normalized collection")

    sample_50_docs = stratified_sample_docs(docs, args.template_size, args.seed)
    sample_200_docs = stratified_sample_docs(docs, args.stratified_size, args.seed + 1)

    sample_50_rows = [
        doc_to_csv_row(doc, args.top_occ, args.top_skill, args.resume_max_chars)
        for doc in sample_50_docs
    ]
    sample_200_rows = [
        doc_to_csv_row(doc, args.top_occ, args.top_skill, args.resume_max_chars)
        for doc in sample_200_docs
    ]

    out_template_csv = Path(args.out_template_csv)
    out_stratified_csv = Path(args.out_stratified_csv)
    out_summary_json = Path(args.out_summary_json)

    write_csv(out_template_csv, sample_50_rows)
    write_csv(out_stratified_csv, sample_200_rows)

    summary = {
        "generated_at_utc": datetime.utcnow().isoformat(),
        "mongo": {
            "db_name": args.db_name,
            "collection": args.collection,
            "source_dataset": args.source_dataset,
            "total_docs": len(docs),
        },
        "settings": {
            "template_size": args.template_size,
            "stratified_size": args.stratified_size,
            "seed": args.seed,
            "top_occ": args.top_occ,
            "top_skill": args.top_skill,
            "resume_max_chars": args.resume_max_chars,
        },
        "outputs": {
            "template_csv": str(out_template_csv),
            "stratified_csv": str(out_stratified_csv),
            "summary_json": str(out_summary_json),
        },
        "template_50_summary": summarize_rows(sample_50_rows),
        "stratified_200_summary": summarize_rows(sample_200_rows),
    }

    out_summary_json.parent.mkdir(parents=True, exist_ok=True)
    out_summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
