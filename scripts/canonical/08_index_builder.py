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
import re
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
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pipeline_classification import profile_metadata  # noqa: E402


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
            width=4096,
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


def section_item_kind(text: str) -> str:
    """Classify a section item for later translation and HTML/CSS formatting."""

    stripped = text.strip()
    if not stripped or stripped.upper() == "TBD":
        return "placeholder"
    if re.match(r"^[IVXLCDM]+\.\s+", stripped, re.IGNORECASE):
        return "roman_heading"
    if re.match(r"^[A-Z]\.\s+", stripped):
        return "letter_subpoint"
    if stripped.startswith("(") and stripped.endswith(")"):
        return "scripture_reference"
    if stripped.startswith("¿") or stripped.endswith("?"):
        return "question"
    return "paragraph"


def indexed_section_items(
    lesson_id: str,
    section_key: str,
    raw_items: Any,
    *,
    has_section_trace: bool = False,
) -> list[dict[str, Any]]:
    """Build stable, item-level index entries for one lesson section."""

    if not isinstance(raw_items, list):
        return []

    indexed_items: list[dict[str, Any]] = []
    item_slug = section_key.replace("_", "-")
    for index, item in enumerate(raw_items, start=1):
        text = str(item).strip()
        if not text:
            continue
        entry = {
            "item_id": f"{lesson_id}-{item_slug}-{index:03d}",
            "order": index,
            "kind": section_item_kind(text),
            "text": text,
        }
        if has_section_trace:
            entry["source_trace_ref"] = section_key
        indexed_items.append(entry)
    return indexed_items


def indexed_section(
    lesson: dict[str, Any],
    section_key: str,
    source_trace: dict[str, Any],
) -> dict[str, Any]:
    """Return a section index block with item IDs, kinds, and source trace."""

    section = lesson.get("lesson_sections", {}).get(section_key, {})
    section_traces = source_trace.get("section_traces")
    has_section_trace = isinstance(section_traces, dict) and isinstance(
        section_traces.get(section_key), dict
    )
    items = indexed_section_items(
        lesson["lesson_id"],
        section_key,
        section.get("items"),
        has_section_trace=has_section_trace,
    )
    result: dict[str, Any] = {
        "item_count": len(items),
        "items": items,
    }
    if has_section_trace:
        result["source_trace"] = section_traces[section_key]
    return result


