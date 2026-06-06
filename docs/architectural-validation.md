# Architectural Validation

Validation date: 2026-06-05

Validated repository state:

```text
commit: fc1867d Add canonical safety gates
canonical_yaml: 0
draft_yaml: 26
official_indexes: 0
```

Current production-readiness verdict: **PARTIALLY**

The repository is safer and architecturally improved after the canonical safety
gate changes. Generated scaffold YAML is now stored under `archive/drafts`,
reviewed canonical YAML belongs under `archive/lessons`, and canonical
validation rejects placeholder values such as `TBD`, `pending-*`,
`minimal-valid-placeholder`, and zero-valued scripture references. Index
generation is also blocked when no reviewed canonical lesson YAML exists.

The repository is not fully production-ready because there is no reviewed
canonical YAML yet, no official retrieval index exists, OCR/layout quality
issues remain, and real section extraction plus scripture normalization are
still pending.

## Evidence Summary

Commands and observed results from the latest validation pass:

```text
python -m unittest discover -s tests
```

Result:

```text
Ran 3 tests
OK
```

```text
python scripts/canonical/07_schema_validator.py
```

Result:

```text
No lesson YAML files found under archive/lessons
```

```text
python scripts/canonical/07_schema_validator.py
```

Draft YAML under `archive/drafts/<publication_id>/` may still contain explicit
review placeholders. It should not be validated as canonical until a reviewed
file is promoted into `archive/lessons`.

Result:

```text
Draft YAML validation fails intentionally because all 26 draft lessons still
contain placeholder scripture metadata such as chapter: 0.
```

```text
python scripts/canonical/08_index_builder.py
```

Result:

```text
No canonical lesson YAML files found under archive/lessons
Index generation stopped because there is no canonical data.
```

Artifact counts:

```text
canonical_yaml: 0
draft_yaml: 26
official_indexes: 0
```

Structure and OCR evidence:

```text
pages: 223
total_words: 97440
zero_word_pages: [1]
low_word_pages_lt20: [(1, 0), (223, 9)]
markers: 469
content_index: 26
page_marker: 223
section_label: 141
lesson_header: 105
segments: 26
missing_observed_headers: []
unexpected_observed_headers: []
```

Known OCR/layout artifacts:

```text
Lectura Biblica: 1Romanos 1:18-25
/ / / fecha sugerida
```

## 1. Architectural Validation

### Findings

The repository has a clear deterministic pipeline architecture organized into
three processing layers:

- `scripts/ingestion`: source discovery and raw text extraction.
- `scripts/structuring`: normalization, structure recognition, and lesson
  segmentation.
- `scripts/canonical`: draft YAML generation, canonical validation, and index
  building.

The repository now has an explicit draft/canonical boundary:

- `archive/drafts`: generated scaffold YAML awaiting review.
- `archive/lessons`: reviewed canonical lesson YAML only.

This separation is a significant architectural improvement because generated
placeholder data can no longer be treated as archival truth.

The validator now blocks placeholder-bearing canonical YAML, and the index
builder refuses to generate official indexes when no reviewed canonical lessons
exist. This prevents incomplete scaffold data from becoming searchable archive
metadata.

### Risks

The repository has no reviewed canonical YAML files. The canonical archive is
therefore structurally prepared but not populated.

The current generator still writes minimal draft YAML with placeholder section
content. That is safe because the files live under `archive/drafts`, but those
drafts cannot become production records until real section extraction and human
review are complete.

The pipeline is still manually orchestrated through individual numbered
scripts. This is readable for maintainers, but it increases the risk of missed
or out-of-order processing steps.

### Recommendations

Add a single orchestration command such as:

```text
python scripts/run_pipeline.py --drive-root-folder-id GOOGLE_DRIVE_FOLDER_ID
```

The orchestrator should run source sync validation, source PDF rename checks,
each processing layer in order, and canonical validation/indexing. It should
stop on failed validation and emit a single pipeline report.

Continue using `archive/drafts/<publication_id>/` for generated output and
reserve `archive/lessons` for reviewed, placeholder-free canonical YAML only.

Add CI checks that verify:

- Draft YAML is not indexed.
- Canonical YAML contains no placeholders.
- Indexes are generated only from reviewed canonical records.
- Generated index files are deterministic.

### Confidence Level

High.

The architecture and current repository state are directly supported by code,
tests, folder layout, validation commands, and generated artifacts.

## 2. Structure Validation

### Repository Structure Findings

The repository organization supports maintainability better than before because
generated draft records and reviewed canonical records now have separate
locations.

Current high-level structure:

```text
source_assets/original_pdfs/
ocr/raw_txt/
ocr/processing_logs/
normalized/
structured/document_structure/
metadata/lessons/
archive/drafts/
archive/lessons/
schemas/base/
indexes/
scripts/
docs/
tests/
```

The module grouping is understandable:

- Ingestion scripts are grouped together.
- Structuring scripts are grouped together.
- Canonical scripts are grouped together.
- Documentation lives under `docs`.
- Tests now exist under `tests`.

