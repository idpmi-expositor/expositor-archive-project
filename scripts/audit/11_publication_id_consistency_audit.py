"""Audit for inconsistent publication IDs across pipeline artifacts.

This script helps ensure that a publication's ID is used consistently in
file paths and in the content of metadata and draft files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "PyYAML is required for this script. "
        "Install it with: python -m pip install pyyaml"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON file."""
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file."""
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected YAML mapping")
    return data


def check_draft_yaml(draft_dir: Path) -> list[str]:
    """Check draft YAML files for path/content mismatches."""
    mismatches: list[str] = []
    yaml_files = sorted(draft_dir.rglob("*.yaml")) if draft_dir.exists() else []
    for yaml_file in yaml_files:
        try:
            path_pub_id = yaml_file.relative_to(draft_dir).parts[0]
            data = load_yaml(yaml_file)
            content_pub_id = data.get("publication_id")
            if content_pub_id and content_pub_id != path_pub_id:
                mismatches.append(
                    f"Draft YAML mismatch: {yaml_file.relative_to(PROJECT_ROOT)} "
                    f"(path implies '{path_pub_id}', content has '{content_pub_id}')"
                )
        except (ValueError, IndexError) as exc:
            mismatches.append(f"Could not parse {yaml_file}: {exc}")
    return mismatches


def check_metadata_files(metadata_dir: Path, source_key: str) -> list[str]:
    """Check metadata JSON files for path/content mismatches."""
    mismatches: list[str] = []
    json_files = sorted(metadata_dir.rglob("*.json")) if metadata_dir.exists() else []
    for json_file in json_files:
        try:
            path_pub_id = json_file.stem
            data = load_json(json_file)
            source_path = data.get(source_key)
            if isinstance(source_path, str) and path_pub_id not in source_path:
                mismatches.append(
                    f"Metadata mismatch: {json_file.relative_to(PROJECT_ROOT)} "
                    f"(filename is '{path_pub_id}', but source is '{source_path}')"
                )
        except ValueError as exc:
            mismatches.append(f"Could not parse {json_file}: {exc}")
    return mismatches


def main() -> int:
    """Command-line entry point for the publication ID consistency audit."""
    parser = argparse.ArgumentParser(description="Audit publication ID consistency.")
    parser.add_argument(
        "--draft-dir", default=PROJECT_ROOT / "archive" / "drafts", type=Path
    )
    parser.add_argument(
        "--lesson-meta-dir", default=PROJECT_ROOT / "metadata" / "lessons", type=Path
    )
    parser.add_argument(
        "--section-meta-dir",
        default=PROJECT_ROOT / "metadata" / "lesson_sections",
        type=Path,
    )
    args = parser.parse_args()

    all_mismatches: list[str] = []
    all_mismatches.extend(check_draft_yaml(args.draft_dir))
    all_mismatches.extend(
        check_metadata_files(args.lesson_meta_dir, "source_structure")
    )
    all_mismatches.extend(
        check_metadata_files(args.section_meta_dir, "source_segments")
    )

    if not all_mismatches:
        print("Publication ID consistency audit passed.")
        return 0

    print(f"Found {len(all_mismatches)} publication ID inconsistencies:")
    for mismatch in all_mismatches:
        print(f"- {mismatch}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
