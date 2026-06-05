# Draft To Canonical Promotion

Generated YAML starts as draft data. A lesson becomes canonical only after human
review, placeholder removal, validation, and index regeneration.

## Source And Destination

Draft YAML:

```text
archive/drafts/**/*.yaml
```

Reviewed canonical YAML:

```text
archive/lessons/**/*.yaml
```

Do not build official indexes from `archive/drafts`.

## Promotion Steps

1. Select one draft lesson file.
2. Compare the draft against:
   - the source PDF
   - `ocr/raw_txt`
   - `ocr/processing_logs`
   - `normalized`
   - `structured/document_structure`
   - `metadata/lessons`
3. Complete [human-review-checklist.md](human-review-checklist.md).
4. Replace every placeholder with reviewed source-backed values.
5. Normalize biblical reading metadata.
6. Confirm all required canonical sections contain real reviewed content.
7. Confirm source traceability points back to source pages and lines or
   extraction blocks.
8. Move the file from `archive/drafts` to `archive/lessons`.
9. Run canonical validation:

```text
python scripts/canonical/07_schema_validator.py
```

10. If validation passes, rebuild indexes:

```text
python scripts/canonical/08_index_builder.py
```

11. Review generated index diffs before committing.

## Promotion Blockers

Do not promote a draft when:

- any required field is empty
- any placeholder remains
- OCR quality is unresolved
- lesson boundaries are uncertain
- section extraction is incomplete
- scripture references are not normalized
- Bible passage text is stored in canonical YAML
- `processing_status.human_review_completed` is false
- `processing_status.validated` is false
- canonical validation fails

## Review Evidence

Each promoted lesson should be explainable from repository artifacts. A reviewer
should be able to answer:

- Which PDF page range produced this lesson?
- Which normalized line range or extraction block produced each section?
- Which OCR quality warnings were reviewed?
- Which scripture references were normalized?
- Which command validated the final canonical YAML?

