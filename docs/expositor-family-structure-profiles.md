# Expositor Family Structure Profiles

Each Expositor family can use a different publication structure. The pipeline
must classify the family first, then use the matching structure profile for
normalization checks, section extraction, YAML generation, and indexing.

## Supported Family Folders

Use ASCII folder names on disk:

| Family | Folder name | Current status |
| --- | --- | --- |
| Expositor Maestro | `maestro` | Active pilot family |
| Expositor Alumno | `alumno` | Profile required before full ingestion |
| Expositor Joven | `joven` | Profile required before full ingestion |
| Expositor Adolescente | `adolescente` | Profile required before full ingestion |
| Expositor Nino | `nino` | Profile required before full ingestion |
| Expositor Parvulo | `parvulo` | Profile required before full ingestion |
| Unknown family | `unclassified` | Audit-only holding area |

The source title may contain Spanish accents, such as `Niño` or `Párvulo`, but
repository paths should remain `nino` and `parvulo` so PowerShell, GitHub
Actions, rclone, and Drive sync commands stay simple.

## Required Profile Fields

Each family profile should eventually define:

| Area | Required profile detail |
| --- | --- |
| Source naming | Filename patterns that identify the family |
| Page layout | Expected front matter, table of contents, lesson pages, and repeated headers or footers |
| Section labels | Labels used for title, biblical reading, golden text, outline, teacher/student notes, activities, and application |
| Lesson boundary rules | Whether boundaries come from `Contenido`, repeated `LECCION` markers, page ranges, or another marker |
| YAML shape | Required and optional section blocks for that family |
| Index shape | Section and item fields needed for lookup, translation alignment, and future CSS/HTML formatting |
| Quality gates | OCR or extraction warnings that block promotion for that family |

## Current Maestro Profile

The current pilot profile is `maestro`.

Generated artifacts use:

```text
normalized/maestro/
structured/document_structure/maestro/
metadata/lessons/maestro/
metadata/lesson_sections/maestro/
archive/drafts/expositor-guia-maestro-volumen-*/
indexes/provisional/
```

The provisional lesson index currently includes:

- `publication_classification`
- `lesson_outline` items
- `teacher_notes` items
- `summary_application` items
- stable `item_id`, `order`, `kind`, and `text` fields

This is enough for audit and future translation planning, but it is not
canonical until reviewed lesson YAML exists under `archive/lessons`.

## Rules For New Families

1. Add or confirm the family name in `scripts/pipeline_classification.py`.
2. Add sample source PDFs for the family.
3. Run extraction and normalization into `normalized/<family>/`.
4. Inspect source layout before changing extraction logic.
5. Add family-specific section labels only when source evidence proves they are
   needed.
6. Generate draft YAML under `archive/drafts`.
7. Generate provisional indexes with `--allow-unreviewed` for audit only.
8. Do not promote into `archive/lessons` until human review is complete.

## Design Decision

Classification is not just a storage folder. It is the selector for the
structure profile. Future improvements should move toward explicit profile
configuration files so `maestro`, `alumno`, `joven`, `nino`, `parvulo`, and
other families can evolve without hard-coding every rule into one script.