### Document Structure Recognition Findings

The new PDF is recognized at the lesson-count level:

- 26 `Contenido` entries were extracted.
- 26 lesson segments were generated.
- No missing observed lesson headers were reported.
- No unexpected observed lesson headers were reported.
- Segment metadata now carries page and line spans.

Example segment metadata:

```text
lesson_number: 1
start_line: 90
end_line: 196
page_start: 6
page_end: 13
```

Final segment evidence:

```text
lesson_number: 26
start_line: 3405
end_line: 3602
page_start: 207
page_end: 223
```

### Weaknesses

`Contenido` detection is still hardcoded to PDF page 5 in
`scripts/structuring/04_document_structure_detector.py`.

This assumption works for the current PDF but is fragile for future
publications, other collections, alternate layouts, or front matter changes.

The system currently recognizes section labels, but it does not yet extract
complete section blocks into canonical YAML fields.

Repeated lesson headers are detected across the document. This is not currently
breaking segmentation because `Contenido` is preferred, but richer logic will be
needed to distinguish primary lesson starts from repeated headers inside lesson
pages.

### Required Improvements

Make `Contenido` detection dynamic:

```text
scan pages 1-10 for CONTENIDO / INDICE
parse the detected contents page
record the detected source page in structure JSON
```

Add real section extraction for:

- `Lectura Biblica`
- `Bosquejo de la Leccion`
- `Notas para el Maestro`
- `Resumen y aplicacion practica`

Carry source traceability for each extracted section:

```yaml
source_trace:
  page_start:
  page_end:
  line_start:
  line_end:
```

### Confidence Level

High.

Structure detection evidence comes from the generated `DocumentStructure` JSON,
lesson metadata JSON, and direct command output.

## 3. Indexing Validation

### Findings

Indexing is safer than before but not retrieval-ready.

There are currently no official index YAML files:

```text
official_indexes: 0
```

This is intentional and correct under the new policy. The index builder refuses
to build indexes when no reviewed canonical YAML exists.

Draft YAML is blocked by validation because it still contains placeholder
scripture fields:

```yaml
reference_display: TBD
canonical_references:
  - testament: TBD
    book_standardized: TBD
    chapter: 0
    verse_start: 0
    verse_end: 0
```

### Risks

The repository currently has no production retrieval surface.

Semantic search, hierarchy-aware retrieval, scripture lookup, and citation
traceability are not ready because reviewed canonical YAML does not exist.

The current draft files contain titles and page ranges, but not enough real
section content or normalized scripture metadata to support reliable retrieval.

### Recommendations

Implement scripture extraction and normalization before regenerating official
indexes.

The scripture parser should support references such as:

```text
Santiago 2:14-24
I Corintios 3:10-19
Exodo 30:14-15; Mateo 17:24-27; 22:17, 19-21
Romanos 1:1-7, 16-17
```

Indexes should remain blocked until:

- `reference_display` is real.
- `canonical_references` are normalized.
- Section metadata is extracted.
- Human review is complete.

### Confidence Level

High.

The index builder behavior and absence of official index YAML files were
verified directly.

## 4. OCR Validation

### Findings

Text extraction successfully produced large raw and normalized text artifacts,
but OCR/layout quality is not production-ready.

Extraction evidence:

```text
pages: 223
total_words: 97440
zero_word_pages: [1]
low_word_pages_lt20: [(1, 0), (223, 9)]
```

Known text issues include malformed references and layout contamination:

```text
Lectura Biblica: 1Romanos 1:18-25
/ / / fecha sugerida
```

There are merged blocks where biblical text, memory verse text, suggested date
text, and lesson prose appear in the same normalized paragraph. This creates
risk for downstream section extraction.

### Root Cause

The current ingestion script uses embedded PDF text extraction through PyMuPDF
and supports Tesseract OCR fallback for pages whose embedded text is empty or
insufficient. Fallback OCR is still gated by deterministic quality checks before
it can become trusted downstream text.

The normalizer reflows text deterministically, but page layout artifacts can
still be merged into prose when the extracted text does not preserve clean
block boundaries.

### Severity

High for production canonical output.

Medium for draft intake, because lesson-level discovery and metadata generation
still work well enough to produce reviewable draft scaffolds.

### Recommendations

Add OCR quality reports under a path such as:

```text
ocr/quality_reports/
```

Each report should flag:

- zero-text pages
- very low word count pages
- malformed scripture references
- layout artifacts such as `/ / / fecha sugerida`
- merged section labels
- probable header/footer contamination

Keep OCR fallback limited to scanned, empty, or low-quality text-layer pages.
Fallback OCR should remain acceptable only when its quality evaluation returns
PASS or WARNING.

Add page-level quality status values:

```text
PASS
WARNING
FAIL
NEEDS_OCR
NEEDS_HUMAN_REVIEW
```

### Confidence Level

Medium-High.

The audit is based on extraction logs and normalized text artifacts, but not a
full visual page-by-page comparison against rendered PDF pages.

