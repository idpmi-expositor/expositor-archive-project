# Architectural Validation

Validation date: 2026-06-12

Validated repository state:

```text
base_commit: 1f9b59d Update architecture validation and pipeline audit
pipeline_audit: docs/pipeline-audit-2026-06-12.md
source_pdfs: 2
raw_txt: 2
normalized_txt: 2
document_structure_json: 2
lesson_segment_json: 2
lesson_section_json: 2
draft_yaml: 52
canonical_yaml: 0
official_indexes: 0
provisional_draft_indexes: 2
quality_reports: 2
```

Current production-readiness verdict: **PARTIALLY READY FOR DEVELOPMENT, NOT
READY FOR CANONICAL PRODUCTION USE**

The repository now has a safer and more complete automated draft pipeline than
the earlier architecture validation described. Google Drive source validation
works, raw extraction artifacts exist, normalized text exists, document
structure is detected, lesson segmentation works for both source volumes,
automated section extraction exists, scripture reference parsing exists for
draft generation, and the orchestration script can rebuild downstream outputs.

The repository is still not ready for production retrieval or canonical archive
use. There are no reviewed canonical lesson YAML files under `archive/lessons`,
there are no official generated indexes, all 52 draft records remain
automated-unreviewed, OCR/layout quality issues remain, and section coverage is
incomplete enough that a human reviewer must still verify every promoted lesson.
The repository can now build clearly labeled provisional indexes from drafts for
audit and planning, but those indexes are not canonical archive truth.

This document uses the project terminology consistently:

- **Human revision** means the instructions, comments, and operational steps are
  understandable to a normal maintainer without Python knowledge.
- **Human review** means a person verifies extracted lesson content before a
  draft can become canonical archive data.

## Evidence Summary

Latest validation evidence:

```text
python scripts\run_pipeline.py --drive-root-folder-id 1LX-wYECeqZVD_Uwe8ZEpfFL9oicVdeG7 --rclone-config rclone\rclone.conf --skip-raw-extraction
```

Observed result:

```text
Pipeline completed through draft generation.
```

Google Drive `outputs` cleanup was performed before the run:

```text
C:\Tools\rclone\rclone.exe --config rclone\rclone.conf delete "gdrive,root_folder_id=18J7kB4mUpNU7J7aPn17xl7SQOSYYyO7n:outputs"
C:\Tools\rclone\rclone.exe --config rclone\rclone.conf rmdirs "gdrive,root_folder_id=18J7kB4mUpNU7J7aPn17xl7SQOSYYyO7n:outputs" --leave-root
```

```text
python -m unittest discover -s tests
```

Observed result:

```text
Ran 18 tests
OK
```

```text
python scripts\canonical\07_schema_validator.py
```

Observed result:

```text
No lesson YAML files found under archive/lessons
```

```text
python scripts\canonical\08_index_builder.py
```

Observed result:

```text
No canonical lesson YAML files found under archive/lessons
Index generation stopped because there is no canonical data.
```

Provisional draft indexing evidence:

```text
python scripts\canonical\08_index_builder.py archive\drafts --output-dir indexes\provisional --allow-unreviewed
```

Observed result:

```text
WARNING: building a provisional index from unreviewed draft YAML. This output is not canonical archive truth.
Indexed 52 lesson YAML file(s).
```

Google Drive source validation evidence:

```text
source_assets/original_pdfs/expositor-guia-maestro-volumen-45.pdf
source_assets/original_pdfs/expositor-guia-maestro-volumen-46.pdf
```

Both expected PDFs were present in the configured Google Drive source folder and
matched the local source set used by the pipeline audit.

## 1. Architecture Validation

### Findings

The repository has a clear deterministic pipeline architecture organized into
three processing layers:

- `scripts/ingestion`: source discovery, raw text extraction, and OCR quality
  reporting.
- `scripts/structuring`: normalization, document structure detection, lesson
  segmentation, and automated section extraction.
- `scripts/canonical`: scripture reference parsing, draft YAML generation,
  canonical validation, and index building.

The draft/canonical boundary is now explicit:

