"""
Issue #9 – Runner: Extract fields from all docs and store in MongoDB.

Usage:
    python extract_fields_to_mongo.py [--mongo-uri URI] [--db-name DB]
                                       [--collection COL] [--batch-size N]
                                       [--sample N]
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from pymongo import MongoClient, UpdateOne

from extract_fields import (
    EXTRACTOR_VERSION,
    ExtractedFields,
    compute_fill_rates,
    extract_all_fields,
    fields_to_dict,
)

# ── CLI ──────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Issue #9: Extract deterministic fields and store in MongoDB"
    )
    p.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    p.add_argument("--db-name", default="prodapt_capstone")
    p.add_argument("--collection", default="source_1st_resumes")
    p.add_argument("--batch-size", type=int, default=500)
    p.add_argument("--sample", type=int, default=0,
                   help="Process only N random docs (0=all)")
    p.add_argument(
        "--report-out",
        default=str(Path(__file__).resolve().parent / "extract_fields_report.json"),
    )
    return p.parse_args()


# ── Main ─────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    print(f"Connecting to {args.mongo_uri} / {args.db_name} / {args.collection} ...")
    client: MongoClient = MongoClient(args.mongo_uri)
    db = client[args.db_name]
    coll = db[args.collection]

    # Load documents
    if args.sample > 0:
        pipeline = [{"$sample": {"size": args.sample}}]
        docs = list(coll.aggregate(pipeline))
        print(f"Sampled {len(docs)} documents")
    else:
        docs = list(coll.find())
        print(f"Loaded {len(docs)} documents")

    total = len(docs)

    # Process
    print("Extracting fields ...")
    t0 = time.time()

    operations: list[UpdateOne] = []
    stats: dict[str, int] = {"total": 0, "html": 0, "text": 0, "none": 0, "errors": 0}
    all_fill_rates: list[dict[str, float]] = []
    error_ids: list[str] = []

    for i, doc in enumerate(docs):
        stats["total"] += 1
        try:
            ef = extract_all_fields(doc)
            ef_dict = fields_to_dict(ef)
            fill = compute_fill_rates(ef)
            all_fill_rates.append(fill)

            operations.append(UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {
                    "extracted_fields": ef_dict,
                    "extractor_version": EXTRACTOR_VERSION,
                    "extraction_method": ef.extraction_method,
                    "experience_count": len(ef.experiences),
                    "education_count": len(ef.educations),
                    "skill_count": len(ef.skills),
                }},
            ))
            stats[ef.extraction_method] += 1
        except Exception as e:
            stats["errors"] += 1
            rid = doc.get("source_record_id", "?")
            error_ids.append(str(rid))
            print(f"  ERROR [{rid}]: {e}")
            operations.append(UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {
                    "extracted_fields": None,
                    "extractor_version": EXTRACTOR_VERSION,
                    "extraction_method": "error",
                    "experience_count": 0,
                    "education_count": 0,
                    "skill_count": 0,
                }},
            ))

        if len(operations) >= args.batch_size:
            coll.bulk_write(operations)
            operations.clear()
            pct = (i + 1) / total * 100
            print(f"  [{i+1}/{total}] {pct:.0f}%  "
                  f"html={stats['html']} text={stats['text']} none={stats['none']} "
                  f"err={stats['errors']}")

    if operations:
        coll.bulk_write(operations)

    elapsed = time.time() - t0

    # ── Aggregate fill rates ──────────────────────────────────
    agg_fill: dict[str, dict[str, float]] = {}
    if all_fill_rates:
        all_keys = set()
        for fr in all_fill_rates:
            all_keys.update(fr.keys())

        for key in sorted(all_keys):
            vals = [fr.get(key, 0.0) for fr in all_fill_rates]
            n = len(vals)
            agg_fill[key] = {
                "mean": round(sum(vals) / n, 4),
                "min": round(min(vals), 4),
                "max": round(max(vals), 4),
                "non_zero_count": sum(1 for v in vals if v > 0),
                "non_zero_pct": round(sum(1 for v in vals if v > 0) / n * 100, 1),
            }

    # ── Method distribution from DB ──────────────────────────
    pipeline_method = [
        {"$group": {"_id": "$extraction_method", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    method_dist = list(coll.aggregate(pipeline_method))

    # ── Experience / Education count distributions ────────────
    pipeline_exp = [
        {"$group": {"_id": "$experience_count", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    exp_dist = list(coll.aggregate(pipeline_exp))

    pipeline_edu = [
        {"$group": {"_id": "$education_count", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    edu_dist = list(coll.aggregate(pipeline_edu))

    pipeline_skill_avg = [
        {"$group": {
            "_id": None,
            "avg_skills": {"$avg": "$skill_count"},
            "min_skills": {"$min": "$skill_count"},
            "max_skills": {"$max": "$skill_count"},
        }},
    ]
    skill_agg = list(coll.aggregate(pipeline_skill_avg))

    # ── Sample verification: 50 docs ─────────────────────────
    sample_docs = list(coll.aggregate([
        {"$match": {"extraction_method": "html"}},
        {"$sample": {"size": 50}},
        {"$project": {
            "source_record_id": 1, "category": 1,
            "extraction_method": 1,
            "experience_count": 1, "education_count": 1, "skill_count": 1,
            "extracted_fields.name_title": 1,
            "extracted_fields.current_location": 1,
            "extracted_fields.experiences.title": 1,
            "extracted_fields.experiences.company": 1,
            "extracted_fields.experiences.start_date": 1,
            "extracted_fields.experiences.is_current": 1,
            "extracted_fields.experiences.confidence": 1,
            "extracted_fields.educations.institution": 1,
            "extracted_fields.educations.degree": 1,
            "extracted_fields.educations.field_of_study": 1,
            "extracted_fields.educations.graduation_year": 1,
            "extracted_fields.educations.confidence": 1,
        }},
    ]))

    # Build report
    report: dict[str, Any] = {
        "extractor_version": EXTRACTOR_VERSION,
        "elapsed_seconds": round(elapsed, 2),
        "stats": stats,
        "method_distribution": method_dist,
        "experience_count_distribution": exp_dist,
        "education_count_distribution": edu_dist,
        "skill_aggregates": skill_agg,
        "field_fill_rates": agg_fill,
        "error_ids": error_ids,
        "sample_verification": [
            {
                "source_record_id": d.get("source_record_id"),
                "category": d.get("category"),
                "method": d.get("extraction_method"),
                "exp_count": d.get("experience_count"),
                "edu_count": d.get("education_count"),
                "skill_count": d.get("skill_count"),
                "name_title": (d.get("extracted_fields") or {}).get("name_title"),
                "location": (d.get("extracted_fields") or {}).get("current_location"),
                "first_exp": (
                    (d.get("extracted_fields") or {}).get("experiences", [{}])[0]
                    if (d.get("extracted_fields") or {}).get("experiences")
                    else None
                ),
                "first_edu": (
                    (d.get("extracted_fields") or {}).get("educations", [{}])[0]
                    if (d.get("extracted_fields") or {}).get("educations")
                    else None
                ),
            }
            for d in sample_docs
        ],
    }

    # ── Console output ───────────────────────────────────────
    print(f"\nExtraction complete in {elapsed:.1f}s")
    print(f"  Total:  {stats['total']}")
    print(f"  HTML:   {stats['html']}")
    print(f"  Text:   {stats['text']}")
    print(f"  None:   {stats['none']}")
    print(f"  Errors: {stats['errors']}")

    print("\n" + "=" * 60)
    print("FIELD FILL RATES (across all documents)")
    print("=" * 60)
    for key, vals in sorted(agg_fill.items()):
        print(f"  {key:30s}  mean={vals['mean']:.3f}  "
              f"non-zero={vals['non_zero_pct']:5.1f}%  "
              f"({vals['non_zero_count']}/{stats['total']})")

    print(f"\nExperience count distribution:")
    for item in exp_dist:
        if item["_id"] is not None:
            print(f"  {item['_id']:3d} experiences: {item['count']:>5d} docs")

    print(f"\nEducation count distribution:")
    for item in edu_dist:
        if item["_id"] is not None:
            print(f"  {item['_id']:3d} educations: {item['count']:>5d} docs")

    if skill_agg:
        sa = skill_agg[0]
        print(f"\nSkills: avg={sa.get('avg_skills', 0):.1f}  "
              f"min={sa.get('min_skills', 0)}  max={sa.get('max_skills', 0)}")

    # Show a few samples
    print(f"\n{'='*60}")
    print("SAMPLE VERIFICATION (first 10 of 50)")
    print(f"{'='*60}")
    for s in report["sample_verification"][:10]:
        print(f"\n  ID={s['source_record_id']}  cat={s['category']}  "
              f"exp={s['exp_count']}  edu={s['edu_count']}  "
              f"skills={s['skill_count']}")
        print(f"    title={s['name_title']!r}  loc={s['location']!r}")
        if s.get("first_exp"):
            e = s["first_exp"]
            print(f"    1st_exp: title={e.get('title')!r}  "
                  f"company={e.get('company')!r}  "
                  f"start={e.get('start_date')}  "
                  f"current={e.get('is_current')}")
        if s.get("first_edu"):
            e = s["first_edu"]
            print(f"    1st_edu: inst={e.get('institution')!r}  "
                  f"degree={e.get('degree')!r}  "
                  f"field={e.get('field_of_study')!r}  "
                  f"year={e.get('graduation_year')}")

    print("=" * 60)

    # Write report
    out_path = Path(args.report_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"\nReport written to: {out_path}")


if __name__ == "__main__":
    main()
