from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pymongo import MongoClient, ReplaceOne, UpdateOne
from rapidfuzz import fuzz, process

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


NORMALIZER_VERSION = "v0.1.0"
FUZZY_THRESHOLD = 0.85
LLM_DEFAULT_MODEL = "gpt-4.1-mini"

GENERIC_TERMS = {
    "construction",
    "material",
    "materials",
    "methods",
    "software",
    "management",
    "specifications",
    "skills",
    "experience",
    "education",
    "company",
    "state",
    "city",
}


# ---------------------------
# Matching model
# ---------------------------
@dataclass
class ConceptEntry:
    esco_id: str
    preferred_label: str
    label_type: str  # preferred | alt


@dataclass
class MatchCandidate:
    esco_id: str
    preferred_label: str
    raw_text: str
    confidence: float
    match_method: str
    hierarchy: list[dict[str, str]]
    source_span: str | None = None


class BaseMatcher(ABC):
    @abstractmethod
    def match(self, phrase: str, index: "ConceptIndex") -> list[MatchCandidate]:
        raise NotImplementedError


class ExactMatcher(BaseMatcher):
    def match(self, phrase: str, index: "ConceptIndex") -> list[MatchCandidate]:
        key = normalize_text(phrase)
        matches = index.preferred_map.get(key, [])
        return [
            MatchCandidate(
                esco_id=m.esco_id,
                preferred_label=m.preferred_label,
                raw_text=phrase,
                confidence=1.0,
                match_method="exact",
                hierarchy=index.get_hierarchy(m.esco_id),
                source_span=phrase,
            )
            for m in matches
        ]


class AltLabelMatcher(BaseMatcher):
    def match(self, phrase: str, index: "ConceptIndex") -> list[MatchCandidate]:
        key = normalize_text(phrase)
        matches = index.alt_map.get(key, [])
        return [
            MatchCandidate(
                esco_id=m.esco_id,
                preferred_label=m.preferred_label,
                raw_text=phrase,
                confidence=0.95,
                match_method="alt_label",
                hierarchy=index.get_hierarchy(m.esco_id),
                source_span=phrase,
            )
            for m in matches
        ]


class FuzzyMatcher(BaseMatcher):
    def __init__(self, threshold: float = FUZZY_THRESHOLD, limit: int = 5) -> None:
        self.threshold = threshold
        self.limit = limit

    def match(self, phrase: str, index: "ConceptIndex") -> list[MatchCandidate]:
        key = normalize_text(phrase)
        if not key:
            return []

        key_tokens = [t for t in re.findall(r"[a-z]{2,}", key) if t not in GENERIC_TERMS]
        # Avoid noisy fuzzy matching for short/single-token phrases
        if len(key_tokens) < 2:
            return []

        result = process.extract(
            key,
            index.search_labels,
            scorer=fuzz.token_set_ratio,
            limit=self.limit,
        )

        out: list[MatchCandidate] = []
        for label_norm, score, _ in result:
            conf = score / 100.0
            if conf < self.threshold:
                continue

            label_tokens = set(re.findall(r"[a-z]{2,}", label_norm))
            overlap = len(set(key_tokens) & label_tokens)
            if len(key_tokens) >= 2 and overlap == 0:
                continue

            for entry in index.label_to_entries.get(label_norm, []):
                out.append(
                    MatchCandidate(
                        esco_id=entry.esco_id,
                        preferred_label=entry.preferred_label,
                        raw_text=phrase,
                        confidence=round(conf * 0.92, 5),
                        match_method="fuzzy",
                        hierarchy=index.get_hierarchy(entry.esco_id),
                        source_span=phrase,
                    )
                )
        return out


# Future extension point
class LLMMatcher(BaseMatcher):
    def match(self, phrase: str, index: "ConceptIndex") -> list[MatchCandidate]:
        return []


