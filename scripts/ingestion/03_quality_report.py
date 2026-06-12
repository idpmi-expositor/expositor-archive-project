"""Build readable OCR/extraction quality reports from processing logs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_DIR = PROJECT_ROOT / "ocr" / "processing_logs"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "ocr" / "quality_reports"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def report_status(pages: list[dict[str, Any]]) -> str:
    statuses = {str(page.get("quality_status") or "") for page in pages}
    if "NEEDS_HUMAN_REVIEW" in statuses or "NEEDS_OCR" in statuses:
        return "BLOCKED"
    if "WARNING" in statuses:
        return "WARNING"
    return "PASS"


def build_report(log_path: Path) -> dict[str, Any]:
    log = load_json(log_path)
    pages = [page for page in log.get("pages", []) if isinstance(page, dict)]
    status_counts = Counter(str(page.get("quality_status") or "UNKNOWN") for page in pages)
    issue_counts: Counter[str] = Counter()
    for page in pages:
        for issue in page.get("quality_issues", []):
            issue_counts[str(issue)] += 1

    def pages_with_status(status: str) -> list[int]:
        return [
            int(page["pdf_page"])
            for page in pages
            if page.get("quality_status") == status and "pdf_page" in page
        ]

    return {
        "source_log": str(log_path.relative_to(PROJECT_ROOT)),
        "source_pdf": log.get("source_pdf"),
        "page_count": log.get("page_count", len(pages)),
        "status": report_status(pages),
        "status_counts": dict(sorted(status_counts.items())),
        "issue_counts": dict(sorted(issue_counts.items())),
        "zero_text_pages": [
            int(page["pdf_page"])
            for page in pages
            if int(page.get("word_count") or 0) == 0 and "pdf_page" in page
        ],
        "low_word_count_pages": [
            {
                "pdf_page": int(page["pdf_page"]),
                "word_count": int(page.get("word_count") or 0),
            }
            for page in pages
            if 0 < int(page.get("word_count") or 0) < 25 and "pdf_page" in page
        ],
        "needs_ocr_pages": pages_with_status("NEEDS_OCR"),
        "needs_human_review_pages": pages_with_status("NEEDS_HUMAN_REVIEW"),
        "warning_pages": pages_with_status("WARNING"),
        "ocr_fallback_pages": [
            int(page["pdf_page"])
            for page in pages
            if page.get("ocr_applied") and "pdf_page" in page
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create OCR quality report summaries.")
    parser.add_argument("--log-dir", default=DEFAULT_LOG_DIR, type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_REPORT_DIR, type=Path)
    args = parser.parse_args()

    log_files = sorted(args.log_dir.rglob("*.json")) if args.log_dir.exists() else []
    if not log_files:
        print(f"No processing logs found under {args.log_dir}")
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for log_file in log_files:
        report = build_report(log_file)
        output_file = args.output_dir / log_file.relative_to(args.log_dir)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote quality report {output_file} [{report['status']}]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
