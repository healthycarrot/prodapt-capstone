from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "3rd_data"


@dataclass
class PersonAnalysis:
    person_id: str
    name: str
    has_summary: bool
    has_experience: bool
    has_skill: bool
    has_education: bool
    experience_count: int
    education_count: int
    skill_count: int
    ability_count: int
    total_skill_like_count: int
    preview_experience_titles: list[str]
    preview_education_programs: list[str]
    preview_skills: list[str]


@dataclass
class AggregateReport:
    total_people: int
    rows_with_summary: int
    rows_with_experience: int
    rows_with_skill: int
    rows_with_education: int
    rows_with_all_four: int
    rows_with_three_or_more: int
    rows_with_two_or_more: int
    rows_with_experience_and_skill: int
    rows_with_skill_and_education: int
    median_experience_count: float
    median_education_count: float
    median_skill_like_count: float
    mean_experience_count: float
    mean_education_count: float
    mean_skill_like_count: float
    source_summary_note: str


def read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_people(data_dir: Path) -> dict[str, dict[str, str]]:
    people_rows = read_csv_rows(data_dir / "01_people.csv")
    return {row["person_id"]: row for row in people_rows}


def group_rows_by_person(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["person_id"]].append(row)
    return grouped


def build_person_analyses(data_dir: Path) -> list[PersonAnalysis]:
    people = load_people(data_dir)
    education = group_rows_by_person(read_csv_rows(data_dir / "03_education.csv"))
    experience = group_rows_by_person(read_csv_rows(data_dir / "04_experience.csv"))
    person_skills = group_rows_by_person(read_csv_rows(data_dir / "05_person_skills.csv"))
    abilities = group_rows_by_person(read_csv_rows(data_dir / "02_abilities.csv"))

    analyses: list[PersonAnalysis] = []
    for person_id, person_row in people.items():
        person_experience = experience.get(person_id, [])
        person_education = education.get(person_id, [])
        person_skills_rows = person_skills.get(person_id, [])
        person_abilities = abilities.get(person_id, [])

        analyses.append(
            PersonAnalysis(
                person_id=person_id,
                name=(person_row.get("name", "") or "").strip(),
                has_summary=False,
                has_experience=bool(person_experience),
                has_skill=bool(person_skills_rows or person_abilities),
                has_education=bool(person_education),
                experience_count=len(person_experience),
                education_count=len(person_education),
                skill_count=len(person_skills_rows),
                ability_count=len(person_abilities),
                total_skill_like_count=len(person_skills_rows) + len(person_abilities),
                preview_experience_titles=[row.get("title", "") for row in person_experience[:3] if row.get("title")],
                preview_education_programs=[row.get("program", "") for row in person_education[:3] if row.get("program")],
                preview_skills=[
                    value
                    for value in ([row.get("skill", "") for row in person_skills_rows[:3]] + [row.get("ability", "") for row in person_abilities[:3]])
                    if value
                ][:5],
            )
        )

    analyses.sort(key=lambda item: int(item.person_id))
    return analyses


def build_aggregate_report(rows: list[PersonAnalysis]) -> AggregateReport:
    component_totals = [
        int(row.has_summary) + int(row.has_experience) + int(row.has_skill) + int(row.has_education)
        for row in rows
    ]
    return AggregateReport(
        total_people=len(rows),
        rows_with_summary=sum(1 for row in rows if row.has_summary),
        rows_with_experience=sum(1 for row in rows if row.has_experience),
        rows_with_skill=sum(1 for row in rows if row.has_skill),
        rows_with_education=sum(1 for row in rows if row.has_education),
        rows_with_all_four=sum(1 for total in component_totals if total == 4),
        rows_with_three_or_more=sum(1 for total in component_totals if total >= 3),
        rows_with_two_or_more=sum(1 for total in component_totals if total >= 2),
        rows_with_experience_and_skill=sum(1 for row in rows if row.has_experience and row.has_skill),
        rows_with_skill_and_education=sum(1 for row in rows if row.has_skill and row.has_education),
        median_experience_count=statistics.median(row.experience_count for row in rows),
        median_education_count=statistics.median(row.education_count for row in rows),
        median_skill_like_count=statistics.median(row.total_skill_like_count for row in rows),
        mean_experience_count=round(statistics.mean(row.experience_count for row in rows), 3),
        mean_education_count=round(statistics.mean(row.education_count for row in rows), 3),
        mean_skill_like_count=round(statistics.mean(row.total_skill_like_count for row in rows), 3),
        source_summary_note="3rd_data is relational and has no dedicated summary table/column, so summary is treated as unavailable in the source schema.",
    )


