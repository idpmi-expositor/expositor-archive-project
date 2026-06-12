from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = PROJECT_ROOT / "scripts" / "canonical" / "06_yaml_generator.py"
DRIVE_VALIDATOR_PATH = (
    PROJECT_ROOT / "scripts" / "ingestion" / "00_validate_source_pdf_sync.py"
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


generator = load_module("yaml_generator", GENERATOR_PATH)
drive_validator = load_module("drive_validator", DRIVE_VALIDATOR_PATH)


class DraftGenerationTest(unittest.TestCase):
    def test_existing_imported_at_is_preserved_on_regeneration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            input_dir = root / "metadata"
            draft_dir = root / "drafts"
            input_dir.mkdir()
            segment_file = input_dir / "expositor-guia-maestro-volumen-45.json"
            segment_file.write_text(
                json.dumps(
                    {
                        "source_structure": (
                            "structured/document_structure/"
                            "expositor-guia-maestro-volumen-45.json"
                        ),
                        "segments": [
                            {
                                "lesson_number": 1,
                                "start_line": 10,
                                "end_line": 20,
                                "page_start": 6,
                                "page_end": 13,
                                "expected_title": "Lesson title",
                                "lesson_date": "03/mar/24",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            output_path = (
                draft_dir
                / "expositor-guia-maestro-volumen-45"
                / "2024"
                / "C1"
                / "LES-2024-C1-001.yaml"
            )
            output_path.parent.mkdir(parents=True)
            output_path.write_text(
                yaml.safe_dump(
                    {
                        "processing_audit": {
                            "intake_date": "2026-06-06T15:27:09+00:00"
                        },
                        "source_integrity": {
                            "imported_at": "2026-06-06T15:27:09+00:00"
                        },
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(
                sys,
                "argv",
                [
                    "06_yaml_generator.py",
                    "--input-dir",
                    str(input_dir),
                    "--draft-dir",
                    str(draft_dir),
                ],
            ):
                self.assertEqual(generator.main(), 0)

            generated = yaml.safe_load(output_path.read_text(encoding="utf-8"))
            self.assertEqual(
                generated["processing_audit"]["intake_date"],
                "2026-06-06T15:27:09+00:00",
            )
            self.assertEqual(
                generated["source_integrity"]["imported_at"],
                "2026-06-06T15:27:09+00:00",
            )


class DriveValidatorConfigTest(unittest.TestCase):
    def test_rclone_config_path_is_passed_through_environment(self) -> None:
        captured = {}

        def fake_run(command, check, capture_output, text, env):
            captured["command"] = command
            captured["env"] = env
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    [{"Name": "source.pdf", "Size": 123, "IsDir": False}]
                ),
                stderr="",
            )

        config_path = Path("local-rclone.conf")
        with patch.object(drive_validator.subprocess, "run", side_effect=fake_run):
            entries = drive_validator.remote_pdf_entries(
                "gdrive:",
                "folder-id",
                config_path,
            )

        self.assertEqual(entries["source.pdf"].size, 123)
        self.assertEqual(captured["env"]["RCLONE_CONFIG"], str(config_path))
        self.assertIn("--drive-root-folder-id", captured["command"])


if __name__ == "__main__":
    unittest.main()