- `archive/drafts`: generated scaffold or automated-unreviewed YAML awaiting
  human review.
- `archive/lessons`: reviewed canonical lesson YAML only.

This is the most important safety feature in the current architecture.
Generated output can be inspected and improved without being treated as archival
truth or indexed as production data.

The repository also has a top-level orchestration script:

```text
scripts/run_pipeline.py
```

That script provides a safer routine path than manually running every numbered
script. Individual numbered scripts remain useful for debugging a specific
pipeline layer.

The index builder now has an explicit `--allow-unreviewed` mode for audit-only
draft indexing. That mode writes warning-labeled indexes from `archive/drafts`
without weakening the official canonical validation path.

### Risks

The canonical archive is structurally prepared but empty. Because
`archive/lessons` has no reviewed lesson YAML, the system has no production
retrieval surface.

The architecture still depends on human review before promotion. That is the
correct policy, but the current draft quality means review effort remains
substantial.

There is no CI workflow yet to enforce the documented gates automatically on
GitHub.

### Recommendations

Keep the current layered architecture and the draft/canonical boundary.

Use the pipeline runner for routine regeneration:

```text
python scripts\run_pipeline.py --drive-root-folder-id GOOGLE_DRIVE_FOLDER_ID
```

When source PDFs and raw extraction already exist, use:

```text
python scripts\run_pipeline.py --skip-drive-validation --skip-rename --skip-raw-extraction
```

Add GitHub Actions checks that run tests, canonical validation, official index
generation safety checks, provisional index generation, and a no-placeholders
policy for canonical YAML.

### Confidence Level

High.

The architecture is supported by folder layout, executable scripts, tests,
generated artifacts, and the latest audit report.

## 2. Source Sync and Ingestion Validation

### Findings

The configured Google Drive source connection is usable for the current source
set. The latest audit confirmed the expected two source PDFs:

```text
expositor-guia-maestro-volumen-45.pdf
expositor-guia-maestro-volumen-46.pdf
```

Local source PDF naming is stable, and the rename dry-run reported both files
as keep/no-change.

Raw text extraction exists for both source PDFs, with processing logs and
quality reports present.

### Risks

Drive validation is operational but should remain a first-class pipeline gate.
If maintainers skip Drive validation during routine reruns, they should only do
so when the local source PDFs were already verified.

### Recommendations

Document Drive validation as required before accepting a new source volume.
Keep `--skip-drive-validation` only for repeat local rebuilds from already
verified PDFs.

### Confidence Level

High.

The source set was checked against the configured Drive folder during the
latest audit.

## 3. Structure and Segmentation Validation

### Findings

The pipeline recognizes both source volumes at the lesson-count level:

```text
volume 45 segments: 26
volume 46 segments: 26
```

Both segment reports completed with warning status, not hard failure.

Known warning:

```text
DUPLICATE_OBSERVED_LESSON_HEADERS
```

This warning is expected for the current PDFs because repeated lesson headers
can appear inside lesson pages. Segmentation still works because the system
prefers `Contenido` entries and preserves page and line spans.

### Risks

Repeated headers are not currently breaking segmentation, but richer logic is
still needed to separate primary lesson starts from repeated in-page headers.

If a future volume has a different contents layout, structure detection could
need additional regression coverage.

### Recommendations

Add regression fixtures for shifted front matter and alternate contents-page
layouts.

Keep source traceability fields on every segment:

```yaml
source_trace:
  page_start:
  page_end:
  line_start:
  line_end:
```

### Confidence Level

High.

Segment counts, status values, and warnings are generated by the current
pipeline artifacts.

## 4. Automated Section Extraction Validation

### Findings

Automated section extraction is now implemented and produces metadata under:

```text
metadata/lesson_sections/
```

Latest section coverage:

```text
volume 45 lessons: 26
volume 45 biblical_reading: 26
volume 45 lesson_outline: 26
volume 45 teacher_notes: 26
volume 45 summary_application: 0

volume 46 lessons: 26
volume 46 biblical_reading: 25
volume 46 lesson_outline: 25
volume 46 teacher_notes: 26
volume 46 summary_application: 0
```

