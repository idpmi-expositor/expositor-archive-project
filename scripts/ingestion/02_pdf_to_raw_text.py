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
    - Direct PDF text extraction uses PyMuPDF first.
    - OCR fallback is used only for pages with weak or empty extracted text.
    - Page boundaries are preserved because later traceability depends on
      knowing where each extracted block came from.
    - The original PDF is never modified.

Beginner note:
    PyMuPDF is imported as ``fitz``. It opens the PDF, lets us loop over pages,
    and extracts text from each page without changing the original PDF.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

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

# Pages below these thresholds are considered weak direct text extraction and
# become eligible for OCR fallback. These are intentionally conservative so
# normal text-layer PDFs continue to use deterministic PyMuPDF extraction.
MIN_DIRECT_TEXT_CHARACTERS = 40
MIN_DIRECT_TEXT_WORDS = 5


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


def normalize_line_endings(text: str) -> str:
    """Normalize line endings without changing extracted wording."""

    return text.replace("\r\n", "\n").replace("\r", "\n")


def page_text_quality(text: str) -> dict[str, Any]:
    """Return simple page-level extraction quality signals."""

    normalized = normalize_line_endings(text)
    words = normalized.split()
    character_count = len(normalized)
    word_count = len(words)
    is_weak = (
        character_count < MIN_DIRECT_TEXT_CHARACTERS
        or word_count < MIN_DIRECT_TEXT_WORDS
    )

    return {
        "character_count": character_count,
        "word_count": word_count,
        "is_weak_text_layer": is_weak,
    }


def ocr_available() -> tuple[bool, str | None]:
    """Return whether optional Tesseract OCR dependencies appear available."""

    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        return False, "missing_python_ocr_dependency"

    if shutil.which("tesseract") is None:
        return False, "missing_tesseract_executable"

    return True, None


def render_page_for_ocr(page: fitz.Page, dpi: int = 300) -> "Image.Image":
    """Render one PDF page into a PIL image for OCR fallback."""

    from PIL import Image

    pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    return Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)


def extract_text_with_ocr(page: fitz.Page, language: str) -> tuple[str, float | None]:
    """Extract text from one page using Tesseract OCR.

    OCR is extraction-only. It does not classify headings, infer lesson
    boundaries, or reorganize paragraphs.
    """

    import pytesseract
    from pytesseract import Output

    image = render_page_for_ocr(page)
    text = normalize_line_endings(pytesseract.image_to_string(image, lang=language))

    confidence_values: list[float] = []
    data = pytesseract.image_to_data(image, lang=language, output_type=Output.DICT)
    for raw_confidence in data.get("conf", []):
        try:
            confidence = float(raw_confidence)
        except (TypeError, ValueError):
            continue
        if confidence >= 0:
            confidence_values.append(confidence)

    average_confidence = (
        sum(confidence_values) / len(confidence_values)
        if confidence_values
        else None
    )
    return text, average_confidence


def extract_page_text(
    page: fitz.Page,
    *,
    use_ocr_fallback: bool,
    ocr_language: str,
    can_ocr: bool,
    ocr_unavailable_reason: str | None,
) -> tuple[str, dict[str, Any]]:
    """Extract one page and return text plus audit metadata."""

    direct_text = normalize_line_endings(page.get_text("text"))
    direct_quality = page_text_quality(direct_text)

    log_entry: dict[str, Any] = {
        "character_count": direct_quality["character_count"],
        "word_count": direct_quality["word_count"],
        "direct_text_character_count": direct_quality["character_count"],
        "direct_text_word_count": direct_quality["word_count"],
        "direct_text_is_weak": direct_quality["is_weak_text_layer"],
        "extraction_method": "pymupdf_text",
        "ocr_attempted": False,
        "ocr_applied": False,
        "ocr_confidence": None,
        "ocr_unavailable_reason": None,
    }

    if not use_ocr_fallback or not direct_quality["is_weak_text_layer"]:
        return direct_text, log_entry

    log_entry["ocr_attempted"] = True
    if not can_ocr:
        log_entry["ocr_unavailable_reason"] = ocr_unavailable_reason
        return direct_text, log_entry

    ocr_text, ocr_confidence = extract_text_with_ocr(page, ocr_language)
    ocr_quality = page_text_quality(ocr_text)

    # Use OCR only when it provides more usable text than the weak direct layer.
    if ocr_quality["word_count"] > direct_quality["word_count"]:
        log_entry.update(
            {
                "character_count": ocr_quality["character_count"],
                "word_count": ocr_quality["word_count"],
                "extraction_method": "tesseract_ocr_fallback",
                "ocr_applied": True,
                "ocr_confidence": ocr_confidence,
            }
        )
        return ocr_text, log_entry

    log_entry["ocr_confidence"] = ocr_confidence
    return direct_text, log_entry


