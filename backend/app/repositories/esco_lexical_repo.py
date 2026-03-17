from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Mapping, Sequence

from ..core.config import Settings, get_settings
from ..domain import EscoDomain
from ..services.query_normalizer import EscoLexicalRepo, RepoMatch

try:
    from pymongo import MongoClient
except Exception:  # pragma: no cover
    MongoClient = None

try:
    from rapidfuzz import fuzz, process
except Exception:  # pragma: no cover
    fuzz = None
    process = None


_SPLIT_PATTERN = re.compile(r"[,\n;|]+")


@dataclass(slots=True)
class _LexicalIndex:
    exact_map: dict[str, list[RepoMatch]]
    alt_map: dict[str, list[RepoMatch]]
    fuzzy_values: list[tuple[str, RepoMatch]]


@dataclass(slots=True)
class EscoLexicalMongoRepository(EscoLexicalRepo):
    settings: Settings = field(default_factory=get_settings)
    fuzzy_min_score: float = 0.60
    _client: Any | None = field(default=None, init=False, repr=False)
    _db: Any | None = field(default=None, init=False, repr=False)
    _index_cache: dict[EscoDomain, _LexicalIndex] = field(default_factory=dict, init=False, repr=False)

    def find_exact(self, domain: EscoDomain, term: str, limit: int = 5) -> Sequence[RepoMatch]:
        key = _normalize(term)
        if not key:
            return []
        index = self._get_index(domain)
        return list(index.exact_map.get(key, []))[:limit]

    def find_alt(self, domain: EscoDomain, term: str, limit: int = 5) -> Sequence[RepoMatch]:
        key = _normalize(term)
        if not key:
            return []
        index = self._get_index(domain)
        return list(index.alt_map.get(key, []))[:limit]

    def find_fuzzy(self, domain: EscoDomain, term: str, limit: int = 5) -> Sequence[RepoMatch]:
        key = _normalize(term)
        if not key:
            return []
        index = self._get_index(domain)
        return _fuzzy_search(
            query=key,
            values=index.fuzzy_values,
            limit=limit,
            min_score=self.fuzzy_min_score,
        )

    def _get_index(self, domain: EscoDomain) -> _LexicalIndex:
        cached = self._index_cache.get(domain)
        if cached is not None:
            return cached

        collection_name = _collection_name_for_domain(domain, self.settings)
        rows = list(
            self._ensure_db()[collection_name].find(
                {},
                {
                    "_id": 0,
                },
            )
        )
        index = _build_index(rows)
        self._index_cache[domain] = index
        return index

    def _ensure_db(self) -> Any:
        if self._db is not None:
            return self._db
        if MongoClient is None:
            raise RuntimeError("pymongo is not installed.")
        self._client = MongoClient(self.settings.mongo_uri)
        self._db = self._client[self.settings.mongo_db_name]
        return self._db


def _build_index(rows: Sequence[Mapping[str, Any]]) -> _LexicalIndex:
    exact_map: dict[str, list[RepoMatch]] = {}
    alt_map: dict[str, list[RepoMatch]] = {}
    fuzzy_values: list[tuple[str, RepoMatch]] = []

    for row in rows:
        esco_id = _extract_esco_id(row)
        preferred_label = _extract_preferred_label(row)
        if not esco_id or not preferred_label:
            continue

        preferred_norm = _normalize(preferred_label)
        if preferred_norm:
            exact_map.setdefault(preferred_norm, []).append(
                RepoMatch(esco_id=esco_id, label=preferred_label, score=0.98)
            )
            fuzzy_values.append(
                (preferred_norm, RepoMatch(esco_id=esco_id, label=preferred_label, score=0.98))
            )

        for alt_label in _extract_alt_labels(row):
            alt_norm = _normalize(alt_label)
            if not alt_norm:
                continue
            alt_map.setdefault(alt_norm, []).append(
                RepoMatch(esco_id=esco_id, label=preferred_label, score=0.87)
            )
            fuzzy_values.append((alt_norm, RepoMatch(esco_id=esco_id, label=preferred_label, score=0.87)))

    for mapping in (exact_map, alt_map):
        for key in list(mapping.keys()):
            mapping[key] = _dedupe_best(mapping[key])

    return _LexicalIndex(exact_map=exact_map, alt_map=alt_map, fuzzy_values=fuzzy_values)


def _collection_name_for_domain(domain: EscoDomain, settings: Settings) -> str:
    if domain == "skill":
        return settings.mongo_raw_esco_skills_collection
    if domain == "occupation":
        return settings.mongo_raw_esco_occupations_collection
    return settings.mongo_raw_esco_isco_groups_collection


def _extract_esco_id(row: Mapping[str, Any]) -> str:
    for key in ("esco_id", "id", "conceptUri", "uri"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_preferred_label(row: Mapping[str, Any]) -> str:
    for key in ("preferred_label", "preferredLabel", "label", "title"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_alt_labels(row: Mapping[str, Any]) -> list[str]:
    labels: list[str] = []
    for key in ("alt_labels", "altLabels", "alternative_labels", "alternativeLabel"):
        value = row.get(key)
        if isinstance(value, list):
            labels.extend(str(item).strip() for item in value if str(item).strip())
        elif isinstance(value, str):
            labels.extend(part.strip() for part in _SPLIT_PATTERN.split(value) if part.strip())
    return _dedupe_strings(labels)


def _fuzzy_search(
    *,
    query: str,
    values: list[tuple[str, RepoMatch]],
    limit: int,
    min_score: float,
) -> list[RepoMatch]:
    if not values:
        return []

    score_map: dict[str, tuple[float, RepoMatch]] = {}

    if process is not None and fuzz is not None:
        choices = [value for value, _ in values]
        fuzzy_hits = process.extract(
            query,
            choices,
            scorer=fuzz.WRatio,
            limit=max(limit * 3, 10),
        )
        for matched, score, index in fuzzy_hits:
            confidence = max(0.0, min(1.0, float(score) / 100.0))
            if confidence < min_score:
                continue
            _, repo_match = values[index]
            merged_score = max(confidence, repo_match.score)
            current = score_map.get(repo_match.esco_id)
            candidate = RepoMatch(
                esco_id=repo_match.esco_id,
                label=repo_match.label,
                score=merged_score,
            )
            if current is None or merged_score > current[0]:
                score_map[repo_match.esco_id] = (merged_score, candidate)
    else:
        for value, repo_match in values:
            confidence = SequenceMatcher(a=query, b=value).ratio()
            if confidence < min_score:
                continue
            merged_score = max(confidence, repo_match.score)
            current = score_map.get(repo_match.esco_id)
            candidate = RepoMatch(
                esco_id=repo_match.esco_id,
                label=repo_match.label,
                score=merged_score,
            )
            if current is None or merged_score > current[0]:
                score_map[repo_match.esco_id] = (merged_score, candidate)

    ordered = sorted(score_map.values(), key=lambda item: (-item[0], item[1].label.lower()))
    return [item[1] for item in ordered[:limit]]


def _dedupe_best(matches: Sequence[RepoMatch]) -> list[RepoMatch]:
    best: dict[str, RepoMatch] = {}
    for match in matches:
        current = best.get(match.esco_id)
        if current is None or match.score > current.score:
            best[match.esco_id] = match
    return sorted(best.values(), key=lambda item: (-item.score, item.label.lower()))


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        key = _normalize(value)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(value.strip())
    return out


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())
