# expositor-archive-project

Archival-grade canonical metadata repository for Expositor publications from
Iglesia de Dios Pentecostal M.I.

This repository is reserved for deterministic archival processing only:

PDF -> RAW TEXT -> STRUCTURED DOCUMENT MODEL -> CANONICAL YAML

## Scope

This project preserves and structures lesson-level archival metadata for:

- Expositor Maestro
- Expositor Alumno
- Expositor Joven
- Expositor Adolescente
- Expositor Nino
- Expositor Parvulo

## Boundaries

This project does not include translation, multilingual workflows, publication rendering, HTML generation, PDF generation, EPUB generation, frontend systems, UI systems, or AI translation pipelines.

## Canonical Unit

The only canonical unit of truth is one lesson per YAML file.

## Repository Map

```text
source_assets/original_pdfs/   Immutable input PDFs.
ocr/raw_txt/                   Extracted text with PDF_PAGE markers.
ocr/processing_logs/           Per-PDF extraction audit logs.
normalized/                    Minimally cleaned text for structure detection.
structured/document_structure/ DocumentStructure JSON marker reports.
metadata/lessons/              Intermediate lesson segment metadata.
archive/drafts/                Generated draft lesson YAML awaiting review.
archive/lessons/               Reviewed canonical one-lesson-per-file YAML archive.
schemas/base/                  Validation contracts for canonical YAML.
indexes/                       Generated search/reference indexes.
scripts/                       Deterministic pipeline scripts.
docs/                          Architecture, sync, contract, and trace docs.
```

## Pipeline Layers

- `scripts/ingestion/`: PDF discovery, source validation, intake logging, and raw text extraction.
- `scripts/structuring/`: deterministic cleanup, document structure detection, and lesson segmentation.
- `scripts/canonical/`: canonical YAML generation, schema validation, and index building.

The Python scripts are intentionally documented for maintainers who are still
learning Python. Each script includes:

- a module-level explanation of its pipeline role
- default path configuration near the top of the file
- beginner-oriented comments for the main functions
- explicit notes about what the script must not do

## Architecture Specification

The authoritative project design is maintained in
[`docs/master-architecture-specification.md`](docs/master-architecture-specification.md).

For operational traceability from one PDF through every generated artifact, see
[`docs/pipeline-traceability.md`](docs/pipeline-traceability.md).

## Lesson Segmentation Contract

Canonical lesson YAML must validate the required lesson sections documented in
[`docs/lesson-yaml-contract.md`](docs/lesson-yaml-contract.md). The biblical
reading section is stored as normalized reference metadata only, so downstream
systems can replace Bible text by reference through providers such as api.bible.

Install script dependencies before running extraction, canonical validation, or
index generation:

```text
python -m pip install -r requirements.txt
```

## Current Script Commands

Run these from the repository root.

```text
python scripts/ingestion/01_pdf_discovery.py
python scripts/ingestion/02_pdf_to_raw_text.py
python scripts/structuring/03_minimal_text_normalizer.py
python scripts/structuring/04_document_structure_detector.py
python scripts/structuring/05_lesson_segmenter.py
python scripts/canonical/06_yaml_generator.py
python scripts/canonical/07_schema_validator.py
python scripts/canonical/08_index_builder.py
```

Each script reads from the previous layer and writes to the next layer. The
current pipeline state is:

- `01_pdf_discovery.py` discovers immutable source PDFs.
- `02_pdf_to_raw_text.py` extracts embedded PDF text, applies optional Tesseract
  OCR fallback on weak or empty text-layer pages, preserves page markers, and
  writes page-aware quality logs.
- `03_minimal_text_normalizer.py` preserves structure while reflowing plain prose.
- `04_document_structure_detector.py` detects page markers, section labels,
  lesson headers, and dynamically detected `Contenido` rows.
- `05_lesson_segmenter.py` writes lesson segment metadata with page/line spans,
  validation status, warnings, and errors.
- `06_yaml_generator.py` writes draft lesson YAML under `archive/drafts` while
  preserving placeholders when source evidence is still missing.
- `07_schema_validator.py` validates canonical lesson YAML.
- `08_index_builder.py` validates lessons before writing indexes.

Canonical validation and index building are active only for reviewed lesson
YAML files under `archive/lessons`. Generated scaffold YAML belongs under
`archive/drafts` until placeholders are replaced and human review is complete.

The index builder validates lesson YAML before writing index files. If a lesson
does not satisfy the required root fields, nested metadata fields, lesson
sections, biblical reading replacement policy, or placeholder-free canonical
policy, index generation stops.

For source publications with a `Contenido` section, the structuring layer now
scans normalized text for `CONTENIDO`, `INDICE`, or `ÍNDICE` labels and selects
the strongest deterministic table-of-contents candidate based on lesson/date row
signals. Lesson segmentation uses that source index as the preferred validation
map before falling back to repeated `LECCION X` markers.

## OCR Fallback and Extraction Quality

`02_pdf_to_raw_text.py` uses PyMuPDF text extraction first. If a page has a weak
or empty text layer, the script attempts Tesseract OCR fallback when `Pillow`,
`pytesseract`, and the `tesseract` executable are available.

OCR fallback can be disabled:

```text
python scripts/ingestion/02_pdf_to_raw_text.py --no-ocr-fallback
```

Processing logs include:

- direct text character and word counts
- weak text-layer detection
- OCR attempted/applied flags
- OCR confidence when available
- extraction method per page
- summary lists of weak pages and OCR fallback pages

## Architectural Validation

The full current architectural validation report is maintained in
[`docs/architectural-validation.md`](docs/architectural-validation.md). It
records the latest findings, risks, confidence levels, production-readiness
verdict, and improvement roadmap.

## Paragraph Reflow Check

PDF extraction often hard-wraps normal prose across many short lines. Script
`03_minimal_text_normalizer.py` reflows plain paragraph lines while preserving
structural lines such as lesson headers, section labels, outline markers,
questions, Bible-reference-only lines, dates, and `Contenido` rows.

After changing reflow rules, rerun:

```text
python scripts/structuring/03_minimal_text_normalizer.py
python scripts/structuring/04_document_structure_detector.py
python scripts/structuring/05_lesson_segmenter.py
```

Then inspect a known paragraph, such as `Justificados por la Fe`, to confirm
that prose is joined and lesson structure remains intact.

## Segmentation Validation

`05_lesson_segmenter.py` writes a `validation_summary` containing:

```text
validation_status: pass|warning|error
validation_warnings: []
validation_errors: []
```

Warnings identify review conditions such as missing `Contenido` entries,
missing observed lesson headers, unexpected lesson headers, and duplicate
observed headers. Errors identify blocking conditions such as duplicate
`Contenido` lesson numbers, duplicate generated segments, or no created lesson
segments.

## Index Policy

The generated indexes are reference-oriented:

- `indexes/lessons_index.yaml` lists lesson metadata and the biblical reading
  reference.
- `indexes/scripture_index.yaml` lists normalized scripture references by
  lesson.

Neither index stores Bible passage text. Bible text replacement belongs to a
downstream system that can use the canonical reference metadata with api.bible.
