from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from pymongo import MongoClient, UpdateOne
from rapidfuzz import fuzz, process

try:
    from extract_fields import extract_all_fields, fields_to_dict
except Exception:
    extract_all_fields = None
    fields_to_dict = None

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    from milvus_client import MilvusSearchClient
except Exception:
    MilvusSearchClient = None


NORMALIZER_VERSION = "issue13_llm_occ_jury_v1"

PROFILE_CONFIG = {
    "precision": {
        "occ_threshold": 0.92,
        "skill_threshold": 0.90,
        "top_occ": 5,
        "top_skill": 20,
        "drop_fuzzy_when_non_fuzzy": True,
        "max_fuzzy_per_raw": 1,
        "fallback_fuzzy_only": True,
    },
    "balanced": {
        "occ_threshold": 0.88,
        "skill_threshold": 0.86,
        "top_occ": 10,
        "top_skill": 30,
        "drop_fuzzy_when_non_fuzzy": True,
        "max_fuzzy_per_raw": 2,
        "fallback_fuzzy_only": True,
    },
    "coverage": {
        "occ_threshold": 0.82,
        "skill_threshold": 0.80,
        "top_occ": 15,
        "top_skill": 40,
        "drop_fuzzy_when_non_fuzzy": False,
        "max_fuzzy_per_raw": 3,
        "fallback_fuzzy_only": False,
    },
}

STRICTNESS_DELTA = {
    "strict": 0.03,
    "medium": 0.0,
    "lenient": -0.03,
}

TITLE_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z/&-]*(?:\s+[A-Z][A-Za-z/&-]*){0,4}\s+"
    r"(?:Manager|Engineer|Developer|Analyst|Consultant|Architect|"
    r"Administrator|Officer|Specialist|Coordinator|Supervisor|Director|"
    r"Technician|Designer))\b"
)

GENERIC_TERMS = {
    "skills",
    "experience",
    "education",
    "summary",
    "profile",
    "company",
    "city",
    "state",
}

# Category anchor expansions used for two things:
# 1) Expand short/ambiguous category phrases (e.g. HR -> human resources)
# 2) Guard against low-confidence fuzzy mismatches with no category alignment
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


@dataclass
class Candidate:
    esco_id: str
    preferred_label: str
    raw_text: str
    confidence: float
    match_method: str
    hierarchy_json: list[dict[str, str]]
    source_span: str | None = None
    graph_support: dict[str, Any] | None = None
    base_confidence: float | None = None
    llm_fit_score: float | None = None
    llm_rank_score: float | None = None


@dataclass
class EmbeddingRuntime:
    mode: str = "off"
    enabled: bool = False
    disabled_reason: str = ""
    model: str = "text-embedding-3-small"
    occ_top_k: int = 12
    skill_top_k: int = 20
    min_confidence: float = 0.58
    confidence_scale: float = 0.90
    occ_query_limit: int = 5
    skill_query_limit: int = 8
    milvus_uri: str = ""
    milvus_db_name: str = ""
    milvus_occ_collection: str = ""
    milvus_skill_collection: str = ""
    openai_client: Any | None = None
    milvus_client: Any | None = None
    embedding_cache: dict[str, list[float]] = field(default_factory=dict)
    occ_search_cache: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    skill_search_cache: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    embed_api_calls: int = 0
    embedding_cache_hits: int = 0
    search_api_calls: int = 0
    search_cache_hits: int = 0
    failed_embedding_calls: int = 0
    failed_search_calls: int = 0

    def summary(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "enabled": self.enabled,
            "disabled_reason": self.disabled_reason or None,
            "model": self.model,
            "milvus_db_name": self.milvus_db_name,
            "milvus_occ_collection": self.milvus_occ_collection,
            "milvus_skill_collection": self.milvus_skill_collection,
            "embed_api_calls": self.embed_api_calls,
            "embedding_cache_hits": self.embedding_cache_hits,
            "search_api_calls": self.search_api_calls,
            "search_cache_hits": self.search_cache_hits,
            "failed_embedding_calls": self.failed_embedding_calls,
            "failed_search_calls": self.failed_search_calls,
            "embedding_cache_size": len(self.embedding_cache),
            "occ_search_cache_size": len(self.occ_search_cache),
            "skill_search_cache_size": len(self.skill_search_cache),
        }


@dataclass
class LlmOccupationRuntime:
    mode: str = "off"
    enabled: bool = False
    disabled_reason: str = ""
    model: str = "gpt-4.1-mini"
    candidate_k: int = 30
    jury_size: int = 5
    temperature: float = 0.2
    max_resume_chars: int = 5000
    openai_client: Any | None = None
    api_calls: int = 0
    failed_calls: int = 0
    profile_cache_hits: int = 0
    profile_cache: dict[str, dict[str, Any]] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "enabled": self.enabled,
            "disabled_reason": self.disabled_reason or None,
            "model": self.model,
            "candidate_k": self.candidate_k,
            "jury_size": self.jury_size,
            "temperature": self.temperature,
            "max_resume_chars": self.max_resume_chars,
            "api_calls": self.api_calls,
            "failed_calls": self.failed_calls,
            "profile_cache_hits": self.profile_cache_hits,
            "profile_cache_size": len(self.profile_cache),
        }


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def normalize_spaces(value: str | None) -> str:
    return " ".join((value or "").split())


