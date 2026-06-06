# expositor-archive-project

Deterministic archival pipeline for converting Expositor lesson PDFs from
Iglesia de Dios Pentecostal M.I. into reviewed canonical lesson YAML.

This repository is limited to archival ETL:

```text
PDF -> RAW TEXT -> STRUCTURED DOCUMENT MODEL -> CANONICAL YAML
```

One reviewed lesson equals one canonical YAML file. Canonical YAML under
`archive/lessons` is the single source of truth for downstream systems.

## Quick Start

Run commands from the repository root.

```text
python -m pip install -r requirements.txt
python scripts/ingestion/01_pdf_discovery.py
python scripts/ingestion/02_pdf_to_raw_text.py
```

Optional setup checks:

```text
python -m unittest discover -s tests
python scripts/canonical/07_schema_validator.py
```

If no reviewed canonical YAML exists yet, the validator may report that no
lesson YAML files were found under `archive/lessons`. That is acceptable for an
empty canonical archive and does not validate draft YAML.

For full setup, including system dependencies, see [INSTALL.md](INSTALL.md).
For the complete operating sequence and review gates, see [PROCESS.md](PROCESS.md).

## Scope

This project preserves and structures lesson-level archival metadata for:

- Expositor Maestro
- Expositor Alumno
- Expositor Joven
- Expositor Adolescente
- Expositor Nino
- Expositor Parvulo

The archive stores source-derived lesson structure, references, metadata,
processing audit information, and traceability. It does not render lessons or
translate lesson content.

## Non-Goals

The repository must not introduce:

- UI systems, frontend applications, dashboards, or administrative screens
- publication rendering, HTML generation, PDF generation, or EPUB generation
- AI or LLM translation pipelines
- multilingual workflow systems
- downstream Bible text replacement implementations
- canonical output formats other than lesson YAML

Downstream systems may consume canonical YAML, but they must not redefine
archival truth inside this repository.

## System Architecture

```text
source_assets/original_pdfs/*.pdf
  |
  |  scripts/ingestion/
  v
ocr/raw_txt/*.txt
ocr/processing_logs/*.json
  |
  |  scripts/structuring/
  v
normalized/*.txt
structured/document_structure/*.json
metadata/lessons/*.json
  |
  |  scripts/canonical/
  v
archive/drafts/<publication_id>/**/*.yaml
  |
  |  human review and promotion
  v
archive/lessons/**/*.yaml
  |
  |  validation before indexing
  v
indexes/lessons_index.yaml
indexes/scripture_index.yaml
```

The core canonical transformation remains:

```text
PDF -> RAW TEXT -> STRUCTURED DOCUMENT MODEL -> CANONICAL YAML
```

Draft YAML is generated scaffold data. It is not canonical and must not be
indexed. Reviewed YAML under `archive/lessons` is canonical only after human
review and schema validation pass.

## Design Principles

- Determinism: identical inputs must produce identical outputs. Scripts should
  avoid randomness, probabilistic classification, and hidden state.
- Traceability: every generated artifact must remain explainable from the
  prior layer and ultimately from the source PDF.
- File-based pipeline state: each stage writes concrete artifacts to stable
  repository paths so maintainers can inspect, diff, rerun, and recover.
- Human review requirements: generated drafts and OCR-derived text are not
  archival truth until a reviewer resolves placeholders and quality issues.
- Canonical YAML as source of truth: downstream systems consume reviewed lesson
  YAML and indexes; they do not replace the archive's canonical records.

## Repository Map

```text
source_assets/original_pdfs/   Immutable input PDFs.
ocr/raw_txt/                   Extracted text with PDF_PAGE markers.
ocr/processing_logs/           Per-PDF extraction audit logs.
normalized/                    Minimally cleaned text for structure detection.
structured/document_structure/ DocumentStructure JSON marker reports.
metadata/lessons/              Intermediate lesson segment metadata.
archive/drafts/                Generated draft lesson YAML awaiting review.
archive/lessons/               Reviewed canonical one-lesson-per-file YAML.
schemas/base/                  Validation contracts for canonical YAML.
indexes/                       Generated reference indexes.
scripts/                       Deterministic pipeline scripts.
docs/                          Architecture, contracts, traceability, and review docs.
tests/                         Unit tests for pipeline behavior.
```

## Pipeline Layers

### Pre-Ingestion

`scripts/ingestion/00_validate_source_pdf_sync.py`

- Compares local source PDF filenames and sizes with a Google Drive source
  folder through `rclone`.
- Read-only gate used when Drive is the source of record.
- Fails before extraction when local and remote source sets do not match.

`scripts/ingestion/00_rename_source_pdfs.py`

- Proposes stable archive filenames from source filenames, metadata, and first
  page text.
- Runs as a dry run by default.
- Renames only when `--apply` is passed and refuses overwrite collisions.

### Ingestion

`scripts/ingestion/01_pdf_discovery.py`

