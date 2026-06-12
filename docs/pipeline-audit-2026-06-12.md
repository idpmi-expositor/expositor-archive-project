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

Key interpretation:

- Volume 45 remains blocked because page 1 has zero text / needs human review.
- Volume 45 used OCR fallback on page 223.
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
