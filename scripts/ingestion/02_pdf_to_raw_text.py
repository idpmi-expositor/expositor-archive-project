"""Extract raw text from source PDFs.

This is the second script in the ingestion layer.

Pipeline position:
    PDF -> RAW TEXT -> STRUCTURED DOCUMENT MODEL -> CANONICAL YAML
          ^
          This script creates raw text artifacts.

Important archive rule:
    Raw text is temporary and non-canonical. It exists only so later scripts can
    detect structure in a repeatable way.

Implementation notes:
    - Direct PDF text extraction uses PyMuPDF.
    - OCR fallback is still a future enhancement.
    - Page boundaries are preserved because later traceability depends on
      knowing where each extracted block came from.

Beginner note:
    PyMuPDF is imported as ``fitz``. It opens the PDF, lets us loop over pages,
    and extracts text from each page without changing the original PDF.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import fitz
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "PyMuPDF is required to extract PDF text. "
        "Install it with: python -m pip install pymupdf"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "source_assets" / "original_pdfs"
DEFAULT_RAW_TEXT_DIR = PROJECT_ROOT / "ocr" / "raw_txt"
DEFAULT_PROCESSING_LOG_DIR = PROJECT_ROOT / "ocr" / "processing_logs"


def expected_raw_text_path(pdf_path: Path, output_dir: Path) -> Path:
    """Return the raw text path that would be generated for one PDF.

    Example:
        source_assets/original_pdfs/booklet.pdf
        becomes
        ocr/raw_txt/booklet.txt
    """

    return output_dir / f"{pdf_path.stem}.txt"


def expected_log_path(pdf_path: Path, log_dir: Path) -> Path:
    """Return the JSON processing log path for one PDF."""

    return log_dir / f"{pdf_path.stem}.json"


def page_header(page_number: int) -> str:
    """Create a deterministic page marker for raw text output.

    These markers make page boundaries visible to later scripts while keeping
    the raw text easy for a human to inspect.
    """

    return f"===== PDF_PAGE {page_number} ====="


def extract_pdf_text(pdf_path: Path) -> tuple[str, list[dict[str, object]]]:
    """Extract text from one PDF while preserving page boundaries.

    The returned tuple has two parts:
        1. the raw text artifact consumed by the normalization layer
        2. the per-page audit data consumed by human reviewers
    """

    output_parts: list[str] = []
    page_logs: list[dict[str, object]] = []

    with fitz.open(pdf_path) as document:
        for page_index, page in enumerate(document, start=1):
            text = page.get_text("text").replace("\r\n", "\n").replace("\r", "\n")
            # The page header becomes the trace anchor used by later layers.
            # If a lesson section is later mapped to PDF page 6, this marker is
            # the evidence trail back to the source extraction.
            output_parts.append(page_header(page_index))
            output_parts.append(text.strip())
            output_parts.append("")
            page_logs.append(
                {
                    "pdf_page": page_index,
                    "character_count": len(text),
                    "word_count": len(text.split()),
                    "extraction_method": "pymupdf_text",
                }
            )

    return "\n".join(output_parts).rstrip() + "\n", page_logs


def extract_pdf_file(pdf_path: Path, output_dir: Path, log_dir: Path) -> None:
    """Extract one PDF to raw text and write a small processing log."""

    output_path = expected_raw_text_path(pdf_path, output_dir)
    log_path = expected_log_path(pdf_path, log_dir)
    raw_text, page_logs = extract_pdf_text(pdf_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(raw_text, encoding="utf-8", newline="\n")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    # Keep the log small and factual. Structure detection belongs to the next
    # layer, so this audit only records source paths and extraction counts.
    log_path.write_text(
        json.dumps(
            {
                "source_pdf": str(pdf_path.relative_to(PROJECT_ROOT)),
                "raw_text": str(output_path.relative_to(PROJECT_ROOT)),
                "page_count": len(page_logs),
                "pages": page_logs,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    """Command-line entry point for raw text extraction."""

    parser = argparse.ArgumentParser(
        description="Extract raw text from source PDFs while preserving pages."
    )
    parser.add_argument(
        "--source-dir",
        default=DEFAULT_SOURCE_DIR,
        type=Path,
        help="Folder containing source PDF files.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_RAW_TEXT_DIR,
        type=Path,
        help="Folder where raw text files will be written.",
    )
    parser.add_argument(
        "--log-dir",
        default=DEFAULT_PROCESSING_LOG_DIR,
        type=Path,
        help="Folder where extraction logs will be written.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.log_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(args.source_dir.rglob("*.pdf")) if args.source_dir.exists() else []
    if not pdf_files:
        print(f"No PDF files found under {args.source_dir}")
        return 0

    for pdf_file in pdf_files:
        output_path = expected_raw_text_path(pdf_file, args.output_dir)
        extract_pdf_file(pdf_file, args.output_dir, args.log_dir)
        print(f"Extracted {pdf_file} -> {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
