# expositor-archive-project

Archival-grade canonical metadata repository for Expositor publications from Iglesia de Dios Pentecostal M.I.

This repository is reserved for deterministic archival processing only:

PDF -> RAW TEXT -> STRUCTURED DOCUMENT MODEL -> CANONICAL YAML

## Scope

This project preserves and structures lesson-level archival metadata for:

- Expositor Maestro
- Expositor Alumno
- Expositor Joven
- Expositor Adolescente
- Expositor Nino
- Expositor Parvulo

## Boundaries

This project does not include translation, multilingual workflows, publication rendering, HTML generation, PDF generation, EPUB generation, frontend systems, UI systems, or AI translation pipelines.

## Canonical Unit

The only canonical unit of truth is one lesson per YAML file.

## Pipeline Layers

- `scripts/ingestion/`: PDF discovery, source validation, intake logging, and raw text extraction.
- `scripts/structuring/`: deterministic cleanup, document structure detection, and lesson segmentation.
- `scripts/canonical/`: canonical YAML generation, schema validation, and index building.

Python script files are intentionally empty placeholders at this stage.
