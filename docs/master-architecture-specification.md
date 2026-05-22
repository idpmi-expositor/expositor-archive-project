# Regenerated Master Architecture Specification

Canonical Archive System for Expositor de la Iglesia de Dios Pentecostal M.I.

This document consolidates, normalizes, and refines all previously agreed architectural decisions into a single authoritative design specification intended for long-term continuation inside ChatGPT, Codex, GitHub planning, and future implementation discussions.

# Master Archive Project Design Specification

## Project Name

expositor-archive-project

## 1. System Purpose

The Archive Project is a long-term canonical archival and semantic structuring system for theological educational publications produced by the Iglesia de Dios Pentecostal M.I.

The system is responsible for preserving and structuring:

- Expositor Maestro
- Expositor Alumno
- Expositor Joven
- Expositor Adolescente
- Expositor Niño
- Expositor Párvulo

The architecture must support:

- 20+ years of publications
- thousands of lessons
- recurring publication cycles
- future OCR reprocessing
- semantic indexing
- AI-assisted downstream processing
- Git-based archival maintenance

## 2. Strict Scope Boundaries

The Archive Project MUST NOT include:

- translation systems
- multilingual workflows
- publication rendering
- HTML generation
- PDF generation
- EPUB generation
- frontend applications
- UI systems
- website rendering
- AI translation pipelines
- formatting engines

These belong to downstream systems outside the Archive Project.

## 3. Core Architectural Principle

The Archive Project exists exclusively to transform source publications into canonical structured metadata.

Canonical processing flow:

```text
PDF -> RAW TEXT -> STRUCTURED DOCUMENT MODEL -> CANONICAL YAML
```

## 4. Canonical Unit of Truth

The ONLY canonical content unit is:

```text
LESSON
```

The following are NOT canonical units:

- PDF
- booklet
- page
- publication cycle
- teaching unit

Lesson-level YAML metadata is the permanent canonical representation.

## 5. Architectural Layers

The system must use a strict three-layer deterministic pipeline.

### Layer 1: Ingestion

Responsibilities:

- discover PDFs
- validate source files
- preserve immutable source assets
- extract raw text
- preserve page boundaries
- maintain intake logs

Rules:

INGESTION performs:

- NO semantic interpretation
- NO heading detection
- NO lesson segmentation
- NO YAML generation

### Layer 2: Structuring

Responsibilities:

- minimal text normalization
- deterministic structure detection
- lesson boundary segmentation
- structural metadata mapping
- intermediate model creation

Rules:

STRUCTURING performs:

- NO publication rendering
- NO semantic inference
- NO AI heuristics
- NO YAML generation

### Layer 3: Canonical Output

Responsibilities:

- convert structured models into YAML
- enforce strict schemas
- validate metadata integrity
- build indexes
- maintain canonical lesson archive

## 6. Determinism Requirement

All processing must be reproducible.

Given identical source inputs, the system must generate identical outputs.

The architecture prioritizes:

- reproducibility
- auditability
- traceability
- consistency
- long-term durability

over:

- heuristic convenience
- probabilistic inference
- AI interpretation

## 7. OCR Rules

OCR is strictly extraction-only.

OCR MAY:

- extract text
- preserve page boundaries
- preserve positional ordering

OCR MUST NOT:

- infer headings
- infer lesson boundaries
- merge semantic blocks
- reorganize paragraphs
- classify sections
- interpret structure

TXT output is temporary and non-canonical.

TXT exists only as an intermediary OCR artifact.

## 8. Required Intermediate Model

A mandatory intermediate structured representation must exist between OCR text and canonical YAML.

Required model:

```text
DocumentStructure
```

Purpose:

The intermediate model isolates:

- OCR concerns
- structural detection
- semantic organization
- canonical serialization

This separation prevents:

- schema pollution
- OCR coupling
- YAML contamination
- future migration instability

## 9. Lesson Segmentation Policy

Lesson segmentation must be deterministic and rule-based only.

Allowed segmentation signals:

- "LECCIÓN X"
- explicit lesson headers
- predefined publication markers
- known structural formatting patterns

Forbidden:

- AI inference
- probabilistic segmentation
- heuristic guessing
- semantic prediction

## 10. Schema Architecture

The metadata system must use inheritance-based schema normalization.

Required hierarchy:

```text
BaseExpositorSchema
|
+-- MaestroExtension
+-- AlumnoExtension
+-- JovenExtension
+-- AdolescenteExtension
+-- NinoExtension
+-- ParvuloExtension
```

## 11. Schema Principles

Schemas must be:

- strict
- deterministic
- normalized
- versioned
- auditable
- extensible
- human-readable
- Git-friendly

## 12. Required Root Metadata

Each lesson YAML file must contain:

```yaml
schema_version:
lesson_id:
publication_id:
collection_type:
year:
cycle:
title:
subtitle:
language:
page_range:
```

## 13. Required Processing Audit Metadata

```yaml
processing_audit:
  intake_date:
  ocr_engine:
  ocr_engine_version:
  extraction_method:
  extraction_confidence:
  manual_review_required:
  reviewed_by:
  review_status:
```

## 14. Required Source Integrity Metadata

```yaml
source_integrity:
  original_filename:
  sha256:
  imported_at:
  source_scan_quality:
```

## 15. Required Processing Status Metadata

```yaml
processing_status:
  intake_completed:
  ocr_completed:
  metadata_extracted:
  semantic_indexed:
  human_review_completed:
  yaml_generated:
  validated:
```

