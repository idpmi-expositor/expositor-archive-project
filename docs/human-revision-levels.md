# Human Revision And Review Levels

This repository uses two related but different ideas:

- **Human revision** means a normal maintainer can read, configure, and run the
  Python scripts without knowing Python.
- **Human review** means a person has compared generated lesson data against
  source evidence and accepted it for canonical use.

Automation can improve drafts, but it does not replace human review. The review
level must remain visible in generated artifacts and in any promotion decision.

## Plain-Language Script Standard

Every operating document and Python script should be understandable to a
non-programmer maintainer. A maintainer should be able to answer these questions
without reading Python code:

- What command should I run?
- Which folder does it read?
- Which folder does it write?
- Is it safe to rerun?
- Can it overwrite source or raw extraction files?
- Does it create draft data or canonical data?
- What does a warning or blocked status mean?
- What should I check before promoting a file?

Python files should keep configuration near the top, use descriptive argument
names, and include comments/docstrings that explain the script's pipeline role
in plain language.

## Data Review Levels

| Level | Meaning | Allowed location | Indexable |
| --- | --- | --- | --- |
| `generated_placeholder` | Schema-shaped scaffold data with unresolved placeholders. | `archive/drafts` | No |
| `automated_unreviewed` | Deterministic extraction populated draft fields, but no human has accepted them as canonical. | `archive/drafts` | No |
| `human_reviewed` | A reviewer compared the lesson against source evidence, resolved quality issues, and accepted the values. | `archive/lessons` after validation | Yes |

## Current Operating Rule

Human review may be skipped while improving the pipeline and regenerating
drafts. When that happens:

- generated YAML must remain under `archive/drafts`
- `processing_audit.manual_review_required` must remain `true`
- `processing_audit.review_status` must remain `automated_unreviewed` or another
  non-reviewed value
- `processing_status.human_review_completed` must remain `false`
- `archive/lessons` must not receive the file
- indexes must not be generated from the draft

This lets maintainers advance architecture, extraction, and normalization work
without weakening the canonical boundary. Human revision still applies: the
commands, configuration, and warnings must remain readable to maintainers who do
not know Python.

## Promotion Rule

Only the `human_reviewed` level may be promoted to canonical YAML. A reviewer
must verify source traceability, OCR quality, section content, scripture
references, placeholders, and validation output before moving a lesson into
`archive/lessons`.

## Review Status Values

Use these values consistently:

- `pending`: generated scaffold still needs automated extraction or review
- `automated_unreviewed`: automated extraction was applied but human review is
  not complete
- `human_reviewed`: reviewer accepted the lesson for canonical validation
- `rejected`: reviewer found blockers that prevent promotion

Canonical YAML must not use `pending` or `automated_unreviewed`.
