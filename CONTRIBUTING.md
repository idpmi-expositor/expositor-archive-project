# Contributing

This repository preserves Expositor publications as deterministic archival
metadata. Contributions should keep the pipeline reproducible, traceable, and
separate from downstream publishing or translation systems.
They should also keep the project human-revision friendly: a maintainer should
be able to run and configure scripts from the documented commands without
knowing Python.

## Before You Start

Install the local dependencies and run the current validation commands:

```text
python -m pip install -r requirements.txt
python -m unittest discover -s tests
python scripts/canonical/07_schema_validator.py
```

For setup details, see [INSTALL.md](INSTALL.md). For the full operating
workflow, see [PROCESS.md](PROCESS.md).

## Adding A Source PDF

1. Add immutable source PDFs under `source_assets/original_pdfs`.
2. Run the rename utility in dry-run mode, then apply the stable archive names
   when the proposed names are correct.
3. If the source files also live in Google Drive, validate local/remote sync by
   filename and size before generating downstream artifacts.
4. Run the ingestion and structuring pipeline from the repository root:

```text
python scripts/run_pipeline.py --run-tags ingestion,structuring
```

Use `--rclone-config path/to/rclone.conf` with
`00_validate_source_pdf_sync.py` when the `gdrive` remote is not configured in
the default user rclone location.

5. Review generated raw text, processing logs, quality reports, normalized
   text, structure JSON, lesson segment metadata, and lesson section metadata.

## Generated Drafts

Run draft generation after structuring artifacts exist. Draft generation may use
automated section extraction, but the output remains unreviewed unless a human
explicitly completes the review checklist.

```text
python scripts/canonical/06_yaml_generator.py
```

Generated YAML belongs under `archive/drafts/<publication_id>/`. Draft files
may contain explicit placeholders while source evidence is still missing. Draft
files must not be indexed and must not be treated as canonical records.

When automation has populated section content or scripture references, keep
`processing_audit.review_status: automated_unreviewed`,
`processing_audit.manual_review_required: true`, and
`processing_status.human_review_completed: false` until review is complete.

## Canonical YAML

Reviewed canonical YAML belongs only under `archive/lessons`.

Before adding or changing canonical YAML:

1. Complete the human review checklist in
   [docs/human-review-checklist.md](docs/human-review-checklist.md).
2. Follow the promotion workflow in
   [docs/draft-to-canonical-promotion.md](docs/draft-to-canonical-promotion.md).
3. Confirm the file satisfies
   [docs/production-ready-canonical-yaml.md](docs/production-ready-canonical-yaml.md).
4. Run canonical validation:

```text
python scripts/canonical/07_schema_validator.py
```

Do not commit canonical YAML that contains `TBD`, `pending-*`,
`minimal-valid-placeholder`, `manual-placeholder`, zero-valued scripture
references, or other generated scaffolding values.

## OCR Quality

Inspect OCR and extraction quality before promoting any lesson to canonical
YAML. Follow [docs/ocr-quality-policy.md](docs/ocr-quality-policy.md).

At minimum, check:

- page count and text count consistency in `ocr/processing_logs`
- zero-text and low-text pages
- malformed scripture references
- merged section labels
- header, footer, or layout contamination
- whether OCR fallback was needed and whether it produced acceptable text

## Pull Request Expectations

Keep changes narrowly scoped. A documentation-only change should not modify
generated data unless the documentation change requires it.

For pipeline or schema changes, include:

- the reason for the change
- affected scripts, schemas, and artifact paths
- commands used for validation
- whether the change affects plain-language script operation or canonical
  human review
- any remaining manual review risk

For canonical YAML changes, include:

- the source PDF and lesson numbers reviewed
- OCR quality status
- reviewer identity or review marker
- validator output
- index generation status, when indexes are expected
