"""Tests for the pipeline quality summary audit script."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "PyYAML is required for this script. "
        "Install it with: python -m pip install pyyaml"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from audit._10_pipeline_quality_audit import build_report  # noqa: E402


class TestPipelineQualityAudit(unittest.TestCase):
    """Verify the summary audit aggregates data correctly."""

    def setUp(self) -> None:
        """Create a temporary directory for mock artifacts."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        # Create mock directories
        (self.root / "reports" / "missing_sections").mkdir(parents=True)
        (self.root / "reports" / "title_consistency").mkdir(parents=True)
        (self.root / "reports" / "low_confidence_scripture").mkdir(parents=True)
        (self.root / "ocr" / "quality_reports").mkdir(parents=True)
        (self.root / "normalized" / "maestro").mkdir(parents=True)
        (self.root / "archive" / "drafts").mkdir(parents=True)
        (self.root / "indexes" / "provisional").mkdir(parents=True)
        (self.root / "config" / "expositor_profiles").mkdir(parents=True)

        # Create mock profile
        profile_path = self.root / "config" / "expositor_profiles" / "maestro.yaml"
        profile_path.write_text(
            yaml.dump(
                {
                    "profile_id": "maestro",
                    "expected_sections": ["biblical_reading", "lesson_outline"],
                }
            )
        )

    def tearDown(self) -> None:
        """Clean up the temporary directory."""
        self.temp_dir.cleanup()

    def test_summary_report_aggregation(self) -> None:
        """Verify that the summary report aggregates data from other audits."""
        # 1. Create mock audit report files
        (self.root / "reports" / "missing_sections" / "missing_sections.json").write_text(
            json.dumps(
                {
                    "total_missing": 2,
                    "missing_items": [
                        {"missing_section": "lesson_outline"},
                        {"missing_section": "summary_application"},
                    ],
                }
            )
        )
        (
            self.root / "reports" / "title_consistency" / "title_consistency_audit.json"
        ).write_text(json.dumps({"total_inconsistencies": 3}))
        (
            self.root
            / "reports"
            / "low_confidence_scripture"
            / "low_confidence_scripture_audit.json"
        ).write_text(json.dumps({"total_low_confidence": 4}))

        # 2. Create other mock artifacts
        (self.root / "ocr" / "quality_reports" / "test-pub.json").write_text(
            json.dumps(
                {
                    "source": "test-pub",
                    "status": "BLOCKED",
                    "page_count": 10,
                    "issue_counts": {"zero_text": 1},
                }
            )
        )
        (self.root / "normalized" / "maestro" / "test-pub.txt").touch()
        draft_path = self.root / "archive" / "drafts" / "test.yaml"
        draft_path.write_text(
            yaml.dump(
                {
                    "publication_id": "maestro-pub",
                    "processing_audit": {"review_status": "automated_unreviewed"},
                    "lesson_sections": {"biblical_reading": {"items": ["Test"]}},
                }
            )
        )
        (self.root / "indexes" / "provisional" / "lessons_index.yaml").write_text(
            yaml.dump({"index_scope": "automated_unreviewed_draft", "lessons": [{}, {}]})
        )

        # 3. Run the report builder
        report = build_report(self.root)

        # 4. Assert the aggregated results
        # Content Audits
        content_audits = report["content_audits"]
        self.assertEqual(content_audits["missing_sections"]["total_missing"], 2)
        self.assertEqual(
            content_audits["missing_sections"]["critical_missing_count"], 1
        )
        self.assertTrue(content_audits["missing_sections"]["has_critical_gaps"])
        self.assertEqual(content_audits["title_consistency"]["total_inconsistencies"], 3)
        self.assertEqual(
            content_audits["low_confidence_scripture"]["total_low_confidence"], 4
        )

        # OCR Audit
        ocr_audit = report["ocr"]
        self.assertEqual(len(ocr_audit["reports"]), 1)
        self.assertEqual(ocr_audit["reports"][0]["status"], "BLOCKED")

        # YAML Audit
        yaml_audit = report["yaml"]
        self.assertEqual(yaml_audit["draft_yaml_count"], 1)
        self.assertEqual(yaml_audit["canonical_yaml_count"], 0)
        self.assertIn("automated_unreviewed", yaml_audit["review_statuses"])
        self.assertEqual(yaml_audit["missing_sections"]["lesson_outline"], 1)

        # Indexing Audit
        indexing_audit = report["indexing"]
        self.assertEqual(indexing_audit["detailed_lesson_count"], 2)