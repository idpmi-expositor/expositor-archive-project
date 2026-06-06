"""Rename source PDFs using references found inside each document.

This script is a pre-ingestion utility. It helps convert unclear source names
such as ``Lecc46Maestro.pdf`` into stable archive names such as
``expositor-guia-maestro-volumen-46.pdf``.

Important archive rule:
    The script does a dry run by default. It only renames files when ``--apply``
    is provided, so reviewers can inspect the proposed names first.

What this script reads:
    - Existing PDF filename
    - PDF metadata title, when available
    - Text from the first few pages, using PyMuPDF

What this script must NOT do:
    - It must not change PDF contents.
    - It must not extract canonical lesson data.
    - It must not overwrite another PDF.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

try:
    import fitz
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "PyMuPDF is required to inspect PDF references. "
        "Install it with: python -m pip install pymupdf"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "source_assets" / "original_pdfs"
DEFAULT_PAGE_LIMIT = 5
DEFAULT_PUBLICATION_SLUG = "expositor-guia-maestro"

SPANISH_NUMBER_WORDS = {
    "uno": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "dieciseis": 16,
    "diecisiete": 17,
    "dieciocho": 18,
    "diecinueve": 19,
    "veinte": 20,
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
}


@dataclass(frozen=True)
class RenameProposal:
    """One proposed source PDF rename."""

    source_path: Path
    target_path: Path
    volume_number: int | None
    reason: str


def normalize_text(value: str) -> str:
    """Return lowercase text with accents removed for easier matching."""

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }
    normalized = value.lower()
    for original, replacement in replacements.items():
        normalized = normalized.replace(original, replacement)
    return normalized


def read_reference_text(pdf_path: Path, page_limit: int) -> str:
    """Read metadata and first-page text used only for naming decisions."""

    parts = [pdf_path.stem]
    with fitz.open(pdf_path) as document:
        title = (document.metadata or {}).get("title")
        if title:
            parts.append(title)

        for page in document[: min(page_limit, document.page_count)]:
            parts.append(page.get_text("text"))

    return "\n".join(parts)


def extract_volume_number(reference_text: str) -> int | None:
    """Infer the publication volume number from filename or PDF text."""

    normalized = normalize_text(reference_text)
    patterns = [
        r"\bvol(?:umen)?\.?\s*(?:no\.?\s*)?(\d{1,3})\b",
        r"\bvolume\s*(?:no\.?\s*)?(\d{1,3})\b",
        r"\blecc(?:ion|iones)?\s*(\d{1,3})\b",
        r"\blecc(\d{1,3})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return int(match.group(1))

    phrase_match = re.search(r"\bvol(?:umen)?\s+([a-z]+)\b", normalized)
    if phrase_match:
        return SPANISH_NUMBER_WORDS.get(phrase_match.group(1))

    return None


def detect_publication_slug(reference_text: str, default_slug: str) -> tuple[str, str]:
    """Return a stable publication slug and the reason for choosing it."""

    normalized = normalize_text(reference_text)
    if "expositor" in normalized and "maestro" in normalized:
        return "expositor-guia-maestro", "matched Expositor/maestro reference"
    if "maestro" in normalized:
        return default_slug, "matched maestro reference; used archive default"
    return default_slug, "used archive default"


def build_target_name(
    pdf_path: Path,
    page_limit: int,
    default_publication_slug: str,
) -> RenameProposal:
    """Build the proposed target name for one PDF."""

    reference_text = read_reference_text(pdf_path, page_limit)
    volume_number = extract_volume_number(reference_text)
    publication_slug, reason = detect_publication_slug(
        reference_text,
        default_publication_slug,
    )

    if volume_number is None:
        target_name = f"{publication_slug}-{pdf_path.stem}.pdf"
        reason = f"{reason}; volume number not found"
    else:
        target_name = f"{publication_slug}-volumen-{volume_number:02d}.pdf"
        reason = f"{reason}; volume {volume_number} found"

    return RenameProposal(
        source_path=pdf_path,
        target_path=pdf_path.with_name(target_name),
        volume_number=volume_number,
        reason=reason,
    )


def discover_pdfs(source_dir: Path) -> list[Path]:
    """Return source PDFs in deterministic order."""

    if not source_dir.exists():
        return []
    return sorted(source_dir.rglob("*.pdf"))


def print_proposal(proposal: RenameProposal) -> None:
    """Print one rename proposal in a reviewer-friendly format."""

    if proposal.source_path == proposal.target_path:
        action = "keep"
    else:
        action = "rename"

    print(f"{action}: {proposal.source_path.name}")
    print(f"  -> {proposal.target_path.name}")
    print(f"  reason: {proposal.reason}")


def apply_proposal(proposal: RenameProposal) -> None:
    """Apply one safe rename without overwriting existing files."""

    if proposal.source_path == proposal.target_path:
        return
    if proposal.target_path.exists():
        raise FileExistsError(f"Target already exists: {proposal.target_path}")
    proposal.source_path.rename(proposal.target_path)


def main() -> int:
    """Command-line entry point for source PDF rename proposals."""

    parser = argparse.ArgumentParser(
        description="Read source PDFs and rename them with stable references."
    )
    parser.add_argument(
        "--source-dir",
        default=DEFAULT_SOURCE_DIR,
        type=Path,
        help="Folder containing source PDF files.",
    )
    parser.add_argument(
        "--page-limit",
        default=DEFAULT_PAGE_LIMIT,
        type=int,
        help="Number of first pages to inspect for title and volume references.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually rename files. Without this flag, only print proposals.",
    )
    parser.add_argument(
        "--publication-slug",
        default=DEFAULT_PUBLICATION_SLUG,
        help="Default slug to use when a specific publication title is not found.",
    )
    args = parser.parse_args()

    pdf_files = discover_pdfs(args.source_dir)
    if not pdf_files:
        print(f"No PDF files found under {args.source_dir}")
        return 0

    proposals = [
        build_target_name(pdf_file, args.page_limit, args.publication_slug)
        for pdf_file in pdf_files
    ]

    for proposal in proposals:
        print_proposal(proposal)
        if args.apply:
            apply_proposal(proposal)

    if not args.apply:
        print("")
        print("Dry run only. Re-run with --apply to rename the PDF files.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
