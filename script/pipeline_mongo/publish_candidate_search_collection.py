from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
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

try:
    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
except Exception:
    Collection = None
    CollectionSchema = None
    DataType = None
    FieldSchema = None
    connections = None
    utility = None


EMBEDDING_VERSION_DEFAULT = "pr06_candidate_search_v1"
MAX_VECTOR_TEXT_CHARS = 1200
DEFAULT_SNAPSHOT_PREFIX = "snapshot"
SAFE_SNAPSHOT_RE = re.compile(r"^[A-Za-z0-9._-]+$")
ESCO_ISCO_PREFIX = "http://data.europa.eu/esco/isco/"
PRESENT_DATE_TOKENS = {
    "present",
    "current",
    "ongoing",
    "now",
    "to date",
    "till date",
}
SKILL_CONTEXT_HINTS = (
    "skill",
    "skills",
    "tool",
    "tools",
    "technology",
    "technologies",
    "framework",
    "frameworks",
    "platform",
    "platforms",
    "develop",
    "developed",
    "implemented",
    "programming",
    "analysis",
    "automation",
)


@dataclass
class CandidatePublishRecord:
    vector_doc_id: str
    candidate_id: str
    normalized_doc_id: str
    source_dataset: str
    source_record_id: str
    snapshot_version: str
    normalizer_version: str
    embedding_model: str
    embedding_version: str
    skill_text: str
    occupation_text: str
    category: str
    industry_esco_id: str | None
    industry_esco_ids_json: list[str]
    occupation_esco_ids_json: list[str]
    skill_esco_ids_json: list[str]
    experience_months_total: int | None
    highest_education_level_rank: int
    current_location: str
    normalization_status: str


class PublishError(RuntimeError):
    pass


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


