# Pipeline Audit Report

Audit date: 2026-06-16

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
python scripts/run_pipeline.py --run-tags ingestion,structuring,audit,canonical,indexing
```

The CI workflow was also triggered and passed, but with a critical finding (see below). The key CI commands are:

```text
flake8 .
coverage run -m unittest discover -s tests
coverage report -m --fail-under=80
python scripts/canonical/07_schema_validator.py
python scripts/canonical/08_index_builder.py
```

## Pipeline Result Summary

| Artifact | Count | Status |
| --- | ---: | --- |
| Source PDFs | 2 | Pass |
| Raw text files | 2 | Pass |
| Quality reports | 2 | WARNING |
| Normalized text files | 2 | Pass |
| Structure JSON files | 2 | Pass |
| Lesson segment JSON files | 2 | Pass |
| Lesson section JSON files | 2 | Pass |
| Draft YAML files | 52 | Pass |
| Reviewed canonical YAML files | 1 | Pass |
| Official index YAML files | 12 | Pass |
| Provisional draft index YAML files | 12 | Pass |
| Unit Tests Discovered | 20 | **FAIL** (See Finding #1) |
| Unit Tests Created | 24 | **FAIL** (See Finding #1) |
| Code Coverage | >80% | Pass |

**Cycle Interpretation**: The pipeline is functionally stable, and the canonical pilot was a success. However, a critical inconsistency in the test suite's file structure means that **new tests are not being run by the CI workflow**, creating a significant blind spot in quality assurance.

## Key Findings

### 1. CRITICAL: Test Location Inconsistency

**Status: High-Priority Error**

The CI workflow is configured to discover tests only within the `tests/` directory (`unittest discover -s tests`). However, several new test files have been created in the `scripts/` directory instead:
- `scripts/structuring/test_06_section_extractor.py`
- `scripts/test_08_title_consistency_audit.py`
- `scripts/test_09_low_confidence_scripture_audit.py`
- `scripts/audit/test_10_pipeline_quality_audit.py`
- `scripts/audit/test_11_publication_id_consistency_audit.py`

Because these files are in the wrong location, **they are being ignored by the test runner**. The CI build appears "green" only because it is not aware of these new tests. This must be fixed immediately to ensure the integrity of the test suite.

### 2. Canonical Pilot Success

**Status: Excellent**

The canonical pilot promotion was a success. The first human-reviewed lesson (`archive/lessons/2024/C1/LES-2024-C1-001.yaml`) has been added to the archive. The schema validator and official index builder ran successfully against this file, proving that the end-to-end production workflow is functional. This is a major project milestone.

### 3. Automated Section Extraction Coverage

**Status: Excellent**

The most significant content gaps have been resolved. The section extractor now correctly identifies and extracts the `summary_application` section for all 52 lessons. The bug affecting lesson 22 of volume 46 has also been fixed. The automated extraction coverage for core sections is now effectively 100%.

### 4. Architectural Maturity

**Status: Excellent**

The pipeline architecture is now mature and flexible. The `run_pipeline.py` script is driven by a clear JSON configuration, and the CI workflow provides robust, automated quality gates including linting, testing, coverage checks, and index validation.

## Remaining Gaps

1.  **Test Discovery Failure**: The misplaced test files are the most critical gap.
2.  **Onboarding a Second Publication Family**: The architecture is designed to support different publication families (e.g., `alumno`), but has only been tested with `maestro` content. Onboarding a second family is necessary to fully validate the profile-based system.
3.  **Human Review at Scale**: The process is proven for one lesson, but a workflow for reviewing and promoting lessons in bulk has not yet been established.

## Recommended Next Actions

### Highest Priority

1.  **Fix Test File Locations**:
    - **Action**: Move all test files from the `scripts/` directory into the appropriate subdirectories under `tests/`.
    - **Goal**: Ensure that all created tests are discovered and run by the CI workflow, restoring the integrity of the automated test suite.

### Medium Priority

2.  **Onboard a Second Publication Family**:
    - **Action**: Add a source PDF for a different publication family (e.g., `alumno` or `joven`) and run it through the pipeline.
    - **Goal**: Validate the profile-based architecture and identify any family-specific extraction rules that need to be added.

### Lower Priority

3.  **Establish a Bulk Review Process**:
    - **Action**: Document a process for a human reviewer to efficiently review and promote a full publication's worth of lessons.
    - **Goal**: Define the workflow needed to scale up the population of the canonical archive.