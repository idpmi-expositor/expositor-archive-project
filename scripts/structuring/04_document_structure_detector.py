"""Detect document structure from normalized text.

This script identifies structural markers but does not create final YAML.

Pipeline position:
    PDF -> RAW TEXT -> STRUCTURED DOCUMENT MODEL -> CANONICAL YAML
                             ^
                             This script starts the intermediate model.

Allowed signals:
    - Explicit lesson headers, such as "LECCION 1" or "LECCION 12".
    - Page markers written by the raw text extractor.
    - The "Contenido" page, which can validate lesson titles and page numbers.
    - Known section labels, such as "Lectura Biblica", "Lectura Bíblica",
      and "Notas para el Maestro".
    - Deterministic patterns that can be explained and repeated.

Forbidden behavior:
    - No AI interpretation.
    - No guessing based on theology or wording.
    - No translation.
    - No canonical YAML generation.

Beginner note:
    Regular expressions are used here because the source publications have
    repeated textual markers. A regular expression is a pattern for matching
    text, such as "LECCION" followed by one or more digits.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NORMALIZED_DIR = PROJECT_ROOT / "normalized"
DEFAULT_STRUCTURE_DIR = PROJECT_ROOT / "structured" / "document_structure"


LESSON_HEADER_PATTERN = re.compile(r"^\s*LECCI[OÓ]N\s+(\d+)\b", re.IGNORECASE)
PAGE_MARKER_PATTERN = re.compile(r"^===== PDF_PAGE (\d+) =====$")
DATE_PATTERN = re.compile(r"^\d{1,2}/[A-Za-zÁÉÍÓÚáéíóúñÑ]{3}/\d{2}$")
CONTENT_ENTRY_START_PATTERN = re.compile(
    r"^(?P<lesson_number>\d{1,3})\.\s*(?P<rest>.+)$"
)
CONTENT_ENTRY_PAGE_PATTERN = re.compile(r"(?P<title>.*?)(?P<page>\d{1,4})\s*$")
CONTENIDO_LABELS = {"contenido", "indice", "índice"}
SECTION_LABELS = (
    "Titulo",
    "Título",
    "Lectura Biblica",
    "Lectura Bíblica",
    "Bosquejo de la leccion",
    "Bosquejo de la lección",
    "Notas para el Maestro",
    "Resumen y aplicacion practica",
    "Resumen y aplicación práctica",
    "Contenido",
)


@dataclass(frozen=True)
class StructureMarker:
    """A single detected marker in a normalized text file."""

    line_number: int
    marker_type: str
    text: str


@dataclass(frozen=True)
class ContentIndexEntry:
    """One row extracted from the source publication's Contenido page."""

    lesson_number: int
    title: str
    page_start: int
    lesson_date: str | None
    source_pdf_page: int


def normalize_for_matching(value: str) -> str:
    """Return lowercase text without accents for deterministic label matching.

    This allows source text such as ``Lectura Bíblica`` and ``Lectura Biblica``
    to match the same section label without using AI or fuzzy guessing.
    """

    decomposed = unicodedata.normalize("NFD", value)
    without_accents = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )
    return without_accents.lower().strip()


NORMALIZED_SECTION_LABELS = tuple(
    normalize_for_matching(label) for label in SECTION_LABELS
)


def relative_output_path(input_path: Path, input_dir: Path, output_dir: Path) -> Path:
    """Preserve input subfolders when writing structure JSON.

    Preserving the relative path prevents different collections from overwriting
    each other when they reuse the same filename.
    """

    return output_dir / input_path.relative_to(input_dir).with_suffix(".json")


def safe_relative_to_project(path: Path) -> str:
    """Return a readable relative path when the file is inside the repository."""

    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def current_pdf_page(line: str, existing_page: int | None) -> int | None:
    """Update the active PDF page when a page marker line is encountered."""

    match = PAGE_MARKER_PATTERN.match(line.strip())
    if match:
        return int(match.group(1))
    return existing_page


