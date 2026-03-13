from __future__ import annotations

import argparse
import re
import uuid
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from pymongo import MongoClient, ReplaceOne, UpdateOne
from rapidfuzz import fuzz, process


NORMALIZER_VERSION = "v0.1.0"
FUZZY_THRESHOLD = 0.85


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
            for entry in index.label_to_entries.get(label_norm, []):
                out.append(
                    MatchCandidate(
                        esco_id=entry.esco_id,
                        preferred_label=entry.preferred_label,
                        raw_text=phrase,
                        confidence=round(conf, 5),
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


def normalize_text(value: str) -> str:
    return " ".join((value or "").lower().strip().split())


def split_skill_phrases(resume_text: str) -> list[str]:
    text = resume_text or ""
    m = re.search(r"skills?\s*[:\n](.*)", text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        section = m.group(1)
        stop = SECTION_BREAK.search(section)
        if stop:
            section = section[: stop.start()]
    else:
        section = text[:1500]

    raw_parts = re.split(r"[\n,;|•\-]+", section)
    phrases = [" ".join(p.strip().split()) for p in raw_parts]
    phrases = [p for p in phrases if 2 <= len(p) <= 80]

    seen: set[str] = set()
    out: list[str] = []
    for p in phrases:
        key = p.lower()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out[:30]


def extract_experience_titles(resume_text: str) -> list[str]:
    lines = [l.strip() for l in (resume_text or "").splitlines() if l.strip()]
    titles: list[str] = []
    for i, line in enumerate(lines):
        if DATE_RANGE_RE.search(line):
            for offset in (1, 2):
                j = i - offset
                if j >= 0 and 2 <= len(lines[j]) <= 80:
                    titles.append(lines[j])
    dedup: list[str] = []
    seen: set[str] = set()
    for t in titles:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            dedup.append(t)
    return dedup[:30]


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
    lines = [l.strip() for l in (resume_text or "").splitlines() if l.strip()]
    out: list[dict[str, Any]] = []

    for i, line in enumerate(lines):
        m = DATE_RANGE_RE.search(line)
        if not m:
            continue

        start_token = m.group("start")
        end_token = m.group("end")
        start_dt = parse_date_token(start_token)
        end_dt = parse_date_token(end_token)
        is_current = end_token.lower() in {"present", "current"}

        title = lines[i - 1] if i - 1 >= 0 else None
        company = lines[i - 2] if i - 2 >= 0 else None

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
                "description_raw": line,
            }
        )

    return out[:30]


def extract_educations(resume_text: str) -> list[dict[str, Any]]:
    lines = [l.strip() for l in (resume_text or "").splitlines() if l.strip()]
    out: list[dict[str, Any]] = []
    edu_keywords = re.compile(r"university|college|bachelor|master|phd|degree", re.IGNORECASE)

    for line in lines:
        if not edu_keywords.search(line):
            continue
        out.append(
            {
                "institution": line if re.search(r"university|college", line, re.IGNORECASE) else None,
                "degree": line if re.search(r"bachelor|master|phd|degree", line, re.IGNORECASE) else None,
                "field_of_study": None,
                "start_date": None,
                "end_date": None,
                "graduation_year": None,
                "location": None,
            }
        )
    return out[:15]


def detect_current_location(resume_text: str) -> str | None:
    lines = [l.strip() for l in (resume_text or "").splitlines() if l.strip()]
    # heuristic only
    for line in lines[:20]:
        if re.search(r"[A-Za-z]+,\s*[A-Za-z]{2,}", line):
            return line[:120]
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
    return parser.parse_args()


def build_upsert_op(
    src: dict[str, Any],
    occ_index: ConceptIndex,
    skill_index: ConceptIndex,
    matchers: list[BaseMatcher],
    fuzzy_fallback_only: bool,
    occ_cache: dict[str, list[dict[str, Any]]] | None,
    skill_cache: dict[str, list[dict[str, Any]]] | None,
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
        matchers,
        cache=occ_cache,
        fuzzy_fallback_only=fuzzy_fallback_only,
    )
    skill_candidates = run_matchers(
        skill_phrases,
        skill_index,
        matchers,
        cache=skill_cache,
        fuzzy_fallback_only=fuzzy_fallback_only,
    )

    experiences = extract_experiences(resume_text)
    for exp in experiences:
        exp_phrases = [exp.get("raw_title") or ""]
        exp["normalized_occupation_candidates"] = run_matchers(
            exp_phrases,
            occ_index,
            matchers,
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

    client = MongoClient(args.mongo_uri)
    db = client[args.db_name]

    # Build ESCO indexes from raw collections
    occ_rows = list(db["raw_esco_occupations"].find({}, {"_id": 0}))
    skill_rows = list(db["raw_esco_skills"].find({}, {"_id": 0}))

    broader_occ_rows = list(db["raw_esco_broader_relations_occ"].find({}, {"_id": 0}))
    broader_skill_rows = list(db["raw_esco_broader_relations_skill"].find({}, {"_id": 0}))

    occ_index = ConceptIndex(occ_rows, broader_occ_rows)
    skill_index = ConceptIndex(skill_rows, broader_skill_rows)

    matchers: list[BaseMatcher] = [ExactMatcher(), AltLabelMatcher(), FuzzyMatcher(args.fuzzy_threshold)]
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
                        matchers,
                        not args.no_fuzzy_fallback_only,
                        None,
                        None,
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
                    matchers,
                    not args.no_fuzzy_fallback_only,
                    occ_cache,
                    skill_cache,
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
