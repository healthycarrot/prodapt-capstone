from __future__ import annotations

import argparse
import csv
import json
import random
import re
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV_PATH = REPO_ROOT / "data" / "2nd_data" / "UpdatedResumeDataSet.csv"

SECTION_PATTERNS: dict[str, list[str]] = {
    "summary": [
        r"\bprofessional\s+summary\b",
        r"\bcareer\s+overview\b",
        r"\bprofessional\s+overview\b",
        r"\bsummary\b",
        r"\bprofile\b",
        r"\bobjective\b",
        r"\babout\s+me\b",
    ],
    "experience": [
        r"\bexperience\b",
        r"\bwork\s+experience\b",
        r"\bprofessional\s+experience\b",
        r"\bemployment\s+history\b",
        r"\bcareer\s+history\b",
        r"\bprojects\b",
    ],
    "skill": [
        r"\bskills?\b",
        r"\bskill\s+details\b",
        r"\btechnical\s+skills\b",
        r"\bcore\s+qualifications\b",
        r"\bcompetencies\b",
        r"\bhighlights\b",
        r"\bareas\s+of\s+interest\b",
    ],
    "education": [
        r"\beducation\b",
        r"\beducation\s+details\b",
        r"\bacademic\s+background\b",
        r"\bqualification\b",
        r"\bqualifications\b",
        r"\bdegree\b",
    ],
}