- Discovers immutable source PDFs under `source_assets/original_pdfs`.
- Establishes deterministic source ordering.
- Does not inspect lesson content.

`scripts/ingestion/02_pdf_to_raw_text.py`

- Extracts embedded PDF text with PyMuPDF.
- Preserves page boundaries with deterministic `PDF_PAGE` markers.
- Attempts Tesseract OCR fallback only for weak or empty direct text pages when
  OCR tooling is available.
- Writes raw text and per-page extraction logs.
- Does not infer headings, lesson boundaries, sections, or canonical fields.

### Structuring

`scripts/structuring/03_minimal_text_normalizer.py`

- Normalizes line endings, Unicode, whitespace, and selected OCR hyphen breaks.
- Reflows hard-wrapped prose while preserving structural lines.
- Does not rewrite meaning or perform semantic interpretation.

`scripts/structuring/04_document_structure_detector.py`

- Detects page markers, lesson headers, section labels, and `Contenido` rows.
- Writes DocumentStructure JSON reports.
- Uses deterministic marker rules, not AI or fuzzy semantic inference.

`scripts/structuring/05_lesson_segmenter.py`

- Converts structure markers into lesson segment metadata.
- Prefers source `Contenido` entries when available.
- Falls back to repeated lesson markers when no usable `Contenido` map exists.
- Writes page and line spans plus validation warnings and errors.

### Canonical

`scripts/canonical/06_yaml_generator.py`

- Converts lesson segment metadata into draft lesson YAML.
- Writes only under `archive/drafts/<publication_id>/`.
- Preserves explicit placeholders when source evidence or review data is
  missing.

`scripts/canonical/07_schema_validator.py`

- Validates reviewed canonical YAML under `archive/lessons`.
- Enforces required root fields, nested metadata, lesson sections, scripture
  reference structure, and placeholder-free canonical records.
- Halts with failures when a canonical lesson does not satisfy the contract.

`scripts/canonical/08_index_builder.py`

- Validates canonical lessons before writing indexes.
- Writes `indexes/lessons_index.yaml` and `indexes/scripture_index.yaml`.
- Excludes draft YAML and Bible passage text.

## Current Pipeline Commands

Run the full process in order when source PDFs and review context are ready:

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

Skip the Google Drive validation command only when there is no configured Drive
source to validate against.

## Dependency Summary

- Python 3.11 or newer.
- Python packages listed in `requirements.txt`: PyYAML, PyMuPDF, Pillow, and
  pytesseract.
- Git for repository work.
- `rclone` for Google Drive source sync validation.
- Tesseract executable on the system path for OCR fallback.

Pillow, pytesseract, and Tesseract are required only when OCR fallback is
needed. Without OCR tooling, direct PyMuPDF extraction still runs and records
weak-page review signals.

## Failure Behavior

- Source sync mismatch: `00_validate_source_pdf_sync.py` reports missing files
  or size mismatches and fails before extraction work should proceed.
- Weak or empty text pages: `02_pdf_to_raw_text.py` records weak pages, attempts
  OCR fallback when available, and marks manual review as required.
- OCR unavailable: extraction continues with direct text and records why OCR
  could not run; affected pages must be reviewed before canonical promotion.
- Structuring mismatch: detector and segmenter artifacts record missing,
  duplicate, unexpected, or conflicting lesson markers as warnings or errors.
- Canonical validation failure: `07_schema_validator.py` reports invalid files;
  those files must remain out of the canonical archive until fixed.
- Index validation failure: `08_index_builder.py` validates lessons before
  writing indexes and stops when canonical YAML is malformed or contains
  placeholders.

Generated drafts are expected to be incomplete. Validation and indexes apply to
reviewed canonical YAML under `archive/lessons`, not to draft scaffold files.

## Canonical YAML Contract

Canonical YAML must validate the lesson section contract documented in
[docs/lesson-yaml-contract.md](docs/lesson-yaml-contract.md).

The biblical reading section stores normalized reference metadata only. Bible
passage text is not stored in canonical YAML or generated indexes. A downstream
system may replace Bible text by reference, but that replacement system is
outside this repository.

## Review And Promotion

Use these documents before moving any generated draft into `archive/lessons`:

- [docs/human-review-checklist.md](docs/human-review-checklist.md)
- [docs/draft-to-canonical-promotion.md](docs/draft-to-canonical-promotion.md)
- [docs/ocr-quality-policy.md](docs/ocr-quality-policy.md)
- [docs/production-ready-canonical-yaml.md](docs/production-ready-canonical-yaml.md)

## Architecture References

- [docs/master-architecture-specification.md](docs/master-architecture-specification.md)
- [docs/pipeline-traceability.md](docs/pipeline-traceability.md)
- [docs/lesson-yaml-contract.md](docs/lesson-yaml-contract.md)
- [docs/google-drive-sync.md](docs/google-drive-sync.md)
- [docs/architectural-validation.md](docs/architectural-validation.md)
- [docs/documentation-audit.md](docs/documentation-audit.md)
