"""Project-local launch-profile resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from houmao.agents.definition_parser import AgentPreset, parse_agent_preset
from houmao.project.catalog import LaunchProfileCatalogEntry, ProjectCatalog
from houmao.project.easy import TOOL_PROVIDER_MAP, SpecialistMetadata, load_specialist
from houmao.project.overlay import HoumaoProjectOverlay


@dataclass(frozen=True)
class ResolvedProjectLaunchProfile:
    """Resolved launch-profile entry plus current source context."""

    entry: LaunchProfileCatalogEntry
    prompt_overlay_text: str | None
    source_exists: bool
    source_path: Path | None
    recipe_name: str | None
    recipe_path: Path | None
    tool: str | None
    provider: str | None
    role_name: str | None
    specialist: SpecialistMetadata | None = None
    recipe: AgentPreset | None = None


def list_resolved_launch_profiles(
    *, overlay: HoumaoProjectOverlay
) -> list[ResolvedProjectLaunchProfile]:
    """Return every stored launch profile resolved against the current overlay state."""

    catalog = ProjectCatalog.from_overlay(overlay)
    return [
        resolve_launch_profile_entry(overlay=overlay, entry=entry)
        for entry in catalog.list_launch_profiles()
    ]


def resolve_launch_profile(
    *, overlay: HoumaoProjectOverlay, name: str
) -> ResolvedProjectLaunchProfile:
    """Resolve one named launch profile from the project catalog."""

    entry = ProjectCatalog.from_overlay(overlay).load_launch_profile(name)
    return resolve_launch_profile_entry(overlay=overlay, entry=entry)


def resolve_launch_profile_entry(
    *,
    overlay: HoumaoProjectOverlay,
    entry: LaunchProfileCatalogEntry,
) -> ResolvedProjectLaunchProfile:
    """Resolve one stored launch-profile entry plus its current source context."""

    prompt_overlay_text = None
    if entry.prompt_overlay_ref is not None:
        prompt_path = entry.prompt_overlay_ref.resolve(overlay)
        if prompt_path.is_file():
            prompt_overlay_text = prompt_path.read_text(encoding="utf-8").rstrip()

    if entry.source_kind == "specialist":
        try:
            specialist = load_specialist(overlay=overlay, name=entry.source_name)
        except (FileNotFoundError, ValueError):
            return ResolvedProjectLaunchProfile(
                entry=entry,
                prompt_overlay_text=prompt_overlay_text,
                source_exists=False,
                source_path=None,
                recipe_name=None,
                recipe_path=None,
                tool=None,
                provider=None,
                role_name=None,
            )
        recipe_path = specialist.resolved_preset_path(overlay)
        return ResolvedProjectLaunchProfile(
            entry=entry,
            prompt_overlay_text=prompt_overlay_text,
            source_exists=True,
            source_path=specialist.metadata_path,
            recipe_name=specialist.preset_name,
            recipe_path=recipe_path,
            tool=specialist.tool,
            provider=specialist.provider,
            role_name=specialist.role_name,
            specialist=specialist,
            recipe=parse_agent_preset(recipe_path) if recipe_path.is_file() else None,
        )

    recipe_path = (overlay.agents_root / "presets" / f"{entry.source_name}.yaml").resolve()
    if not recipe_path.is_file():
        return ResolvedProjectLaunchProfile(
            entry=entry,
            prompt_overlay_text=prompt_overlay_text,
            source_exists=False,
            source_path=recipe_path,
            recipe_name=entry.source_name,
            recipe_path=recipe_path,
            tool=None,
            provider=None,
            role_name=None,
        )
    recipe = parse_agent_preset(recipe_path)
    return ResolvedProjectLaunchProfile(
        entry=entry,
        prompt_overlay_text=prompt_overlay_text,
        source_exists=True,
        source_path=recipe_path,
        recipe_name=entry.source_name,
        recipe_path=recipe_path,
        tool=recipe.tool,
        provider=TOOL_PROVIDER_MAP.get(recipe.tool, recipe.tool),
        role_name=recipe.role_name,
        recipe=recipe,
    )


def launch_profile_defaults_payload(
    profile: ResolvedProjectLaunchProfile,
    *,
    include_prompt_overlay_text: bool = False,
) -> dict[str, Any]:
    """Return one operator-facing defaults payload for a resolved launch profile."""

    payload: dict[str, Any] = {}
    entry = profile.entry
    if entry.managed_agent_name is not None:
        payload["agent_name"] = entry.managed_agent_name
    if entry.managed_agent_id is not None:
        payload["agent_id"] = entry.managed_agent_id
    if entry.workdir is not None:
        payload["workdir"] = entry.workdir
    if entry.auth_name is not None:
        payload["auth"] = entry.auth_name
    if entry.operator_prompt_mode is not None:
        payload["prompt_mode"] = entry.operator_prompt_mode
    if entry.env_payload:
        payload["env"] = dict(entry.env_payload)
    if entry.mailbox_payload:
        payload["mailbox"] = entry.mailbox_payload
    if entry.posture_payload:
        payload["posture"] = entry.posture_payload
    if entry.prompt_overlay_mode is not None:
        overlay_payload: dict[str, Any] = {
            "mode": entry.prompt_overlay_mode,
            "present": profile.prompt_overlay_text is not None,
        }
        if include_prompt_overlay_text and profile.prompt_overlay_text is not None:
            overlay_payload["text"] = profile.prompt_overlay_text
        payload["prompt_overlay"] = overlay_payload
    return payload


def launch_profile_source_payload(profile: ResolvedProjectLaunchProfile) -> dict[str, Any]:
    """Return one operator-facing source payload for a resolved launch profile."""

    payload: dict[str, Any] = {
        "kind": profile.entry.source_kind,
        "name": profile.entry.source_name,
        "exists": profile.source_exists,
    }
    if profile.source_path is not None:
        payload["path"] = str(profile.source_path)
    if profile.recipe_name is not None:
        payload["recipe"] = profile.recipe_name
    if profile.recipe_path is not None:
        payload["recipe_path"] = str(profile.recipe_path)
    if profile.tool is not None:
        payload["tool"] = profile.tool
    if profile.provider is not None:
        payload["provider"] = profile.provider
    if profile.role_name is not None:
        payload["role_name"] = profile.role_name
    return payload