All 52 drafts remain marked as automated-unreviewed.

### Risks

Summary/application extraction is currently missing for every lesson. Volume 46
lesson 22 is also missing biblical reading and lesson outline extraction.

Because section coverage is incomplete, generated drafts are useful review
inputs but are not canonical-ready.

### Recommendations

Improve section label detection for:

- `Resumen y aplicacion practica`
- variant accent/capitalization patterns
- multi-line section labels
- lessons where the biblical reading or outline appears near a page boundary

Add an extraction completeness report that lists missing required sections per
lesson and exits non-zero when canonical promotion is attempted with missing
required content.

### Confidence Level

High.

The section coverage numbers come from generated `metadata/lesson_sections`
artifacts and draft generation output.

## 5. OCR and Text Quality Validation

### Findings

Quality reports now exist under:

```text
ocr/quality_reports/
```

Latest quality status:

```text
volume 45 status: BLOCKED
volume 46 status: WARNING
```

Volume 45 has one zero-text page and one OCR fallback page. Volume 46 has no
zero-text pages in the latest report, but still has low-word-count and repeated
header/footer warnings.

Common reported issues include:

- low OCR confidence
- low word count
- malformed scripture references
- repeated header/footer contamination
- zero text

Known text artifact:

```text
Lectura Biblica: 1Romanos 1:18-25
```

### Risks

OCR/text quality is a production blocker for canonical promotion when the
quality report status is `BLOCKED`.

Repeated header/footer warnings are currently very noisy. The reports are
useful, but maintainers need clearer prioritization so a normal reviewer can
separate blocking issues from expected layout noise.

### Recommendations

Keep quality reports, but add a human-readable summary at the top of each
report:

- blocking pages
- pages needing visual comparison
- warning-only pages
- extraction issues likely safe to ignore

Tune repeated header/footer detection to reduce noise while preserving real
layout warnings.

Add a promotion gate that blocks canonical promotion when a source volume has
quality status `BLOCKED`.

### Confidence Level

Medium-High.

The quality report findings are direct pipeline artifacts, but a full visual
page-by-page comparison against rendered PDFs has not been completed.

## 6. Canonical and Indexing Validation

### Findings

Official indexing is safe but not retrieval-ready.

There are no reviewed canonical lesson YAML files:

```text
canonical_yaml: 0
```

There are no official indexes:

```text
official_indexes: 0
```

This is correct under the current policy. The index builder refuses to generate
official indexes without reviewed canonical input.

There are provisional draft indexes:

```text
indexes/provisional/lessons_index.yaml
indexes/provisional/scripture_index.yaml
```

These indexes were generated with:

```text
python scripts\canonical\08_index_builder.py archive\drafts --output-dir indexes\provisional --allow-unreviewed
```

The provisional lesson index contains 52 draft lessons. The provisional
scripture index contains 91 scripture-reference entries. Both files include:

```yaml
index_scope: automated_unreviewed_draft
warning: This index was built from unreviewed draft YAML. Do not use it as canonical archive truth.
```

Draft YAML under `archive/drafts` can contain automated extraction values,
review placeholders, and unreviewed text. Draft YAML is intentionally excluded
from official canonical validation and official indexing.

### Risks

The repository currently has no production retrieval surface. Semantic search,
hierarchy-aware retrieval, scripture lookup, and citation traceability cannot be
considered production-ready until reviewed canonical YAML exists.

Provisional indexes can help reviewers see what the automated pipeline produced,
but they also contain unreviewed values and may include placeholders. They must
not be published as official retrieval indexes.

### Recommendations

Keep indexes blocked until:

- reviewed YAML exists under `archive/lessons`
- canonical YAML contains no placeholders
- scripture references are normalized
- source traceability is complete
- OCR quality for the source volume is not blocked
- human review is complete

Keep provisional indexes under `indexes/provisional` or another clearly labeled
non-canonical path.

Add a small pilot promotion of one or two reviewed lessons after the extraction
and OCR issues are triaged. Use that pilot to test canonical validation and
index generation end to end.

