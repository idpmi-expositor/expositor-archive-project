from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = PROJECT_ROOT / "scripts" / "ingestion" / "ocr_quality_gate.py"


def load_gate_module():
    spec = importlib.util.spec_from_file_location("ocr_quality_gate", GATE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load OCR quality gate from {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = load_gate_module()


class OcrQualityGateTest(unittest.TestCase):
    def test_zero_text_needs_ocr_for_pymupdf(self) -> None:
        result = gate.evaluate_page_text(
            page_number=1,
            text="",
            source="pymupdf",
        )

        self.assertEqual(result.status, gate.QualityStatus.NEEDS_OCR)
        self.assertTrue(result.ocr_required)
        self.assertIn(gate.Issue.ZERO_TEXT, result.issues)

    def test_zero_text_needs_human_review_after_ocr(self) -> None:
        result = gate.evaluate_page_text(
            page_number=1,
            text="",
            source="tesseract",
            ocr_confidence=40,
        )

        self.assertEqual(result.status, gate.QualityStatus.NEEDS_HUMAN_REVIEW)
        self.assertIn(gate.Issue.ZERO_TEXT, result.issues)
        self.assertIn(gate.Issue.LOW_OCR_CONFIDENCE, result.issues)

    def test_clean_pymupdf_text_passes(self) -> None:
        text = (
            "Leccion 4\n"
            "Juan 3:16\n"
            "This lesson explains the passage with enough ordinary words to pass "
            "the deterministic page quality gate without requiring OCR fallback."
        )

        result = gate.evaluate_page_text(
            page_number=2,
            text=text,
            source="pymupdf",
        )

        self.assertEqual(result.status, gate.QualityStatus.PASS)
        self.assertFalse(result.ocr_required)
        self.assertEqual(result.confidence_score, 100)

    def test_short_text_warns_when_not_below_ocr_threshold(self) -> None:
        result = gate.evaluate_page_text(
            page_number=3,
            text="Short lesson note with twelve total words present here today.",
            source="pymupdf",
        )

        self.assertEqual(result.status, gate.QualityStatus.WARNING)
        self.assertFalse(result.ocr_required)
        self.assertIn(gate.Issue.LOW_WORD_COUNT, result.issues)

    def test_spanish_accents_are_counted_as_valid_text(self) -> None:
        text = (
            "Señor Jesús está aquí con la canción y la acción bíblica.\n"
            "La introducción explica cómo el discípulo crece en obediencia, "
            "oración, comunión, enseñanza, carácter, propósito y misión."
        )

        result = gate.evaluate_page_text(
            page_number=4,
            text=text,
            source="pymupdf",
        )

        self.assertEqual(result.status, gate.QualityStatus.PASS)
        self.assertGreaterEqual(result.word_count, 25)
        self.assertGreaterEqual(result.valid_char_ratio, 0.99)

    def test_malformed_scripture_reference_warns(self) -> None:
        text = (
            "Lesson text with sufficient clean surrounding words for evaluation. "
            "Read Juan 3 16 and Romanos 8.28 carefully before answering."
        )

        result = gate.evaluate_page_text(
            page_number=4,
            text=text,
            source="pymupdf",
        )

        self.assertEqual(result.status, gate.QualityStatus.WARNING)
        self.assertIn(gate.Issue.MALFORMED_SCRIPTURE_REFERENCE, result.issues)

    def test_repeated_header_footer_is_flagged_without_rewriting_text(self) -> None:
        pages = [
            gate.evaluate_page_text(
                1,
                "Archive Header\nPage one has enough words for clean passage "
                "evaluation today.\nFooter 1",
                "pymupdf",
            ),
            gate.evaluate_page_text(
                2,
                "Archive Header\nPage two has enough words for clean passage "
                "evaluation today.\nFooter 2",
                "pymupdf",
            ),
            gate.evaluate_page_text(
                3,
                "Archive Header\nPage three has enough words for clean passage "
                "evaluation today.\nFooter 3",
                "pymupdf",
            ),
        ]

        updated = gate.apply_repeated_header_footer_issues(pages)

        self.assertTrue(
            all(gate.Issue.REPEATED_HEADER_FOOTER in page.issues for page in updated)
        )
        self.assertEqual(updated[0].text, pages[0].text)

    def test_ocr_selected_when_pymupdf_requires_ocr_and_ocr_passes(self) -> None:
        pymupdf_result = gate.evaluate_page_text(
            page_number=5,
            text="",
            source="pymupdf",
        )
        ocr_result = gate.evaluate_page_text(
            page_number=5,
            text=(
                "This OCR result contains enough clean words to pass the quality gate "
                "and should replace the empty embedded text extraction.\n"
                "It uses stable deterministic output for the archival ingestion "
                "pipeline today while preserving page order, source provenance, "
                "and review metadata."
            ),
            source="tesseract",
            ocr_confidence=91,
        )

        selected = gate.select_best_page_text(pymupdf_result, ocr_result)

        self.assertEqual(selected.source, "tesseract")
        self.assertEqual(selected.status, gate.QualityStatus.PASS)

    def test_pymupdf_wins_close_confidence_tie(self) -> None:
        pymupdf_result = gate.evaluate_page_text(
            page_number=6,
            text=(
                "This embedded text has enough clean words to pass the quality gate "
                "and should remain preferred when OCR is only slightly higher."
            ),
            source="pymupdf",
        )
        ocr_result = gate.evaluate_page_text(
            page_number=6,
            text=(
                "This OCR text has enough clean words to pass the quality gate "
                "but should not replace embedded text for a close score."
            ),
            source="tesseract",
            ocr_confidence=100,
        )

        selected = gate.select_best_page_text(pymupdf_result, ocr_result)

        self.assertEqual(selected.source, "pymupdf")


if __name__ == "__main__":
    unittest.main()