class ConceptIndex:
    def __init__(self, concepts: list[dict[str, Any]], broader_relations: list[dict[str, Any]]) -> None:
        self.preferred_map: dict[str, list[ConceptEntry]] = {}
        self.alt_map: dict[str, list[ConceptEntry]] = {}
        self.label_to_entries: dict[str, list[ConceptEntry]] = {}
        self.search_labels: list[str] = []
        self._broader_map: dict[str, list[dict[str, str]]] = {}
        self._hierarchy_cache: dict[str, list[dict[str, str]]] = {}

        # hierarchy map
        for row in broader_relations:
            child = (row.get("concept_uri") or row.get("conceptUri") or "").strip()
            parent = (row.get("broader_uri") or row.get("broaderUri") or "").strip()
            parent_label = (row.get("broader_label") or row.get("broaderLabel") or "").strip()
            if child and parent:
                self._broader_map.setdefault(child, []).append({"id": parent, "label": parent_label})

        # concept labels
        for row in concepts:
            esco_id = (row.get("concept_uri") or row.get("conceptUri") or "").strip()
            preferred = (row.get("preferred_label") or row.get("preferredLabel") or "").strip()
            if not esco_id or not preferred:
                continue

            pref_norm = normalize_text(preferred)
            entry = ConceptEntry(esco_id=esco_id, preferred_label=preferred, label_type="preferred")
            self.preferred_map.setdefault(pref_norm, []).append(entry)
            self.label_to_entries.setdefault(pref_norm, []).append(entry)

            for alt in row.get("alt_labels_list") or []:
                alt_norm = normalize_text(alt)
                if not alt_norm:
                    continue
                alt_entry = ConceptEntry(esco_id=esco_id, preferred_label=preferred, label_type="alt")
                self.alt_map.setdefault(alt_norm, []).append(alt_entry)
                self.label_to_entries.setdefault(alt_norm, []).append(alt_entry)

        self.search_labels = sorted(self.label_to_entries.keys())

    def get_hierarchy(self, concept_uri: str, max_depth: int = 5) -> list[dict[str, str]]:
        cached = self._hierarchy_cache.get(concept_uri)
        if cached is not None:
            return cached

        chain: list[dict[str, str]] = []
        current = concept_uri
        visited: set[str] = set()
        depth = 0

        while depth < max_depth and current and current not in visited:
            visited.add(current)
            parents = self._broader_map.get(current, [])
            if not parents:
                break
            parent = parents[0]
            chain.append(parent)
            current = parent.get("id", "")
            depth += 1
        self._hierarchy_cache[concept_uri] = chain
        return chain


# ---------------------------
# Text extraction helpers
# ---------------------------
SECTION_BREAK = re.compile(
    r"\b(experience|education|projects?|certifications?|skills?|summary|objective|profile)\b",
    re.IGNORECASE,
)

DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:\d{1,2}/\d{2,4}|\d{4}|[A-Za-z]{3,9}\s+\d{4}))\s*(?:-|to|–|—)\s*(?P<end>(?:present|current|\d{1,2}/\d{2,4}|\d{4}|[A-Za-z]{3,9}\s+\d{4}))",
    re.IGNORECASE,
)

MONTH_MAP = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

TITLE_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z/&-]*(?:\s+[A-Z][A-Za-z/&-]*){0,4}\s+"
    r"(?:Manager|Engineer|Developer|Analyst|Estimator|Consultant|Agent|Assistant|Architect|Administrator|Officer|Specialist|Coordinator|Supervisor|Director|Technician))\b"
)


def normalize_text(value: str) -> str:
    return " ".join((value or "").lower().strip().split())


def normalize_spaces(value: str) -> str:
    return " ".join((value or "").split())


