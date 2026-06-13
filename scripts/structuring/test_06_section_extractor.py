"""Tests for the automated section extractor."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from structuring._06_section_extractor import (  # noqa: E402
    extract_sections_for_segment,
    load_json,
    source_text_for_segment_file,
)


class TestSectionExtractor(unittest.TestCase):
    """Verify section extraction for known edge cases."""

    def test_volume_46_lesson_22_extraction(self) -> None:
        """Verify that lesson 22 of volume 46 extracts its core sections.

        This lesson is a known edge case where the "Bosquejo de la lección"
        label is on the same line as the "Lectura Bíblica" reference, which
        previously caused both sections to be missed.
        """
        segment_file_path = (
            PROJECT_ROOT
            / "metadata"
            / "lessons"
            / "maestro"
            / "expositor-guia-maestro-volumen-46.json"
        )
        self.assertTrue(
            segment_file_path.exists(),
            f"Missing required test input: {segment_file_path}",
        )

        metadata = load_json(segment_file_path)
        source_text_path = source_text_for_segment_file(segment_file_path, metadata)
        self.assertTrue(
            source_text_path.exists(),
            f"Missing required source text: {source_text_path}",
        )

        lines = source_text_path.read_text(encoding="utf-8").splitlines()
        lesson_22_segment = next(
            (s for s in metadata["segments"] if s.get("lesson_number") == 22),
            None,
        )
        self.assertIsNotNone(lesson_22_segment, "Lesson 22 segment not found")

        extracted = extract_sections_for_segment(lines, source_text_path, lesson_22_segment)

        self.assertIn("biblical_reading", extracted, "biblical_reading should be extracted")
        self.assertIn("lesson_outline", extracted, "lesson_outline should be extracted")
        self.assertIn(
            "teacher_notes", extracted, "teacher_notes should be extracted"
        )
        self.assertGreater(len(extracted["lesson_outline"]["items"]), 0, "Outline should have items")

    def test_volume_45_lesson_01_summary_extraction(self) -> None:
        """Verify that lesson 1 of volume 45 extracts the summary.

        This is a baseline test to confirm that the improved logic for
        `summary_application` is working for a standard lesson layout.
        """
        segment_file_path = (
            PROJECT_ROOT
            / "metadata"
            / "lessons"
            / "maestro"
            / "expositor-guia-maestro-volumen-45.json"
        )
        self.assertTrue(
            segment_file_path.exists(),
            f"Missing required test input: {segment_file_path}",
        )

        metadata = load_json(segment_file_path)
        source_text_path = source_text_for_segment_file(segment_file_path, metadata)
        self.assertTrue(
            source_text_path.exists(),
            f"Missing required source text: {source_text_path}",
        )

        lines = source_text_path.read_text(encoding="utf-8").splitlines()
        lesson_01_segment = next(
            (s for s in metadata["segments"] if s.get("lesson_number") == 1),
            None,
        )
        self.assertIsNotNone(lesson_01_segment, "Lesson 1 segment not found")

        extracted = extract_sections_for_segment(lines, source_text_path, lesson_01_segment)

        self.assertIn("summary_application", extracted, "summary_application should be extracted")
        self.assertGreater(
            len(extracted["summary_application"].get("items", [])),
            0,
            "Summary/application section should have items",
        )