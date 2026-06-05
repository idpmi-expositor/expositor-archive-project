"""Segment detected document structures into lesson-level records.

This script is the final step in the structuring layer.

Pipeline position:
    PDF -> RAW TEXT -> STRUCTURED DOCUMENT MODEL -> CANONICAL YAML
                                      ^
                                      This script creates lesson segments.

What lesson segmentation means:
    A source publication may contain many lessons. The canonical archive stores
    one YAML file per lesson, so the system needs an intermediate lesson record
    before canonical YAML can be generated.

Important rule:
    Lesson boundaries must come from explicit source markers such as "LECCION 1"
    or from source Contenido entries. The script must not guess boundaries from
    topic changes or paragraph meaning.

Beginner note:
    This script reads the JSON marker reports created by
    ``04_document_structure_detector.py`` and records auditable validation
    warnings before canonical YAML is generated.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STRUCTURE_DIR = PROJECT_ROOT / "structured" / "document_structure"
DEFAULT_SEGMENT_DIR = PROJECT_ROOT / "metadata" / "lessons"

LESSON_NUMBER_PATTERN = re.compile(r"LECCI[OÓ]N\s+(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class LessonSegment:
    """A deterministic intermediate record for one lesson boundary.

    This is not canonical YAML. It is the bridge between structure detection
    and future one-lesson-per-file serialization.
    """

    lesson_number: int
    start_line: int
    marker: str
    expected_title: str | None = None
    expected_page_start: int | None = None
    lesson_date: str | None = None


def load_structure(path: Path) -> dict[str, Any]:
    """Read one DocumentStructure JSON file."""

    return json.loads(path.read_text(encoding="utf-8"))


def extract_lesson_segments(structure: dict[str, Any]) -> list[LessonSegment]:
    """Create one lesson segment for each Contenido entry or lesson header.

    The preferred source is the ``content_index`` extracted from the publication
    table of contents. If no content index is available, the function falls
    back to explicit lesson header markers.
    """

    content_entries = structure.get("content_index", [])
    if content_entries:
        # The source table of contents is preferred because it carries the
        # expected title, date, and page start in addition to lesson number.
        return [
            LessonSegment(
                lesson_number=int(entry["lesson_number"]),
                start_line=0,
                marker="Contenido",
                expected_title=entry["title"],
                expected_page_start=int(entry["page_start"]),
                lesson_date=entry.get("lesson_date"),
            )
            for entry in content_entries
        ]

    segments: list[LessonSegment] = []
    for marker in structure.get("markers", []):
        if marker.get("marker_type") != "lesson_header":
            continue

        match = LESSON_NUMBER_PATTERN.search(marker.get("text", ""))
        if not match:
            continue

        segments.append(
            LessonSegment(
                lesson_number=int(match.group(1)),
                start_line=int(marker["line_number"]),
                marker=marker["text"],
            )
        )

    return segments


def observed_lesson_headers(structure: dict[str, Any]) -> dict[str, list[int]]:
    """Group observed lesson header line numbers by lesson number."""

    observed: dict[str, list[int]] = {}
    for marker in structure.get("markers", []):
        if marker.get("marker_type") != "lesson_header":
            continue

        match = LESSON_NUMBER_PATTERN.search(marker.get("text", ""))
        if not match:
            continue

        lesson_number = match.group(1)
        observed.setdefault(lesson_number, []).append(int(marker["line_number"]))

    return observed


def duplicate_numbers(numbers: list[str]) -> list[str]:
    """Return duplicate lesson numbers in deterministic numeric order."""

    counts = Counter(numbers)
    return sorted(
        [number for number, count in counts.items() if count > 1],
        key=int,
    )


def content_index_lesson_numbers(structure: dict[str, Any]) -> list[str]:
    """Return lesson numbers from content_index entries as strings."""

    numbers: list[str] = []
    for entry in structure.get("content_index", []):
        lesson_number = entry.get("lesson_number")
        if lesson_number is not None:
            numbers.append(str(lesson_number))
    return numbers


def segment_lesson_numbers(segments: list[LessonSegment]) -> list[str]:
    """Return lesson numbers from generated segments as strings."""

    return [str(segment.lesson_number) for segment in segments]


def build_validation_messages(
    structure: dict[str, Any],
    segments: list[LessonSegment],
    expected_numbers: set[str],
    observed_numbers: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Create explicit validation warnings and errors for human review."""

    warnings: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    content_entries = structure.get("content_index", [])
    detection = structure.get("content_index_detection", {})
    observed = observed_lesson_headers(structure)

    missing_observed = sorted(expected_numbers - observed_numbers, key=int)
    unexpected_observed = sorted(observed_numbers - expected_numbers, key=int)

    if not content_entries:
        warnings.append(
            {
                "code": "CONTENT_INDEX_MISSING",
                "message": "No Contenido entries were available; segmentation uses explicit lesson headers only.",
                "content_index_detection": detection,
            }
        )

    if missing_observed:
        warnings.append(
            {
                "code": "LESSON_HEADERS_MISSING_FOR_CONTENT_INDEX",
                "message": "Contenido lesson numbers were not all observed as lesson headers.",
                "lesson_numbers": missing_observed,
            }
        )

    if unexpected_observed:
        warnings.append(
            {
                "code": "UNEXPECTED_LESSON_HEADERS",
                "message": "Observed lesson headers that were not present in the Contenido expectations.",
                "lesson_numbers": unexpected_observed,
                "observed_header_line_numbers": {
                    number: observed[number]
                    for number in unexpected_observed
                    if number in observed
                },
            }
        )

    duplicate_content_numbers = duplicate_numbers(content_index_lesson_numbers(structure))
    if duplicate_content_numbers:
        errors.append(
            {
                "code": "DUPLICATE_CONTENT_INDEX_LESSON_NUMBERS",
                "message": "The Contenido table contains duplicate lesson numbers.",
                "lesson_numbers": duplicate_content_numbers,
            }
        )

    duplicate_segment_numbers = duplicate_numbers(segment_lesson_numbers(segments))
    if duplicate_segment_numbers:
        errors.append(
            {
                "code": "DUPLICATE_SEGMENT_LESSON_NUMBERS",
                "message": "Generated lesson segments contain duplicate lesson numbers.",
                "lesson_numbers": duplicate_segment_numbers,
            }
        )

    duplicate_observed_numbers = duplicate_numbers(
        [number for number, line_numbers in observed.items() for _ in line_numbers]
    )
    if duplicate_observed_numbers:
        warnings.append(
            {
                "code": "DUPLICATE_OBSERVED_LESSON_HEADERS",
                "message": "The same lesson number was observed in multiple lesson header markers.",
                "lesson_numbers": duplicate_observed_numbers,
                "observed_header_line_numbers": {
                    number: observed[number]
                    for number in duplicate_observed_numbers
                    if number in observed
                },
            }
        )

    if not segments:
        errors.append(
            {
                "code": "NO_LESSON_SEGMENTS_CREATED",
                "message": "No lesson segments were created from Contenido entries or lesson headers.",
            }
        )

    return warnings, errors


