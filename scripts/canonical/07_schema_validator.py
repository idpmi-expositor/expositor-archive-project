"""Validate canonical lesson YAML files.

The archive stores one lesson per YAML file. This validator enforces the
minimum lesson segmentation contract, including reference-only biblical
readings that can later be replaced by api.bible or another downstream source.

How to read this script as a novice programmer:
    - Constants near the top define the default folders and files.
    - Small helper functions do one job each.
    - Validation functions raise ``ValidationError`` when the YAML is wrong.
    - ``main`` connects command-line arguments to the validation functions.

Run from the repository root:
    python scripts/canonical/07_schema_validator.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "PyYAML is required to validate canonical lesson YAML files. "
        "Install it with: python -m pip install pyyaml"
    ) from exc


# This script lives in scripts/canonical, so parents[2] is the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Default configuration values. These are not magic; they are simply the paths
# this repository expects when no command-line overrides are provided.
DEFAULT_SCHEMA = PROJECT_ROOT / "schemas" / "base" / "lesson_schema.yaml"
DEFAULT_ARCHIVE = PROJECT_ROOT / "archive" / "lessons"


class ValidationError(ValueError):
    """Raised when a lesson YAML file does not satisfy the archive contract."""


def load_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML file and make sure the root is a mapping.

    In Python, a YAML mapping becomes a ``dict``. The canonical lesson files
    must be dictionaries at the root because fields such as ``lesson_id`` and
    ``lesson_sections`` are named keys.
    """

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: root document must be a mapping")
    return data


def get_nested(data: dict[str, Any], dotted_path: str) -> Any:
    """Look up a nested value using a dotted path.

    Example:
        ``lesson_sections.biblical_reading`` means:
        data["lesson_sections"]["biblical_reading"]

    Returning ``None`` lets the validator produce a friendly error instead of a
    raw Python ``KeyError``.
    """

    current: Any = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    """Require a value to be a dictionary-like YAML mapping."""

    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be a mapping")
    return value


def require_non_empty(value: Any, label: str) -> None:
    """Require a field to be present and not blank.

    ``None`` means the field is missing or empty. Empty strings, lists, and
    dictionaries are also rejected because required archival fields must carry
    useful information.
    """

    if value is None:
        raise ValidationError(f"{label} is required")
    if isinstance(value, str) and not value.strip():
        raise ValidationError(f"{label} must not be empty")
    if isinstance(value, (list, dict)) and not value:
        raise ValidationError(f"{label} must not be empty")


def validate_root_fields(lesson: dict[str, Any], schema: dict[str, Any]) -> None:
    """Validate required top-level fields like ``lesson_id`` and ``title``."""

    for field in schema["required_root_fields"]:
        require_non_empty(lesson.get(field), field)


def validate_nested_fields(lesson: dict[str, Any], schema: dict[str, Any]) -> None:
    """Validate required fields inside root metadata mappings.

    The root check proves that ``processing_audit`` exists. This deeper check
    proves that expected children such as ``processing_audit.ocr_engine`` also
    exist and contain useful archival information.
    """

    for parent_field, child_fields in schema.get("required_nested_fields", {}).items():
        parent = require_mapping(lesson.get(parent_field), parent_field)
        for child_field in child_fields:
            require_non_empty(parent.get(child_field), f"{parent_field}.{child_field}")


def validate_lesson_sections(lesson: dict[str, Any], schema: dict[str, Any]) -> None:
    """Validate the minimum required lesson sections.

    A lesson can contain additional sections later, but it must contain the core
    structure needed for searching, review, and downstream generation.
    """

    sections = require_mapping(lesson.get("lesson_sections"), "lesson_sections")

    for section_name, section_schema in schema["required_lesson_sections"].items():
        section = require_mapping(
            sections.get(section_name), f"lesson_sections.{section_name}"
        )
        for field in section_schema["required_fields"]:
            require_non_empty(
                section.get(field), f"lesson_sections.{section_name}.{field}"
            )


