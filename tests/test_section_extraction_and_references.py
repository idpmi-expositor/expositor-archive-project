from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARSER_PATH = PROJECT_ROOT / "scripts" / "canonical" / "scripture_reference_parser.py"
EXTRACTOR_PATH = PROJECT_ROOT / "scripts" / "structuring" / "06_section_extractor.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


parser = load_module("scripture_reference_parser_test", PARSER_PATH)
extractor = load_module("section_extractor_test", EXTRACTOR_PATH)


class ScriptureReferenceParserTest(unittest.TestCase):
    def test_parses_spanish_multi_reference_display(self) -> None:
        references = parser.parse_scripture_references(
            "Exodo 30:14-15; Mateo 17:24-27; 22:17, 19-21"
        )

        self.assertEqual(
            references,
            [
                {
                    "testament": "old",
                    "book_standardized": "Exodus",
                    "chapter": 30,
                    "verse_start": 14,
                    "verse_end": 15,
                },
                {
                    "testament": "new",
                    "book_standardized": "Matthew",
                    "chapter": 17,
                    "verse_start": 24,
                    "verse_end": 27,
                },
                {
                    "testament": "new",
                    "book_standardized": "Matthew",
                    "chapter": 22,
                    "verse_start": 17,
                    "verse_end": 17,
                },
                {
                    "testament": "new",
                    "book_standardized": "Matthew",
                    "chapter": 22,
                    "verse_start": 19,
                    "verse_end": 21,
                },
            ],
        )

    def test_parses_roman_numeral_book_prefix(self) -> None:
        references = parser.parse_scripture_references("I Corintios 3:10-19")
        self.assertEqual(references[0]["book_standardized"], "1 Corinthians")


class SectionExtractorTest(unittest.TestCase):
    def test_extracts_lesson_sections_from_segment_span(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            normalized = root / "normalized.txt"
            structure = root / "structure.json"
            segments = root / "segments.json"
            output = root / "sections.json"

            normalized.write_text(
                "\n".join(
                    [
                        "===== PDF_PAGE 6 =====",
                        "LECCIÓN Sample title",
                        "Lectura Bíblica: Isaías 5:1-7; Jeremías 2:21",
                        "Notas para el Maestro",
                        "Pregunta guia",
                        "Introducción a la Lección",
                        "Bosquejo de la Lección",
                        "I. Primer punto",
                        "A. Subpunto",
                        "Resumen y aplicación práctica:",
                        "Resumen final",
                        "Lecturas Diarias",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            structure.write_text(
                json.dumps({"source_text": str(normalized)}),
                encoding="utf-8",
            )
            segments.write_text(
                json.dumps(
                    {
                        "source_structure": str(structure),
                        "segments": [
                            {
                                "lesson_number": 1,
                                "start_line": 1,
                                "end_line": 12,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = extractor.write_section_file(segments, output)

            sections = result["lessons"][0]["sections"]
            self.assertEqual(
                sections["biblical_reading"]["reference_display"],
                "Isaías 5:1-7; Jeremías 2:21",
            )
            self.assertEqual(
                sections["biblical_reading"]["canonical_references"][0][
                    "book_standardized"
                ],
                "Isaiah",
            )
            self.assertEqual(sections["teacher_notes"]["items"], ["Pregunta guia"])
            self.assertEqual(
                sections["lesson_outline"]["items"],
                ["I. Primer punto", "A. Subpunto"],
            )
            self.assertEqual(sections["summary_application"]["items"], ["Resumen final"])


if __name__ == "__main__":
    unittest.main()
