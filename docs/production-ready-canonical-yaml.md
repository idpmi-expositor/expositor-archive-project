# Production-Ready Canonical YAML

This document defines the exact criteria for a lesson YAML file to be treated as
production-ready canonical archive data.

Production-ready canonical YAML lives under:

```text
archive/lessons/**/*.yaml
```

Generated scaffold YAML under `archive/drafts` is never production-ready.

## Required Validation Command

Run from the repository root:

```text
python scripts/canonical/07_schema_validator.py
```

The command must pass before indexes are generated.

## Required Root Fields

Each canonical lesson must contain non-empty values for:

- `schema_version`
- `lesson_id`
- `publication_id`
- `collection_type`
- `year`
- `cycle`
- `lesson_number`
- `title`
- `language`
- `page_range`
- `lesson_sections`
- `processing_audit`
- `source_integrity`
- `processing_status`
- `source_trace`
- `semantic_metadata`

## Required Nested Fields

`page_range`:

- `start`
- `end`

`processing_audit`:

- `intake_date`
- `ocr_engine`
- `ocr_engine_version`
- `extraction_method`
- `extraction_confidence`
- `manual_review_required`
- `reviewed_by`
- `review_status`

`source_integrity`:

- `original_filename`
- `sha256`
- `imported_at`
- `source_scan_quality`

`processing_status`:

- `intake_completed`
- `ocr_completed`
- `metadata_extracted`
- `semantic_indexed`
- `human_review_completed`
- `yaml_generated`
- `validated`

`source_trace`:

- `source_pdf`
- `page_start`
- `page_end`
- `extraction_block`

`semantic_metadata`:

- `doctrinal_categories`
- `theological_themes`
- `educational_level`
- `intended_audience`

## Required Lesson Sections

`lesson_sections.lesson_header`:

- `marker`
- `lesson_number`

`lesson_sections.title`:

- `text`

`lesson_sections.biblical_reading`:

- `reference_display`
- `canonical_references`
- `replacement_policy`

`lesson_sections.lesson_outline`:

- `items`

`lesson_sections.teacher_notes`:

- `items`

`lesson_sections.summary_application`:

- `items`

## Biblical Reading Criteria

Canonical YAML stores biblical reading references only. It must not store Bible
passage text.

`replacement_policy` must be:

```yaml
provider: api.bible
strategy: replace_by_canonical_reference
source_text_included: false
```

Each item in `canonical_references` must include:

- `testament`
- `book_standardized`
- `chapter`
- `verse_start`
- `verse_end`

`chapter`, `verse_start`, and `verse_end` must be positive integers.

## Placeholder-Free Criteria

Canonical YAML must not contain generated placeholders, including:

- `TBD`
- `pending`
- `pending-*`
- `placeholder-*`
- `minimal-valid-placeholder`
- `manual-placeholder`
- `pending-source-hash`
- `pending-block-id`
- zero-valued scripture references

## Production-Ready Decision

A lesson is production-ready only when all of these are true:

- human review is complete
- OCR quality blockers are resolved
- required fields and sections are populated
- source traceability is preserved
- biblical reading follows the reference-only policy
- scripture references are normalized
- placeholders are absent
- canonical validation passes
- indexes can be generated from `archive/lessons` without reading drafts

