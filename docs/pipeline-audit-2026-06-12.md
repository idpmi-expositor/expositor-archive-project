# Pipeline Audit Report

Audit date: 2026-06-12

## Scope

This audit checked the Google Drive source PDFs, ran the current Python pipeline
from existing raw text artifacts, collected errors and warnings, and identifies
the next recommended improvements.

## Commands Run

Google Drive source listing:

```text
rclone --config rclone/rclone.conf lsjson gdrive: --drive-root-folder-id 1LX-wYECeqZVD_Uwe8ZEpfFL9oicVdeG7 --files-only
```

Source PDF sync validation:

```text
python scripts/ingestion/00_validate_source_pdf_sync.py --rclone-config rclone/rclone.conf --drive-root-folder-id 1LX-wYECeqZVD_Uwe8ZEpfFL9oicVdeG7
```

Pipeline regeneration from existing raw text:

```text
python scripts/run_pipeline.py --skip-drive-validation --skip-rename --skip-raw-extraction
```

Validation and checks:

```text
python -m unittest discover -s tests
python scripts/canonical/07_schema_validator.py
python scripts/canonical/08_index_builder.py
python scripts/ingestion/00_rename_source_pdfs.py
```

## Google Drive Source PDF Check

Google Drive is reachable through the project-local rclone config:

```text
rclone/rclone.conf
remote: gdrive:
```

Drive folder checked:

```text
1LX-wYECeqZVD_Uwe8ZEpfFL9oicVdeG7
```

Drive source PDFs found:

| File | Size | Drive ID |
| --- | ---: | --- |
| `expositor-guia-maestro-volumen-45.pdf` | 8,314,666 | `14V88TBMETcPeX5PaXz-uz25lRczqfmI7` |
| `expositor-guia-maestro-volumen-46.pdf` | 5,699,052 | `1lb6vIOz4SfJFyh_ZK9g-LCMobknOBvbf` |

Source validation result:

```text
Source PDF sync validation passed for 2 PDF file(s).
```

## Pipeline Result

The pipeline completed successfully from existing raw extraction artifacts
through draft YAML regeneration.

Raw extraction was intentionally skipped because
`scripts/ingestion/02_pdf_to_raw_text.py` refuses to overwrite existing raw text
artifacts. This is correct archive behavior. To rerun extraction, move or
archive existing `ocr/raw_txt/*.txt` first or run the extractor into a separate
output folder.

Pipeline output summary:

| Artifact | Count |
| --- | ---: |
| Source PDFs | 2 |
| Raw text files | 2 |
| Processing logs | 2 |
| Quality reports | 2 |
| Normalized text files | 2 |
| Structure JSON files | 2 |
| Lesson segment JSON files | 2 |
| Lesson section JSON files | 2 |
| Draft YAML files | 52 |
| Canonical YAML files | 0 |
| Index YAML files | 0 |

## Test And Validation Result

Unit tests:

```text
Ran 18 tests
OK
```

Canonical validation:

```text
No lesson YAML files found under archive/lessons
```

Index builder:

```text
No canonical lesson YAML files found under archive/lessons
Index generation stopped because there is no canonical data.
```

This is expected because the project currently has automated-unreviewed drafts
only. No lesson has been promoted into `archive/lessons`.

## OCR And Extraction Quality Findings

| Publication | Status | Pages | Human-review pages | Warning pages | OCR fallback pages |
| --- | --- | ---: | --- | ---: | --- |
| `expositor-guia-maestro-volumen-45` | `BLOCKED` | 223 | 1 | 178 | 223 |
| `expositor-guia-maestro-volumen-46` | `WARNING` | 220 | none | 177 | none |

Volume 45 issue counts:

```text
zero_text=1
low_word_count=2
low_ocr_confidence=1
malformed_scripture_reference=3
repeated_header_footer=177
```

Volume 46 issue counts:

```text
low_word_count=1
malformed_scripture_reference=3
repeated_header_footer=177
```

Key interpretation:

- Volume 45 is blocked because page 1 has zero text / needs human review.
- Volume 45 also used OCR fallback on page 223.
- Both volumes have widespread repeated header/footer warnings.
- Both volumes still have malformed scripture-reference warnings.
- Draft generation can continue, but canonical promotion must not proceed until
  these quality concerns are resolved or explicitly reviewed.

## Structure And Segmentation Findings

| Publication | Segments | Status | Content entries | Selected content page | Warning |
| --- | ---: | --- | ---: | ---: | --- |
| `expositor-guia-maestro-volumen-45` | 26 | `warning` | 26 | 5 | `DUPLICATE_OBSERVED_LESSON_HEADERS` |
| `expositor-guia-maestro-volumen-46` | 26 | `warning` | 26 | 4 | `DUPLICATE_OBSERVED_LESSON_HEADERS` |

Interpretation:

- Lesson count is correct for both publications.
- Dynamic `Contenido` detection worked, selecting page 5 for volume 45 and page
  4 for volume 46.
- Duplicate observed lesson headers remain a review warning. This likely comes
  from repeated lesson labels in running headers or page layout, not necessarily
  a segmentation failure.