## 16. Required Source Traceability

Every extracted section must preserve source traceability.

```yaml
source_trace:
  source_pdf:
  page_start:
  page_end:
  extraction_block:
```

## 17. Scripture Normalization

All scripture references must be normalized into canonical structured metadata.

Required structure:

```yaml
canonical_reference:
  testament:
  book_standardized:
  chapter:
  verse_start:
  verse_end:
```

## 18. Semantic Metadata Requirements

Each lesson must contain semantic metadata.

```yaml
semantic_metadata:
  doctrinal_categories: []
  theological_themes: []
  educational_level:
  intended_audience:
```

## 19. Pedagogical Structure Requirements

The archive must preserve educational semantic structures including:

- lesson hierarchy
- scripture references
- outlines
- teacher notes
- vocabulary
- review questions
- bibliography
- educational metadata
- pedagogical sections

## 20. Lesson Storage Model

REQUIRED:

One YAML file per lesson.

FORBIDDEN:

One YAML file per booklet.

Why lesson-level YAML is mandatory:

Lesson-level architecture improves:

- Git diff readability
- OCR correction workflows
- semantic indexing
- AI chunking
- long-term scalability
- modular maintenance

## 21. Repository Structure

```text
expositor-archive-project/
|
+-- source_assets/
|   +-- original_pdfs/
|   +-- intake_logs/
|
+-- ocr/
|   +-- raw_txt/
|   +-- corrected_txt/
|   +-- processing_logs/
|
+-- normalized/
|   +-- maestro/
|   +-- alumno/
|   +-- joven/
|   +-- adolescente/
|   +-- nino/
|   +-- parvulo/
|
+-- structured/
|   +-- document_structure/
|
+-- archive/
|   +-- lessons/
|       +-- YYYY/
|           +-- CYCLE/
|               +-- LES-YYYY-CYCLE-XXX.yaml
|
+-- metadata/
|   +-- lessons/
|   +-- publications/
|   +-- scripture_indexes/
|   +-- semantic_indexes/
|
+-- schemas/
|   +-- base/
|   +-- extensions/
|
+-- indexes/
|   +-- lessons_index.yaml
|   +-- scripture_index.yaml
|   +-- topics_index.yaml
|
+-- scripts/
|   +-- ingestion/
|   +-- structuring/
|   +-- canonical/
|
+-- README.md
```

## 22. Script Grouping Strategy

The project uses three grouped processing layers rather than many disconnected scripts.

Rationale:

This improves:

- maintainability
- debugging
- rerun reliability
- pipeline stability
- operational clarity

## 23. Required Script Responsibilities

### Ingestion

#### 01_pdf_discovery.py

Responsibilities:

- scan PDFs
- validate source files
- register intake metadata
- generate intake logs

#### 02_pdf_to_raw_text.py

Responsibilities:

- direct extraction via PyMuPDF
- OCR fallback via Tesseract
- preserve page boundaries
- generate raw text artifacts

### Structuring

#### 03_minimal_text_normalizer.py

Responsibilities:

- unicode normalization
- whitespace cleanup
- broken hyphen correction
- minimal deterministic cleanup only

#### 04_document_structure_detector.py

Responsibilities:

- deterministic heading detection
- structural marker mapping
- lesson boundary detection
- intermediate DocumentStructure creation

#### 05_lesson_segmenter.py

Responsibilities:

- split documents into lessons
- assign stable IDs
- map source pages
- preserve traceability

### Canonical

#### 06_yaml_generator.py

Responsibilities:

- convert structured models into canonical YAML
- apply schema normalization
- serialize lesson metadata

#### 07_schema_validator.py

Responsibilities:

- validate required fields
- validate scripture structures
- enforce deterministic schema rules
- verify metadata completeness

#### 08_index_builder.py

Responsibilities:

- generate lesson indexes
- generate scripture indexes
- generate topic indexes
- generate semantic indexes

## 24. Required Indexes

The system must generate:

- lessons_index.yaml
- scripture_index.yaml
- topics_index.yaml

Additional indexes may include:

- doctrinal indexes
- publication indexes
- semantic theme indexes

## 25. Versioning Requirement

Every canonical YAML document must contain:

```yaml
schema_version: "1.0.0"
```

Future migrations must preserve backward compatibility.

## 26. Design Philosophy

This system is NOT:

- a PDF processing tool
- a translation engine
- a publication renderer

This system IS:

A canonical theological knowledge archive system.

Therefore the architecture prioritizes:

| Priority | Principle |
| --- | --- |
| 1 | Reproducibility |
| 2 | Determinism |
| 3 | Traceability |
| 4 | Structural consistency |
| 5 | Long-term maintainability |
| 6 | Semantic normalization |
| 7 | Archival durability |

## 27. Long-Term Archival Goals

The repository must remain stable across:

- 20+ years of publications
- schema migrations
- OCR engine upgrades
- semantic indexing improvements
- future downstream systems
- AI-assisted theological analysis

## 28. Final Architectural Constraint

The Archive Project must remain permanently independent from:

- translation systems
- publication systems
- rendering engines
- multilingual delivery systems

Those must consume canonical YAML downstream without modifying archival truth.

## 29. Final System Definition

The final system is:

- archival-grade
- deterministic
- reproducible
- auditable
- schema-driven
- lesson-centric
- semantically normalized
- AI-compatible
- Git-scalable
- operationally maintainable for decades
