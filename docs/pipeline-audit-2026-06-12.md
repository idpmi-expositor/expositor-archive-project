# Pipeline Audit Report

Audit date: 2026-06-12

## Scope

This audit performed the requested no-human-review pipeline run:

1. Confirm Google Drive source PDFs.
2. Clear the Google Drive `outputs` folder.
3. Run the repository pipeline from verified source inputs through draft YAML.
4. Run tests, canonical validation, official index generation, and provisional
   draft index generation.
5. Record errors, warnings, gaps, and recommended next actions.

Important policy note: this run intentionally did **not** complete human review.
Generated YAML remains draft/unreviewed unless a person promotes it into
`archive/lessons`.

Latest complete-cycle rerun result: **PASS FOR PROVISIONAL PIPELINE TESTING,
NOT PASS FOR CANONICAL PRODUCTION**.

The complete cycle can now be tested without human review by using provisional
draft indexes. Official canonical validation and official index generation
remain correctly blocked because no reviewed lessons exist under
`archive/lessons`.

## Commands Run

Google Drive `outputs` listing before cleanup:

```text
C:\Tools\rclone\rclone.exe --config rclone\rclone.conf lsf "gdrive,root_folder_id=18J7kB4mUpNU7J7aPn17xl7SQOSYYyO7n:outputs" --recursive
```

Google Drive `outputs` cleanup:

```text
C:\Tools\rclone\rclone.exe --config rclone\rclone.conf delete "gdrive,root_folder_id=18J7kB4mUpNU7J7aPn17xl7SQOSYYyO7n:outputs"
C:\Tools\rclone\rclone.exe --config rclone\rclone.conf rmdirs "gdrive,root_folder_id=18J7kB4mUpNU7J7aPn17xl7SQOSYYyO7n:outputs" --leave-root
C:\Tools\rclone\rclone.exe --config rclone\rclone.conf lsf "gdrive,root_folder_id=18J7kB4mUpNU7J7aPn17xl7SQOSYYyO7n:outputs" --recursive
```

Pipeline run:

```text
python scripts\run_pipeline.py --drive-root-folder-id 1LX-wYECeqZVD_Uwe8ZEpfFL9oicVdeG7 --rclone-config rclone\rclone.conf --skip-raw-extraction
```

Validation and indexing:

```text
python -m unittest discover -s tests
python scripts\canonical\07_schema_validator.py
python scripts\canonical\08_index_builder.py
python scripts\canonical\08_index_builder.py archive\drafts --output-dir indexes\provisional --allow-unreviewed
```

Raw extraction was skipped because existing raw text artifacts are already
present and the extractor is designed not to overwrite them during a normal
pipeline run. The source PDFs were still validated against Google Drive before
downstream regeneration.

## Google Drive Source PDF Check

Drive source PDF folder:

```text
1LX-wYECeqZVD_Uwe8ZEpfFL9oicVdeG7
```

Validation result:

```text
Source PDF sync validation passed for 2 PDF file(s).
```

Source PDFs:

| File | Local Status |
| --- | --- |
| `expositor-guia-maestro-volumen-45.pdf` | present and matched |
| `expositor-guia-maestro-volumen-46.pdf` | present and matched |

## Google Drive Outputs Cleanup

The Google Drive `outputs` folder under Drive root
`18J7kB4mUpNU7J7aPn17xl7SQOSYYyO7n` was listed before cleanup. It contained old
generated outputs, including normalized text, OCR artifacts, metadata, indexes,
draft YAML, and legacy `archive/lessons` YAML.

The folder contents were deleted and empty directories were removed while
leaving the `outputs` root folder in place.

Verification command after cleanup returned no files.

## Pipeline Result

The downstream pipeline completed successfully from verified source PDFs and
existing raw text artifacts through regenerated draft YAML.

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
| Reviewed canonical YAML files | 0 |
| Official index YAML files | 0 |
| Provisional draft index YAML files | 2 |

Cycle interpretation:

- Full downstream regeneration completed.
- Official canonical validation did not fail on malformed files; it reported
  that there are no reviewed canonical files to validate.
- Official index generation stopped safely because there is no canonical data.
- Provisional draft indexing completed and produced the expected two diagnostic
  index files.

## Test, Validation, And Index Result

Unit tests:

```text
Ran 18 tests
OK
```

Canonical validation:

```text
No lesson YAML files found under C:\Repos\expositor-archive-project\archive\lessons
```

Official index builder:

```text
No canonical lesson YAML files found under C:\Repos\expositor-archive-project\archive\lessons
Index generation stopped because there is no canonical data.
```

