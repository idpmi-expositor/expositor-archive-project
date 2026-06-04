# Lesson YAML Contract

Each canonical YAML file represents exactly one lesson. A lesson may preserve
additional source sections, but it must contain at least these normalized
sections:

- `lesson_header`
- `title`
- `biblical_reading`
- `lesson_outline`
- `teacher_notes`
- `summary_application`

The source section `Lectura Biblica` must be stored as a reference only. The
archive does not store or translate Bible text. Future downstream systems can
replace Bible text using `api.bible` or another provider through the normalized
reference metadata.

## Validation

The contract is enforced by:

- `schemas/base/lesson_schema.yaml`
- `scripts/canonical/07_schema_validator.py`

Run validation from the repository root:

```text
python scripts/canonical/07_schema_validator.py
```

Validation is intentionally a canonical-layer gate. Earlier artifacts may be
partial or intermediate, but lesson YAML under `archive/lessons` must satisfy
this contract before indexes are generated.

## Indexing

The index builder reads canonical lesson YAML and writes:

- `indexes/lessons_index.yaml`
- `indexes/scripture_index.yaml`

Run index generation from the repository root:

```text
python scripts/canonical/08_index_builder.py
```

The indexes preserve the same rule as canonical YAML: references are indexed,
but Bible passage text is not stored.

## Contenido Validation Source

For Expositor source PDFs that include a `Contenido` section, the structuring
layer reads PDF page 5 and extracts lesson expectations:

```yaml
content_index:
  - lesson_number: 1
    title: La fe que transforma la conducta y pensamientos del creyente
    page_start: 6
    lesson_date: 03/mar/24
    source_pdf_page: 5
```

Future canonical YAML generation should compare each lesson against this source
index:

- `lesson_number` must match the `Contenido` entry.
- `title` must match the `Contenido` title.
- `page_range.start` must match the `Contenido` page start.
- `source_trace.page_start` should remain explainable from the extracted page
  marker or source `Contenido` page value.

Example shape:

```yaml
---
schema_version: "1.0.0"
lesson_id: LES-2026-C1-001
publication_id: EXP-MAESTRO-2026-C1
collection_type: maestro
year: 2026
cycle: C1
lesson_number: 1
title: La fe que transforma la conducta y pensamientos del creyente
subtitle:
language: es
page_range:
  start: 1
  end: 4
lesson_sections:
  lesson_header:
    marker: LECCION 1
    lesson_number: 1
  title:
    text: La fe que transforma la conducta y pensamientos del creyente
  biblical_reading:
    reference_display: Santiago 2:14-24
    replacement_policy:
      provider: api.bible
      strategy: replace_by_canonical_reference
      source_text_included: false
    canonical_references:
      - testament: new
        book_standardized: Santiago
        chapter: 2
        verse_start: 14
        verse_end: 24
  lesson_outline:
    items:
      - marker: I
        title: Justificados pues por la fe en Cristo
        reference_display: Romanos 3:28; 5:1-5
        children:
          - marker: A
            title: Justificados por la fe sin las obras de la Ley
            reference_display: Romanos 3:28
          - marker: B
            title: Estamos completos en Cristo
            reference_display: Romanos 5:1-5
      - marker: II
        title: Una fe carente de significado
        reference_display: Santiago 2:14-20
      - marker: III
        title: Las obras y la justificacion por la fe en Cristo
        reference_display: Santiago 2:21-24
      - marker: IV
        title: Resumen y aplicacion practica
  teacher_notes:
    items:
      - De que aprovechara si alguno dice que tiene fe, pero no tiene obras?
      - Puede la fe sin obras justificar al creyente?
  summary_application:
    items:
      - Extracted from the source section when present.
processing_audit:
  intake_date: 2026-05-29
  ocr_engine: manual-placeholder
  ocr_engine_version: not-applicable
  extraction_method: manual-entry
  extraction_confidence: 1.0
  manual_review_required: true
  reviewed_by: pending-review
  review_status: pending
source_integrity:
  original_filename: source-publication.pdf
  sha256: pending-source-hash
  imported_at: 2026-05-29
  source_scan_quality: pending-review
processing_status:
  intake_completed: false
  ocr_completed: false
  metadata_extracted: false
  semantic_indexed: false
  human_review_completed: false
  yaml_generated: true
  validated: false
source_trace:
  source_pdf: source_assets/original_pdfs/source-publication.pdf
  page_start: 1
  page_end: 4
  extraction_block: pending-block-id
semantic_metadata:
  doctrinal_categories: []
  theological_themes: []
  educational_level: adult
  intended_audience: maestro
```
