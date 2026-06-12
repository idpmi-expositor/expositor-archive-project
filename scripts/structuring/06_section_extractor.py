"""Extract deterministic lesson sections from normalized text spans."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEGMENT_DIR = PROJECT_ROOT / "metadata" / "lessons"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "metadata" / "lesson_sections"
CANONICAL_DIR = PROJECT_ROOT / "scripts" / "canonical"
if str(CANONICAL_DIR) not in sys.path:
    sys.path.insert(0, str(CANONICAL_DIR))

from scripture_reference_parser import parse_scripture_references  # noqa: E402


SECTION_ALIASES = {
    "biblical_reading": ("lectura biblica",),
    "teacher_notes": ("notas para el maestro",),
    "lesson_outline": ("bosquejo de la leccion",),
    "summary_application": ("resumen y aplicacion practica",),
}
STOP_LABELS = {
    "lectura biblica",
    "notas para el maestro",
    "introduccion a la leccion",
    "bosquejo de la leccion",
    "vocabulario",
    "aplicacion del maestro",
    "lecturas diarias",
    "bibliografias",
    "bibliografia",
    "resumen y aplicacion practica",
}
REFERENCE_PREFIX_RE = re.compile(r"^Lectura B[ií]blica:\s*(?P<reference>.+)$", re.I)


def normalize_for_matching(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value)
    without_accents = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"\s+", " ", without_accents.lower()).strip().rstrip(":")


def resolve_project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def safe_relative_to_project(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def source_text_for_segment_file(segment_file: Path, metadata: dict[str, Any]) -> Path:
    structure_path = resolve_project_path(str(metadata.get("source_structure") or ""))
    structure = load_json(structure_path)
    source_text = structure.get("source_text")
    if not isinstance(source_text, str) or not source_text:
        raise ValueError(f"{structure_path}: missing source_text")
    return resolve_project_path(source_text)


def line_page(line: str, active_page: int | None) -> int | None:
    match = re.match(r"^===== PDF_PAGE (\d+) =====$", line.strip())
    if match:
        return int(match.group(1))
    return active_page


def is_stop_label(line: str) -> bool:
    normalized = normalize_for_matching(line)
    return any(normalized.startswith(label) for label in STOP_LABELS) or any(
        label in normalized for label in ("vocabulario", "aplicacion del maestro")
    )


def find_label(lines: list[str], start: int, end: int, aliases: tuple[str, ...]) -> int | None:
    for index in range(start, min(end, len(lines))):
        normalized = normalize_for_matching(lines[index])
        if any(normalized.startswith(alias) for alias in aliases):
            return index
    return None


def collect_block(
    lines: list[str],
    label_index: int,
    end: int,
    *,
    include_label_remainder: bool = True,
) -> tuple[list[str], int]:
    items: list[str] = []
    first_line = lines[label_index].strip()
    if include_label_remainder and ":" in first_line:
        remainder = first_line.split(":", 1)[1].strip()
        if remainder:
            items.append(remainder)

    block_end = label_index
    for index in range(label_index + 1, min(end, len(lines))):
        line = lines[index].strip()
        if not line:
            continue
        if re.match(r"^===== PDF_PAGE \d+ =====$", line):
            continue
        if is_stop_label(line):
            break
        if re.fullmatch(r"\d{1,4}", line):
            continue
        if normalize_for_matching(line) in {"maestro", "alumno"}:
            continue
        items.append(line)
        block_end = index

    return items, block_end


def collect_outline_block(lines: list[str], label_index: int, end: int) -> tuple[list[str], int]:
    """Collect only the compact outline block, not the full lesson body."""

    items: list[str] = []
    block_end = label_index
    seen_outline_item = False
    outline_item_re = re.compile(r"^(?:[IVXLCDM]+\.|[A-Z]\.)\s+", re.I)

    for index in range(label_index + 1, min(end, len(lines))):
        line = lines[index].strip()
        if not line:
            continue
        if re.match(r"^===== PDF_PAGE \d+ =====$", line):
            if seen_outline_item:
                break
            continue
        normalized = normalize_for_matching(line)
        if normalized.startswith("resumen y aplicacion practica") and not outline_item_re.match(line):
            break
        if any(normalized.startswith(label) for label in STOP_LABELS - {"resumen y aplicacion practica"}):
            break
        if re.fullmatch(r"\d{1,4}", line) or normalized in {"maestro", "alumno"}:
            continue

        if outline_item_re.match(line):
            items.append(line)
            block_end = index
            seen_outline_item = True
            if normalize_for_matching(line).startswith("iv. resumen"):
                break
            continue

        if seen_outline_item and len(line) < 120:
            items.append(line)
            block_end = index
            continue

        if seen_outline_item:
            break

    return items, block_end


def page_for_line(lines: list[str], line_number: int) -> int | None:
    active_page: int | None = None
    for index, line in enumerate(lines[:line_number], start=1):
        active_page = line_page(line, active_page)
    return active_page


def source_trace(
    source_text: Path,
    lines: list[str],
    start_index: int,
    end_index: int,
) -> dict[str, Any]:
    return {
        "source_text": safe_relative_to_project(source_text),
        "line_start": start_index + 1,
        "line_end": end_index + 1,
        "page_start": page_for_line(lines, start_index + 1),
        "page_end": page_for_line(lines, end_index + 1),
    }


def extract_biblical_reading(
    lines: list[str],
    source_text: Path,
    start: int,
    end: int,
) -> dict[str, Any] | None:
    label_index = find_label(lines, start, end, SECTION_ALIASES["biblical_reading"])
    if label_index is None:
        return None

    line = lines[label_index].strip()
    match = REFERENCE_PREFIX_RE.match(line)
    if not match:
        return None

    reference_display = match.group("reference").strip()
    return {
        "reference_display": reference_display,
        "canonical_references": parse_scripture_references(reference_display),
        "source_trace": source_trace(source_text, lines, label_index, label_index),
    }


def extract_list_section(
    lines: list[str],
    source_text: Path,
    start: int,
    end: int,
    section_name: str,
) -> dict[str, Any] | None:
    label_index = find_label(lines, start, end, SECTION_ALIASES[section_name])
    if label_index is None:
        return None

    if section_name == "lesson_outline":
        items, block_end = collect_outline_block(lines, label_index, end)
    else:
        items, block_end = collect_block(lines, label_index, end, include_label_remainder=False)
    if not items:
        return None

    return {
        "items": items,
        "source_trace": source_trace(source_text, lines, label_index, block_end),
    }


def extract_sections_for_segment(
    lines: list[str],
    source_text: Path,
    segment: dict[str, Any],
) -> dict[str, Any]:
    start = max(0, int(segment.get("start_line") or 1) - 1)
    end = int(segment.get("end_line") or len(lines))
    extracted: dict[str, Any] = {}

    biblical_reading = extract_biblical_reading(lines, source_text, start, end)
    if biblical_reading:
        extracted["biblical_reading"] = biblical_reading

    for section_name in ("teacher_notes", "lesson_outline", "summary_application"):
        section = extract_list_section(lines, source_text, start, end, section_name)
        if section:
            extracted[section_name] = section

    return extracted


def write_section_file(input_path: Path, output_path: Path) -> dict[str, Any]:
    metadata = load_json(input_path)
    source_text = source_text_for_segment_file(input_path, metadata)
    lines = source_text.read_text(encoding="utf-8").splitlines()
    lessons: list[dict[str, Any]] = []

    for segment in metadata.get("segments", []):
        if not isinstance(segment, dict):
            continue
        sections = extract_sections_for_segment(lines, source_text, segment)
        lessons.append(
            {
                "lesson_number": int(segment["lesson_number"]),
                "sections": sections,
                "automation_status": "automated_unreviewed",
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "source_segments": safe_relative_to_project(input_path),
        "source_text": safe_relative_to_project(source_text),
        "lessons": lessons,
    }
    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract automated unreviewed lesson sections from normalized text."
    )
    parser.add_argument("--input-dir", default=DEFAULT_SEGMENT_DIR, type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, type=Path)
    args = parser.parse_args()

    segment_files = sorted(args.input_dir.rglob("*.json")) if args.input_dir.exists() else []
    if not segment_files:
        print(f"No lesson segment metadata found under {args.input_dir}")
        return 0

    for segment_file in segment_files:
        output_file = args.output_dir / segment_file.relative_to(args.input_dir)
        result = write_section_file(segment_file, output_file)
        extracted_count = sum(1 for lesson in result["lessons"] if lesson["sections"])
        print(f"Extracted sections {segment_file} -> {output_file} [{extracted_count} lesson(s)]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