def extract_section_text(
    resume_text: str,
    start_pattern: str,
    stop_pattern: str = r"experience|education|projects?|certifications?|skills?|summary|objective|profile",
) -> str:
    text = normalize_spaces(resume_text)
    if not text:
        return ""
    regex = re.compile(rf"\b(?:{start_pattern})\b\s*:?\s*(.+?)(?=\b(?:{stop_pattern})\b|$)", re.IGNORECASE)
    m = regex.search(text)
    return m.group(1).strip() if m else ""


def split_skill_phrases(resume_text: str) -> list[str]:
    text = normalize_spaces(resume_text)
    section = extract_section_text(text, r"skills?")
    if not section:
        section = text[:1200]

    raw_parts = re.split(r"[\n,;|•\-]+", section)
    phrases = [" ".join(p.strip().split()) for p in raw_parts]
    phrases = [p for p in phrases if 3 <= len(p) <= 64]

    filtered: list[str] = []
    for p in phrases:
        p_norm = normalize_text(p)
        tokens = re.findall(r"[a-z]{2,}", p_norm)
        if not tokens:
            continue
        if len(tokens) == 1 and tokens[0] in GENERIC_TERMS:
            continue
        if len(tokens) > 8:
            continue
        filtered.append(p)

    seen: set[str] = set()
    out: list[str] = []
    for p in filtered:
        key = p.lower()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out[:24]


def extract_experience_titles(resume_text: str) -> list[str]:
    text = normalize_spaces(resume_text)
    titles = [m.group(1).strip() for m in TITLE_PATTERN.finditer(text)]

    # fallback for line-preserved resumes
    lines = [l.strip() for l in (resume_text or "").splitlines() if l.strip()]
    for i, line in enumerate(lines):
        if DATE_RANGE_RE.search(line):
            for offset in (1, 2):
                j = i - offset
                if j >= 0 and 2 <= len(lines[j]) <= 80:
                    titles.append(lines[j])
    dedup: list[str] = []
    seen: set[str] = set()
    for t in titles:
        if re.search(r"\b(summary|objective|profile)\b", t, re.IGNORECASE):
            continue
        if re.match(r"^(experience|accomplishments|highlights|summary)\b", t.strip(), re.IGNORECASE):
            continue
        if len(t.split()) > 6:
            continue
        key = t.lower()
        if key not in seen:
            seen.add(key)
            dedup.append(t)
    return dedup[:20]


def parse_date_token(token: str) -> date | None:
    t = (token or "").strip().lower()
    if not t or t in {"present", "current"}:
        return None

    # mm/yyyy or mm/yy
    m = re.fullmatch(r"(\d{1,2})/(\d{2,4})", t)
    if m:
        mm = int(m.group(1))
        yy = int(m.group(2))
        if yy < 100:
            yy += 2000
        if 1 <= mm <= 12:
            return date(yy, mm, 1)

    # yyyy
    if re.fullmatch(r"\d{4}", t):
        return date(int(t), 1, 1)

    # Mon yyyy
    m = re.fullmatch(r"([a-z]{3,9})\s+(\d{4})", t)
    if m:
        month_key = m.group(1)[:3]
        mm = MONTH_MAP.get(month_key)
        if mm:
            return date(int(m.group(2)), mm, 1)

    return None


def months_between(start: date | None, end: date | None, is_current: bool) -> int | None:
    if start is None:
        return None
    end_date = end or (date.today() if is_current else None)
    if end_date is None:
        return None
    delta = (end_date.year - start.year) * 12 + (end_date.month - start.month)
    return max(delta, 0)


