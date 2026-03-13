from __future__ import annotations

import argparse
import csv
import json
import random
import re
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, cast


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV_PATH = REPO_ROOT / "data" / "1st_data" / "Resume" / "Resume.csv"

SECTION_PATTERNS: list[tuple[str, str]] = [
    (
        "summary",
        r"\b(?:professional\s+summary|career\s+overview|professional\s+overview|summary|profile|objective|professional\s+profile)\b",
    ),
    (
        "skills",
        r"\b(?:technical\s+skills|core\s+qualifications|qualifications|skills|highlights|areas\s+of\s+expertise|competencies)\b",
    ),
    (
        "experience",
        r"\b(?:professional\s+experience|work\s+experience|employment\s+history|career\s+history|experience)\b",
    ),
    ("education", r"\b(?:education|academic\s+background|educational\s+background)\b"),
    ("certifications", r"\b(?:certifications|licenses|credentials|certificates)\b"),
    ("projects", r"\bprojects\b"),
    ("languages", r"\blanguages\b"),
    ("awards", r"\b(?:awards|achievements|honors)\b"),
    ("affiliations", r"\b(?:affiliations|memberships|professional\s+affiliations)\b"),
]

DATE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"\b(?:0?[1-9]|1[0-2])[/-](?:19|20)?\d{2}\s*(?:to|-|–|—)\s*(?:current|present|(?:0?[1-9]|1[0-2])[/-](?:19|20)?\d{2})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(?:19|20)\d{2}\s*(?:to|-|–|—)\s*(?:current|present|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(?:19|20)\d{2})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:19|20)\d{2}\s*(?:to|-|–|—)\s*(?:current|present|(19|20)\d{2})\b",
        re.IGNORECASE,
    ),
]

BULLET_PATTERN = re.compile(r"[•●▪◦■□]|\s[*-]\s")
UPPERCASE_SECTION_PATTERN = re.compile(r"\b(?:SUMMARY|SKILLS|EXPERIENCE|EDUCATION|CERTIFICATIONS|PROJECTS|LANGUAGES)\b")
SPACE_BLOCK_PATTERN = re.compile(r"\s{3,}")


@dataclass
class ResumeAnalysis:
    resume_id: str
    category: str
    text_length: int
    newline_count: int
    space_block_count: int
    bullet_like: bool
    section_hits: list[str]
    section_count: int
    date_range_count: int
    uppercase_section_count: int
    structure_score: int
    preview: str


@dataclass
class AggregateSummary:
    total_rows: int
    rows_with_1plus_sections: int
    rows_with_2plus_sections: int
    rows_with_3plus_sections: int
    rows_with_any_date_range: int
    rows_with_bullet_like_markers: int
    rows_with_newlines: int
    rows_with_large_space_blocks: int
    median_text_length: float
    median_newline_count: float
    mean_structure_score: float
    median_structure_score: float


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def detect_sections(compact_text: str) -> list[str]:
    hits: list[str] = []
    for name, pattern in SECTION_PATTERNS:
        if re.search(pattern, compact_text, re.IGNORECASE):
            hits.append(name)
    return hits


def count_date_ranges(compact_text: str) -> int:
    return sum(len(pattern.findall(compact_text)) for pattern in DATE_PATTERNS)


def structure_score(
    section_count: int,
    date_range_count: int,
    bullet_like: bool,
    newline_count: int,
    uppercase_section_count: int,
) -> int:
    score = 0
    score += min(section_count, 4)
    score += min(date_range_count, 4)
    score += 1 if bullet_like else 0
    score += 1 if newline_count > 0 else 0
    score += 1 if uppercase_section_count > 0 else 0
    return score


def analyze_row(row: dict[str, str]) -> ResumeAnalysis:
    text = row.get("Resume_str", "") or ""
    compact = normalize_whitespace(text)
    section_hits = detect_sections(compact)
    date_range_count = count_date_ranges(compact)
    bullet_like = bool(BULLET_PATTERN.search(text))
    newline_count = text.count("\n") + text.count("\r")
    uppercase_section_count = len(UPPERCASE_SECTION_PATTERN.findall(text))
    score = structure_score(
        section_count=len(section_hits),
        date_range_count=date_range_count,
        bullet_like=bullet_like,
        newline_count=newline_count,
        uppercase_section_count=uppercase_section_count,
    )
    return ResumeAnalysis(
        resume_id=row.get("ID", ""),
        category=row.get("Category", "UNKNOWN"),
        text_length=len(text),
        newline_count=newline_count,
        space_block_count=len(SPACE_BLOCK_PATTERN.findall(text)),
        bullet_like=bullet_like,
        section_hits=section_hits,
        section_count=len(section_hits),
        date_range_count=date_range_count,
        uppercase_section_count=uppercase_section_count,
        structure_score=score,
        preview=compact[:300],
    )


