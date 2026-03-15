from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict
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

try:
    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
except Exception:
    Collection = None
    CollectionSchema = None
    DataType = None
    FieldSchema = None
    connections = None
    utility = None


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


def parse_alt_labels(row: dict[str, Any]) -> list[str]:
    alt = row.get("alt_labels_list")
    if isinstance(alt, list):
        return [normalize_spaces(v) for v in alt if isinstance(v, str)]

    raw = row.get("altLabels") or ""
    if not isinstance(raw, str):
        return []
    parts = []
    for chunk in raw.replace("|", "\n").splitlines():
        text = normalize_spaces(chunk)
        if text:
            parts.append(text)
    return unique_strings(parts)


def concept_uri(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def concept_label(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_spaces(value)
    return ""


def stable_int64(value: str) -> int:
    digest = hashlib.sha1(value.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False) & ((1 << 63) - 1)


def truncate_payload(text: str, max_len: int = 7800) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def build_broader_index(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        child = concept_uri(row, "concept_uri", "conceptUri")
        parent = concept_uri(row, "broader_uri", "broaderUri")
        parent_label = concept_label(row, "broader_label", "broaderLabel")
        if not child or not parent:
            continue
        out.setdefault(child, []).append({"id": parent, "label": parent_label})
    return out


def hierarchy_labels(concept_id: str, broader_index: dict[str, list[dict[str, str]]], max_depth: int = 6) -> list[str]:
    current = concept_id
    visited: set[str] = set()
    labels: list[str] = []
    depth = 0

    while current and current not in visited and depth < max_depth:
        visited.add(current)
        parents = broader_index.get(current) or []
        if not parents:
            break
        parent = parents[0]
        label = normalize_spaces(parent.get("label"))
        if label:
            labels.append(label)
        current = normalize_spaces(parent.get("id"))
        depth += 1

    return list(reversed(labels))


def build_label_map(rows: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in rows:
        cid = concept_uri(row, "concept_uri", "conceptUri")
        label = concept_label(row, "preferred_label", "preferredLabel")
        if cid and label:
            out[cid] = label
    return out


def build_essential_maps(
    relation_rows: list[dict[str, Any]],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    occ_to_skill: dict[str, list[str]] = defaultdict(list)
    skill_to_occ: dict[str, list[str]] = defaultdict(list)
    for row in relation_rows:
        rel = normalize_text(row.get("relationType"))
        if rel != "essential":
            continue
        occ = concept_uri(row, "occupation_uri", "occupationUri")
        skill = concept_uri(row, "skill_uri", "skillUri")
        if not occ or not skill:
            continue
        occ_to_skill[occ].append(skill)
        skill_to_occ[skill].append(occ)
    return occ_to_skill, skill_to_occ


def build_payload(
    concept_type: str,
    preferred: str,
    alt_labels: list[str],
    description: str,
    hierarchy: list[str],
    related_label_name: str,
    related_labels: list[str],
) -> str:
    lines: list[str] = [f"type: {concept_type}", f"preferred: {preferred}"]
    if alt_labels:
        lines.append("alt: " + "; ".join(alt_labels))
    if description:
        lines.append("description: " + description)
    if hierarchy:
        lines.append("hierarchy: " + " > ".join(hierarchy))
    if related_labels:
        lines.append(f"{related_label_name}: " + "; ".join(related_labels))
    return truncate_payload("\n".join(lines))


def build_occupation_records(
    occupation_rows: list[dict[str, Any]],
    broader_occ_rows: list[dict[str, Any]],
    relation_rows: list[dict[str, Any]],
    skill_label_map: dict[str, str],
    max_essential_skills: int,
) -> list[dict[str, Any]]:
    broader = build_broader_index(broader_occ_rows)
    occ_to_skill, _ = build_essential_maps(relation_rows)

    records: list[dict[str, Any]] = []
    for row in occupation_rows:
        esco_id = concept_uri(row, "concept_uri", "conceptUri")
        preferred = concept_label(row, "preferred_label", "preferredLabel")
        if not esco_id or not preferred:
            continue

        alt = parse_alt_labels(row)[:40]
        description = concept_label(row, "description", "definition")
        hierarchy = hierarchy_labels(esco_id, broader, max_depth=6)[:8]

        essential_skill_labels = unique_strings(
            [skill_label_map.get(skill_uri, "") for skill_uri in occ_to_skill.get(esco_id, [])]
        )[:max_essential_skills]

        payload = build_payload(
            concept_type="occupation",
            preferred=preferred,
            alt_labels=alt,
            description=description,
            hierarchy=hierarchy,
            related_label_name="essential_skills",
            related_labels=essential_skill_labels,
        )

        records.append(
            {
                "id": stable_int64(esco_id),
                "esco_id": esco_id,
                "preferred_label": preferred,
                "payload_text": payload,
            }
        )

    return records


def build_skill_records(
    skill_rows: list[dict[str, Any]],
    broader_skill_rows: list[dict[str, Any]],
    relation_rows: list[dict[str, Any]],
    occupation_label_map: dict[str, str],
    max_related_occupations: int,
) -> list[dict[str, Any]]:
    broader = build_broader_index(broader_skill_rows)
    _, skill_to_occ = build_essential_maps(relation_rows)

    records: list[dict[str, Any]] = []
    for row in skill_rows:
        esco_id = concept_uri(row, "concept_uri", "conceptUri")
        preferred = concept_label(row, "preferred_label", "preferredLabel")
        if not esco_id or not preferred:
            continue

        alt = parse_alt_labels(row)[:40]
        description = concept_label(row, "description", "definition")
        hierarchy = hierarchy_labels(esco_id, broader, max_depth=6)[:8]

        related_occ_labels = unique_strings(
            [occupation_label_map.get(occ_uri, "") for occ_uri in skill_to_occ.get(esco_id, [])]
        )[:max_related_occupations]

        payload = build_payload(
            concept_type="skill",
            preferred=preferred,
            alt_labels=alt,
            description=description,
            hierarchy=hierarchy,
            related_label_name="related_occupations_essential",
            related_labels=related_occ_labels,
        )

        records.append(
            {
                "id": stable_int64(esco_id),
                "esco_id": esco_id,
                "preferred_label": preferred,
                "payload_text": payload,
            }
        )

    return records


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
            raise RuntimeError("Received empty embedding vector from OpenAI")
        vectors.append(embedding)
    if len(vectors) != len(texts):
        raise RuntimeError("Embedding response size mismatch")
    return vectors


def create_vector_collection(
    collection_name: str,
    vector_dim: int,
    drop_existing: bool,
    metric_type: str,
) -> Any:
    if Collection is None or CollectionSchema is None or FieldSchema is None or DataType is None:
        raise RuntimeError("pymilvus is not installed")
    if utility is None:
        raise RuntimeError("pymilvus.utility is not available")

    if utility.has_collection(collection_name):
        if drop_existing:
            utility.drop_collection(collection_name)
        else:
            raise RuntimeError(
                f"Collection already exists: {collection_name}. Use --drop-existing to rebuild."
            )

    schema = CollectionSchema(
        fields=[
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=False),
            FieldSchema(name="esco_id", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="preferred_label", dtype=DataType.VARCHAR, max_length=1024),
            FieldSchema(name="payload_text", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=vector_dim),
        ],
        description="ESCO concept embedding index",
    )
    collection = Collection(name=collection_name, schema=schema)
    collection.create_index(
        field_name="vector",
        index_params={
            "index_type": "HNSW",
            "metric_type": metric_type,
            "params": {"M": 16, "efConstruction": 200},
        },
    )
    return collection


def insert_chunk(collection: Any, records: list[dict[str, Any]], vectors: list[list[float]]) -> None:
    ids = [int(r["id"]) for r in records]
    esco_ids = [str(r["esco_id"]) for r in records]
    labels = [str(r["preferred_label"]) for r in records]
    payloads = [str(r["payload_text"]) for r in records]
    collection.insert([ids, esco_ids, labels, payloads, vectors])


def write_collection(
    collection_name: str,
    records: list[dict[str, Any]],
    openai_client: Any,
    embedding_model: str,
    batch_size: int,
    drop_existing: bool,
    metric_type: str,
) -> dict[str, Any]:
    if not records:
        return {"collection": collection_name, "inserted": 0, "vector_dim": 0}

    first_batch = records[:batch_size]
    first_vectors = embed_batch(openai_client, embedding_model, [r["payload_text"] for r in first_batch])
    vector_dim = len(first_vectors[0])
    collection = create_vector_collection(collection_name, vector_dim, drop_existing, metric_type)

    total_inserted = 0
    insert_chunk(collection, first_batch, first_vectors)
    total_inserted += len(first_batch)
    print(f"[{collection_name}] inserted {total_inserted}/{len(records)}")

    for start in range(batch_size, len(records), batch_size):
        chunk = records[start : start + batch_size]
        vectors = embed_batch(openai_client, embedding_model, [r["payload_text"] for r in chunk])
        insert_chunk(collection, chunk, vectors)
        total_inserted += len(chunk)
        if total_inserted % (batch_size * 5) == 0 or total_inserted == len(records):
            print(f"[{collection_name}] inserted {total_inserted}/{len(records)}")

    collection.flush()
    collection.load()
    return {"collection": collection_name, "inserted": total_inserted, "vector_dim": vector_dim}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ESCO occupation/skill embedding collections in Milvus.")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db-name", default="prodapt_capstone")
    parser.add_argument("--occupation-source", default="raw_esco_occupations")
    parser.add_argument("--skill-source", default="raw_esco_skills")
    parser.add_argument("--broader-occ-source", default="raw_esco_broader_relations_occ")
    parser.add_argument("--broader-skill-source", default="raw_esco_broader_relations_skill")
    parser.add_argument("--relation-source", default="raw_esco_occupation_skill_relations")
    parser.add_argument("--max-essential-skills", type=int, default=20)
    parser.add_argument("--max-related-occupations", type=int, default=20)
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--openai-api-key", default="")
    parser.add_argument("--milvus-uri", default="")
    parser.add_argument("--milvus-token", default="")
    parser.add_argument("--milvus-db-name", default="")
    parser.add_argument("--milvus-occ-collection", default="")
    parser.add_argument("--milvus-skill-collection", default="")
    parser.add_argument("--milvus-metric-type", default="COSINE")
    parser.add_argument("--drop-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--summary-out", default="script/pipeline_mongo/milvus_build_report.json")
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
        "esco_occupation_embeddings",
    )
    milvus_skill_collection = args.milvus_skill_collection or os.getenv(
        "MILVUS_SKILL_COLLECTION",
        "esco_skill_embeddings",
    )

    client = MongoClient(args.mongo_uri)
    db = client[args.db_name]
    occupation_rows = list(db[args.occupation_source].find({}, {"_id": 0}))
    skill_rows = list(db[args.skill_source].find({}, {"_id": 0}))
    broader_occ_rows = list(db[args.broader_occ_source].find({}, {"_id": 0}))
    broader_skill_rows = list(db[args.broader_skill_source].find({}, {"_id": 0}))
    relation_rows = list(db[args.relation_source].find({}, {"_id": 0}))

    occupation_label_map = build_label_map(occupation_rows)
    skill_label_map = build_label_map(skill_rows)

    occupation_records = build_occupation_records(
        occupation_rows=occupation_rows,
        broader_occ_rows=broader_occ_rows,
        relation_rows=relation_rows,
        skill_label_map=skill_label_map,
        max_essential_skills=args.max_essential_skills,
    )
    skill_records = build_skill_records(
        skill_rows=skill_rows,
        broader_skill_rows=broader_skill_rows,
        relation_rows=relation_rows,
        occupation_label_map=occupation_label_map,
        max_related_occupations=args.max_related_occupations,
    )

    summary: dict[str, Any] = {
        "generated_at_utc": datetime.utcnow().isoformat(),
        "mongo_db": args.db_name,
        "embedding_model": args.embedding_model,
        "dry_run": args.dry_run,
        "counts": {
            "occupation_records": len(occupation_records),
            "skill_records": len(skill_records),
        },
        "milvus": {
            "uri_configured": bool(milvus_uri),
            "db_name": milvus_db_name,
            "occ_collection": milvus_occ_collection,
            "skill_collection": milvus_skill_collection,
            "metric_type": args.milvus_metric_type,
            "drop_existing": args.drop_existing,
        },
        "preview": {
            "occupation_payload": occupation_records[0]["payload_text"][:600] if occupation_records else "",
            "skill_payload": skill_records[0]["payload_text"][:600] if skill_records else "",
        },
    }

    if args.dry_run:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        if OpenAI is None:
            raise RuntimeError("openai package is not installed")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        if connections is None:
            raise RuntimeError("pymilvus package is not installed")
        if not milvus_uri:
            raise RuntimeError("MILVUS_URI is not configured")

        connect_kwargs: dict[str, Any] = {"alias": "default", "uri": milvus_uri}
        if milvus_token:
            connect_kwargs["token"] = milvus_token
        if milvus_db_name:
            connect_kwargs["db_name"] = milvus_db_name
        connections.connect(**connect_kwargs)

        openai_client = OpenAI(api_key=openai_api_key)
        occ_result = write_collection(
            collection_name=milvus_occ_collection,
            records=occupation_records,
            openai_client=openai_client,
            embedding_model=args.embedding_model,
            batch_size=max(1, args.batch_size),
            drop_existing=args.drop_existing,
            metric_type=args.milvus_metric_type,
        )
        skill_result = write_collection(
            collection_name=milvus_skill_collection,
            records=skill_records,
            openai_client=openai_client,
            embedding_model=args.embedding_model,
            batch_size=max(1, args.batch_size),
            drop_existing=args.drop_existing,
            metric_type=args.milvus_metric_type,
        )
        summary["write_result"] = {
            "occupation": occ_result,
            "skill": skill_result,
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))

    out_path = Path(args.summary_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Summary written: {out_path}")


if __name__ == "__main__":
    main()
