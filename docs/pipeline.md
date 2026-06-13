# Pipeline

The confirmed archival pipeline is:

```text
PDF
-> raw text extraction
-> normalized text
-> document structure detection
-> lesson segmentation
-> automated section extraction
-> draft YAML
-> human review
-> canonical YAML
```

## Stage Responsibilities

| Stage | Reads | Writes | Rule |
| --- | --- | --- | --- |
| PDF source | `source_assets/original_pdfs/*.pdf` | unchanged source PDFs | Source PDFs are immutable inputs and must not be deleted by pipeline work. |
| Raw text extraction | PDFs | `ocr/raw_txt/*.txt`, `ocr/processing_logs/*.json` | Extract embedded text first, preserve `PDF_PAGE` markers, and do not overwrite existing raw text. OCR is fallback only for weak or empty embedded-text pages. |
| Normalization | `ocr/raw_txt/*.txt` | `normalized/<classification>/*.txt` | First-class stage. Normalize Unicode, line endings, whitespace, and safe hyphen breaks while preserving author wording, theological content, and page markers. |
| Document structure detection | `normalized/<classification>/*.txt` | `structured/document_structure/<classification>/*.json` | Detect page markers, lesson headers, section labels, and `Contenido` rows from normalized text. |
| Lesson segmentation | structure JSON | `metadata/lessons/<classification>/*.json` | Convert detected structure into lesson spans with page and line traceability. |
| Automated section extraction | normalized text plus lesson segment metadata | `metadata/lesson_sections/<classification>/*.json` | Extract unreviewed section content, scripture references, and source traces for draft generation. |
| Draft YAML | segment and section metadata | `archive/drafts/<publication_id>/**/*.yaml` | Drafts are generated scaffolds for review. They are not canonical and must not be indexed. |
| Human review | drafts plus source evidence | reviewed lesson records | Reviewers resolve placeholders, OCR/extraction concerns, scripture references, section content, and traceability. |
| Canonical YAML | reviewed records | `archive/lessons/**/*.yaml` | Canonical only after human review and schema validation. |

## Non-Negotiable Rules

- Do not generate YAML directly from raw text.
- Do not overwrite raw extracted text.
- Preserve `PDF_PAGE` markers so each downstream artifact can be traced back to the source PDF.
- Preserve author wording. Do not rewrite theological content during normalization, structuring, segmentation, or draft generation.
- Treat OCR as extraction-only fallback. Most Expositor PDFs have embedded text after page 1, so OCR should only be attempted for weak or empty text-layer pages.
- Treat `archive/drafts` as generated, non-canonical review material.
- Treat `automated_unreviewed` as a draft revision level, not a shortcut around
  human review.
- Treat `archive/lessons` as canonical only after human review and validation.
- Treat `ExpositorMain/outputs` as legacy/non-canonical generated output, even when it contains files with canonical-looking names.

## Canonical And Legacy Paths

Canonical candidates move through the root repository pipeline paths:

```text
ocr/raw_txt -> normalized/<classification> -> structured/document_structure/<classification> -> metadata/lessons/<classification> -> metadata/lesson_sections/<classification> -> archive/drafts -> archive/lessons
```

`ExpositorMain/outputs` is a duplicate generated tree from the synced source layout. It is retained only as legacy evidence or comparison material. Do not promote from it, validate it as canonical, or build official indexes from it.