def summarize(rows: list[ResumeAnalysis]) -> AggregateSummary:
    return AggregateSummary(
        total_rows=len(rows),
        rows_with_1plus_sections=sum(1 for row in rows if row.section_count >= 1),
        rows_with_2plus_sections=sum(1 for row in rows if row.section_count >= 2),
        rows_with_3plus_sections=sum(1 for row in rows if row.section_count >= 3),
        rows_with_any_date_range=sum(1 for row in rows if row.date_range_count > 0),
        rows_with_bullet_like_markers=sum(1 for row in rows if row.bullet_like),
        rows_with_newlines=sum(1 for row in rows if row.newline_count > 0),
        rows_with_large_space_blocks=sum(1 for row in rows if row.space_block_count > 0),
        median_text_length=statistics.median(row.text_length for row in rows),
        median_newline_count=statistics.median(row.newline_count for row in rows),
        mean_structure_score=round(statistics.mean(row.structure_score for row in rows), 3),
        median_structure_score=statistics.median(row.structure_score for row in rows),
    )


def category_breakdown(rows: Iterable[ResumeAnalysis]) -> list[dict[str, object]]:
    grouped: dict[str, list[ResumeAnalysis]] = {}
    for row in rows:
        grouped.setdefault(row.category, []).append(row)

    breakdown: list[dict[str, object]] = []
    for category, items in sorted(grouped.items()):
        breakdown.append(
            {
                "category": category,
                "count": len(items),
                "avg_structure_score": round(statistics.mean(item.structure_score for item in items), 3),
                "pct_with_sections": round(
                    100 * sum(1 for item in items if item.section_count >= 1) / len(items),
                    2,
                ),
                "pct_with_dates": round(
                    100 * sum(1 for item in items if item.date_range_count > 0) / len(items),
                    2,
                ),
            }
        )
    return breakdown


def choose_samples(rows: list[ResumeAnalysis], sample_size: int, seed: int) -> dict[str, list[ResumeAnalysis]]:
    rng = random.Random(seed)
    sample_size = min(sample_size, len(rows))

    shuffled = rows[:]
    rng.shuffle(shuffled)

    high = sorted((row for row in shuffled if row.structure_score >= 6), key=lambda row: (-row.structure_score, row.resume_id))[:sample_size]
    medium = sorted((row for row in shuffled if 3 <= row.structure_score <= 5), key=lambda row: (-row.structure_score, row.resume_id))[:sample_size]
    low = sorted((row for row in shuffled if row.structure_score <= 2), key=lambda row: (row.structure_score, row.resume_id))[:sample_size]
    random_sample = rng.sample(rows, sample_size)

    return {
        "random": random_sample,
        "high_structure": high,
        "medium_structure": medium,
        "low_structure": low,
    }


def print_report(summary: AggregateSummary, samples: dict[str, list[ResumeAnalysis]], top_categories: list[dict[str, object]]) -> None:
    print("=== 1st Resume.csv Structure Analysis ===")
    print(f"total_rows: {summary.total_rows}")
    print(f"rows_with_1plus_sections: {summary.rows_with_1plus_sections}")
    print(f"rows_with_2plus_sections: {summary.rows_with_2plus_sections}")
    print(f"rows_with_3plus_sections: {summary.rows_with_3plus_sections}")
    print(f"rows_with_any_date_range: {summary.rows_with_any_date_range}")
    print(f"rows_with_bullet_like_markers: {summary.rows_with_bullet_like_markers}")
    print(f"rows_with_newlines: {summary.rows_with_newlines}")
    print(f"rows_with_large_space_blocks: {summary.rows_with_large_space_blocks}")
    print(f"median_text_length: {summary.median_text_length}")
    print(f"median_newline_count: {summary.median_newline_count}")
    print(f"mean_structure_score: {summary.mean_structure_score}")
    print(f"median_structure_score: {summary.median_structure_score}")

    print("\n=== Top Categories by Average Structure Score ===")
    for item in top_categories[:10]:
        print(
            f"{item['category']}: count={item['count']}, avg_structure_score={item['avg_structure_score']}, "
            f"pct_with_sections={item['pct_with_sections']}%, pct_with_dates={item['pct_with_dates']}%"
        )

    for sample_name, sample_rows in samples.items():
        print(f"\n=== Sample Group: {sample_name} ===")
        for row in sample_rows:
            print(
                f"ID={row.resume_id} | category={row.category} | score={row.structure_score} | "
                f"sections={row.section_hits} | dates={row.date_range_count} | bullets={row.bullet_like} | "
                f"newlines={row.newline_count}"
            )
            print(f"preview={row.preview}")
            print("---")


def build_payload(
    summary: AggregateSummary,
    samples: dict[str, list[ResumeAnalysis]],
    categories: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "summary": asdict(summary),
        "categories": categories,
        "samples": {
            group_name: [asdict(row) for row in group_rows]
            for group_name, group_rows in samples.items()
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze how much structural signal exists in the 1st Resume.csv Resume_str fields."
    )
    parser.add_argument(
        "--csv-path",
        default=str(DEFAULT_CSV_PATH),
        help="Path to the 1st Resume.csv",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=5,
        help="Number of examples to print for each sample group.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling.",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional path to write the analysis result as JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    analyses: list[ResumeAnalysis] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            analyses.append(analyze_row(row))

    summary = summarize(analyses)
    categories = sorted(
        category_breakdown(analyses),
        key=lambda item: (
            -cast(float, item["avg_structure_score"]),
            str(item["category"]),
        ),
    )
    samples = choose_samples(analyses, sample_size=args.sample_size, seed=args.seed)

    print_report(summary, samples, categories)

    if args.json_out:
        payload = build_payload(summary, samples, categories)
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nJSON report written to: {json_path}")


if __name__ == "__main__":
    main()
