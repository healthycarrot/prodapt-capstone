from __future__ import annotations

import argparse
import ast
import json
import random
import re
import statistics
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEXT_PATH = REPO_ROOT / "data" / "5th_data" / "train_data.txt"

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
        r"\bwork\s+experience\b",
        r"\bprofessional\s+experience\b",
        r"\bemployment\s+history\b",
        r"\bcareer\s+history\b",
        r"\bexperience\b",
        r"\bproject\b",
        r"\bprojects\b",
    ],
    "skill": [
        r"\bskills?\b",
        r"\bskill\s+set\b",
        r"\btechnical\s+skills\b",
        r"\bcore\s+competencies\b",
        r"\bcore\s+qualifications\b",
        r"\btechnical\s+skillset\b",
        r"\bsoftware\s+skills\b",
    ],
    "education": [
        r"\beducation\b",
        r"\beducation\s+details\b",
        r"\bacademic\s+background\b",
        r"\bacademeic\s+credentials\b",
        r"\beducation\s+qualification\b",
        r"\bqualification\b",
        r"\bqualifications\b",
        r"\bdegree\b",
    ],
}

DATE_RANGE_PATTERNS: list[re.Pattern[str]] = [
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

BULLET_PATTERN = re.compile(r"[•●▪◦■□➢❑✓]|\s[*-]\s")


@dataclass
class ResumeRecordAnalysis:
    index: int
    has_summary: bool
    has_experience: bool
    has_skill: bool
    has_education: bool
    detected_sections: list[str]
    entity_labels: list[str]
    entity_count: int
    date_range_count: int
    bullet_like: bool
    text_length: int
    preview: str


@dataclass
class AggregateReport:
    total_records: int
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
    median_entity_count: float
    mean_entity_count: float


def load_records(text_path: Path) -> list[tuple[str, dict[str, Any]]]:
    raw_text = text_path.read_text(encoding="utf-8")
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n+", raw_text) if chunk.strip()]
    records: list[tuple[str, dict[str, Any]]] = []
    for chunk in chunks:
        parsed = ast.literal_eval(chunk)
        if not isinstance(parsed, tuple) or len(parsed) != 2:
            continue
        resume_text, metadata = parsed
        if isinstance(resume_text, str) and isinstance(metadata, dict):
            records.append((resume_text, metadata))
    return records


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def detect_sections(compact_text: str) -> list[str]:
    hits: list[str] = []
    for name, patterns in SECTION_PATTERNS.items():
        if any(re.search(pattern, compact_text, re.IGNORECASE) for pattern in patterns):
            hits.append(name)
    return hits


def count_date_ranges(compact_text: str) -> int:
    return sum(len(pattern.findall(compact_text)) for pattern in DATE_RANGE_PATTERNS)


def analyze_record(index: int, resume_text: str, metadata: dict[str, Any]) -> ResumeRecordAnalysis:
    compact = normalize_text(resume_text)
    sections = detect_sections(compact)
    entities = metadata.get("entities", [])
    entity_labels = sorted({str(entity[2]) for entity in entities if isinstance(entity, (tuple, list)) and len(entity) >= 3})
    return ResumeRecordAnalysis(
        index=index,
        has_summary="summary" in sections,
        has_experience="experience" in sections,
        has_skill="skill" in sections,
        has_education="education" in sections,
        detected_sections=sections,
        entity_labels=entity_labels,
        entity_count=len(entities),
        date_range_count=count_date_ranges(compact),
        bullet_like=bool(BULLET_PATTERN.search(resume_text)),
        text_length=len(resume_text),
        preview=compact[:320],
    )


def build_aggregate_report(rows: list[ResumeRecordAnalysis]) -> AggregateReport:
    totals = [
        int(row.has_summary) + int(row.has_experience) + int(row.has_skill) + int(row.has_education)
        for row in rows
    ]
    return AggregateReport(
        total_records=len(rows),
        rows_with_summary=sum(1 for row in rows if row.has_summary),
        rows_with_experience=sum(1 for row in rows if row.has_experience),
        rows_with_skill=sum(1 for row in rows if row.has_skill),
        rows_with_education=sum(1 for row in rows if row.has_education),
        rows_with_all_four=sum(1 for total in totals if total == 4),
        rows_with_three_or_more=sum(1 for total in totals if total >= 3),
        rows_with_two_or_more=sum(1 for total in totals if total >= 2),
        rows_with_date_ranges=sum(1 for row in rows if row.date_range_count > 0),
        rows_with_bullet_like_markers=sum(1 for row in rows if row.bullet_like),
        median_text_length=statistics.median(row.text_length for row in rows),
        median_entity_count=statistics.median(row.entity_count for row in rows),
        mean_entity_count=round(statistics.mean(row.entity_count for row in rows), 3),
    )


def top_entity_labels(records: list[ResumeRecordAnalysis], top_n: int = 15) -> list[dict[str, object]]:
    counter: Counter[str] = Counter()
    for record in records:
        counter.update(record.entity_labels)
    return [{"label": label, "count": count} for label, count in counter.most_common(top_n)]


def choose_samples(rows: list[ResumeRecordAnalysis], sample_size: int, seed: int) -> dict[str, list[ResumeRecordAnalysis]]:
    rng = random.Random(seed)
    sample_size = min(sample_size, len(rows))
    random_sample = rng.sample(rows, sample_size)
    all_four = [row for row in rows if row.has_summary and row.has_experience and row.has_skill and row.has_education][:sample_size]
    missing_any = [row for row in rows if not (row.has_summary and row.has_experience and row.has_skill and row.has_education)][:sample_size]
    sparse = sorted(
        rows,
        key=lambda row: (
            int(row.has_summary) + int(row.has_experience) + int(row.has_skill) + int(row.has_education),
            row.entity_count,
            row.text_length,
        ),
    )[:sample_size]
    return {
        "random": random_sample,
        "all_four": all_four,
        "missing_any": missing_any,
        "sparse": sparse,
    }


def print_report(summary: AggregateReport, entity_labels: list[dict[str, object]], samples: dict[str, list[ResumeRecordAnalysis]]) -> None:
    print("=== 5th train_data.txt Resume Section Analysis ===")
    for key, value in asdict(summary).items():
        print(f"{key}: {value}")

    print("\n=== Top Entity Labels ===")
    for item in entity_labels:
        print(f"{item['label']}: count={item['count']}")

    for group_name, sample_rows in samples.items():
        print(f"\n=== Sample Group: {group_name} ===")
        for row in sample_rows:
            print(
                f"index={row.index} | sections={row.detected_sections} | entities={row.entity_count} | "
                f"dates={row.date_range_count} | bullets={row.bullet_like}"
            )
            print(f"entity_labels={row.entity_labels}")
            print(f"preview={row.preview}")
            print("---")


def build_payload(summary: AggregateReport, entity_labels: list[dict[str, object]], samples: dict[str, list[ResumeRecordAnalysis]]) -> dict[str, object]:
    return {
        "summary": asdict(summary),
        "top_entity_labels": entity_labels,
        "samples": {
            group_name: [asdict(row) for row in group_rows]
            for group_name, group_rows in samples.items()
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze whether 5th_data train_data.txt resumes contain summary, experience, skill, and education elements."
    )
    parser.add_argument(
        "--text-path",
        default=str(DEFAULT_TEXT_PATH),
        help="Path to train_data.txt",
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
    text_path = Path(args.text_path)
    if not text_path.exists():
        raise FileNotFoundError(f"train_data.txt not found: {text_path}")

    records = load_records(text_path)
    analyses = [analyze_record(index, resume_text, metadata) for index, (resume_text, metadata) in enumerate(records)]
    summary = build_aggregate_report(analyses)
    entity_labels = top_entity_labels(analyses)
    samples = choose_samples(analyses, sample_size=args.sample_size, seed=args.seed)

    print_report(summary, entity_labels, samples)

    if args.json_out:
        payload = build_payload(summary, entity_labels, samples)
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nJSON report written to: {json_path}")


if __name__ == "__main__":
    main()