def extract_experiences(resume_text: str) -> list[dict[str, Any]]:
    exp_text = extract_section_text(resume_text, r"experience")
    base_text = exp_text if exp_text else normalize_spaces(resume_text)
    out: list[dict[str, Any]] = []
    matches = list(DATE_RANGE_RE.finditer(base_text))
    for i, m in enumerate(matches):
        start_token = m.group("start")
        end_token = m.group("end")
        start_dt = parse_date_token(start_token)
        end_dt = parse_date_token(end_token)
        is_current = end_token.lower() in {"present", "current"}

        seg_start = max(0, m.start() - 120)
        seg_end = matches[i + 1].start() if i + 1 < len(matches) else min(len(base_text), m.end() + 500)
        segment = base_text[seg_start:seg_end].strip()

        title_match = TITLE_PATTERN.search(segment)
        title = title_match.group(1).strip() if title_match else None

        company = None
        company_match = re.search(r"\bCompany Name\b", segment, re.IGNORECASE)
        if company_match:
            company = "Company Name"

        out.append(
            {
                "title": title,
                "raw_title": title,
                "company": company,
                "start_date": start_dt.isoformat() if start_dt else None,
                "end_date": end_dt.isoformat() if end_dt else None,
                "is_current": is_current,
                "location": None,
                "duration_months": months_between(start_dt, end_dt, is_current),
                "description_raw": segment[:400],
            }
        )

    return out[:15]


def extract_educations(resume_text: str) -> list[dict[str, Any]]:
    edu_text = extract_section_text(resume_text, r"education")
    if not edu_text:
        return []

    chunks = [c.strip() for c in re.split(r"(?=\b(?:19|20)\d{2}\b)", edu_text) if c.strip()]
    lines = chunks if chunks else [edu_text]
    out: list[dict[str, Any]] = []
    edu_keywords = re.compile(r"university|college|bachelor|master|phd|degree|school", re.IGNORECASE)

    for line in lines:
        if not edu_keywords.search(line):
            continue
        line = line[:220]

        degree_match = re.search(r"(bachelor[^,.;]*|master[^,.;]*|phd[^,.;]*|degree[^,.;]*)", line, re.IGNORECASE)
        institution_match = re.search(r"([A-Z][A-Za-z&\-\s]*(University|College|School))", line)
        grad_year_match = re.search(r"\b(19|20)\d{2}\b", line)
        out.append(
            {
                "institution": institution_match.group(1).strip() if institution_match else None,
                "degree": degree_match.group(1).strip() if degree_match else None,
                "field_of_study": None,
                "start_date": None,
                "end_date": None,
                "graduation_year": grad_year_match.group(0) if grad_year_match else None,
                "location": None,
            }
        )
    return out[:8]


def detect_current_location(resume_text: str) -> str | None:
    header = normalize_spaces(resume_text)
    header = re.split(r"\b(summary|skills?|experience|education)\b", header, flags=re.IGNORECASE)[0]
    if len(header) > 240:
        header = header[:240]

    m = re.search(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2}|[A-Z][a-z]+)\b", header)
    if m:
        city = m.group(1).strip()
        if city.lower() in {"specialist", "manager", "director", "analyst", "assistant", "engineer"}:
            return None
        return f"{city}, {m.group(2)}"
    return None


# ---------------------------
# Candidate ranking and dedupe
# ---------------------------
def rank_candidates(candidates: list[MatchCandidate]) -> list[dict[str, Any]]:
    best_by_esco: dict[str, MatchCandidate] = {}
    for cand in candidates:
        prev = best_by_esco.get(cand.esco_id)
        if prev is None or cand.confidence > prev.confidence:
            best_by_esco[cand.esco_id] = cand

    ranked = sorted(best_by_esco.values(), key=lambda x: x.confidence, reverse=True)

    # precision-first suppression:
    # 1) if a raw_text has exact/alt hit, drop fuzzy for same raw_text
    # 2) otherwise keep only best fuzzy hit per raw_text
    has_non_fuzzy_raw = {c.raw_text for c in ranked if c.match_method != "fuzzy"}
    best_fuzzy_by_raw: dict[str, MatchCandidate] = {}
    for c in ranked:
        if c.match_method != "fuzzy":
            continue
        prev = best_fuzzy_by_raw.get(c.raw_text)
        if prev is None or c.confidence > prev.confidence:
            best_fuzzy_by_raw[c.raw_text] = c

    filtered: list[MatchCandidate] = []
    for c in ranked:
        if c.match_method != "fuzzy":
            filtered.append(c)
            continue
        if c.raw_text in has_non_fuzzy_raw:
            continue
        if best_fuzzy_by_raw.get(c.raw_text) is c:
            filtered.append(c)

    ranked = filtered

    out: list[dict[str, Any]] = []
    for i, cand in enumerate(ranked, start=1):
        out.append(
            {
                "esco_id": cand.esco_id,
                "preferred_label": cand.preferred_label,
                "raw_text": cand.raw_text,
                "confidence": round(cand.confidence, 5),
                "match_method": cand.match_method,
                "rank": i,
                "is_primary": i == 1,
                "hierarchy_json": cand.hierarchy,
                "source_span": cand.source_span,
            }
        )
    return out


