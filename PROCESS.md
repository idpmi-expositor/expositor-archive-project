# Process

This repository turns source PDFs into reviewed, one-lesson-per-file canonical
YAML.

The required flow is:

```text
PDF -> RAW TEXT EXTRACTION -> NORMALIZED TEXT -> DOCUMENT STRUCTURE DETECTION -> LESSON SEGMENTATION -> SECTION EXTRACTION -> DRAFT YAML -> HUMAN REVIEW -> CANONICAL YAML -> INDEXES
```

The canonical architecture is staged so no script generates YAML directly from
raw text:

```text
PDF -> RAW TEXT EXTRACTION -> NORMALIZED TEXT -> DOCUMENT STRUCTURE DETECTION -> LESSON SEGMENTATION -> SECTION EXTRACTION -> DRAFT YAML -> HUMAN REVIEW -> CANONICAL YAML
```

Draft YAML is an intermediate review artifact, not canonical truth. Human
review may be skipped for pipeline improvement work only when generated files
remain at the `automated_unreviewed` level under `archive/drafts`.

Human revision means the process must remain followable by a maintainer without
Python knowledge: each command should make clear what it reads, what it writes,
whether it can overwrite anything, and what warnings require attention. See
[docs/human-revision-levels.md](docs/human-revision-levels.md).

## Operating Principles

- Processing must be deterministic and rerunnable from file-based artifacts.
- Every output must remain traceable to the previous layer.
- Raw extracted text is preserved as-is and is not overwritten by normalization.
- Normalization preserves author wording and does not rewrite theological content.
- Each Expositor family can require a different structure profile. Classify
  first, then apply the correct profile for structure detection, section
  extraction, YAML shape, and indexing.
- Human review is required before any draft lesson becomes canonical YAML.
- Canonical YAML under `archive/lessons` is the source of truth.
- UI, publishing, rendering, and AI translation systems are outside this
  repository.

## Pipeline Order

Run commands from the repository root:

```text
python scripts/run_pipeline.py --run-tags ingestion,structuring,audit,canonical,indexing
```

To regenerate downstream artifacts from existing raw text without rerunning PDF
extraction:

```text
python scripts/run_pipeline.py --skip-drive-validation --skip-rename --skip-raw-extraction
```

To also write a per-stage timing log under `reports/pipeline_runs`, add
`--write-run-log`.

When the rclone remote is not configured in the default user location, pass the
config file explicitly:

```text
python scripts/ingestion/00_validate_source_pdf_sync.py --rclone-config path/to/rclone.conf --drive-root-folder-id GOOGLE_DRIVE_FOLDER_ID
```

## Expected Outputs

| Step | Expected output |
| --- | --- |
| Source sync validation | pass/fail comparison of local PDF names and sizes against Google Drive |
| Source PDF rename | stable archive filenames such as `expositor-guia-maestro-volumen-46.pdf` |
| PDF discovery | source discovery report and intake log readiness |
| Raw text extraction | `ocr/raw_txt/*.txt` and `ocr/processing_logs/*.json`; existing raw text is not overwritten |
| OCR quality report | `ocr/quality_reports/*.json`; summarizes extraction risk for maintainer review |
| Normalization | `normalized/<classification>/*.txt`; first-class input to structure detection |
| Structure detection | `structured/document_structure/<classification>/*.json`; reads normalized text |
| Lesson segmentation | `metadata/lessons/<classification>/*.json`; reads structure JSON |
| Section extraction | `metadata/lesson_sections/<classification>/*.json`; automated unreviewed section and reference extraction |
| Draft generation | `archive/drafts/<publication_id>/**/*.yaml`; reads segment and section metadata, not raw text |
| Canonical validation | pass/fail result for `archive/lessons/**/*.yaml` |
| Index building | detailed, compact, section-outline, scripture, translation-alignment, and family-specific YAML indexes |
| Quality audit | `reports/audits/pipeline-quality-audit.json` and `.md` |

## Review Gates

Do not skip gates. Each layer depends on the previous layer being explainable.

1. Source sync gate: local PDFs under `source_assets/original_pdfs` match the
   configured Google Drive source folder by filename and file size.
2. Source PDF naming gate: PDFs use stable archive filenames before downstream
   artifacts are generated.
3. OCR quality gate: extraction logs and raw text meet
   [docs/ocr-quality-policy.md](docs/ocr-quality-policy.md). OCR is fallback
   only for weak or empty embedded text pages.
4. Normalization gate: `normalized/<classification>/*.txt` preserves `PDF_PAGE` markers, author
   wording, and theological content while making whitespace stable.
5. Structure gate: page markers, lesson headers, section labels, and
   `Contenido` entries are detected correctly for the identified Expositor
   family profile.
6. Segment gate: lesson numbers, titles, page spans, and validation summaries
   are explainable from source evidence.
7. Automated section gate: extracted sections and references are traceable and
   marked unreviewed.
8. Draft gate: generated YAML stays under `archive/drafts/<publication_id>/`
   and is not indexed.
