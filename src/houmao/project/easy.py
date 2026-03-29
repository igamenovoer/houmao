"""Project-local specialist metadata helpers for `project easy`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any, Mapping

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


@dataclass(frozen=True)
class SpecialistMetadata:
    """Persisted high-level specialist metadata."""

    name: str
    tool: str
    provider: str
    credential_name: str
    role_name: str
    system_prompt_path: str
    preset_path: str
    auth_path: str
    skills: tuple[str, ...]
    metadata_path: Path | None = None

    @property
    def schema_version(self) -> int:
        """Return the persisted metadata schema version."""

        return 1

    def resolved_system_prompt_path(self, overlay: HoumaoProjectOverlay) -> Path:
        """Return the specialist prompt path resolved against the overlay root."""

        return (overlay.overlay_root / self.system_prompt_path).resolve()

    def resolved_preset_path(self, overlay: HoumaoProjectOverlay) -> Path:
        """Return the specialist preset path resolved against the overlay root."""

        return (overlay.overlay_root / self.preset_path).resolve()

    def resolved_auth_path(self, overlay: HoumaoProjectOverlay) -> Path:
        """Return the specialist auth path resolved against the overlay root."""

        return (overlay.overlay_root / self.auth_path).resolve()

    def resolved_skill_paths(self, overlay: HoumaoProjectOverlay) -> tuple[Path, ...]:
        """Return the managed skill roots for this specialist."""

        return tuple(
            (overlay.agents_root / "skills" / skill_name).resolve() for skill_name in self.skills
        )


def specialist_metadata_path(*, overlay: HoumaoProjectOverlay, name: str) -> Path:
    """Return the metadata path for one persisted specialist."""

    return (overlay.specialists_root / f"{name}.toml").resolve()


def list_specialists(*, overlay: HoumaoProjectOverlay) -> list[SpecialistMetadata]:
    """Load every persisted specialist definition for one overlay."""

    specialists_root = overlay.specialists_root
    if not specialists_root.is_dir():
        return []
    results: list[SpecialistMetadata] = []
    for candidate in sorted(specialists_root.glob("*.toml")):
        results.append(load_specialist(overlay=overlay, name=candidate.stem))
    return results


def load_specialist(*, overlay: HoumaoProjectOverlay, name: str) -> SpecialistMetadata:
    """Load one persisted specialist definition from disk."""

    metadata_path = specialist_metadata_path(overlay=overlay, name=name)
    try:
        with metadata_path.open("rb") as handle:
            payload = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Specialist `{name}` was not found: {metadata_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{metadata_path}: expected a top-level TOML table.")
    return _specialist_from_payload(payload=payload, metadata_path=metadata_path)


def save_specialist(*, overlay: HoumaoProjectOverlay, metadata: SpecialistMetadata) -> Path:
    """Persist one specialist metadata document under `.houmao/easy/specialists/`."""

    metadata_path = specialist_metadata_path(overlay=overlay, name=metadata.name)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(_render_specialist_toml(metadata), encoding="utf-8")
    return metadata_path


def remove_specialist_metadata(*, overlay: HoumaoProjectOverlay, name: str) -> Path:
    """Delete one persisted specialist metadata document."""

    metadata_path = specialist_metadata_path(overlay=overlay, name=name)
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Specialist `{name}` was not found: {metadata_path}")
    metadata_path.unlink()
    return metadata_path


def _specialist_from_payload(
    *,
    payload: Mapping[str, Any],
    metadata_path: Path,
) -> SpecialistMetadata:
    """Convert one parsed TOML payload into structured metadata."""

    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise ValueError(f"{metadata_path}: only schema_version=1 is supported.")
    name = _require_string(payload, "name", where=str(metadata_path))
    tool = _require_string(payload, "tool", where=str(metadata_path))
    provider = _require_string(payload, "provider", where=str(metadata_path))
    credential_name = _require_string(payload, "credential_name", where=str(metadata_path))
    role_name = _require_string(payload, "role_name", where=str(metadata_path))
    system_prompt_path = _require_string(payload, "system_prompt_path", where=str(metadata_path))
    preset_path = _require_string(payload, "preset_path", where=str(metadata_path))
    auth_path = _require_string(payload, "auth_path", where=str(metadata_path))
    skills = _require_string_list(payload, "skills", where=str(metadata_path))
    return SpecialistMetadata(
        name=name,
        tool=tool,
        provider=provider,
        credential_name=credential_name,
        role_name=role_name,
        system_prompt_path=system_prompt_path,
        preset_path=preset_path,
        auth_path=auth_path,
        skills=tuple(skills),
        metadata_path=metadata_path,
    )


def _render_specialist_toml(metadata: SpecialistMetadata) -> str:
    """Render one stable specialist metadata document."""

    lines = [
        "schema_version = 1",
        f'name = "{_escape_toml_string(metadata.name)}"',
        f'tool = "{_escape_toml_string(metadata.tool)}"',
        f'provider = "{_escape_toml_string(metadata.provider)}"',
        f'credential_name = "{_escape_toml_string(metadata.credential_name)}"',
        f'role_name = "{_escape_toml_string(metadata.role_name)}"',
        f'system_prompt_path = "{_escape_toml_string(metadata.system_prompt_path)}"',
        f'preset_path = "{_escape_toml_string(metadata.preset_path)}"',
        f'auth_path = "{_escape_toml_string(metadata.auth_path)}"',
        "skills = ["
        + ", ".join(f'"{_escape_toml_string(skill_name)}"' for skill_name in metadata.skills)
        + "]",
        "",
    ]
    return "\n".join(lines)


def _require_string(payload: Mapping[str, Any], key: str, *, where: str) -> str:
    """Return one required non-empty string field."""

    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}: missing string `{key}`.")
    return value.strip()


def _require_string_list(payload: Mapping[str, Any], key: str, *, where: str) -> list[str]:
    """Return one required string list field."""

    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"{where}: expected `{key}` to be a list of non-empty strings.")
    return [item.strip() for item in value]


def _escape_toml_string(value: str) -> str:
    """Escape one string for use in a TOML basic string."""

    return value.replace("\\", "\\\\").replace('"', '\\"')