def should_use_llm_rerank(candidates: list[dict[str, Any]], margin_threshold: float) -> bool:
    if len(candidates) < 2:
        return False
    c1 = candidates[0].get("confidence")
    c2 = candidates[1].get("confidence")
    if c1 is None or c2 is None:
        return False
    if c1 < 0.92:
        return True
    return (c1 - c2) <= margin_threshold


def llm_rerank_occupation_candidates(
    resume_text: str,
    candidates: list[dict[str, Any]],
    llm_client: Any,
    llm_model: str,
    max_candidates: int,
    max_resume_chars: int,
) -> list[dict[str, Any]]:
    if not llm_client or not candidates:
        return candidates

    top = candidates[:max_candidates]
    resume_excerpt = normalize_spaces(resume_text)[:max_resume_chars]

    input_payload = {
        "resume_excerpt": resume_excerpt,
        "candidates": [
            {
                "esco_id": c.get("esco_id"),
                "preferred_label": c.get("preferred_label"),
                "raw_text": c.get("raw_text"),
            }
            for c in top
        ],
        "task": "Rank occupation candidates by best fit to the resume. Return strict JSON only.",
        "output_format": {
            "ranked_esco_ids": ["esco_id_1", "esco_id_2"],
            "reason": "one short sentence"
        },
    }

    try:
        response = llm_client.responses.create(
            model=llm_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are an occupation reranker for ESCO. "
                        "Return strict JSON only with key ranked_esco_ids as an ordered list."
                    ),
                },
                {"role": "user", "content": json.dumps(input_payload, ensure_ascii=False)},
            ],
            temperature=0,
        )
        text = (response.output_text or "").strip()
        if not text:
            return candidates

        parsed = json.loads(text)
        ranked_ids = parsed.get("ranked_esco_ids") if isinstance(parsed, dict) else None
        if not isinstance(ranked_ids, list):
            return candidates

        cand_by_id = {c.get("esco_id"): c for c in top if c.get("esco_id")}
        reranked_top: list[dict[str, Any]] = []
        used: set[str] = set()
        for esco_id in ranked_ids:
            if esco_id in cand_by_id and esco_id not in used:
                row = dict(cand_by_id[esco_id])
                row["match_method"] = f"{row.get('match_method', 'unknown')}+llm_rerank"
                reranked_top.append(row)
                used.add(esco_id)

        for c in top:
            esco_id = c.get("esco_id")
            if esco_id and esco_id not in used:
                reranked_top.append(c)

        merged = reranked_top + candidates[max_candidates:]
        out: list[dict[str, Any]] = []
        for i, c in enumerate(merged, start=1):
            row = dict(c)
            row["rank"] = i
            row["is_primary"] = i == 1
            out.append(row)
        return out
    except Exception:
        return candidates


