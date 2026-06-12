"""Generate draft lesson YAML from structured lesson metadata.

This is the first script in the canonical output layer.

Pipeline position:
    PDF -> RAW TEXT -> STRUCTURED DOCUMENT MODEL -> CANONICAL YAML
                                                          ^
                                                          This script writes draft YAML.

What this script will eventually do:
    1. Read lesson segment metadata from the structuring layer.
    2. Convert each lesson into the canonical YAML shape.
    3. Store one draft YAML file per lesson under ``archive/drafts``.
    4. Preserve biblical readings as references only, never as Bible text.

Why this matters:
    The archive's permanent unit is one reviewed lesson YAML file. Generated
    draft YAML is intentionally separated from canonical lesson YAML so
    scaffolding cannot be indexed as archival truth.

Beginner note:
    YAML is a human-readable data format. It works well for this project because
    it can be reviewed in Git, edited carefully by humans, and validated by
    scripts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "PyYAML is required to generate canonical lesson YAML files. "
        "Install it with: python -m pip install pyyaml"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEGMENT_DIR = PROJECT_ROOT / "metadata" / "lessons"
DEFAULT_DRAFT_DIR = PROJECT_ROOT / "archive" / "drafts"
DEFAULT_SCHEMA_VERSION = "1.0.0"
DEFAULT_COLLECTION_TYPE = "Expositor Maestro"
DEFAULT_CYCLE = "C1"
DEFAULT_LANGUAGE = "es"
DEFAULT_IMPORTED_AT = "1970-01-01T00:00:00+00:00"


def lesson_output_path(
    draft_dir: Path,
    publication_id: str,
    year: int,
    cycle: str,
    lesson_number: int,
) -> Path:
    """Build the standard draft path for one lesson YAML file.

    Example:
        archive/drafts/expositor-guia-maestro-volumen-45/2026/C1/LES-2026-C1-001.yaml
    """

    filename = f"LES-{year}-{cycle}-{lesson_number:03d}.yaml"
    return draft_dir / publication_id / str(year) / cycle / filename


def load_json(path: Path) -> dict[str, Any]:
    """Read one segmentation JSON file."""

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root document must be a JSON object")
    return data


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    """Write a generated lesson YAML file with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        yaml.safe_dump(
            data,
            handle,
            allow_unicode=True,
            sort_keys=False,
            explicit_start=True,
        )


def imported_at_from_epoch(epoch_text: str) -> str:
    """Convert SOURCE_DATE_EPOCH-style seconds into an ISO timestamp."""

    return datetime.fromtimestamp(int(epoch_text), UTC).replace(microsecond=0).isoformat()


def existing_imported_at(path: Path) -> str | None:
    """Preserve existing generated audit timestamps to avoid no-op churn."""

    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as handle:
        existing = yaml.safe_load(handle) or {}
    if not isinstance(existing, dict):
        return None

    source_integrity = existing.get("source_integrity")
    if isinstance(source_integrity, dict):
        imported_at = source_integrity.get("imported_at")
        if isinstance(imported_at, str) and imported_at:
            return imported_at

    processing_audit = existing.get("processing_audit")
    if isinstance(processing_audit, dict):
        intake_date = processing_audit.get("intake_date")
        if isinstance(intake_date, str) and intake_date:
            return intake_date

    return None


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for a source file, or a pending marker."""

    if not path.exists():
        return "pending-source-file-verification"

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def infer_year(segments: list[dict[str, Any]]) -> int:
    """Infer publication year from the first lesson date in the segment file."""

    for segment in segments:
        lesson_date = str(segment.get("lesson_date", ""))
        if lesson_date.endswith("/24"):
            return 2024
    return datetime.now(UTC).year


def source_pdf_from_segment_file(segment_file: Path) -> Path:
    """Infer the original PDF path from a lesson metadata filename."""

    return PROJECT_ROOT / "source_assets" / "original_pdfs" / f"{segment_file.stem}.pdf"


def page_end_for(index: int, segments: list[dict[str, Any]]) -> int:
    """Use the next lesson's start page as the best available page boundary."""

    current_start = int(segments[index].get("expected_page_start") or 0)
    if index + 1 >= len(segments):
        return current_start

    next_start = int(segments[index + 1].get("expected_page_start") or current_start)
    return max(current_start, next_start - 1)


