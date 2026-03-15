from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from pymongo import MongoClient

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

from milvus_client import MilvusSearchClient


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
    out: list[str] = []
    out.extend(CATEGORY_ALIAS_PHRASES.get(upper_category, []))
    out.extend([tok for tok in normalize_text(normalized_category).split() if len(tok) >= 3])
    return unique_strings(out)


def extract_skill_phrases(doc: dict[str, Any]) -> list[str]:
    extracted = doc.get("extracted_fields")
    if isinstance(extracted, dict):
        raw_skills: list[str] = []
        for item in extracted.get("skills") or []:
            if isinstance(item, dict) and isinstance(item.get("raw_text"), str):
                raw_skills.append(item["raw_text"])
            elif isinstance(item, str):
                raw_skills.append(item)
        if raw_skills:
            return unique_strings(raw_skills)[:30]

    text = normalize_spaces(doc.get("resume_text") or "")
    if not text:
        return []
    parts = re.split(r"[\n,;|•\-]+", text[:1800])
    phrases: list[str] = []
    for part in parts:
        phrase = normalize_spaces(part)
        if 2 <= len(phrase) <= 120:
            phrases.append(phrase)
    return unique_strings(phrases)[:30]


def extract_occupation_phrases(doc: dict[str, Any]) -> list[str]:
    extracted = doc.get("extracted_fields")
    values: list[str] = []
    category = normalize_spaces(doc.get("category") or "")
    if category:
        values.append(category)
        values.extend(category_anchor_phrases(category))

    if isinstance(extracted, dict):
        values.extend([v for v in extracted.get("occupation_candidates") or [] if isinstance(v, str)])

    return unique_strings(values)[:20]


def select_representative_docs(collection, sample_size: int) -> list[dict[str, Any]]:
    pipeline = [
        {"$match": {"source_dataset": "1st_data"}},
        {"$sort": {"source_record_id": 1}},
        {
            "$group": {
                "_id": "$category",
                "doc": {"$first": "$$ROOT"},
            }
        },
        {"$replaceRoot": {"newRoot": "$doc"}},
        {"$limit": sample_size},
        {
            "$project": {
                "_id": 0,
                "source_record_id": 1,
                "category": 1,
                "resume_text": 1,
                "extracted_fields": 1,
            }
        },
    ]
    rows = list(collection.aggregate(pipeline))
    if len(rows) >= sample_size:
        return rows[:sample_size]

    need = sample_size - len(rows)
    existing_ids = {str(r.get("source_record_id") or "") for r in rows}
    fallback = list(
        collection.find(
            {
                "source_dataset": "1st_data",
                "source_record_id": {"$nin": list(existing_ids)},
            },
            {"_id": 0, "source_record_id": 1, "category": 1, "resume_text": 1, "extracted_fields": 1},
        )
        .sort("source_record_id", 1)
        .limit(need)
    )
    rows.extend(fallback)
    return rows[:sample_size]


def embed_query(openai_client: Any, model: str, text: str) -> list[float]:
    resp = openai_client.embeddings.create(model=model, input=text)
    data = getattr(resp, "data", None) or []
    if not data:
        raise RuntimeError("No embedding data returned")
    vector = list(getattr(data[0], "embedding", []) or [])
    if not vector:
        raise RuntimeError("Empty embedding vector returned")
    return vector


def score_to_confidence(score: float) -> float:
    return MilvusSearchClient.score_to_confidence(score)


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{2,}", normalize_text(text)))


