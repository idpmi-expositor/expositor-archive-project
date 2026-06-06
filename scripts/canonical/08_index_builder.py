"""Build canonical lesson and scripture indexes.

Indexes intentionally keep biblical reading references separate from any Bible
text. Downstream replacement systems can use the normalized references without
requiring translated scripture text to be stored in this archive.

How to read this script as a novice programmer:
    - ``load_yaml`` reads one lesson file.
    - ``build_lessons_index`` creates a searchable list of lessons.
    - ``build_scripture_index`` creates a searchable list of Bible references.
    - ``write_yaml`` saves those dictionaries as YAML files.

Run from the repository root:
    python scripts/canonical/08_index_builder.py
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "PyYAML is required to build canonical indexes. "
        "Install it with: python -m pip install pyyaml"
    ) from exc


# Repository-level configuration. Keeping these values near the top helps a
# newer programmer see where the script reads from and writes to.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARCHIVE = PROJECT_ROOT / "archive" / "lessons"
DEFAULT_INDEX_DIR = PROJECT_ROOT / "indexes"
DEFAULT_SCHEMA = PROJECT_ROOT / "schemas" / "base" / "lesson_schema.yaml"
VALIDATOR_PATH = PROJECT_ROOT / "scripts" / "canonical" / "07_schema_validator.py"


def load_validator_module() -> Any:
    """Load the validator script so indexes are built only from valid YAML.

    The validator filename starts with a number, so it cannot be imported with a
    normal ``import 07_schema_validator`` statement. ``importlib`` lets us load
    it from its file path instead.
    """

    spec = importlib.util.spec_from_file_location("schema_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load validator module from {VALIDATOR_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_yaml(path: Path) -> dict[str, Any]:
    """Read one YAML file and return it as a Python dictionary."""

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root document must be a mapping")
    return data


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    """Write a Python dictionary as a YAML file.

    ``sort_keys=False`` keeps fields in the order we define them, which makes
    the generated files easier for humans to read in Git diffs.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        yaml.safe_dump(
            data,
            handle,
            allow_unicode=True,
            sort_keys=False,
            explicit_start=True,
        )


def iter_lesson_files(target: Path) -> list[Path]:
    """Return lesson YAML files from either one file or a directory."""

    if target.is_file():
        return [target]
    return sorted(target.rglob("*.yaml"))


def validate_lesson_files(lesson_files: list[Path], schema_path: Path) -> bool:
    """Validate every lesson before writing indexes.

    Returning ``False`` tells ``main`` to stop. This prevents stale or malformed
    lesson YAML from producing official-looking index files.
    """

    validator = load_validator_module()
    schema = validator.load_yaml(schema_path)
    failures: dict[Path, list[str]] = {}

    for lesson_file in lesson_files:
        errors = validator.validate_lesson(lesson_file, schema)
        if errors:
            failures[lesson_file] = errors

    if not failures:
        return True

    for lesson_file, errors in failures.items():
        print(f"FAIL {lesson_file}")
        for error in errors:
            print(f"  - {error}")

    return False


def build_lessons_index(lessons: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the high-level lesson index.

    This index answers questions such as:
        - What lessons exist?
        - What publication, year, and cycle does each lesson belong to?
        - What biblical reading reference belongs to the lesson?
    """

    entries = []
    for lesson in lessons:
        reading = lesson["lesson_sections"]["biblical_reading"]
        entries.append(
            {
                "lesson_id": lesson["lesson_id"],
                "publication_id": lesson["publication_id"],
                "collection_type": lesson["collection_type"],
                "year": lesson["year"],
                "cycle": lesson["cycle"],
                "lesson_number": lesson["lesson_number"],
                "title": lesson["title"],
                "biblical_reading": {
                    "reference_display": reading["reference_display"],
                    "replacement_provider": reading["replacement_policy"]["provider"],
                    "replacement_strategy": reading["replacement_policy"]["strategy"],
                },
            }
        )
    return {"schema_version": "1.0.0", "lessons": entries}


def build_scripture_index(lessons: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the scripture reference index.

    This index is intentionally reference-centered. It stores normalized
    reference metadata so an external api.bible integration can fetch Bible text
    later without changing the canonical archive.
    """

    entries = []
    for lesson in lessons:
        reading = lesson["lesson_sections"]["biblical_reading"]
        for reference in reading["canonical_references"]:
            entries.append(
                {
                    "lesson_id": lesson["lesson_id"],
                    "reference_display": reading["reference_display"],
                    "canonical_reference": reference,
                    "replacement_provider": reading["replacement_policy"]["provider"],
                }
            )
    return {"schema_version": "1.0.0", "scripture_references": entries}


def main() -> int:
    """Parse command-line options and write all configured indexes."""

    parser = argparse.ArgumentParser(
        description="Build Expositor lesson and scripture indexes."
    )
    parser.add_argument(
        "archive",
        nargs="?",
        default=DEFAULT_ARCHIVE,
        type=Path,
        help="Lesson YAML file or directory.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_INDEX_DIR,
        type=Path,
        help="Directory where index YAML files will be written.",
    )
    parser.add_argument(
        "--schema",
        default=DEFAULT_SCHEMA,
        type=Path,
        help="Schema contract used to validate lessons before indexing.",
    )
    args = parser.parse_args()

    lesson_files = iter_lesson_files(args.archive)
    if not lesson_files:
        print(f"No canonical lesson YAML files found under {args.archive}")
        print("Index generation stopped because there is no canonical data.")
        return 0

    # Index files are public-looking outputs, so validation is the guardrail
    # that keeps incomplete lesson YAML from becoming searchable metadata.
    if not validate_lesson_files(lesson_files, args.schema):
        print("Index generation stopped because lesson validation failed.")
        return 1

    lessons = [load_yaml(path) for path in lesson_files]

    write_yaml(args.output_dir / "lessons_index.yaml", build_lessons_index(lessons))
    write_yaml(args.output_dir / "scripture_index.yaml", build_scripture_index(lessons))

    print(f"Indexed {len(lessons)} lesson YAML file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