def build_minimal_lesson(
    *,
    segment: dict[str, Any],
    segment_file: Path,
    source_structure: str,
    segment_index: int,
    segments: list[dict[str, Any]],
    schema_version: str,
    imported_at: str,
) -> dict[str, Any]:
    """Create the smallest schema-valid lesson record from segment metadata."""

    lesson_number = int(segment["lesson_number"])
    year = infer_year(segments)
    cycle = DEFAULT_CYCLE
    source_pdf = source_pdf_from_segment_file(segment_file)
    publication_id = segment_file.stem
    lesson_id = f"LES-{year}-{cycle}-{lesson_number:03d}"
    page_start = int(segment.get("page_start") or segment.get("expected_page_start") or 0)
    page_end = int(segment.get("page_end") or page_end_for(segment_index, segments))
    title = str(segment.get("expected_title") or f"Lesson {lesson_number}")
    lesson_date = str(segment.get("lesson_date") or "TBD")

    return {
        "schema_version": schema_version,
        "lesson_id": lesson_id,
        "publication_id": publication_id,
        "collection_type": DEFAULT_COLLECTION_TYPE,
        "year": year,
        "cycle": cycle,
        "lesson_number": lesson_number,
        "title": title,
        "language": DEFAULT_LANGUAGE,
        "page_range": {
            "start": page_start,
            "end": page_end,
        },
        "lesson_sections": {
            "lesson_header": {
                "marker": str(segment.get("marker") or "Contenido"),
                "lesson_number": lesson_number,
                "lesson_date": lesson_date,
            },
            "title": {
                "text": title,
            },
            "biblical_reading": {
                "reference_display": "TBD",
                "canonical_references": [
                    {
                        "testament": "TBD",
                        "book_standardized": "TBD",
                        "chapter": 0,
                        "verse_start": 0,
                        "verse_end": 0,
                    }
                ],
                "replacement_policy": {
                    "provider": "api.bible",
                    "strategy": "replace_by_canonical_reference",
                    "source_text_included": False,
                },
            },
            "lesson_outline": {
                "items": ["TBD"],
            },
            "teacher_notes": {
                "items": ["TBD"],
            },
            "summary_application": {
                "items": ["TBD"],
            },
        },
        "processing_audit": {
            "intake_date": imported_at,
            "ocr_engine": "PyMuPDF",
            "ocr_engine_version": "pending-version-capture",
            "extraction_method": "pdf_text_extraction",
            "extraction_confidence": "minimal-valid-placeholder",
            "manual_review_required": True,
            "reviewed_by": "pending-human-review",
            "review_status": "pending",
        },
        "source_integrity": {
            "original_filename": source_pdf.name,
            "sha256": sha256_file(source_pdf),
            "imported_at": imported_at,
            "source_scan_quality": "pending-human-review",
        },
        "processing_status": {
            "intake_completed": True,
            "ocr_completed": True,
            "metadata_extracted": True,
            "semantic_indexed": False,
            "human_review_completed": False,
            "yaml_generated": True,
            "validated": False,
        },
        "source_trace": {
            "source_pdf": source_pdf.relative_to(PROJECT_ROOT).as_posix(),
            "page_start": page_start,
            "page_end": page_end,
            "line_start": int(segment.get("start_line") or 0),
            "line_end": int(segment.get("end_line") or 0),
            "extraction_block": source_structure or segment_file.relative_to(PROJECT_ROOT).as_posix(),
        },
        "semantic_metadata": {
            "doctrinal_categories": ["TBD"],
            "theological_themes": ["TBD"],
            "educational_level": "adult",
            "intended_audience": DEFAULT_COLLECTION_TYPE,
        },
    }


def main() -> int:
    """Command-line entry point for minimal draft YAML generation."""

    parser = argparse.ArgumentParser(
        description="Generate draft lesson YAML from structured metadata."
    )
    parser.add_argument(
        "--input-dir",
        default=DEFAULT_SEGMENT_DIR,
        type=Path,
        help="Folder containing lesson segment metadata.",
    )
    parser.add_argument(
        "--draft-dir",
        default=DEFAULT_DRAFT_DIR,
        type=Path,
        help="Folder where draft lesson YAML files will be written.",
    )
    parser.add_argument(
        "--schema-version",
        default=DEFAULT_SCHEMA_VERSION,
        help="Schema version to write into generated YAML.",
    )
    parser.add_argument(
        "--imported-at",
        help=(
            "ISO timestamp for newly generated draft audit fields. Existing "
            "draft files keep their prior imported_at value unless this is set. "
            "When omitted for a new file, SOURCE_DATE_EPOCH is honored, then a "
            "stable placeholder timestamp is used."
        ),
    )
    args = parser.parse_args()

    segment_files = sorted(args.input_dir.rglob("*.json")) if args.input_dir.exists() else []
    if not segment_files:
        print(f"No lesson segment metadata found under {args.input_dir}")
        return 0

    # This generator writes minimal schema-shaped draft YAML from segment
    # metadata. Placeholder values are explicit so reviewers can distinguish
    # generated scaffolding from human-reviewed canonical truth.
    default_imported_at = (
        args.imported_at
        or (
            imported_at_from_epoch(os.environ["SOURCE_DATE_EPOCH"])
            if "SOURCE_DATE_EPOCH" in os.environ
            else DEFAULT_IMPORTED_AT
        )
    )
    written_files: list[Path] = []
    output_paths_seen: set[Path] = set()

    for segment_file in segment_files:
        metadata = load_json(segment_file)
        segments = metadata.get("segments", [])
        if not isinstance(segments, list):
            raise ValueError(f"{segment_file}: segments must be a list")
        source_structure = str(metadata.get("source_structure") or "")

        for index, segment in enumerate(segments):
            if not isinstance(segment, dict):
                raise ValueError(f"{segment_file}: segment {index} must be an object")

            lesson_number = int(segment["lesson_number"])
            year = infer_year(segments)
            output_path = lesson_output_path(
                args.draft_dir,
                segment_file.stem,
                year,
                DEFAULT_CYCLE,
                lesson_number,
            )
            if output_path in output_paths_seen:
                raise ValueError(f"Duplicate draft output path generated: {output_path}")
            output_paths_seen.add(output_path)
            imported_at = (
                args.imported_at
                or existing_imported_at(output_path)
                or default_imported_at
            )
            lesson = build_minimal_lesson(
                segment=segment,
                segment_file=segment_file,
                source_structure=source_structure,
                segment_index=index,
                segments=segments,
                schema_version=args.schema_version,
                imported_at=imported_at,
            )
            write_yaml(output_path, lesson)
            written_files.append(output_path)

    print(f"Generated {len(written_files)} draft lesson YAML file(s).")
    print(f"Draft output folder: {args.draft_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
