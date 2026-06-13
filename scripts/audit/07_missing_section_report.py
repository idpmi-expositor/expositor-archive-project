"""Generate a report of lessons with missing extracted sections.

This script helps reviewers identify which lessons need attention before
canonical promotion. It reads the automated section extraction metadata and
flags any lesson that is missing a required section.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "metadata" / "lesson_sections"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "missing_sections"

REQUIRED_SECTIONS = (
    "biblical_reading",
    "lesson_outline",
    "teacher_notes",
    "summary_application",
)

# Missing sections that should cause a non-zero (failure) exit code.
CRITICAL_SECTIONS = (
    "biblical_reading",
    "lesson_outline",
    "teacher_notes",
)


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON file."""
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def resolve_project_path(value: str) -> Path:
    """Resolve a repository-relative path stored in generated JSON."""
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def get_lesson_page_range(
    lesson_number: int,
    section_file_path: Path,
) -> tuple[int | None, int | None]:
    """Trace back to the lesson segment to find the page range."""
    section_metadata = load_json(section_file_path)
    segment_file_path = resolve_project_path(str(section_metadata.get("source_segments") or ""))
    if not segment_file_path.exists():
        return None, None

    segment_metadata = load_json(segment_file_path)
    for segment in segment_metadata.get("segments", []):
        if int(segment.get("lesson_number") or 0) == lesson_number:
            return segment.get("page_start"), segment.get("page_end")

    return None, None


def find_missing_sections(section_file_path: Path) -> list[dict[str, Any]]:
    """Check one publication's section metadata for missing content."""
    metadata = load_json(section_file_path)
    missing_items: list[dict[str, Any]] = []
    publication_id = Path(str(metadata.get("source_text") or "")).stem

    for lesson in metadata.get("lessons", []):
        lesson_number = int(lesson.get("lesson_number") or 0)
        present_sections = set(lesson.get("sections", {}).keys())
        missing_sections = sorted(list(set(REQUIRED_SECTIONS) - present_sections))

        if missing_sections:
            page_start, page_end = get_lesson_page_range(lesson_number, section_file_path)
            for section_name in missing_sections:
                missing_items.append(
                    {
                        "publication_id": publication_id,
                        "lesson_number": lesson_number,
                        "missing_section": section_name,
                        "source_page_start": page_start,
                        "source_page_end": page_end,
                        "reviewer_action": "Inspect normalized text to find the section label or content.",
                    }
                )

    return missing_items


def write_markdown_report(report_data: dict[str, Any], output_path: Path) -> None:
    """Write a human-readable Markdown version of the report."""
    lines: list[str] = [
        "# Missing Section Report",
        "",
        f"Total missing section items: {report_data['total_missing']}",
        "",
    ]
    if not report_data["missing_items"]:
        lines.append("No missing sections found.")
    else:
        lines.append("| Publication | Lesson | Missing Section | Page Range |")
        lines.append("| --- | ---: | --- | ---: |")
        for item in report_data["missing_items"]:
            page_range = (
                f"{item['source_page_start']}-{item['source_page_end']}"
                if item["source_page_start"] and item["source_page_end"]
                else "N/A"
            )
            lines.append(
                f"| {item['publication_id']} | {item['lesson_number']} | "
                f"`{item['missing_section']}` | {page_range} |"
            )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    """Command-line entry point for the missing section report generator."""
    parser = argparse.ArgumentParser(description="Generate a report on missing lesson sections.")
    parser.add_argument(
        "--input-dir",
        default=DEFAULT_INPUT_DIR,
        type=Path,
        help="Directory containing lesson section metadata JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        type=Path,
        help="Directory where the report will be written.",
    )
    args = parser.parse_args()

    section_files = sorted(args.input_dir.rglob("*.json")) if args.input_dir.exists() else []
    if not section_files:
        print(f"No lesson section metadata found under {args.input_dir}")
        return 0

    all_missing_items: list[dict[str, Any]] = []
    for section_file in section_files:
        all_missing_items.extend(find_missing_sections(section_file))

    report_data = {
        "total_missing": len(all_missing_items),
        "missing_items": sorted(
            all_missing_items,
            key=lambda x: (x["publication_id"], x["lesson_number"], x["missing_section"]),
        ),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_output_path = args.output_dir / "missing_sections.json"
    json_output_path.write_text(
        json.dumps(report_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote JSON report to {json_output_path}")

    md_output_path = args.output_dir / "missing_sections.md"
    write_markdown_report(report_data, md_output_path)
    print(f"Wrote Markdown report to {md_output_path}")

    has_critical_missing = any(
        item["missing_section"] in CRITICAL_SECTIONS
        for item in report_data["missing_items"]
    )
    return 1 if has_critical_missing else 0


if __name__ == "__main__":
    raise SystemExit(main())