def run_matchers(
    phrases: list[str],
    index: ConceptIndex,
    matchers: list[BaseMatcher],
    cache: dict[str, list[dict[str, Any]]] | None = None,
    fuzzy_fallback_only: bool = True,
) -> list[dict[str, Any]]:
    all_candidates: list[MatchCandidate] = []
    # phrase-level dedupe to reduce repeated matcher calls
    seen: set[str] = set()

    for phrase in phrases:
        phrase_norm = normalize_text(phrase)
        if not phrase_norm or phrase_norm in seen:
            continue
        seen.add(phrase_norm)

        if cache is not None and phrase_norm in cache:
            for row in cache[phrase_norm]:
                all_candidates.append(
                    MatchCandidate(
                        esco_id=row["esco_id"],
                        preferred_label=row["preferred_label"],
                        raw_text=row["raw_text"],
                        confidence=row["confidence"],
                        match_method=row["match_method"],
                        hierarchy=row.get("hierarchy_json") or [],
                        source_span=row.get("source_span"),
                    )
                )
            continue

        phrase_candidates: list[MatchCandidate] = []
        # exact / alt first
        for matcher in matchers:
            if isinstance(matcher, FuzzyMatcher):
                continue
            phrase_candidates.extend(matcher.match(phrase, index))

        # fuzzy only as fallback (big speed-up)
        if not phrase_candidates or not fuzzy_fallback_only:
            for matcher in matchers:
                if isinstance(matcher, FuzzyMatcher):
                    phrase_candidates.extend(matcher.match(phrase, index))

        all_candidates.extend(phrase_candidates)

        if cache is not None:
            cache[phrase_norm] = [
                {
                    "esco_id": c.esco_id,
                    "preferred_label": c.preferred_label,
                    "raw_text": c.raw_text,
                    "confidence": c.confidence,
                    "match_method": c.match_method,
                    "hierarchy_json": c.hierarchy,
                    "source_span": c.source_span,
                }
                for c in phrase_candidates
            ]

    return rank_candidates(all_candidates)


# ---------------------------
# Main pipeline
# ---------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize 1st_data resumes into normalized_candidates collection.")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db-name", default="prodapt_capstone")
    parser.add_argument("--fuzzy-threshold", type=float, default=FUZZY_THRESHOLD)
    parser.add_argument("--limit", type=int, default=0, help="Optional number of resumes to process.")
    parser.add_argument("--write-batch-size", type=int, default=200)
    parser.add_argument("--fetch-batch-size", type=int, default=200)
    parser.add_argument("--no-fuzzy-fallback-only", action="store_true")
    parser.add_argument("--workers", type=int, default=1, help="Parallel worker threads for per-resume normalization.")
    parser.add_argument("--enable-llm-rerank", action="store_true", help="Use OpenAI to rerank top occupation candidates for ambiguous cases.")
    parser.add_argument("--llm-model", default=LLM_DEFAULT_MODEL)
    parser.add_argument("--llm-max-candidates", type=int, default=5)
    parser.add_argument("--llm-max-resume-chars", type=int, default=2500)
    parser.add_argument("--llm-ambiguity-margin", type=float, default=0.06)
    return parser.parse_args()


