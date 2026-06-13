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
DEFAULT_STEPS_CONFIG = PROJECT_ROOT / "config" / "pipeline_steps.json"


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


def load_steps_config(path: Path) -> list[dict[str, Any]]:
    """Load pipeline steps from a JSON configuration file."""
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    steps = data.get("steps")
    if not isinstance(steps, list):
        raise ValueError(f"{path}: 'steps' must be a list")
    return steps


def filter_steps(
    all_steps: list[dict[str, Any]],
    run_tags: set[str],
    skip_tags: set[str],
) -> list[dict[str, Any]]:
    """Filter pipeline steps based on command-line tags."""
    if not run_tags and not skip_tags:
        return all_steps

    filtered_steps: list[dict[str, Any]] = []
    for step in all_steps:
        step_tags = set(step.get("tags", []))
        if skip_tags and step_tags.intersection(skip_tags):
            continue
        if run_tags and not step_tags.intersection(run_tags):
            continue
        filtered_steps.append(step)
    return filtered_steps


def build_command(step: dict[str, Any], python_executable: str, args: argparse.Namespace) -> list[str]:
    """Build the command list for a single pipeline step."""
    command = [python_executable, step["command"]]
    step_name = step["name"]

    if step_name == "validate-drive-sync" and args.drive_root_folder_id:
        command.extend(["--drive-root-folder-id", args.drive_root_folder_id])
        if args.rclone_config:
            command.extend(["--rclone-config", str(args.rclone_config)])

    if step_name == "extract-raw-text" and args.no_ocr_fallback:
        command.append("--no-ocr-fallback")

    return command


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Expositor archive pipeline.")
    parser.add_argument(
        "--steps-config",
        default=DEFAULT_STEPS_CONFIG,
        type=Path,
        help="Path to the JSON file defining pipeline steps.",
    )
    parser.add_argument(
        "--run-tags",
        help="Comma-separated list of tags to run (e.g., 'ingestion,structuring').",
    )
    parser.add_argument(
        "--skip-tags",
        help="Comma-separated list of tags to skip (e.g., 'pre-flight,ocr').",
    )
    # Arguments for specific steps
    parser.add_argument("--drive-root-folder-id")
    parser.add_argument("--rclone-config", type=Path)
    parser.add_argument("--no-ocr-fallback", action="store_true")
    # Run log arguments
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
    args = parser.parse_args()

    all_steps = load_steps_config(args.steps_config)
    run_tags = set(args.run_tags.split(",")) if args.run_tags else set()
    skip_tags = set(args.skip_tags.split(",")) if args.skip_tags else set()

    # By default, don't run indexing steps unless explicitly requested.
    if "indexing" not in run_tags:
        skip_tags.add("indexing")

    steps_to_run = filter_steps(all_steps, run_tags, skip_tags)

    step_results: list[dict[str, object]] = []
    for step in steps_to_run:
        command = build_command(step, sys.executable, args)
        optional = bool(step.get("optional", False))
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