### Confidence Level

High.

The validator and index builder behavior were verified directly.

## 7. Documentation and Human-Revision Validation

### Findings

Documentation has improved significantly. The repository now documents:

- installation and setup
- Google Drive source sync
- pipeline operation
- draft vs canonical boundaries
- human review requirements
- human revision levels for non-Python maintainers
- OCR quality policy
- draft-to-canonical promotion
- production-ready YAML expectations

Important documentation files include:

```text
README.md
INSTALL.md
PROCESS.md
CONTRIBUTING.md
docs/google-drive-sync.md
docs/human-revision-levels.md
docs/human-review-checklist.md
docs/draft-to-canonical-promotion.md
docs/lesson-yaml-contract.md
docs/master-architecture-specification.md
docs/ocr-quality-policy.md
docs/pipeline-audit-2026-06-12.md
docs/pipeline-traceability.md
docs/production-ready-canonical-yaml.md
```

### Risks

Documentation is close to human-revision-friendly, but the command-line
workflow can still expose Python terms and script names without enough plain
language context at the point of use.

Documentation can drift from the executable source of truth. Treat these files
as authoritative for behavior:

```text
schemas/base/lesson_schema.yaml
scripts/canonical/07_schema_validator.py
scripts/canonical/08_index_builder.py
scripts/run_pipeline.py
```

### Recommendations

Add one short "daily operator path" to the README or PROCESS document:

1. confirm Drive source PDFs
2. run the pipeline command
3. read the audit and quality summaries
4. review drafts
5. promote only reviewed lessons
6. run validation and index generation

For every script intended for maintainers, keep the opening comments and CLI
help understandable without Python knowledge.

### Confidence Level

High.

The documentation set was reviewed against current scripts and artifacts.

## 8. Test and CI Validation

### Findings

Local regression tests pass:

```text
Ran 18 tests
OK
```

The tests cover important safety behavior such as placeholder blocking and
pipeline components.

### Risks

There is no GitHub CI gate yet. A local passing test suite is useful, but it
does not automatically protect the remote repository.

Current coverage should be expanded for:

- summary/application extraction
- missing section reporting
- OCR quality status handling
- index determinism after canonical pilot promotion
- Drive validation behavior, where feasible with mocked source metadata

### Recommendations

Add GitHub Actions with at least:

```text
python -m unittest discover -s tests
python scripts\canonical\07_schema_validator.py
python scripts\canonical\08_index_builder.py
```

The index builder command should be expected to stop cleanly when no canonical
lessons exist, and to produce deterministic output when reviewed canonical
fixtures are present.

### Confidence Level

High for local test status. Medium-High for CI readiness because CI has not yet
been implemented.

## Final Validation Matrix

| Validation Area | Status | Risk | Confidence |
| --- | --- | --- | --- |
| Architecture | Warning | Medium | High |
| Google Drive Source Sync | Pass | Low | High |
| Ingestion Artifacts | Warning | Medium | High |
| Structure and Segmentation | Warning | Medium | High |
| Automated Section Extraction | Warning | High | High |
| OCR and Text Quality | Fail | High | Medium-High |
| Canonical Review Readiness | Fail | High | High |
| Official Indexing and Retrieval | Fail | High | High |
| Provisional Draft Indexing | Pass | High | High |
| Documentation and Human Revision | Warning | Medium | High |
| Tests | Warning | Medium | High |
| CI and Remote Quality Gates | Fail | High | Medium-High |

## Matrix Recommendation

Yes. The validation matrix should include more items than the original five.
The previous matrix grouped too much risk under broad labels, which made the
repository look closer to production-ready than it is.

Add and keep these matrix areas:

- **Google Drive Source Sync**: verifies the repository is using the expected
  source PDFs.
- **Ingestion Artifacts**: confirms raw text, logs, normalized text, and quality
  reports exist for every source.
- **Automated Section Extraction**: tracks whether drafts contain enough real
  lesson content to reduce human review effort.
