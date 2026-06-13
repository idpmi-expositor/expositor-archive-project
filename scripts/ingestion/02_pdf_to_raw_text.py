"""Extract raw text from source PDFs.

This is the second script in the ingestion layer.

Pipeline position:
    PDF -> RAW TEXT EXTRACTION -> NORMALIZED TEXT -> DOCUMENT STRUCTURE DETECTION
          ^
          This script creates raw text artifacts only.

Important archive rule:
    Raw text is non-canonical extraction evidence. It is never rewritten by this
    script after creation; normalization writes a separate artifact under
    normalized/.

Implementation notes:
    - Direct PDF text extraction uses PyMuPDF first.
    - OCR fallback is used only for pages with weak or empty extracted text.
      Most Expositor PDFs have embedded text after page 1, so OCR is fallback
      only, not the primary path.
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
import os
import shutil
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL.Image import Image

try:
    import fitz
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "PyMuPDF is required to extract PDF text. "
        "Install it with: python -m pip install pymupdf"
    ) from exc

from ocr_quality_gate import (
    QualityStatus,
    apply_repeated_header_footer_issues,
    evaluate_page_text,
    select_best_page_text,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "source_assets" / "original_pdfs"
DEFAULT_RAW_TEXT_DIR = PROJECT_ROOT / "ocr" / "raw_txt"
DEFAULT_PROCESSING_LOG_DIR = PROJECT_ROOT / "ocr" / "processing_logs"
DEFAULT_TESSERACT_CMD = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


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


def project_relative_path(path: Path) -> str:
    """Return a stable project-relative path when possible."""

    resolved_path = path.resolve()
    try:
        return str(resolved_path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def runtime_config_path(path: Path | None) -> str | None:
    """Return reproducible runtime path metadata for processing logs."""

    if path is None:
        return None

    resolved_path = path.resolve()
    try:
        return str(resolved_path.relative_to(PROJECT_ROOT))
    except ValueError:
        return f"external:{path.name}"


def page_header(page_number: int) -> str:
    """Create a deterministic page marker for raw text output.

    These markers make page boundaries visible to later scripts while keeping
    the raw text easy for a human to inspect.
    """

    return f"===== PDF_PAGE {page_number} ====="


def normalize_line_endings(text: str) -> str:
    """Normalize line endings without changing extracted wording."""

    return text.replace("\r\n", "\n").replace("\r", "\n")


def ocr_available(tesseract_cmd: Path | None) -> tuple[bool, str | None]:
    """Return whether optional Tesseract OCR dependencies appear available."""

    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        return False, "missing_python_ocr_dependency"

    if tesseract_cmd and tesseract_cmd.exists():
        return True, None

    if shutil.which("tesseract") is None:
        return False, "missing_tesseract_executable"

    return True, None


def render_page_for_ocr(page: fitz.Page, dpi: int = 300) -> Image:
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


def configure_tesseract(tesseract_cmd: Path | None, tessdata_dir: Path | None) -> None:
    """Configure pytesseract with deterministic local executable settings."""

    import pytesseract

    if tesseract_cmd and tesseract_cmd.exists():
        pytesseract.pytesseract.tesseract_cmd = str(tesseract_cmd)

    if tessdata_dir:
        os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)


def quality_log_entry(quality, *, prefix: str | None = None) -> dict[str, Any]:
    """Convert a quality result into JSON log fields."""

    metadata = quality.to_metadata()
    fields = {
        "status": metadata["status"],
        "word_count": metadata["word_count"],
        "issues": metadata["issues"],
        "confidence_score": metadata["confidence_score"],
        "valid_char_ratio": round(quality.valid_char_ratio, 4),
        "long_line_ratio": round(quality.long_line_ratio, 4),
        "malformed_scripture_count": quality.malformed_scripture_count,
    }
    if prefix is None:
        return fields
    return {f"{prefix}_{key}": value for key, value in fields.items()}


def extract_page_text(
    page: fitz.Page,
    *,
    page_number: int,
    use_ocr_fallback: bool,
    ocr_language: str,
    can_ocr: bool,
    ocr_unavailable_reason: str | None,
) -> tuple[str, dict[str, Any]]:
    """Extract one page and return text plus audit metadata."""

    direct_text = normalize_line_endings(page.get_text("text"))
    direct_quality = evaluate_page_text(page_number, direct_text, "pymupdf")

    log_entry: dict[str, Any] = {
        "character_count": len(direct_text),
        "word_count": direct_quality.word_count,
        "direct_text_character_count": len(direct_text),
        "direct_text_word_count": direct_quality.word_count,
        "direct_text_is_weak": direct_quality.status == QualityStatus.NEEDS_OCR,
        "direct_text_status": direct_quality.status.value,
        "direct_text_issues": [issue.value for issue in direct_quality.issues],
        "direct_text_confidence_score": direct_quality.confidence_score,
        "extraction_method": "pymupdf_text",
        "ocr_attempted": False,
        "ocr_applied": False,
        "ocr_confidence": None,
        "ocr_unavailable_reason": None,
        "quality_gate": quality_log_entry(direct_quality),
    }

    if not use_ocr_fallback or direct_quality.status != QualityStatus.NEEDS_OCR:
        return direct_text, log_entry

    log_entry["ocr_attempted"] = True
    if not can_ocr:
        log_entry["ocr_unavailable_reason"] = ocr_unavailable_reason
        return direct_text, log_entry

    ocr_text, ocr_confidence = extract_text_with_ocr(page, ocr_language)
    ocr_quality = evaluate_page_text(
        page_number,
        ocr_text,
        "tesseract",
        ocr_confidence=ocr_confidence,
    )
    selected_quality = select_best_page_text(direct_quality, ocr_quality)

    log_entry.update(quality_log_entry(ocr_quality, prefix="ocr"))
    log_entry["ocr_confidence"] = ocr_confidence
    log_entry["quality_gate"] = quality_log_entry(selected_quality)

    if selected_quality.source == "tesseract":
        log_entry.update(
            {
                "character_count": len(ocr_text),
                "word_count": ocr_quality.word_count,
                "extraction_method": "tesseract_ocr_fallback",
                "ocr_applied": True,
            }
        )
        return ocr_text, log_entry

    if selected_quality.status == QualityStatus.NEEDS_HUMAN_REVIEW:
        log_entry["extraction_method"] = "quality_gate_blocked"
        return "", log_entry

    return selected_quality.text, log_entry


def extract_pdf_text(
    pdf_path: Path,
    *,
    use_ocr_fallback: bool = True,
    ocr_language: str = "spa+eng",
    tesseract_cmd: Path | None = DEFAULT_TESSERACT_CMD,
    tessdata_dir: Path | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Extract text from one PDF while preserving page boundaries.

    The returned tuple has two parts:
        1. the raw text artifact consumed by the normalization layer
        2. the per-page audit data consumed by human reviewers
    """

    extracted_pages: list[tuple[str, dict[str, Any]]] = []
    can_ocr, ocr_unavailable_reason = ocr_available(tesseract_cmd)
    if can_ocr:
        configure_tesseract(tesseract_cmd, tessdata_dir)

    with fitz.open(pdf_path) as document:
        for page_index, page in enumerate(document, start=1):
            text, page_log = extract_page_text(
                page,
                page_number=page_index,
                use_ocr_fallback=use_ocr_fallback,
                ocr_language=ocr_language,
                can_ocr=can_ocr,
                ocr_unavailable_reason=ocr_unavailable_reason,
            )

            page_log["pdf_page"] = page_index
            extracted_pages.append((text, page_log))

    quality_pages = [
        evaluate_page_text(
            page_log["pdf_page"],
            text,
            page_log["extraction_method"],
            ocr_confidence=page_log.get("ocr_confidence"),
        )
        for text, page_log in extracted_pages
    ]
    quality_pages = apply_repeated_header_footer_issues(quality_pages)

    output_parts: list[str] = []
    page_logs: list[dict[str, Any]] = []
    for (text, page_log), final_quality in zip(extracted_pages, quality_pages):
        page_log["quality_gate"] = quality_log_entry(final_quality)
        page_log["quality_status"] = final_quality.status.value
        page_log["quality_issues"] = [issue.value for issue in final_quality.issues]
        page_log["quality_confidence_score"] = final_quality.confidence_score

        # The page header becomes the trace anchor used by later layers.
        # If a lesson section is later mapped to PDF page 6, this marker is
        # the evidence trail back to the source extraction.
        output_parts.append(page_header(page_log["pdf_page"]))
        output_parts.append(text.strip())
        output_parts.append("")
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
    human_review_pages = [
        page_log["pdf_page"]
        for page_log in page_logs
        if page_log.get("quality_status") == QualityStatus.NEEDS_HUMAN_REVIEW.value
    ]

    return {
        "weak_direct_text_pages": weak_pages,
        "ocr_fallback_pages": ocr_pages,
        "ocr_fallback_page_count": len(ocr_pages),
        "human_review_pages": human_review_pages,
        "human_review_page_count": len(human_review_pages),
        "manual_review_required": bool(weak_pages or human_review_pages),
    }


