"""Generate a pipeline quality audit report.

This script is for maintainers who want one report covering normalization,
draft YAML, provisional indexing, known gaps, warnings, and errors.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit("PyYAML is required. Install it with: python -m pip install pyyaml") from exc


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pipeline_classification import (  # noqa: E402
    KNOWN_CLASSIFICATIONS,
    infer_publication_classification,
    load_profile,
)

CRITICAL_SECTIONS = (
    "biblical_reading",
    "lesson_outline",
    "teacher_notes",
)


def count_files(path: Path, pattern: str) -> int:
    return len(list(path.rglob(pattern))) if path.exists() else 0


def file_size_total(path: Path, pattern: str) -> int:
    return sum(file.stat().st_size for file in path.rglob(pattern)) if path.exists() else 0


def load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def normalized_audit(root: Path) -> dict[str, Any]:
    normalized_dir = root / "normalized"
    txt_files = [file for file in normalized_dir.rglob("*.txt")] if normalized_dir.exists() else []
    by_family = Counter(file.relative_to(normalized_dir).parts[0] for file in txt_files)
    root_level = [
        file.name for file in txt_files if len(file.relative_to(normalized_dir).parts) == 1
    ]
    unknown_families = sorted(
        family
        for family in by_family
        if family not in (*KNOWN_CLASSIFICATIONS, "unclassified")
    )
    return {
        "txt_file_count": len(txt_files),
        "by_family": dict(sorted(by_family.items())),
        "root_level_files": root_level,
        "unknown_families": unknown_families,
        "warnings": [
            "root-level normalized text exists; expected normalized/<classification>/*.txt"
            for _ in root_level[:1]
        ]
        + [
            f"unknown normalized family folder: {family}"
            for family in unknown_families
        ],
    }


def yaml_audit(root: Path) -> dict[str, Any]:
    draft_files = sorted((root / "archive" / "drafts").rglob("*.yaml"))
    canonical_files = sorted((root / "archive" / "lessons").rglob("*.yaml"))
    review_statuses: Counter[str] = Counter()
    section_missing: Counter[str] = Counter()
    profiles: Counter[str] = Counter()

    for draft_file in draft_files:
        data = load_yaml_file(draft_file)
        processing_audit = data.get("processing_audit", {})
        review_status = "unknown"
        if isinstance(processing_audit, dict):
            review_status = str(processing_audit.get("review_status", "unknown"))
        review_statuses[review_status] += 1
        publication_id = str(data.get("publication_id", "unclassified"))
        profile = load_profile(infer_publication_classification(publication_id))
        profiles[str(profile.get("profile_id", "unclassified"))] += 1
        sections = data.get("lesson_sections", {})
        for section_name in profile.get("expected_sections", []):
            section = sections.get(section_name, {}) if isinstance(sections, dict) else {}
            items = section.get("items") if isinstance(section, dict) else None
            if section_name != "biblical_reading" and not items:
                section_missing[section_name] += 1

    warnings = []
    if not canonical_files:
        warnings.append("no reviewed canonical YAML exists under archive/lessons")
    if review_statuses.get("automated_unreviewed"):
        warnings.append("draft YAML remains automated_unreviewed and cannot be official")

    return {
        "draft_yaml_count": len(draft_files),
        "canonical_yaml_count": len(canonical_files),
        "review_statuses": dict(sorted(review_statuses.items())),
        "profiles": dict(sorted(profiles.items())),
        "missing_sections": dict(sorted(section_missing.items())),
        "warnings": warnings,
    }


def indexing_audit(root: Path) -> dict[str, Any]:
    index_dir = root / "indexes" / "provisional"
    lesson_index = load_yaml_file(index_dir / "lessons_index.yaml")
    compact_index = load_yaml_file(index_dir / "compact_lessons_index.yaml")
    section_index = load_yaml_file(index_dir / "section_outline_index.yaml")
    translation_index = load_yaml_file(index_dir / "translation_alignment_index.yaml")
    scripture_index = load_yaml_file(index_dir / "scripture_index.yaml")
    family_dirs = [
        child.name for child in index_dir.iterdir() if child.is_dir()
    ] if index_dir.exists() else []

    lessons = lesson_index.get("lessons", [])
    sections = section_index.get("sections", [])
    translation_lessons = translation_index.get("lessons", [])
    scripture_refs = scripture_index.get("scripture_references", [])
    warnings = []
    if lesson_index.get("index_scope") != "automated_unreviewed_draft":
        warnings.append("provisional lesson index is missing automated_unreviewed_draft scope")
    if not compact_index:
        warnings.append("compact lesson index is missing")
    if not section_index:
        warnings.append("section outline index is missing")
    if not translation_index:
        warnings.append("translation alignment index is missing")

    return {
        "detailed_lesson_count": len(lessons) if isinstance(lessons, list) else 0,
        "compact_lesson_count": len(compact_index.get("lessons", [])),
        "section_entry_count": len(sections) if isinstance(sections, list) else 0,
        "translation_lesson_count": len(translation_lessons) if isinstance(translation_lessons, list) else 0,
        "scripture_reference_count": len(scripture_refs) if isinstance(scripture_refs, list) else 0,
        "family_index_folders": sorted(family_dirs),
        "warnings": warnings,
    }


def ocr_audit(root: Path) -> dict[str, Any]:
    reports = []
    for report_file in sorted((root / "ocr" / "quality_reports").glob("*.json")):
        data = load_json_file(report_file)
        reports.append(
            {
                "source": report_file.stem,
                "status": data.get("status"),
                "page_count": data.get("page_count"),
                "issue_counts": data.get("issue_counts", {}),
            }
        )
    return {"reports": reports}


def other_audits(root: Path) -> dict[str, Any]:
    """Summarize the findings from other dedicated audit reports."""
    missing_sections_report = load_json_file(
        root / "reports" / "missing_sections" / "missing_sections.json"
    )
    title_consistency_report = load_json_file(
        root / "reports" / "title_consistency" / "title_consistency_audit.json"
    )
    low_confidence_scripture_report = load_json_file(
        root / "reports" / "low_confidence_scripture" / "low_confidence_scripture_audit.json"
    )

    missing_items = missing_sections_report.get("missing_items", [])
    critical_missing = [
        item
        for item in missing_items
        if isinstance(item, dict) and item.get("missing_section") in CRITICAL_SECTIONS
    ]

    return {
        "missing_sections": {
            "total_missing": missing_sections_report.get("total_missing", 0),
            "critical_missing_count": len(critical_missing),
            "has_critical_gaps": bool(critical_missing),
        },
        "title_consistency": {
            "total_inconsistencies": title_consistency_report.get("total_inconsistencies", 0),
        },
        "low_confidence_scripture": {
            "total_low_confidence": low_confidence_scripture_report.get(
                "total_low_confidence", 0
            ),
        },
    }


def build_report(root: Path) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "normalization": normalized_audit(root),
        "yaml": yaml_audit(root),
        "indexing": indexing_audit(root),
        "ocr": ocr_audit(root),
        "content_audits": other_audits(root),
        "sizes": {
            "raw_text_bytes": file_size_total(root / "ocr" / "raw_txt", "*.txt"),
            "normalized_text_bytes": file_size_total(root / "normalized", "*.txt"),
            "draft_yaml_bytes": file_size_total(root / "archive" / "drafts", "*.yaml"),
            "provisional_index_bytes": file_size_total(root / "indexes" / "provisional", "*.yaml"),
        },
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Pipeline Quality Audit",
        "",
        f"Generated at: `{report['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Normalized text files: {report['normalization']['txt_file_count']}",
        f"- Draft YAML files: {report['yaml']['draft_yaml_count']}",
        f"- Reviewed canonical YAML files: {report['yaml']['canonical_yaml_count']}",
        f"- Detailed provisional lessons: {report['indexing']['detailed_lesson_count']}",
        f"- Compact provisional lessons: {report['indexing']['compact_lesson_count']}",
        f"- Section index entries: {report['indexing']['section_entry_count']}",
        f"- Translation alignment lessons: {report['indexing']['translation_lesson_count']}",
        f"- Scripture references: {report['indexing']['scripture_reference_count']}",
        f"- Missing section items: {report['content_audits']['missing_sections']['total_missing']}",
        f"- Inconsistent lesson titles: {report['content_audits']['title_consistency']['total_inconsistencies']}",
        f"- Low-confidence scripture references: {report['content_audits']['low_confidence_scripture']['total_low_confidence']}",
        "",
        "## Warnings And Gaps",
        "",
    ]
    warnings = (
        report["normalization"]["warnings"]
        + report["yaml"]["warnings"]
        + report["indexing"]["warnings"]
    )
    if report["content_audits"]["missing_sections"]["has_critical_gaps"]:
        warnings.append(
            f"critical content gaps exist: {report['content_audits']['missing_sections']['critical_missing_count']} missing required sections"
        )
    if report["content_audits"]["title_consistency"]["total_inconsistencies"] > 0:
        warnings.append("lesson title inconsistencies exist between Contenido and headers")
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- No audit warnings detected.")
    lines.extend(
        [
            "",
            "## OCR",
            "",
        ]
    )
    for item in report["ocr"]["reports"]:
        lines.append(
            f"- `{item['source']}`: `{item['status']}`; issues: `{item['issue_counts']}`"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate pipeline quality audit reports.")
    parser.add_argument("--output-dir", default=PROJECT_ROOT / "reports" / "audits", type=Path)
    args = parser.parse_args()

    report = build_report(PROJECT_ROOT)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "pipeline-quality-audit.json"
    md_path = args.output_dir / "pipeline-quality-audit.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(md_path, report)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
