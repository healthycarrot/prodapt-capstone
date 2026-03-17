from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from bson import json_util
from pymongo import MongoClient


def fetch_normalized_candidates_raw(
    candidate_ids: list[str],
    candidate_final_scores: dict[str, float] | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Temporary direct Mongo fetch for debugging.
    Intentionally bypasses repository/common layers for easy removal.
    """
    if not candidate_ids:
        return []

    ranked_candidate_ids = list(dict.fromkeys(candidate_ids))
    if candidate_final_scores:
        ranked_candidate_ids = sorted(
            ranked_candidate_ids,
            key=lambda candidate_id: candidate_final_scores.get(candidate_id, float("-inf")),
            reverse=True,
        )
    if top_k > 0:
        ranked_candidate_ids = ranked_candidate_ids[:top_k]
    if not ranked_candidate_ids:
        return []

    _load_env_if_exists(Path(__file__).resolve().parents[3] / ".env")
    _load_env_if_exists(Path(__file__).resolve().parents[5] / "backend" / ".env")

    mongo_uri = os.getenv("MONGO_URI", "")
    db_name = os.getenv("MONGO_DB_NAME", "prodapt_capstone")
    collection_name = os.getenv("MONGO_NORMALIZED_COLLECTION", "normalized_candidates")

    if not mongo_uri:
        return []

    client = MongoClient(mongo_uri)
    collection = client[db_name][collection_name]
    rows = list(collection.find({"candidate_id": {"$in": ranked_candidate_ids}}))

    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        candidate_id = str(row.get("candidate_id") or "")
        if not candidate_id:
            continue
        # Extended JSON keeps Mongo-native structure as-is as much as possible.
        by_id[candidate_id] = json.loads(json_util.dumps(row, ensure_ascii=False))

    ordered: list[dict[str, Any]] = []
    for candidate_id in ranked_candidate_ids:
        if candidate_id in by_id:
            ordered.append(by_id[candidate_id])
    return ordered


def _load_env_if_exists(path: Path) -> None:
    if not path.exists():
        return
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