Provisional draft index builder:

```text
WARNING: building a provisional index from unreviewed draft YAML. This output is not canonical archive truth.
Indexed 52 lesson YAML file(s).
```

Provisional index outputs:

| File | Scope | Entries |
| --- | --- | ---: |
| `indexes/provisional/lessons_index.yaml` | `automated_unreviewed_draft` | 52 lessons |
| `indexes/provisional/scripture_index.yaml` | `automated_unreviewed_draft` | 91 scripture references |

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

Volume 46 low-word-count detail:

```text
page 110: 13 words
```

Key interpretation:

- Volume 45 remains blocked because page 1 has zero text / needs human review.
- Volume 45 used OCR fallback on page 223.
- Volume 46 has a low-word-count warning on page 110.
- Both volumes still have widespread repeated header/footer warnings.
- Both volumes still have malformed scripture-reference warnings.
- Draft generation can continue, but canonical promotion should remain blocked
  until these quality concerns are resolved or explicitly reviewed.

## Structure And Segmentation Findings

| Publication | Segments | Result |
| --- | ---: | --- |
| `expositor-guia-maestro-volumen-45` | 26 | completed |
| `expositor-guia-maestro-volumen-46` | 26 | completed |

Interpretation:

- Lesson count is correct for both publications.
- Segmentation produced 52 total lesson draft inputs.
- Repeated lesson headers remain a known layout warning in the broader quality
  audit, but they did not prevent segmentation.

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
- Draft YAML can now be indexed provisionally, but it is not canonical.

## Main Gaps

1. No reviewed canonical lessons exist.
   `archive/lessons` contains no reviewed YAML, so official validation and
   official indexing still have no production data to process.

2. Provisional indexing now exists, but it is intentionally not canonical.
   `indexes/provisional` can support pipeline diagnostics and review planning,
   but should not be used as the public archive retrieval surface.

3. Summary/application extraction is missing.
   The section extractor currently fails to capture `summary_application` for
   all 52 lessons.

4. Volume 46 lesson 22 has missing automated core sections.
   It lacks biblical reading and lesson outline extraction.

5. OCR quality is not promotion-ready.
   Volume 45 is `BLOCKED`; volume 46 is `WARNING`.

6. Repeated header/footer warnings are noisy.
   Both PDFs report 177 repeated header/footer warnings, which may obscure more
   important content-level issues.

7. Drafts still contain placeholders and unreviewed status.
   This is expected for no-human-review output, but it is the reason official
   validation and official indexes must remain blocked.

## Recommended Next Actions

### Highest Priority

1. Improve `summary_application` extraction.
   This is the largest content gap because it affects all 52 lessons.

2. Add a missing-section report.
   A normal reviewer should be able to open one report and see exactly which
   lessons need attention and why.

3. Resolve volume 45 `BLOCKED` OCR status.
   Page 1 needs visual/source confirmation or an explicit documented waiver.

4. Keep provisional indexes separate from official indexes.
   The new `--allow-unreviewed` path is useful for audit, but official indexes
   should still require reviewed canonical YAML.

### Medium Priority

5. Reduce repeated-header/footer warning noise.
   The quality report should separate true blockers from expected layout
   repetition.

6. Fix volume 46 lesson 22 extraction.
   This is the only lesson currently missing both biblical reading and outline.

7. Add CI for tests and validation.
   GitHub should run tests and confirm official indexes cannot be built from
   unreviewed drafts.

### Later Priority

8. Promote a small reviewed pilot set into `archive/lessons`.
   Use one or two human-reviewed lessons to prove canonical validation and
   official index generation end to end.

9. Add Drive output publishing as a documented command.
   The project should document exactly which local folders are copied to Drive
   `outputs` after an audit run.

## Next Steps Workflow To Fix Audit Gaps

This workflow is ordered so each step creates evidence for the next step. It
keeps the useful no-human-review cycle available for engineering tests, while
still protecting official canonical YAML and official indexes from unreviewed
content.

### Phase 1: Make Gaps Easy To Review

Goal: produce one plain-language report that a non-Python reviewer can follow.

Recommended work:

1. Add a missing-section report script.
   The report should read `metadata/lesson_sections` and list every lesson
   missing `biblical_reading`, `lesson_outline`, `teacher_notes`, or
   `summary_application`.

2. Save the report under:

```text
reports/missing_sections/
```

3. Include the source file, lesson number, missing field, source page range,
   and a suggested reviewer action.

Exit criteria:

- The report identifies all 54 missing section items currently known:
  52 missing `summary_application` values, plus volume 46 lesson 22 missing
  `biblical_reading` and `lesson_outline`.
