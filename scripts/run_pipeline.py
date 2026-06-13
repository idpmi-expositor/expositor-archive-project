"""Run the staged archive pipeline in order.

The runner can regenerate automated-unreviewed drafts for architecture work.
It does not promote drafts into `archive/lessons` or complete human review.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_step(command: list[str], *, optional: bool = False) -> dict[str, object]:
    print(f"\n$ {' '.join(command)}")
    started = time.perf_counter()
    result = subprocess.run(command, cwd=PROJECT_ROOT)
    elapsed = round(time.perf_counter() - started, 3)
    step_result = {
        "command": command,
        "returncode": result.returncode,
        "elapsed_seconds": elapsed,
        "optional": optional,
    }
    if result.returncode != 0 and not optional:
        return step_result
    return step_result


def write_run_log(run_log_dir: Path, steps: list[dict[str, object]]) -> Path:
    """Write a beginner-readable JSON timing log for one pipeline run."""

    run_log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = run_log_dir / f"pipeline-run-{timestamp}.json"
    payload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "total_elapsed_seconds": round(
            sum(float(step["elapsed_seconds"]) for step in steps), 3
        ),
        "steps": steps,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Expositor archive pipeline.")
    parser.add_argument("--drive-root-folder-id")
    parser.add_argument("--rclone-config", type=Path)
    parser.add_argument("--skip-drive-validation", action="store_true")
    parser.add_argument("--skip-rename", action="store_true")
    parser.add_argument("--skip-raw-extraction", action="store_true")
    parser.add_argument("--no-ocr-fallback", action="store_true")
    parser.add_argument(
        "--write-run-log",
        action="store_true",
        help="Write a JSON performance log under reports/pipeline_runs.",
    )
    parser.add_argument(
        "--run-log-dir",
        default=PROJECT_ROOT / "reports" / "pipeline_runs",
        type=Path,
        help="Folder for optional performance run logs.",
    )
    parser.add_argument(
        "--build-indexes",
        action="store_true",
        help=(
            "Attempt canonical validation and index generation after drafts are "
            "built. This only succeeds when reviewed files already exist under "
            "archive/lessons."
        ),
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

    step_results: list[dict[str, object]] = []
    for command, optional in steps:
        step_result = run_step(command, optional=optional)
        step_results.append(step_result)
        if int(step_result["returncode"]) != 0 and not optional:
            print(f"Pipeline stopped at: {' '.join(command)}")
            if args.write_run_log:
                log_path = write_run_log(args.run_log_dir, step_results)
                print(f"Pipeline run log written: {log_path}")
            return int(step_result["returncode"])

    if args.write_run_log:
        log_path = write_run_log(args.run_log_dir, step_results)
        print(f"Pipeline run log written: {log_path}")
    print("\nPipeline completed. Generated YAML remains draft/unreviewed unless promoted separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