9. Human review gate: the checklist in
   [docs/human-review-checklist.md](docs/human-review-checklist.md) is complete.
10. Promotion gate: the workflow in
   [docs/draft-to-canonical-promotion.md](docs/draft-to-canonical-promotion.md)
   is complete.
11. Canonical gate: `python scripts/canonical/07_schema_validator.py` passes.
12. Index gate: indexes are regenerated only from reviewed canonical YAML.

## Failure Modes

- Missing or weak raw text: inspect OCR logs. OCR fallback is attempted by
  `02_pdf_to_raw_text.py` when it is enabled and Tesseract tooling is
  available. If fallback is unavailable or insufficient, the affected pages
  require human review.
- Local/Drive source mismatch: sync the missing PDF files, rerun
  `00_rename_source_pdfs.py --apply`, then rerun source sync validation.
- Duplicate generated trees under `ExpositorMain/outputs`: treat that path as
  legacy/non-canonical. Review and promote only from the root pipeline paths.
- Duplicate or conflicting lesson signals: inspect
  `structured/document_structure/<classification>/*.json` and `metadata/lessons/<classification>/*.json` before
  generating or promoting YAML.
- Malformed scripture references: do not promote until references are
  normalized into positive chapter and verse integers.
- Merged section labels: fix section extraction or manual canonical content
  before promotion.
- Automated-unreviewed draft: do not promote until `review_status` is changed
  through human review and `human_review_completed` is true.
- Placeholder values in canonical YAML: validation must fail; keep the file in
  `archive/drafts`.
- Canonical validation failure: `07_schema_validator.py` reports failing files
  and validation errors; indexes must not be generated from those files.
- No canonical lessons: index generation must stop without writing official
  indexes and exit cleanly.

## Draft Promotion Rules

A draft may move from `archive/drafts` to `archive/lessons` only when:

- every required field is populated from source evidence or reviewed metadata
- every placeholder is removed
- OCR quality has passed or is explicitly resolved by human review
- source traceability is preserved
- biblical reading stores references only, not Bible passage text
- canonical scripture references are normalized
- human review is complete
- canonical validation passes

See [docs/production-ready-canonical-yaml.md](docs/production-ready-canonical-yaml.md)
for the exact production-ready criteria.

## Bulk Review and Promotion Workflow

While the pipeline can promote a single lesson, a more efficient workflow is needed to review and promote an entire publication (e.g., 26 lessons) at once. This process ensures consistency and allows for the scalable population of the canonical archive.

The recommended workflow is as follows:

1.  **Run the Full Draft Pipeline**: Ensure that the entire pipeline has been run for the target publication. All draft YAML files must be present under `archive/drafts/<publication_id>/`.

    ```text
    python scripts/run_pipeline.py --run-tags ingestion,structuring,audit,canonical
    ```

2.  **Triage with Audit Reports**: Before diving into individual lessons, a reviewer should consult the main audit reports to identify systemic issues or high-risk lessons.
    - `reports/audits/pipeline-quality-audit.md`: Provides a high-level overview of pipeline health.
    - `ocr/quality_reports/<publication_id>.json`: Details any OCR or text extraction issues that may require closer inspection of the source PDF.

3.  **Systematic Lesson Review**: Working through one publication, review each draft YAML file against the source PDF. It is often efficient to do this in a dedicated branch in version control.
    - For each file in `archive/drafts/<publication_id>/...`, follow the `docs/human-review-checklist.md`.
    - Correct any extraction errors, normalize scripture references, and remove all placeholder values directly in the draft YAML file.
    - Update the `processing_audit` block to reflect the review:
        - Set `review_status` to `human_reviewed`.
        - Set `human_review_completed` to `true`.
        - Set `manual_review_required` to `false`.
        - Add an entry to the `review_history` with the reviewer's identifier and the date.

4.  **Promote Reviewed Files**: Once all lessons for the publication have been reviewed and their YAML files updated, move them from their location under `archive/drafts/` to the corresponding path under `archive/lessons/`. Use `git mv` to preserve file history.

    For example, to promote lessons for `2024/C1` from a specific publication:
    ```bash
    # Ensure the target directory exists
    mkdir -p archive/lessons/2024/C1

    # Move the reviewed YAML files
    git mv archive/drafts/expositor-guia-maestro-volumen-45/2024/C1/*.yaml archive/lessons/2024/C1/
    ```

5.  **Generate Canonical Indexes**: After the files have been moved, run the schema validator and the official index builder. These scripts will now operate on the newly promoted canonical files.

    ```text
    python scripts/canonical/07_schema_validator.py
    python scripts/canonical/08_index_builder.py
    ```
    If validation fails, correct the issues in the files under `archive/lessons/` and rerun the commands until they pass.

6.  **Commit the Changes**: Stage and commit all changes. This includes the moved lesson files (which `git` will see as renames) and the newly generated official indexes under `indexes/`. The commit message should clearly summarize which publication was promoted.
