from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = PROJECT_ROOT / "scripts" / "canonical" / "07_schema_validator.py"
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "base" / "lesson_schema.yaml"


def load_validator_module():
    spec = importlib.util.spec_from_file_location("schema_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load validator module from {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_validator_module()
SCHEMA = validator.load_yaml(SCHEMA_PATH)


def valid_lesson() -> dict:
    return {
        "schema_version": "1.0.0",
        "lesson_id": "LES-2024-C1-001",
        "publication_id": "expositor-guia-maestro-volumen-45",
        "collection_type": "Expositor Maestro",
        "year": 2024,
        "cycle": "C1",
        "lesson_number": 1,
        "title": "La fe que transforma la conducta y pensamientos del creyente",
        "language": "es",
        "page_range": {"start": 6, "end": 13},
        "lesson_sections": {
            "lesson_header": {"marker": "Leccion 1", "lesson_number": 1},
            "title": {
                "text": "La fe que transforma la conducta y pensamientos del creyente"
            },
            "biblical_reading": {
                "reference_display": "Santiago 2:14-24",
                "canonical_references": [
                    {
                        "testament": "new",
                        "book_standardized": "Santiago",
                        "chapter": 2,
                        "verse_start": 14,
                        "verse_end": 24,
                    }
                ],
                "replacement_policy": {
                    "provider": "api.bible",
                    "strategy": "replace_by_canonical_reference",
                    "source_text_included": False,
                },
            },
            "lesson_outline": {"items": ["Bosquejo revisado"]},
            "teacher_notes": {"items": ["Notas revisadas"]},
            "summary_application": {"items": ["Resumen revisado"]},
        },
        "processing_audit": {
            "intake_date": "2026-06-05",
            "ocr_engine": "PyMuPDF",
            "ocr_engine_version": "1.27.0",
            "extraction_method": "pdf_text_extraction",
            "extraction_confidence": "reviewed",
            "manual_review_required": True,
            "reviewed_by": "human-reviewer",
            "review_status": "reviewed",
        },
        "source_integrity": {
            "original_filename": "expositor-guia-maestro-volumen-45.pdf",
            "sha256": "40ab0be15cca1b8da3c6d51579262c1e7a46a39c2d2e560f0693ad2be28a0404",
            "imported_at": "2026-06-05",
            "source_scan_quality": "reviewed",
        },
        "processing_status": {
            "intake_completed": True,
            "ocr_completed": True,
            "metadata_extracted": True,
            "semantic_indexed": True,
            "human_review_completed": True,
            "yaml_generated": True,
            "validated": True,
        },
        "source_trace": {
            "source_pdf": "source_assets/original_pdfs/expositor-guia-maestro-volumen-45.pdf",
            "page_start": 6,
            "page_end": 13,
            "extraction_block": "structured/document_structure/expositor-guia-maestro-volumen-45.json",
        },
        "semantic_metadata": {
            "doctrinal_categories": ["fe"],
            "theological_themes": ["justificacion"],
            "educational_level": "adult",
            "intended_audience": "maestro",
        },
    }


class SchemaValidatorTest(unittest.TestCase):
    def assert_validation_error_contains(self, lesson: dict, expected: str) -> None:
        errors = []
        try:
            validator.validate_root_fields(lesson, SCHEMA)
            validator.validate_nested_fields(lesson, SCHEMA)
            validator.validate_lesson_sections(lesson, SCHEMA)
            validator.validate_biblical_reading(lesson, SCHEMA)
            validator.validate_no_placeholders(lesson, "lesson")
        except validator.ValidationError as exc:
            errors = [str(exc)]

        self.assertTrue(errors)
        self.assertIn(expected, errors[0])

    def test_valid_reviewed_lesson_passes(self) -> None:
        lesson = valid_lesson()

        validator.validate_root_fields(lesson, SCHEMA)
        validator.validate_nested_fields(lesson, SCHEMA)
        validator.validate_lesson_sections(lesson, SCHEMA)
        validator.validate_biblical_reading(lesson, SCHEMA)
        validator.validate_no_placeholders(lesson, "lesson")

    def test_rejects_tbd_placeholder(self) -> None:
        lesson = deepcopy(valid_lesson())
        lesson["lesson_sections"]["biblical_reading"]["reference_display"] = "TBD"

        self.assert_validation_error_contains(lesson, "placeholder value")

    def test_rejects_zero_scripture_numbers(self) -> None:
        lesson = deepcopy(valid_lesson())
        lesson["lesson_sections"]["biblical_reading"]["canonical_references"][0][
            "chapter"
        ] = 0

        self.assert_validation_error_contains(lesson, "positive integer")

    def test_rejects_automated_unreviewed_status(self) -> None:
        lesson = deepcopy(valid_lesson())
        lesson["processing_audit"]["review_status"] = "automated_unreviewed"

        self.assert_validation_error_contains(lesson, "placeholder value")


if __name__ == "__main__":
    unittest.main()
