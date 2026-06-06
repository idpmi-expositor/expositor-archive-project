"""Validate local source PDFs against a Google Drive source folder.

This script checks that ``source_assets/original_pdfs`` contains the same PDF
filenames and file sizes as the configured Google Drive source folder.

It is intentionally read-only. If a mismatch is found, it exits with status 1
and prints the exact missing or mismatched files for a human/operator to sync.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "source_assets" / "original_pdfs"
DEFAULT_REMOTE = "gdrive:"


@dataclass(frozen=True)
class PdfEntry:
    """Minimal comparable information for one source PDF."""

    name: str
    size: int


def local_pdf_entries(source_dir: Path) -> dict[str, PdfEntry]:
    """Return local PDF entries keyed by filename."""

    if not source_dir.exists():
        return {}

    entries: dict[str, PdfEntry] = {}
    for pdf_path in sorted(source_dir.glob("*.pdf")):
        entries[pdf_path.name] = PdfEntry(name=pdf_path.name, size=pdf_path.stat().st_size)
    return entries


def remote_pdf_entries(remote: str, drive_root_folder_id: str | None) -> dict[str, PdfEntry]:
    """Return Google Drive PDF entries through rclone, keyed by filename."""

    command = ["rclone", "lsjson"]
    if drive_root_folder_id:
        command.extend(["--drive-root-folder-id", drive_root_folder_id])
    command.append(remote)

    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit("rclone is required for Drive sync validation.") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip()
        raise SystemExit(f"rclone failed while listing remote PDFs: {message}") from exc

    entries: dict[str, PdfEntry] = {}
    for item in json.loads(completed.stdout):
        if item.get("IsDir"):
            continue
        name = item.get("Name") or item.get("Path")
        if not name or not name.lower().endswith(".pdf"):
            continue
        entries[name] = PdfEntry(name=name, size=int(item.get("Size", 0)))
    return entries


def print_entry_list(title: str, names: list[str]) -> None:
    """Print a named list only when it has entries."""

    if not names:
        return
    print(title)
    for name in names:
        print(f"- {name}")


def validate_sync(local_entries: dict[str, PdfEntry], remote_entries: dict[str, PdfEntry]) -> int:
    """Compare local and remote entries, printing a concise validation report."""

    local_names = set(local_entries)
    remote_names = set(remote_entries)
    missing_local = sorted(remote_names - local_names)
    missing_remote = sorted(local_names - remote_names)
    size_mismatches = sorted(
        name
        for name in local_names & remote_names
        if local_entries[name].size != remote_entries[name].size
    )

    print_entry_list("Missing locally:", missing_local)
    print_entry_list("Missing on Google Drive:", missing_remote)

    if size_mismatches:
        print("Size mismatches:")
        for name in size_mismatches:
            print(
                f"- {name}: local={local_entries[name].size}, "
                f"remote={remote_entries[name].size}"
            )

    if missing_local or missing_remote or size_mismatches:
        print("Source PDF sync validation failed.")
        return 1

    print(f"Source PDF sync validation passed for {len(local_entries)} PDF file(s).")
    return 0


def main() -> int:
    """Command-line entry point for source PDF sync validation."""

    parser = argparse.ArgumentParser(
        description="Validate local source PDFs against a Google Drive folder."
    )
    parser.add_argument(
        "--source-dir",
        default=DEFAULT_SOURCE_DIR,
        type=Path,
        help="Local folder containing source PDF files.",
    )
    parser.add_argument(
        "--remote",
        default=DEFAULT_REMOTE,
        help="rclone remote/path to compare against.",
    )
    parser.add_argument(
        "--drive-root-folder-id",
        help="Google Drive folder ID used with the rclone Google Drive remote.",
    )
    args = parser.parse_args()

    local_entries = local_pdf_entries(args.source_dir)
    remote_entries = remote_pdf_entries(args.remote, args.drive_root_folder_id)
    return validate_sync(local_entries, remote_entries)


if __name__ == "__main__":
    raise SystemExit(main())
