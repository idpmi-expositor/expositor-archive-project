"""Run the staged archive pipeline in order."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_step(command: list[str], *, optional: bool = False) -> int:
    print(f"\n$ {' '.join(command)}")
    result = subprocess.run(command, cwd=PROJECT_ROOT)
    if result.returncode != 0 and not optional:
        return result.returncode
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Expositor archive pipeline.")
    parser.add_argument("--drive-root-folder-id")
    parser.add_argument("--rclone-config", type=Path)
    parser.add_argument("--skip-drive-validation", action="store_true")
    parser.add_argument("--skip-rename", action="store_true")
    parser.add_argument("--skip-raw-extraction", action="store_true")
    parser.add_argument("--no-ocr-fallback", action="store_true")
    parser.add_argument(
        "--build-indexes",
        action="store_true",
        help="Attempt canonical validation and index generation after drafts are built.",
    )
    args = parser.parse_args()

    python = sys.executable
    steps: list[tuple[list[str], bool]] = []

    if not args.skip_drive_validation and args.drive_root_folder_id:
        command = [
            python,
            "scripts/ingestion/00_validate_source_pdf_sync.py",
            "--drive-root-folder-id",
            args.drive_root_folder_id,
        ]
        if args.rclone_config:
            command.extend(["--rclone-config", str(args.rclone_config)])
        steps.append((command, False))

    if not args.skip_rename:
        steps.append(([python, "scripts/ingestion/00_rename_source_pdfs.py"], False))

    steps.append(([python, "scripts/ingestion/01_pdf_discovery.py"], False))

    if not args.skip_raw_extraction:
        command = [python, "scripts/ingestion/02_pdf_to_raw_text.py"]
        if args.no_ocr_fallback:
            command.append("--no-ocr-fallback")
        steps.append((command, False))

    steps.extend(
        [
            ([python, "scripts/ingestion/03_quality_report.py"], False),
            ([python, "scripts/structuring/03_minimal_text_normalizer.py"], False),
            ([python, "scripts/structuring/04_document_structure_detector.py"], False),
            ([python, "scripts/structuring/05_lesson_segmenter.py"], False),
            ([python, "scripts/structuring/06_section_extractor.py"], False),
            ([python, "scripts/canonical/06_yaml_generator.py"], False),
        ]
    )

    if args.build_indexes:
        steps.extend(
            [
                ([python, "scripts/canonical/07_schema_validator.py"], False),
                ([python, "scripts/canonical/08_index_builder.py"], False),
            ]
        )

    for command, optional in steps:
        exit_code = run_step(command, optional=optional)
        if exit_code:
            print(f"Pipeline stopped at: {' '.join(command)}")
            return exit_code

    print("\nPipeline completed. Generated YAML remains draft/unreviewed unless promoted separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
