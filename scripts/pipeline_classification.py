"""Shared publication classification helpers.

These helpers keep generated output paths grouped by Expositor audience, such
as maestro, alumno, joven, nino, and parvulo. The names are ASCII on disk so
they are easy to use from PowerShell, GitHub Actions, and Google Drive syncs.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path


KNOWN_CLASSIFICATIONS = ("maestro", "alumno", "joven", "adolescente", "nino", "parvulo")


def normalize_for_classification(value: str) -> str:
    """Return lowercase ASCII-ish text for filename classification checks."""

    decomposed = unicodedata.normalize("NFD", value)
    without_accents = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )
    return without_accents.lower()


def infer_publication_classification(value: str | Path) -> str:
    """Infer the Expositor audience folder from a filename or publication id."""

    normalized = normalize_for_classification(str(value))
    for classification in KNOWN_CLASSIFICATIONS:
        if classification in normalized:
            return classification
    return "unclassified"


def classified_relative_path(path: Path, base_dir: Path) -> Path:
    """Return a path grouped under the inferred publication classification."""

    relative = path.relative_to(base_dir)
    if relative.parts and relative.parts[0] in (*KNOWN_CLASSIFICATIONS, "unclassified"):
        return relative
    return Path(infer_publication_classification(relative.stem)) / relative
