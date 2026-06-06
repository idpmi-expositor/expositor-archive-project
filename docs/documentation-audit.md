# Documentation Audit

This audit records the documentation issues found during review of
`README.md`, root operating documents, `docs/`, and the current script layout.
It is intentionally scoped to documentation. No pipeline logic changes are
required by this audit.

## Issues Found

- The previous `README.md` contained correct architecture details but combined
  onboarding, architecture, script inventory, OCR behavior, validation policy,
  and operational notes in one long sequence.
- The quick start path was implicit. New maintainers had to infer the minimal
  setup command and the first safe pipeline commands from the full command list.
- The main pipeline flow was described in text but did not include a single
  full artifact-level diagram from source PDFs to canonical indexes.
- Design principles were present across several documents but not grouped at
  the top level as operating constraints.
- Non-goals were listed, but the boundary against UI systems, AI translation,
  publishing, and non-YAML canonical formats needed a stronger top-level
  statement.
- Dependency expectations were split between `README.md`, `INSTALL.md`, and
  script import guards. The root README did not clearly distinguish Python
  package requirements from OS-level tooling such as `rclone` and Tesseract.
- Failure behavior was partially documented in `PROCESS.md` and OCR policy, but
  the README did not summarize what happens when validation, OCR fallback, or
  index building fails.
- Script responsibility descriptions were generally accurate, but the README
  needed clearer separation between pre-ingestion, ingestion, structuring, and
  canonical layers.
- `docs/master-architecture-specification.md` contained stale implementation
  wording that said OCR fallback was pending, while
  `scripts/ingestion/02_pdf_to_raw_text.py` implements Tesseract OCR fallback
  for weak or empty text-layer pages.
- `docs/master-architecture-specification.md` listed `topics_index.yaml` as a
  required generated index, while the current implemented index builder writes
  `lessons_index.yaml` and `scripture_index.yaml`. Documentation needed to
  distinguish current generated indexes from future possible indexes.
- Some architecture language mentioned future AI-adjacent downstream uses. That
  wording risked blurring the project boundary. The archive itself must remain
  deterministic and must not include AI or LLM translation pipelines.

## Documentation Structure

The repository should use this documentation layout:

```text
README.md                              Top-level orientation and operating summary.
INSTALL.md                             Environment and dependency setup.
PROCESS.md                             End-to-end execution order and review gates.
CONTRIBUTING.md                        Contribution and PR expectations.
docs/master-architecture-specification.md
                                       Authoritative architecture constraints.
docs/pipeline-traceability.md          Artifact chain and review tracing.
docs/lesson-yaml-contract.md           Canonical YAML validation contract.
docs/ocr-quality-policy.md             OCR review and blocking conditions.
docs/human-review-checklist.md         Manual review checklist.
docs/draft-to-canonical-promotion.md   Promotion workflow.
docs/production-ready-canonical-yaml.md
                                       Production readiness criteria.
docs/google-drive-sync.md              Source sync validation.
docs/architectural-validation.md       Architecture validation report.
docs/documentation-audit.md            Documentation audit and structure record.
```

## Improvements Applied

- Rewrote `README.md` to provide a quick start, explicit non-goals, an
  artifact-level architecture diagram, design principles, dependency summary,
  failure behavior, and clear script responsibility definitions.
- Kept the core pipeline definition unchanged:
  `PDF -> RAW TEXT -> STRUCTURED DOCUMENT MODEL -> CANONICAL YAML`.
- Preserved the rule that one lesson equals one canonical YAML file.
- Preserved the draft-to-canonical separation: generated YAML remains under
  `archive/drafts` until human review and validation are complete.
- Clarified that OCR fallback is extraction-only and does not perform structure
  detection, lesson segmentation, or semantic inference.
- Clarified that indexes are built only from reviewed canonical YAML.
- Corrected stale architecture text so implemented OCR fallback and current
  index outputs are represented accurately.

## Remaining Documentation Risks

- If future scripts add new generated indexes, update `README.md`, `PROCESS.md`,
  and `docs/master-architecture-specification.md` at the same time.
- If canonical schema fields change, update
  `docs/lesson-yaml-contract.md`, `schemas/base/lesson_schema.yaml`, and the
  validator documentation together.
- If OCR thresholds or fallback behavior change, update
  `docs/ocr-quality-policy.md` and the README failure behavior section.
