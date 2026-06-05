# Process

This repository turns source PDFs into reviewed, one-lesson-per-file canonical
YAML.

The required flow is:

```text
PDF -> RAW TEXT -> STRUCTURED DOCUMENT MODEL -> DRAFT YAML -> REVIEWED CANONICAL YAML -> INDEXES
```

## Pipeline Order

Run commands from the repository root:

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

## Expected Outputs

| Step | Expected output |
| --- | --- |
| PDF discovery | source discovery report and intake log readiness |
| Raw text extraction | `ocr/raw_txt/*.txt` and `ocr/processing_logs/*.json` |
| Normalization | `normalized/*.txt` |
| Structure detection | `structured/document_structure/*.json` |
| Lesson segmentation | `metadata/lessons/*.json` |
| Draft generation | `archive/drafts/**/*.yaml` |
| Canonical validation | pass/fail result for `archive/lessons/**/*.yaml` |
| Index building | `indexes/lessons_index.yaml` and `indexes/scripture_index.yaml` |

## Review Gates

Do not skip gates. Each layer depends on the previous layer being explainable.

1. Source PDF gate: the PDF exists under `source_assets/original_pdfs` and is
   the intended source file.
2. OCR quality gate: extraction logs and raw text meet
   [docs/ocr-quality-policy.md](docs/ocr-quality-policy.md).
3. Structure gate: page markers, lesson headers, section labels, and
   `Contenido` entries are detected correctly.
4. Segment gate: lesson numbers, titles, page spans, and validation summaries
   are explainable from source evidence.
5. Draft gate: generated YAML stays under `archive/drafts` and is not indexed.
6. Human review gate: the checklist in
   [docs/human-review-checklist.md](docs/human-review-checklist.md) is complete.
7. Promotion gate: the workflow in
   [docs/draft-to-canonical-promotion.md](docs/draft-to-canonical-promotion.md)
   is complete.
8. Canonical gate: `python scripts/canonical/07_schema_validator.py` passes.
9. Index gate: indexes are regenerated only from reviewed canonical YAML.

## Failure Modes

- Missing or weak raw text: inspect OCR logs and rerun with OCR fallback if
  tooling is available.
- Malformed scripture references: do not promote until references are
  normalized into positive chapter and verse integers.
- Merged section labels: fix section extraction or manual canonical content
  before promotion.
- Placeholder values in canonical YAML: validation must fail; keep the file in
  `archive/drafts`.
- No canonical lessons: index generation must stop without writing official
  indexes.

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

