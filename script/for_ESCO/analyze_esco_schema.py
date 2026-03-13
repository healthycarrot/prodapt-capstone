from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "ESCO"
DEFAULT_JSON_OUT = Path(__file__).with_name("analyze_esco_schema_report.json")
DEFAULT_MD_OUT = Path(__file__).with_name("analyze_esco_schema_report.md")
SAMPLE_LIMIT = 3


def configure_csv_field_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


@dataclass
class ColumnProfile:
    name: str
    non_empty_count: int
    non_empty_ratio: float
    sample_values: list[str]
    description: str | None


@dataclass
class FileProfile:
    file_name: str
    row_count: int
    column_count: int
    table_role: str
    description: str
    primary_key_candidates: list[str]
    uri_columns: list[str]
    label_columns: list[str]
    columns: list[ColumnProfile]


def read_dictionary(data_dir: Path) -> dict[str, dict[str, str]]:
    dictionary_path = data_dir / "dictionary_en.csv"
    if not dictionary_path.exists():
        return {}

    mapping: dict[str, dict[str, str]] = defaultdict(dict)
    with dictionary_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            file_key = (row.get("filename") or "").strip()
            header = (row.get("data header") or "").strip()
            description = (row.get("description") or "").strip()
            if file_key and header and description:
                mapping[file_key][header] = description
    return dict(mapping)


def iter_csv_files(data_dir: Path) -> Iterable[Path]:
    return sorted(path for path in data_dir.glob("*.csv") if path.is_file())


def infer_table_role(file_name: str) -> tuple[str, str]:
    lower = file_name.lower()
    if file_name == "dictionary_en.csv":
        return "data_dictionary", "Field-level glossary for the ESCO CSV export."
    if "relations" in lower:
        return "relation", "Edge table connecting concepts to broader concepts or related concepts."
    if "hierarchy" in lower:
        return "hierarchy", "Precomputed hierarchy view for navigating multi-level skill groups."
    if "collection" in lower or "shareocc" in lower:
        return "collection", "Thematic subset of ESCO concepts for a domain-specific use case."
    if "scheme" in lower:
        return "scheme", "Concept scheme metadata and top-level concept membership."
    if "groups" in lower:
        return "taxonomy_group", "Taxonomy grouping table used as parent categories or classification levels."
    if file_name in {"occupations_en.csv", "skills_en.csv"}:
        return "core_concept", "Primary concept table containing normalized occupation or skill records."
    return "reference", "Reference-style ESCO table."


def base_dictionary_key(file_name: str) -> str:
    return file_name.replace("_en.csv", "").replace(".csv", "")


def analyze_csv(csv_path: Path, dictionary_map: dict[str, dict[str, str]]) -> FileProfile:
    file_name = csv_path.name
    dictionary_key = base_dictionary_key(file_name)
    field_descriptions = dictionary_map.get(dictionary_key, {})
    table_role, role_description = infer_table_role(file_name)

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        non_empty_counts = {field: 0 for field in fieldnames}
        samples = {field: [] for field in fieldnames}
        seen = {field: set() for field in fieldnames}
        row_count = 0

        for row in reader:
            row_count += 1
            for field in fieldnames:
                value = (row.get(field) or "").strip()
                if not value:
                    continue
                non_empty_counts[field] += 1
                if len(samples[field]) < SAMPLE_LIMIT and value not in seen[field]:
                    compact_value = " ".join(value.split())
                    samples[field].append(compact_value[:160])
                    seen[field].add(value)

    column_profiles = [
        ColumnProfile(
            name=field,
            non_empty_count=non_empty_counts[field],
            non_empty_ratio=round((non_empty_counts[field] / row_count), 3) if row_count else 0.0,
            sample_values=samples[field],
            description=field_descriptions.get(field),
        )
        for field in fieldnames
    ]

    primary_key_candidates = [
        field for field in fieldnames if field.lower() in {"concepturi", "occupationuri", "skilluri", "conceptschemeuri"}
    ]
    uri_columns = [field for field in fieldnames if "uri" in field.lower()]
    label_columns = [field for field in fieldnames if "label" in field.lower() or field.lower().endswith("name")]

    return FileProfile(
        file_name=file_name,
        row_count=row_count,
        column_count=len(fieldnames),
        table_role=table_role,
        description=role_description,
        primary_key_candidates=primary_key_candidates,
        uri_columns=uri_columns,
        label_columns=label_columns,
        columns=column_profiles,
    )


