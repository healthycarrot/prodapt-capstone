from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pymongo import MongoClient, UpdateOne

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


SEARCH_TEXT_VERSION = "issue16_search_text_backfill_v1"
DEFAULT_INDEX_NAME = "idx_search_text_text"


@dataclass(slots=True)
class BackfillStats:
    total_scanned: int = 0
    total_matched: int = 0
    total_modified: int = 0
    docs_updated: int = 0
    docs_unchanged: int = 0
    docs_empty_text: int = 0
    bulk_batches: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill normalized_candidates.search_text and create text index (idempotent)."
    )
    parser.add_argument("--mongo-uri", default="")
    parser.add_argument("--db-name", default="prodapt_capstone")
    parser.add_argument("--collection", default="normalized_candidates")
    parser.add_argument("--batch-size", type=int, default=300)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--create-text-index", action="store_true")
    parser.add_argument("--text-index-name", default=DEFAULT_INDEX_NAME)
    parser.add_argument("--summary-out", default="script/pipeline_mongo/backfill_candidate_search_text_report.json")
    return parser.parse_args()


def load_local_env() -> None:
    script_env = Path(__file__).resolve().parent / ".env"
    backend_env = Path(__file__).resolve().parents[2] / "backend" / ".env"

    if load_dotenv is not None:
        if script_env.exists():
            load_dotenv(script_env, override=False)
        if backend_env.exists():
            load_dotenv(backend_env, override=False)
        return

    for path in (script_env, backend_env):
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            os.environ.setdefault(key, value)


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def normalize_spaces(value: str | None) -> str:
    return " ".join((value or "").split())


def dedupe_strings(values: list[str]) -> list[str]:
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


def recency_key(exp: dict[str, Any]) -> tuple[int, str, str]:
    is_current = 1 if bool(exp.get("is_current")) else 0
    end_date = str(exp.get("end_date") or "")
    start_date = str(exp.get("start_date") or "")
    return (is_current, end_date, start_date)


def build_search_text(doc: dict[str, Any]) -> str:
    chunks: list[str] = []

    category = normalize_spaces(doc.get("category"))
    if category:
        chunks.append(category)

    location = normalize_spaces(doc.get("current_location"))
    if location:
        chunks.append(location)

    occupations = sorted(
        [item for item in (doc.get("occupation_candidates") or []) if isinstance(item, dict)],
        key=lambda item: (
            0 if bool(item.get("is_primary")) else 1,
            int(item.get("rank") or 9999),
        ),
    )
    for occ in occupations[:20]:
        label = normalize_spaces(occ.get("preferred_label"))
        raw = normalize_spaces(occ.get("raw_text"))
        if label:
            chunks.append(label)
        if raw:
            chunks.append(raw)

    skills = sorted(
        [item for item in (doc.get("skill_candidates") or []) if isinstance(item, dict)],
        key=lambda item: int(item.get("rank") or 9999),
    )
    for skill in skills[:60]:
        label = normalize_spaces(skill.get("preferred_label"))
        raw = normalize_spaces(skill.get("raw_text"))
        if label:
            chunks.append(label)
        if raw:
            chunks.append(raw)

    experiences = sorted(
        [item for item in (doc.get("experiences") or []) if isinstance(item, dict)],
        key=recency_key,
        reverse=True,
    )
    for exp in experiences[:6]:
        title = normalize_spaces(exp.get("title"))
        raw_title = normalize_spaces(exp.get("raw_title"))
        description_raw = normalize_spaces(exp.get("description_raw"))
        if title:
            chunks.append(title)
        if raw_title:
            chunks.append(raw_title)
        if description_raw:
            chunks.append(description_raw[:320])

    educations = [item for item in (doc.get("educations") or []) if isinstance(item, dict)]
    for edu in educations[:4]:
        degree = normalize_spaces(edu.get("degree"))
        field_of_study = normalize_spaces(edu.get("field_of_study"))
        if degree:
            chunks.append(degree)
        if field_of_study:
            chunks.append(field_of_study)

    deduped = dedupe_strings(chunks)
    if not deduped:
        fallback = normalize_spaces(doc.get("candidate_id")) or "unknown-candidate"
        return fallback

    text = " | ".join(deduped)
    # Keep tokenization stable and bounded for text index.
    return text[:12000]


def has_search_text_index(indexes: list[dict[str, Any]]) -> tuple[bool, str | None, str | None]:
    any_text_index = None
    for idx in indexes:
        key = idx.get("key", {})
        weights = idx.get("weights", {})
        key_is_text = isinstance(key, dict) and any(v == "text" for v in key.values())
        if key_is_text:
            any_text_index = idx.get("name")
            has_search_text_key = bool(isinstance(key, dict) and key.get("search_text") == "text")
            has_search_text_weight = bool(isinstance(weights, dict) and "search_text" in weights)
            if has_search_text_key or has_search_text_weight:
                return True, str(idx.get("name")), None
    if any_text_index:
        return False, None, str(any_text_index)
    return False, None, None


