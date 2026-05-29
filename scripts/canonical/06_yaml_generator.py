"""Generate canonical lesson YAML from structured lesson metadata.

This is the first script in the canonical output layer.

Pipeline position:
    PDF -> RAW TEXT -> STRUCTURED DOCUMENT MODEL -> CANONICAL YAML
                                                          ^
                                                          This script writes YAML.

What this script will eventually do:
    1. Read lesson segment metadata from the structuring layer.
    2. Convert each lesson into the canonical YAML shape.
    3. Store one YAML file per lesson under ``archive/lessons``.
    4. Preserve biblical readings as references only, never as Bible text.

Why this matters:
    The archive's permanent unit is one lesson YAML file. Downstream systems can
    translate, render, or replace Bible text later, but this repository keeps the
    archival structure stable and source-traceable.

Beginner note:
    YAML is a human-readable data format. It works well for this project because
    it can be reviewed in Git, edited carefully by humans, and validated by
    scripts.
"""

from __future__ import annotations

import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEGMENT_DIR = PROJECT_ROOT / "metadata" / "lessons"
DEFAULT_ARCHIVE_DIR = PROJECT_ROOT / "archive" / "lessons"
DEFAULT_SCHEMA_VERSION = "1.0.0"


def lesson_output_path(
    archive_dir: Path,
    year: int,
    cycle: str,
    lesson_number: int,
) -> Path:
    """Build the standard archive path for one lesson YAML file.

    Example:
        archive/lessons/2026/C1/LES-2026-C1-001.yaml
    """

    filename = f"LES-{year}-{cycle}-{lesson_number:03d}.yaml"
    return archive_dir / str(year) / cycle / filename


def main() -> int:
    """Command-line entry point for canonical YAML generation planning."""

    parser = argparse.ArgumentParser(
        description="Generate canonical lesson YAML from structured metadata."
    )
    parser.add_argument(
        "--input-dir",
        default=DEFAULT_SEGMENT_DIR,
        type=Path,
        help="Folder containing lesson segment metadata.",
    )
    parser.add_argument(
        "--archive-dir",
        default=DEFAULT_ARCHIVE_DIR,
        type=Path,
        help="Folder where canonical lesson YAML files will be written.",
    )
    parser.add_argument(
        "--schema-version",
        default=DEFAULT_SCHEMA_VERSION,
        help="Schema version to write into generated YAML.",
    )
    args = parser.parse_args()

    segment_files = sorted(args.input_dir.rglob("*.json")) if args.input_dir.exists() else []
    if not segment_files:
        print(f"No lesson segment metadata found under {args.input_dir}")
        return 0

    print("Canonical YAML generation is intentionally pending.")
    print(f"Schema version configured for future output: {args.schema_version}")
    print(f"Archive output folder: {args.archive_dir}")
    print(f"Segment metadata files found: {len(segment_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
