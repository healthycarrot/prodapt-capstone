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

GENERIC_EXPERIENCE_WORDS = {
    "responsible",
    "responsibilities",
    "duties",
    "worked",
    "work",
    "team",
    "using",
    "use",
    "ensure",
    "managed",
    "manage",
    "support",
    "various",
    "including",
    "daily",
    "year",
    "years",
    "ability",
    "skills",
    "experience",
}

SKILL_STOPWORDS = {
    "skill",
    "skills",
    "experience",
    "years",
    "year",
    "used",
    "knowledge",
    "ability",
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


def tokens(text: str, stopwords: set[str] | None = None) -> set[str]:
    sw = stopwords or set()
    return {t for t in re.findall(r"[a-z]{2,}", normalize_text(text)) if t not in sw}


def parse_date_key(value: str | None) -> str:
    return normalize_spaces(value or "")


def sort_experiences(experiences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(e: dict[str, Any]) -> tuple[int, str, str]:
        return (
            1 if bool(e.get("is_current")) else 0,
            parse_date_key(e.get("end_date")),
            parse_date_key(e.get("start_date")),
        )

    return sorted(experiences, key=key, reverse=True)


def build_experience_raw(experiences: list[dict[str, Any]], max_chars: int) -> str:
    top = sort_experiences(experiences)[:2]
    chunks: list[str] = []
    for exp in top:
        title = normalize_spaces(exp.get("title") or exp.get("raw_title"))
        company = normalize_spaces(exp.get("company"))
        desc = normalize_spaces(exp.get("description_raw"))
        part = " | ".join([v for v in [title, company, desc] if v])
        if part:
            chunks.append(part)
    text = " ; ".join(chunks)
    return text[:max_chars]


def build_experience_summary(experiences: list[dict[str, Any]], max_chars: int) -> str:
    top = sort_experiences(experiences)[:2]
    titles = unique_strings(
        [
            normalize_spaces(exp.get("title") or exp.get("raw_title"))
            for exp in top
            if normalize_spaces(exp.get("title") or exp.get("raw_title"))
        ]
    )[:2]
    desc_text = " ".join(normalize_spaces(exp.get("description_raw")) for exp in top)
    desc_tokens = [t for t in re.findall(r"[a-z]{3,}", desc_text.lower()) if t not in GENERIC_EXPERIENCE_WORDS]
    top_terms = [term for term, _ in Counter(desc_tokens).most_common(6)]

    snippets: list[str] = []
    if titles:
        snippets.append("titles: " + " / ".join(titles))
    if top_terms:
        snippets.append("tasks: " + ", ".join(top_terms))
    return " ; ".join(snippets)[:max_chars]


def get_extracted(doc: dict[str, Any]) -> dict[str, Any]:
    return doc.get("extracted_fields") if isinstance(doc.get("extracted_fields"), dict) else {}


def build_base_occupation_query(doc: dict[str, Any]) -> str:
    category = normalize_spaces(doc.get("category") or "")
    extracted = get_extracted(doc)
    occ_candidates = [v for v in extracted.get("occupation_candidates") or [] if isinstance(v, str)]
    phrases = unique_strings([category] + category_anchor_phrases(category) + occ_candidates)
    return " ; ".join(phrases[:3])


def build_base_skill_query(doc: dict[str, Any]) -> str:
    extracted = get_extracted(doc)
    raw_skills: list[str] = []
    for item in extracted.get("skills") or []:
        if isinstance(item, dict) and isinstance(item.get("raw_text"), str):
            raw_skills.append(item["raw_text"])
        elif isinstance(item, str):
            raw_skills.append(item)
    phrases = unique_strings(raw_skills)
    return " ; ".join(phrases[:3])


def build_queries(doc: dict[str, Any], raw_max_chars: int, summary_max_chars: int) -> dict[str, dict[str, str]]:
    extracted = get_extracted(doc)
    experiences = extracted.get("experiences") if isinstance(extracted.get("experiences"), list) else []
    experiences = [e for e in experiences if isinstance(e, dict)]

    occ_base = build_base_occupation_query(doc)
    skill_base = build_base_skill_query(doc)
    exp_raw = build_experience_raw(experiences, raw_max_chars)
    exp_summary = build_experience_summary(experiences, summary_max_chars)

    def join_query(base: str, exp_text: str) -> str:
        base_norm = normalize_spaces(base)
        exp_norm = normalize_spaces(exp_text)
        if base_norm and exp_norm:
            return f"{base_norm} ; experience: {exp_norm}"
        return base_norm or exp_norm

    return {
        "occupation": {
            "A": occ_base,
            "B1": join_query(occ_base, exp_raw),
            "B2": join_query(occ_base, exp_summary),
        },
        "skill": {
            "A": skill_base,
            "B1": join_query(skill_base, exp_raw),
            "B2": join_query(skill_base, exp_summary),
        },
        "experience": {
            "raw": exp_raw,
            "summary": exp_summary,
        },
    }


def select_representative_docs(collection, sample_size: int) -> list[dict[str, Any]]:
    pipeline = [
        {"$match": {"source_dataset": "1st_data"}},
        {"$sort": {"source_record_id": 1}},
        {"$group": {"_id": "$category", "doc": {"$first": "$$ROOT"}}},
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


def load_pseudo_labels(collection, source_ids: list[str]) -> dict[str, dict[str, str]]:
    labels: dict[str, dict[str, str]] = {}
    docs = list(
        collection.find(
            {
                "source_dataset": "1st_data",
                "source_record_id": {"$in": source_ids},
            },
            {
                "_id": 0,
                "source_record_id": 1,
                "occupation_candidates": 1,
                "skill_candidates": 1,
            },
        )
    )
    for doc in docs:
        rid = str(doc.get("source_record_id") or "")
        occ_rows = doc.get("occupation_candidates") if isinstance(doc.get("occupation_candidates"), list) else []
        skill_rows = doc.get("skill_candidates") if isinstance(doc.get("skill_candidates"), list) else []
        occ_top1 = occ_rows[0] if occ_rows else {}
        skill_top1 = skill_rows[0] if skill_rows else {}
        labels[rid] = {
            "occ_esco_id": str(occ_top1.get("esco_id") or ""),
            "skill_esco_id": str(skill_top1.get("esco_id") or ""),
        }
    return labels


def embed(openai_client: Any, model: str, text: str, cache: dict[str, list[float]]) -> list[float] | None:
    key = normalize_text(text)
    if not key:
        return None
    if key in cache:
        return cache[key]
    resp = openai_client.embeddings.create(model=model, input=text)
    data = getattr(resp, "data", None) or []
    if not data:
        return None
    vec = list(getattr(data[0], "embedding", []) or [])
    if not vec:
        return None
    cache[key] = vec
    return vec


def search_single(
    target: str,
    query: str,
    top_k: int,
    openai_client: Any,
    model: str,
    milvus_client: MilvusSearchClient,
    embed_cache: dict[str, list[float]],
) -> list[dict[str, Any]]:
    vector = embed(openai_client, model, query, embed_cache)
    if not vector:
        return []

    hits = (
        milvus_client.search_occupation(vector, top_k)
        if target == "occupation"
        else milvus_client.search_skill(vector, top_k)
    )
    out: list[dict[str, Any]] = []
    for rank, hit in enumerate(hits, start=1):
        conf = MilvusSearchClient.score_to_confidence(float(hit.score))
        out.append(
            {
                "rank": rank,
                "esco_id": str(hit.esco_id),
                "label": str(hit.preferred_label),
                "score": float(hit.score),
                "confidence": float(conf),
            }
        )
    return out


def rrf_fuse(hit_lists: list[list[dict[str, Any]]], out_top_k: int, rrf_k: int) -> list[dict[str, Any]]:
    fused: dict[str, dict[str, Any]] = {}
    for result in hit_lists:
        for item in result:
            esco_id = str(item["esco_id"])
            rank = int(item["rank"])
            row = fused.setdefault(
                esco_id,
                {
                    "esco_id": esco_id,
                    "label": str(item["label"]),
                    "rrf_score": 0.0,
                    "confidence": 0.0,
                    "best_score": float(item["score"]),
                },
            )
            row["rrf_score"] += 1.0 / float(rrf_k + rank)
            if float(item["confidence"]) > float(row["confidence"]):
                row["confidence"] = float(item["confidence"])
                row["label"] = str(item["label"])
            if float(item["score"]) > float(row["best_score"]):
                row["best_score"] = float(item["score"])

    rows = sorted(fused.values(), key=lambda x: (x["rrf_score"], x["confidence"]), reverse=True)[:out_top_k]
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        out.append(
            {
                "rank": idx,
                "esco_id": row["esco_id"],
                "label": row["label"],
                "rrf_score": round(float(row["rrf_score"]), 8),
                "confidence": round(float(row["confidence"]), 8),
                "score": round(float(row["best_score"]), 8),
            }
        )
    return out


def reciprocal_rank(results: list[dict[str, Any]], target_esco_id: str, cutoff: int) -> float:
    if not target_esco_id:
        return 0.0
    for item in results[:cutoff]:
        if item.get("esco_id") == target_esco_id:
            return 1.0 / float(item.get("rank") or 1)
    return 0.0


def hit_at(results: list[dict[str, Any]], target_esco_id: str, k: int) -> bool:
    if not target_esco_id:
        return False
    return any(item.get("esco_id") == target_esco_id for item in results[:k])


def summarize_variant(
    rows: list[dict[str, Any]],
    variant: str,
    target: str,
    pseudo_key: str,
    top_k: int,
) -> dict[str, Any]:
    with_results = [r for r in rows if r.get("results", {}).get(target, {}).get(variant)]
    expected_rows = [r for r in with_results if (r.get("pseudo") or {}).get(pseudo_key)]

    hit1 = 0
    hit5 = 0
    mrr = 0.0
    top1_conf_sum = 0.0
    top1_count = 0
    heur_hit = 0
    heur_count = 0

    for row in with_results:
        result_rows = row["results"][target][variant]
        if result_rows:
            top1_conf_sum += float(result_rows[0].get("confidence", 0.0))
            top1_count += 1
        heuristics = row.get("heuristics", {})
        if target == "occupation":
            v = heuristics.get("occ_anchor_hit", {}).get(variant)
        else:
            v = heuristics.get("skill_overlap_hit", {}).get(variant)
        if v is not None:
            heur_count += 1
            if v:
                heur_hit += 1

    for row in expected_rows:
        result_rows = row["results"][target][variant]
        expected = row["pseudo"][pseudo_key]
        if hit_at(result_rows, expected, 1):
            hit1 += 1
        if hit_at(result_rows, expected, min(5, top_k)):
            hit5 += 1
        mrr += reciprocal_rank(result_rows, expected, min(10, top_k))

    expected_count = len(expected_rows)
    return {
        "docs_with_results": len(with_results),
        "expected_count": expected_count,
        "pseudo_hit_at_1": round((hit1 / expected_count), 4) if expected_count else None,
        "pseudo_hit_at_5": round((hit5 / expected_count), 4) if expected_count else None,
        "pseudo_mrr_at_10": round((mrr / expected_count), 4) if expected_count else None,
        "avg_top1_confidence": round((top1_conf_sum / top1_count), 4) if top1_count else None,
        "heuristic_hit_ratio": round((heur_hit / heur_count), 4) if heur_count else None,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Milvus A/B Experience Query Comparison")
    lines.append("")
    lines.append(f"- Generated at (UTC): {report['generated_at_utc']}")
    lines.append(f"- Sample size: {report['sample_size']}")
    lines.append(f"- Top-K: {report['top_k']}")
    lines.append(f"- Embedding model: {report['embedding_model']}")
    lines.append(f"- Low-confidence threshold: {report['low_conf_threshold']}")
    lines.append("")
    lines.append("## Variant Definition")
    lines.append("- A: base query only")
    lines.append("- B1: base + raw experience (top 2 experiences)")
    lines.append("- B2: base + summarized experience (titles + representative terms)")
    lines.append("- G_B1: low-confidence gate (A default, switch to B1 only when A top1 confidence < threshold)")
    lines.append("- G_B2: low-confidence gate (A default, switch to B2 only when A top1 confidence < threshold)")
    lines.append("- Fusion: RRF for multi-query variants (A + B1_input / A + B2_input)")
    lines.append("")

    lines.append("## Occupation Metrics")
    lines.append("")
    lines.append("| variant | docs_with_results | expected_count | pseudo_hit@1 | pseudo_hit@5 | pseudo_mrr@10 | avg_top1_conf | heuristic_hit |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for variant in ["A", "B1", "B2", "G_B1", "G_B2"]:
        row = report["summary"]["occupation"][variant]
        lines.append(
            f"| {variant} | {row['docs_with_results']} | {row['expected_count']} | "
            f"{row['pseudo_hit_at_1']} | {row['pseudo_hit_at_5']} | {row['pseudo_mrr_at_10']} | "
            f"{row['avg_top1_confidence']} | {row['heuristic_hit_ratio']} |"
        )

    lines.append("")
    lines.append("## Skill Metrics")
    lines.append("")
    lines.append("| variant | docs_with_results | expected_count | pseudo_hit@1 | pseudo_hit@5 | pseudo_mrr@10 | avg_top1_conf | heuristic_hit |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for variant in ["A", "B1", "B2", "G_B1", "G_B2"]:
        row = report["summary"]["skill"][variant]
        lines.append(
            f"| {variant} | {row['docs_with_results']} | {row['expected_count']} | "
            f"{row['pseudo_hit_at_1']} | {row['pseudo_hit_at_5']} | {row['pseudo_mrr_at_10']} | "
            f"{row['avg_top1_confidence']} | {row['heuristic_hit_ratio']} |"
        )

    lines.append("")
    lines.append("## Low-Confidence Cohort (A-based gate)")
    lines.append("")
    lines.append(
        f"- low_conf_doc_count: {report['low_conf_summary']['doc_count']} / {report['sample_size']}"
    )
    lines.append(f"- occupation_gate_ratio: {report['low_conf_summary']['occupation_ratio']}")
    lines.append(f"- skill_gate_ratio: {report['low_conf_summary']['skill_ratio']}")
    lines.append("")
    lines.append("## Notes")
    lines.append("- pseudo_* metrics use current `normalized_candidates` top1 as weak target.")
    lines.append("- heuristic_hit is:")
    lines.append("  - occupation: top1 label has category anchor")
    lines.append("  - skill: top1 label token overlaps base skill query tokens")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare A/B1/B2 Milvus retrieval patterns with experience augmentation.")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db-name", default="prodapt_capstone")
    parser.add_argument("--source-collection", default="source_1st_resumes")
    parser.add_argument("--normalized-collection", default="normalized_candidates")
    parser.add_argument("--sample-size", type=int, default=60)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument("--low-conf-threshold", type=float, default=0.45)
    parser.add_argument("--raw-exp-max-chars", type=int, default=500)
    parser.add_argument("--summary-exp-max-chars", type=int, default=220)
    parser.add_argument("--openai-api-key", default="")
    parser.add_argument("--milvus-uri", default="")
    parser.add_argument("--milvus-token", default="")
    parser.add_argument("--milvus-db-name", default="")
    parser.add_argument("--milvus-occ-collection", default="")
    parser.add_argument("--milvus-skill-collection", default="")
    parser.add_argument("--out-json", default="script/pipeline_mongo/milvus_ab_experience_comparison.json")
    parser.add_argument("--out-md", default="docs/Milvus-AB-Experience-Comparison.md")
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
        raise RuntimeError("openai package is not installed")
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
    normalized = mongo[args.db_name][args.normalized_collection]

    docs = select_representative_docs(source, args.sample_size)
    source_ids = [str(d.get("source_record_id") or "") for d in docs if str(d.get("source_record_id") or "")]
    pseudo = load_pseudo_labels(normalized, source_ids)

    embed_cache: dict[str, list[float]] = {}
    rows: list[dict[str, Any]] = []
    low_conf_occ = 0
    low_conf_skill = 0

    for doc in docs:
        rid = str(doc.get("source_record_id") or "")
        category = normalize_spaces(doc.get("category") or "")
        query_pack = build_queries(
            doc,
            raw_max_chars=args.raw_exp_max_chars,
            summary_max_chars=args.summary_exp_max_chars,
        )

        results: dict[str, dict[str, list[dict[str, Any]]]] = {
            "occupation": {"A": [], "B1": [], "B2": [], "G_B1": [], "G_B2": []},
            "skill": {"A": [], "B1": [], "B2": [], "G_B1": [], "G_B2": []},
        }
        heur_occ: dict[str, bool | None] = {}
        heur_skill: dict[str, bool | None] = {}

        for target in ["occupation", "skill"]:
            q_a = query_pack[target]["A"]
            q_b1 = query_pack[target]["B1"]
            q_b2 = query_pack[target]["B2"]

            base = search_single(
                target=target,
                query=q_a,
                top_k=args.top_k,
                openai_client=openai_client,
                model=args.embedding_model,
                milvus_client=milvus_client,
                embed_cache=embed_cache,
            ) if q_a else []
            extra_b1 = search_single(
                target=target,
                query=q_b1,
                top_k=args.top_k,
                openai_client=openai_client,
                model=args.embedding_model,
                milvus_client=milvus_client,
                embed_cache=embed_cache,
            ) if q_b1 else []
            extra_b2 = search_single(
                target=target,
                query=q_b2,
                top_k=args.top_k,
                openai_client=openai_client,
                model=args.embedding_model,
                milvus_client=milvus_client,
                embed_cache=embed_cache,
            ) if q_b2 else []

            results[target]["A"] = base
            results[target]["B1"] = rrf_fuse([base, extra_b1], out_top_k=args.top_k, rrf_k=args.rrf_k)
            results[target]["B2"] = rrf_fuse([base, extra_b2], out_top_k=args.top_k, rrf_k=args.rrf_k)

            base_top1_conf = float(base[0].get("confidence", 0.0)) if base else 0.0
            use_gate = base_top1_conf < args.low_conf_threshold
            results[target]["G_B1"] = results[target]["B1"] if use_gate else results[target]["A"]
            results[target]["G_B2"] = results[target]["B2"] if use_gate else results[target]["A"]
            if target == "occupation" and base_top1_conf < args.low_conf_threshold:
                low_conf_occ += 1
            if target == "skill" and base_top1_conf < args.low_conf_threshold:
                low_conf_skill += 1

        for variant in ["A", "B1", "B2", "G_B1", "G_B2"]:
            occ_top1 = results["occupation"][variant][0]["label"] if results["occupation"][variant] else None
            heur_occ[variant] = label_matches_category(occ_top1, category) if occ_top1 else None

            skill_top1 = results["skill"][variant][0]["label"] if results["skill"][variant] else None
            skill_base_tokens = tokens(query_pack["skill"]["A"], stopwords=SKILL_STOPWORDS)
            skill_label_tokens = tokens(skill_top1) if skill_top1 else set()
            heur_skill[variant] = bool(skill_base_tokens & skill_label_tokens) if skill_top1 and skill_base_tokens else None

        rows.append(
            {
                "source_record_id": rid,
                "category": category,
                "queries": query_pack,
                "pseudo": pseudo.get(rid, {"occ_esco_id": "", "skill_esco_id": ""}),
                "results": results,
                "heuristics": {
                    "occ_anchor_hit": heur_occ,
                    "skill_overlap_hit": heur_skill,
                },
            }
        )

    summary = {
        "occupation": {},
        "skill": {},
    }
    for variant in ["A", "B1", "B2", "G_B1", "G_B2"]:
        summary["occupation"][variant] = summarize_variant(
            rows,
            variant=variant,
            target="occupation",
            pseudo_key="occ_esco_id",
            top_k=args.top_k,
        )
        summary["skill"][variant] = summarize_variant(
            rows,
            variant=variant,
            target="skill",
            pseudo_key="skill_esco_id",
            top_k=args.top_k,
        )

    report = {
        "generated_at_utc": datetime.utcnow().isoformat(),
        "sample_size": len(rows),
        "top_k": args.top_k,
        "rrf_k": args.rrf_k,
        "embedding_model": args.embedding_model,
        "low_conf_threshold": args.low_conf_threshold,
        "milvus": {
            "db_name": milvus_db_name,
            "occ_collection": milvus_occ_collection,
            "skill_collection": milvus_skill_collection,
        },
        "summary": summary,
        "low_conf_summary": {
            "doc_count": len(rows),
            "occupation_low_conf_count": low_conf_occ,
            "skill_low_conf_count": low_conf_skill,
            "occupation_ratio": round(low_conf_occ / len(rows), 4) if rows else 0.0,
            "skill_ratio": round(low_conf_skill / len(rows), 4) if rows else 0.0,
        },
        "samples": rows,
    }

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    out_md = Path(args.out_md)
    write_markdown(out_md, report)

    print(
        {
            "json": str(out_json),
            "md": str(out_md),
            "summary": report["summary"],
            "low_conf_summary": report["low_conf_summary"],
        }
    )


if __name__ == "__main__":
    main()
