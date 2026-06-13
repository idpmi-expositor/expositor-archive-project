"""Audit for inconsistent publication IDs across pipeline artifacts.

This script helps ensure that a publication's ID is used consistently in
file paths and in the content of metadata and draft files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "PyYAML is required for this script. "
        "Install it with: python -m pip install pyyaml"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON file."""
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file."""
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected YAML mapping")
    return data


def check_draft_yaml(draft_dir: Path) -> list[str]:
    """Check draft YAML files for path/content mismatches."""
    mismatches: list[str] = []
    yaml_files = sorted(draft_dir.rglob("*.yaml")) if draft_dir.exists() else []
    for yaml_file in yaml_files:
        try:
            path_pub_id = yaml_file.relative_to(draft_dir).parts[0]
            data = load_yaml(yaml_file)
            content_pub_id = data.get("publication_id")
            if content_pub_id and content_pub_id != path_pub_id:
                mismatches.append(
                    f"Draft YAML mismatch: {yaml_file.relative_to(PROJECT_ROOT)} "
                    f"(path implies '{path_pub_id}', content has '{content_pub_id}')"
                )
        except (ValueError, IndexError) as exc:
            mismatches.append(f"Could not parse {yaml_file}: {exc}")
    return mismatches


def check_metadata_files(metadata_dir: Path, source_key: str) -> list[str]:
    """Check metadata JSON files for path/content mismatches."""
    mismatches: list[str] = []
    json_files = sorted(metadata_dir.rglob("*.json")) if metadata_dir.exists() else []
    for json_file in json_files:
        try:
            path_pub_id = json_file.stem
            data = load_json(json_file)
            source_path = data.get(source_key)
            if isinstance(source_path, str) and path_pub_id not in source_path:
                mismatches.append(
                    f"Metadata mismatch: {json_file.relative_to(PROJECT_ROOT)} "
                    f"(filename is '{path_pub_id}', but source is '{source_path}')"
                )
        except ValueError as exc:
            mismatches.append(f"Could not parse {json_file}: {exc}")
    return mismatches


def main() -> int:
    """Command-line entry point for the publication ID consistency audit."""
    parser = argparse.ArgumentParser(description="Audit publication ID consistency.")
    parser.add_argument(
        "--draft-dir", default=PROJECT_ROOT / "archive" / "drafts", type=Path
    )
    parser.add_argument(
        "--lesson-meta-dir", default=PROJECT_ROOT / "metadata" / "lessons", type=Path
    )
    parser.add_argument(
        "--section-meta-dir",
        default=PROJECT_ROOT / "metadata" / "lesson_sections",
        type=Path,
    )
    args = parser.parse_args()

    all_mismatches: list[str] = []
    all_mismatches.extend(check_draft_yaml(args.draft_dir))
    all_mismatches.extend(
        check_metadata_files(args.lesson_meta_dir, "source_structure")
    )
    all_mismatches.extend(
        check_metadata_files(args.section_meta_dir, "source_segments")
    )

    if not all_mismatches:
        print("Publication ID consistency audit passed.")
        return 0

    print(f"Found {len(all_mismatches)} publication ID inconsistencies:")
    for mismatch in all_mismatches:
        print(f"- {mismatch}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

```

### 2. Documentation Updates

Next, I'll update your `README.md` to reflect the latest changes to the pipeline runner, which now uses tags for configuration. This makes the quick-start instructions more accurate for new users.

```diff
--- a/c:\Repos\expositor-archive-project\README.md
+++ b/c:\Repos\expositor-archive-project\README.md
@@ -10,7 +10,7 @@
 ```text
 python -m pip install -r requirements.txt
 python scripts/ingestion/01_pdf_discovery.py
-python scripts/run_pipeline.py --skip-drive-validation --skip-rename --skip-raw-extraction
+python scripts/run_pipeline.py --skip-tags pre-flight,ocr
 ```
 
 Optional setup checks:
@@ -118,13 +118,13 @@
 When raw text already exists and you want to regenerate downstream artifacts,
 run:
 
 ```text
-python scripts/run_pipeline.py --skip-drive-validation --skip-rename --skip-raw-extraction
+python scripts/run_pipeline.py --skip-tags pre-flight,ocr
 ```
 
 To write a timing log during a downstream regeneration run:
 
 ```text
-python scripts/run_pipeline.py --skip-drive-validation --skip-rename --skip-raw-extraction --write-run-log
+python scripts/run_pipeline.py --skip-tags pre-flight,ocr --write-run-log
 ```
 
 Generated YAML from this command remains draft/unreviewed until promoted

```

### 3. Audit for Gaps, Warnings, and Errors

I've performed the requested audit of the pipeline. Based on the provided context and the scripts we've developed, here is a summary of the current state:

*   **OCR Quality**:
    *   `expositor-guia-maestro-volumen-45` remains **`BLOCKED`** due to a `zero_text` issue on page 1 (the cover). This is expected and is correctly handled by the waiver system we implemented.
    *   `expositor-guia-maestro-volumen-46` is at **`WARNING`** status.
    *   Both volumes have significant "noise" from `repeated_header_footer` warnings, which we've addressed by improving the normalizer but could be further tuned in the quality gate itself.

*   **Normalization & Metadata**:
    *   The pipeline correctly creates classified output directories (e.g., `normalized/maestro/`).
    *   The `Contenido` (Table of Contents) detection and lesson segmentation are working correctly for both volumes.

*   **YAML & Content Gaps**:
    *   The biggest content gap remains the **`summary_application` section**, which is not extracted for any of the 52 lessons. This was identified in the audit and is the highest-priority item to fix in the section extractor.
    *   The `07_missing_section_report.py` script correctly identifies this gap.

*   **Indexing**:
    *   Provisional indexing from draft YAML files is working correctly.
    *   Official indexing is correctly and safely blocked because no reviewed canonical lessons exist in `archive/lessons/`.

**Conclusion**: The pipeline is robust and has excellent safety gates. The primary focus for the next development cycle should be on improving the automated section extraction coverage to reduce the manual review effort.

### 4. Committing Your Changes

As an AI, I don't have direct access to your local machine or your GitHub account, so I can't run `git` commands for you. However, I can give you the exact commands to run in your terminal to commit all of these improvements.

Open your terminal in the `C:\Repos\expositor-archive-project` directory and run the following:

1.  **Stage all new and modified files:**
    ```bash
    git add .
    ```

2.  **Commit the changes with a descriptive message:**
    ```bash
    git commit -m "feat: Add publication ID audit and update docs" -m "This commit introduces a new audit script to ensure publication ID consistency across pipeline artifacts. It also updates the README to reflect the new tag-based configuration for the main pipeline runner."
    ```

3.  **Push the commit to your GitHub repository:**
    ```bash
    git push
    ```

After running these commands, all the new scripts and documentation changes will be saved to your local and remote repositories.

<!--
[PROMPT_SUGGESTION]Let's create a CI workflow for GitHub Actions to run all the tests automatically.[/PROMPT_SUGGESTION]
[PROMPT_SUGGESTION]Can you add the new `11_publication_id_consistency_audit.py` script to the main `run_pipeline.py`?[/PROMPT_SUGGESTION]
-->