# Install

This project is a Python-based archival processing pipeline. Run all commands
from the repository root unless a document says otherwise.

## Requirements

- Python 3.11 or newer is required.
- Git is required for normal repository work.
- `rclone` is required when validating local source PDFs against the Google
  Drive source folder.
- Tesseract OCR is optional but recommended for scanned or weak text-layer
  pages.

Install Python dependencies:

```text
python -m pip install -r requirements.txt
```

The Python dependency file currently includes:

- `PyYAML` for canonical YAML validation and index writing
- `PyMuPDF` for embedded PDF text extraction
- `Pillow` and `pytesseract` for optional OCR fallback

## Optional OCR Tooling

`scripts/ingestion/02_pdf_to_raw_text.py` uses embedded PDF text extraction
first. When a page has weak or empty embedded text, it can attempt OCR fallback
if these are available:

- `Pillow`
- `pytesseract`
- the `tesseract` executable on the system path

If OCR tooling is unavailable, the script still writes direct extraction
artifacts and quality logs. Weak or empty text-layer pages are recorded with
the OCR unavailable reason and must be reviewed before canonical promotion.

OCR fallback can be disabled:

```text
python scripts/ingestion/02_pdf_to_raw_text.py --no-ocr-fallback
```

## Verify The Setup

Confirm source discovery works:

```text
python scripts/ingestion/01_pdf_discovery.py
```

Run tests:

```text
python -m unittest discover -s tests
```

Run canonical validation:

```text
python scripts/canonical/07_schema_validator.py
```

When no reviewed canonical lesson YAML exists, validation may report:

```text
No lesson YAML files found under archive/lessons
```

That message is acceptable for an empty canonical archive. It is not proof that
draft YAML is production-ready.

## Current Pipeline Commands

Run the pipeline in order:

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

The current scripts are intentionally separate so maintainers can inspect each
layer. For the review and promotion process, see [PROCESS.md](PROCESS.md).

If no reviewed canonical lesson YAML exists yet, `08_index_builder.py` reports
that there is no canonical data and exits cleanly without writing indexes.