def build_relationship_hints() -> list[dict[str, str]]:
    return [
        {
            "from": "occupations_en.conceptUri",
            "to": "occupationSkillRelations_en.occupationUri",
            "meaning": "Occupation concept joins to occupation-skill relation edges.",
        },
        {
            "from": "skills_en.conceptUri",
            "to": "occupationSkillRelations_en.skillUri",
            "meaning": "Skill concept joins to occupation-skill relation edges.",
        },
        {
            "from": "skills_en.conceptUri",
            "to": "skillSkillRelations_en.originalSkillUri / relatedSkillUri",
            "meaning": "Skill-to-skill graph edges for related, optional, or knowledge links.",
        },
        {
            "from": "occupations_en.iscoGroup",
            "to": "ISCOGroups_en.code",
            "meaning": "Occupation rows reference an ISCO classification code.",
        },
        {
            "from": "broaderRelationsOccPillar_en.conceptUri",
            "to": "broaderRelationsOccPillar_en.broaderUri",
            "meaning": "Occupation-side broader/narrower hierarchy edges.",
        },
        {
            "from": "broaderRelationsSkillPillar_en.conceptUri",
            "to": "broaderRelationsSkillPillar_en.broaderUri",
            "meaning": "Skill-side broader/narrower hierarchy edges.",
        },
        {
            "from": "skillsHierarchy_en.Level N URI",
            "to": "skills_en.conceptUri / skillGroups_en.conceptUri",
            "meaning": "Readable multi-level hierarchy projection for skills and skill groups.",
        },
    ]


def build_payload(data_dir: Path, file_profiles: list[FileProfile]) -> dict[str, Any]:
    by_role: dict[str, list[str]] = defaultdict(list)
    for profile in file_profiles:
        by_role[profile.table_role].append(profile.file_name)

    return {
        "data_dir": str(data_dir),
        "summary": {
            "total_csv_files": len(file_profiles),
            "core_concept_files": by_role.get("core_concept", []),
            "relation_files": by_role.get("relation", []),
            "hierarchy_files": by_role.get("hierarchy", []),
            "collection_files": by_role.get("collection", []),
            "taxonomy_group_files": by_role.get("taxonomy_group", []),
            "scheme_files": by_role.get("scheme", []),
            "data_dictionary_files": by_role.get("data_dictionary", []),
        },
        "recommended_logical_schema": {
            "concept_master": ["occupations_en.csv", "skills_en.csv", "ISCOGroups_en.csv", "skillGroups_en.csv"],
            "relation_edges": [
                "occupationSkillRelations_en.csv",
                "skillSkillRelations_en.csv",
                "broaderRelationsOccPillar_en.csv",
                "broaderRelationsSkillPillar_en.csv",
            ],
            "hierarchy_views": ["skillsHierarchy_en.csv"],
            "theme_collections": [
                "digCompSkillsCollection_en.csv",
                "digitalSkillsCollection_en.csv",
                "greenSkillsCollection_en.csv",
                "languageSkillsCollection_en.csv",
                "researchOccupationsCollection_en.csv",
                "researchSkillsCollection_en.csv",
                "transversalSkillsCollection_en.csv",
            ],
        },
        "relationship_hints": build_relationship_hints(),
        "files": [
            {
                **asdict(profile),
                "columns": [asdict(column) for column in profile.columns],
            }
            for profile in file_profiles
        ],
    }


