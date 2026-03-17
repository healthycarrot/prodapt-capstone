from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ..core.config import Settings, get_settings
from ..services.cross_encoder import CandidateTextRepo
from ..services.keyword_search import KeywordRepoHit, KeywordSearchRepo
from ..services.rerank import CandidateEscoRepo

try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
except Exception:  # pragma: no cover
    MongoClient = None
    Collection = Any  # type: ignore[assignment]


@dataclass(slots=True)
class MongoRepository(KeywordSearchRepo, CandidateTextRepo, CandidateEscoRepo):
    settings: Settings = field(default_factory=get_settings)
    _client: Any | None = field(default=None, init=False, repr=False)
    _db: Any | None = field(default=None, init=False, repr=False)

    def _ensure_db(self) -> Any:
        if MongoClient is None:
            raise RuntimeError("pymongo is not installed.")
        if self._db is not None:
            return self._db
        self._client = MongoClient(self.settings.mongo_uri)
        self._db = self._client[self.settings.mongo_db_name]
        return self._db

    def _normalized_collection(self) -> Collection:
        db = self._ensure_db()
        return db[self.settings.mongo_normalized_collection]

    def _source_collection(self) -> Collection:
        db = self._ensure_db()
        return db[self.settings.mongo_source_collection]

    def _guardrail_audit_collection(self) -> Collection:
        db = self._ensure_db()
        return db[self.settings.mongo_guardrail_audit_collection]

    def search(
        self,
        query: str,
        *,
        top_k: int,
        mongo_filter: dict[str, object] | None = None,
    ) -> Sequence[KeywordRepoHit]:
        if not query.strip():
            return []

        collection = self._normalized_collection()
        filter_doc: dict[str, Any] = dict(mongo_filter or {})
        filter_doc["$text"] = {"$search": query}

        cursor = (
            collection.find(
                filter_doc,
                {
                    "_id": 0,
                    "candidate_id": 1,
                    "score": {"$meta": "textScore"},
                },
            )
            .sort([("score", {"$meta": "textScore"})])
            .limit(top_k)
        )

        hits: list[KeywordRepoHit] = []
        for row in cursor:
            candidate_id = str(row.get("candidate_id") or "")
            if not candidate_id:
                continue
            score = _to_float(row.get("score"))
            hits.append(KeywordRepoHit(candidate_id=candidate_id, text_score=score))
        return hits

    def fetch_rerank_text(self, candidate_ids: Sequence[str]) -> Mapping[str, str]:
        if not candidate_ids:
            return {}
        collection = self._normalized_collection()
        cursor = collection.find(
            {"candidate_id": {"$in": list(candidate_ids)}},
            {
                "_id": 0,
                "candidate_id": 1,
                "search_text": 1,
                "occupation_candidates.preferred_label": 1,
                "skill_candidates.preferred_label": 1,
                "experiences.title": 1,
                "experiences.description_raw": 1,
            },
        )
        text_map: dict[str, str] = {}
        for row in cursor:
            candidate_id = str(row.get("candidate_id") or "")
            if not candidate_id:
                continue
            search_text = str(row.get("search_text") or "").strip()
            if search_text:
                text_map[candidate_id] = search_text
                continue

            chunks: list[str] = []
            for occ in row.get("occupation_candidates") or []:
                if isinstance(occ, dict):
                    label = str(occ.get("preferred_label") or "").strip()
                    if label:
                        chunks.append(label)
            for skill in row.get("skill_candidates") or []:
                if isinstance(skill, dict):
                    label = str(skill.get("preferred_label") or "").strip()
                    if label:
                        chunks.append(label)
            for exp in row.get("experiences") or []:
                if isinstance(exp, dict):
                    title = str(exp.get("title") or "").strip()
                    if title:
                        chunks.append(title)
                    description = str(exp.get("description_raw") or "").strip()
                    if description:
                        chunks.append(description[:280])
            text_map[candidate_id] = " | ".join(_dedupe_preserve_order(chunks))
        return text_map

    def fetch_candidate_esco_ids(self, candidate_ids: Sequence[str]) -> Mapping[str, Sequence[str]]:
        if not candidate_ids:
            return {}
        collection = self._normalized_collection()
        cursor = collection.find(
            {"candidate_id": {"$in": list(candidate_ids)}},
            {
                "_id": 0,
                "candidate_id": 1,
                "occupation_candidates.esco_id": 1,
                "skill_candidates.esco_id": 1,
                "industry_esco_ids_json": 1,
            },
        )

        result: dict[str, list[str]] = {}
        for row in cursor:
            candidate_id = str(row.get("candidate_id") or "")
            if not candidate_id:
                continue
            esco_ids: list[str] = []
            for candidate in row.get("occupation_candidates") or []:
                if isinstance(candidate, dict):
                    esco_id = str(candidate.get("esco_id") or "").strip()
                    if esco_id:
                        esco_ids.append(esco_id)
            for candidate in row.get("skill_candidates") or []:
                if isinstance(candidate, dict):
                    esco_id = str(candidate.get("esco_id") or "").strip()
                    if esco_id:
                        esco_ids.append(esco_id)
            for industry_id in row.get("industry_esco_ids_json") or []:
                value = str(industry_id or "").strip()
                if value:
                    esco_ids.append(value)
            result[candidate_id] = _dedupe_preserve_order(esco_ids)

        for candidate_id in candidate_ids:
            result.setdefault(candidate_id, [])
        return result

    def fetch_candidate_profiles(self, candidate_ids: Sequence[str]) -> Mapping[str, dict[str, Any]]:
        if not candidate_ids:
            return {}

        collection = self._normalized_collection()
        cursor = collection.find(
            {"candidate_id": {"$in": list(candidate_ids)}},
            {
                "_id": 0,
                "candidate_id": 1,
                "resume_text": 1,
                "occupation_candidates.preferred_label": 1,
                "skill_candidates.preferred_label": 1,
                "experiences": 1,
                "educations": 1,
            },
        )

        profiles: dict[str, dict[str, Any]] = {}
        for row in cursor:
            candidate_id = str(row.get("candidate_id") or "")
            if not candidate_id:
                continue
            occupation_labels: list[str] = []
            for item in row.get("occupation_candidates") or []:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("preferred_label") or "").strip()
                if label:
                    occupation_labels.append(label)

            skill_labels: list[str] = []
            for item in row.get("skill_candidates") or []:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("preferred_label") or "").strip()
                if label:
                    skill_labels.append(label)

            experiences = [
                dict(item)
                for item in (row.get("experiences") or [])
                if isinstance(item, dict)
            ]
            educations = [
                dict(item)
                for item in (row.get("educations") or [])
                if isinstance(item, dict)
            ]
            profiles[candidate_id] = {
                "candidate_id": candidate_id,
                "resume_text": str(row.get("resume_text") or ""),
                "occupation_labels": _dedupe_preserve_order(occupation_labels),
                "skill_labels": _dedupe_preserve_order(skill_labels),
                "experiences": experiences,
                "educations": educations,
            }

        for candidate_id in candidate_ids:
            profiles.setdefault(
                candidate_id,
                {
                    "candidate_id": candidate_id,
                    "resume_text": "",
                    "occupation_labels": [],
                    "skill_labels": [],
                    "experiences": [],
                    "educations": [],
                },
            )
        return profiles

    def fetch_candidate_detail(self, candidate_id: str) -> dict[str, Any] | None:
        target = candidate_id.strip()
        if not target:
            return None

        collection = self._normalized_collection()
        row = collection.find_one(
            {"candidate_id": target},
            {
                "_id": 0,
                "candidate_id": 1,
                "source_dataset": 1,
                "source_record_id": 1,
                "current_location": 1,
                "category": 1,
                "resume_text": 1,
                "occupation_candidates": 1,
                "skill_candidates": 1,
                "experiences": 1,
                "educations": 1,
            },
        )
        if not isinstance(row, dict):
            return None

        return {
            "candidate_id": str(row.get("candidate_id") or target),
            "source_dataset": str(row.get("source_dataset") or ""),
            "source_record_id": str(row.get("source_record_id") or ""),
            "current_location": str(row.get("current_location") or ""),
            "category": str(row.get("category") or ""),
            "resume_text": str(row.get("resume_text") or ""),
            "occupation_candidates": [
                dict(item) for item in (row.get("occupation_candidates") or []) if isinstance(item, dict)
            ],
            "skill_candidates": [
                dict(item) for item in (row.get("skill_candidates") or []) if isinstance(item, dict)
            ],
            "experiences": [dict(item) for item in (row.get("experiences") or []) if isinstance(item, dict)],
            "educations": [dict(item) for item in (row.get("educations") or []) if isinstance(item, dict)],
        }

    def fetch_candidate_resume_raw(self, candidate_id: str) -> dict[str, Any] | None:
        target = candidate_id.strip()
        if not target:
            return None

        normalized = self._normalized_collection().find_one(
            {"candidate_id": target},
            {
                "_id": 0,
                "candidate_id": 1,
                "source_dataset": 1,
                "source_record_id": 1,
                "resume_text": 1,
            },
        )
        if not isinstance(normalized, dict):
            return None

        source_dataset = str(normalized.get("source_dataset") or "")
        source_record_id = str(normalized.get("source_record_id") or "")
        resume_text = str(normalized.get("resume_text") or "")

        if source_dataset and source_record_id:
            source_row = self._source_collection().find_one(
                {
                    "source_dataset": source_dataset,
                    "source_record_id": source_record_id,
                },
                {
                    "_id": 0,
                    "resume_text": 1,
                },
            )
            if isinstance(source_row, dict):
                source_resume_text = str(source_row.get("resume_text") or "")
                if source_resume_text:
                    resume_text = source_resume_text

        return {
            "candidate_id": str(normalized.get("candidate_id") or target),
            "source_dataset": source_dataset,
            "source_record_id": source_record_id,
            "resume_text": resume_text,
        }

    def insert_guardrail_audit_logs(self, rows: Sequence[Mapping[str, Any]]) -> int:
        docs = [dict(row) for row in rows if isinstance(row, Mapping) and row]
        if not docs:
            return 0
        collection = self._guardrail_audit_collection()
        result = collection.insert_many(docs, ordered=False)
        return len(result.inserted_ids)


def _to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _dedupe_preserve_order(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(value.strip())
    return out