DATE_RANGE_PATTERNS = [
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

BULLET_PATTERN = re.compile(r"[•●▪◦■□]|\s[*-]\s|\bq\b", re.IGNORECASE)


@dataclass
class ResumeSectionAnalysis:
    row_index: int
    category: str
    text_length: int
    newline_count: int
    bullet_like: bool
    date_range_count: int
    summary: bool
    experience: bool
    skill: bool
    education: bool
    detected_sections: list[str]
    preview: str


@dataclass
class AggregateReport:
    total_rows: int
    rows_with_summary: int
    rows_with_experience: int
    rows_with_skill: int
    rows_with_education: int
    rows_with_all_four: int
    rows_with_three_or_more: int
    rows_with_two_or_more: int
    rows_with_date_ranges: int
    rows_with_bullet_like_markers: int
    median_text_length: float
    median_newline_count: float


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def detect_sections(compact_text: str) -> dict[str, bool]:
    detected: dict[str, bool] = {}
    for name, patterns in SECTION_PATTERNS.items():
        detected[name] = any(re.search(pattern, compact_text, re.IGNORECASE) for pattern in patterns)
    return detected


def count_date_ranges(compact_text: str) -> int:
    return sum(len(pattern.findall(compact_text)) for pattern in DATE_RANGE_PATTERNS)


def analyze_row(row_index: int, row: dict[str, str]) -> ResumeSectionAnalysis:
    raw_text = row.get("Resume", "") or ""
    compact = normalize_text(raw_text)
    detected = detect_sections(compact)
    detected_sections = [name for name, is_present in detected.items() if is_present]
    return ResumeSectionAnalysis(
        row_index=row_index,
        category=row.get("Category", "UNKNOWN") or "UNKNOWN",
        text_length=len(raw_text),
        newline_count=raw_text.count("\n") + raw_text.count("\r"),
        bullet_like=bool(BULLET_PATTERN.search(raw_text)),
        date_range_count=count_date_ranges(compact),
        summary=detected["summary"],
        experience=detected["experience"],
        skill=detected["skill"],
        education=detected["education"],
        detected_sections=detected_sections,
        preview=compact[:320],
    )


def build_aggregate_report(rows: list[ResumeSectionAnalysis]) -> AggregateReport:
    section_totals = [
        int(row.summary) + int(row.experience) + int(row.skill) + int(row.education)
        for row in rows
    ]
    return AggregateReport(
        total_rows=len(rows),
        rows_with_summary=sum(1 for row in rows if row.summary),
        rows_with_experience=sum(1 for row in rows if row.experience),
        rows_with_skill=sum(1 for row in rows if row.skill),
        rows_with_education=sum(1 for row in rows if row.education),
        rows_with_all_four=sum(1 for total in section_totals if total == 4),
        rows_with_three_or_more=sum(1 for total in section_totals if total >= 3),
        rows_with_two_or_more=sum(1 for total in section_totals if total >= 2),
        rows_with_date_ranges=sum(1 for row in rows if row.date_range_count > 0),
        rows_with_bullet_like_markers=sum(1 for row in rows if row.bullet_like),
        median_text_length=statistics.median(row.text_length for row in rows),
        median_newline_count=statistics.median(row.newline_count for row in rows),
    )


def build_category_report(rows: Iterable[ResumeSectionAnalysis]) -> list[dict[str, object]]:
    grouped: dict[str, list[ResumeSectionAnalysis]] = defaultdict(list)
    for row in rows:
        grouped[row.category].append(row)

    report: list[dict[str, object]] = []
    for category, items in sorted(grouped.items()):
        report.append(
            {
                "category": category,
                "count": len(items),
                "pct_summary": round(100 * sum(1 for item in items if item.summary) / len(items), 2),
                "pct_experience": round(100 * sum(1 for item in items if item.experience) / len(items), 2),
                "pct_skill": round(100 * sum(1 for item in items if item.skill) / len(items), 2),
                "pct_education": round(100 * sum(1 for item in items if item.education) / len(items), 2),
                "pct_all_four": round(
                    100
                    * sum(
                        1
                        for item in items
                        if item.summary and item.experience and item.skill and item.education
                    )
                    / len(items),
                    2,
                ),
            }
        )
    return report


def choose_samples(rows: list[ResumeSectionAnalysis], sample_size: int, seed: int) -> dict[str, list[ResumeSectionAnalysis]]:
    rng = random.Random(seed)
    sample_size = min(sample_size, len(rows))
    random_sample = rng.sample(rows, sample_size)

    all_four = [row for row in rows if row.summary and row.experience and row.skill and row.education]
    missing_any = [row for row in rows if not (row.summary and row.experience and row.skill and row.education)]
    sparse = sorted(
        rows,
        key=lambda row: (
            int(row.summary) + int(row.experience) + int(row.skill) + int(row.education),
            row.text_length,
        ),
    )[:sample_size]

    return {
        "random": random_sample,
        "all_four": all_four[:sample_size],
        "missing_any": missing_any[:sample_size],
        "sparse": sparse,
    }


def print_report(summary: AggregateReport, categories: list[dict[str, object]], samples: dict[str, list[ResumeSectionAnalysis]]) -> None:
    print("=== 2nd UpdatedResumeDataSet.csv Section Analysis ===")
    for key, value in asdict(summary).items():
        print(f"{key}: {value}")

    print("\n=== Category Coverage ===")
    for item in categories:
        print(
            f"{item['category']}: count={item['count']}, summary={item['pct_summary']}%, "
            f"experience={item['pct_experience']}%, skill={item['pct_skill']}%, "
            f"education={item['pct_education']}%, all_four={item['pct_all_four']}%"
        )

    for group_name, group_rows in samples.items():
        print(f"\n=== Sample Group: {group_name} ===")
        for row in group_rows:
            print(
                f"row={row.row_index} | category={row.category} | sections={row.detected_sections} | "
                f"dates={row.date_range_count} | bullets={row.bullet_like} | length={row.text_length}"
            )
            print(f"preview={row.preview}")
            print("---")


def build_payload(summary: AggregateReport, categories: list[dict[str, object]], samples: dict[str, list[ResumeSectionAnalysis]]) -> dict[str, object]:
    return {
        "summary": asdict(summary),
        "categories": categories,
        "samples": {
            group_name: [asdict(item) for item in items]
            for group_name, items in samples.items()
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze whether the 2nd UpdatedResumeDataSet.csv resumes contain summary, experience, skill, and education elements."
    )
    parser.add_argument(
        "--csv-path",
        default=str(DEFAULT_CSV_PATH),
        help="Path to UpdatedResumeDataSet.csv",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=5,
        help="Number of examples to print per sample group.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling.",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional path to write the report as JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    analyses: list[ResumeSectionAnalysis] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            analyses.append(analyze_row(index, row))

    summary = build_aggregate_report(analyses)
    categories = build_category_report(analyses)
    samples = choose_samples(analyses, sample_size=args.sample_size, seed=args.seed)

    print_report(summary, categories, samples)

    if args.json_out:
        payload = build_payload(summary, categories, samples)
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nJSON report written to: {json_path}")


if __name__ == "__main__":
    main()
