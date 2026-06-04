# Pipeline Traceability

This document explains how to trace one source publication through the current
repository pipeline. It is meant for maintainers reviewing generated artifacts,
debugging a mismatch, or deciding where a future canonical YAML field should
come from.

## Trace Chain

For a source file named `expositor-guia-maestro-volumen-45.pdf`, the expected
artifact chain is:

```text
source_assets/original_pdfs/expositor-guia-maestro-volumen-45.pdf
  -> ocr/raw_txt/expositor-guia-maestro-volumen-45.txt
  -> ocr/processing_logs/expositor-guia-maestro-volumen-45.json
  -> normalized/expositor-guia-maestro-volumen-45.txt
  -> structured/document_structure/expositor-guia-maestro-volumen-45.json
  -> metadata/lessons/expositor-guia-maestro-volumen-45.json
  -> archive/lessons/YYYY/CYCLE/LES-YYYY-CYCLE-###.yaml
  -> indexes/lessons_index.yaml
  -> indexes/scripture_index.yaml
```

The final canonical YAML step is still pending in
`scripts/canonical/06_yaml_generator.py`. Until that generator is implemented,
`metadata/lessons/*.json` is the last automatically produced lesson-level
artifact.

## Layer Responsibilities

| Layer | Script | Reads | Writes | Trace responsibility |
| --- | --- | --- | --- | --- |
| Ingestion | `01_pdf_discovery.py` | `source_assets/original_pdfs/*.pdf` | console report, intake log directory | Establishes the immutable source set. |
| Ingestion | `02_pdf_to_raw_text.py` | source PDFs | `ocr/raw_txt/*.txt`, `ocr/processing_logs/*.json` | Preserves page boundaries with `PDF_PAGE` markers and records extraction counts. |
| Structuring | `03_minimal_text_normalizer.py` | `ocr/raw_txt/*.txt` | `normalized/*.txt` | Keeps page and section markers visible while making prose stable for detection. |
| Structuring | `04_document_structure_detector.py` | `normalized/*.txt` | `structured/document_structure/*.json` | Records marker type, line number, source text path, and `Contenido` expectations. |
| Structuring | `05_lesson_segmenter.py` | structure JSON | `metadata/lessons/*.json` | Converts source markers into lesson segment records and validation summaries. |
| Canonical | `06_yaml_generator.py` | segment JSON | future `archive/lessons/**/*.yaml` | Will serialize one lesson per canonical YAML file. |
| Canonical | `07_schema_validator.py` | lesson YAML and schema | validation result | Blocks malformed canonical records. |
| Canonical | `08_index_builder.py` | validated lesson YAML | `indexes/*.yaml` | Builds reference-only indexes after validation passes. |

## What To Check During Review

Start with the source PDF and move forward one layer at a time:

1. Confirm the PDF exists under `source_assets/original_pdfs`.
2. Confirm raw text exists and includes `===== PDF_PAGE N =====` markers.
3. Confirm the processing log records the same page count expected from the PDF.
4. Confirm normalized text still includes lesson headers, section labels, page
   markers, and Bible-reference-only lines.
5. Confirm structure JSON has `markers` and, when available, `content_index`
   entries from the publication's `Contenido` page.
6. Confirm segment metadata includes expected lesson numbers, titles, dates, and
   validation summaries.
7. Once canonical YAML generation is implemented, confirm each lesson YAML
   preserves `source_trace`, `source_integrity`, `processing_audit`, and
   reference-only biblical reading metadata.

## Deterministic Review Rules

- Prefer source markers over interpretation.
- Do not infer lesson boundaries from topic changes.
- Keep Bible reading text out of canonical YAML and indexes.
- Sort inputs before processing so reruns remain stable.
- Preserve relative paths when writing artifacts so parallel collections cannot
  overwrite one another.
- Treat `metadata/lessons/*.json` as intermediate data, not canonical truth.

## Common Mismatch Points

- A scanned PDF may have low or empty extracted text because OCR fallback is not
  implemented yet.
- A missing `Contenido` page means segmentation falls back to explicit
  `LECCION X` markers.
- If normalized text accidentally merges a section label into paragraph prose,
  structure detection may miss that label.
- If a lesson header appears in decorative front matter, the segmenter may
  report it as an unexpected observed header until richer source rules are
  added.
