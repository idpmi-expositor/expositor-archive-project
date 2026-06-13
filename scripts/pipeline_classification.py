"""Shared publication classification helpers.

These helpers keep generated output paths grouped by Expositor audience, such
as maestro, alumno, joven, nino, and parvulo. The names are ASCII on disk so
they are easy to use from PowerShell, GitHub Actions, and Google Drive syncs.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard for scripts that do not need profiles
    yaml = None


KNOWN_CLASSIFICATIONS = ("maestro", "alumno", "joven", "adolescente", "nino", "parvulo")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE_DIR = PROJECT_ROOT / "config" / "expositor_profiles"


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


def load_profile(classification: str, profile_dir: Path = DEFAULT_PROFILE_DIR) -> dict[str, Any]:
    """Load one Expositor family profile.

    Profiles are intentionally small YAML files. They make family differences
    visible to maintainers before those differences become script logic.
    """

    if yaml is None:
        raise RuntimeError("PyYAML is required to load Expositor family profiles.")

    profile_path = profile_dir / f"{classification}.yaml"
    if not profile_path.exists():
        profile_path = profile_dir / "unclassified.yaml"
    with profile_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{profile_path}: profile root must be a mapping")
    return data


def profile_for_publication(value: str | Path) -> dict[str, Any]:
    """Infer and load the profile for one source filename or publication id."""

    return load_profile(infer_publication_classification(value))


def profile_metadata(value: str | Path) -> dict[str, str]:
    """Return compact profile metadata for generated indexes and reports."""

    classification = infer_publication_classification(value)
    profile = load_profile(classification)
    return {
        "profile_id": str(profile.get("profile_id") or classification),
        "profile_version": str(profile.get("profile_version") or "0.0.0"),
        "publication_classification": classification,
    }