def build_upsert_op(
    src: dict[str, Any],
    occ_index: ConceptIndex,
    skill_index: ConceptIndex,
    occ_matchers: list[BaseMatcher],
    skill_matchers: list[BaseMatcher],
    fuzzy_fallback_only: bool,
    occ_cache: dict[str, list[dict[str, Any]]] | None,
    skill_cache: dict[str, list[dict[str, Any]]] | None,
    llm_cfg: dict[str, Any] | None,
) -> UpdateOne:
    source_dataset = "1st_data"
    source_record_id = str(src.get("source_record_id", "")).strip()
    category = (src.get("category") or "").strip()
    resume_text = src.get("resume_text") or ""

    occupation_phrases = [category] if category else []
    occupation_phrases.extend(extract_experience_titles(resume_text))

    skill_phrases = split_skill_phrases(resume_text)

    occupation_candidates = run_matchers(
        occupation_phrases,
        occ_index,
        occ_matchers,
        cache=occ_cache,
        fuzzy_fallback_only=fuzzy_fallback_only,
    )
    skill_candidates = run_matchers(
        skill_phrases,
        skill_index,
        skill_matchers,
        cache=skill_cache,
        fuzzy_fallback_only=fuzzy_fallback_only,
    )

    # precision-first post-filtering
    if occupation_candidates:
        has_occ_non_fuzzy = any(c.get("match_method") != "fuzzy" for c in occupation_candidates)
        if has_occ_non_fuzzy:
            occupation_candidates = [c for c in occupation_candidates if c.get("match_method") != "fuzzy"]
        else:
            occupation_candidates = occupation_candidates[:1]

    if skill_candidates:
        has_skill_non_fuzzy = any(c.get("match_method") != "fuzzy" for c in skill_candidates)
        if has_skill_non_fuzzy:
            skill_candidates = [c for c in skill_candidates if c.get("match_method") != "fuzzy"]

    if llm_cfg and llm_cfg.get("enabled") and should_use_llm_rerank(occupation_candidates, llm_cfg.get("ambiguity_margin", 0.06)):
        occupation_candidates = llm_rerank_occupation_candidates(
            resume_text=resume_text,
            candidates=occupation_candidates,
            llm_client=llm_cfg.get("client"),
            llm_model=llm_cfg.get("model", LLM_DEFAULT_MODEL),
            max_candidates=llm_cfg.get("max_candidates", 5),
            max_resume_chars=llm_cfg.get("max_resume_chars", 2500),
        )

    experiences = extract_experiences(resume_text)
    for exp in experiences:
        exp_phrases = [exp.get("raw_title") or ""]
        exp["normalized_occupation_candidates"] = run_matchers(
            exp_phrases,
            occ_index,
            occ_matchers,
            cache=occ_cache,
            fuzzy_fallback_only=fuzzy_fallback_only,
        )

    educations = extract_educations(resume_text)
    current_location = detect_current_location(resume_text)

    occ_primary = occupation_candidates[0]["confidence"] if occupation_candidates else None
    skill_primary = skill_candidates[0]["confidence"] if skill_candidates else None
    scores = [s for s in [occ_primary, skill_primary] if s is not None]
    extraction_confidence = round(sum(scores) / len(scores), 5) if scores else None

    if occupation_candidates and skill_candidates:
        normalization_status = "success"
    elif occupation_candidates or skill_candidates:
        normalization_status = "partial"
    else:
        normalization_status = "failed"

    key = {"source_dataset": source_dataset, "source_record_id": source_record_id}
    set_doc = {
        "source_dataset": source_dataset,
        "source_record_id": source_record_id,
        "normalizer_version": NORMALIZER_VERSION,
        "normalized_at": datetime.utcnow(),
        "normalization_status": normalization_status,
        "current_location": current_location,
        "resume_text": resume_text,
        "extraction_confidence": extraction_confidence,
        "occupation_candidates": occupation_candidates,
        "skill_candidates": skill_candidates,
        "experiences": experiences,
        "educations": educations,
    }

    return UpdateOne(
        key,
        {
            "$set": set_doc,
            "$setOnInsert": {"candidate_id": str(uuid.uuid4())},
        },
        upsert=True,
    )