def extract_pdf_text(
    pdf_path: Path,
    *,
    use_ocr_fallback: bool = True,
    ocr_language: str = "spa+eng",
) -> tuple[str, list[dict[str, Any]]]:
    """Extract text from one PDF while preserving page boundaries.

    The returned tuple has two parts:
        1. the raw text artifact consumed by the normalization layer
        2. the per-page audit data consumed by human reviewers
    """

    output_parts: list[str] = []
    page_logs: list[dict[str, Any]] = []
    can_ocr, ocr_unavailable_reason = ocr_available()

    with fitz.open(pdf_path) as document:
        for page_index, page in enumerate(document, start=1):
            text, page_log = extract_page_text(
                page,
                use_ocr_fallback=use_ocr_fallback,
                ocr_language=ocr_language,
                can_ocr=can_ocr,
                ocr_unavailable_reason=ocr_unavailable_reason,
            )

            # The page header becomes the trace anchor used by later layers.
            # If a lesson section is later mapped to PDF page 6, this marker is
            # the evidence trail back to the source extraction.
            output_parts.append(page_header(page_index))
            output_parts.append(text.strip())
            output_parts.append("")

            page_log["pdf_page"] = page_index
            page_logs.append(page_log)

    return "\n".join(output_parts).rstrip() + "\n", page_logs


def extraction_summary(page_logs: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize extraction methods and quality across the PDF."""

    weak_pages = [
        page_log["pdf_page"]
        for page_log in page_logs
        if page_log.get("direct_text_is_weak")
    ]
    ocr_pages = [
        page_log["pdf_page"]
        for page_log in page_logs
        if page_log.get("ocr_applied")
    ]

    return {
        "weak_direct_text_pages": weak_pages,
        "ocr_fallback_pages": ocr_pages,
        "ocr_fallback_page_count": len(ocr_pages),
        "manual_review_required": bool(weak_pages),
    }


def extract_pdf_file(
    pdf_path: Path,
    output_dir: Path,
    log_dir: Path,
    *,
    use_ocr_fallback: bool = True,
    ocr_language: str = "spa+eng",
) -> None:
    """Extract one PDF to raw text and write a processing log."""

    output_path = expected_raw_text_path(pdf_path, output_dir)
    log_path = expected_log_path(pdf_path, log_dir)
    raw_text, page_logs = extract_pdf_text(
        pdf_path,
        use_ocr_fallback=use_ocr_fallback,
        ocr_language=ocr_language,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(raw_text, encoding="utf-8", newline="\n")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    # Keep the log factual. Structure detection belongs to the next layer, so
    # this audit records source paths, extraction methods, and quality signals.
    log_path.write_text(
        json.dumps(
            {
                "source_pdf": str(pdf_path.relative_to(PROJECT_ROOT)),
                "raw_text": str(output_path.relative_to(PROJECT_ROOT)),
                "page_count": len(page_logs),
                "ocr_fallback_enabled": use_ocr_fallback,
                "ocr_language": ocr_language,
                "extraction_summary": extraction_summary(page_logs),
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
    parser.add_argument(
        "--no-ocr-fallback",
        action="store_true",
        help="Disable Tesseract OCR fallback for weak or empty text-layer pages.",
    )
    parser.add_argument(
        "--ocr-language",
        default="spa+eng",
        help="Tesseract language string used for OCR fallback.",
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
        extract_pdf_file(
            pdf_file,
            args.output_dir,
            args.log_dir,
            use_ocr_fallback=not args.no_ocr_fallback,
            ocr_language=args.ocr_language,
        )
        print(f"Extracted {pdf_file} -> {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