def clean_content_title(value: str) -> str:
    """Remove dot leaders and normalize spacing from a Contenido title."""

    value = re.sub(r"\s*(?:\.\s*){2,}", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" .")


def parse_content_entry_buffer(
    lesson_number: int,
    buffer: list[str],
    lesson_date: str | None,
    source_pdf_page: int,
) -> ContentIndexEntry | None:
    """Try to convert buffered Contenido lines into one entry."""

    joined = " ".join(part.strip() for part in buffer if part.strip())
    match = CONTENT_ENTRY_PAGE_PATTERN.match(joined)
    if not match:
        return None

    title = clean_content_title(match.group("title"))
    page_start = int(match.group("page"))
    if not title:
        return None

    return ContentIndexEntry(
        lesson_number=lesson_number,
        title=title,
        page_start=page_start,
        lesson_date=lesson_date,
        source_pdf_page=source_pdf_page,
    )


def detect_markers(text: str) -> list[StructureMarker]:
    """Find known structural markers in normalized text.

    Markers are intentionally lightweight: type, line number, and source text.
    Lesson slicing and canonical field mapping happen later.
    """

    markers: list[StructureMarker] = []
    active_page: int | None = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        updated_page = current_pdf_page(line, active_page)
        if updated_page != active_page:
            active_page = updated_page
            markers.append(
                StructureMarker(
                    line_number=line_number,
                    marker_type="page_marker",
                    text=line.strip(),
                )
            )
            continue

        if LESSON_HEADER_PATTERN.search(line):
            markers.append(
                StructureMarker(
                    line_number=line_number,
                    marker_type="lesson_header",
                    text=line.strip(),
                )
            )
            continue

        normalized_line = normalize_for_matching(line)
        for label in NORMALIZED_SECTION_LABELS:
            if normalized_line.startswith(label):
                markers.append(
                    StructureMarker(
                        line_number=line_number,
                        marker_type="section_label",
                        text=line.strip(),
                    )
                )
                break

    return markers


def page_text_blocks(text: str) -> dict[int, list[str]]:
    """Group normalized text lines by PDF page marker."""

    pages: dict[int, list[str]] = {}
    active_page: int | None = None
    for line in text.splitlines():
        updated_page = current_pdf_page(line, active_page)
        if updated_page != active_page:
            active_page = updated_page
            pages.setdefault(active_page, [])
            continue
        if active_page is not None:
            pages.setdefault(active_page, []).append(line)
    return pages


def content_entry_signal_count(lines: list[str]) -> int:
    """Count deterministic Contenido row signals on a page."""

    count = 0
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue
        if DATE_PATTERN.match(stripped_line):
            count += 1
            continue
        if CONTENT_ENTRY_START_PATTERN.match(stripped_line):
            count += 1
    return count


def detect_contenido_pages(text: str) -> list[int]:
    """Return candidate PDF pages that contain the source Contenido table.

    The detector is deterministic. It searches for a page with a standalone
    ``CONTENIDO``/``INDICE`` label and table-like lesson/date rows instead of
    relying on a fixed page number.
    """

    candidates: list[tuple[int, int]] = []
    for page_number, lines in page_text_blocks(text).items():
        normalized_lines = [normalize_for_matching(line.strip()) for line in lines]
        has_contenido_label = any(line in CONTENIDO_LABELS for line in normalized_lines)
        if not has_contenido_label:
            continue
        signal_count = content_entry_signal_count(lines)
        candidates.append((page_number, signal_count))

    # Prefer pages that look most like a table of contents, then lowest page
    # number for deterministic tie-breaking.
    return [
        page_number
        for page_number, _signal_count in sorted(
            candidates,
            key=lambda item: (-item[1], item[0]),
        )
    ]