def evaluate_doc(
    doc: dict[str, Any],
    openai_client: Any,
    model: str,
    milvus_client: MilvusSearchClient,
    top_k: int,
) -> dict[str, Any]:
    category = normalize_spaces(doc.get("category") or "")
    source_record_id = str(doc.get("source_record_id") or "")

    occ_phrases = extract_occupation_phrases(doc)
    skill_phrases = extract_skill_phrases(doc)

    occ_query = occ_phrases[0] if occ_phrases else ""
    skill_query = skill_phrases[0] if skill_phrases else ""

    occupation_hits: list[dict[str, Any]] = []
    skill_hits: list[dict[str, Any]] = []

    if occ_query:
        vector = embed_query(openai_client, model, occ_query)
        for rank, hit in enumerate(milvus_client.search_occupation(vector, top_k), start=1):
            occupation_hits.append(
                {
                    "rank": rank,
                    "esco_id": hit.esco_id,
                    "label": hit.preferred_label,
                    "score": round(float(hit.score), 6),
                    "confidence": round(score_to_confidence(float(hit.score)), 6),
                }
            )

    if skill_query:
        vector = embed_query(openai_client, model, skill_query)
        for rank, hit in enumerate(milvus_client.search_skill(vector, top_k), start=1):
            skill_hits.append(
                {
                    "rank": rank,
                    "esco_id": hit.esco_id,
                    "label": hit.preferred_label,
                    "score": round(float(hit.score), 6),
                    "confidence": round(score_to_confidence(float(hit.score)), 6),
                }
            )

    occ_top1 = occupation_hits[0] if occupation_hits else None
    skill_top1 = skill_hits[0] if skill_hits else None
    occ_anchor_tokens = tokens(" ".join(category_anchor_phrases(category) + [category]))
    occ_label_tokens = tokens(occ_top1["label"]) if occ_top1 else set()
    skill_query_tokens = tokens(skill_query)
    skill_label_tokens = tokens(skill_top1["label"]) if skill_top1 else set()

    return {
        "source_record_id": source_record_id,
        "category": category,
        "occupation_query": occ_query,
        "skill_query": skill_query,
        "occupation_hits": occupation_hits,
        "skill_hits": skill_hits,
        "heuristics": {
            "occ_top1_has_category_anchor": bool(occ_anchor_tokens & occ_label_tokens) if occ_top1 else None,
            "skill_top1_has_query_token_overlap": bool(skill_query_tokens & skill_label_tokens) if skill_top1 else None,
        },
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Milvus Retrieval Check (1st_data Representative Samples)")
    lines.append("")
    lines.append(f"- Generated at (UTC): {report['generated_at_utc']}")
    lines.append(f"- Sample size: {report['sample_size']}")
    lines.append(f"- Top-K: {report['top_k']}")
    lines.append(f"- Embedding model: {report['embedding_model']}")
    lines.append(f"- Occ collection: {report['milvus']['occ_collection']}")
    lines.append(f"- Skill collection: {report['milvus']['skill_collection']}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Occ top1 category-anchor hit: {report['summary']['occ_top1_anchor_hit_count']} / {report['sample_size']}")
    lines.append(
        f"- Skill top1 query-token overlap hit: {report['summary']['skill_top1_query_overlap_count']} / {report['sample_size']}"
    )
    lines.append("")
    lines.append("## Per Sample")

    for item in report["samples"]:
        lines.append("")
        lines.append(
            f"### ID={item['source_record_id']} / category={item['category']}"
        )
        lines.append(f"- Occupation query: `{item['occupation_query']}`")
        lines.append(f"- Skill query: `{item['skill_query']}`")
        lines.append(
            f"- Heuristic: occ_anchor_hit={item['heuristics']['occ_top1_has_category_anchor']}, "
            f"skill_query_overlap={item['heuristics']['skill_top1_has_query_token_overlap']}"
        )

        lines.append("")
        lines.append("Occupation Top-K")
        lines.append("")
        lines.append("| rank | label | score | confidence |")
        lines.append("|---:|---|---:|---:|")
        for hit in item["occupation_hits"]:
            lines.append(
                f"| {hit['rank']} | {hit['label']} | {hit['score']:.6f} | {hit['confidence']:.6f} |"
            )

        lines.append("")
        lines.append("Skill Top-K")
        lines.append("")
        lines.append("| rank | label | score | confidence |")
        lines.append("|---:|---|---:|---:|")
        for hit in item["skill_hits"]:
            lines.append(
                f"| {hit['rank']} | {hit['label']} | {hit['score']:.6f} | {hit['confidence']:.6f} |"
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Milvus retrieval on representative 1st_data samples.")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db-name", default="prodapt_capstone")
    parser.add_argument("--source-collection", default="source_1st_resumes")
    parser.add_argument("--sample-size", type=int, default=10)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument("--openai-api-key", default="")
    parser.add_argument("--milvus-uri", default="")
    parser.add_argument("--milvus-token", default="")
    parser.add_argument("--milvus-db-name", default="")
    parser.add_argument("--milvus-occ-collection", default="")
    parser.add_argument("--milvus-skill-collection", default="")
    parser.add_argument(
        "--out-json",
        default="script/pipeline_mongo/milvus_retrieval_samples.json",
    )
    parser.add_argument(
        "--out-md",
        default="docs/Milvus-Retrieval-Samples.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    env_path = Path(__file__).resolve().parent / ".env"
    if load_dotenv is not None and env_path.exists():
        load_dotenv(env_path)

    openai_api_key = args.openai_api_key or os.getenv("OPENAI_API_KEY", "")
    milvus_uri = args.milvus_uri or os.getenv("MILVUS_URI", "")
    milvus_token = args.milvus_token or os.getenv("MILVUS_TOKEN", "")
    milvus_db_name = args.milvus_db_name or os.getenv("MILVUS_DB_NAME", "")
    milvus_occ_collection = args.milvus_occ_collection or os.getenv(
        "MILVUS_OCC_COLLECTION",
        "occupation_collection",
    )
    milvus_skill_collection = args.milvus_skill_collection or os.getenv(
        "MILVUS_SKILL_COLLECTION",
        "skill_collection",
    )

    if OpenAI is None:
        raise RuntimeError("openai package is not available")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    if not milvus_uri:
        raise RuntimeError("MILVUS_URI is not configured")

    openai_client = OpenAI(api_key=openai_api_key)
    milvus_client = MilvusSearchClient(
        uri=milvus_uri,
        token=milvus_token,
        db_name=milvus_db_name,
        occupation_collection=milvus_occ_collection,
        skill_collection=milvus_skill_collection,
    )

    mongo = MongoClient(args.mongo_uri)
    source = mongo[args.db_name][args.source_collection]
    docs = select_representative_docs(source, args.sample_size)

    rows: list[dict[str, Any]] = []
    for doc in docs:
        rows.append(
            evaluate_doc(
                doc,
                openai_client=openai_client,
                model=args.embedding_model,
                milvus_client=milvus_client,
                top_k=args.top_k,
            )
        )

    occ_anchor_hits = sum(1 for r in rows if r["heuristics"]["occ_top1_has_category_anchor"])
    skill_overlap_hits = sum(1 for r in rows if r["heuristics"]["skill_top1_has_query_token_overlap"])
    categories = Counter(normalize_spaces(r.get("category")) or "UNKNOWN" for r in rows)

    report = {
        "generated_at_utc": datetime.utcnow().isoformat(),
        "sample_size": len(rows),
        "top_k": args.top_k,
        "embedding_model": args.embedding_model,
        "milvus": {
            "db_name": milvus_db_name,
            "occ_collection": milvus_occ_collection,
            "skill_collection": milvus_skill_collection,
        },
        "summary": {
            "occ_top1_anchor_hit_count": occ_anchor_hits,
            "skill_top1_query_overlap_count": skill_overlap_hits,
            "category_counts": dict(categories),
        },
        "samples": rows,
    }

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    out_md = Path(args.out_md)
    write_markdown(out_md, report)

    print({"json": str(out_json), "md": str(out_md), "summary": report["summary"]})


if __name__ == "__main__":
    main()