def index_header(
    *,
    index_scope: str,
    source_archive: str | None,
    view: str,
    lessons: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return shared index metadata for all index views."""

    profile_values = {
        tuple(profile_metadata(lesson["publication_id"]).items()) for lesson in lessons
    }
    profile_entries = [dict(items) for items in sorted(profile_values)]
    header: dict[str, Any] = {
        "schema_version": "1.0.0",
        "index_scope": index_scope,
        "index_view": view,
        "profiles": profile_entries,
    }
    if source_archive:
        header["source_archive"] = source_archive
    if index_scope != "canonical_reviewed":
        header["warning"] = (
            "This index was built from unreviewed draft YAML. Do not use it as "
            "canonical archive truth."
        )
    return header


def lesson_profile_fields(lesson: dict[str, Any]) -> dict[str, str]:
    """Return profile metadata fields for one lesson entry."""

    metadata = profile_metadata(lesson["publication_id"])
    return {
        "publication_classification": metadata["publication_classification"],
        "profile_id": metadata["profile_id"],
        "profile_version": metadata["profile_version"],
    }


def build_lessons_index(
    lessons: list[dict[str, Any]],
    *,
    index_scope: str = "canonical_reviewed",
    source_archive: str | None = None,
) -> dict[str, Any]:
    """Build the high-level lesson index.

    This index answers questions such as:
        - What lessons exist?
        - What publication, year, and cycle does each lesson belong to?
        - What biblical reading reference belongs to the lesson?
    """

    entries = []
    for lesson in lessons:
        reading = lesson["lesson_sections"]["biblical_reading"]
        source_trace = lesson.get("source_trace", {})
        if not isinstance(source_trace, dict):
            source_trace = {}
        entry = {
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
                "lesson_sections": {
                    "lesson_outline": indexed_section(
                        lesson, "lesson_outline", source_trace
                    ),
                    "teacher_notes": indexed_section(
                        lesson, "teacher_notes", source_trace
                    ),
                    "summary_application": indexed_section(
                        lesson, "summary_application", source_trace
                    ),
                },
        }
        entry.update(lesson_profile_fields(lesson))
        entries.append(entry)
    index = index_header(
        index_scope=index_scope,
        source_archive=source_archive,
        view="detailed_lessons",
        lessons=lessons,
    )
    index["lessons"] = entries
    return index


def build_compact_lessons_index(
    lessons: list[dict[str, Any]],
    *,
    index_scope: str = "canonical_reviewed",
    source_archive: str | None = None,
) -> dict[str, Any]:
    """Build a small lookup index without section item text."""

    entries = []
    for lesson in lessons:
        reading = lesson["lesson_sections"]["biblical_reading"]
        entry = {
            "lesson_id": lesson["lesson_id"],
            "publication_id": lesson["publication_id"],
            "year": lesson["year"],
            "cycle": lesson["cycle"],
            "lesson_number": lesson["lesson_number"],
            "title": lesson["title"],
            "biblical_reading": reading["reference_display"],
        }
        entry.update(lesson_profile_fields(lesson))
        entries.append(entry)
    index = index_header(
        index_scope=index_scope,
        source_archive=source_archive,
        view="compact_lessons",
        lessons=lessons,
    )
    index["lessons"] = entries
    return index


def build_section_outline_index(
    lessons: list[dict[str, Any]],
    *,
    index_scope: str = "canonical_reviewed",
    source_archive: str | None = None,
) -> dict[str, Any]:
    """Build a section/item pointer index for formatting and review."""

    entries = []
    for lesson in lessons:
        source_trace = lesson.get("source_trace", {})
        if not isinstance(source_trace, dict):
            source_trace = {}
        for section_key in ("lesson_outline", "teacher_notes", "summary_application"):
            indexed = indexed_section(lesson, section_key, source_trace)
            entry = {
                "lesson_id": lesson["lesson_id"],
                "publication_id": lesson["publication_id"],
                "section_key": section_key,
                "item_count": indexed["item_count"],
                "items": indexed["items"],
            }
            if "source_trace" in indexed:
                entry["source_trace"] = indexed["source_trace"]
            entry.update(lesson_profile_fields(lesson))
            entries.append(entry)
    index = index_header(
        index_scope=index_scope,
        source_archive=source_archive,
        view="section_outline",
        lessons=lessons,
    )
    index["sections"] = entries
    return index


def build_translation_alignment_index(
    lessons: list[dict[str, Any]],
    *,
    index_scope: str = "canonical_reviewed",
    source_archive: str | None = None,
) -> dict[str, Any]:
    """Build stable source item IDs for future translation alignment."""

    entries = []
    for lesson in lessons:
        source_trace = lesson.get("source_trace", {})
        if not isinstance(source_trace, dict):
            source_trace = {}
        alignment_items = []
        for section_key in ("lesson_outline", "teacher_notes", "summary_application"):
            indexed = indexed_section(lesson, section_key, source_trace)
            for item in indexed["items"]:
                alignment_items.append(
                    {
                        "source_item_id": item["item_id"],
                        "section_key": section_key,
                        "order": item["order"],
                        "kind": item["kind"],
                        "source_text": item["text"],
                    }
                )
        entry = {
            "lesson_id": lesson["lesson_id"],
            "publication_id": lesson["publication_id"],
            "source_language": lesson.get("language", "es"),
            "target_language": "pending",
            "items": alignment_items,
        }
        entry.update(lesson_profile_fields(lesson))
        entries.append(entry)
    index = index_header(
        index_scope=index_scope,
        source_archive=source_archive,
        view="translation_alignment",
        lessons=lessons,
    )
    index["lessons"] = entries
    return index


def build_scripture_index(
    lessons: list[dict[str, Any]],
    *,
    index_scope: str = "canonical_reviewed",
    source_archive: str | None = None,
) -> dict[str, Any]:
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
    index = index_header(
        index_scope=index_scope,
        source_archive=source_archive,
        view="scripture",
        lessons=lessons,
    )
    index["scripture_references"] = entries
    return index


def lessons_by_classification(lessons: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group lessons by publication classification for smaller index views."""

    grouped: dict[str, list[dict[str, Any]]] = {}
    for lesson in lessons:
        classification = profile_metadata(lesson["publication_id"])[
            "publication_classification"
        ]
        grouped.setdefault(classification, []).append(lesson)
    return grouped


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
    parser.add_argument(
        "--allow-unreviewed",
        action="store_true",
        help=(
            "Build a provisional index from unreviewed draft YAML without "
            "canonical validation. Use only for audit and pipeline diagnostics."
        ),
    )
    args = parser.parse_args()

    lesson_files = iter_lesson_files(args.archive)
    if not lesson_files:
        print(f"No canonical lesson YAML files found under {args.archive}")
        print("Index generation stopped because there is no canonical data.")
        return 0

    index_scope = "canonical_reviewed"
    if args.allow_unreviewed:
        index_scope = "automated_unreviewed_draft"
        print(
            "WARNING: building a provisional index from unreviewed draft YAML. "
            "This output is not canonical archive truth."
        )
    else:
        # Index files are public-looking outputs, so validation is the
        # guardrail that keeps incomplete lesson YAML from becoming searchable
        # metadata.
        if not validate_lesson_files(lesson_files, args.schema):
            print("Index generation stopped because lesson validation failed.")
            return 1

    lessons = [load_yaml(path) for path in lesson_files]
    source_archive = args.archive.relative_to(PROJECT_ROOT).as_posix() if args.archive.is_relative_to(PROJECT_ROOT) else str(args.archive)

    write_yaml(
        args.output_dir / "lessons_index.yaml",
        build_lessons_index(
            lessons,
            index_scope=index_scope,
            source_archive=source_archive,
        ),
    )
    write_yaml(
        args.output_dir / "scripture_index.yaml",
        build_scripture_index(
            lessons,
            index_scope=index_scope,
            source_archive=source_archive,
        ),
    )
    write_yaml(
        args.output_dir / "compact_lessons_index.yaml",
        build_compact_lessons_index(
            lessons,
            index_scope=index_scope,
            source_archive=source_archive,
        ),
    )
    write_yaml(
        args.output_dir / "section_outline_index.yaml",
        build_section_outline_index(
            lessons,
            index_scope=index_scope,
            source_archive=source_archive,
        ),
    )
    write_yaml(
        args.output_dir / "translation_alignment_index.yaml",
        build_translation_alignment_index(
            lessons,
            index_scope=index_scope,
            source_archive=source_archive,
        ),
    )

    for classification, family_lessons in lessons_by_classification(lessons).items():
        family_output_dir = args.output_dir / classification
        write_yaml(
            family_output_dir / "compact_lessons_index.yaml",
            build_compact_lessons_index(
                family_lessons,
                index_scope=index_scope,
                source_archive=source_archive,
            ),
        )
        write_yaml(
            family_output_dir / "section_outline_index.yaml",
            build_section_outline_index(
                family_lessons,
                index_scope=index_scope,
                source_archive=source_archive,
            ),
        )
        write_yaml(
            family_output_dir / "translation_alignment_index.yaml",
            build_translation_alignment_index(
                family_lessons,
                index_scope=index_scope,
                source_archive=source_archive,
            ),
        )

    print(f"Indexed {len(lessons)} lesson YAML file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
