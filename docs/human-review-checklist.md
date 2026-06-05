# Human Review Checklist

Use this checklist before any generated draft lesson YAML is promoted from
`archive/drafts` to `archive/lessons`.

## Reviewer Requirements

A reviewer must have access to the source PDF and the generated pipeline
artifacts for the lesson being reviewed. The reviewer must be able to compare
canonical YAML values against source evidence and run the validation commands in
this repository.

Record the reviewer in `processing_audit.reviewed_by` and mark
`processing_audit.review_status` with a reviewed value before promotion.

## Source And Traceability

- The source PDF exists under `source_assets/original_pdfs`.
- The source filename in YAML matches the source file.
- Source hash or source integrity metadata is populated with reviewed values.
- `source_trace.source_pdf` points to the correct source PDF.
- `source_trace.page_start` and `source_trace.page_end` match the lesson span.
- `source_trace.line_start`, `source_trace.line_end`, or `extraction_block`
  values are explainable from intermediate artifacts.

## OCR And Extraction Quality

- The processing log page count matches the PDF page count.
- No zero-text page affects the lesson content.
- Low-word-count pages are explained.
- OCR fallback pages, if any, are reviewed.
- Malformed references such as merged book names and chapter numbers are fixed.
- Layout artifacts such as `/ / / fecha sugerida` are removed from canonical
  content unless intentionally preserved as source evidence.
- Header, footer, page number, and decorative text contamination are removed
  from lesson sections.

## Lesson Identity

- `lesson_id` is stable and follows the repository naming pattern.
- `publication_id`, `collection_type`, `year`, and `cycle` are correct.
- `lesson_number` matches the source lesson number.
- `title` matches the source title.
- `page_range.start` and `page_range.end` match the reviewed lesson span.
- `language` is correct.

## Required Lesson Sections

- `lesson_header.marker` and `lesson_header.lesson_number` are correct.
- `title.text` matches the source lesson title.
- `biblical_reading.reference_display` is the source reading reference.
- `biblical_reading.canonical_references` are normalized.
- `lesson_outline.items` contains reviewed outline content.
- `teacher_notes.items` contains reviewed teacher notes.
- `summary_application.items` contains reviewed summary/application content.

## Biblical Reading Policy

- Canonical YAML does not store Bible passage text.
- `replacement_policy.provider` is `api.bible`.
- `replacement_policy.strategy` is `replace_by_canonical_reference`.
- `replacement_policy.source_text_included` is `false`.
- Scripture chapters and verses are positive integers.
- Multi-reference strings are split into separate normalized references where
  needed.

## Placeholder Check

Canonical YAML must not contain:

- `TBD`
- `pending`
- `pending-*`
- `placeholder-*`
- `minimal-valid-placeholder`
- `manual-placeholder`
- `pending-source-hash`
- `pending-block-id`
- `chapter: 0`
- `verse_start: 0`
- `verse_end: 0`

## Final Reviewer Actions

1. Confirm all checklist items above are complete.
2. Move the reviewed file into `archive/lessons`.
3. Run:

```text
python scripts/canonical/07_schema_validator.py
```

4. Regenerate indexes only after validation passes:

```text
python scripts/canonical/08_index_builder.py
```