def choose_samples(rows: list[PersonAnalysis], sample_size: int, seed: int) -> dict[str, list[PersonAnalysis]]:
    rng = random.Random(seed)
    sample_size = min(sample_size, len(rows))
    random_sample = rng.sample(rows, sample_size)
    complete_profiles = [row for row in rows if row.has_experience and row.has_skill and row.has_education][:sample_size]
    sparse_profiles = sorted(
        rows,
        key=lambda row: (
            int(row.has_experience) + int(row.has_skill) + int(row.has_education),
            row.total_skill_like_count,
            row.experience_count,
        ),
    )[:sample_size]
    skill_rich = sorted(rows, key=lambda row: (-row.total_skill_like_count, row.person_id))[:sample_size]
    return {
        "random": random_sample,
        "complete_profiles": complete_profiles,
        "sparse_profiles": sparse_profiles,
        "skill_rich_profiles": skill_rich,
    }


def top_titles(rows: list[PersonAnalysis], top_n: int = 10) -> list[dict[str, object]]:
    counter = Counter()
    for row in rows:
        if row.name:
            counter[row.name] += 1
    return [
        {"name": name, "count": count}
        for name, count in counter.most_common(top_n)
    ]


def print_report(summary: AggregateReport, samples: dict[str, list[PersonAnalysis]], titles: list[dict[str, object]]) -> None:
    print("=== 3rd Structured Resume Data Analysis ===")
    for key, value in asdict(summary).items():
        print(f"{key}: {value}")

    print("\n=== Frequent Names / Headline Values ===")
    for item in titles:
        print(f"{item['name']}: count={item['count']}")

    for group_name, sample_rows in samples.items():
        print(f"\n=== Sample Group: {group_name} ===")
        for row in sample_rows:
            print(
                f"person_id={row.person_id} | name={row.name} | summary={row.has_summary} | "
                f"experience={row.has_experience} ({row.experience_count}) | "
                f"skill={row.has_skill} ({row.total_skill_like_count}) | education={row.has_education} ({row.education_count})"
            )
            print(f"experience_preview={row.preview_experience_titles}")
            print(f"education_preview={row.preview_education_programs}")
            print(f"skills_preview={row.preview_skills}")
            print("---")


def build_payload(summary: AggregateReport, samples: dict[str, list[PersonAnalysis]], titles: list[dict[str, object]]) -> dict[str, object]:
    return {
        "summary": asdict(summary),
        "top_names": titles,
        "samples": {
            group_name: [asdict(row) for row in group_rows]
            for group_name, group_rows in samples.items()
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze whether 3rd_data provides summary, experience, skill, and education components per person."
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help="Path to the 3rd_data directory.",
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
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"3rd data directory not found: {data_dir}")

    analyses = build_person_analyses(data_dir)
    summary = build_aggregate_report(analyses)
    samples = choose_samples(analyses, sample_size=args.sample_size, seed=args.seed)
    titles = top_titles(analyses)

    print_report(summary, samples, titles)

    if args.json_out:
        payload = build_payload(summary, samples, titles)
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nJSON report written to: {json_path}")


if __name__ == "__main__":
    main()
