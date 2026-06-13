# Pipeline Optimization Audit - 2026-06-13

Scope: normalization, YAML generation, performance, token maximization, and
indexing improvement.

## Executive Summary

The current `maestro` pilot cycle is functional for no-human-review diagnostics:
normalization, draft YAML generation, provisional indexing, and tests all run.
Google Drive `outputs` was cleared before this audit. The next major
architecture improvement is to treat `maestro`, `alumno`, `joven`, `nino`,
`parvulo`, and other families as separate structure profiles, not only as
folder names.

Official canonical output remains blocked because there are still no reviewed
lesson YAML files under `archive/lessons`.

## Evidence

Commands measured from the repository root:

| Area | Command | Result |
| --- | --- | --- |
| Normalization | `python scripts\structuring\03_minimal_text_normalizer.py` | 6.647 seconds |
| Draft YAML | `python scripts\canonical\06_yaml_generator.py` | 11.907 seconds |
| Provisional indexing | `python scripts\canonical\08_index_builder.py archive\drafts --output-dir indexes\provisional --allow-unreviewed` | 9.796 seconds |
| Tests | `python -m unittest discover -s tests` | 20 tests passed in command timing of 5.449 seconds |

Current artifact counts:

| Artifact | Count or size |
| --- | --- |
| Normalized `maestro` text files | 2 |
| Draft YAML files | 52 |
| Reviewed canonical YAML files | 0 |
| Provisional lesson index | 52 lessons |
| Provisional scripture index | 91 scripture references |
| Indexed outline items | 724 |
| Indexed teacher-note items | 169 |
| Indexed summary/application items | 52 |

OCR quality status:

| Source | Status | Main issues |
| --- | --- | --- |
| `expositor-guia-maestro-volumen-45` | `BLOCKED` | page 1 zero text/human review, repeated header/footer noise, malformed scripture-reference warnings |
| `expositor-guia-maestro-volumen-46` | `WARNING` | repeated header/footer noise, malformed scripture-reference warnings |

Size and token-footprint estimate:

| Artifact group | Size |
| --- | --- |
| Raw text total | 1,231,635 bytes |
| Normalized text total | 1,204,231 bytes |
| Draft YAML total | 198,828 bytes |
| Draft YAML average | 3,823.6 bytes per lesson |
| Draft YAML estimated tokens | about 49,361 |
| Provisional lesson index | 210,390 bytes |
| Provisional lesson index estimated tokens | about 52,261 |

The detailed provisional lesson index is now slightly larger than all draft
YAML combined. That is acceptable for diagnostics, but it should not become the
only retrieval artifact used by future translation tooling.

## Normalization Audit

Status: working for the current `maestro` pilot.

Findings:

- Normalized text is stored under `normalized/maestro`, which is the correct
  classification-aware layout.
- Raw text remains separate under `ocr/raw_txt`, preserving the source
  extraction layer.
- Normalized text is about 2.2 percent smaller than raw text, mainly from safe
  whitespace cleanup and reflow.
- Current classification is filename-based. This is acceptable for the pilot,
  but future families need explicit profile evidence because each family may
  use different headings, age-level activities, notes, and lesson layouts.

Recommendations:

1. Add profile configuration files under a future path such as
   `config/expositor_profiles/<family>.yaml`.
2. Move family-specific section labels and boundary rules out of generic
   scripts once a second family is onboarded.
3. Add a normalized-text audit report that flags unexpected root-level files,
   unknown `unclassified` outputs, and profile mismatches.

## YAML Audit

Status: draft YAML generation works, but canonical YAML remains blocked.

Findings:

- 52 draft YAML files exist under `archive/drafts`.
- 0 reviewed canonical YAML files exist under `archive/lessons`.
- Drafts remain `automated_unreviewed`, which is correct while human review is
  skipped for pipeline testing.
- YAML output uses wide line wrapping to avoid unwanted line breaks in Spanish
  prose.
- Current YAML shape is still mostly `maestro`-oriented. Other families may
  require different fields, for example student activities, child-level memory
  aids, or age-specific application sections.

Recommendations:

1. Define profile-driven YAML section maps before ingesting `alumno`, `joven`,
   `nino`, or `parvulo`.
2. Add a YAML completeness report by family and section.
3. Keep all generated drafts out of `archive/lessons` until human review is
   complete.

## Performance Audit

Status: acceptable for two source PDFs, but the workflow needs scaling
controls before multi-year ingestion.

Findings:

- Normalization, YAML generation, and provisional indexing each complete in
  under 12 seconds on the current local run.
- The index builder reparses every draft YAML file on each run.
- The pipeline currently favors deterministic full regeneration over
  incremental caching, which is safer for early architecture work.

Recommendations:

1. Keep full regeneration as the default until the profile system stabilizes.
2. Add optional incremental mode later using source file hash, script version,
   and profile version.
3. Add timing logs per stage to `ocr/processing_logs` or a new
   `reports/pipeline_runs` folder.

## Token Maximization Audit

Status: usable, with clear improvement opportunities.

Findings:

- The provisional lesson index is about 52,261 estimated tokens, larger than
  the full draft YAML set estimate of about 49,361 tokens.
- The detailed index is useful for translation planning and CSS/HTML mapping,
  but it mixes lookup fields and full item text in one file.
- Future AI-assisted review or translation should avoid loading every lesson
  and every index item at once.

Recommendations:

1. Split future indexes into multiple views:
   - compact lesson lookup index
   - section outline index
   - scripture index
   - translation alignment index
2. Keep full text in lesson YAML and use index entries as pointers when a task
   only needs lookup.
3. Add per-family and per-cycle index files to reduce context size during
   future translation phases.

## Indexing Audit

Status: provisional indexing works; official indexing is correctly blocked.

Findings:

- Provisional index generation succeeds with `--allow-unreviewed`.
- Official index generation remains blocked because canonical reviewed YAML is
  absent.
- The provisional lesson index now includes section-level items, which supports
  future translation and CSS/HTML formatting.
- Current item-level source traces are section-level, not individual item-level.

Recommendations:

1. Add `profile_id` and `profile_version` to index metadata.
2. Add item-level source traces when extractor support is ready.
3. Produce classification-specific index outputs such as:

```text
indexes/provisional/maestro/lessons_index.yaml
indexes/provisional/alumno/lessons_index.yaml
indexes/provisional/joven/lessons_index.yaml
```

4. Keep `indexes/provisional` separate from official indexes until canonical
   human-reviewed YAML exists.

## Recommended Next Implementation Order

1. Create explicit Expositor family profile configuration. Status:
   implemented as `config/expositor_profiles/*.yaml`.
2. Add a profile-aware normalized-output audit command. Status: implemented in
   `scripts/audit/10_pipeline_quality_audit.py`.
3. Add profile-specific YAML section maps. Status: scaffolded in profile YAML;
   only `maestro` is active until more PDFs are added.
4. Split provisional indexes into compact and detailed views. Status:
   implemented with compact, detailed, section-outline, scripture,
   translation-alignment, and family-specific views.
5. Add item-level source traces. Status: implemented as item-level
   `source_trace_ref` pointers to section source traces.
6. Add per-stage performance logs. Status: implemented with
   `scripts/run_pipeline.py --write-run-log`.
7. Run a second-family pilot before scaling to multiple years. Status: blocked
   until non-`maestro` PDFs are added.

## Google Drive Output Status

The configured Google Drive `outputs` folder was cleared during this audit.
The empty listing was verified after deleting files and removing empty
subfolders while leaving the root `outputs` folder available for future runs.