- **Canonical Review Readiness**: separates "drafts exist" from "reviewed
  canonical records exist."
- **Official Indexing and Retrieval**: confirms production indexes remain
  blocked until reviewed canonical records exist.
- **Provisional Draft Indexing**: confirms no-human-review pipeline diagnostics
  can be generated without weakening canonical safety gates.
- **Tests**: shows whether local regression protection is healthy.
- **CI and Remote Quality Gates**: shows whether GitHub blocks unsafe changes.

Also split **OCR** from **Structure**. Structure can be good while OCR remains a
canonical blocker, and the current repository demonstrates exactly that.

## Final Verdict

Answer: **PARTIALLY**

The repository is safe enough to continue development and structured pipeline
improvement. It is not ready for canonical archive production, official
retrieval indexes, or search-facing use.

The key improvement since the earlier validation is that automated extraction
and provisional draft indexing now exist. The key blocker is that extraction is
incomplete and unreviewed, OCR quality still blocks at least one source volume,
and no lesson has been promoted to reviewed canonical YAML.

## Improvement Roadmap

### Stage 1: Safety Gates

Status: Completed.

Completed work:

- Draft YAML is stored under `archive/drafts`.
- Reviewed canonical YAML is reserved for `archive/lessons`.
- Placeholder values are blocked by canonical validation.
- Zero-valued scripture references are blocked.
- Index generation refuses to run without canonical lesson YAML.
- Provisional draft indexing is explicitly labeled as non-canonical.
- Stale placeholder indexes were removed.
- Focused validator tests were added.

### Stage 2: Dynamic Structure Detection

Status: Completed for current source layouts.

Completed work:

- Dynamic contents-page detection is implemented.
- Detected `Contenido` page is recorded in structure JSON.
- Both current source volumes segment into 26 lessons.

Remaining work:

- Add regression tests for shifted front matter and alternate contents layouts.

### Stage 3: Section Extraction

Status: In progress.

Completed work:

- Automated-unreviewed section metadata is generated.
- Biblical reading, outline, and teacher notes extraction works for most
  lessons.
- Source traceability is preserved for extracted sections.

Remaining work:

- Improve `summary_application` extraction, currently 0 of 52 lessons.
- Fix volume 46 lesson 22 missing biblical reading and outline extraction.
- Produce a reviewer-friendly missing-section report.

### Stage 4: Scripture Normalization

Status: In progress.

Completed work:

- Spanish scripture reference parsing exists.
- Draft generation can populate parsed reference metadata when deterministic
  extraction succeeds.

Remaining work:

- Expand coverage for malformed references and multi-reference strings.
- Add clearer reporting for references that require human review.
- Verify normalized references during pilot canonical promotion.

### Stage 5: OCR Quality Gate

Status: In progress.

Completed work:

- OCR quality reports exist.
- Zero-text, low-word-count, malformed-reference, repeated-header/footer, and
  OCR fallback conditions are reported.

Remaining work:

- Resolve or explicitly waive volume 45 `BLOCKED` quality status.
- Reduce repeated-header/footer noise.
- Add reviewer-friendly quality summaries.
- Block canonical promotion for `BLOCKED` source volumes.

### Stage 6: Promotion Workflow

Status: Documented, not yet exercised.

Completed work:

- Human review checklist exists.
- Draft-to-canonical promotion criteria are documented.
- Production-ready YAML expectations are documented.

Remaining work:

- Promote a small reviewed pilot set into `archive/lessons`.
- Run canonical validation on the pilot.
- Generate official indexes from the pilot.
- Document lessons learned from the first promotion.

### Stage 7: CI and Orchestration

Status: Partially complete.

Completed work:

- A top-level pipeline runner exists.
- Local tests pass.
- Provisional draft indexes can be generated for no-human-review audit runs.

Remaining work:

- Add GitHub Actions CI.
- Run tests, canonical validation, and index safety checks in CI.
- Include provisional draft index generation in CI as a diagnostic artifact if
  the project wants no-human-review pipeline visibility.
- Add deterministic index fixture tests once pilot canonical YAML exists.