## 5. Documentation Validation

### Findings

Documentation is improved. The README, pipeline traceability document, and YAML
contract now explain:

- draft vs canonical YAML
- placeholder blocking
- index blocking
- source traceability expectations
- reviewed canonical promotion requirement

Current documentation files:

```text
README.md
docs/google-drive-sync.md
docs/lesson-yaml-contract.md
docs/master-architecture-specification.md
docs/pipeline-traceability.md
docs/architectural-validation.md
```

### Documentation Gap Closure

The documentation gaps identified during this validation pass are now covered by
dedicated documents:

- `CONTRIBUTING.md`
- `PROCESS.md`
- `INSTALL.md`
- `docs/human-review-checklist.md`
- `docs/draft-to-canonical-promotion.md`
- `docs/ocr-quality-policy.md`
- `docs/production-ready-canonical-yaml.md`

### Documentation Drift

Some architecture documentation still describes target future directories and
indexes such as:

- `topics_index.yaml`
- schema extensions
- semantic indexes
- corrected OCR text

These are appropriate long-term targets, but maintainers should understand
that they are not fully implemented.

### Risks

If these documents drift from the validator or schema, maintainers may follow
outdated review criteria. Treat `schemas/base/lesson_schema.yaml` and
`scripts/canonical/07_schema_validator.py` as the executable source of truth for
canonical YAML requirements.

### Recommendations

Keep `PROCESS.md`, `CONTRIBUTING.md`, `INSTALL.md`, and the focused policy docs
aligned whenever the pipeline, schema, validator, or OCR behavior changes.

### Confidence Level

High.

Documentation was reviewed directly and compared against current code and
artifact behavior.

## Final Validation Matrix

| Validation Area | Status | Risk | Confidence |
| --- | --- | --- | --- |
| Architecture | Warning | Medium | High |
| Structure | Warning | Medium | High |
| Indexing | Fail | High | High |
| OCR | Warning | High | Medium-High |
| Documentation | Warning | Medium | High |

## Final Verdict

Answer: **PARTIALLY**

The repository is partially production-ready after the canonical safety changes.
It is safe enough to continue development because generated placeholder data is
no longer treated as canonical or indexed. It is not ready for production
retrieval or canonical archival use because there are no reviewed canonical
lesson YAML files, no official indexes, unresolved OCR/layout issues, and no
real section or scripture extraction yet.

## Improvement Roadmap

### Stage 1: Safety Gates

Status: Completed.

Completed work:

- Draft YAML is stored under `archive/drafts`.
- Reviewed canonical YAML is reserved for `archive/lessons`.
- Placeholder values are blocked by canonical validation.
- Zero-valued scripture references are blocked.
- Index generation refuses to run without canonical lesson YAML.
- Stale placeholder indexes were removed.
- Focused validator tests were added.

### Stage 2: Dynamic Structure Detection

Status: Required next.

Tasks:

- Replace hardcoded `Contenido` page 5 with dynamic contents-page detection.
- Record detected `Contenido` page in structure JSON.
- Add tests for documents where `Contenido` is not on page 5.

Exit criteria:

- `Contenido` entries are detected from source markers, not fixed page
  assumptions.
- Segment metadata remains stable when front matter shifts.

### Stage 3: Section Extraction

Status: Pending.

Tasks:

- Extract real section blocks from normalized text.
- Populate draft YAML with real biblical reading, outline, teacher notes, and
  summary/application content.
- Preserve page and line spans for each section.

Exit criteria:

- Draft YAML no longer uses `TBD` for core lesson sections.
- Section extraction can be traced to normalized source line ranges.

### Stage 4: Scripture Normalization

Status: Pending.

Tasks:

- Parse Spanish scripture references.
- Normalize book names, chapter numbers, verse ranges, and multi-reference
  strings.
- Populate `canonical_references`.

Exit criteria:

- Draft validation no longer fails on `chapter: 0`.
- Scripture index can be generated from reviewed canonical YAML.

### Stage 5: OCR Quality Gate

Status: In progress.

Tasks:

- Add OCR quality reports.
- Flag zero-text and low-text pages.
- Detect malformed references and layout artifacts.
- Keep OCR fallback gated for scanned, empty, or low-quality pages.

Exit criteria:

- Each PDF has a quality report.
- Low-quality extraction blocks cannot silently become canonical.

### Stage 6: Promotion Workflow

Status: Pending.

Tasks:

- Add a human review checklist.
- Define draft-to-canonical promotion criteria.
- Document who can review, what must be checked, and what validation must pass.

Exit criteria:

- A draft lesson can be promoted into `archive/lessons` with clear evidence.
- Official indexes can be generated from reviewed canonical YAML.

### Stage 7: CI and Orchestration

Status: Pending.

Tasks:

- Add a top-level pipeline runner.
- Add CI checks for validation, placeholder blocking, and index determinism.
- Add regression tests for the current PDF.

Exit criteria:

- One command can run the pipeline safely.
- CI blocks invalid canonical records and stale indexes.