def extract_pdf_file(
    pdf_path: Path,
    output_dir: Path,
    log_dir: Path,
    *,
    use_ocr_fallback: bool = True,
    ocr_language: str = "spa+eng",
    tesseract_cmd: Path | None = DEFAULT_TESSERACT_CMD,
    tessdata_dir: Path | None = None,
) -> None:
    """Extract one PDF to raw text and write a processing log."""

    output_path = expected_raw_text_path(pdf_path, output_dir)
    log_path = expected_log_path(pdf_path, log_dir)
    if output_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing raw text artifact: {output_path}. "
            "Move it aside or choose a new --output-dir before rerunning extraction."
        )

    raw_text, page_logs = extract_pdf_text(
        pdf_path,
        use_ocr_fallback=use_ocr_fallback,
        ocr_language=ocr_language,
        tesseract_cmd=tesseract_cmd,
        tessdata_dir=tessdata_dir,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(raw_text, encoding="utf-8", newline="\n")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    # Keep the log factual. Structure detection belongs to the next layer, so
    # this audit records source paths, extraction methods, and quality signals.
    log_path.write_text(
        json.dumps(
            {
                "source_pdf": project_relative_path(pdf_path),
                "raw_text": project_relative_path(output_path),
                "page_count": len(page_logs),
                "ocr_fallback_enabled": use_ocr_fallback,
                "ocr_language": ocr_language,
                "tesseract_cmd": runtime_config_path(tesseract_cmd),
                "tessdata_dir": runtime_config_path(tessdata_dir),
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
        description="Extract raw text from source PDFs while preserving pages; existing raw text is not overwritten."
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
    parser.add_argument(
        "--tesseract-cmd",
        default=DEFAULT_TESSERACT_CMD,
        type=Path,
        help="Path to tesseract.exe. Defaults to the standard Windows install path.",
    )
    parser.add_argument(
        "--tessdata-dir",
        default=None,
        type=Path,
        help="Optional tessdata directory for deterministic language data.",
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
            tesseract_cmd=args.tesseract_cmd,
            tessdata_dir=args.tessdata_dir,
        )
        print(f"Extracted {pdf_file} -> {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
