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
    Lesson boundaries must come from explicit source markers such as "LECCION 1".
    The script must not guess boundaries from topic changes or paragraph meaning.

Beginner note:
    This script currently reads the JSON marker reports created by
    ``04_document_structure_detector.py`` and shows where lesson records will be
    created. Full text slicing will be added once real normalized source files
    are available.
"""

from __future__ import annotations

import argparse
import json
import re
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


def build_segmentation_validation(
    structure: dict[str, Any],
    segments: list[LessonSegment],
) -> dict[str, Any]:
    """Summarize how Contenido expectations compare with observed headers.

    The summary is a review aid. It does not silently repair mismatches because
    correction should remain explicit and auditable.
    """

    observed = observed_lesson_headers(structure)
    expected_numbers = {str(segment.lesson_number) for segment in segments}
    observed_numbers = set(observed)

    return {
        "content_index_entries": len(structure.get("content_index", [])),
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


def write_segment_file(input_path: Path, output_path: Path) -> None:
    """Write lesson segmentation metadata for one structure file."""

    structure = load_structure(input_path)
    segments = extract_lesson_segments(structure)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "source_structure": safe_relative_to_project(input_path),
                "segments": [asdict(segment) for segment in segments],
                "validation_summary": build_segmentation_validation(
                    structure,
                    segments,
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


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

    for structure_file in structure_files:
        output_file = relative_output_path(structure_file, args.input_dir, args.output_dir)
        write_segment_file(structure_file, output_file)
        print(f"Segmented lessons {structure_file} -> {output_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