def compact_text(value: str, max_chars: int = MAX_VECTOR_TEXT_CHARS) -> str:
    text = normalize_spaces(value)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            return int(text)
        if text.startswith("-") and text[1:].isdigit():
            return int(text)
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish candidate_search_collection (PR-06) from normalized_candidates."
    )
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db-name", default="prodapt_capstone")
    parser.add_argument("--normalized-collection", default="normalized_candidates")
    parser.add_argument("--source-collection", default="source_1st_resumes")
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument("--embedding-version", default=EMBEDDING_VERSION_DEFAULT)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--snapshot-version", default="")
    parser.add_argument("--openai-api-key", default="")
    parser.add_argument("--milvus-uri", default="")
    parser.add_argument("--milvus-token", default="")
    parser.add_argument("--milvus-db-name", default="")
    parser.add_argument("--milvus-candidate-collection", default="")
    parser.add_argument("--milvus-metric-type", default="COSINE")
    parser.add_argument("--milvus-index-type", default="HNSW")
    parser.add_argument("--milvus-index-m", type=int, default=32)
    parser.add_argument("--milvus-index-ef-construction", type=int, default=200)
    parser.add_argument("--milvus-search-ef", type=int, default=128)
    parser.add_argument("--overwrite-snapshot", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--summary-out", default="script/pipeline_mongo/candidate_search_publish_report.json")
    return parser.parse_args()


def resolve_snapshot_version(snapshot_version: str) -> str:
    text = normalize_spaces(snapshot_version)
    if not text:
        now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        text = f"{DEFAULT_SNAPSHOT_PREFIX}_{now}"
    if not SAFE_SNAPSHOT_RE.match(text):
        raise PublishError(
            "snapshot_version contains unsafe characters. Allowed: A-Z a-z 0-9 . _ -"
        )
    return text


def sorted_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [row for row in (candidates or []) if isinstance(row, dict)]

    def key(row: dict[str, Any]) -> tuple[int, float]:
        rank = safe_int(row.get("rank"))
        confidence = row.get("confidence")
        conf = float(confidence) if isinstance(confidence, (int, float)) else 0.0
        return (rank if rank is not None else 10**9, -conf)

    return sorted(rows, key=key)


def collect_candidate_labels(
    candidates: list[dict[str, Any]],
    field_name: str,
    cap: int,
) -> list[str]:
    rows = sorted_candidates(candidates)
    values = [normalize_spaces(str(row.get(field_name) or "")) for row in rows]
    return unique_strings(values)[:cap]


def collect_esco_ids(candidates: list[dict[str, Any]]) -> list[str]:
    rows = sorted_candidates(candidates)
    ids: list[str] = []
    seen: set[str] = set()
    for row in rows:
        esco_id = normalize_spaces(str(row.get("esco_id") or ""))
        if not esco_id or esco_id in seen:
            continue
        seen.add(esco_id)
        ids.append(esco_id)
    return ids


def industry_source_occupation_candidates(
    occupation_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = sorted_candidates(occupation_candidates)
    if not rows:
        return []

    primary_index: int | None = None
    for index, row in enumerate(rows):
        if bool(row.get("is_primary")):
            primary_index = index
            break
    if primary_index is None:
        return rows

    primary = rows[primary_index]
    others = [row for index, row in enumerate(rows) if index != primary_index]
    return [primary] + others


def collect_industry_esco_ids(occupation_candidates: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for occupation_row in industry_source_occupation_candidates(occupation_candidates):
        hierarchy = occupation_row.get("hierarchy_json") or []
        if not isinstance(hierarchy, list):
            continue
        for row in hierarchy:
            item = row if isinstance(row, dict) else {}
            industry_esco_id = normalize_spaces(str(item.get("id") or ""))
            if not industry_esco_id or industry_esco_id in seen:
                continue
            if not industry_esco_id.lower().startswith(ESCO_ISCO_PREFIX):
                continue
            seen.add(industry_esco_id)
            ids.append(industry_esco_id)
    return ids


def pick_industry_esco_id(occupation_candidates: list[dict[str, Any]]) -> str | None:
    ids = collect_industry_esco_ids(occupation_candidates)
    if not ids:
        return None
    return ids[0]


def derive_experience_total(experiences: list[dict[str, Any]]) -> int | None:
    durations: list[int] = []
    for row in experiences or []:
        if not isinstance(row, dict):
            continue
        value = safe_int(row.get("duration_months"))
        if value is None:
            continue
        durations.append(value)
    if not durations:
        return None
    return sum(durations)


def degree_rank(degree: str, field_of_study: str) -> int:
    text = normalize_text(f"{degree} {field_of_study}")
    if not text:
        return 0

    if any(token in text for token in ["doctorate", "doctoral", "phd", "dphil", "md", "jd"]):
        return 5
    if any(
        token in text
        for token in [
            "master",
            "m.sc",
            "msc",
            "m.s.",
            "m.s ",
            "ms ",
            "m.a.",
            "ma ",
            "mba",
            "m.eng",
            "meng",
        ]
    ):
        return 4
    if any(
        token in text
        for token in [
            "bachelor",
            "b.sc",
            "bsc",
            "b.s.",
            "b.s ",
            "bs ",
            "b.a.",
            "ba ",
            "b.eng",
            "beng",
            "undergraduate",
        ]
    ):
        return 3
    if any(token in text for token in ["associate", "diploma", "certificate", "certification"]):
        return 2
    if any(token in text for token in ["high school", "secondary", "secondary school"]):
        return 1
    return 0


def derive_education_rank(educations: list[dict[str, Any]]) -> int:
    rows = educations or []
    if not rows:
        return 0

    max_rank = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        rank = degree_rank(
            degree=str(row.get("degree") or ""),
            field_of_study=str(row.get("field_of_study") or ""),
        )
        if rank > max_rank:
            max_rank = rank
    return max_rank


def truncate_text(text: str, max_chars: int = 200) -> str:
    value = normalize_spaces(text)
    if not value:
        return ""
    if len(value) > max_chars:
        value = value[: max_chars - 3].rstrip() + "..."
    return value


def date_rank(value: Any) -> int:
    text = normalize_spaces(str(value or ""))
    if not text:
        return 0

    lowered = text.lower()
    if lowered in PRESENT_DATE_TOKENS:
        return 99991231

    normalized = lowered.replace("/", "-").replace(".", "-")
    ym_match = re.match(r"^(\d{4})-(\d{1,2})(?:-(\d{1,2}))?$", normalized)
    if ym_match:
        year = int(ym_match.group(1))
        month = int(ym_match.group(2))
        day = int(ym_match.group(3) or 1)
        month = min(max(month, 1), 12)
        day = min(max(day, 1), 31)
        return year * 10000 + month * 100 + day

    year_match = re.match(r"^(\d{4})$", normalized)
    if year_match:
        return int(year_match.group(1)) * 10000 + 101

    any_year = re.search(r"(19|20)\d{2}", normalized)
    if any_year:
        return int(any_year.group(0)) * 10000 + 101

    return 0


def sorted_recent_experiences(experiences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [row for row in (experiences or []) if isinstance(row, dict)]

    def key(row: dict[str, Any]) -> tuple[int, int, int]:
        return (
            1 if bool(row.get("is_current")) else 0,
            date_rank(row.get("end_date")),
            date_rank(row.get("start_date")),
        )

    return sorted(rows, key=key, reverse=True)


def split_sentences(text: str) -> list[str]:
    value = normalize_spaces(text)
    if not value:
        return []
    parts = re.split(r"(?<=[.!?])\s+", value)
    out: list[str] = []
    for part in parts:
        sentence = normalize_spaces(part)
        if sentence:
            out.append(sentence)
    return out


def is_skill_bearing_sentence(sentence: str, skill_anchor_terms: set[str]) -> bool:
    normalized_sentence = normalize_text(sentence)
    if not normalized_sentence:
        return False

    for term in skill_anchor_terms:
        if term and term in normalized_sentence:
            return True

    return any(hint in normalized_sentence for hint in SKILL_CONTEXT_HINTS)


def pick_skill_bearing_snippet(
    text: str,
    skill_anchor_terms: set[str],
    max_chars: int = 180,
) -> str:
    for sentence in split_sentences(text):
        if is_skill_bearing_sentence(sentence, skill_anchor_terms):
            return truncate_text(sentence, max_chars=max_chars)
    return ""


def source_skill_phrases(source_doc: dict[str, Any]) -> list[str]:
    extracted = source_doc.get("extracted_fields") if isinstance(source_doc, dict) else None
    if not isinstance(extracted, dict):
        return []
    skills = extracted.get("skills")
    if not isinstance(skills, list):
        return []

    values: list[str] = []
    for row in skills:
        if isinstance(row, dict):
            text = normalize_spaces(str(row.get("raw_text") or ""))
            if text:
                values.append(text)
    return unique_strings(values)


def source_occupation_phrases(source_doc: dict[str, Any]) -> list[str]:
    extracted = source_doc.get("extracted_fields") if isinstance(source_doc, dict) else None
    if not isinstance(extracted, dict):
        return []
    raw = extracted.get("occupation_candidates")
    if not isinstance(raw, list):
        return []
    values = [normalize_spaces(str(v)) for v in raw if isinstance(v, str)]
    return unique_strings(values)


def source_name_title(source_doc: dict[str, Any]) -> str:
    extracted = source_doc.get("extracted_fields") if isinstance(source_doc, dict) else None
    if not isinstance(extracted, dict):
        return ""
    return normalize_spaces(str(extracted.get("name_title") or ""))


def build_skill_text(
    normalized_doc: dict[str, Any],
    source_doc: dict[str, Any] | None,
) -> str:
    skill_candidates = normalized_doc.get("skill_candidates") or []
    occupation_candidates = normalized_doc.get("occupation_candidates") or []
    experiences = sorted_recent_experiences(normalized_doc.get("experiences") or [])

    skill_labels = collect_candidate_labels(skill_candidates, "preferred_label", cap=12)
    skill_raw = collect_candidate_labels(skill_candidates, "raw_text", cap=12)
    source_skill_raw = source_skill_phrases(source_doc or {})[:20]
    skill_anchor_terms: set[str] = set()
    for value in skill_labels + skill_raw + source_skill_raw:
        normalized_value = normalize_text(value)
        if normalized_value:
            skill_anchor_terms.add(normalized_value)

    exp_titles: list[str] = []
    exp_snippets: list[str] = []
    for row in experiences:
        title = normalize_spaces(str(row.get("title") or ""))
        if title:
            exp_titles.append(title)
        snippet = pick_skill_bearing_snippet(
            str(row.get("description_raw") or ""),
            skill_anchor_terms=skill_anchor_terms,
            max_chars=180,
        )
        if snippet:
            exp_snippets.append(snippet)
        if len(exp_titles) >= 3 and len(exp_snippets) >= 3:
            break
    exp_titles = unique_strings(exp_titles)[:3]
    exp_snippets = unique_strings(exp_snippets)[:3]

    occ_anchor = collect_candidate_labels(occupation_candidates, "preferred_label", cap=2)

    parts: list[str] = []
    if skill_labels:
        parts.append("skills: " + "; ".join(skill_labels))
    if skill_raw:
        parts.append("raw_skills: " + "; ".join(skill_raw))
    if source_skill_raw:
        parts.append("source_skills: " + "; ".join(source_skill_raw))
    if exp_titles:
        parts.append("recent_titles: " + "; ".join(exp_titles))
    if exp_snippets:
        parts.append("skill_context: " + " | ".join(exp_snippets))
    if occ_anchor:
        parts.append("occupation_anchor: " + "; ".join(occ_anchor))

    text = compact_text("\n".join(parts))
    if not text:
        text = "skills: unknown"
    return text


def build_occupation_text(
    normalized_doc: dict[str, Any],
    source_doc: dict[str, Any] | None,
) -> str:
    occupation_candidates = sorted_candidates(normalized_doc.get("occupation_candidates") or [])
    experiences = sorted_recent_experiences(normalized_doc.get("experiences") or [])

    occ_labels = collect_candidate_labels(occupation_candidates, "preferred_label", cap=3)
    occ_raw = collect_candidate_labels(occupation_candidates, "raw_text", cap=3)

    hierarchy_labels: list[str] = []
    for row in occupation_candidates[:3]:
        hierarchy = row.get("hierarchy_json") or []
        if not isinstance(hierarchy, list):
            continue
        for item in hierarchy:
            if not isinstance(item, dict):
                continue
            label = normalize_spaces(str(item.get("label") or ""))
            if label:
                hierarchy_labels.append(label)
    hierarchy_labels = unique_strings(hierarchy_labels)[:12]

    source_occ = source_occupation_phrases(source_doc or {})[:5]
    headline = source_name_title(source_doc or {})

    exp_titles: list[str] = []
    exp_raw_titles: list[str] = []
    for row in experiences:
        title = normalize_spaces(str(row.get("title") or ""))
        raw_title = normalize_spaces(str(row.get("raw_title") or ""))
        if title:
            exp_titles.append(title)
        if raw_title:
            exp_raw_titles.append(raw_title)
        if len(exp_titles) >= 5 and len(exp_raw_titles) >= 5:
            break
    exp_titles = unique_strings(exp_titles)[:5]
    exp_raw_titles = unique_strings(exp_raw_titles)[:5]

    parts: list[str] = []
    if occ_labels:
        parts.append("occupations: " + "; ".join(occ_labels))
    if hierarchy_labels:
        parts.append("occupation_hierarchy: " + " > ".join(hierarchy_labels))
    if occ_raw:
        parts.append("raw_occupations: " + "; ".join(occ_raw))
    if source_occ:
        parts.append("source_occupations: " + "; ".join(source_occ))
    if exp_titles:
        parts.append("recent_titles: " + "; ".join(exp_titles))
    if exp_raw_titles:
        parts.append("recent_raw_titles: " + "; ".join(exp_raw_titles))
    if headline:
        parts.append("headline: " + headline)

    text = compact_text("\n".join(parts))
    if not text:
        text = "occupation: unknown"
    return text


def build_source_lookup(
    db: Any,
    source_collection: str,
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, int]]:
    projection = {
        "_id": 0,
        "source_dataset": 1,
        "source_record_id": 1,
        "extracted_fields.skills.raw_text": 1,
        "extracted_fields.occupation_candidates": 1,
        "extracted_fields.name_title": 1,
    }
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    stats = {
        "source_docs": 0,
        "duplicate_source_keys": 0,
    }

    for doc in db[source_collection].find({}, projection):
        stats["source_docs"] += 1
        source_dataset = normalize_spaces(str(doc.get("source_dataset") or ""))
        source_record_id = normalize_spaces(str(doc.get("source_record_id") or ""))
        if not source_dataset or not source_record_id:
            continue
        key = (source_dataset, source_record_id)
        if key in lookup:
            stats["duplicate_source_keys"] += 1
            continue
        lookup[key] = doc
    return lookup, stats


def build_publish_records(
    db: Any,
    normalized_collection: str,
    source_lookup: dict[tuple[str, str], dict[str, Any]],
    snapshot_version: str,
    embedding_model: str,
    embedding_version: str,
) -> tuple[list[CandidatePublishRecord], dict[str, Any]]:
    projection = {
        "_id": 1,
        "candidate_id": 1,
        "source_dataset": 1,
        "source_record_id": 1,
        "normalizer_version": 1,
        "normalization_status": 1,
        "category": 1,
        "current_location": 1,
        "occupation_candidates": 1,
        "skill_candidates": 1,
        "experiences": 1,
        "educations": 1,
    }

    records: list[CandidatePublishRecord] = []
    seen_vector_doc_id: set[str] = set()
    stats: dict[str, Any] = {
        "normalized_docs": 0,
        "status_counts": {},
        "missing_source_docs": 0,
        "empty_occupation_esco_ids_docs": 0,
        "empty_skill_esco_ids_docs": 0,
        "empty_both_esco_ids_docs": 0,
        "empty_industry_esco_ids_docs": 0,
        "missing_candidate_id_docs": 0,
        "null_industry_esco_id_docs": 0,
        "null_experience_months_total_docs": 0,
        "unknown_education_rank_docs": 0,
    }

    for doc in db[normalized_collection].find({}, projection):
        stats["normalized_docs"] += 1

        status = normalize_spaces(str(doc.get("normalization_status") or "unknown"))
        status_counts = stats["status_counts"]
        status_counts[status] = int(status_counts.get(status, 0)) + 1

        candidate_id = normalize_spaces(str(doc.get("candidate_id") or ""))
        if not candidate_id:
            stats["missing_candidate_id_docs"] += 1
            raise PublishError("Found normalized doc without candidate_id; aborting full publish.")

        normalized_doc_id = normalize_spaces(str(doc.get("_id") or ""))
        source_dataset = normalize_spaces(str(doc.get("source_dataset") or ""))
        source_record_id = normalize_spaces(str(doc.get("source_record_id") or ""))
        if not source_dataset or not source_record_id:
            raise PublishError(
                f"Missing source key on normalized doc candidate_id={candidate_id} _id={normalized_doc_id}"
            )

        source_doc = source_lookup.get((source_dataset, source_record_id))
        if source_doc is None:
            stats["missing_source_docs"] += 1

        occupation_candidates = doc.get("occupation_candidates") or []
        skill_candidates = doc.get("skill_candidates") or []
        experiences = doc.get("experiences") or []
        educations = doc.get("educations") or []

        occupation_esco_ids = collect_esco_ids(occupation_candidates)
        skill_esco_ids = collect_esco_ids(skill_candidates)
        if not occupation_esco_ids:
            stats["empty_occupation_esco_ids_docs"] += 1
        if not skill_esco_ids:
            stats["empty_skill_esco_ids_docs"] += 1
        if not occupation_esco_ids and not skill_esco_ids:
            stats["empty_both_esco_ids_docs"] += 1

        industry_esco_ids = collect_industry_esco_ids(occupation_candidates)
        industry_esco_id = pick_industry_esco_id(occupation_candidates)
        experience_months_total = derive_experience_total(experiences)
        education_rank = derive_education_rank(educations)
        if not industry_esco_ids:
            stats["empty_industry_esco_ids_docs"] += 1
        if industry_esco_id is None:
            stats["null_industry_esco_id_docs"] += 1
        if experience_months_total is None:
            stats["null_experience_months_total_docs"] += 1
        if education_rank == 0:
            stats["unknown_education_rank_docs"] += 1

        vector_doc_id = f"{snapshot_version}:{candidate_id}"
        if vector_doc_id in seen_vector_doc_id:
            raise PublishError(f"Duplicate vector_doc_id generated: {vector_doc_id}")
        seen_vector_doc_id.add(vector_doc_id)

        record = CandidatePublishRecord(
            vector_doc_id=vector_doc_id,
            candidate_id=candidate_id,
            normalized_doc_id=normalized_doc_id,
            source_dataset=source_dataset,
            source_record_id=source_record_id,
            snapshot_version=snapshot_version,
            normalizer_version=normalize_spaces(str(doc.get("normalizer_version") or "")),
            embedding_model=embedding_model,
            embedding_version=embedding_version,
            skill_text=build_skill_text(doc, source_doc),
            occupation_text=build_occupation_text(doc, source_doc),
            category=normalize_spaces(str(doc.get("category") or "")),
            industry_esco_id=industry_esco_id,
            industry_esco_ids_json=industry_esco_ids,
            occupation_esco_ids_json=occupation_esco_ids,
            skill_esco_ids_json=skill_esco_ids,
            experience_months_total=experience_months_total,
            highest_education_level_rank=education_rank,
            current_location=normalize_spaces(str(doc.get("current_location") or "")),
            normalization_status=status,
        )
        records.append(record)

    return records, stats


def embed_batch(openai_client: Any, model: str, texts: list[str]) -> list[list[float]]:
    response = openai_client.embeddings.create(
        model=model,
        input=texts,
    )
    data = sorted(getattr(response, "data", []), key=lambda item: getattr(item, "index", 0))
    vectors: list[list[float]] = []
    for item in data:
        embedding = list(getattr(item, "embedding", []) or [])
        if not embedding:
            raise PublishError("OpenAI embedding response contained empty vector.")
        vectors.append(embedding)
    if len(vectors) != len(texts):
        raise PublishError("OpenAI embedding response size mismatch.")
    return vectors


def embed_batch_with_retry(
    openai_client: Any,
    model: str,
    texts: list[str],
    max_attempts: int = 5,
) -> list[list[float]]:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return embed_batch(openai_client=openai_client, model=model, texts=texts)
        except Exception as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            wait_sec = min(8.0, 0.8 * (2 ** (attempt - 1)))
            print(f"[embed] attempt {attempt} failed; retrying in {wait_sec:.1f}s: {exc}")
            time.sleep(wait_sec)
    raise PublishError(f"Embedding batch failed after {max_attempts} attempts: {last_error}")


def create_candidate_collection(
    collection_name: str,
    vector_dim: int,
    metric_type: str,
    index_type: str,
    index_m: int,
    index_ef_construction: int,
) -> Any:
    if Collection is None or CollectionSchema is None or FieldSchema is None or DataType is None:
        raise PublishError("pymilvus is not installed.")
    if utility is None:
        raise PublishError("pymilvus.utility is not available.")

    if utility.has_collection(collection_name):
        coll = Collection(collection_name)
        expected_fields = {
            "vector_doc_id",
            "candidate_id",
            "normalized_doc_id",
            "source_dataset",
            "source_record_id",
            "snapshot_version",
            "normalizer_version",
            "embedding_model",
            "embedding_version",
            "skill_vector",
            "occupation_vector",
            "category",
            "industry_esco_id",
            "industry_esco_ids_json",
            "occupation_esco_ids_json",
            "skill_esco_ids_json",
            "experience_months_total",
            "highest_education_level_rank",
            "current_location",
        }
        existing_fields = {f.name for f in coll.schema.fields}
        missing = sorted(expected_fields - existing_fields)
        if missing:
            raise PublishError(
                f"Existing Milvus collection is missing required fields: {missing}"
            )
        field_by_name = {f.name: f for f in coll.schema.fields}
        nullable_required = {
            "industry_esco_id",
            "experience_months_total",
        }
        not_nullable = sorted(
            name
            for name in nullable_required
            if not bool(getattr(field_by_name.get(name), "nullable", False))
        )
        if not_nullable:
            raise PublishError(
                "Existing Milvus collection has non-nullable fields that must allow null values: "
                f"{not_nullable}. Recreate collection (or use a new collection name) before publishing."
            )
        return coll

    fields = [
        FieldSchema(name="vector_doc_id", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=256),
        FieldSchema(name="candidate_id", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="normalized_doc_id", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="source_dataset", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="source_record_id", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="snapshot_version", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="normalizer_version", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="embedding_model", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="embedding_version", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="skill_vector", dtype=DataType.FLOAT_VECTOR, dim=vector_dim),
        FieldSchema(name="occupation_vector", dtype=DataType.FLOAT_VECTOR, dim=vector_dim),
        FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="industry_esco_id", dtype=DataType.VARCHAR, max_length=256, nullable=True),
        FieldSchema(name="industry_esco_ids_json", dtype=DataType.JSON),
        FieldSchema(name="occupation_esco_ids_json", dtype=DataType.JSON),
        FieldSchema(name="skill_esco_ids_json", dtype=DataType.JSON),
        FieldSchema(name="experience_months_total", dtype=DataType.INT64, nullable=True),
        FieldSchema(name="highest_education_level_rank", dtype=DataType.INT64),
        FieldSchema(name="current_location", dtype=DataType.VARCHAR, max_length=256),
    ]
    schema = CollectionSchema(fields=fields, description="Candidate search serving collection (PR-06)")
    coll = Collection(name=collection_name, schema=schema)

    index_params = {
        "index_type": index_type,
        "metric_type": metric_type,
        "params": {
            "M": max(4, index_m),
            "efConstruction": max(8, index_ef_construction),
        },
    }
    coll.create_index(field_name="skill_vector", index_params=index_params)
    coll.create_index(field_name="occupation_vector", index_params=index_params)
    return coll


def ensure_indexes(
    collection: Any,
    metric_type: str,
    index_type: str,
    index_m: int,
    index_ef_construction: int,
) -> None:
    existing_fields: set[str] = set()
    for idx in getattr(collection, "indexes", []) or []:
        field_name = getattr(idx, "field_name", "")
        if field_name:
            existing_fields.add(field_name)

    params = {
        "index_type": index_type,
        "metric_type": metric_type,
        "params": {
            "M": max(4, index_m),
            "efConstruction": max(8, index_ef_construction),
        },
    }
    if "skill_vector" not in existing_fields:
        collection.create_index(field_name="skill_vector", index_params=params)
    if "occupation_vector" not in existing_fields:
        collection.create_index(field_name="occupation_vector", index_params=params)


def snapshot_expr(snapshot_version: str) -> str:
    # snapshot_version is validated with SAFE_SNAPSHOT_RE beforehand.
    return f'snapshot_version == "{snapshot_version}"'


def snapshot_exists(collection: Any, snapshot_version: str) -> bool:
    rows = collection.query(
        expr=snapshot_expr(snapshot_version),
        output_fields=["vector_doc_id"],
        limit=1,
    )
    return bool(rows)


def delete_snapshot_rows(collection: Any, snapshot_version: str) -> None:
    collection.delete(expr=snapshot_expr(snapshot_version))
    collection.flush()


def insert_batch(
    collection: Any,
    records: list[CandidatePublishRecord],
    skill_vectors: list[list[float]],
    occupation_vectors: list[list[float]],
) -> None:
    if len(records) != len(skill_vectors) or len(records) != len(occupation_vectors):
        raise PublishError("Insert payload size mismatch.")

    vector_doc_ids = [r.vector_doc_id for r in records]
    candidate_ids = [r.candidate_id for r in records]
    normalized_doc_ids = [r.normalized_doc_id for r in records]
    source_datasets = [r.source_dataset for r in records]
    source_record_ids = [r.source_record_id for r in records]
    snapshot_versions = [r.snapshot_version for r in records]
    normalizer_versions = [r.normalizer_version for r in records]
    embedding_models = [r.embedding_model for r in records]
    embedding_versions = [r.embedding_version for r in records]
    categories = [r.category for r in records]
    industry_esco_ids = [r.industry_esco_id for r in records]
    industry_esco_ids_json = [r.industry_esco_ids_json for r in records]
    occupation_esco_ids = [r.occupation_esco_ids_json for r in records]
    skill_esco_ids = [r.skill_esco_ids_json for r in records]
    experience_totals = [r.experience_months_total for r in records]
    education_ranks = [r.highest_education_level_rank for r in records]
    current_locations = [r.current_location for r in records]

    collection.insert(
        [
            vector_doc_ids,
            candidate_ids,
            normalized_doc_ids,
            source_datasets,
            source_record_ids,
            snapshot_versions,
            normalizer_versions,
            embedding_models,
            embedding_versions,
            skill_vectors,
            occupation_vectors,
            categories,
            industry_esco_ids,
            industry_esco_ids_json,
            occupation_esco_ids,
            skill_esco_ids,
            experience_totals,
            education_ranks,
            current_locations,
        ]
    )


def publish_records(
    collection: Any,
    records: list[CandidatePublishRecord],
    openai_client: Any,
    embedding_model: str,
    batch_size: int,
    snapshot_version: str,
) -> dict[str, Any]:
    inserted = 0
    started_at = datetime.now(timezone.utc)
    try:
        for start in range(0, len(records), batch_size):
            chunk = records[start : start + batch_size]
            skill_texts = [r.skill_text for r in chunk]
            occupation_texts = [r.occupation_text for r in chunk]

            skill_vectors = embed_batch_with_retry(
                openai_client=openai_client,
                model=embedding_model,
                texts=skill_texts,
            )
            occupation_vectors = embed_batch_with_retry(
                openai_client=openai_client,
                model=embedding_model,
                texts=occupation_texts,
            )
            insert_batch(
                collection=collection,
                records=chunk,
                skill_vectors=skill_vectors,
                occupation_vectors=occupation_vectors,
            )
            inserted += len(chunk)
            if inserted % (batch_size * 5) == 0 or inserted == len(records):
                print(f"[publish] inserted {inserted}/{len(records)}")

        collection.flush()
        collection.load()
        return {
            "inserted": inserted,
            "snapshot_version": snapshot_version,
            "started_at_utc": started_at.isoformat(),
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "rolled_back": False,
        }
    except Exception as exc:
        print(f"[publish] failed after {inserted} rows; rolling back snapshot={snapshot_version}: {exc}")
        try:
            delete_snapshot_rows(collection=collection, snapshot_version=snapshot_version)
            print(f"[publish] rollback completed for snapshot={snapshot_version}")
        except Exception as rollback_exc:
            raise PublishError(
                f"Publish failed and rollback failed for snapshot={snapshot_version}: {rollback_exc}"
            ) from exc
        raise


def main() -> None:
    args = parse_args()

    env_path = Path(__file__).resolve().parent / ".env"
    if load_dotenv is not None and env_path.exists():
        load_dotenv(env_path)

    openai_api_key = args.openai_api_key or os.getenv("OPENAI_API_KEY", "")
    milvus_uri = args.milvus_uri or os.getenv("MILVUS_URI", "")
    milvus_token = args.milvus_token or os.getenv("MILVUS_TOKEN", "")
    milvus_db_name = args.milvus_db_name or os.getenv("MILVUS_DB_NAME", "")
    milvus_candidate_collection = args.milvus_candidate_collection or os.getenv(
        "MILVUS_CANDIDATE_COLLECTION",
        "candidate_search_collection",
    )

    snapshot_version = resolve_snapshot_version(args.snapshot_version)

    summary: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mongo_db": args.db_name,
        "normalized_collection": args.normalized_collection,
        "source_collection": args.source_collection,
        "snapshot_version": snapshot_version,
        "embedding_model": args.embedding_model,
        "embedding_version": args.embedding_version,
        "batch_size": max(1, args.batch_size),
        "dry_run": args.dry_run,
        "milvus": {
            "uri_configured": bool(milvus_uri),
            "db_name": milvus_db_name,
            "collection": milvus_candidate_collection,
            "metric_type": args.milvus_metric_type,
            "index_type": args.milvus_index_type,
            "index_m": args.milvus_index_m,
            "index_ef_construction": args.milvus_index_ef_construction,
            "search_ef": args.milvus_search_ef,
            "overwrite_snapshot": args.overwrite_snapshot,
        },
    }

    mongo = MongoClient(args.mongo_uri)
    db = mongo[args.db_name]

    source_lookup, source_stats = build_source_lookup(
        db=db,
        source_collection=args.source_collection,
    )
    records, build_stats = build_publish_records(
        db=db,
        normalized_collection=args.normalized_collection,
        source_lookup=source_lookup,
        snapshot_version=snapshot_version,
        embedding_model=args.embedding_model,
        embedding_version=args.embedding_version,
    )

    summary["source_lookup"] = source_stats
    summary["build_stats"] = build_stats
    summary["counts"] = {
        "records": len(records),
        "missing_source_docs": build_stats["missing_source_docs"],
        "empty_occupation_esco_ids_docs": build_stats["empty_occupation_esco_ids_docs"],
        "empty_skill_esco_ids_docs": build_stats["empty_skill_esco_ids_docs"],
        "empty_both_esco_ids_docs": build_stats["empty_both_esco_ids_docs"],
        "empty_industry_esco_ids_docs": build_stats["empty_industry_esco_ids_docs"],
        "null_industry_esco_id_docs": build_stats["null_industry_esco_id_docs"],
        "null_experience_months_total_docs": build_stats["null_experience_months_total_docs"],
        "unknown_education_rank_docs": build_stats["unknown_education_rank_docs"],
    }
    summary["preview"] = {
        "first_skill_text": records[0].skill_text[:500] if records else "",
        "first_occupation_text": records[0].occupation_text[:500] if records else "",
    }

    if args.dry_run:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        if OpenAI is None:
            raise PublishError("openai package is not installed.")
        if not openai_api_key:
            raise PublishError("OPENAI_API_KEY is not configured.")
        if connections is None or utility is None or Collection is None:
            raise PublishError("pymilvus package is not installed.")
        if not milvus_uri:
            raise PublishError("MILVUS_URI is not configured.")
        if not records:
            raise PublishError("No records to publish.")

        probe_client = OpenAI(api_key=openai_api_key)
        probe_vector = embed_batch_with_retry(
            openai_client=probe_client,
            model=args.embedding_model,
            texts=[records[0].skill_text],
        )[0]
        vector_dim = len(probe_vector)
        if vector_dim <= 0:
            raise PublishError("Invalid vector dimension from embedding probe.")

        connect_kwargs: dict[str, Any] = {"alias": "default", "uri": milvus_uri}
        if milvus_token:
            connect_kwargs["token"] = milvus_token
        if milvus_db_name:
            connect_kwargs["db_name"] = milvus_db_name
        connections.connect(**connect_kwargs)

        collection = create_candidate_collection(
            collection_name=milvus_candidate_collection,
            vector_dim=vector_dim,
            metric_type=args.milvus_metric_type,
            index_type=args.milvus_index_type,
            index_m=args.milvus_index_m,
            index_ef_construction=args.milvus_index_ef_construction,
        )
        ensure_indexes(
            collection=collection,
            metric_type=args.milvus_metric_type,
            index_type=args.milvus_index_type,
            index_m=args.milvus_index_m,
            index_ef_construction=args.milvus_index_ef_construction,
        )
        collection.load()

        if snapshot_exists(collection=collection, snapshot_version=snapshot_version):
            if args.overwrite_snapshot:
                print(f"[publish] existing snapshot found; deleting snapshot={snapshot_version}")
                delete_snapshot_rows(collection=collection, snapshot_version=snapshot_version)
            else:
                raise PublishError(
                    f"snapshot_version already exists: {snapshot_version}. "
                    "Use --overwrite-snapshot to replace."
                )

        publish_result = publish_records(
            collection=collection,
            records=records,
            openai_client=probe_client,
            embedding_model=args.embedding_model,
            batch_size=max(1, args.batch_size),
            snapshot_version=snapshot_version,
        )
        summary["publish_result"] = publish_result
        summary["vector_dim"] = vector_dim
        print(json.dumps(summary, indent=2, ensure_ascii=False))

    out_path = Path(args.summary_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Summary written: {out_path}")


if __name__ == "__main__":
    main()
