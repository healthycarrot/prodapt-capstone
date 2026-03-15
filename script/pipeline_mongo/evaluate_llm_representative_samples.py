from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from pymongo import MongoClient

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LLM-as-a-Judge evaluation for representative 10 normalized docs."
    )
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db-name", default="prodapt_capstone")
    parser.add_argument("--collection", default="normalized_candidates")
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--sample-size", type=int, default=10)
    parser.add_argument(
        "--out-json",
        default="script/pipeline_mongo/llm_eval_10samples.json",
    )
    parser.add_argument(
        "--out-md",
        default="docs/LLM-Eval-10samples.md",
    )
    return parser.parse_args()


def _pick_diverse(rows: list[dict[str, Any]], k: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen_categories: set[str] = set()

    for row in rows:
        cat = (row.get("category") or "UNKNOWN").strip().upper()
        if cat in seen_categories:
            continue
        out.append(row)
        seen_categories.add(cat)
        if len(out) >= k:
            return out

    for row in rows:
        if row in out:
            continue
        out.append(row)
        if len(out) >= k:
            return out

    return out


def select_representative_docs(
    docs: list[dict[str, Any]],
    sample_size: int,
) -> list[dict[str, Any]]:
    # Expect sample_size=10. If changed, keep proportional fallback.
    # Target buckets: success_high 3, success_mid 2, success_low 2, partial 3
    success = [d for d in docs if d.get("normalization_status") == "success" and d.get("occupation_candidates")]
    partial = [d for d in docs if d.get("normalization_status") == "partial" and d.get("occupation_candidates")]

    def top_conf(d: dict[str, Any]) -> float:
        occ = d.get("occupation_candidates") or []
        return float(occ[0].get("confidence", 0.0)) if occ else 0.0

    success_high = sorted([d for d in success if top_conf(d) >= 0.95], key=top_conf, reverse=True)
    success_mid = sorted([d for d in success if 0.90 <= top_conf(d) < 0.95], key=top_conf, reverse=True)
    success_low = sorted([d for d in success if top_conf(d) < 0.90], key=top_conf)
    partial_any = sorted(partial, key=top_conf)

    if sample_size == 10:
        targets = {
            "success_high": 3,
            "success_mid": 2,
            "success_low": 2,
            "partial_any": 3,
        }
    else:
        # Simple fallback distribution
        targets = {
            "success_high": max(1, round(sample_size * 0.3)),
            "success_mid": max(1, round(sample_size * 0.2)),
            "success_low": max(1, round(sample_size * 0.2)),
            "partial_any": max(1, sample_size - (round(sample_size * 0.3) + round(sample_size * 0.2) + round(sample_size * 0.2))),
        }

    picked: list[dict[str, Any]] = []
    picked.extend(_pick_diverse(success_high, targets["success_high"]))
    picked.extend(_pick_diverse(success_mid, targets["success_mid"]))
    picked.extend(_pick_diverse(success_low, targets["success_low"]))
    picked.extend(_pick_diverse(partial_any, targets["partial_any"]))

    # De-dupe by source_record_id
    dedup: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in picked:
        rid = str(row.get("source_record_id") or "")
        if rid in seen_ids:
            continue
        seen_ids.add(rid)
        dedup.append(row)

    return dedup[:sample_size]


def build_prompt_payload(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for row in rows:
        occ = row.get("occupation_candidates") or []
        skills = row.get("skill_candidates") or []
        payload.append(
            {
                "source_record_id": row.get("source_record_id"),
                "category": row.get("category"),
                "normalization_status": row.get("normalization_status"),
                "top_occupations": [
                    {
                        "preferred_label": c.get("preferred_label"),
                        "confidence": c.get("confidence"),
                        "match_method": c.get("match_method"),
                    }
                    for c in occ[:5]
                ],
                "top_skills": [s.get("preferred_label") for s in skills[:12]],
                "resume_excerpt": (row.get("resume_text") or "")[:1300],
            }
        )
    return payload


def parse_json_response(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except Exception:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", stripped)
    if fenced:
        return json.loads(fenced.group(1))

    raise ValueError("Could not parse LLM response as JSON")


def main() -> None:
    args = parse_args()

    env_path = Path("script/pipeline_mongo/.env")
    if load_dotenv is not None and env_path.exists():
        load_dotenv(env_path)

    if OpenAI is None:
        raise RuntimeError("openai package is not available")

    client = MongoClient(args.mongo_uri)
    col = client[args.db_name][args.collection]

    docs = list(
        col.find(
            {},
            {
                "_id": 0,
                "source_record_id": 1,
                "category": 1,
                "normalization_status": 1,
                "resume_text": 1,
                "occupation_candidates": 1,
                "skill_candidates": 1,
            },
        )
    )
    selected = select_representative_docs(docs, args.sample_size)
    if len(selected) < args.sample_size:
        raise RuntimeError(f"Not enough docs selected: {len(selected)}")

    payload = build_prompt_payload(selected)

    oa = OpenAI()
    response = oa.responses.create(
        model=args.model,
        temperature=0,
        input=[
            {
                "role": "system",
                "content": (
                    "You are an evaluator for resume-to-occupation matching quality. "
                    "Judge top occupation candidates using resume excerpt and skills. "
                    "Return strict JSON only."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": (
                            "For each item, evaluate quality of Top-1 fit and Top-3 ranking. "
                            "Scoring range is 0-100. "
                            "Use verdict: good|mixed|poor. "
                            "Keep reason_ja concise (<=120 Japanese chars)."
                        ),
                        "items": payload,
                        "output_schema": {
                            "evaluations": [
                                {
                                    "source_record_id": "string",
                                    "top1_fit_score": 0,
                                    "top3_ranking_score": 0,
                                    "overall_score": 0,
                                    "verdict": "good|mixed|poor",
                                    "reason_ja": "string",
                                    "manual_check_needed": True,
                                }
                            ]
                        },
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    )

    parsed = parse_json_response(response.output_text or "")
    evaluations = parsed.get("evaluations") if isinstance(parsed, dict) else None
    if not isinstance(evaluations, list):
        raise RuntimeError("LLM output did not contain evaluations list")

    by_id = {str(item.get("source_record_id")): item for item in evaluations}
    merged: list[dict[str, Any]] = []
    for row in payload:
        rid = str(row.get("source_record_id"))
        judge = by_id.get(rid, {})
        merged.append(
            {
                "source_record_id": rid,
                "category": row.get("category"),
                "normalization_status": row.get("normalization_status"),
                "top_occupations": row.get("top_occupations"),
                "judge": judge,
            }
        )

    verdict_counts = Counter((m.get("judge") or {}).get("verdict", "unknown") for m in merged)
    avg_top1 = sum(float((m.get("judge") or {}).get("top1_fit_score", 0)) for m in merged) / len(merged)
    avg_top3 = sum(float((m.get("judge") or {}).get("top3_ranking_score", 0)) for m in merged) / len(merged)
    avg_overall = sum(float((m.get("judge") or {}).get("overall_score", 0)) for m in merged) / len(merged)

    report = {
        "generated_at_utc": datetime.utcnow().isoformat(),
        "model": args.model,
        "sample_size": len(merged),
        "summary": {
            "avg_top1_fit_score": round(avg_top1, 2),
            "avg_top3_ranking_score": round(avg_top3, 2),
            "avg_overall_score": round(avg_overall, 2),
            "verdict_counts": dict(verdict_counts),
        },
        "evaluations": merged,
    }

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# LLM Evaluation (Representative 10 Docs)")
    lines.append("")
    lines.append(f"- Generated at (UTC): {report['generated_at_utc']}")
    lines.append(f"- Model: {args.model}")
    lines.append(f"- Avg Top1 fit score: {report['summary']['avg_top1_fit_score']}")
    lines.append(f"- Avg Top3 ranking score: {report['summary']['avg_top3_ranking_score']}")
    lines.append(f"- Avg overall score: {report['summary']['avg_overall_score']}")
    lines.append(f"- Verdict counts: {report['summary']['verdict_counts']}")
    lines.append("")
    lines.append("## Items")
    for item in merged:
        judge = item.get("judge") or {}
        top1_label = ""
        top_occupations = item.get("top_occupations") or []
        if top_occupations:
            top1_label = str(top_occupations[0].get("preferred_label") or "")
        lines.append(
            f"- ID={item.get('source_record_id')} cat={item.get('category')} status={item.get('normalization_status')} "
            f"top1='{top1_label}' score={judge.get('overall_score')} verdict={judge.get('verdict')} "
            f"reason={judge.get('reason_ja')}"
        )

    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print({"json": str(out_json), "md": str(out_md), "summary": report["summary"]})


if __name__ == "__main__":
    main()