## Automated Section Extraction Coverage

| Publication | Lessons | Biblical reading | Outline | Teacher notes | Summary/application |
| --- | ---: | ---: | ---: | ---: | ---: |
| `expositor-guia-maestro-volumen-45` | 26 | 26 | 26 | 26 | 0 |
| `expositor-guia-maestro-volumen-46` | 26 | 25 | 25 | 26 | 0 |

Critical gaps:

- `summary_application` was not extracted for any lesson in either publication.
- Volume 46 lesson 22 is missing automated `biblical_reading` and
  `lesson_outline`.
- All 52 generated YAML drafts still contain `automated_unreviewed` markers.
- All 52 draft YAML files still contain placeholder or pending review markers.

This is correct for draft status, but it confirms there is no production-ready
canonical YAML yet.

## Source Filename Check

The rename utility was run in dry-run mode. Both source filenames are already
stable:

```text
keep: expositor-guia-maestro-volumen-45.pdf
keep: expositor-guia-maestro-volumen-46.pdf
```

No rename action is needed.

## Main Gaps

1. No canonical lessons exist.
   `archive/lessons` contains no reviewed YAML, so validation and indexing have
   no production data to process.

2. Summary/application extraction is missing.
   The section extractor currently fails to capture `summary_application` for
   all 52 lessons.

3. Volume 46 lesson 22 has missing automated core sections.
   It lacks biblical reading and lesson outline extraction.

4. OCR quality is not promotion-ready.
   Volume 45 is `BLOCKED`; volume 46 is `WARNING`.

5. Repeated header/footer warnings are noisy.
   Both PDFs report 177 repeated header/footer warnings, which may obscure more
   important content-level issues.

6. Drafts still contain placeholders and unreviewed status.
   This is expected, but it means no generated draft should be indexed or
   treated as canonical.

## Recommended Next Actions

### 1. Improve Summary/Application Extraction

Priority: High

Add extraction support for summary/application sections that appear as:

```text
IV. Resumen y aplicación práctica
Resumen y aplicación práctica:
Resumen y aplicacion practica
```

The extractor should handle cases where the summary appears as an outline item
and the actual paragraph follows later in the lesson.

Exit criteria:

- `metadata/lesson_sections/*.json` shows `summary_application` for most or all
  lessons.
- Draft YAML no longer uses `TBD` for `summary_application.items` when source
  text is present.

### 2. Investigate Volume 46 Lesson 22

Priority: High

Inspect the normalized text span for lesson 22 and identify why biblical
reading and outline labels were missed.

Likely causes:

- label merged into surrounding text
- unexpected accent/capitalization/layout variant
- segment boundary starts after the label
- section label exists on prior page or in a non-standard position

Exit criteria:

- Volume 46 lesson 22 has biblical reading and outline metadata, or a documented
  warning explains why extraction cannot be automated.

### 3. Reduce Header/Footer Warning Noise

Priority: Medium-High

The quality gate is flagging repeated header/footer patterns on 177 pages in
each publication. Improve classification so repeated expected labels such as
`Maestro`, page numbers, and lesson headers are grouped into a readable summary
instead of making almost every content page look equally risky.

Exit criteria:

- Quality reports separate severe content risks from layout-noise warnings.
- Reports remain understandable to maintainers without Python knowledge.

### 4. Resolve Volume 45 Blocked OCR Status

Priority: Medium-High

Page 1 is zero-text and blocks the publication. Determine whether page 1 is
front matter with no lesson content or whether it contains meaningful source
evidence.

Exit criteria:

- If page 1 is non-content/front matter, mark the report as resolved with a
  documented non-content-page exception.
- If page 1 contains source evidence, rerun OCR or manually capture the needed
  text evidence.

### 5. Add A Draft Completeness Report

Priority: Medium

Create a script such as:

```text
python scripts/canonical/09_draft_completeness_report.py
```

It should summarize, per lesson:

- missing section fields
- placeholders
- unparsed scripture references
- quality blockers
- segment warnings
- promotion readiness

Exit criteria:

- Maintainers can see which drafts are closest to promotion without grepping
  YAML files.

### 6. Promote One Pilot Lesson Only After Gaps Are Reduced

Priority: Medium

Choose one lesson with:

- quality report not blocked
- biblical reading extracted
- outline extracted
- teacher notes extracted
- summary/application extracted
- no segment errors

Then complete human review and promote only that lesson into `archive/lessons`.

Exit criteria:

- `python scripts/canonical/07_schema_validator.py` passes with one canonical
  lesson.
- `python scripts/canonical/08_index_builder.py` creates initial official
  indexes from reviewed data only.

## Current Production Readiness

Current status: **not production-ready for canonical/index use**.

Current status for development: **good for continued pipeline improvement**.

The project is successfully connected to Google Drive, can regenerate automated
drafts, and has clear safety gates. The next meaningful improvement is not more
repository structure; it is better extraction completeness, clearer quality
signal handling, and one carefully reviewed pilot canonical lesson.
