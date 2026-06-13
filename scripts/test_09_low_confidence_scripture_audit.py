"""Tests for the low-confidence scripture reference audit script."""

from __future__ import annotations

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

from audit._09_low_confidence_scripture_audit import (  # noqa: E402
    find_low_confidence_references,
)


class TestLowConfidenceScriptureAudit(unittest.TestCase):
    """Verify low-confidence scripture audit for known edge cases."""

    def setUp(self) -> None:
        """Create a temporary directory for mock artifacts."""
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        """Clean up the temporary directory."""
        self.temp_dir.cleanup()

    def test_low_confidence_detection(self) -> None:
        """Verify that a low-confidence scripture reference is detected."""
        root = Path(self.temp_dir.name)
        draft_dir = root / "archive" / "drafts"
        draft_dir.mkdir(parents=True, exist_ok=True)

        # 1. Create a mock draft YAML file with one good and one bad reference
        draft_file_path = draft_dir / "test-lesson.yaml"
        mock_lesson = {
            "lesson_id": "TEST-001",
            "publication_id": "test-pub",
            "lesson_sections": {
                "biblical_reading": {
                    "reference_display": "Hechos 10:1-5; Hechos 1l:1-2",
                    "canonical_references": [
                        {
                            "book_standardized": "hechos",
                            "chapter": 10,
                            "verse_start": 1,
                            "verse_end": 5,
                            "confidence_score": 100,
                        },
                        {
                            "book_standardized": "hechos",
                            "chapter": 11,
                            "verse_start": 1,
                            "verse_end": 2,
                            "confidence_score": 85,
                        },
                    ],
                }
            },
        }
        with draft_file_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(mock_lesson, handle)

        # 2. Run the audit logic with a threshold of 95
        low_confidence_items = find_low_confidence_references(
            draft_file_path, threshold=95
        )

        # 3. Assert that only the low-confidence reference was flagged
        self.assertEqual(len(low_confidence_items), 1)
        flagged_item = low_confidence_items[0]
        self.assertEqual(flagged_item["lesson_id"], "TEST-001")
        self.assertEqual(flagged_item["confidence_score"], 85)
        self.assertEqual(flagged_item["parsed_book"], "hechos")
        self.assertEqual(flagged_item["parsed_chapter"], 11)