def validate_biblical_reading(lesson: dict[str, Any], schema: dict[str, Any]) -> None:
    """Validate that ``Lectura Biblica`` is stored as replaceable metadata.

    The important rule is ``source_text_included: false``. The archive keeps the
    reference, such as ``Santiago 2:14-24``, and a downstream system can later
    fetch the actual Bible text from api.bible.
    """

    reading = require_mapping(
        get_nested(lesson, "lesson_sections.biblical_reading"),
        "lesson_sections.biblical_reading",
    )
    policy_schema = schema["biblical_reading_policy"]
    replacement_policy = require_mapping(
        reading.get("replacement_policy"),
        "lesson_sections.biblical_reading.replacement_policy",
    )

    for field in policy_schema["required_replacement_policy_fields"]:
        require_non_empty(
            replacement_policy.get(field),
            f"lesson_sections.biblical_reading.replacement_policy.{field}",
        )

    if replacement_policy["provider"] != policy_schema["replacement_provider"]:
        raise ValidationError(
            "lesson_sections.biblical_reading.replacement_policy.provider "
            f"must be {policy_schema['replacement_provider']}"
        )

    if replacement_policy["strategy"] != policy_schema["replacement_strategy"]:
        raise ValidationError(
            "lesson_sections.biblical_reading.replacement_policy.strategy "
            f"must be {policy_schema['replacement_strategy']}"
        )

    if replacement_policy["source_text_included"] is not False:
        raise ValidationError(
            "lesson_sections.biblical_reading.replacement_policy."
            "source_text_included must be false"
        )

    references = reading.get("canonical_references")
    if not isinstance(references, list) or not references:
        raise ValidationError(
            "lesson_sections.biblical_reading.canonical_references "
            "must be a non-empty list"
        )

    for index, reference in enumerate(references):
        if not isinstance(reference, dict):
            raise ValidationError(
                "lesson_sections.biblical_reading.canonical_references"
                f"[{index}] must be a mapping"
            )
        for field in policy_schema["canonical_reference_required_fields"]:
            require_non_empty(
                reference.get(field),
                "lesson_sections.biblical_reading."
                f"canonical_references[{index}].{field}",
            )


def validate_lesson(path: Path, schema: dict[str, Any]) -> list[str]:
    """Validate one lesson file and return a list of error messages."""

    try:
        lesson = load_yaml(path)
        validate_root_fields(lesson, schema)
        validate_nested_fields(lesson, schema)
        validate_lesson_sections(lesson, schema)
        validate_biblical_reading(lesson, schema)
    except ValidationError as exc:
        return [str(exc)]
    return []


def iter_lesson_files(target: Path) -> list[Path]:
    """Return YAML files from either one file or a whole directory."""

    if target.is_file():
        return [target]
    return sorted(target.rglob("*.yaml"))


def main() -> int:
    """Parse command-line options, validate files, and return an exit code.

    Exit codes are useful for automation:
        0 means success.
        1 means validation failed.
    """

    parser = argparse.ArgumentParser(
        description="Validate canonical Expositor lesson YAML files."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=DEFAULT_ARCHIVE,
        type=Path,
        help="Lesson YAML file or directory to validate.",
    )
    parser.add_argument(
        "--schema",
        default=DEFAULT_SCHEMA,
        type=Path,
        help="Schema contract YAML file.",
    )
    args = parser.parse_args()

    schema = load_yaml(args.schema)
    lesson_files = iter_lesson_files(args.target)

    if not lesson_files:
        print(f"No lesson YAML files found under {args.target}")
        return 0

    failures: dict[Path, list[str]] = {}
    for lesson_file in lesson_files:
        errors = validate_lesson(lesson_file, schema)
        if errors:
            failures[lesson_file] = errors

    if failures:
        for lesson_file, errors in failures.items():
            print(f"FAIL {lesson_file}")
            for error in errors:
                print(f"  - {error}")
        return 1

    print(f"Validated {len(lesson_files)} lesson YAML file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
