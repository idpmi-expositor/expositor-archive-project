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
archive/lessons/               Canonical one-lesson-per-file YAML archive.
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

Install script dependencies before running canonical validation or index
generation:

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
- `02_pdf_to_raw_text.py` extracts embedded PDF text and writes page-aware logs.
- `03_minimal_text_normalizer.py` preserves structure while reflowing plain prose.
- `04_document_structure_detector.py` detects page markers, section labels,
  lesson headers, and `Contenido` rows.
- `05_lesson_segmenter.py` writes lesson segment metadata and validation
  summaries.
- `06_yaml_generator.py` documents the future canonical YAML output path but
  intentionally does not serialize lesson YAML yet.
- `07_schema_validator.py` validates canonical lesson YAML.
- `08_index_builder.py` validates lessons before writing indexes.

Canonical validation and index building are active for lesson YAML files that
follow the schema in
[`schemas/base/lesson_schema.yaml`](schemas/base/lesson_schema.yaml).

The index builder validates lesson YAML before writing index files. If a lesson
does not satisfy the required root fields, nested metadata fields, lesson
sections, or biblical reading replacement policy, index generation stops.

For source publications with a `Contenido` section, the structuring layer reads
the table of contents from PDF page 5 and records expected lesson numbers,
titles, dates, and page starts. Lesson segmentation uses that source index as
the preferred validation map before falling back to repeated `LECCION X`
markers.

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

## Index Policy

The generated indexes are reference-oriented:

- `indexes/lessons_index.yaml` lists lesson metadata and the biblical reading
  reference.
- `indexes/scripture_index.yaml` lists normalized scripture references by
  lesson.

Neither index stores Bible passage text. Bible text replacement belongs to a
downstream system that can use the canonical reference metadata with api.bible.
