# OCR Quality Policy

OCR and embedded text extraction are intermediary steps. They are not canonical
truth. A lesson may become canonical only when extraction quality is good enough
to support reviewed source traceability.

## Quality Report Location

Extraction logs are written under:

```text
ocr/processing_logs/
```

Dedicated quality summaries are written under:

```text
ocr/quality_reports/
```

`scripts/ingestion/03_quality_report.py` writes these summaries from processing
logs. A `BLOCKED` report does not prevent draft regeneration, but it must block
canonical promotion until human review resolves the affected pages. The report
format is part of human revision: it should be understandable without reading
Python code.

## Implemented Quality Gate

`scripts/ingestion/02_pdf_to_raw_text.py` evaluates every page before raw text
is accepted by downstream stages. PyMuPDF remains the primary extractor.
Tesseract OCR is attempted only when the embedded text result is marked
`NEEDS_OCR`.

Fallback OCR text is accepted only when the second quality evaluation returns
`PASS` or `WARNING`. Pages that remain unsafe after OCR are marked
`NEEDS_HUMAN_REVIEW` and do not contribute OCR text as trusted lesson content.

## Page Status Values

Use these status values when reporting page-level quality:

- `PASS`: extracted text is complete enough for downstream structuring
- `WARNING`: extraction is usable but needs reviewer attention
- `FAIL`: reserved for future non-OCR fatal errors; the current gate does not
  return this state
- `NEEDS_OCR`: embedded text is absent or too weak and OCR fallback is needed
- `NEEDS_HUMAN_REVIEW`: automated checks cannot determine quality safely

## Blocking Conditions

The affected lesson must not be promoted to canonical YAML when:

- a content page has zero extracted text
- a content page has very low word count without explanation
- lesson headings or section labels are missing from extracted text
- scripture references are malformed or merged into surrounding text
- source paragraphs are merged across unrelated sections
- header, footer, date, or page layout text contaminates lesson sections
- OCR confidence is unavailable or low and no human review has resolved it

## Warning Conditions

These conditions require reviewer attention but may be resolved by source
comparison:

- front matter or final blank pages have low word count
- repeated headers appear inside lesson pages
- decorative separators are present
- page numbers appear near content
- OCR fallback was applied to only part of a lesson

## Minimum Review Checks

For each source PDF:

1. Confirm total extracted page count.
2. Review zero-text pages.
3. Review low-word-count pages.
4. Spot-check section labels in raw and normalized text.
5. Spot-check scripture references in raw and normalized text.
6. Confirm OCR fallback pages, if any, are readable.
7. Record unresolved extraction problems before draft promotion.

## Canonical Promotion Rule

OCR quality is production-ready only when every canonical lesson can be traced
to readable source text or manually reviewed source evidence. Automated
extraction alone is not enough when logs contain blocking conditions.