def print_report(payload: dict[str, Any]) -> None:
    summary: dict[str, Any] = payload["summary"]
    print("=== ESCO CSV Schema Overview ===")
    print(f"data_dir: {payload['data_dir']}")
    print(f"total_csv_files: {summary['total_csv_files']}")
    print()

    for role_key in [
        "core_concept_files",
        "taxonomy_group_files",
        "relation_files",
        "hierarchy_files",
        "collection_files",
        "scheme_files",
        "data_dictionary_files",
    ]:
        print(f"{role_key}: {', '.join(summary[role_key]) if summary[role_key] else '-'}")

    print("\n=== File Details ===")
    for profile in payload["files"]:
        print(
            f"- {profile['file_name']} | role={profile['table_role']} | rows={profile['row_count']} | columns={profile['column_count']}"
        )
        print(f"  description: {profile['description']}")
        print(f"  primary_key_candidates: {profile['primary_key_candidates']}")
        for column in profile["columns"][:6]:
            print(
                f"    - {column['name']} | fill={column['non_empty_ratio']:.1%} | "
                f"samples={column['sample_values'][:2]}"
            )
        if len(profile["columns"]) > 6:
            print("    - ...")

    print("\n=== Relationship Hints ===")
    for rel in payload["relationship_hints"]:
        print(f"- {rel['from']} -> {rel['to']} | {rel['meaning']}")


def build_markdown_report(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    summary: dict[str, Any] = payload["summary"]

    lines.append("# ESCO Schema Analysis")
    lines.append("")
    lines.append(f"- data_dir: {payload['data_dir']}")
    lines.append(f"- total_csv_files: {summary['total_csv_files']}")
    lines.append("")
    lines.append("## Logical groups")
    for role_key, label in [
        ("core_concept_files", "Core concepts"),
        ("taxonomy_group_files", "Taxonomy groups"),
        ("relation_files", "Relation edges"),
        ("hierarchy_files", "Hierarchy views"),
        ("collection_files", "Theme collections"),
        ("scheme_files", "Concept schemes"),
        ("data_dictionary_files", "Data dictionary"),
    ]:
        values = summary.get(role_key, [])
        lines.append(f"- {label}: {', '.join(values) if values else '-'}")

    lines.append("")
    lines.append("## Recommended logical schema")
    for group, files in payload["recommended_logical_schema"].items():
        lines.append(f"### {group}")
        for file_name in files:
            lines.append(f"- {file_name}")

    lines.append("")
    lines.append("## Relationship hints")
    for rel in payload["relationship_hints"]:
        lines.append(f"- {rel['from']} -> {rel['to']}: {rel['meaning']}")

    lines.append("")
    lines.append("## File schema details")
    for profile in payload["files"]:
        lines.append("")
        lines.append(f"### {profile['file_name']}")
        lines.append(f"- role: {profile['table_role']}")
        lines.append(f"- rows: {profile['row_count']}")
        lines.append(f"- columns: {profile['column_count']}")
        lines.append(f"- description: {profile['description']}")
        if profile["primary_key_candidates"]:
            lines.append(f"- primary_key_candidates: {', '.join(profile['primary_key_candidates'])}")
        if profile["uri_columns"]:
            lines.append(f"- uri_columns: {', '.join(profile['uri_columns'])}")
        if profile["label_columns"]:
            lines.append(f"- label_columns: {', '.join(profile['label_columns'])}")
        lines.append("")
        lines.append("| column | fill_ratio | sample_values | description |")
        lines.append("|---|---:|---|---|")
        for column in profile["columns"]:
            sample_text = " / ".join(column["sample_values"]) if column["sample_values"] else ""
            description = (column["description"] or "").replace("\n", " ")
            lines.append(
                f"| {column['name']} | {column['non_empty_ratio']:.1%} | {sample_text} | {description} |"
            )

    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze the ESCO CSV export and produce a readable schema report.")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Path to the ESCO directory.")
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT), help="Path to write the JSON report.")
    parser.add_argument("--md-out", default=str(DEFAULT_MD_OUT), help="Path to write the Markdown report.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"ESCO directory not found: {data_dir}")

    configure_csv_field_limit()

    dictionary_map = read_dictionary(data_dir)
    file_profiles = [analyze_csv(csv_path, dictionary_map) for csv_path in iter_csv_files(data_dir)]
    payload = build_payload(data_dir, file_profiles)

    print_report(payload)

    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    md_out = Path(args.md_out)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text(build_markdown_report(payload), encoding="utf-8")

    print(f"\nJSON report written to: {json_out}")
    print(f"Markdown report written to: {md_out}")


if __name__ == "__main__":
    main()