def parse_content_index(text: str, contenido_page: int) -> list[ContentIndexEntry]:
    """Extract lesson title/page rows from one Contenido page.

    The parser is deterministic: entries must start with a lesson number such as
    ``15.`` and eventually end with a page number. Wrapped title lines are
    buffered until the page number is found.
    """

    entries: list[ContentIndexEntry] = []
    active_page: int | None = None
    pending_date: str | None = None
    active_lesson_number: int | None = None
    active_buffer: list[str] = []

    def flush_active_entry() -> None:
        nonlocal active_lesson_number, active_buffer, pending_date

        if active_lesson_number is None:
            return

        entry = parse_content_entry_buffer(
            active_lesson_number,
            active_buffer,
            pending_date,
            contenido_page,
        )
        if entry is not None:
            entries.append(entry)
            pending_date = None

        active_lesson_number = None
        active_buffer = []

    for line in text.splitlines():
        active_page = current_pdf_page(line, active_page)
        if active_page != contenido_page:
            continue

        stripped_line = line.strip()
        if not stripped_line:
            continue

        normalized_line = normalize_for_matching(stripped_line)
        if normalized_line in CONTENIDO_LABELS:
            continue

        if DATE_PATTERN.match(stripped_line):
            pending_date = stripped_line
            continue

        start_match = CONTENT_ENTRY_START_PATTERN.match(stripped_line)
        if start_match:
            flush_active_entry()
            active_lesson_number = int(start_match.group("lesson_number"))
            active_buffer = [start_match.group("rest")]
            entry = parse_content_entry_buffer(
                active_lesson_number,
                active_buffer,
                pending_date,
                contenido_page,
            )
            if entry is not None:
                entries.append(entry)
                pending_date = None
                active_lesson_number = None
                active_buffer = []
            continue

        if active_lesson_number is not None:
            active_buffer.append(stripped_line)
            entry = parse_content_entry_buffer(
                active_lesson_number,
                active_buffer,
                pending_date,
                contenido_page,
            )
            if entry is not None:
                entries.append(entry)
                pending_date = None
                active_lesson_number = None
                active_buffer = []

    flush_active_entry()

    return entries


def build_content_index(text: str) -> tuple[list[ContentIndexEntry], dict[str, object]]:
    """Detect Contenido dynamically and return entries plus audit metadata."""

    candidate_pages = detect_contenido_pages(text)
    attempted_pages: list[dict[str, object]] = []
    for page_number in candidate_pages:
        entries = parse_content_index(text, contenido_page=page_number)
        attempted_pages.append(
            {
                "pdf_page": page_number,
                "entry_count": len(entries),
            }
        )
        if entries:
            return entries, {
                "detection_method": "dynamic_contenido_label",
                "selected_pdf_page": page_number,
                "candidate_pdf_pages": candidate_pages,
                "attempted_pages": attempted_pages,
                "warning": None,
            }

    return [], {
        "detection_method": "dynamic_contenido_label",
        "selected_pdf_page": None,
        "candidate_pdf_pages": candidate_pages,
        "attempted_pages": attempted_pages,
        "warning": "No parseable Contenido table was detected.",
    }


def write_structure_file(input_path: Path, output_path: Path) -> None:
    """Write a simple JSON structure report for one normalized text file."""

    text = input_path.read_text(encoding="utf-8")
    markers = detect_markers(text)
    content_index, content_index_detection = build_content_index(text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "source_text": safe_relative_to_project(input_path),
                "markers": [asdict(marker) for marker in markers],
                "content_index_detection": content_index_detection,
                "content_index": [asdict(entry) for entry in content_index],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    """Command-line entry point for structure detection."""

    parser = argparse.ArgumentParser(
        description="Detect deterministic structure markers in normalized text."
    )
    parser.add_argument(
        "--input-dir",
        default=DEFAULT_NORMALIZED_DIR,
        type=Path,
        help="Folder containing normalized .txt files.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_STRUCTURE_DIR,
        type=Path,
        help="Folder where DocumentStructure JSON files will be written.",
    )
    args = parser.parse_args()

    input_files = sorted(args.input_dir.rglob("*.txt")) if args.input_dir.exists() else []
    if not input_files:
        print(f"No normalized text files found under {args.input_dir}")
        return 0

    for input_file in input_files:
        output_file = relative_output_path(input_file, args.input_dir, args.output_dir)
        write_structure_file(input_file, output_file)
        print(f"Detected structure {input_file} -> {output_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
