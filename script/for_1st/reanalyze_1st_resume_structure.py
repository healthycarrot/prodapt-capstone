"""
Issue #6 – [Pipeline v2] Step 1: 1stデータ再解析

Reads from MongoDB `source_1st_resumes` and performs:
1. Whitespace-pattern (\s{3,}) position/frequency aggregation
2. Newline presence ratio re-confirmation
3. Resume_html column presence & HTML-tag section-split feasibility
4. 10-sample visual verification of whitespace-block splitting
5. Bottom-5 structure-score edge-case identification
6. JSON report with splitting-method recommendation
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pymongo import MongoClient

# ── regex patterns ──────────────────────────────────────────────
SPACE_BLOCK_RE = re.compile(r"\s{3,}")
NEWLINE_RE = re.compile(r"[\r\n]+")

SECTION_KEYWORDS = [
    "summary", "profile", "objective", "overview",
    "skills", "qualifications", "competencies", "expertise",
    "experience", "employment", "work history", "career",
    "education", "academic",
    "certifications", "licenses", "credentials",
    "projects", "languages", "awards", "achievements",
    "affiliations", "memberships",
]

SECTION_HEADER_RE = re.compile(
    r"\b(?:"
    + "|".join(re.escape(k) for k in SECTION_KEYWORDS)
    + r")\b",
    re.IGNORECASE,
)

DATE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"\b(?:0?[1-9]|1[0-2])[/-](?:19|20)?\d{2}\s*(?:to|-|–|—)\s*"
        r"(?:current|present|(?:0?[1-9]|1[0-2])[/-](?:19|20)?\d{2})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
        r"\s+(?:19|20)\d{2}\s*(?:to|-|–|—)\s*"
        r"(?:current|present|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|"
        r"oct|nov|dec)[a-z]*\s+(?:19|20)\d{2})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:19|20)\d{2}\s*(?:to|-|–|—)\s*(?:current|present|(?:19|20)\d{2})\b",
        re.IGNORECASE,
    ),
]

BULLET_RE = re.compile(r"[•●▪◦■□]|\s[*-]\s")
UPPER_SECTION_RE = re.compile(
    r"\b(?:SUMMARY|SKILLS|EXPERIENCE|EDUCATION|"
    r"CERTIFICATIONS|PROJECTS|LANGUAGES|OBJECTIVE|"
    r"QUALIFICATIONS|PROFILE)\b"
)

# HTML section-class patterns found in the 1st-data Resume_html
HTML_SECTION_RE = re.compile(
    r'class="section[^"]*"\s+id="(SECTION_[^"]+)"', re.IGNORECASE
)
HTML_SECTION_HEADER_RE = re.compile(
    r"<span[^>]*>([A-Z][A-Za-z &/]+)</span>", re.IGNORECASE
)
HTML_TAG_RE = re.compile(r"<[^>]+>")


# ── dataclasses ─────────────────────────────────────────────────
@dataclass
class SpaceBlockInfo:
    """Per-document whitespace-block stats."""
    position: int          # char offset
    length: int            # how many whitespace chars
    context_before: str    # 40 chars before
    context_after: str     # 40 chars after


@dataclass
class DocAnalysis:
    source_record_id: str
    category: str
    text_length: int
    newline_count: int
    has_newlines: bool
    space_block_count: int
    space_block_positions: list[int]
    space_block_lengths: list[int]
    section_hits: list[str]
    section_count: int
    date_range_count: int
    bullet_like: bool
    uppercase_section_count: int
    structure_score: int
    # HTML analysis
    html_length: int
    html_section_ids: list[str]
    html_section_count: int
    html_has_content: bool


@dataclass
class WhitespaceAggregation:
    total_docs: int
    docs_with_space_blocks: int
    pct_with_space_blocks: float
    total_space_blocks: int
    mean_blocks_per_doc: float
    median_blocks_per_doc: float
    max_blocks_in_single_doc: int
    block_length_histogram: dict[str, int]   # "3-5", "6-10", "11-20", "21+"
    mean_block_length: float
    median_block_length: float
    # positional: what fraction of doc length
    mean_first_block_relative_pos: float     # 0.0–1.0


@dataclass
class NewlineStats:
    total_docs: int
    docs_with_newlines: int
    docs_without_newlines: int
    pct_with_newlines: float
    pct_without_newlines: float
    mean_newline_count: float
    median_newline_count: float


@dataclass
class HtmlStats:
    total_docs: int
    docs_with_html: int
    docs_without_html: int
    pct_with_html: float
    mean_html_sections: float
    median_html_sections: float
    max_html_sections: int
    section_id_frequency: dict[str, int]  # top-20 section IDs
    html_splittable: bool                 # recommendation flag
    html_splittable_reason: str


@dataclass
class SplitVerification:
    source_record_id: str
    category: str
    method: str                    # "whitespace" | "html" | "hybrid"
    segments: list[dict[str, str]]  # [{label, preview}]
    segment_count: int


@dataclass
class EdgeCase:
    source_record_id: str
    category: str
    text_length: int
    structure_score: int
    newline_count: int
    space_block_count: int
    html_section_count: int
    preview: str
    issue: str  # human-readable reason


# ── analysis functions ──────────────────────────────────────────

def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _structure_score(
    section_count: int,
    date_range_count: int,
    bullet_like: bool,
    newline_count: int,
    uppercase_section_count: int,
) -> int:
    s = 0
    s += min(section_count, 4)
    s += min(date_range_count, 4)
    s += 1 if bullet_like else 0
    s += 1 if newline_count > 0 else 0
    s += 1 if uppercase_section_count > 0 else 0
    return s


def analyze_doc(doc: dict[str, Any]) -> DocAnalysis:
    text: str = doc.get("resume_text") or ""
    html: str = doc.get("resume_html") or ""
    compact = _compact(text)

    # space blocks
    blocks = [(m.start(), m.end() - m.start()) for m in SPACE_BLOCK_RE.finditer(text)]
    positions = [b[0] for b in blocks]
    lengths = [b[1] for b in blocks]

    # sections
    section_hits = sorted(
        {kw for kw in SECTION_KEYWORDS if re.search(r"\b" + re.escape(kw) + r"\b", compact, re.IGNORECASE)}
    )
    date_count = sum(len(p.findall(compact)) for p in DATE_PATTERNS)
    bullet_like = bool(BULLET_RE.search(text))
    newline_count = len(NEWLINE_RE.findall(text))
    upper_count = len(UPPER_SECTION_RE.findall(text))

    score = _structure_score(len(section_hits), date_count, bullet_like, newline_count, upper_count)

    # HTML
    html_section_ids = HTML_SECTION_RE.findall(html)

    return DocAnalysis(
        source_record_id=doc.get("source_record_id", ""),
        category=doc.get("category", ""),
        text_length=len(text),
        newline_count=newline_count,
        has_newlines=newline_count > 0,
        space_block_count=len(blocks),
        space_block_positions=positions,
        space_block_lengths=lengths,
        section_hits=section_hits,
        section_count=len(section_hits),
        date_range_count=date_count,
        bullet_like=bullet_like,
        uppercase_section_count=upper_count,
        structure_score=score,
        html_length=len(html),
        html_section_ids=html_section_ids,
        html_section_count=len(html_section_ids),
        html_has_content=len(html.strip()) > 0,
    )


# ── Task 1: whitespace pattern aggregation ──────────────────────

def aggregate_whitespace(analyses: list[DocAnalysis]) -> dict[str, Any]:
    all_lengths: list[int] = []
    first_rel_positions: list[float] = []

    for a in analyses:
        all_lengths.extend(a.space_block_lengths)
        if a.space_block_positions and a.text_length > 0:
            first_rel_positions.append(a.space_block_positions[0] / a.text_length)

    block_counts = [a.space_block_count for a in analyses]

    hist: dict[str, int] = {"3-5": 0, "6-10": 0, "11-20": 0, "21-50": 0, "51+": 0}
    for length in all_lengths:
        if length <= 5:
            hist["3-5"] += 1
        elif length <= 10:
            hist["6-10"] += 1
        elif length <= 20:
            hist["11-20"] += 1
        elif length <= 50:
            hist["21-50"] += 1
        else:
            hist["51+"] += 1

    return {
        "total_docs": len(analyses),
        "docs_with_space_blocks": sum(1 for a in analyses if a.space_block_count > 0),
        "pct_with_space_blocks": round(
            100 * sum(1 for a in analyses if a.space_block_count > 0) / len(analyses), 2
        ),
        "total_space_blocks": len(all_lengths),
        "mean_blocks_per_doc": round(statistics.mean(block_counts), 2) if block_counts else 0,
        "median_blocks_per_doc": round(statistics.median(block_counts), 1) if block_counts else 0,
        "max_blocks_in_single_doc": max(block_counts) if block_counts else 0,
        "block_length_histogram": hist,
        "mean_block_length": round(statistics.mean(all_lengths), 2) if all_lengths else 0,
        "median_block_length": round(statistics.median(all_lengths), 1) if all_lengths else 0,
        "mean_first_block_relative_pos": round(
            statistics.mean(first_rel_positions), 4
        ) if first_rel_positions else None,
    }


# ── Task 2: newline ratio re-confirmation ──────────────────────

def compute_newline_stats(analyses: list[DocAnalysis]) -> dict[str, Any]:
    n = len(analyses)
    with_nl = sum(1 for a in analyses if a.has_newlines)
    counts = [a.newline_count for a in analyses]
    return {
        "total_docs": n,
        "docs_with_newlines": with_nl,
        "docs_without_newlines": n - with_nl,
        "pct_with_newlines": round(100 * with_nl / n, 2),
        "pct_without_newlines": round(100 * (n - with_nl) / n, 2),
        "mean_newline_count": round(statistics.mean(counts), 2),
        "median_newline_count": round(statistics.median(counts), 1),
    }


# ── Task 3: HTML column analysis ───────────────────────────────

def compute_html_stats(analyses: list[DocAnalysis], docs_raw: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(analyses)
    with_html = sum(1 for a in analyses if a.html_has_content)
    section_counts = [a.html_section_count for a in analyses if a.html_has_content]

    # Section-ID frequency (top-25)
    id_counter: Counter[str] = Counter()
    for a in analyses:
        for sid in a.html_section_ids:
            # normalise to section type (e.g. SECTION_NAME -> NAME)
            short = sid.replace("SECTION_", "").split("_")[0] if "_" in sid else sid
            id_counter[short] += 1

    # Deeper HTML tag analysis on a few docs
    tag_counter: Counter[str] = Counter()
    for doc in docs_raw[:200]:
        html = doc.get("resume_html") or ""
        tags = HTML_TAG_RE.findall(html)
        for t in tags:
            tag_name = t.split()[0].strip("<>/").lower()
            if tag_name:
                tag_counter[tag_name] += 1

    splittable = with_html / n >= 0.95 and (statistics.mean(section_counts) if section_counts else 0) >= 2
    reason = (
        f"{with_html}/{n} docs ({round(100*with_html/n,1)}%) have HTML; "
        f"mean section count = {round(statistics.mean(section_counts),1) if section_counts else 0}. "
        + ("HTML splitting is VIABLE as primary method."
           if splittable
           else "HTML splitting is NOT reliable as sole method.")
    )

    return {
        "total_docs": n,
        "docs_with_html": with_html,
        "docs_without_html": n - with_html,
        "pct_with_html": round(100 * with_html / n, 2),
        "mean_html_sections": round(statistics.mean(section_counts), 2) if section_counts else 0,
        "median_html_sections": round(statistics.median(section_counts), 1) if section_counts else 0,
        "max_html_sections": max(section_counts) if section_counts else 0,
        "section_id_frequency_top25": dict(id_counter.most_common(25)),
        "top_html_tags": dict(tag_counter.most_common(20)),
        "html_splittable": splittable,
        "html_splittable_reason": reason,
    }


# ── Task 4: 10-sample whitespace/HTML split verification ───────

def _split_by_whitespace(text: str) -> list[dict[str, str]]:
    """Split text on \\s{3,} and try to assign section labels."""
    parts = SPACE_BLOCK_RE.split(text)
    segments: list[dict[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # try to find a section label at the start
        m = re.match(r"^([A-Z][A-Za-z &/-]+?)(?:\s{2,}|\n|$)", part)
        label = m.group(1).strip() if m else "(unlabeled)"
        segments.append({
            "label": label,
            "preview": part[:200],
            "char_count": len(part),
        })
    return segments


def _split_by_html(html: str) -> list[dict[str, str]]:
    """Split HTML by <div class='section ...'> blocks and extract text."""
    # Find all section divs
    section_splits = re.split(r'(<div\s+class="section[^"]*"[^>]*>)', html)
    segments: list[dict[str, str]] = []
    current_label = "(preamble)"

    for i, chunk in enumerate(section_splits):
        sec_match = re.match(r'<div\s+class="section[^"]*"\s+id="([^"]+)"', chunk)
        if sec_match:
            current_label = sec_match.group(1)
            continue
        # strip tags for text preview
        text = HTML_TAG_RE.sub(" ", chunk)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 10:
            segments.append({
                "label": current_label,
                "preview": text[:200],
                "char_count": len(text),
            })

    return segments


def verify_splits(docs_raw: list[dict[str, Any]], analyses: list[DocAnalysis], n: int = 10) -> list[dict[str, Any]]:
    """Pick n diverse samples and show split results."""
    # Sort by structure score and pick from different score buckets
    sorted_analyses = sorted(analyses, key=lambda a: a.structure_score)
    # Evenly sample across the range
    step = max(len(sorted_analyses) // n, 1)
    sample_indices = [min(i * step, len(sorted_analyses) - 1) for i in range(n)]

    # Build lookup
    id_to_doc: dict[str, dict[str, Any]] = {}
    for d in docs_raw:
        id_to_doc[d.get("source_record_id", "")] = d

    results: list[dict[str, Any]] = []
    for idx in sample_indices:
        a = sorted_analyses[idx]
        doc = id_to_doc.get(a.source_record_id, {})
        text = doc.get("resume_text", "")
        html = doc.get("resume_html", "")

        ws_segments = _split_by_whitespace(text)
        html_segments = _split_by_html(html) if html.strip() else []

        # Decide best method
        if html_segments and len(html_segments) >= 2:
            method = "html"
            segments = html_segments
        elif ws_segments and len(ws_segments) >= 2:
            method = "whitespace"
            segments = ws_segments
        else:
            method = "none"
            segments = ws_segments

        results.append({
            "source_record_id": a.source_record_id,
            "category": a.category,
            "structure_score": a.structure_score,
            "text_length": a.text_length,
            "method_used": method,
            "whitespace_segment_count": len(ws_segments),
            "html_segment_count": len(html_segments),
            "segments_preview": segments[:8],  # cap for readability
        })

    return results


# ── Task 5: bottom-5 edge cases ────────────────────────────────

def find_edge_cases(analyses: list[DocAnalysis], docs_raw: list[dict[str, Any]], n: int = 5) -> list[dict[str, Any]]:
    sorted_by_score = sorted(analyses, key=lambda a: (a.structure_score, a.text_length))
    bottom = sorted_by_score[:n]

    id_to_doc = {d.get("source_record_id", ""): d for d in docs_raw}

    cases: list[dict[str, Any]] = []
    for a in bottom:
        doc = id_to_doc.get(a.source_record_id, {})
        text = doc.get("resume_text", "")

        issues: list[str] = []
        if a.text_length < 100:
            issues.append("very short text")
        if a.section_count == 0:
            issues.append("no section headers detected")
        if a.date_range_count == 0:
            issues.append("no date ranges")
        if not a.bullet_like:
            issues.append("no bullet markers")
        if a.newline_count == 0:
            issues.append("no newlines")
        if a.space_block_count == 0:
            issues.append("no space blocks")
        if a.html_section_count == 0:
            issues.append("no HTML sections")

        cases.append({
            "source_record_id": a.source_record_id,
            "category": a.category,
            "text_length": a.text_length,
            "structure_score": a.structure_score,
            "newline_count": a.newline_count,
            "space_block_count": a.space_block_count,
            "html_section_count": a.html_section_count,
            "section_hits": a.section_hits,
            "preview": _compact(text)[:300],
            "issues": issues,
        })

    return cases


# ── recommendation ──────────────────────────────────────────────

def build_recommendation(
    ws_agg: dict[str, Any],
    nl_stats: dict[str, Any],
    html_stats: dict[str, Any],
    split_verification: list[dict[str, Any]],
) -> dict[str, Any]:
    html_viable = html_stats["html_splittable"]
    ws_viable = ws_agg["pct_with_space_blocks"] >= 95
    nl_low = nl_stats["pct_without_newlines"] > 40

    if html_viable and ws_viable:
        method = "hybrid"
        detail = (
            "RECOMMENDED: Hybrid approach — use HTML section divs as primary splitter "
            "(high coverage, semantic section IDs). Fall back to whitespace-block splitting "
            "for any documents where HTML is missing or has fewer than 2 sections. "
            f"HTML covers {html_stats['pct_with_html']}% of docs with mean "
            f"{html_stats['mean_html_sections']} sections. "
            f"Whitespace blocks cover {ws_agg['pct_with_space_blocks']}% of docs."
        )
    elif html_viable:
        method = "html"
        detail = (
            "Use HTML section divs for splitting. Almost all documents have HTML "
            "with multiple sections."
        )
    elif ws_viable:
        method = "whitespace"
        detail = (
            "Use whitespace-block (\\s{3,}) splitting. HTML is unreliable. "
            f"Newline-based splitting is weak ({nl_stats['pct_with_newlines']}% have newlines)."
        )
    else:
        method = "manual"
        detail = "Neither HTML nor whitespace provides reliable splitting."

    # Verification summary
    methods_used = Counter(v["method_used"] for v in split_verification)

    return {
        "recommended_method": method,
        "detail": detail,
        "newline_warning": (
            f"{nl_stats['pct_without_newlines']}% of docs have NO newlines — "
            "newline-only splitting is not viable"
        ) if nl_low else None,
        "verification_method_distribution": dict(methods_used),
    }


# ── main ────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Issue #6: Re-analyze 1st data from MongoDB")
    p.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    p.add_argument("--db-name", default="prodapt_capstone")
    p.add_argument("--collection", default="source_1st_resumes")
    p.add_argument(
        "--json-out",
        default=str(Path(__file__).resolve().parent / "reanalyze_1st_resume_structure_report.json"),
        help="Output JSON report path",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    print(f"Connecting to {args.mongo_uri} / {args.db_name} / {args.collection} ...")
    client: MongoClient = MongoClient(args.mongo_uri)
    db = client[args.db_name]
    coll = db[args.collection]

    docs_raw: list[dict[str, Any]] = list(coll.find())
    print(f"Loaded {len(docs_raw)} documents from MongoDB")

    if not docs_raw:
        print("ERROR: No documents found. Run ingest_csv_to_mongo.py first.")
        return

    # ── analyse every document ──
    print("Analyzing documents ...")
    analyses: list[DocAnalysis] = [analyze_doc(d) for d in docs_raw]

    # ── Task 1: whitespace aggregation ──
    print("Task 1: Whitespace pattern aggregation ...")
    ws_agg = aggregate_whitespace(analyses)

    # ── Task 2: newline stats ──
    print("Task 2: Newline ratio re-confirmation ...")
    nl_stats = compute_newline_stats(analyses)

    # ── Task 3: HTML stats ──
    print("Task 3: HTML column analysis ...")
    html_stats = compute_html_stats(analyses, docs_raw)

    # ── Task 4: 10-sample split verification ──
    print("Task 4: 10-sample split verification ...")
    split_verification = verify_splits(docs_raw, analyses, n=10)

    # ── Task 5: bottom-5 edge cases ──
    print("Task 5: Bottom-5 edge cases ...")
    edge_cases = find_edge_cases(analyses, docs_raw, n=5)

    # ── Recommendation ──
    print("Building recommendation ...")
    recommendation = build_recommendation(ws_agg, nl_stats, html_stats, split_verification)

    # ── Build report ──
    report = {
        "meta": {
            "source_collection": args.collection,
            "total_documents": len(docs_raw),
            "script": "reanalyze_1st_resume_structure.py",
            "issue": "#6 – [Pipeline v2] Step 1: 1stデータ再解析",
        },
        "whitespace_pattern_analysis": ws_agg,
        "newline_stats": nl_stats,
        "html_analysis": html_stats,
        "split_verification_10_samples": split_verification,
        "edge_cases_bottom_5": edge_cases,
        "recommendation": recommendation,
    }

    # ── Console summary ──
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"  Total documents:           {len(docs_raw)}")
    print(f"  Docs with space blocks:    {ws_agg['docs_with_space_blocks']} ({ws_agg['pct_with_space_blocks']}%)")
    print(f"  Mean blocks/doc:           {ws_agg['mean_blocks_per_doc']}")
    print(f"  Block length histogram:    {ws_agg['block_length_histogram']}")
    print(f"  Docs WITH newlines:        {nl_stats['docs_with_newlines']} ({nl_stats['pct_with_newlines']}%)")
    print(f"  Docs WITHOUT newlines:     {nl_stats['docs_without_newlines']} ({nl_stats['pct_without_newlines']}%)")
    print(f"  Docs with HTML:            {html_stats['docs_with_html']} ({html_stats['pct_with_html']}%)")
    print(f"  Mean HTML sections:        {html_stats['mean_html_sections']}")
    print(f"  HTML splittable:           {html_stats['html_splittable']}")
    print(f"  RECOMMENDATION:            {recommendation['recommended_method']}")
    print(f"  Detail:                    {recommendation['detail']}")
    print("=" * 60)

    # ── Write JSON ──
    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nJSON report written to: {out_path}")


if __name__ == "__main__":
    main()