def run_backfill(args: argparse.Namespace) -> dict[str, Any]:
    load_local_env()
    mongo_uri = args.mongo_uri or os.getenv("MONGO_URI", "")
    db_name = args.db_name or os.getenv("MONGO_DB_NAME", "prodapt_capstone")
    collection_name = args.collection or os.getenv("MONGO_NORMALIZED_COLLECTION", "normalized_candidates")

    if not mongo_uri:
        raise RuntimeError("MONGO_URI is not configured.")

    client = MongoClient(mongo_uri)
    collection = client[db_name][collection_name]

    query: dict[str, Any] = {}
    projection = {
        "_id": 1,
        "candidate_id": 1,
        "category": 1,
        "current_location": 1,
        "occupation_candidates.preferred_label": 1,
        "occupation_candidates.raw_text": 1,
        "occupation_candidates.rank": 1,
        "occupation_candidates.is_primary": 1,
        "skill_candidates.preferred_label": 1,
        "skill_candidates.raw_text": 1,
        "skill_candidates.rank": 1,
        "experiences.title": 1,
        "experiences.raw_title": 1,
        "experiences.description_raw": 1,
        "experiences.start_date": 1,
        "experiences.end_date": 1,
        "experiences.is_current": 1,
        "educations.degree": 1,
        "educations.field_of_study": 1,
        "search_text": 1,
        "search_text_version": 1,
    }

    cursor = collection.find(query, projection=projection, no_cursor_timeout=True)
    if args.limit and args.limit > 0:
        cursor = cursor.limit(int(args.limit))

    now_iso = datetime.now(timezone.utc).isoformat()
    stats = BackfillStats()
    ops: list[UpdateOne] = []
    started_at = time.time()

    try:
        for doc in cursor:
            stats.total_scanned += 1
            new_text = build_search_text(doc)
            old_text = str(doc.get("search_text") or "")
            old_version = str(doc.get("search_text_version") or "")

            if not new_text.strip():
                stats.docs_empty_text += 1

            if old_text == new_text and old_version == SEARCH_TEXT_VERSION:
                stats.docs_unchanged += 1
                continue

            ops.append(
                UpdateOne(
                    {"_id": doc["_id"]},
                    {
                        "$set": {
                            "search_text": new_text,
                            "search_text_version": SEARCH_TEXT_VERSION,
                            "search_text_updated_at": now_iso,
                        }
                    },
                )
            )
            stats.docs_updated += 1

            if len(ops) >= max(1, int(args.batch_size)):
                result = collection.bulk_write(ops, ordered=False)
                stats.bulk_batches += 1
                stats.total_matched += int(result.matched_count)
                stats.total_modified += int(result.modified_count)
                ops.clear()

        if ops:
            result = collection.bulk_write(ops, ordered=False)
            stats.bulk_batches += 1
            stats.total_matched += int(result.matched_count)
            stats.total_modified += int(result.modified_count)
    finally:
        cursor.close()

    indexes = list(collection.list_indexes())
    index_exists, existing_name, conflicting_text_index = has_search_text_index(indexes)
    index_created = False
    index_error: str | None = None
    index_name = existing_name

    if args.create_text_index:
        if index_exists:
            pass
        elif conflicting_text_index:
            index_error = (
                "A different text index already exists on the collection "
                f"({conflicting_text_index}). MongoDB allows only one text index per collection."
            )
        else:
            try:
                index_name = collection.create_index(
                    [("search_text", "text")],
                    name=args.text_index_name or DEFAULT_INDEX_NAME,
                )
                index_created = True
                index_exists = True
            except Exception as exc:  # pragma: no cover
                index_error = f"{type(exc).__name__}: {exc}"

    duration_sec = round(time.time() - started_at, 3)
    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "db_name": db_name,
        "collection": collection_name,
        "search_text_version": SEARCH_TEXT_VERSION,
        "args": {
            "batch_size": int(args.batch_size),
            "limit": int(args.limit),
            "create_text_index": bool(args.create_text_index),
            "text_index_name": args.text_index_name,
        },
        "stats": {
            "total_scanned": stats.total_scanned,
            "docs_updated": stats.docs_updated,
            "docs_unchanged": stats.docs_unchanged,
            "docs_empty_text": stats.docs_empty_text,
            "bulk_batches": stats.bulk_batches,
            "bulk_matched": stats.total_matched,
            "bulk_modified": stats.total_modified,
        },
        "index": {
            "search_text_text_index_exists": bool(index_exists),
            "index_name": index_name,
            "index_created": bool(index_created),
            "conflicting_text_index": conflicting_text_index,
            "error": index_error,
        },
        "duration_sec": duration_sec,
    }
    return summary


def main() -> None:
    args = parse_args()
    summary = run_backfill(args)

    summary_out = Path(args.summary_out) if args.summary_out else None
    if summary_out:
        summary_out.parent.mkdir(parents=True, exist_ok=True)
        summary_out.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