def unique_strings(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = normalize_text(value)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(normalize_spaces(value))
    return out


def category_anchor_phrases(category: str | None) -> list[str]:
    normalized_category = normalize_spaces(category or "")
    upper_category = normalized_category.upper()

    phrases: list[str] = []
    phrases.extend(CATEGORY_ALIAS_PHRASES.get(upper_category, []))
    phrases.extend([tok for tok in normalize_text(normalized_category).split() if len(tok) >= 3])
    return unique_strings(phrases)


def embedding_phrase_allowed(phrase: str) -> bool:
    key = normalize_text(phrase)
    # B1 occupation queries append short raw-experience text, so allow moderate length.
    if len(key) < 3 or len(key) > 320:
        return False
    if key in GENERIC_TERMS:
        return False
    tokens = [tok for tok in re.findall(r"[a-z]{2,}", key) if tok not in GENERIC_TERMS]
    return len(tokens) >= 1


def build_embedding_runtime(args: argparse.Namespace) -> EmbeddingRuntime:
    runtime = EmbeddingRuntime(
        mode=args.embedding_mode,
        model=args.embedding_model,
        occ_top_k=args.embedding_occ_top_k,
        skill_top_k=args.embedding_skill_top_k,
        min_confidence=args.embedding_min_confidence,
        confidence_scale=args.embedding_confidence_scale,
        occ_query_limit=args.embedding_occ_query_limit,
        skill_query_limit=args.embedding_skill_query_limit,
    )

    if args.embedding_mode == "off":
        runtime.disabled_reason = "embedding_mode=off"
        return runtime

    env_path = Path(__file__).resolve().parent / ".env"
    if load_dotenv is not None and env_path.exists():
        load_dotenv(env_path)

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
    openai_api_key = args.openai_api_key or os.getenv("OPENAI_API_KEY", "")

    runtime.milvus_uri = milvus_uri
    runtime.milvus_db_name = milvus_db_name
    runtime.milvus_occ_collection = milvus_occ_collection
    runtime.milvus_skill_collection = milvus_skill_collection

    if OpenAI is None:
        runtime.disabled_reason = "openai package is not installed"
        return runtime
    if MilvusSearchClient is None:
        runtime.disabled_reason = "pymilvus package is not installed"
        return runtime
    if not milvus_uri:
        runtime.disabled_reason = "MILVUS_URI is not configured"
        return runtime
    if not openai_api_key:
        runtime.disabled_reason = "OPENAI_API_KEY is not configured"
        return runtime

    try:
        runtime.openai_client = OpenAI(api_key=openai_api_key)
        runtime.milvus_client = MilvusSearchClient(
            uri=milvus_uri,
            token=milvus_token,
            db_name=milvus_db_name,
            occupation_collection=milvus_occ_collection,
            skill_collection=milvus_skill_collection,
            metric_type=args.milvus_metric_type,
            ef=args.milvus_search_ef,
        )
        runtime.enabled = True
        runtime.disabled_reason = ""
    except Exception as exc:
        runtime.enabled = False
        runtime.openai_client = None
        runtime.milvus_client = None
        runtime.disabled_reason = f"{type(exc).__name__}: {exc}"

    return runtime


def build_llm_occ_runtime(
    args: argparse.Namespace,
    shared_openai_client: Any | None = None,
) -> LlmOccupationRuntime:
    runtime = LlmOccupationRuntime(
        mode=args.llm_occ_rerank_mode,
        model=args.llm_occ_model,
        candidate_k=args.llm_occ_candidate_k,
        jury_size=max(1, int(args.llm_occ_jury_size)),
        temperature=max(0.0, min(1.0, float(args.llm_occ_temperature))),
        max_resume_chars=max(1000, int(args.llm_occ_max_resume_chars)),
    )

    if runtime.mode == "off":
        runtime.disabled_reason = "llm_occ_rerank_mode=off"
        return runtime

    env_path = Path(__file__).resolve().parent / ".env"
    if load_dotenv is not None and env_path.exists():
        load_dotenv(env_path)

    openai_api_key = args.openai_api_key or os.getenv("OPENAI_API_KEY", "")
    if OpenAI is None:
        runtime.disabled_reason = "openai package is not installed"
        return runtime
    if not openai_api_key and shared_openai_client is None:
        runtime.disabled_reason = "OPENAI_API_KEY is not configured"
        return runtime

    try:
        runtime.openai_client = shared_openai_client or OpenAI(api_key=openai_api_key)
        runtime.enabled = True
        runtime.disabled_reason = ""
    except Exception as exc:
        runtime.enabled = False
        runtime.openai_client = None
        runtime.disabled_reason = f"{type(exc).__name__}: {exc}"

    return runtime


def safe_json_loads(text: str) -> dict[str, Any] | None:
    value = (text or "").strip()
    if not value:
        return None
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = value.find("{")
    end = value.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(value[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None
    return None


def llm_chat_json(
    runtime: LlmOccupationRuntime,
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int = 1800,
) -> dict[str, Any] | None:
    if not runtime.enabled or runtime.openai_client is None:
        return None

    try:
        response = runtime.openai_client.chat.completions.create(
            model=runtime.model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        runtime.api_calls += 1
        choices = getattr(response, "choices", None) or []
        if not choices:
            runtime.failed_calls += 1
            return None
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", "") if message is not None else ""
        parsed = safe_json_loads(str(content))
        if parsed is None:
            runtime.failed_calls += 1
            return None
        return parsed
    except Exception:
        runtime.failed_calls += 1
        return None


def embed_text(runtime: EmbeddingRuntime, text: str) -> list[float] | None:
    key = normalize_text(text)
    if not key or runtime.openai_client is None:
        return None

    if key in runtime.embedding_cache:
        runtime.embedding_cache_hits += 1
        return runtime.embedding_cache[key]

    try:
        response = runtime.openai_client.embeddings.create(
            model=runtime.model,
            input=text,
        )
        data = getattr(response, "data", None) or []
        if not data:
            runtime.failed_embedding_calls += 1
            return None

        vector = list(getattr(data[0], "embedding", []) or [])
        if not vector:
            runtime.failed_embedding_calls += 1
            return None

        runtime.embedding_cache[key] = vector
        runtime.embed_api_calls += 1
        return vector
    except Exception:
        runtime.failed_embedding_calls += 1
        return None


def embedding_match(
    phrases: list[str],
    index: ConceptIndex,
    runtime: EmbeddingRuntime,
    target: str,
) -> list[Candidate]:
    if not runtime.enabled or runtime.milvus_client is None:
        return []

    if target not in {"occupation", "skill"}:
        return []

    out: list[Candidate] = []
    phrase_limit = runtime.occ_query_limit if target == "occupation" else runtime.skill_query_limit
    top_k = runtime.occ_top_k if target == "occupation" else runtime.skill_top_k
    search_cache = runtime.occ_search_cache if target == "occupation" else runtime.skill_search_cache

    for phrase in unique_strings(phrases)[:phrase_limit]:
        if not embedding_phrase_allowed(phrase):
            continue

        cache_key = normalize_text(phrase)
        if cache_key in search_cache:
            cached_rows = search_cache.get(cache_key, [])
            out.extend(_candidate_from_cache_row(row, phrase) for row in cached_rows)
            runtime.search_cache_hits += 1
            continue

        vector = embed_text(runtime, phrase)
        if not vector:
            search_cache[cache_key] = []
            continue

        try:
            if target == "occupation":
                hits = runtime.milvus_client.search_occupation(vector, top_k)
            else:
                hits = runtime.milvus_client.search_skill(vector, top_k)
            runtime.search_api_calls += 1
        except Exception:
            runtime.failed_search_calls += 1
            search_cache[cache_key] = []
            continue

        cached_rows: list[dict[str, Any]] = []
        for hit in hits:
            if not hit.esco_id:
                continue
            score_conf = runtime.milvus_client.score_to_confidence(float(hit.score))
            confidence = round(
                max(0.0, min(1.0, score_conf * runtime.confidence_scale)),
                5,
            )
            if confidence < runtime.min_confidence:
                continue

            candidate = Candidate(
                esco_id=hit.esco_id,
                preferred_label=normalize_spaces(hit.preferred_label) or hit.esco_id,
                raw_text=normalize_spaces(phrase),
                confidence=confidence,
                match_method="embedding",
                hierarchy_json=index.get_hierarchy(hit.esco_id),
                source_span=normalize_spaces(phrase),
            )
            out.append(candidate)
            cached_rows.append(_candidate_to_cache_row(candidate))

        search_cache[cache_key] = cached_rows

    return out


def build_experience_raw_snippet(experiences: list[dict[str, Any]], max_chars: int = 180) -> str:
    if not experiences:
        return ""

    def _sort_key(exp: dict[str, Any]) -> tuple[int, str, str]:
        return (
            1 if bool(exp.get("is_current")) else 0,
            str(exp.get("end_date") or ""),
            str(exp.get("start_date") or ""),
        )

    top = sorted([e for e in experiences if isinstance(e, dict)], key=_sort_key, reverse=True)[:2]
    chunks: list[str] = []
    for exp in top:
        title = normalize_spaces(exp.get("title") or exp.get("raw_title"))
        company = normalize_spaces(exp.get("company"))
        desc = normalize_spaces(exp.get("description_raw"))
        chunk = " | ".join([v for v in [title, company, desc] if v])
        if chunk:
            chunks.append(chunk)
    if not chunks:
        return ""
    return " ; ".join(chunks)[:max_chars]


def build_occupation_b1_queries(occupation_phrases: list[str], experiences: list[dict[str, Any]]) -> list[str]:
    exp_snippet = build_experience_raw_snippet(experiences)
    if not exp_snippet:
        return []

    base = unique_strings(occupation_phrases)[:2]
    out: list[str] = []
    for phrase in base:
        if not phrase:
            continue
        out.append(f"{phrase} ; experience: {exp_snippet}")
    return out


def rrf_fuse_embedding_candidates(
    primary: list[Candidate],
    secondary: list[Candidate],
    top_k: int,
    rrf_k: int = 60,
) -> list[Candidate]:
    if not primary and not secondary:
        return []
    if not secondary:
        return sorted(primary, key=lambda c: c.confidence, reverse=True)[:top_k]

    def _ranked(rows: list[Candidate]) -> list[Candidate]:
        best: dict[str, Candidate] = {}
        for cand in rows:
            current = best.get(cand.esco_id)
            if current is None or cand.confidence > current.confidence:
                best[cand.esco_id] = cand
        return sorted(best.values(), key=lambda c: c.confidence, reverse=True)

    fused: dict[str, dict[str, Any]] = {}
    for ranked in [_ranked(primary), _ranked(secondary)]:
        for rank, cand in enumerate(ranked, start=1):
            row = fused.setdefault(
                cand.esco_id,
                {
                    "best": cand,
                    "rrf_score": 0.0,
                    "best_conf": cand.confidence,
                },
            )
            row["rrf_score"] += 1.0 / float(rrf_k + rank)
            if cand.confidence > row["best_conf"]:
                row["best_conf"] = cand.confidence
                row["best"] = cand

    merged: list[Candidate] = []
    for row in fused.values():
        best = row["best"]
        # Convert rank-fusion evidence into a bounded confidence bump.
        boosted = min(1.0, float(row["best_conf"]) + (float(row["rrf_score"]) * 3.0))
        merged.append(
            Candidate(
                esco_id=best.esco_id,
                preferred_label=best.preferred_label,
                raw_text=best.raw_text,
                confidence=round(boosted, 5),
                match_method="embedding_b1",
                hierarchy_json=best.hierarchy_json,
                source_span=best.source_span,
            )
        )

    return sorted(merged, key=lambda c: c.confidence, reverse=True)[:top_k]


def label_matches_category(label: str | None, category: str | None) -> bool:
    label_norm = normalize_text(label)
    if not label_norm:
        return False

    anchors = [normalize_text(p) for p in category_anchor_phrases(category)]
    anchors = [a for a in anchors if a]
    return any(anchor in label_norm for anchor in anchors)


def parse_alt_labels(row: dict[str, Any]) -> list[str]:
    alt = row.get("alt_labels_list")
    if isinstance(alt, list):
        return [v for v in alt if isinstance(v, str)]

    raw = row.get("altLabels") or ""
    if not isinstance(raw, str):
        return []
    labels = []
    for part in raw.replace("|", "\n").splitlines():
        text = normalize_spaces(part)
        if text:
            labels.append(text)
    return labels


class ConceptIndex:
    def __init__(self, concept_rows: list[dict[str, Any]], broader_rows: list[dict[str, Any]]) -> None:
        self.preferred_map: dict[str, list[tuple[str, str]]] = {}
        self.alt_map: dict[str, list[tuple[str, str]]] = {}
        self.label_to_entries: dict[str, list[tuple[str, str]]] = {}
        self.search_labels: list[str] = []
        self._broader: dict[str, list[dict[str, str]]] = {}
        self._hierarchy_cache: dict[str, list[dict[str, str]]] = {}
        self._meta_by_esco: dict[str, dict[str, Any]] = {}

        for row in broader_rows:
            child = (row.get("concept_uri") or row.get("conceptUri") or "").strip()
            parent = (row.get("broader_uri") or row.get("broaderUri") or "").strip()
            label = (row.get("broader_label") or row.get("broaderLabel") or "").strip()
            if child and parent:
                self._broader.setdefault(child, []).append({"id": parent, "label": label})

        for row in concept_rows:
            esco_id = (row.get("concept_uri") or row.get("conceptUri") or "").strip()
            preferred = (row.get("preferred_label") or row.get("preferredLabel") or "").strip()
            if not esco_id or not preferred:
                continue

            description = normalize_spaces(
                row.get("description")
                or row.get("definition")
                or row.get("scopeNote")
                or row.get("scope_note")
                or ""
            )
            isco_group = normalize_spaces(str(row.get("iscoGroup") or row.get("isco_group") or ""))
            self._meta_by_esco[esco_id] = {
                "preferred_label": preferred,
                "alt_labels": parse_alt_labels(row),
                "description": description,
                "isco_group": isco_group,
            }

            pref_norm = normalize_text(preferred)
            self.preferred_map.setdefault(pref_norm, []).append((esco_id, preferred))
            self.label_to_entries.setdefault(pref_norm, []).append((esco_id, preferred))

            for alt in parse_alt_labels(row):
                alt_norm = normalize_text(alt)
                if not alt_norm:
                    continue
                self.alt_map.setdefault(alt_norm, []).append((esco_id, preferred))
                self.label_to_entries.setdefault(alt_norm, []).append((esco_id, preferred))

        self.search_labels = sorted(self.label_to_entries.keys())

    def get_hierarchy(self, concept_uri: str, max_depth: int = 6) -> list[dict[str, str]]:
        if concept_uri in self._hierarchy_cache:
            return self._hierarchy_cache[concept_uri]

        chain: list[dict[str, str]] = []
        current = concept_uri
        visited: set[str] = set()
        depth = 0
        while depth < max_depth and current and current not in visited:
            visited.add(current)
            parents = self._broader.get(current, [])
            if not parents:
                break
            parent = parents[0]
            chain.append(parent)
            current = parent.get("id", "")
            depth += 1

        self._hierarchy_cache[concept_uri] = chain
        return chain

    def get_meta(self, concept_uri: str) -> dict[str, Any]:
        return self._meta_by_esco.get(concept_uri, {})


class OccupationSkillGraph:
    def __init__(self, relation_rows: list[dict[str, Any]]) -> None:
        self.essential_by_occ: dict[str, set[str]] = {}
        self.optional_by_occ: dict[str, set[str]] = {}

        for row in relation_rows:
            occ = (row.get("occupation_uri") or row.get("occupationUri") or "").strip()
            skill = (row.get("skill_uri") or row.get("skillUri") or "").strip()
            rel = (row.get("relationType") or "").strip().lower()
            if not occ or not skill:
                continue
            if rel == "essential":
                self.essential_by_occ.setdefault(occ, set()).add(skill)
            else:
                self.optional_by_occ.setdefault(occ, set()).add(skill)

    def support(self, occ: str, matched_skills: set[str], essential_w: float, optional_w: float, max_boost: float) -> dict[str, Any]:
        essential_hits = len(self.essential_by_occ.get(occ, set()) & matched_skills)
        optional_hits = len(self.optional_by_occ.get(occ, set()) & matched_skills)
        boost = min(max_boost, (essential_hits * essential_w) + (optional_hits * optional_w))
        return {
            "essential_hits": essential_hits,
            "optional_hits": optional_hits,
            "boost": round(boost, 5),
        }


def exact_match(phrase: str, index: ConceptIndex) -> list[Candidate]:
    key = normalize_text(phrase)
    out: list[Candidate] = []
    for esco_id, preferred in index.preferred_map.get(key, []):
        out.append(
            Candidate(
                esco_id=esco_id,
                preferred_label=preferred,
                raw_text=normalize_spaces(phrase),
                confidence=1.0,
                match_method="exact",
                hierarchy_json=index.get_hierarchy(esco_id),
                source_span=normalize_spaces(phrase),
            )
        )
    return out


def alt_match(phrase: str, index: ConceptIndex) -> list[Candidate]:
    key = normalize_text(phrase)
    out: list[Candidate] = []
    for esco_id, preferred in index.alt_map.get(key, []):
        out.append(
            Candidate(
                esco_id=esco_id,
                preferred_label=preferred,
                raw_text=normalize_spaces(phrase),
                confidence=0.95,
                match_method="alt_label",
                hierarchy_json=index.get_hierarchy(esco_id),
                source_span=normalize_spaces(phrase),
            )
        )
    return out


def fuzzy_match(phrase: str, index: ConceptIndex, threshold: float, limit: int) -> list[Candidate]:
    key = normalize_text(phrase)
    if len(key) > 64:
        return []
    tokens = [t for t in re.findall(r"[a-z]{2,}", key) if t not in GENERIC_TERMS]
    if len(tokens) < 2:
        return []
    if len(tokens) > 6:
        return []

    out: list[Candidate] = []
    for label_norm, score, _ in process.extract(key, index.search_labels, scorer=fuzz.token_set_ratio, limit=limit):
        confidence = score / 100.0
        if confidence < threshold:
            continue

        label_tokens = set(re.findall(r"[a-z]{2,}", label_norm))
        if not set(tokens) & label_tokens:
            continue

        for esco_id, preferred in index.label_to_entries.get(label_norm, []):
            out.append(
                Candidate(
                    esco_id=esco_id,
                    preferred_label=preferred,
                    raw_text=normalize_spaces(phrase),
                    confidence=round(confidence * 0.92, 5),
                    match_method="fuzzy",
                    hierarchy_json=index.get_hierarchy(esco_id),
                    source_span=normalize_spaces(phrase),
                )
            )
    return out


def _candidate_to_cache_row(candidate: Candidate) -> dict[str, Any]:
    return {
        "esco_id": candidate.esco_id,
        "preferred_label": candidate.preferred_label,
        "raw_text": candidate.raw_text,
        "confidence": candidate.confidence,
        "match_method": candidate.match_method,
        "hierarchy_json": candidate.hierarchy_json,
        "source_span": candidate.source_span,
    }


def _candidate_from_cache_row(row: dict[str, Any], phrase: str) -> Candidate:
    return Candidate(
        esco_id=row["esco_id"],
        preferred_label=row["preferred_label"],
        raw_text=normalize_spaces(phrase),
        confidence=float(row["confidence"]),
        match_method=row["match_method"],
        hierarchy_json=row.get("hierarchy_json") or [],
        source_span=row.get("source_span"),
    )


def staged_match(
    phrases: list[str],
    index: ConceptIndex,
    threshold: float,
    fallback_fuzzy_only: bool,
    phrase_cache: dict[str, list[dict[str, Any]]] | None = None,
) -> list[Candidate]:
    out: list[Candidate] = []
    for phrase in unique_strings(phrases):
        cache_key = normalize_text(phrase)
        if phrase_cache is not None and cache_key in phrase_cache:
            out.extend(
                [_candidate_from_cache_row(row, phrase) for row in phrase_cache.get(cache_key, [])]
            )
            continue

        hits = exact_match(phrase, index) + alt_match(phrase, index)
        out.extend(hits)
        if fallback_fuzzy_only and hits:
            if phrase_cache is not None:
                phrase_cache[cache_key] = [_candidate_to_cache_row(c) for c in hits]
            continue

        fuzzy_hits = fuzzy_match(phrase, index, threshold=threshold, limit=6)
        out.extend(fuzzy_hits)

        if phrase_cache is not None:
            phrase_cache[cache_key] = [_candidate_to_cache_row(c) for c in (hits + fuzzy_hits)]
    return out


def profile_filter(candidates: list[Candidate], profile: str, top_k: int) -> list[Candidate]:
    config = PROFILE_CONFIG[profile]
    drop_fuzzy = bool(config["drop_fuzzy_when_non_fuzzy"])
    max_fuzzy = int(config["max_fuzzy_per_raw"])

    by_raw_esco: dict[tuple[str, str], Candidate] = {}
    for cand in sorted(candidates, key=lambda c: c.confidence, reverse=True):
        key = (normalize_text(cand.raw_text), cand.esco_id)
        if key not in by_raw_esco or cand.confidence > by_raw_esco[key].confidence:
            by_raw_esco[key] = cand

    grouped: dict[str, list[Candidate]] = {}
    for cand in by_raw_esco.values():
        grouped.setdefault(normalize_text(cand.raw_text), []).append(cand)

    filtered: list[Candidate] = []
    for group in grouped.values():
        group = sorted(group, key=lambda c: c.confidence, reverse=True)
        has_non_fuzzy = any(c.match_method != "fuzzy" for c in group)
        fuzzy_count = 0
        for cand in group:
            if cand.match_method == "fuzzy":
                if drop_fuzzy and has_non_fuzzy:
                    continue
                if fuzzy_count >= max_fuzzy:
                    continue
                fuzzy_count += 1
            filtered.append(cand)

    best_by_esco: dict[str, Candidate] = {}
    for cand in filtered:
        if cand.esco_id not in best_by_esco or cand.confidence > best_by_esco[cand.esco_id].confidence:
            best_by_esco[cand.esco_id] = cand

    return sorted(best_by_esco.values(), key=lambda c: c.confidence, reverse=True)[:top_k]


def dedupe_best_by_esco(candidates: list[Candidate], top_k: int = 0) -> list[Candidate]:
    best_by_esco: dict[str, Candidate] = {}
    for cand in sorted(candidates, key=lambda c: c.confidence, reverse=True):
        current = best_by_esco.get(cand.esco_id)
        if current is None or cand.confidence > current.confidence:
            best_by_esco[cand.esco_id] = cand
    rows = sorted(best_by_esco.values(), key=lambda c: c.confidence, reverse=True)
    if top_k > 0:
        return rows[:top_k]
    return rows


def llm_occ_should_apply(runtime: LlmOccupationRuntime, occ_candidates: list[Candidate]) -> tuple[bool, str]:
    if not runtime.enabled:
        return False, runtime.disabled_reason or "llm runtime is disabled"
    if runtime.mode == "off":
        return False, "llm_occ_rerank_mode=off"
    if not occ_candidates:
        return False, "no occupation candidates"
    if runtime.mode == "always":
        return True, "mode=always"

    top_conf = float(occ_candidates[0].confidence)
    second_conf = float(occ_candidates[1].confidence) if len(occ_candidates) > 1 else None
    margin = (top_conf - second_conf) if second_conf is not None else None

    top_graph = occ_candidates[0].graph_support or {}
    top_hits = int(top_graph.get("essential_hits", 0)) + int(top_graph.get("optional_hits", 0))
    should = bool(
        (margin is not None and margin <= 0.03)
        or top_conf < 0.90
        or (top_conf < 0.85 and top_hits == 0)
    )
    if should:
        return True, "mode=low_conf_only and low-confidence condition matched"
    return False, "mode=low_conf_only and confidence condition not matched"


def build_resume_profile_fallback(
    *,
    category: str,
    occupation_phrases: list[str],
    experiences: list[dict[str, Any]],
) -> dict[str, Any]:
    top_title = ""
    for phrase in occupation_phrases:
        if normalize_text(phrase):
            top_title = normalize_spaces(phrase)
            break

    exp_snippet = build_experience_raw_snippet(experiences, max_chars=200)
    domains = unique_strings([category] + [tok for tok in normalize_spaces(top_title).split() if len(tok) >= 3])[:6]
    return {
        "core_role": top_title or category or "unknown",
        "management_scope": "",
        "domains": domains,
        "must_have_terms": unique_strings([top_title] + domains)[:8],
        "must_not_terms": [],
        "evidence_snippets": [exp_snippet] if exp_snippet else [],
    }


def llm_resume_profile(
    *,
    runtime: LlmOccupationRuntime,
    category: str,
    resume_text: str,
    occupation_phrases: list[str],
    skill_phrases: list[str],
    experiences: list[dict[str, Any]],
) -> dict[str, Any]:
    fallback = build_resume_profile_fallback(
        category=category,
        occupation_phrases=occupation_phrases,
        experiences=experiences,
    )
    if not runtime.enabled:
        return fallback

    title_hint = unique_strings(occupation_phrases)[:6]
    skill_hint = unique_strings(skill_phrases)[:14]
    exp_snippet = build_experience_raw_snippet(experiences, max_chars=500)
    resume_trim = normalize_spaces(resume_text)[: runtime.max_resume_chars]
    cache_src = json.dumps(
        {
            "category": category,
            "title_hint": title_hint,
            "skill_hint": skill_hint,
            "exp_snippet": exp_snippet,
            "resume_trim": resume_trim[:2000],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    cache_key = hashlib.sha1(cache_src.encode("utf-8")).hexdigest()
    cached = runtime.profile_cache.get(cache_key)
    if isinstance(cached, dict):
        runtime.profile_cache_hits += 1
        return cached

    system_prompt = (
        "You summarize resume evidence for occupation matching. "
        "Return strict JSON object only."
    )
    user_prompt = (
        "Create a compact role profile from resume evidence for ESCO occupation matching.\n"
        "Return JSON with keys:\n"
        "core_role (string), management_scope (string), domains (array[string]), "
        "must_have_terms (array[string]), must_not_terms (array[string]), evidence_snippets (array[string]).\n\n"
        f"Category: {category}\n"
        f"Title hints: {json.dumps(title_hint, ensure_ascii=False)}\n"
        f"Skill hints: {json.dumps(skill_hint, ensure_ascii=False)}\n"
        f"Experience snippet: {exp_snippet}\n"
        f"Resume text:\n{resume_trim}"
    )
    parsed = llm_chat_json(
        runtime,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
        max_tokens=900,
    )
    if not isinstance(parsed, dict):
        runtime.profile_cache[cache_key] = fallback
        return fallback

    profile = {
        "core_role": normalize_spaces(str(parsed.get("core_role") or fallback["core_role"]))[:140],
        "management_scope": normalize_spaces(str(parsed.get("management_scope") or ""))[:240],
        "domains": unique_strings(
            [str(v) for v in (parsed.get("domains") or []) if isinstance(v, (str, int, float))]
        )[:10]
        or fallback["domains"],
        "must_have_terms": unique_strings(
            [str(v) for v in (parsed.get("must_have_terms") or []) if isinstance(v, (str, int, float))]
        )[:14]
        or fallback["must_have_terms"],
        "must_not_terms": unique_strings(
            [str(v) for v in (parsed.get("must_not_terms") or []) if isinstance(v, (str, int, float))]
        )[:10],
        "evidence_snippets": unique_strings(
            [str(v) for v in (parsed.get("evidence_snippets") or []) if isinstance(v, (str, int, float))]
        )[:6]
        or fallback["evidence_snippets"],
    }
    runtime.profile_cache[cache_key] = profile
    return profile


def candidate_to_llm_payload(candidate: Candidate, occ_index: ConceptIndex) -> dict[str, Any]:
    meta = occ_index.get_meta(candidate.esco_id)
    hierarchy = candidate.hierarchy_json or occ_index.get_hierarchy(candidate.esco_id)
    hierarchy_labels = [normalize_spaces(str(v.get("label") or "")) for v in hierarchy if isinstance(v, dict)]
    graph = candidate.graph_support or {}
    return {
        "esco_id": candidate.esco_id,
        "preferred_label": normalize_spaces(meta.get("preferred_label") or candidate.preferred_label),
        "alt_labels": unique_strings([str(v) for v in (meta.get("alt_labels") or []) if isinstance(v, str)])[:10],
        "description": normalize_spaces(str(meta.get("description") or ""))[:450],
        "isco_group": normalize_spaces(str(meta.get("isco_group") or "")),
        "hierarchy_labels": [v for v in hierarchy_labels if v][:6],
        "raw_text": candidate.raw_text,
        "match_method": candidate.match_method,
        "base_confidence": round(float(candidate.confidence), 5),
        "graph_hits": int(graph.get("essential_hits", 0)) + int(graph.get("optional_hits", 0)),
    }


def apply_llm_occupation_rerank(
    *,
    occ_candidates: list[Candidate],
    occ_pool: list[Candidate],
    occ_index: ConceptIndex,
    runtime: LlmOccupationRuntime | None,
    category: str,
    resume_text: str,
    occupation_phrases: list[str],
    skill_phrases: list[str],
    experiences: list[dict[str, Any]],
    top_k: int,
) -> tuple[list[Candidate], dict[str, Any]]:
    debug = {
        "mode": runtime.mode if runtime is not None else "off",
        "enabled": bool(runtime is not None and runtime.enabled),
        "applied": False,
        "reason": None,
        "candidate_count": 0,
        "judge_runs": 0,
        "consensus_rate": None,
        "top1_before": occ_candidates[0].esco_id if occ_candidates else None,
        "top1_after": occ_candidates[0].esco_id if occ_candidates else None,
        "fallback_used": False,
    }
    if runtime is None:
        debug["reason"] = "llm runtime is not configured"
        return occ_candidates, debug

    should_apply, reason = llm_occ_should_apply(runtime, occ_candidates)
    debug["reason"] = reason
    if not should_apply:
        return occ_candidates, debug

    pool = dedupe_best_by_esco(occ_pool + occ_candidates)
    pool = pool[: max(int(top_k), int(runtime.candidate_k))]
    pool = pool[: int(runtime.candidate_k)]
    debug["candidate_count"] = len(pool)
    if len(pool) < 2:
        debug["reason"] = "candidate pool is too small"
        debug["fallback_used"] = True
        return occ_candidates, debug

    profile = llm_resume_profile(
        runtime=runtime,
        category=category,
        resume_text=resume_text,
        occupation_phrases=occupation_phrases,
        skill_phrases=skill_phrases,
        experiences=experiences,
    )

    payload_candidates = [candidate_to_llm_payload(cand, occ_index) for cand in pool]
    allowed_ids = [row["esco_id"] for row in payload_candidates]
    allowed_id_set = set(allowed_ids)

    fit_scores: dict[str, list[float]] = {esco_id: [] for esco_id in allowed_ids}
    rank_scores: dict[str, float] = {esco_id: 0.0 for esco_id in allowed_ids}
    top1_votes: Counter[str] = Counter()
    successful_judges = 0

    for judge_id in range(1, int(runtime.jury_size) + 1):
        system_prompt = (
            "You are an ESCO occupation adjudicator. "
            "Use role/domain/seniority evidence from resume profile and occupation definitions. "
            "Penalize domain mismatch. Return strict JSON."
        )
        user_prompt = (
            f"Judge #{judge_id}\n"
            "Task: score each candidate and provide ranked occupation IDs.\n"
            "Return JSON keys: scores (array), ranked_esco_ids (array).\n"
            "scores item keys: esco_id, fit_score (0-100), conflicts (array[string]), reason_short (string).\n\n"
            f"Resume profile: {json.dumps(profile, ensure_ascii=False)}\n"
            f"Candidates: {json.dumps(payload_candidates, ensure_ascii=False)}"
        )
        parsed = llm_chat_json(
            runtime,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=runtime.temperature,
            max_tokens=1800,
        )
        if not isinstance(parsed, dict):
            continue

        score_map: dict[str, float] = {}
        for item in parsed.get("scores") or []:
            if not isinstance(item, dict):
                continue
            esco_id = str(item.get("esco_id") or "").strip()
            if esco_id not in allowed_id_set:
                continue
            try:
                fit_score = float(item.get("fit_score", 0.0))
            except Exception:
                fit_score = 0.0
            score_map[esco_id] = max(0.0, min(100.0, fit_score))

        ranked_ids: list[str] = []
        seen_ranked: set[str] = set()
        for value in parsed.get("ranked_esco_ids") or []:
            esco_id = str(value or "").strip()
            if esco_id in allowed_id_set and esco_id not in seen_ranked:
                ranked_ids.append(esco_id)
                seen_ranked.add(esco_id)
        if not ranked_ids:
            ranked_ids = [
                esco_id
                for esco_id, _ in sorted(
                    score_map.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ]
        for esco_id in allowed_ids:
            if esco_id not in seen_ranked:
                ranked_ids.append(esco_id)
                seen_ranked.add(esco_id)

        if not ranked_ids:
            continue

        successful_judges += 1
        top1_votes[ranked_ids[0]] += 1
        for rank, esco_id in enumerate(ranked_ids, start=1):
            rank_scores[esco_id] += 1.0 / float(60 + rank)
        for esco_id in allowed_ids:
            fit_scores[esco_id].append(score_map.get(esco_id, 0.0))

    debug["judge_runs"] = successful_judges
    if successful_judges == 0:
        debug["reason"] = "llm calls failed for all judges"
        debug["fallback_used"] = True
        return occ_candidates, debug

    base_by_esco = {cand.esco_id: cand for cand in pool}
    max_rank_score = max([rank_scores[v] for v in allowed_ids] + [1e-9])
    reranked: list[Candidate] = []
    for esco_id in allowed_ids:
        base = base_by_esco[esco_id]
        scores = fit_scores.get(esco_id) or []
        avg_fit = (sum(scores) / len(scores)) if scores else 0.0
        rank_norm = float(rank_scores.get(esco_id, 0.0)) / float(max_rank_score)
        llm_conf = (avg_fit / 100.0) * 0.75 + rank_norm * 0.25
        merged_conf = max(0.0, min(1.0, (float(base.confidence) * 0.35) + (llm_conf * 0.65)))
        reranked.append(
            Candidate(
                esco_id=base.esco_id,
                preferred_label=base.preferred_label,
                raw_text=base.raw_text,
                confidence=round(merged_conf, 5),
                match_method=base.match_method,
                hierarchy_json=base.hierarchy_json,
                source_span=base.source_span,
                graph_support=base.graph_support,
                base_confidence=base.base_confidence,
                llm_fit_score=round(avg_fit, 2),
                llm_rank_score=round(rank_norm, 5),
            )
        )

    reranked = sorted(
        reranked,
        key=lambda cand: (
            cand.confidence,
            cand.llm_fit_score if cand.llm_fit_score is not None else 0.0,
        ),
        reverse=True,
    )[:top_k]
    if not reranked:
        debug["reason"] = "llm rerank returned no candidates"
        debug["fallback_used"] = True
        return occ_candidates, debug

    top1_after = reranked[0].esco_id
    top1_votes_total = sum(top1_votes.values())
    consensus_rate = (
        float(top1_votes.get(top1_after, 0)) / float(top1_votes_total)
        if top1_votes_total > 0
        else 0.0
    )

    debug.update(
        {
            "applied": True,
            "reason": "llm rerank applied",
            "consensus_rate": round(consensus_rate, 5),
            "top1_after": top1_after,
            "fallback_used": False,
        }
    )
    return reranked, debug


def apply_graph_rerank(
    occ_candidates: list[Candidate],
    matched_skill_uris: set[str],
    graph: OccupationSkillGraph,
    essential_weight: float,
    optional_weight: float,
    max_boost: float,
) -> tuple[list[Candidate], bool, bool]:
    if not occ_candidates:
        return occ_candidates, False, False

    before = [c.esco_id for c in occ_candidates]
    applied = False
    updated: list[Candidate] = []

    for cand in occ_candidates:
        support = graph.support(cand.esco_id, matched_skill_uris, essential_weight, optional_weight, max_boost)
        base = cand.confidence
        new_conf = min(1.0, base + float(support["boost"]))
        if support["essential_hits"] > 0 or support["optional_hits"] > 0:
            applied = True
        updated.append(
            Candidate(
                esco_id=cand.esco_id,
                preferred_label=cand.preferred_label,
                raw_text=cand.raw_text,
                confidence=round(new_conf, 5),
                match_method=cand.match_method,
                hierarchy_json=cand.hierarchy_json,
                source_span=cand.source_span,
                graph_support=support,
                base_confidence=round(base, 5),
            )
        )

    reranked = sorted(updated, key=lambda c: c.confidence, reverse=True)
    changed = before != [c.esco_id for c in reranked]
    return reranked, applied, changed


def candidate_rows(candidates: list[Candidate]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rank, cand in enumerate(candidates, start=1):
        row: dict[str, Any] = {
            "esco_id": cand.esco_id,
            "preferred_label": cand.preferred_label,
            "raw_text": cand.raw_text,
            "confidence": round(cand.confidence, 5),
            "match_method": cand.match_method,
            "rank": rank,
            "is_primary": rank == 1,
            "hierarchy_json": cand.hierarchy_json,
            "source_span": cand.source_span,
        }
        if cand.base_confidence is not None:
            row["base_confidence"] = cand.base_confidence
        if cand.graph_support is not None:
            row["graph_support"] = cand.graph_support
        if cand.llm_fit_score is not None:
            row["llm_fit_score"] = cand.llm_fit_score
        if cand.llm_rank_score is not None:
            row["llm_rank_score"] = cand.llm_rank_score
        out.append(row)
    return out


def apply_occupation_guardrails(
    occ_candidates: list[Candidate],
    category: str,
    profile: str,
) -> tuple[list[Candidate], dict[str, Any]]:
    if not occ_candidates:
        return occ_candidates, {"removed_count": 0, "removed_examples": []}

    low_conf_cutoff = 0.85 if profile in {"precision", "balanced"} else 0.82
    kept: list[Candidate] = []
    removed_examples: list[dict[str, Any]] = []

    for cand in occ_candidates:
        graph = cand.graph_support or {}
        graph_hits = int(graph.get("essential_hits", 0)) + int(graph.get("optional_hits", 0))
        category_ok = label_matches_category(cand.preferred_label, category)

        # Rule: suppress likely fuzzy misfire when all evidence is weak.
        is_low_conf_misfire = bool(
            cand.match_method == "fuzzy"
            and cand.confidence < low_conf_cutoff
            and graph_hits == 0
            and not category_ok
        )

        if is_low_conf_misfire:
            if len(removed_examples) < 5:
                removed_examples.append(
                    {
                        "label": cand.preferred_label,
                        "confidence": round(cand.confidence, 5),
                        "match_method": cand.match_method,
                        "graph_hits": graph_hits,
                    }
                )
            continue

        kept.append(cand)

    # Prefer abstaining over returning clearly noisy fuzzy-only results.
    return kept, {"removed_count": len(occ_candidates) - len(kept), "removed_examples": removed_examples}


def build_llm_handoff(
    occ_rows: list[dict[str, Any]],
    skill_rows: list[dict[str, Any]],
    normalization_status: str,
) -> dict[str, Any]:
    top_conf = float(occ_rows[0]["confidence"]) if occ_rows else 0.0
    second_conf = float(occ_rows[1]["confidence"]) if len(occ_rows) > 1 else None
    margin = (top_conf - second_conf) if second_conf is not None else None

    top_graph = occ_rows[0].get("graph_support") if occ_rows else None
    top_hits = 0
    if isinstance(top_graph, dict):
        top_hits = int(top_graph.get("essential_hits", 0)) + int(top_graph.get("optional_hits", 0))

    rerank_trigger = bool(
        len(occ_rows) >= 2
        and (
            (
                margin is not None
                and margin <= 0.03
                and top_conf < 0.92
            )
            or (top_conf < 0.85 and top_hits == 0)
        )
    )

    extraction_trigger = bool(
        normalization_status != "success"
        or len(skill_rows) < 3
        or top_conf < 0.82
    )

    return {
        "rerank_trigger": rerank_trigger,
        "extraction_trigger": extraction_trigger,
        "top_occupation_confidence": round(top_conf, 5),
        "top2_margin": round(margin, 5) if margin is not None else None,
        "top_graph_hits": top_hits,
        "skill_candidate_count": len(skill_rows),
    }


def extract_titles_from_text(resume_text: str) -> list[str]:
    return unique_strings([m.group(1).strip() for m in TITLE_PATTERN.finditer(normalize_spaces(resume_text))])[:20]


def extract_skills_from_text(resume_text: str) -> list[str]:
    text = normalize_spaces(resume_text)
    if not text:
        return []
    parts = re.split(r"[\n,;|•\-]+", text[:1500])
    raw = []
    for part in parts:
        phrase = normalize_spaces(part)
        if len(phrase) < 2 or len(phrase) > 100:
            continue
        raw.append(phrase)
    return unique_strings(raw)[:30]


def get_payload(doc: dict[str, Any]) -> dict[str, Any]:
    extracted = doc.get("extracted_fields")
    if isinstance(extracted, dict):
        occ = [v for v in (extracted.get("occupation_candidates") or []) if isinstance(v, str)]
        skill = []
        for item in extracted.get("skills") or []:
            if isinstance(item, dict) and isinstance(item.get("raw_text"), str):
                skill.append(item["raw_text"])
            elif isinstance(item, str):
                skill.append(item)

        return {
            "occupation_phrases": unique_strings(occ)[:20],
            "skill_phrases": unique_strings(skill)[:35],
            "experiences": extracted.get("experiences") if isinstance(extracted.get("experiences"), list) else [],
            "educations": extracted.get("educations") if isinstance(extracted.get("educations"), list) else [],
            "current_location": extracted.get("current_location") if isinstance(extracted.get("current_location"), str) else None,
        }

    if extract_all_fields is not None and fields_to_dict is not None:
        try:
            ef_dict = fields_to_dict(extract_all_fields(doc))
            return get_payload({"extracted_fields": ef_dict})
        except Exception:
            pass

    resume_text = doc.get("resume_text") or ""
    return {
        "occupation_phrases": extract_titles_from_text(resume_text),
        "skill_phrases": extract_skills_from_text(resume_text),
        "experiences": [],
        "educations": [],
        "current_location": None,
    }


def resolve_threshold(base: float, strictness: str) -> float:
    return max(0.5, min(0.99, base + STRICTNESS_DELTA[strictness]))


def build_doc(
    src: dict[str, Any],
    occ_index: ConceptIndex,
    skill_index: ConceptIndex,
    graph: OccupationSkillGraph,
    occ_phrase_cache: dict[str, list[dict[str, Any]]],
    skill_phrase_cache: dict[str, list[dict[str, Any]]],
    profile: str,
    strictness: str,
    graph_essential_weight: float,
    graph_optional_weight: float,
    graph_max_boost: float,
    embedding_runtime: EmbeddingRuntime | None = None,
    llm_occ_runtime: LlmOccupationRuntime | None = None,
) -> tuple[dict[str, Any], bool, bool]:
    cfg = PROFILE_CONFIG[profile]
    occ_threshold = resolve_threshold(cfg["occ_threshold"], strictness)
    skill_threshold = resolve_threshold(cfg["skill_threshold"], strictness)

    source_dataset = (src.get("source_dataset") or "1st_data").strip()
    source_record_id = str(src.get("source_record_id") or "").strip()
    category = normalize_spaces(src.get("category") or "")
    resume_text = src.get("resume_text") or ""

    payload = get_payload(src)
    occupation_phrases = payload["occupation_phrases"]
    if category:
        category_phrases = category_anchor_phrases(category)
        occupation_phrases = unique_strings([category] + category_phrases + occupation_phrases)
    if not occupation_phrases:
        occupation_phrases = extract_titles_from_text(resume_text)

    skill_phrases = payload["skill_phrases"]
    if not skill_phrases:
        skill_phrases = extract_skills_from_text(resume_text)
    experiences = payload.get("experiences") or []

    raw_occ = staged_match(
        occupation_phrases,
        occ_index,
        occ_threshold,
        bool(cfg["fallback_fuzzy_only"]),
        phrase_cache=occ_phrase_cache,
    )
    raw_skill = staged_match(
        skill_phrases,
        skill_index,
        skill_threshold,
        bool(cfg["fallback_fuzzy_only"]),
        phrase_cache=skill_phrase_cache,
    )

    embedding_occ_a: list[Candidate] = []
    embedding_occ_b1: list[Candidate] = []
    embedding_occ: list[Candidate] = []
    embedding_skill: list[Candidate] = []
    if embedding_runtime is not None and embedding_runtime.enabled:
        embedding_occ_a = embedding_match(
            occupation_phrases,
            occ_index,
            embedding_runtime,
            target="occupation",
        )
        occ_b1_queries = build_occupation_b1_queries(occupation_phrases, experiences)
        embedding_occ_b1 = embedding_match(
            occ_b1_queries,
            occ_index,
            embedding_runtime,
            target="occupation",
        )
        embedding_occ = rrf_fuse_embedding_candidates(
            embedding_occ_a,
            embedding_occ_b1,
            top_k=embedding_runtime.occ_top_k,
        )
        embedding_skill = embedding_match(
            skill_phrases,
            skill_index,
            embedding_runtime,
            target="skill",
        )
        raw_occ.extend(embedding_occ)
        raw_skill.extend(embedding_skill)

    occ_pool_for_llm = dedupe_best_by_esco(raw_occ, top_k=max(int(cfg["top_occ"]), 60))
    occ_candidates = profile_filter(raw_occ, profile=profile, top_k=int(cfg["top_occ"]))
    skill_candidates = profile_filter(raw_skill, profile=profile, top_k=int(cfg["top_skill"]))

    matched_skill_uris = {c.esco_id for c in skill_candidates if c.confidence >= 0.70}
    occ_candidates, graph_applied, graph_changed = apply_graph_rerank(
        occ_candidates,
        matched_skill_uris=matched_skill_uris,
        graph=graph,
        essential_weight=graph_essential_weight,
        optional_weight=graph_optional_weight,
        max_boost=graph_max_boost,
    )
    occ_candidates, llm_occ_debug = apply_llm_occupation_rerank(
        occ_candidates=occ_candidates,
        occ_pool=occ_pool_for_llm,
        occ_index=occ_index,
        runtime=llm_occ_runtime,
        category=category,
        resume_text=resume_text,
        occupation_phrases=occupation_phrases,
        skill_phrases=skill_phrases,
        experiences=experiences,
        top_k=int(cfg["top_occ"]),
    )
    occ_candidates, guardrail_debug = apply_occupation_guardrails(
        occ_candidates,
        category=category,
        profile=profile,
    )

    occ_rows = candidate_rows(occ_candidates)
    skill_rows = candidate_rows(skill_candidates)

    if occ_rows and skill_rows:
        status = "success"
    elif occ_rows or skill_rows:
        status = "partial"
    else:
        status = "failed"

    confidence_scores = []
    if occ_rows:
        confidence_scores.append(float(occ_rows[0]["confidence"]))
    if skill_rows:
        confidence_scores.append(float(skill_rows[0]["confidence"]))
    extraction_confidence = round(sum(confidence_scores) / len(confidence_scores), 5) if confidence_scores else None
    llm_handoff = build_llm_handoff(occ_rows, skill_rows, status)
    embedding_debug = {
        "mode": embedding_runtime.mode if embedding_runtime is not None else "off",
        "enabled": bool(embedding_runtime is not None and embedding_runtime.enabled),
        "disabled_reason": (
            embedding_runtime.disabled_reason if (embedding_runtime is not None and not embedding_runtime.enabled) else None
        ),
        "occupation_a_candidate_count": len(embedding_occ_a),
        "occupation_b1_candidate_count": len(embedding_occ_b1),
        "occupation_fused_candidate_count": len(embedding_occ),
        "skill_a_candidate_count": len(embedding_skill),
    }

    out = {
        "source_dataset": source_dataset,
        "source_record_id": source_record_id,
        "category": category,
        "normalizer_version": NORMALIZER_VERSION,
        "normalized_at": datetime.utcnow(),
        "normalization_status": status,
        "current_location": payload.get("current_location"),
        "resume_text": resume_text,
        "extraction_confidence": extraction_confidence,
        "occupation_candidates": occ_rows,
        "skill_candidates": skill_rows,
        "experiences": experiences,
        "educations": payload.get("educations") or [],
        "llm_handoff": llm_handoff,
        "matching_debug": {
            "ranking_profile": profile,
            "threshold_strictness": strictness,
            "fuzzy_thresholds": {
                "occupation": occ_threshold,
                "skill": skill_threshold,
            },
            "graph": {
                "essential_weight": graph_essential_weight,
                "optional_weight": graph_optional_weight,
                "max_boost": graph_max_boost,
                "rerank_applied": graph_applied,
                "rank_changed": graph_changed,
            },
            "embedding": embedding_debug,
            "llm_occupation": llm_occ_debug,
            "category_guardrail": guardrail_debug,
            "llm_handoff": llm_handoff,
        },
    }

    return out, graph_applied, graph_changed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Issue #10 simple ESCO normalization pipeline")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db-name", default="prodapt_capstone")
    parser.add_argument("--source-collection", default="source_1st_resumes")
    parser.add_argument("--output-collection", default="normalized_candidates")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--source-record-ids",
        default="",
        help="Comma-separated source_record_id list for targeted run (optional).",
    )
    parser.add_argument("--fetch-batch-size", type=int, default=250)
    parser.add_argument("--write-batch-size", type=int, default=250)
    parser.add_argument("--ranking-profile", choices=["precision", "balanced", "coverage"], default="balanced")
    parser.add_argument("--threshold-strictness", choices=["strict", "medium", "lenient"], default="medium")
    parser.add_argument("--graph-essential-weight", type=float, default=0.03)
    parser.add_argument("--graph-optional-weight", type=float, default=0.015)
    parser.add_argument("--graph-max-boost", type=float, default=0.20)
    parser.add_argument("--embedding-mode", choices=["auto", "off"], default="auto")
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument("--embedding-occ-top-k", type=int, default=12)
    parser.add_argument("--embedding-skill-top-k", type=int, default=20)
    parser.add_argument("--embedding-min-confidence", type=float, default=0.58)
    parser.add_argument("--embedding-confidence-scale", type=float, default=0.90)
    parser.add_argument("--embedding-occ-query-limit", type=int, default=5)
    parser.add_argument("--embedding-skill-query-limit", type=int, default=8)
    parser.add_argument("--openai-api-key", default="")
    parser.add_argument("--milvus-uri", default="")
    parser.add_argument("--milvus-token", default="")
    parser.add_argument("--milvus-db-name", default="")
    parser.add_argument("--milvus-occ-collection", default="")
    parser.add_argument("--milvus-skill-collection", default="")
    parser.add_argument("--milvus-metric-type", default="COSINE")
    parser.add_argument("--milvus-search-ef", type=int, default=64)
    parser.add_argument("--llm-occ-rerank-mode", choices=["off", "low_conf_only", "always"], default="always")
    parser.add_argument("--llm-occ-model", default="gpt-4.1-mini")
    parser.add_argument("--llm-occ-candidate-k", type=int, default=30)
    parser.add_argument("--llm-occ-jury-size", type=int, default=5)
    parser.add_argument("--llm-occ-temperature", type=float, default=0.2)
    parser.add_argument("--llm-occ-max-resume-chars", type=int, default=5000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--metrics-out", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_ids = [x.strip() for x in (args.source_record_ids or "").split(",") if x.strip()]
    embedding_runtime = build_embedding_runtime(args)
    llm_occ_runtime = build_llm_occ_runtime(
        args,
        shared_openai_client=embedding_runtime.openai_client if embedding_runtime.enabled else None,
    )
    if embedding_runtime.enabled:
        print(
            "Embedding search enabled: "
            f"model={embedding_runtime.model}, "
            f"occ_top_k={embedding_runtime.occ_top_k}, "
            f"skill_top_k={embedding_runtime.skill_top_k}"
        )
    else:
        print(f"Embedding search disabled: {embedding_runtime.disabled_reason}")
    if llm_occ_runtime.enabled:
        print(
            "LLM occupation rerank enabled: "
            f"mode={llm_occ_runtime.mode}, "
            f"model={llm_occ_runtime.model}, "
            f"candidate_k={llm_occ_runtime.candidate_k}, "
            f"jury_size={llm_occ_runtime.jury_size}"
        )
    else:
        print(f"LLM occupation rerank disabled: {llm_occ_runtime.disabled_reason}")

    client = MongoClient(args.mongo_uri)
    db = client[args.db_name]
    source = db[args.source_collection]
    output = db[args.output_collection]

    output.create_index([("source_dataset", 1), ("source_record_id", 1)], unique=True, name="uq_source_record")
    output.create_index("candidate_id", name="idx_candidate_id")
    output.create_index("normalization_status", name="idx_normalization_status")
    output.create_index("llm_handoff.rerank_trigger", name="idx_llm_rerank_trigger")
    output.create_index("llm_handoff.extraction_trigger", name="idx_llm_extraction_trigger")

    print("Loading ESCO collections...")
    occ_rows = list(db["raw_esco_occupations"].find({}, {"_id": 0}))
    skill_rows = list(db["raw_esco_skills"].find({}, {"_id": 0}))
    broader_occ = list(db["raw_esco_broader_relations_occ"].find({}, {"_id": 0}))
    broader_skill = list(db["raw_esco_broader_relations_skill"].find({}, {"_id": 0}))
    relations = list(db["raw_esco_occupation_skill_relations"].find({}, {"_id": 0}))

    occ_index = ConceptIndex(occ_rows, broader_occ)
    skill_index = ConceptIndex(skill_rows, broader_skill)
    graph = OccupationSkillGraph(relations)
    occ_phrase_cache: dict[str, list[dict[str, Any]]] = {}
    skill_phrase_cache: dict[str, list[dict[str, Any]]] = {}

    metrics = {
        "processed_docs": 0,
        "graph_rerank_applied_docs": 0,
        "graph_rank_changed_docs": 0,
        "embedding_occ_docs": 0,
        "embedding_skill_docs": 0,
        "llm_rerank_trigger_docs": 0,
        "llm_extraction_trigger_docs": 0,
        "llm_occ_applied_docs": 0,
        "llm_occ_fallback_docs": 0,
        "normalization_status_counts": Counter(),
        "occ_method_counts": Counter(),
        "skill_method_counts": Counter(),
        "occ_candidate_total": 0,
        "skill_candidate_total": 0,
    }

    ops: list[UpdateOne] = []
    count = 0
    last_id = None
    started_at = time.time()

    print("Starting normalization...")
    while True:
        if args.limit and count >= args.limit:
            break

        query: dict[str, Any] = {"source_dataset": "1st_data"}
        if selected_ids:
            query["source_record_id"] = {"$in": selected_ids}
        if last_id is not None:
            query["_id"] = {"$gt": last_id}

        remaining = (args.limit - count) if args.limit else args.fetch_batch_size
        batch_size = min(args.fetch_batch_size, remaining) if args.limit else args.fetch_batch_size

        docs = list(
            source.find(
                query,
                {
                    "_id": 1,
                    "source_dataset": 1,
                    "source_record_id": 1,
                    "category": 1,
                    "resume_text": 1,
                    "resume_html": 1,
                    "parsed_sections": 1,
                    "parsing_method": 1,
                    "extracted_fields": 1,
                },
            )
            .sort("_id", 1)
            .limit(batch_size)
        )
        if not docs:
            break

        for src in docs:
            normalized, graph_applied, graph_changed = build_doc(
                src,
                occ_index=occ_index,
                skill_index=skill_index,
                graph=graph,
                occ_phrase_cache=occ_phrase_cache,
                skill_phrase_cache=skill_phrase_cache,
                profile=args.ranking_profile,
                strictness=args.threshold_strictness,
                graph_essential_weight=args.graph_essential_weight,
                graph_optional_weight=args.graph_optional_weight,
                graph_max_boost=args.graph_max_boost,
                embedding_runtime=embedding_runtime,
                llm_occ_runtime=llm_occ_runtime,
            )

            key = {
                "source_dataset": normalized["source_dataset"],
                "source_record_id": normalized["source_record_id"],
            }
            ops.append(
                UpdateOne(
                    key,
                    {
                        "$set": normalized,
                        "$setOnInsert": {"candidate_id": str(uuid.uuid4())},
                    },
                    upsert=True,
                )
            )

            metrics["processed_docs"] += 1
            metrics["normalization_status_counts"][normalized["normalization_status"]] += 1
            if graph_applied:
                metrics["graph_rerank_applied_docs"] += 1
            if graph_changed:
                metrics["graph_rank_changed_docs"] += 1
            llm_handoff = normalized.get("llm_handoff") or {}
            if llm_handoff.get("rerank_trigger"):
                metrics["llm_rerank_trigger_docs"] += 1
            if llm_handoff.get("extraction_trigger"):
                metrics["llm_extraction_trigger_docs"] += 1
            llm_occ_debug = ((normalized.get("matching_debug") or {}).get("llm_occupation") or {})
            if llm_occ_debug.get("applied"):
                metrics["llm_occ_applied_docs"] += 1
            if llm_occ_debug.get("fallback_used"):
                metrics["llm_occ_fallback_docs"] += 1

            occ_rows = normalized["occupation_candidates"]
            skill_rows = normalized["skill_candidates"]
            metrics["occ_candidate_total"] += len(occ_rows)
            metrics["skill_candidate_total"] += len(skill_rows)
            for row in occ_rows:
                metrics["occ_method_counts"][row.get("match_method", "unknown")] += 1
            for row in skill_rows:
                metrics["skill_method_counts"][row.get("match_method", "unknown")] += 1
            if any(row.get("match_method") in {"embedding", "embedding_b1"} for row in occ_rows):
                metrics["embedding_occ_docs"] += 1
            if any(row.get("match_method") == "embedding" for row in skill_rows):
                metrics["embedding_skill_docs"] += 1

            count += 1
            if count % 50 == 0:
                elapsed = max(1e-6, time.time() - started_at)
                rate = count / elapsed
                print(
                    f"Processed {count} docs... "
                    f"({rate:.2f} docs/s, occ_cache={len(occ_phrase_cache)}, skill_cache={len(skill_phrase_cache)})"
                )

            if not args.dry_run and len(ops) >= args.write_batch_size:
                output.bulk_write(ops, ordered=False)
                ops.clear()

            if args.limit and count >= args.limit:
                break

        last_id = docs[-1]["_id"]

    if not args.dry_run and ops:
        output.bulk_write(ops, ordered=False)

    processed = max(1, metrics["processed_docs"])
    summary = {
        "normalizer_version": NORMALIZER_VERSION,
        "run_at_utc": datetime.utcnow().isoformat(),
        "db_name": args.db_name,
        "source_collection": args.source_collection,
        "output_collection": args.output_collection,
        "profile": args.ranking_profile,
        "threshold_strictness": args.threshold_strictness,
        "source_record_ids_filter": selected_ids,
        "graph_weights": {
            "essential": args.graph_essential_weight,
            "optional": args.graph_optional_weight,
            "max_boost": args.graph_max_boost,
        },
        "embedding": embedding_runtime.summary(),
        "llm_occupation_rerank": llm_occ_runtime.summary(),
        "dry_run": args.dry_run,
        "metrics": {
            "processed_docs": metrics["processed_docs"],
            "graph_rerank_applied_docs": metrics["graph_rerank_applied_docs"],
            "graph_rank_changed_docs": metrics["graph_rank_changed_docs"],
            "embedding_occ_docs": metrics["embedding_occ_docs"],
            "embedding_skill_docs": metrics["embedding_skill_docs"],
            "llm_rerank_trigger_docs": metrics["llm_rerank_trigger_docs"],
            "llm_extraction_trigger_docs": metrics["llm_extraction_trigger_docs"],
            "llm_occ_applied_docs": metrics["llm_occ_applied_docs"],
            "llm_occ_fallback_docs": metrics["llm_occ_fallback_docs"],
            "normalization_status_counts": dict(metrics["normalization_status_counts"]),
            "occ_method_counts": dict(metrics["occ_method_counts"]),
            "skill_method_counts": dict(metrics["skill_method_counts"]),
            "avg_occ_candidates": round(metrics["occ_candidate_total"] / processed, 3),
            "avg_skill_candidates": round(metrics["skill_candidate_total"] / processed, 3),
            "elapsed_seconds": round(time.time() - started_at, 2),
            "occ_phrase_cache_size": len(occ_phrase_cache),
            "skill_phrase_cache_size": len(skill_phrase_cache),
        },
    }

    print("\nNormalization summary")
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))

    if args.metrics_out:
        path = Path(args.metrics_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        print(f"Metrics written: {path}")


if __name__ == "__main__":
    main()
