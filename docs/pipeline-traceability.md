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
  -> archive/drafts/expositor-guia-maestro-volumen-45/YYYY/CYCLE/LES-YYYY-CYCLE-###.yaml
  -> archive/lessons/YYYY/CYCLE/LES-YYYY-CYCLE-###.yaml
  -> indexes/lessons_index.yaml
  -> indexes/scripture_index.yaml
```

Raw text is extracted first and is not overwritten by normalization. The
normalizer writes separate `normalized/*.txt` artifacts that become the only text
input to structure detection. `scripts/canonical/06_yaml_generator.py` writes
draft YAML only. Draft YAML may
contain explicit placeholders and must not be indexed. A lesson becomes
canonical only after placeholders are replaced, source traceability is reviewed,
and the file is promoted into `archive/lessons`.

## Layer Responsibilities

| Layer | Script | Reads | Writes | Trace responsibility |
| --- | --- | --- | --- | --- |
| Pre-ingestion | `00_validate_source_pdf_sync.py` | local source PDFs and Google Drive folder listing | validation result | Confirms local/remote source filenames and sizes match before processing. |
| Pre-ingestion | `00_rename_source_pdfs.py` | source PDF names, metadata, and first pages | stable source PDF filenames when `--apply` is used | Normalizes source filenames before downstream artifact names are derived. |
| Ingestion | `01_pdf_discovery.py` | `source_assets/original_pdfs/*.pdf` | console report, intake log directory | Establishes the immutable source set. |
| Ingestion | `02_pdf_to_raw_text.py` | source PDFs | `ocr/raw_txt/*.txt`, `ocr/processing_logs/*.json` | Preserves page boundaries with `PDF_PAGE` markers, records extraction counts, uses OCR only as fallback, and refuses to overwrite existing raw text. |
| Structuring | `03_minimal_text_normalizer.py` | `ocr/raw_txt/*.txt` | `normalized/*.txt` | First-class stage that keeps page and section markers visible, preserves author wording, and makes prose stable for detection. |
| Structuring | `04_document_structure_detector.py` | `normalized/*.txt` | `structured/document_structure/*.json` | Records marker type, line number, source text path, and `Contenido` expectations after normalization. |
| Structuring | `05_lesson_segmenter.py` | structure JSON | `metadata/lessons/*.json` | Converts source markers into lesson segment records with page/line spans and validation summaries. |
| Canonical | `06_yaml_generator.py` | segment JSON | `archive/drafts/<publication_id>/**/*.yaml` | Serializes draft lesson YAML from lesson segments, never directly from raw text, with explicit review placeholders and path collision protection. |
| Canonical | `07_schema_validator.py` | lesson YAML and schema | validation result | Blocks malformed or placeholder-bearing canonical records. |
| Canonical | `08_index_builder.py` | validated canonical lesson YAML | `indexes/*.yaml` | Builds reference-only indexes after validation passes. |

## What To Check During Review

Start with the source PDF and move forward one layer at a time:

1. Confirm local source PDFs match the Google Drive source folder when a Drive
   source is configured.
2. Confirm source PDFs have stable archive filenames before extraction.
3. Confirm the PDF exists under `source_assets/original_pdfs`.
4. Confirm raw text exists, includes `===== PDF_PAGE N =====` markers, and has not been overwritten by a later stage.
5. Confirm the processing log records the same page count expected from the PDF.
6. Confirm normalized text still includes lesson headers, section labels, page
   markers, Bible-reference-only lines, and preserved author wording.
7. Confirm structure JSON has `markers` and, when available, `content_index`
   entries from the publication's `Contenido` page.
8. Confirm segment metadata includes expected lesson numbers, titles, dates, and
   validation summaries.
9. Confirm generated draft YAML is stored under
   `archive/drafts/<publication_id>/`, not `archive/lessons`.
10. Before promotion, confirm each lesson YAML preserves `source_trace`,
   including page and line spans, `source_integrity`, `processing_audit`, and
   reference-only biblical reading metadata with no `TBD`, `pending-*`, or zero
   scripture placeholder values.

## Deterministic Review Rules

- Prefer source markers over interpretation.
- Preserve author wording; do not rewrite theological content.
- Preserve `PDF_PAGE` markers through normalization and downstream trace fields.
- Do not infer lesson boundaries from topic changes.
- Keep Bible reading text out of canonical YAML and indexes.
- Sort inputs before processing so reruns remain stable.
- Preserve relative paths when writing artifacts so parallel collections cannot
  overwrite one another.
- Treat `metadata/lessons/*.json` as intermediate data, not canonical truth.
- Treat `archive/drafts/**/*.yaml` as generated scaffold data, not canonical
  truth.
- Treat `ExpositorMain/outputs/**` as legacy generated output, not canonical
  truth.
- Build indexes only from reviewed files under `archive/lessons`.

## Common Mismatch Points

- A scanned PDF may still have low or empty trusted text when OCR fallback is
  unavailable or when fallback OCR returns `NEEDS_HUMAN_REVIEW`.
- A missing `Contenido` page means segmentation falls back to explicit
  `LECCION X` markers.
- If normalized text accidentally merges a section label into paragraph prose,
  structure detection may miss that label.
- If a lesson header appears in decorative front matter, the segmenter may
  report it as an unexpected observed header until richer source rules are
  added.
