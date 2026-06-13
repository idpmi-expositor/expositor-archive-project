# Pipeline Audit Report

Audit date: 2026-06-15

## Scope

This audit performed a full, no-human-review pipeline run to assess the current state of data quality, extraction coverage, and architectural stability.

The audit validates that:
- The pipeline runs end-to-end without errors.
- Automated quality gates and audits are functioning correctly.
- The CI workflow provides a reliable safety net.
- The most critical content gaps have been addressed.

## Commands Run

The primary pipeline was executed using the new tag-based runner:

```text
python scripts/run_pipeline.py --run-tags ingestion,structuring,audit,canonical
```

Provisional indexing was run to validate draft output:

```text
python scripts/canonical/08_index_builder.py archive/drafts --output-dir indexes/provisional --allow-unreviewed
```

The CI workflow was also triggered and passed successfully:

```text
coverage run -m unittest discover -s tests
coverage report -m --fail-under=80
```

## Pipeline Result Summary

| Artifact | Count | Status |
| --- | ---: | --- |
| Source PDFs | 2 | Pass |
| Raw text files | 2 | Pass |
| Quality reports | 2 | See Findings |
| Normalized text files | 2 | Pass |
| Structure JSON files | 2 | Pass |
| Lesson segment JSON files | 2 | Pass |
| Lesson section JSON files | 2 | Pass |
| Draft YAML files | 52 | Pass |
| Reviewed canonical YAML files | 0 | Blocked (by design) |
| Official index YAML files | 0 | Blocked (by design) |
| Provisional draft index YAML files | 12 | Pass |
| Unit Tests | 23 | Pass |
| Code Coverage | >80% | Pass |

**Cycle Interpretation**: The full, no-human-review pipeline is stable and functioning correctly. All automated quality gates, including the new CI workflow, are operational. Official canonical output remains correctly blocked, as no human review has been performed.

## Key Findings

### 1. CI and Test Automation

**Status: Excellent**

A GitHub Actions CI workflow is now fully operational. It automatically runs all 23 unit tests on every commit, enforces a minimum of 80% code coverage, and uploads a detailed coverage report as a build artifact. This provides a strong, professional-grade safety net against regressions.

### 2. OCR and Extraction Quality

**Status: Improved**

| Publication | Status | Key Issues |
| --- | --- | --- |
| `expositor-guia-maestro-volumen-45` | `WARNING` | `zero_text` on page 1 (waived), header/footer noise |
| `expositor-guia-maestro-volumen-46` | `WARNING` | `low_word_count` on page 110, header/footer noise |

The `BLOCKED` status for Volume 45 has been successfully resolved by implementing a waiver for the blank cover page. Both volumes now have a `WARNING` status, which allows them to proceed in the pipeline but correctly flags them for review. The primary source of noise in the quality reports remains the `repeated_header_footer` issue.

### 3. Automated Section Extraction Coverage

**Status: Significantly Improved**

| Publication | Lessons | Biblical reading | Outline | Teacher notes | Summary/application |
| --- | ---: | ---: | ---: | ---: | ---: |
| `expositor-guia-maestro-volumen-45` | 26 | 26 | 26 | 26 | **26** |
| `expositor-guia-maestro-volumen-46` | 26 | 26 | 26 | 26 | **26** |

The most critical content gap—the missing `summary_application` section—has been resolved. The section extractor now correctly identifies and extracts this section for all 52 lessons. The bug affecting lesson 22 of volume 46 has also been fixed. The automated extraction coverage for core sections is now effectively 100%.

### 4. Architectural Improvements

**Status: Excellent**

The pipeline architecture has been significantly refactored for clarity and flexibility.
- The main `run_pipeline.py` script is now driven by a clear JSON configuration file (`config/pipeline_steps.json`), making it easy to manage.
- Control over pipeline execution is now managed with flexible `--run-tags` and `--skip-tags` flags, deprecating the old `--skip-*` arguments.
- A suite of new, targeted audit scripts provides deep visibility into data quality, including checks for missing sections, title consistency, and scripture reference confidence.

## Remaining Gaps

1.  **Human Review Workflow Not Exercised**: The single largest remaining gap is not in the code, but in the process. The human review and promotion workflow (moving a `draft` to a `canonical` lesson) is documented but has not yet been tested with a real lesson.
2.  **Publication Family Profiles Not Fully Exercised**: The architecture is designed to support different publication families (e.g., `maestro`, `alumno`), but has only been tested with `maestro` content. Onboarding a second family is necessary to fully validate the profile-based system.
3.  **Minor Audit Noise**: The OCR quality reports are still noisy due to repeated headers and footers. While not a blocker, tuning this would make the reports easier for human reviewers to parse.

## Recommended Next Actions

The project is now in a strong position to move from development and testing towards production readiness.

### Highest Priority

1.  **Conduct a Canonical Pilot Promotion**:
    - **Action**: Manually review and promote one lesson from `archive/drafts` to `archive/lessons` by following the `docs/human-review-checklist.md`.
    - **Goal**: Prove the end-to-end canonical workflow, including schema validation and the generation of the first official, production-ready indexes. This is the final step to unlock the production capabilities of the archive.

### Medium Priority

2.  **Onboard a Second Publication Family**:
    - **Action**: Add a source PDF for a different publication family (e.g., `alumno` or `joven`) and run it through the pipeline.
    - **Goal**: Validate the profile-based architecture and identify any family-specific extraction rules that need to be added.

### Lower Priority

3.  **Fine-Tune Audit Reporting**:
    - **Action**: Refine the quality reporting logic to better distinguish between ignorable layout repetition and meaningful content warnings.
    - **Goal**: Improve the signal-to-noise ratio of the audit reports to accelerate human review.