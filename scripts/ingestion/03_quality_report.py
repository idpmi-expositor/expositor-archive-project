"""Build readable OCR/extraction quality reports from processing logs.

Reports support maintainer review decisions. A blocked report may still allow
draft regeneration, but it must block canonical promotion until reviewed.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_DIR = PROJECT_ROOT / "ocr" / "processing_logs"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "ocr" / "quality_reports"
DEFAULT_WAIVER_FILE = PROJECT_ROOT / "config" / "waivers" / "ocr_quality_waivers.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def load_waivers(path: Path) -> list[dict[str, Any]]:
    """Load waiver rules from a JSON configuration file."""
    if not path.exists():
        return []
    waiver_data = load_json(path)
    waivers = waiver_data.get("waivers", [])
    if not isinstance(waivers, list):
        raise ValueError(f"{path}: expected 'waivers' to be a list")
    return waivers


def is_waived(
    publication_id: str,
    page_number: int,
    issue_code: str,
    waivers: list[dict[str, Any]],
) -> bool:
    """Return true if a specific issue on a page is waived."""
    for waiver in waivers:
        if (
            waiver.get("publication_id") == publication_id
            and int(waiver.get("pdf_page") or 0) == page_number
            and waiver.get("issue_code") == issue_code
        ):
            return True
    return False


def report_status(pages: list[dict[str, Any]], publication_id: str, waivers: list[dict[str, Any]]) -> str:
    statuses = {str(page.get("quality_status") or "") for page in pages}
    if "NEEDS_HUMAN_REVIEW" in statuses or "NEEDS_OCR" in statuses:
        return "BLOCKED"
    if "WARNING" in statuses or any(p.get("word_count", 0) == 0 for p in pages if not is_waived(publication_id, p.get("pdf_page", 0), "zero_text", waivers)):
        return "WARNING"
    return "PASS"


def build_report(log_path: Path, waivers: list[dict[str, Any]]) -> dict[str, Any]:
    log = load_json(log_path)
    pages = [page for page in log.get("pages", []) if isinstance(page, dict)]
    status_counts = Counter(str(page.get("quality_status") or "UNKNOWN") for page in pages)
    issue_counts: Counter[str] = Counter()
    for page in pages:
        for issue in page.get("quality_issues", []):
            issue_counts[str(issue)] += 1

    publication_id = ""
    if log.get("source_pdf"):
        publication_id = Path(str(log["source_pdf"])).stem

    def pages_with_status(status: str) -> list[int]:
        return [
            int(page["pdf_page"])
            for page in pages
            if page.get("quality_status") == status and "pdf_page" in page
        ]

    zero_text_pages = [
        int(page["pdf_page"])
        for page in pages
        if int(page.get("word_count") or 0) == 0 and "pdf_page" in page
    ]
    waived_zero_text_pages = [
        p for p in zero_text_pages if is_waived(publication_id, p, "zero_text", waivers)
    ]
    unwaived_zero_text_pages = [p for p in zero_text_pages if p not in waived_zero_text_pages]

    final_status = report_status(pages, publication_id, waivers)
    if final_status != "BLOCKED" and unwaived_zero_text_pages:
        final_status = "BLOCKED"

    return {
        "source_log": str(log_path.relative_to(PROJECT_ROOT)),
        "source_pdf": log.get("source_pdf"),
        "page_count": log.get("page_count", len(pages)),
        "status": final_status,
        "status_counts": dict(sorted(status_counts.items())),
        "issue_counts": dict(sorted(issue_counts.items())),
        "zero_text_pages": zero_text_pages,
        "waived_zero_text_pages": waived_zero_text_pages,
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
    parser.add_argument("--waiver-file", default=DEFAULT_WAIVER_FILE, type=Path)
    args = parser.parse_args()

    log_files = sorted(args.log_dir.rglob("*.json")) if args.log_dir.exists() else []
    if not log_files:
        print(f"No processing logs found under {args.log_dir}")
        return 0

    waivers = load_waivers(args.waiver_file)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for log_file in log_files:
        report = build_report(log_file, waivers)
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