- The report can be read without Python knowledge.

### Phase 2: Fix Summary/Application Extraction

Goal: reduce the largest extraction gap before any human review pilot.

Recommended work:

1. Inspect normalized text around the end of several lessons where
   `Resumen y aplicacion practica` or equivalent closing material should
   appear.

2. Update `scripts/structuring/06_section_extractor.py` to support:
   accent variations, capitalization variations, line breaks inside labels,
   and alternate labels that mean summary/application.

3. Add tests for at least:
   one volume 45 lesson, one volume 46 lesson, and one missing-label case.

4. Rerun:

```text
python scripts\run_pipeline.py --drive-root-folder-id 1LX-wYECeqZVD_Uwe8ZEpfFL9oicVdeG7 --rclone-config rclone\rclone.conf --skip-raw-extraction
python scripts\canonical\08_index_builder.py archive\drafts --output-dir indexes\provisional --allow-unreviewed
```

Exit criteria:

- `summary_application` extraction improves from `0 / 52`.
- Provisional indexes still generate successfully.
- Audit report shows the new coverage counts.

### Phase 3: Fix Volume 46 Lesson 22

Goal: resolve the only lesson currently missing both biblical reading and
outline.

Recommended work:

1. Inspect volume 46 normalized text around lesson 22 boundaries.
2. Confirm whether the section labels are malformed, shifted, or merged with
   neighboring text.
3. Update section extraction rules or segmentation source tracing as needed.
4. Add a regression test for volume 46 lesson 22.

Exit criteria:

- Volume 46 lesson 22 has `biblical_reading`.
- Volume 46 lesson 22 has `lesson_outline`.
- The missing-section report no longer lists those two gaps.

### Phase 4: Resolve OCR Promotion Blockers

Goal: separate true blockers from noisy warnings.

Recommended work:

1. Review volume 45 page 1 against the source PDF.
2. Decide whether the zero-text page is expected front matter or a real
   extraction failure.
3. Record the decision in the OCR quality report or a waiver file.
4. Tune repeated header/footer detection so the report highlights blockers
   before broad layout warnings.

Exit criteria:

- Volume 45 `BLOCKED` status is either fixed or explicitly waived with a
  reviewer-readable reason.
- Repeated header/footer warnings remain visible but no longer obscure blocker
  pages.

### Phase 5: Promote A Small Canonical Pilot

Goal: prove the official canonical path with reviewed data before scaling.

Recommended work:

1. Select 1 or 2 lessons with the best extraction coverage.
2. Perform human review on those drafts.
3. Remove placeholders and automated-unreviewed markers.
4. Copy reviewed YAML into `archive/lessons`.
5. Run:

```text
python scripts\canonical\07_schema_validator.py
python scripts\canonical\08_index_builder.py
```

Exit criteria:

- Canonical validation passes for the pilot.
- Official `indexes/lessons_index.yaml` and `indexes/scripture_index.yaml`
  are generated from reviewed canonical YAML.
- Provisional indexes remain separate from official indexes.

### Phase 6: Add CI And Repeatable Drive Publishing

Goal: make the complete cycle repeatable without relying on memory.

Recommended work:

1. Add GitHub Actions for tests, canonical validation, and index safety.
2. Add an optional CI or local command for provisional draft index generation.
3. Document the exact Drive `outputs` publishing command in `PROCESS.md`.

Exit criteria:

- GitHub blocks unsafe canonical YAML.
- The no-human-review provisional cycle can be rerun as an engineering audit.
- Drive output publishing is documented step by step.

### Recommended Work Order

Use this order for the next implementation cycle:

1. Missing-section report.
2. Summary/application extraction improvements.
3. Volume 46 lesson 22 fix.
4. OCR blocker triage for volume 45.
5. Canonical pilot promotion.
6. CI and Drive publishing documentation.

## Current Cycle Summary

The no-human-review cycle is now good enough for engineering tests and future
translation planning experiments:

```text
Drive outputs cleared: yes
Pipeline completed: yes
Draft YAML generated: 52
Official canonical YAML: 0
Official indexes: 0
Provisional indexes: 2
Tests passed: 18
Drive outputs republished: yes
```

The main technical blocker is not the index cycle. The index cycle works in
provisional mode. The main blockers are content quality and review readiness:

- missing `summary_application` for all 52 lessons
- missing volume 46 lesson 22 biblical reading and lesson outline
- volume 45 OCR status `BLOCKED`
- no reviewed canonical lesson pilot
- no CI gate yet
