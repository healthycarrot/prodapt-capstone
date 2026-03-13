"""
Issue #8 – [Pipeline v2] Step 3: セクション分割器の構築

Parses resume HTML (BeautifulSoup) into structured sections and stores
the result as `parsed_sections` in MongoDB `source_1st_resumes`.

Usage:
    python parse_sections_to_mongo.py [--mongo-uri URI] [--db-name DB]
                                      [--collection COL] [--batch-size N]
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag
from pymongo import MongoClient, UpdateOne

# ── constants ───────────────────────────────────────────────────

PARSER_VERSION = "parse_sections_v1.0"
MIN_TEXT_LENGTH = 22  # docs with text_length <= 21 are edge-case failures

# Section type extracted from SECTION_ID pattern: SECTION_{TYPE}{DIGITS}
# e.g. SECTION_SUMM500375981 -> SUMM
SECTION_ID_RE = re.compile(r"^SECTION_([A-Z]+)\d+$")

# Section title element selector
SECTION_TITLE_CLASS = "sectiontitle"

# Whitespace-block pattern for fallback splitting
SPACE_BLOCK_RE = re.compile(r"\s{3,}")

# Known section type labels (for fallback header detection)
FALLBACK_HEADER_RE = re.compile(
    r"^\s*(?:"
    r"(?:professional\s+)?summary|profile|objective|overview|"
    r"(?:core\s+)?qualifications|highlights|"
    r"(?:technical\s+)?skills|competencies|areas\s+of\s+expertise|"
    r"(?:professional\s+|work\s+)?experience|employment\s+history|career\s+history|"
    r"education|academic\s+background|"
    r"certifications?|licenses|credentials|"
    r"projects?|languages?|awards?|achievements?|"
    r"affiliations?|memberships?|"
    r"additional\s+information|interests?|"
    r"accomplishments?|publications?"
    r")\s*$",
    re.IGNORECASE,
)

# Map fallback header text → canonical section type
FALLBACK_HEADER_MAP: dict[str, str] = {
    "summary": "SUMM", "professional summary": "SUMM", "profile": "SUMM",
    "objective": "SUMM", "overview": "SUMM", "career overview": "SUMM",
    "professional overview": "SUMM", "executive summary": "SUMM",
    "executive profile": "SUMM",
    "highlights": "HILT", "core qualifications": "HILT", "qualifications": "HILT",
    "skills": "SKLL", "technical skills": "TSKL", "competencies": "SKLL",
    "areas of expertise": "SKLL",
    "experience": "EXPR", "professional experience": "EXPR",
    "work experience": "EXPR", "employment history": "EXPR",
    "career history": "EXPR", "work history": "EXPR",
    "education": "EDUC", "academic background": "EDUC",
    "education and training": "EDUC",
    "certifications": "CERT", "certification": "CERT",
    "licenses": "CERT", "credentials": "CERT",
    "projects": "PROJ", "languages": "LANG",
    "awards": "AWAR", "achievements": "AWAR", "honors": "AWAR",
    "affiliations": "AFIL", "professional affiliations": "AFIL",
    "memberships": "AFIL",
    "accomplishments": "ACCM",
    "additional information": "ADDI",
    "interests": "INTR",
    "publications": "PUBL",
    "personal information": "PRIN",
}


# ── dataclass ───────────────────────────────────────────────────

@dataclass
class ParsedSection:
    section_type: str       # e.g. "SUMM", "EXPR", "EDUC"
    section_id: str         # original HTML id or generated fallback id
    title: str              # section title text (e.g. "Summary", "Experience")
    text: str               # extracted plain text (tags stripped, whitespace normalized)
    char_count: int         # len(text)


# ── HTML parser (Pass 1) ───────────────────────────────────────

def _extract_text(tag: Tag) -> str:
    """Extract text from a BS4 tag, normalizing whitespace."""
    raw = tag.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", raw).strip()


def _resolve_section_type(section_id: str) -> str | None:
    """Extract section type from SECTION_{TYPE}{DIGITS} pattern."""
    m = SECTION_ID_RE.match(section_id)
    return m.group(1) if m else None


def _find_section_title(section_div: Tag) -> str:
    """Find section title text from the sectiontitle div."""
    title_div = section_div.find("div", class_=SECTION_TITLE_CLASS)
    if title_div:
        return _extract_text(title_div)
    # Some sections (like NAME) have no sectiontitle; use first meaningful text
    heading = section_div.find("div", class_="heading")
    if heading:
        return _extract_text(heading)
    return ""


def parse_html_sections(html: str) -> list[ParsedSection]:
    """Parse resume HTML into structured sections using BeautifulSoup.

    Returns list of ParsedSection, one per <div class="section"> found.
    """
    if not html or not html.strip():
        return []

    soup = BeautifulSoup(html, "html.parser")
    sections: list[ParsedSection] = []

    for div in soup.find_all("div", class_="section"):
        section_id = div.get("id", "")
        if not section_id:
            continue

        section_type = _resolve_section_type(section_id)
        if not section_type:
            # Try SECTNAME_ pattern as fallback
            # e.g. id might not match SECTION_ prefix in rare cases
            continue

        title = _find_section_title(div)
        text = _extract_text(div)

        # Remove the title from the beginning of text if duplicated
        if title and text.startswith(title):
            text = text[len(title):].strip()

        if not text:
            continue

        sections.append(ParsedSection(
            section_type=section_type,
            section_id=section_id,
            title=title,
            text=text,
            char_count=len(text),
        ))

    return sections


# ── Whitespace fallback (Pass 2) ──────────────────────────────

def _guess_section_type(header_text: str) -> str:
    """Map a header text to a canonical section type."""
    normalized = re.sub(r"\s+", " ", header_text).strip().lower()
    return FALLBACK_HEADER_MAP.get(normalized, "UNKNOWN")


def parse_whitespace_sections(text: str) -> list[ParsedSection]:
    """Fallback: split resume_text on whitespace blocks and try to identify sections."""
    if not text or not text.strip():
        return []

    # Split on large whitespace blocks
    parts = SPACE_BLOCK_RE.split(text)
    sections: list[ParsedSection] = []
    current_type = "PREAMBLE"
    current_title = ""
    current_text_parts: list[str] = []
    section_idx = 0

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Check if this part looks like a section header
        if FALLBACK_HEADER_RE.match(part):
            # Flush previous section
            if current_text_parts:
                full_text = " ".join(current_text_parts).strip()
                if full_text:
                    sections.append(ParsedSection(
                        section_type=current_type,
                        section_id=f"WS_{section_idx}",
                        title=current_title,
                        text=full_text,
                        char_count=len(full_text),
                    ))
                    section_idx += 1

            current_type = _guess_section_type(part)
            current_title = part
            current_text_parts = []
        else:
            current_text_parts.append(part)

    # Flush last section
    if current_text_parts:
        full_text = " ".join(current_text_parts).strip()
        if full_text:
            sections.append(ParsedSection(
                section_type=current_type,
                section_id=f"WS_{section_idx}",
                title=current_title,
                text=full_text,
                char_count=len(full_text),
            ))

    return sections


# ── Main parser dispatcher ────────────────────────────────────

def parse_resume_sections(doc: dict[str, Any]) -> tuple[list[ParsedSection], str]:
    """Parse a resume document into sections.

    Returns:
        (sections, parsing_method) where parsing_method is "html" | "whitespace" | "none"
    """
    resume_text = doc.get("resume_text", "") or ""
    resume_html = doc.get("resume_html", "") or ""

    # Guard: minimum text length
    if len(resume_text.strip()) <= MIN_TEXT_LENGTH and len(resume_html.strip()) <= MIN_TEXT_LENGTH:
        return [], "none"

    # Pass 1: HTML parsing (primary)
    html_sections = parse_html_sections(resume_html)
    if len(html_sections) >= 2:
        return html_sections, "html"

    # Pass 2: Whitespace fallback
    ws_sections = parse_whitespace_sections(resume_text)
    if ws_sections:
        return ws_sections, "whitespace"

    # Final fallback: entire text as single section
    text = re.sub(r"\s+", " ", resume_text).strip()
    if text:
        return [ParsedSection(
            section_type="FULL",
            section_id="FULL_0",
            title="",
            text=text,
            char_count=len(text),
        )], "whitespace"

    return [], "none"


# ── MongoDB batch upsert ─────────────────────────────────────

def upsert_parsed_sections(
    collection,
    docs: list[dict[str, Any]],
    batch_size: int = 500,
) -> dict[str, int]:
    """Parse all docs and upsert parsed_sections into MongoDB."""
    stats = {"total": 0, "html": 0, "whitespace": 0, "none": 0, "errors": 0}
    operations: list[UpdateOne] = []

    for doc in docs:
        stats["total"] += 1
        try:
            sections, method = parse_resume_sections(doc)
            section_dicts = [asdict(s) for s in sections]

            operations.append(UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {
                    "parsed_sections": section_dicts,
                    "parsing_method": method,
                    "parser_version": PARSER_VERSION,
                    "section_count": len(sections),
                    "section_types": sorted(set(s.section_type for s in sections)),
                }},
            ))
            stats[method] += 1
        except Exception as e:
            stats["errors"] += 1
            print(f"  ERROR on {doc.get('source_record_id', '?')}: {e}")
            operations.append(UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {
                    "parsed_sections": [],
                    "parsing_method": "none",
                    "parser_version": PARSER_VERSION,
                    "section_count": 0,
                    "section_types": [],
                }},
            ))

        if len(operations) >= batch_size:
            collection.bulk_write(operations)
            operations.clear()

    if operations:
        collection.bulk_write(operations)

    return stats


# ── Verification report ──────────────────────────────────────

def build_verification_report(
    collection,
    stats: dict[str, int],
) -> dict[str, Any]:
    """Build verification report with sample checks."""
    report: dict[str, Any] = {
        "parser_version": PARSER_VERSION,
        "stats": stats,
    }

    # Method distribution
    pipeline_method = [
        {"$group": {"_id": "$parsing_method", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    report["method_distribution"] = list(collection.aggregate(pipeline_method))

    # Section type distribution
    pipeline_types = [
        {"$unwind": "$parsed_sections"},
        {"$group": {"_id": "$parsed_sections.section_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    report["section_type_distribution"] = list(collection.aggregate(pipeline_types))

    # Section count distribution
    pipeline_count = [
        {"$group": {"_id": "$section_count", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    report["section_count_distribution"] = list(collection.aggregate(pipeline_count))

    # Average sections per method
    pipeline_avg = [
        {"$group": {
            "_id": "$parsing_method",
            "avg_sections": {"$avg": "$section_count"},
            "min_sections": {"$min": "$section_count"},
            "max_sections": {"$max": "$section_count"},
        }},
    ]
    report["sections_per_method"] = list(collection.aggregate(pipeline_avg))

    # Sample verification: 5 high / 5 medium / 5 low structure docs
    samples: dict[str, list[dict[str, Any]]] = {}

    # High: section_count >= 7
    high_docs = list(collection.find(
        {"section_count": {"$gte": 7}, "parsing_method": "html"},
        {"source_record_id": 1, "category": 1, "parsing_method": 1,
         "section_count": 1, "section_types": 1, "parsed_sections": 1},
    ).sort("section_count", -1).limit(5))
    samples["high_structure"] = [
        {
            "source_record_id": d.get("source_record_id"),
            "category": d.get("category"),
            "method": d.get("parsing_method"),
            "section_count": d.get("section_count"),
            "section_types": d.get("section_types"),
            "sections_preview": [
                {"type": s["section_type"], "title": s["title"], "chars": s["char_count"]}
                for s in (d.get("parsed_sections") or [])
            ],
        }
        for d in high_docs
    ]

    # Medium: section_count 4-6
    med_docs = list(collection.find(
        {"section_count": {"$gte": 4, "$lte": 6}, "parsing_method": "html"},
        {"source_record_id": 1, "category": 1, "parsing_method": 1,
         "section_count": 1, "section_types": 1, "parsed_sections": 1},
    ).limit(5))
    samples["medium_structure"] = [
        {
            "source_record_id": d.get("source_record_id"),
            "category": d.get("category"),
            "method": d.get("parsing_method"),
            "section_count": d.get("section_count"),
            "section_types": d.get("section_types"),
            "sections_preview": [
                {"type": s["section_type"], "title": s["title"], "chars": s["char_count"]}
                for s in (d.get("parsed_sections") or [])
            ],
        }
        for d in med_docs
    ]

    # Low: section_count <= 3
    low_docs = list(collection.find(
        {"section_count": {"$lte": 3}},
        {"source_record_id": 1, "category": 1, "parsing_method": 1,
         "section_count": 1, "section_types": 1, "parsed_sections": 1},
    ).sort("section_count", 1).limit(5))
    samples["low_structure"] = [
        {
            "source_record_id": d.get("source_record_id"),
            "category": d.get("category"),
            "method": d.get("parsing_method"),
            "section_count": d.get("section_count"),
            "section_types": d.get("section_types"),
            "sections_preview": [
                {"type": s["section_type"], "title": s["title"], "chars": s["char_count"]}
                for s in (d.get("parsed_sections") or [])
            ],
        }
        for d in low_docs
    ]

    report["sample_verification"] = samples

    return report


# ── CLI ──────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Issue #8: Parse resume HTML into sections and store in MongoDB"
    )
    p.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    p.add_argument("--db-name", default="prodapt_capstone")
    p.add_argument("--collection", default="source_1st_resumes")
    p.add_argument("--batch-size", type=int, default=500)
    p.add_argument(
        "--report-out",
        default=str(Path(__file__).resolve().parent / "parse_sections_report.json"),
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    print(f"Connecting to {args.mongo_uri} / {args.db_name} / {args.collection} ...")
    client: MongoClient = MongoClient(args.mongo_uri)
    db = client[args.db_name]
    coll = db[args.collection]

    total = coll.count_documents({})
    print(f"Total documents: {total}")

    # Load all docs
    print("Loading documents ...")
    docs = list(coll.find())
    print(f"Loaded {len(docs)} documents")

    # Parse and upsert
    print("Parsing sections and upserting ...")
    t0 = time.time()
    stats = upsert_parsed_sections(coll, docs, batch_size=args.batch_size)
    elapsed = time.time() - t0

    print(f"\nParsing complete in {elapsed:.1f}s")
    print(f"  Total:      {stats['total']}")
    print(f"  HTML:       {stats['html']}")
    print(f"  Whitespace: {stats['whitespace']}")
    print(f"  None:       {stats['none']}")
    print(f"  Errors:     {stats['errors']}")

    # Build verification report
    print("\nBuilding verification report ...")
    report = build_verification_report(coll, stats)
    report["elapsed_seconds"] = round(elapsed, 2)

    # Console summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"  Method distribution:")
    for item in report["method_distribution"]:
        print(f"    {item['_id']:12s} {item['count']:>6d}")
    print(f"\n  Section type distribution (top 15):")
    for item in report["section_type_distribution"][:15]:
        print(f"    {item['_id']:12s} {item['count']:>6d}")
    print(f"\n  Sections per method:")
    for item in report["sections_per_method"]:
        print(f"    {item['_id']:12s}  avg={item['avg_sections']:.1f}  "
              f"min={item['min_sections']}  max={item['max_sections']}")

    for group_name, samples in report["sample_verification"].items():
        print(f"\n  Sample: {group_name}")
        for s in samples:
            print(f"    ID={s['source_record_id']}  cat={s['category']}  "
                  f"method={s['method']}  sections={s['section_count']}  "
                  f"types={s['section_types']}")

    print("=" * 60)

    # Write JSON report
    out_path = Path(args.report_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"\nReport written to: {out_path}")


if __name__ == "__main__":
    main()
