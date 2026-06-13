"""Helpers for publication family classification and profile loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE_DIR = PROJECT_ROOT / "config" / "expositor_profiles"

KNOWN_CLASSIFICATIONS = (
    "maestro",
    "alumno",
    "joven",
    "adolescente",
    "nino",
    "parvulo",
)


def infer_publication_classification(publication_id: str) -> str:
    """Infer the publication family from its ID."""
    normalized_id = publication_id.lower()
    if "maestro" in normalized_id:
        return "maestro"
    if "alumno" in normalized_id:
        return "alumno"
    # Add more rules for other families
    return "unclassified"


def classified_relative_path(input_path: Path, input_dir: Path) -> Path:
    """Return a path with the classification subfolder."""
    classification = infer_publication_classification(input_path.stem)
    return Path(classification) / input_path.relative_to(input_dir)


def load_profile(classification: str) -> dict[str, Any]:
    """Load the YAML profile for a given classification."""
    if classification not in KNOWN_CLASSIFICATIONS:
        classification = "unclassified"

    profile_path = DEFAULT_PROFILE_DIR / f"{classification}.yaml"
    if not profile_path.exists():
        if classification == "unclassified":
            return {"profile_id": "unclassified", "expected_sections": []}
        raise FileNotFoundError(f"Profile not found for classification: {classification}")

    with profile_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Profile {profile_path} must be a YAML mapping.")
    return data


def profile_metadata(publication_id: str) -> dict[str, str]:
    """Return profile metadata for a given publication ID."""
    classification = infer_publication_classification(publication_id)
    profile = load_profile(classification)
    return {
        "publication_classification": classification,
        "profile_id": str(profile.get("profile_id", "unclassified")),
        "profile_version": str(profile.get("profile_version", "0.0.0")),
    }