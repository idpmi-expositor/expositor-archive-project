"""Discover source PDF files and prepare intake metadata.

This is the first script in the archive pipeline.

Pipeline position:
    PDF -> RAW TEXT -> STRUCTURED DOCUMENT MODEL -> CANONICAL YAML
    ^
    This script works at the very beginning.

What this script is responsible for:
    1. Look inside ``source_assets/original_pdfs`` for PDF files.
    2. Report which files were found.
    3. Prepare a stable place for future intake logs.

What this script must NOT do:
    - It must not read lesson text.
    - It must not decide where lessons begin or end.
    - It must not create canonical YAML files.
    - It must not guess meaning from the source publication.

Beginner note:
    A Python file can be used as a script when it has a ``main`` function and
    the ``if __name__ == "__main__"`` block at the bottom. That block only runs
    when you execute this file directly from the command line.
"""

from __future__ import annotations

import argparse
from pathlib import Path


# ``Path(__file__)`` is the path to this Python file.
# ``parents[2]`` walks upward:
#   0 = scripts/ingestion
#   1 = scripts
#   2 = repository root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Default folders used by this script. Keeping these as constants at the top
# makes the script easier to inspect and safer to change later.
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "source_assets" / "original_pdfs"
DEFAULT_INTAKE_LOG_DIR = PROJECT_ROOT / "source_assets" / "intake_logs"


def discover_pdfs(source_dir: Path) -> list[Path]:
    """Return all PDF files under ``source_dir`` in deterministic order.

    Deterministic means the same input folder should produce the same ordered
    list every time. Sorting is important because the archive values repeatable
    output over convenience.
    """

    if not source_dir.exists():
        return []

    return sorted(source_dir.rglob("*.pdf"))


def main() -> int:
    """Command-line entry point for PDF discovery."""

    parser = argparse.ArgumentParser(
        description="Discover source PDFs for Expositor archive intake."
    )
    parser.add_argument(
        "--source-dir",
        default=DEFAULT_SOURCE_DIR,
        type=Path,
        help="Folder containing immutable source PDF files.",
    )
    parser.add_argument(
        "--intake-log-dir",
        default=DEFAULT_INTAKE_LOG_DIR,
        type=Path,
        help="Folder reserved for future intake logs.",
    )
    args = parser.parse_args()

    args.intake_log_dir.mkdir(parents=True, exist_ok=True)
    pdf_files = discover_pdfs(args.source_dir)

    if not pdf_files:
        print(f"No PDF files found under {args.source_dir}")
        return 0

    print(f"Discovered {len(pdf_files)} PDF file(s):")
    for pdf_file in pdf_files:
        print(f"- {pdf_file.relative_to(PROJECT_ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
