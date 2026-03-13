from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection


REPO_ROOT = Path(__file__).resolve().parents[2]
ESCO_DIR = REPO_ROOT / "data" / "ESCO"
FIRST_DATA_CSV = REPO_ROOT / "data" / "1st_data" / "Resume" / "Resume.csv"


def configure_csv_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def normalize_text(value: str) -> str:
    return " ".join(value.lower().strip().split())


def split_labels(value: str) -> list[str]:
    if not value:
        return []
    chunks: list[str] = []
    for part in value.replace("|", "\n").splitlines():
        label = " ".join(part.strip().split())
        if label:
            chunks.append(label)
    # dedupe while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for item in chunks:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def bulk_replace(collection: Collection, docs: list[dict[str, Any]]) -> None:
    if not docs:
        return
    collection.delete_many({})
    collection.insert_many(docs)


def load_esco_collection(db, csv_name: str, collection_name: str) -> None:
    path = ESCO_DIR / csv_name
    rows = read_csv_rows(path)
    docs: list[dict[str, Any]] = []

    for row in rows:
        doc: dict[str, Any] = dict(row)

        if "preferredLabel" in row:
            doc["preferred_label"] = (row.get("preferredLabel") or "").strip()
            doc["preferred_label_normalized"] = normalize_text(doc["preferred_label"])

        if "altLabels" in row:
            alt_labels = split_labels(row.get("altLabels") or "")
            doc["alt_labels_list"] = alt_labels
            doc["alt_labels_normalized"] = [normalize_text(v) for v in alt_labels]

        if "hiddenLabels" in row:
            hidden_labels = split_labels(row.get("hiddenLabels") or "")
            doc["hidden_labels_list"] = hidden_labels
            doc["hidden_labels_normalized"] = [normalize_text(v) for v in hidden_labels]

        if "conceptUri" in row:
            doc["concept_uri"] = (row.get("conceptUri") or "").strip()

        if "occupationUri" in row:
            doc["occupation_uri"] = (row.get("occupationUri") or "").strip()

        if "skillUri" in row:
            doc["skill_uri"] = (row.get("skillUri") or "").strip()

        docs.append(doc)

    collection = db[collection_name]
    bulk_replace(collection, docs)

    # indexes
    if collection_name in {"raw_esco_occupations", "raw_esco_skills"}:
        collection.create_index("concept_uri", name="idx_concept_uri")
        collection.create_index("preferred_label_normalized", name="idx_pref_label_norm")
        collection.create_index("alt_labels_normalized", name="idx_alt_labels_norm")
    if collection_name == "raw_esco_occupation_skill_relations":
        collection.create_index([("occupation_uri", 1), ("relationType", 1)], name="idx_occ_rel")
        collection.create_index([("skill_uri", 1), ("relationType", 1)], name="idx_skill_rel")

    print(f"Loaded {collection_name}: {len(docs)} docs")


def load_first_dataset(db) -> None:
    rows = read_csv_rows(FIRST_DATA_CSV)
    docs: list[dict[str, Any]] = []

    for row in rows:
        source_record_id = (row.get("ID") or "").strip()
        docs.append(
            {
                "source_dataset": "1st_data",
                "source_record_id": source_record_id,
                "category": (row.get("Category") or "").strip(),
                "resume_text": row.get("Resume_str") or "",
                "resume_html": row.get("Resume_html") or "",
            }
        )

    collection = db["source_1st_resumes"]
    bulk_replace(collection, docs)
    collection.create_index(
        [("source_dataset", 1), ("source_record_id", 1)],
        unique=True,
        name="uq_source_dataset_record",
    )
    collection.create_index("category", name="idx_source_category")

    print(f"Loaded source_1st_resumes: {len(docs)} docs")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load ESCO and 1st_data CSV files into MongoDB.")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db-name", default="prodapt_capstone")
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop target collections before ingestion.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_csv_limit()

    client = MongoClient(args.mongo_uri)
    db = client[args.db_name]

    target_collections = [
        "raw_esco_occupations",
        "raw_esco_skills",
        "raw_esco_isco_groups",
        "raw_esco_skill_groups",
        "raw_esco_broader_relations_occ",
        "raw_esco_broader_relations_skill",
        "raw_esco_occupation_skill_relations",
        "source_1st_resumes",
    ]

    if args.drop_existing:
        for name in target_collections:
            db[name].drop()
        print("Dropped existing collections")

    load_esco_collection(db, "occupations_en.csv", "raw_esco_occupations")
    load_esco_collection(db, "skills_en.csv", "raw_esco_skills")
    load_esco_collection(db, "ISCOGroups_en.csv", "raw_esco_isco_groups")
    load_esco_collection(db, "skillGroups_en.csv", "raw_esco_skill_groups")
    load_esco_collection(db, "broaderRelationsOccPillar_en.csv", "raw_esco_broader_relations_occ")
    load_esco_collection(db, "broaderRelationsSkillPillar_en.csv", "raw_esco_broader_relations_skill")
    load_esco_collection(db, "occupationSkillRelations_en.csv", "raw_esco_occupation_skill_relations")

    load_first_dataset(db)

    print("Done.")


if __name__ == "__main__":
    main()
