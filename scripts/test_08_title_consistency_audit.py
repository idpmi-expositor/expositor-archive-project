"""Tests for the lesson title consistency audit script."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from audit._08_title_consistency_audit import (  # noqa: E402
    find_inconsistencies,
)


class TestTitleConsistencyAudit(unittest.TestCase):
    """Verify title consistency audit for known edge cases."""

    def setUp(self) -> None:
        """Create a temporary directory for mock artifacts."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root_backup = sys.modules[
            "audit._08_title_consistency_audit"
        ].PROJECT_ROOT
        sys.modules["audit._08_title_consistency_audit"].PROJECT_ROOT = Path(
            self.temp_dir.name
        )

    def tearDown(self) -> None:
        """Clean up the temporary directory."""
        self.temp_dir.cleanup()
        sys.modules[
            "audit._08_title_consistency_audit"
        ].PROJECT_ROOT = self.project_root_backup

    def test_title_mismatch_detection(self) -> None:
        """Verify that a title mismatch is correctly detected."""
        root = Path(self.temp_dir.name)
        normalized_dir = root / "normalized" / "maestro"
        structure_dir = root / "structured" / "document_structure" / "maestro"
        segment_dir = root / "metadata" / "lessons" / "maestro"

        normalized_dir.mkdir(parents=True, exist_ok=True)
        structure_dir.mkdir(parents=True, exist_ok=True)
        segment_dir.mkdir(parents=True, exist_ok=True)

        # 1. Create mock normalized text
        normalized_text_path = normalized_dir / "test-pub.txt"
        normalized_text_path.write_text(
            "\n".join(
                [
                    "===== PDF_PAGE 1 =====",
                    "CONTENIDO",
                    "1. Un Titulo Correcto 5",
                    "2. Un Título con Error 10",
                    "",
                    "===== PDF_PAGE 5 =====",
                    "LECCIÓN 1: Un Titulo Correcto",
                    "...",
                    "",
                    "===== PDF_PAGE 10 =====",
                    "LECCIÓN 2: Un Titulo con Typo",
                    "...",
                ]
            ),
            encoding="utf-8",
        )

        # 2. Create mock structure file
        structure_file_path = structure_dir / "test-pub.json"
        structure_file_path.write_text(
            json.dumps(
                {"source_text": str(normalized_text_path.relative_to(root))}
            )
        )

        # 3. Create mock segment file
        segment_file_path = segment_dir / "test-pub.json"
        segment_file_path.write_text(
            json.dumps(
                {
                    "source_structure": str(structure_file_path.relative_to(root)),
                    "segments": [
                        {
                            "lesson_number": 1,
                            "start_line": 7,
                            "page_start": 5,
                            "expected_title": "Un Titulo Correcto",
                        },
                        {
                            "lesson_number": 2,
                            "start_line": 11,
                            "page_start": 10,
                            "expected_title": "Un Título con Error",
                        },
                    ],
                }
            )
        )

        # 4. Run the audit logic
        inconsistencies = find_inconsistencies(segment_file_path, threshold=90)

        # 5. Assert the results
        self.assertEqual(len(inconsistencies), 1)
        mismatch = inconsistencies[0]
        self.assertEqual(mismatch["lesson_number"], 2)
        self.assertEqual(mismatch["expected_title"], "Un Título con Error")
        self.assertEqual(mismatch["observed_title"], "Un Titulo con Typo")