def validation_status(
    warnings: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> str:
    """Return pass, warning, or error for the segmentation artifact."""

    if errors:
        return "error"
    if warnings:
        return "warning"
    return "pass"


def build_segmentation_validation(
    structure: dict[str, Any],
    segments: list[LessonSegment],
) -> dict[str, Any]:
    """Summarize Contenido expectations, observed headers, and validation state.

    The summary is a review aid. It does not silently repair mismatches because
    correction should remain explicit and auditable.
    """

    observed = observed_lesson_headers(structure)
    expected_numbers = {str(segment.lesson_number) for segment in segments}
    observed_numbers = set(observed)
    warnings, errors = build_validation_messages(
        structure,
        segments,
        expected_numbers,
        observed_numbers,
    )

    return {
        "validation_status": validation_status(warnings, errors),
        "validation_warnings": warnings,
        "validation_errors": errors,
        "content_index_entries": len(structure.get("content_index", [])),
        "content_index_detection": structure.get("content_index_detection", {}),
        "expected_lesson_numbers": sorted(expected_numbers, key=int),
        "observed_lesson_numbers": sorted(observed_numbers, key=int),
        "missing_observed_headers": sorted(expected_numbers - observed_numbers, key=int),
        "unexpected_observed_headers": sorted(observed_numbers - expected_numbers, key=int),
        "observed_header_line_numbers": observed,
    }


def relative_output_path(input_path: Path, input_dir: Path, output_dir: Path) -> Path:
    """Preserve structure subfolders when writing lesson segment metadata."""

    return output_dir / input_path.relative_to(input_dir)


def safe_relative_to_project(path: Path) -> str:
    """Return a readable relative path when the file is inside the repository."""

    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def write_segment_file(input_path: Path, output_path: Path) -> dict[str, Any]:
    """Write lesson segmentation metadata for one structure file."""

    structure = load_structure(input_path)
    segments = extract_lesson_segments(structure)
    validation_summary = build_segmentation_validation(structure, segments)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "source_structure": safe_relative_to_project(input_path),
                "segments": [asdict(segment) for segment in segments],
                "validation_summary": validation_summary,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return validation_summary


def main() -> int:
    """Command-line entry point for lesson segmentation."""

    parser = argparse.ArgumentParser(
        description="Segment DocumentStructure files into lesson records."
    )
    parser.add_argument(
        "--input-dir",
        default=DEFAULT_STRUCTURE_DIR,
        type=Path,
        help="Folder containing DocumentStructure JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_SEGMENT_DIR,
        type=Path,
        help="Folder where lesson segment metadata will be written.",
    )
    args = parser.parse_args()

    structure_files = sorted(args.input_dir.rglob("*.json")) if args.input_dir.exists() else []
    if not structure_files:
        print(f"No DocumentStructure JSON files found under {args.input_dir}")
        return 0

    exit_code = 0
    for structure_file in structure_files:
        output_file = relative_output_path(structure_file, args.input_dir, args.output_dir)
        validation_summary = write_segment_file(structure_file, output_file)
        status = validation_summary["validation_status"]
        print(f"Segmented lessons {structure_file} -> {output_file} [{status}]")
        if status == "error":
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
