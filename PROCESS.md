# Process

This repository turns source PDFs into reviewed, one-lesson-per-file canonical
YAML.

The required flow is:

```text
PDF -> RAW TEXT EXTRACTION -> NORMALIZED TEXT -> DOCUMENT STRUCTURE DETECTION -> LESSON SEGMENTATION -> DRAFT YAML -> HUMAN REVIEW -> CANONICAL YAML -> INDEXES
```

The canonical architecture is staged so no script generates YAML directly from
raw text:

```text
PDF -> RAW TEXT EXTRACTION -> NORMALIZED TEXT -> DOCUMENT STRUCTURE DETECTION -> LESSON SEGMENTATION -> DRAFT YAML -> HUMAN REVIEW -> CANONICAL YAML
```

Draft YAML is an intermediate review artifact, not canonical truth.

## Operating Principles

- Processing must be deterministic and rerunnable from file-based artifacts.
- Every output must remain traceable to the previous layer.
- Raw extracted text is preserved as-is and is not overwritten by normalization.
- Normalization preserves author wording and does not rewrite theological content.
- Human review is required before any draft lesson becomes canonical YAML.
- Canonical YAML under `archive/lessons` is the source of truth.
- UI, publishing, rendering, and AI translation systems are outside this
  repository.

## Pipeline Order

Run commands from the repository root:

```text
python scripts/ingestion/00_validate_source_pdf_sync.py --drive-root-folder-id GOOGLE_DRIVE_FOLDER_ID
python scripts/ingestion/00_rename_source_pdfs.py
python scripts/ingestion/00_rename_source_pdfs.py --apply
python scripts/ingestion/01_pdf_discovery.py
python scripts/ingestion/02_pdf_to_raw_text.py
python scripts/structuring/03_minimal_text_normalizer.py
python scripts/structuring/04_document_structure_detector.py
python scripts/structuring/05_lesson_segmenter.py
python scripts/canonical/06_yaml_generator.py
python scripts/canonical/07_schema_validator.py
python scripts/canonical/08_index_builder.py
```

## Expected Outputs

| Step | Expected output |
| --- | --- |
| Source sync validation | pass/fail comparison of local PDF names and sizes against Google Drive |
| Source PDF rename | stable archive filenames such as `expositor-guia-maestro-volumen-46.pdf` |
| PDF discovery | source discovery report and intake log readiness |
| Raw text extraction | `ocr/raw_txt/*.txt` and `ocr/processing_logs/*.json`; existing raw text is not overwritten |
| Normalization | `normalized/*.txt`; first-class input to structure detection |
| Structure detection | `structured/document_structure/*.json`; reads normalized text |
| Lesson segmentation | `metadata/lessons/*.json`; reads structure JSON |
| Draft generation | `archive/drafts/<publication_id>/**/*.yaml`; reads segment metadata, not raw text |
| Canonical validation | pass/fail result for `archive/lessons/**/*.yaml` |
| Index building | `indexes/lessons_index.yaml` and `indexes/scripture_index.yaml` |

## Review Gates

Do not skip gates. Each layer depends on the previous layer being explainable.

1. Source sync gate: local PDFs under `source_assets/original_pdfs` match the
   configured Google Drive source folder by filename and file size.
2. Source PDF naming gate: PDFs use stable archive filenames before downstream
   artifacts are generated.
3. OCR quality gate: extraction logs and raw text meet
   [docs/ocr-quality-policy.md](docs/ocr-quality-policy.md). OCR is fallback
   only for weak or empty embedded text pages.
4. Normalization gate: `normalized/*.txt` preserves `PDF_PAGE` markers, author
   wording, and theological content while making whitespace stable.
5. Structure gate: page markers, lesson headers, section labels, and
   `Contenido` entries are detected correctly.
6. Segment gate: lesson numbers, titles, page spans, and validation summaries
   are explainable from source evidence.
7. Draft gate: generated YAML stays under `archive/drafts/<publication_id>/`
   and is not indexed.
8. Human review gate: the checklist in
   [docs/human-review-checklist.md](docs/human-review-checklist.md) is complete.
9. Promotion gate: the workflow in
   [docs/draft-to-canonical-promotion.md](docs/draft-to-canonical-promotion.md)
   is complete.
10. Canonical gate: `python scripts/canonical/07_schema_validator.py` passes.
11. Index gate: indexes are regenerated only from reviewed canonical YAML.

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
  `structured/document_structure/*.json` and `metadata/lessons/*.json` before
  generating or promoting YAML.
- Malformed scripture references: do not promote until references are
  normalized into positive chapter and verse integers.
- Merged section labels: fix section extraction or manual canonical content
  before promotion.
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

