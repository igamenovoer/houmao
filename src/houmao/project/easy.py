"""Project-local specialist helpers backed by the SQLite config catalog."""

from __future__ import annotations

from pathlib import Path

from houmao.project.catalog import (
    LaunchProfileCatalogEntry,
    ProjectCatalog,
    SpecialistCatalogEntry,
)
from houmao.project.overlay import HoumaoProjectOverlay

TOOL_PROVIDER_MAP: dict[str, str] = {
    "claude": "claude_code",
    "codex": "codex",
    "gemini": "gemini_cli",
}

TOOL_AUTH_FILE_FLAG_NAMES: dict[str, str] = {
    "claude": "claude_state.template.json",
    "codex": "auth.json",
    "gemini": "oauth_creds.json",
}

SpecialistMetadata = SpecialistCatalogEntry
EasyProfileMetadata = LaunchProfileCatalogEntry


def list_specialists(*, overlay: HoumaoProjectOverlay) -> list[SpecialistMetadata]:
    """Load every persisted specialist definition for one overlay."""

    return ProjectCatalog.from_overlay(overlay).list_specialists()


def load_specialist(*, overlay: HoumaoProjectOverlay, name: str) -> SpecialistMetadata:
    """Load one persisted specialist definition from the catalog."""

    return ProjectCatalog.from_overlay(overlay).load_specialist(name)


def remove_specialist_metadata(*, overlay: HoumaoProjectOverlay, name: str) -> Path:
    """Delete one persisted specialist definition from the catalog."""

    return ProjectCatalog.from_overlay(overlay).remove_specialist(name)


def list_profiles(*, overlay: HoumaoProjectOverlay) -> list[EasyProfileMetadata]:
    """Load every persisted easy-profile definition for one overlay."""

    catalog = ProjectCatalog.from_overlay(overlay)
    return [
        entry for entry in catalog.list_launch_profiles() if entry.profile_lane == "easy_profile"
    ]


def load_profile(*, overlay: HoumaoProjectOverlay, name: str) -> EasyProfileMetadata:
    """Load one persisted easy-profile definition from the catalog."""

    entry = ProjectCatalog.from_overlay(overlay).load_launch_profile(name)
    if entry.profile_lane != "easy_profile":
        raise FileNotFoundError(f"Easy profile `{name}` was not found: {overlay.catalog_path}")
    return entry


def remove_profile_metadata(*, overlay: HoumaoProjectOverlay, name: str) -> Path:
    """Delete one persisted easy-profile definition from the catalog."""

    load_profile(overlay=overlay, name=name)
    return ProjectCatalog.from_overlay(overlay).remove_launch_profile(name)
