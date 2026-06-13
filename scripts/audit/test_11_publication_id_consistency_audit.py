"""Tests for the publication ID consistency audit script."""

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

from audit._11_publication_id_consistency_audit import (  # noqa: E402
    check_draft_yaml,
    check_metadata_files,
)


class TestPublicationIdConsistencyAudit(unittest.TestCase):
    """Verify publication ID consistency audit logic."""

    def setUp(self) -> None:
        """Create a temporary directory for mock artifacts."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        # Monkey-patch PROJECT_ROOT in the audit script to our temp dir
        self.project_root_backup = sys.modules[
            "audit._11_publication_id_consistency_audit"
        ].PROJECT_ROOT
        sys.modules["audit._11_publication_id_consistency_audit"].PROJECT_ROOT = self.root

    def tearDown(self) -> None:
        """Clean up the temporary directory and restore PROJECT_ROOT."""
        self.temp_dir.cleanup()
        sys.modules[
            "audit._11_publication_id_consistency_audit"
        ].PROJECT_ROOT = self.project_root_backup

    def test_id_mismatch_detection(self) -> None:
        """Verify that path/content mismatches are correctly detected."""
        # 1. Create mock directories
        draft_dir = self.root / "archive" / "drafts"
        lesson_meta_dir = self.root / "metadata" / "lessons"
        section_meta_dir = self.root / "metadata" / "lesson_sections"

        # 2. Create mock draft YAML files (one good, one bad)
        (draft_dir / "pub-a").mkdir(parents=True)
        (draft_dir / "pub-a" / "good.yaml").write_text(
            yaml.dump({"publication_id": "pub-a"})
        )
        (draft_dir / "pub-b").mkdir(parents=True)
        (draft_dir / "pub-b" / "bad.yaml").write_text(
            yaml.dump({"publication_id": "pub-c"})  # Mismatch
        )

        # 3. Create mock lesson metadata files (one good, one bad)
        lesson_meta_dir.mkdir(parents=True)
        (lesson_meta_dir / "pub-d.json").write_text(
            json.dumps({"source_structure": "path/to/pub-d/file.json"})
        )
        (lesson_meta_dir / "pub-e.json").write_text(
            json.dumps({"source_structure": "path/to/pub-f/file.json"})  # Mismatch
        )

        # 4. Create mock section metadata files (one good, one bad)
        section_meta_dir.mkdir(parents=True)
        (section_meta_dir / "pub-g.json").write_text(
            json.dumps({"source_segments": "path/to/pub-g/file.json"})
        )
        (section_meta_dir / "pub-h.json").write_text(
            json.dumps({"source_segments": "path/to/pub-i/file.json"})  # Mismatch
        )

        # 5. Run the audit checks
        draft_mismatches = check_draft_yaml(draft_dir)
        lesson_meta_mismatches = check_metadata_files(
            lesson_meta_dir, "source_structure"
        )
        section_meta_mismatches = check_metadata_files(
            section_meta_dir, "source_segments"
        )

        # 6. Assert the results
        self.assertEqual(len(draft_mismatches), 1)
        self.assertIn("Draft YAML mismatch", draft_mismatches[0])
        self.assertIn("path implies 'pub-b'", draft_mismatches[0])
        self.assertIn("content has 'pub-c'", draft_mismatches[0])

        self.assertEqual(len(lesson_meta_mismatches), 1)
        self.assertIn("Metadata mismatch", lesson_meta_mismatches[0])
        self.assertIn("filename is 'pub-e'", lesson_meta_mismatches[0])
        self.assertIn("source is 'path/to/pub-f/file.json'", lesson_meta_mismatches[0])

        self.assertEqual(len(section_meta_mismatches), 1)
        self.assertIn("Metadata mismatch", section_meta_mismatches[0])
        self.assertIn("filename is 'pub-h'", section_meta_mismatches[0])
        self.assertIn("source is 'path/to/pub-i/file.json'", section_meta_mismatches[0])

```

### How to Run the Test

You can run this new test from your repository root to confirm it works as expected:

```bash
python -m unittest discover -s tests
```

This test will verify that your publication ID consistency audit is functioning correctly, providing another layer of automated quality control for your data pipeline.

<!--
[PROMPT_SUGGESTION]Let's create a CI workflow for GitHub Actions to run all the tests automatically.[/PROMPT_SUGGESTION]
[PROMPT_SUGGESTION]Can you refactor the `10_pipeline_quality_audit.py` script to be more modular?[/PROMPT_SUGGESTION]
-->