def main() -> None:
    args = parse_args()

    dotenv_path = Path(__file__).with_name(".env")
    if load_dotenv is not None and dotenv_path.exists():
        load_dotenv(dotenv_path)

    client = MongoClient(args.mongo_uri)
    db = client[args.db_name]

    llm_cfg: dict[str, Any] = {
        "enabled": False,
        "client": None,
        "model": args.llm_model,
        "max_candidates": args.llm_max_candidates,
        "max_resume_chars": args.llm_max_resume_chars,
        "ambiguity_margin": args.llm_ambiguity_margin,
    }
    if args.enable_llm_rerank:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if api_key and OpenAI is not None:
            llm_cfg["enabled"] = True
            llm_cfg["client"] = OpenAI(api_key=api_key)
            print(f"LLM rerank enabled with model: {args.llm_model}")
        else:
            print("LLM rerank disabled: OPENAI_API_KEY or openai package is unavailable.")

    # Build ESCO indexes from raw collections
    occ_rows = list(db["raw_esco_occupations"].find({}, {"_id": 0}))
    skill_rows = list(db["raw_esco_skills"].find({}, {"_id": 0}))

    broader_occ_rows = list(db["raw_esco_broader_relations_occ"].find({}, {"_id": 0}))
    broader_skill_rows = list(db["raw_esco_broader_relations_skill"].find({}, {"_id": 0}))

    occ_index = ConceptIndex(occ_rows, broader_occ_rows)
    skill_index = ConceptIndex(skill_rows, broader_skill_rows)

    occ_matchers: list[BaseMatcher] = [ExactMatcher(), AltLabelMatcher(), FuzzyMatcher(max(args.fuzzy_threshold, 0.92), limit=3)]
    skill_matchers: list[BaseMatcher] = [ExactMatcher(), AltLabelMatcher(), FuzzyMatcher(max(args.fuzzy_threshold, 0.90), limit=3)]
    # future: matchers.append(LLMMatcher())

    occ_cache: dict[str, list[dict[str, Any]]] = {}
    skill_cache: dict[str, list[dict[str, Any]]] = {}

    source_col = db["source_1st_resumes"]

    out_col = db["normalized_candidates"]
    out_col.create_index([("source_dataset", 1), ("source_record_id", 1)], unique=True, name="uq_source_record")
    out_col.create_index("candidate_id", name="idx_candidate_id")

    count = 0
    writes: list[ReplaceOne | UpdateOne] = []

    last_id = None
    while True:
        if args.limit and count >= args.limit:
            break

        query: dict[str, Any] = {"source_dataset": "1st_data"}
        if last_id is not None:
            query["_id"] = {"$gt": last_id}

        remaining = (args.limit - count) if args.limit else args.fetch_batch_size
        batch_limit = min(args.fetch_batch_size, remaining) if args.limit else args.fetch_batch_size

        source_batch = list(
            source_col.find(query, {"_id": 1, "source_record_id": 1, "category": 1, "resume_text": 1})
            .sort("_id", 1)
            .limit(batch_limit)
        )

        if not source_batch:
            break

        if args.workers > 1:
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                ops = executor.map(
                    lambda src: build_upsert_op(
                        src,
                        occ_index,
                        skill_index,
                        occ_matchers,
                        skill_matchers,
                        not args.no_fuzzy_fallback_only,
                        None,
                        None,
                        llm_cfg,
                    ),
                    source_batch,
                )
                for op in ops:
                    writes.append(op)
                    count += 1

                    if len(writes) >= args.write_batch_size:
                        out_col.bulk_write(writes, ordered=False)
                        writes.clear()

                    if count % 100 == 0:
                        print(f"Processed {count} resumes...")

                    if args.limit and count >= args.limit:
                        break
        else:
            for src in source_batch:
                op = build_upsert_op(
                    src,
                    occ_index,
                    skill_index,
                    occ_matchers,
                    skill_matchers,
                    not args.no_fuzzy_fallback_only,
                    occ_cache,
                    skill_cache,
                    llm_cfg,
                )
                writes.append(op)
                count += 1

                if len(writes) >= args.write_batch_size:
                    out_col.bulk_write(writes, ordered=False)
                    writes.clear()

                if count % 100 == 0:
                    print(f"Processed {count} resumes...")

                if args.limit and count >= args.limit:
                    break

        last_id = source_batch[-1]["_id"]

    if writes:
        out_col.bulk_write(writes, ordered=False)

    print(f"Done. Total processed: {count}")


if __name__ == "__main__":
    main()
