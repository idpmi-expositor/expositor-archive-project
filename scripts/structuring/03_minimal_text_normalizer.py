"""Normalize raw text with minimal deterministic cleanup.

This is the first script in the structuring layer.

Pipeline position:
    PDF -> RAW TEXT -> STRUCTURED DOCUMENT MODEL -> CANONICAL YAML
                ^
                This script cleans raw text before structure detection.

What "minimal" means:
    The script may normalize Unicode form, line endings, repeated spaces, and
    obvious OCR hyphen breaks. It may also reflow hard-wrapped PDF prose lines
    into paragraphs when deterministic structural rules say the lines are plain
    paragraph text. It must not rewrite meaning, summarize content, or decide
    what a paragraph means by interpretation.

Beginner note:
    Text normalization is intentionally conservative. The goal is not to make
    the text beautiful; the goal is to make the next deterministic script see a
    stable, predictable input.
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_TEXT_DIR = PROJECT_ROOT / "ocr" / "raw_txt"
DEFAULT_NORMALIZED_DIR = PROJECT_ROOT / "normalized"

PAGE_MARKER_PATTERN = re.compile(r"^===== PDF_PAGE \d+ =====$")
LESSON_HEADER_PATTERN = re.compile(r"^LECCI[OÓ]N\s+\d+\b", re.IGNORECASE)
ROMAN_OUTLINE_PATTERN = re.compile(r"^[IVXLCDM]+\.\s+", re.IGNORECASE)
LETTER_OUTLINE_PATTERN = re.compile(r"^[A-Z]\.\s+")
CONTENT_ENTRY_PATTERN = re.compile(r"^\d{1,3}\.\s+")
DATE_PATTERN = re.compile(r"^\d{1,2}/[A-Za-zÁÉÍÓÚáéíóúñÑ]{3}/\d{2}$")
PAGE_NUMBER_PATTERN = re.compile(r"^\d{1,4}$")
BIBLE_REFERENCE_ONLY_PATTERN = re.compile(
    r"^(?:\d?\s?[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚáéíóúñÑ]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚáéíóúñÑ]+)?\s+)?"
    r"\d+:\d+(?:-\d+)?(?:\s*[;,]\s*"
    r"(?:\d?\s?[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚáéíóúñÑ]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚáéíóúñÑ]+)?\s+)?"
    r"\d+:\d+(?:-\d+)?)*$"
)

SECTION_LABELS = (
    "titulo",
    "lectura biblica",
    "texto aureo",
    "bosquejo de la leccion",
    "notas para el maestro",
    "resumen y aplicacion practica",
    "lecturas diarias",
    "contenido",
)

# These short labels are protected from paragraph reflow because they often
# appear alone in the source publication. If they were joined to neighboring
# prose, the structure detector could lose a meaningful boundary.
SHORT_STANDALONE_LABELS = {
    "maestro",
    "alumno",
    "joven",
    "adolescente",
    "nino",
    "niño",
    "parvulo",
    "párvulo",
    "lunes",
    "martes",
    "miercoles",
    "miércoles",
    "jueves",
    "viernes",
    "sabado",
    "sábado",
    "domingo",
}


def normalize_for_matching(value: str) -> str:
    """Return lowercase text without accents for deterministic matching."""

    decomposed = unicodedata.normalize("NFD", value)
    without_accents = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )
    return without_accents.lower().strip()


def is_section_label(line: str) -> bool:
    """Return true when a line starts with a known source section label."""

    normalized_line = normalize_for_matching(line).rstrip(":")
    return any(normalized_line.startswith(label) for label in SECTION_LABELS)


def is_bible_reference_only(line: str) -> bool:
    """Return true when a short line appears to contain only a Bible reference."""

    if len(line) > 80:
        return False
    return bool(BIBLE_REFERENCE_ONLY_PATTERN.match(line))


def is_structural_line(line: str) -> bool:
    """Return true for lines that should not be merged into prose paragraphs.

    These rules protect headings, outline items, table-of-contents rows,
    questions, dates, page markers, and other short labels from paragraph
    reflow. This keeps structure visible for later scripts.
    """

    stripped = line.strip()
    if not stripped:
        return True
    if PAGE_MARKER_PATTERN.match(stripped):
        return True
    if LESSON_HEADER_PATTERN.match(stripped):
        return True
    if ROMAN_OUTLINE_PATTERN.match(stripped):
        return True
    if LETTER_OUTLINE_PATTERN.match(stripped):
        return True
    if CONTENT_ENTRY_PATTERN.match(stripped):
        return True
    if DATE_PATTERN.match(stripped):
        return True
    if PAGE_NUMBER_PATTERN.match(stripped):
        return True
    if stripped.startswith("¿"):
        return True
    if is_section_label(stripped):
        return True
    if normalize_for_matching(stripped) in SHORT_STANDALONE_LABELS:
        return True
    if is_bible_reference_only(stripped):
        return True
    return False


def reflow_paragraph_lines(text: str) -> str:
    """Join hard-wrapped prose lines while preserving structural lines.

    The output is still an intermediate artifact. Reflow improves readability
    and detector stability, but it is not canonical text.
    """

    output_lines: list[str] = []
    paragraph_parts: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_parts:
            output_lines.append(re.sub(r"\s+", " ", " ".join(paragraph_parts)).strip())
            paragraph_parts.clear()

    for line in text.split("\n"):
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            output_lines.append("")
            continue

        if is_structural_line(stripped):
            # Flush before structural lines so headings, dates, and labels stay
            # on their own lines for the next script.
            flush_paragraph()
            output_lines.append(stripped)
            continue

        paragraph_parts.append(stripped)

    flush_paragraph()
    return "\n".join(output_lines)


def normalize_text(text: str) -> str:
    """Apply safe text cleanup that does not change lesson meaning."""

    # Normalize Unicode so visually identical characters are stored consistently.
    text = unicodedata.normalize("NFC", text)

    # Convert Windows and old Mac line endings to the standard newline.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Join words broken by a hyphen at the end of a line, such as:
    #   justifica-
    #   cion
    # This is a common OCR artifact.
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Collapse repeated horizontal whitespace while keeping line boundaries.
    text = re.sub(r"[ \t]+", " ", text)

    # Avoid trailing spaces at the ends of lines.
    text = "\n".join(line.rstrip() for line in text.split("\n"))

    # Reflow hard-wrapped PDF lines into paragraph text while preserving source
    # structure needed by later deterministic detectors.
    text = reflow_paragraph_lines(text)

    return text.strip() + "\n" if text.strip() else ""


def normalize_file(input_path: Path, output_path: Path) -> None:
    """Read one raw text file, normalize it, and write the result."""

    source_text = input_path.read_text(encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(normalize_text(source_text), encoding="utf-8")


def main() -> int:
    """Command-line entry point for text normalization."""

    parser = argparse.ArgumentParser(
        description="Apply minimal deterministic cleanup to raw OCR text."
    )
    parser.add_argument(
        "--input-dir",
        default=DEFAULT_RAW_TEXT_DIR,
        type=Path,
        help="Folder containing raw .txt files.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_NORMALIZED_DIR,
        type=Path,
        help="Folder where normalized .txt files will be written.",
    )
    args = parser.parse_args()

    input_files = sorted(args.input_dir.rglob("*.txt")) if args.input_dir.exists() else []
    if not input_files:
        print(f"No raw text files found under {args.input_dir}")
        return 0

    for input_file in input_files:
        output_file = args.output_dir / input_file.relative_to(args.input_dir)
        normalize_file(input_file, output_file)
        print(f"Normalized {input_file} -> {output_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
