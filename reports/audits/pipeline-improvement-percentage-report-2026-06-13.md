# Pipeline Improvement Percentage Report - 2026-06-13

This report compares the previous audit baseline against the current
recommendation implementation pass.

## Baseline And Current Run

| Area | Previous baseline | Current run | Change |
| --- | ---: | ---: | ---: |
| Regression tests | 20 | 22 | +10.0% |
| Expositor profile config files | 0 | 7 | New capability |
| Provisional index files | 2 | 8 | +300.0% |
| Family-specific index folders | 0 | 1 | New capability |
| Compact lesson index entries | 0 | 52 | New capability |
| Section-outline index entries | 0 | 156 | New capability |
| Translation-alignment lesson entries | 0 | 52 | New capability |
| Detailed lesson index entries | 52 | 52 | 0.0% |
| Scripture references indexed | 91 | 91 | 0.0% |
| Draft YAML files | 52 | 52 | 0.0% |
| Reviewed canonical YAML files | 0 | 0 | 0.0% |

## Runtime Comparison

| Stage | Previous timing | Current timing | Change |
| --- | ---: | ---: | ---: |
| Normalization | 6.647 seconds | 2.831 seconds | 57.4% faster |
| Draft YAML generation | 11.907 seconds | 6.858 seconds | 42.4% faster |
| Provisional indexing | 9.796 seconds | 13.586 seconds | 38.7% slower |

Indexing is slower because it now writes detailed, compact, section-outline,
scripture, translation-alignment, and family-specific views instead of only two
provisional files.

## Token And File-Size Comparison

| Area | Previous | Current | Change |
| --- | ---: | ---: | ---: |
| Draft YAML total size | 198,828 bytes | 198,828 bytes | 0.0% |
| Previous provisional index total size | 232,110 bytes | 1,163,000 bytes | +400.9% |
| Detailed lesson index | 210,390 bytes | 249,361 bytes | +18.5% |
| Compact lesson index | not available | 16,190 bytes | New compact view |

The compact lesson index is 93.5% smaller than the current detailed lesson
index. For token-maximized workflows, use:

```text
indexes/provisional/compact_lessons_index.yaml
```

Use the detailed and section indexes only when a task needs section item text,
translation alignment, or future HTML/CSS formatting hooks.

## OCR Percentage Change

| OCR metric | Previous | Current | Change |
| --- | ---: | ---: | ---: |
| Source PDFs covered | 2 | 2 | 0.0% |
| `BLOCKED` quality reports | 1 | 1 | 0.0% |
| `WARNING` quality reports | 1 | 1 | 0.0% |

OCR quality did not improve in this pass because the work focused on profiles,
indexing, reporting, and pipeline observability. Volume 45 still needs page 1
human/source confirmation or a documented waiver before canonical promotion.

## Normalization Percentage Change

| Normalization metric | Previous | Current | Change |
| --- | ---: | ---: | ---: |
| Classified normalized text files | 2 | 2 | 0.0% |
| Root-level normalized text files | 0 | 0 | 0.0% |
| Unknown normalized family folders | 0 | 0 | 0.0% |
| Profile-aware audit coverage | no | yes | New capability |

The normalization layout was already correct for the available `maestro` PDFs.
The improvement is observability: the audit now reports root-level files,
unknown family folders, and normalized output counts by profile.

## YAML Percentage Change

| YAML metric | Previous | Current | Change |
| --- | ---: | ---: | ---: |
| Draft YAML files | 52 | 52 | 0.0% |
| Drafts marked `automated_unreviewed` | 52 | 52 | 0.0% |
| Canonical reviewed YAML files | 0 | 0 | 0.0% |
| Profile-aware YAML completeness audit | no | yes | New capability |

The YAML content count did not increase because no new source PDFs were added.
The improvement is profile-aware reporting and clearer separation between
automated drafts and canonical reviewed YAML.

## Indexing Percentage Change

| Indexing metric | Previous | Current | Change |
| --- | ---: | ---: | ---: |
| Index views | 2 | 8 | +300.0% |
| Compact lookup views | 0 | 2 | New capability |
| Section-outline views | 0 | 2 | New capability |
| Translation-alignment views | 0 | 2 | New capability |
| Family-specific index folders | 0 | 1 | New capability |
| Item source trace pointers | no | yes | New capability |

The indexing improvement is the largest functional gain in this pass. The
tradeoff is higher total generated index size, which is why compact indexes now
exist for token-sensitive workflows.

## Remaining Gaps

- No non-`maestro` PDFs are available yet, so second-family validation is
  scaffolded but not complete.
- No reviewed canonical YAML exists under `archive/lessons`.
- Official index generation remains correctly blocked until canonical reviewed
  YAML exists.
- OCR status did not improve; volume 45 remains `BLOCKED` and volume 46 remains
  `WARNING`.
