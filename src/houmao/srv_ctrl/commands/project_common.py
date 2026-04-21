"""Shared helpers for project-overlay command modules."""

from __future__ import annotations

# ruff: noqa: F401
import os
import shutil
from pathlib import Path
from typing import Any, Literal, cast

import click
import yaml

from houmao.agents.definition_parser import ToolAdapter, parse_agent_preset, parse_tool_adapter
from houmao.agents.launch_env import (
    parse_persistent_env_record_specs,
    resolve_runtime_env_set_specs,
    validate_persistent_env_records,
)
from houmao.agents.launch_policy.models import OperatorPromptMode
from houmao.agents.managed_prompt_header import (
    ManagedHeaderPolicy,
    ManagedHeaderSectionName,
    ManagedHeaderSectionPolicy,
    parse_managed_header_section_names,
    parse_managed_header_section_policy_assignments,
)
from houmao.agents.mailbox_runtime_support import (
    parse_declarative_mailbox_config,
    serialize_declarative_mailbox_config,
)
from houmao.agents.model_selection import (
    ModelConfig,
    model_config_to_payload,
    normalize_model_config,
)
from houmao.agents.realm_controller.gateway_models import (
    GatewayCurrentExecutionMode,
    GatewayTuiTrackingTimingOverridesV1,
)
from houmao.agents.realm_controller.manifest import load_session_manifest
from houmao.project.catalog import AuthProfileCatalogEntry, ProjectCatalog, ProjectSkillCatalogEntry
from houmao.project.easy import (
    SpecialistMetadata,
    TOOL_PROVIDER_MAP,
    list_specialists,
    load_specialist,
    remove_profile_metadata,
    remove_specialist_metadata,
)
from houmao.project.launch_profiles import (
    launch_profile_defaults_payload,
    launch_profile_relaunch_payload,
    launch_profile_source_payload,
    list_resolved_launch_profiles,
    resolve_launch_profile,
)
from houmao.project.overlay import (
    HoumaoProjectOverlay,
    ProjectAwareLocalRoots,
    bootstrap_project_overlay_at_root,
    ensure_project_aware_local_roots,
    ensure_project_agent_compatibility_tree,
    materialize_project_agent_catalog_projection,
    resolve_project_init_overlay_root,
    resolve_project_aware_local_roots,
)

from .credentials import ensure_specialist_credential_bundle
from .agents.core import emit_local_launch_completion, launch_managed_agent_locally
from .cleanup_support import emit_cleanup_payload
from .common import (
    build_destructive_confirmation_callback,
    confirm_destructive_action,
    managed_launch_force_option,
    overwrite_confirm_option,
)
from .output import emit
from .mailbox_support import (
    clear_mailbox_messages_at_root,
    cleanup_mailbox_root,
    export_mailbox_root,
    get_mailbox_account,
    get_mailbox_message,
    init_mailbox_root,
    list_mailbox_accounts,
    list_mailbox_messages,
    mailbox_root_status_payload,
    register_mailbox_at_root,
    repair_mailbox_root,
    unregister_mailbox_at_root,
)
from .managed_agents import list_managed_agents, resolve_managed_agent_target, stop_managed_agent
from .project_aware_wording import (
    describe_overlay_bootstrap,
    describe_overlay_discovery_mode,
    describe_overlay_root_selection_source,
)

_SUPPORTED_PROJECT_TOOLS: tuple[str, ...] = ("claude", "codex", "gemini")
_LaunchProfileStoreOperation = Literal["create", "patch", "replace"]
_RELAUNCH_CHAT_SESSION_MODES: tuple[str, ...] = ("new", "tool_last_or_new", "exact")


def _ensure_project_roots() -> ProjectAwareLocalRoots:
    """Return ensured project-aware roots or raise one operator-facing error."""

    try:
        roots = ensure_project_aware_local_roots(cwd=Path.cwd().resolve())
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if roots.project_overlay is None:
        raise click.ClickException("Failed to ensure the active project overlay.")
    return roots


def _ensure_project_overlay() -> HoumaoProjectOverlay:
    """Return the ensured selected project overlay."""

    overlay = _ensure_project_roots().project_overlay
    assert overlay is not None
    return overlay


def _resolve_existing_project_roots(
    *,
    fallback_label: str | None = None,
) -> ProjectAwareLocalRoots:
    """Return the selected roots for one non-creating project flow."""

    try:
        roots = resolve_project_aware_local_roots(cwd=Path.cwd().resolve())
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if roots.project_overlay is None:
        raise click.ClickException(
            _missing_selected_overlay_message(roots=roots, fallback_label=fallback_label)
        )
    return roots


def _resolve_existing_project_overlay(
    *,
    fallback_label: str | None = None,
) -> HoumaoProjectOverlay:
    """Return the active selected overlay for non-creating project flows."""

    overlay = _resolve_existing_project_roots(fallback_label=fallback_label).project_overlay
    assert overlay is not None
    return overlay


def _selected_overlay_detail(roots: ProjectAwareLocalRoots) -> str:
    """Describe the selected overlay root for one invocation."""

    detail = describe_overlay_root_selection_source(
        overlay_root_source=roots.overlay_root_source,
        overlay_discovery_mode=roots.overlay_discovery_mode,
    )
    if roots.project_overlay is None:
        return (
            f"{detail} No project overlay exists yet at `{roots.overlay_root}` for this invocation."
        )
    return detail


def _status_overlay_bootstrap_detail(roots: ProjectAwareLocalRoots) -> str:
    """Describe the bootstrap outcome for `project status`."""

    if roots.project_overlay is None:
        return (
            "Project status used non-creating resolution and would bootstrap the selected overlay "
            "during a stateful project command."
        )
    return describe_overlay_bootstrap(created_overlay=False, overlay_exists=True)


def _missing_selected_overlay_message(
    *,
    roots: ProjectAwareLocalRoots,
    fallback_label: str | None = None,
) -> str:
    """Build one non-creating selected-overlay failure message."""

    message = (
        "No Houmao project overlay is available at the selected overlay root "
        f"`{roots.overlay_root}`. This command uses non-creating resolution and did not "
        "bootstrap it."
    )
    if fallback_label is not None:
        return f"{message} It did not fall back to the {fallback_label}."
    return message


def _list_tool_setup_names(*, overlay: HoumaoProjectOverlay, tool: str) -> list[str]:
    """Return the existing setup names for one tool."""

    setups_root = (_tool_root(overlay=overlay, tool=tool) / "setups").resolve()
    if not setups_root.is_dir():
        return []
    return sorted(path.name for path in setups_root.iterdir() if path.is_dir())


def _list_tool_bundle_names(*, overlay: HoumaoProjectOverlay, tool: str) -> list[str]:
    """Return the existing auth bundle names for one tool."""

    return [
        profile.display_name
        for profile in ProjectCatalog.from_overlay(overlay).list_auth_profiles(tool=tool)
    ]


def _load_auth_profile_or_click(
    *,
    overlay: HoumaoProjectOverlay,
    tool: str,
    name: str,
) -> AuthProfileCatalogEntry:
    """Load one auth profile or raise one operator-facing error."""

    resolved_name = _require_non_empty_name(name, field_name="--name")
    try:
        return ProjectCatalog.from_overlay(overlay).load_auth_profile(tool=tool, name=resolved_name)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc


def _load_auth_profile_optional(
    *,
    overlay: HoumaoProjectOverlay,
    tool: str,
    name: str,
) -> AuthProfileCatalogEntry | None:
    """Load one auth profile when present."""

    try:
        return ProjectCatalog.from_overlay(overlay).load_auth_profile(tool=tool, name=name)
    except FileNotFoundError:
        return None


def _auth_source_root(*, overlay: HoumaoProjectOverlay, profile: AuthProfileCatalogEntry) -> Path:
    """Return the authoritative managed-content root for one auth profile."""

    return profile.content_ref.resolve(overlay)


def _tool_root(*, overlay: HoumaoProjectOverlay, tool: str) -> Path:
    """Return one project-local tool root."""

    ensure_project_agent_compatibility_tree(overlay)
    return (overlay.agents_root / "tools" / tool).resolve()


def _tool_setup_path(*, overlay: HoumaoProjectOverlay, tool: str, name: str) -> Path:
    """Return one project-local tool setup root."""

    return (_tool_root(overlay=overlay, tool=tool) / "setups" / name).resolve()


def _role_root(*, overlay: HoumaoProjectOverlay, role_name: str) -> Path:
    """Return one project-local role root."""

    ensure_project_agent_compatibility_tree(overlay)
    return (overlay.agents_root / "roles" / role_name).resolve()


def _presets_root(*, overlay: HoumaoProjectOverlay) -> Path:
    """Return the project-local named preset root."""

    ensure_project_agent_compatibility_tree(overlay)
    return (overlay.agents_root / "presets").resolve()


def _preset_path(*, overlay: HoumaoProjectOverlay, preset_name: str) -> Path:
    """Return one canonical project-local named preset path."""

    return (_presets_root(overlay=overlay) / f"{preset_name}.yaml").resolve()


def _list_role_names(*, overlay: HoumaoProjectOverlay) -> list[str]:
    """Return the current project-local role names."""

    ensure_project_agent_compatibility_tree(overlay)
    roles_root = (overlay.agents_root / "roles").resolve()
    if not roles_root.is_dir():
        return []
    return sorted(path.name for path in roles_root.iterdir() if path.is_dir())


def _role_summary(
    *,
    overlay: HoumaoProjectOverlay,
    role_name: str,
    include_prompt: bool = False,
) -> dict[str, object]:
    """Return one structured project-local role summary."""

    role_root = _role_root(overlay=overlay, role_name=role_name)
    prompt_path = (role_root / "system-prompt.md").resolve()
    payload: dict[str, object] = {
        "name": role_name,
        "role_path": str(role_root),
        "system_prompt_path": str(prompt_path),
        "system_prompt_exists": prompt_path.is_file(),
        "recipes": _list_named_preset_summaries(overlay=overlay, role_name=role_name),
    }
    if include_prompt:
        payload["system_prompt_text"] = (
            prompt_path.read_text(encoding="utf-8").rstrip() if prompt_path.is_file() else ""
        )
    return payload


def _list_named_preset_summaries(
    *,
    overlay: HoumaoProjectOverlay,
    role_name: str | None = None,
    tool: str | None = None,
) -> list[dict[str, object]]:
    """Return named preset summaries, optionally filtered by role and tool."""

    presets_root = _presets_root(overlay=overlay)
    if not presets_root.is_dir():
        return []
    results: list[dict[str, object]] = []
    for preset_file in sorted(path for path in presets_root.iterdir() if path.is_file()):
        if preset_file.suffix not in {".yaml", ".yml"}:
            continue
        parsed_preset = _parse_preset_or_click(preset_file)
        if role_name is not None and parsed_preset.role_name != role_name:
            continue
        if tool is not None and parsed_preset.tool != tool:
            continue
        results.append(_preset_summary(overlay=overlay, preset_name=parsed_preset.name))
    return results


def _preset_summary(
    *,
    overlay: HoumaoProjectOverlay,
    preset_name: str,
) -> dict[str, object]:
    """Return one structured project-local preset summary."""

    preset_file = _preset_path(overlay=overlay, preset_name=preset_name)
    if not preset_file.is_file():
        raise click.ClickException(f"Preset not found: {preset_file}")
    parsed_preset = _parse_preset_or_click(preset_file)
    raw_payload = _load_yaml_mapping(preset_file)
    launch_payload = raw_payload.get("launch")
    return {
        "name": parsed_preset.name,
        "role": parsed_preset.role_name,
        "tool": parsed_preset.tool,
        "setup": parsed_preset.setup,
        "path": str(preset_file),
        "skills": list(parsed_preset.skills),
        "auth": parsed_preset.auth,
        "launch": launch_payload if isinstance(launch_payload, dict) else {},
        "mailbox": raw_payload.get("mailbox"),
        "extra": raw_payload.get("extra", {}),
    }


def _write_role_prompt(*, role_root: Path, prompt_text: str, overwrite: bool = False) -> Path:
    """Write one canonical role prompt file."""

    role_root.mkdir(parents=True, exist_ok=overwrite)
    prompt_path = (role_root / "system-prompt.md").resolve()
    if prompt_path.exists() and prompt_path.is_dir():
        raise click.ClickException(f"Prompt path already exists as a directory: {prompt_path}")
    prompt_path.write_text(
        prompt_text.rstrip() + "\n" if prompt_text.strip() else "",
        encoding="utf-8",
    )
    return prompt_path


def _canonical_preset_name(*, role_name: str, tool: str, setup: str) -> str:
    """Return the default deterministic preset name for one role/tool/setup tuple."""

    return f"{role_name}-{tool}-{setup}"


def _ensure_role_exists(*, overlay: HoumaoProjectOverlay, role_name: str) -> None:
    """Fail clearly when one project-local role root is missing."""

    role_root = _role_root(overlay=overlay, role_name=role_name)
    if not role_root.is_dir():
        raise click.ClickException(f"Role not found: {role_root}")


def _ensure_unique_preset_tuple(
    *,
    overlay: HoumaoProjectOverlay,
    preset_name: str,
    role_name: str,
    tool: str,
    setup: str,
) -> None:
    """Reject duplicate `(role, tool, setup)` tuples across named presets."""

    for summary in _list_named_preset_summaries(overlay=overlay):
        if str(summary["name"]) == preset_name:
            continue
        if (
            str(summary["role"]) == role_name
            and str(summary["tool"]) == tool
            and str(summary["setup"]) == setup
        ):
            raise click.ClickException(
                "Recipe `(role, tool, setup)` tuples must remain unique across "
                f"`.houmao/agents/presets/`: `{role_name}`, `{tool}`, `{setup}` is already "
                f"owned by `{summary['name']}`."
            )


def _write_named_preset(
    *,
    overlay: HoumaoProjectOverlay,
    preset_name: str,
    role_name: str,
    tool: str,
    setup: str,
    skills: list[str],
    auth: str | None,
    prompt_mode: str | None,
    model_config: ModelConfig | None = None,
    env_records: dict[str, str] | None = None,
    overwrite: bool = False,
) -> Path:
    """Write one canonical project-local named preset."""

    _ensure_role_exists(overlay=overlay, role_name=role_name)
    preset_file = _preset_path(overlay=overlay, preset_name=preset_name)
    if preset_file.exists() and not overwrite:
        raise click.ClickException(f"Preset already exists: {preset_file}")
    _ensure_unique_preset_tuple(
        overlay=overlay,
        preset_name=preset_name,
        role_name=role_name,
        tool=tool,
        setup=setup,
    )
    resolved_prompt_mode = prompt_mode or "unattended"
    payload: dict[str, Any] = {
        "role": role_name,
        "tool": tool,
        "setup": setup,
        "skills": list(skills),
    }
    if auth is not None:
        payload["auth"] = auth
    payload["launch"] = {"prompt_mode": resolved_prompt_mode}
    model_payload = _model_mapping_payload(model_config)
    if model_payload is not None:
        payload["launch"]["model"] = model_payload
    if env_records:
        payload["launch"]["env_records"] = dict(env_records)
    _write_yaml_mapping(preset_file, payload)
    return preset_file


def _prepare_specialist_projection_for_replace(*, role_root: Path, preset_path: Path) -> None:
    """Clear specialist-owned generated projection paths before one replacement write."""

    if not role_root.exists():
        preset_path.unlink(missing_ok=True)
        return
    prompt_path = (role_root / "system-prompt.md").resolve()
    if prompt_path.is_dir():
        raise click.ClickException(f"Prompt path already exists as a directory: {prompt_path}")
    prompt_path.unlink(missing_ok=True)
    preset_path.unlink(missing_ok=True)


def _ensure_skill_placeholder(*, overlay: HoumaoProjectOverlay, skill_name: str) -> Path | None:
    """Create one placeholder skill directory when it is currently missing."""

    ensure_project_agent_compatibility_tree(overlay)
    skill_root = (overlay.agents_root / "skills" / skill_name).resolve()
    skill_doc = (skill_root / "SKILL.md").resolve()
    if skill_doc.is_file():
        return None
    skill_root.mkdir(parents=True, exist_ok=True)
    skill_doc.write_text(
        f"# {skill_name}\n\nReplace this placeholder skill with real project-local instructions.\n",
        encoding="utf-8",
    )
    return skill_root


def _clone_tool_setup_if_missing(
    *,
    overlay: HoumaoProjectOverlay,
    tool: str,
    target_name: str,
    source_name: str,
) -> Path | None:
    """Clone one tool setup into a missing target path."""

    target_path = _tool_setup_path(overlay=overlay, tool=tool, name=target_name)
    if target_path.exists():
        return None
    source_path = _tool_setup_path(overlay=overlay, tool=tool, name=source_name)
    if not source_path.is_dir():
        raise click.ClickException(f"Source setup bundle not found: {source_path}")
    shutil.copytree(source_path, target_path)
    return target_path


def _ensure_placeholder_auth_bundle(
    *,
    overlay: HoumaoProjectOverlay,
    tool: str,
    name: str,
) -> list[Path]:
    """Create one placeholder auth bundle when it is missing."""

    auth_root = _auth_bundle_root(overlay=overlay, tool=tool, name=name)
    if auth_root.is_dir():
        return []
    adapter = _load_overlay_tool_adapter(overlay=overlay, tool=tool)
    env_file_path = _auth_bundle_env_file(overlay=overlay, tool=tool, name=name)
    files_root = (auth_root / adapter.auth_files_dir).resolve()
    env_file_path.parent.mkdir(parents=True, exist_ok=True)
    files_root.mkdir(parents=True, exist_ok=True)
    env_file_path.write_text(
        "\n".join(
            ["# Fill in the required auth values for this bundle."]
            + [f"# {env_name}=" for env_name in adapter.auth_env_allowlist]
        )
        + "\n",
        encoding="utf-8",
    )
    created_paths: list[Path] = [auth_root, env_file_path]
    for mapping in adapter.auth_file_mappings:
        if not mapping.required:
            continue
        target_path = (files_root / mapping.source).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text("{}\n", encoding="utf-8")
        created_paths.append(target_path)
    return created_paths


def _validate_specialist_create_inputs(
    *,
    overlay: HoumaoProjectOverlay,
    specialist_name: str,
    system_prompt: str | None,
    system_prompt_file: Path | None,
) -> str | None:
    """Validate project easy specialist creation inputs."""

    if system_prompt is not None and system_prompt_file is not None:
        raise click.ClickException(
            "Provide at most one of `--system-prompt` or `--system-prompt-file`."
        )
    conflict_reasons: list[str] = []
    if ProjectCatalog.from_overlay(overlay).specialist_exists(specialist_name):
        conflict_reasons.append(f"catalog entry in `{overlay.catalog_path}`")
    role_root = _role_root(overlay=overlay, role_name=specialist_name)
    if role_root.exists():
        conflict_reasons.append(f"role projection at `{role_root}`")
    if not conflict_reasons:
        return None
    return ", ".join(conflict_reasons)


def _resolve_system_prompt_text(
    *,
    system_prompt: str | None,
    system_prompt_file: Path | None,
) -> str:
    """Resolve specialist system prompt content from inline or file input."""

    if system_prompt is not None:
        value = system_prompt.strip()
        if not value:
            raise click.ClickException("`--system-prompt` must not be empty.")
        return value
    if system_prompt_file is None:
        return ""
    return system_prompt_file.read_text(encoding="utf-8").rstrip()


def _import_skill_directories(
    *,
    overlay: HoumaoProjectOverlay,
    skill_dirs: tuple[Path, ...],
) -> list[Path]:
    """Copy or reuse skill directories under `.houmao/agents/skills/`."""

    ensure_project_agent_compatibility_tree(overlay)
    imported: list[Path] = []
    for skill_dir in skill_dirs:
        source_dir = skill_dir.resolve()
        skill_doc = (source_dir / "SKILL.md").resolve()
        if not skill_doc.is_file():
            raise click.ClickException(f"Skill directory must contain `SKILL.md`: {source_dir}")
        destination_dir = (overlay.agents_root / "skills" / source_dir.name).resolve()
        if not destination_dir.exists():
            shutil.copytree(source_dir, destination_dir)
        elif not destination_dir.is_dir():
            raise click.ClickException(f"Skill destination is not a directory: {destination_dir}")
        imported.append(destination_dir)
    return imported


def _parse_specialist_env_records_or_click(
    *,
    adapter: ToolAdapter,
    env_set: tuple[str, ...],
) -> dict[str, str]:
    """Parse and validate persistent specialist env records."""

    try:
        parsed = parse_persistent_env_record_specs(env_set)
        return validate_persistent_env_records(
            parsed,
            auth_env_allowlist=adapter.auth_env_allowlist,
            source="project easy specialist create --env-set",
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _resolve_instance_env_set_or_click(env_set: tuple[str, ...]) -> dict[str, str]:
    """Resolve one-off instance launch env bindings."""

    try:
        return resolve_runtime_env_set_specs(env_set, process_env=os.environ)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _load_recipe_or_click(*, overlay: HoumaoProjectOverlay, name: str) -> Any:
    """Load one project-local recipe or raise one operator-facing error."""

    recipe_name = _require_non_empty_name(name, field_name="--recipe")
    recipe_path = _preset_path(overlay=overlay, preset_name=recipe_name)
    if not recipe_path.is_file():
        raise click.ClickException(f"Recipe not found: {recipe_path}")
    return _parse_preset_or_click(recipe_path)


def _profile_lane_label(profile_lane: str) -> str:
    """Return one operator-facing launch-profile lane label."""

    if profile_lane == "easy_profile":
        return "easy-profile"
    if profile_lane == "launch_profile":
        return "launch-profile"
    return profile_lane


def _load_launch_profile_or_click(
    *,
    overlay: HoumaoProjectOverlay,
    name: str,
    expected_lane: str | None = None,
) -> Any:
    """Load one resolved launch profile or raise one operator-facing error."""

    try:
        resolved = resolve_launch_profile(overlay=overlay, name=name)
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    if expected_lane is not None and resolved.entry.profile_lane != expected_lane:
        lane_label = _profile_lane_label(expected_lane)
        raise click.ClickException(
            f"Launch profile `{name}` is not an available `{lane_label}` definition."
        )
    return resolved


def _resolve_launch_profile_create_operation_or_click(
    *,
    overlay: HoumaoProjectOverlay,
    profile_name: str,
    profile_lane: str,
    yes: bool,
) -> _LaunchProfileStoreOperation:
    """Return the create operation for one named profile, confirming replacement when needed."""

    catalog = ProjectCatalog.from_overlay(overlay)
    try:
        existing = catalog.load_launch_profile(profile_name)
    except FileNotFoundError:
        return "create"
    if existing.profile_lane != profile_lane:
        lane_label = _profile_lane_label(profile_lane)
        raise click.ClickException(
            f"Launch profile `{profile_name}` is not an available `{lane_label}` definition."
        )
    confirm_destructive_action(
        prompt=(
            f"Replace {_profile_lane_label(profile_lane)} `{profile_name}` in "
            f"`{overlay.catalog_path}`?"
        ),
        yes=yes,
        non_interactive_message=(
            f"Launch profile `{profile_name}` already exists in `{overlay.catalog_path}`. "
            "Rerun with `--yes` to replace it non-interactively."
        ),
        cancelled_message="Launch profile replacement cancelled.",
    )
    return "replace"


def _launch_profile_payload(
    *,
    overlay: HoumaoProjectOverlay,
    profile_name: str,
    expected_lane: str | None = None,
) -> dict[str, object]:
    """Return one operator-facing launch-profile payload."""

    resolved = _load_launch_profile_or_click(
        overlay=overlay,
        name=profile_name,
        expected_lane=expected_lane,
    )
    return _launch_profile_payload_from_resolved(overlay=overlay, resolved=resolved)


def _launch_profile_payload_from_resolved(
    *,
    overlay: HoumaoProjectOverlay,
    resolved: Any,
) -> dict[str, object]:
    """Return one operator-facing payload from a resolved launch profile."""

    relaunch_payload = launch_profile_relaunch_payload(resolved)
    payload: dict[str, object] = {
        "name": resolved.entry.name,
        "profile_lane": _profile_lane_label(resolved.entry.profile_lane),
        "source": launch_profile_source_payload(resolved),
        "defaults": launch_profile_defaults_payload(resolved),
        "path": str(resolved.entry.resolved_projection_path(overlay)),
        "metadata_path": str(resolved.entry.metadata_path)
        if resolved.entry.metadata_path is not None
        else None,
    }
    if relaunch_payload:
        payload["relaunch"] = relaunch_payload
    if resolved.entry.source_kind == "specialist":
        payload["specialist"] = resolved.entry.source_name
    if resolved.entry.source_kind == "recipe":
        payload["recipe"] = resolved.entry.source_name
    if resolved.tool is not None:
        payload["tool"] = resolved.tool
    return payload


def _list_launch_profile_payloads(
    *,
    overlay: HoumaoProjectOverlay,
    source_recipe: str | None = None,
    tool: str | None = None,
) -> list[dict[str, object]]:
    """Return explicit launch-profile payloads filtered by recipe or tool when requested."""

    results: list[dict[str, object]] = []
    for resolved in list_resolved_launch_profiles(overlay=overlay):
        if resolved.entry.profile_lane != "launch_profile":
            continue
        if source_recipe is not None and resolved.recipe_name != source_recipe:
            continue
        if tool is not None and resolved.tool != tool:
            continue
        results.append(_launch_profile_payload_from_resolved(overlay=overlay, resolved=resolved))
    return results


def _parse_launch_profile_env_records_or_click(
    *,
    adapter: ToolAdapter,
    env_set: tuple[str, ...],
    source_label: str,
) -> dict[str, str]:
    """Parse and validate persistent launch-profile env records."""

    try:
        parsed = parse_persistent_env_record_specs(env_set)
        return validate_persistent_env_records(
            parsed,
            auth_env_allowlist=adapter.auth_env_allowlist,
            source=source_label,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _resolve_prompt_overlay_text_or_click(
    *,
    prompt_overlay_mode: str | None,
    prompt_overlay_text: str | None,
    prompt_overlay_file: Path | None,
) -> tuple[str | None, str | None]:
    """Resolve one optional prompt overlay from inline or file input."""

    if prompt_overlay_text is not None and prompt_overlay_file is not None:
        raise click.ClickException(
            "Provide at most one of `--prompt-overlay-text` or `--prompt-overlay-file`."
        )
    resolved_text = (
        prompt_overlay_text.strip()
        if prompt_overlay_text is not None
        else (
            prompt_overlay_file.read_text(encoding="utf-8").rstrip()
            if prompt_overlay_file is not None
            else None
        )
    )
    if resolved_text is not None and not resolved_text:
        raise click.ClickException("Prompt-overlay text must not be empty.")
    if prompt_overlay_mode is None and resolved_text is not None:
        raise click.ClickException(
            "Prompt-overlay text requires `--prompt-overlay-mode append|replace`."
        )
    if prompt_overlay_mode is not None and resolved_text is None:
        raise click.ClickException(
            "Prompt-overlay mode requires `--prompt-overlay-text` or `--prompt-overlay-file`."
        )
    return prompt_overlay_mode, resolved_text


def _resolve_memo_seed_input_or_click(
    *,
    memo_seed_text: str | None,
    memo_seed_file: Path | None,
    memo_seed_dir: Path | None,
    clear_memo_seed: bool,
) -> tuple[str | None, str | None, Path | None]:
    """Resolve one optional launch-profile memo seed from CLI inputs."""

    requested_sources = sum(
        (
            memo_seed_text is not None,
            memo_seed_file is not None,
            memo_seed_dir is not None,
        )
    )
    if requested_sources > 1:
        raise click.ClickException(
            "Provide at most one of `--memo-seed-text`, `--memo-seed-file`, or `--memo-seed-dir`."
        )
    if clear_memo_seed and requested_sources > 0:
        raise click.ClickException(
            "`--clear-memo-seed` cannot be combined with a memo-seed source."
        )
    if memo_seed_text is not None:
        return "memo", memo_seed_text, None
    if memo_seed_file is not None:
        return "memo", None, memo_seed_file
    if memo_seed_dir is not None:
        return "tree", None, memo_seed_dir
    return None, None, None


def _managed_header_policy_from_override(value: bool | None) -> ManagedHeaderPolicy | None:
    """Return one stored managed-header policy from a tri-state CLI override."""

    if value is None:
        return None
    return "enabled" if value else "disabled"


def _managed_header_section_policy_from_options(
    values: tuple[str, ...],
) -> dict[ManagedHeaderSectionName, ManagedHeaderSectionPolicy]:
    """Return managed-header section policy parsed from repeatable CLI options."""

    try:
        return parse_managed_header_section_policy_assignments(
            values,
            source="`--managed-header-section`",
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _managed_header_section_names_from_options(
    values: tuple[str, ...],
) -> tuple[ManagedHeaderSectionName, ...]:
    """Return managed-header section names parsed from repeatable CLI options."""

    try:
        return parse_managed_header_section_names(
            values,
            source="`--clear-managed-header-section`",
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _resolve_managed_header_section_policy_for_storage(
    *,
    current: dict[ManagedHeaderSectionName, ManagedHeaderSectionPolicy] | None,
    section_policy: dict[ManagedHeaderSectionName, ManagedHeaderSectionPolicy],
    clear_sections: tuple[ManagedHeaderSectionName, ...],
    clear_all_sections: bool,
) -> dict[ManagedHeaderSectionName, ManagedHeaderSectionPolicy]:
    """Resolve stored managed-header section-policy mutation for profile storage."""

    if clear_all_sections and clear_sections:
        raise click.ClickException(
            "`--clear-managed-header-sections` cannot be combined with "
            "`--clear-managed-header-section`."
        )
    if clear_all_sections and section_policy:
        raise click.ClickException(
            "`--clear-managed-header-sections` cannot be combined with `--managed-header-section`."
        )
    conflicting_sections = sorted(set(section_policy).intersection(clear_sections))
    if conflicting_sections:
        section_list = ", ".join(f"`{section}`" for section in conflicting_sections)
        raise click.ClickException(
            "`--managed-header-section` cannot be combined with "
            f"`--clear-managed-header-section` for {section_list}."
        )

    resolved = dict(current or {})
    if clear_all_sections:
        resolved.clear()
    for section_name in clear_sections:
        resolved.pop(section_name, None)
    resolved.update(section_policy)
    return resolved


def _build_profile_mailbox_mapping_or_click(
    *,
    mail_transport: str | None,
    mail_principal_id: str | None,
    mail_address: str | None,
    mail_root: str | None,
    mail_base_url: str | None,
    mail_jmap_url: str | None,
    mail_management_url: str | None,
    source_label: str,
) -> dict[str, Any] | None:
    """Resolve one optional declarative mailbox mapping for launch-profile storage."""

    if mail_transport is None:
        provided = (
            mail_principal_id is not None
            or mail_address is not None
            or mail_root is not None
            or mail_base_url is not None
            or mail_jmap_url is not None
            or mail_management_url is not None
        )
        if provided:
            raise click.ClickException(
                "Mailbox fields require `--mail-transport filesystem|stalwart`."
            )
        return None

    payload: dict[str, Any] = {"transport": mail_transport}
    if mail_principal_id is not None:
        payload["principal_id"] = _require_non_empty_name(
            mail_principal_id, field_name="--mail-principal-id"
        )
    if mail_address is not None:
        payload["address"] = _require_non_empty_name(mail_address, field_name="--mail-address")
    if mail_transport == "filesystem":
        if (
            mail_base_url is not None
            or mail_jmap_url is not None
            or mail_management_url is not None
        ):
            raise click.ClickException(
                "Filesystem mailbox defaults do not accept Stalwart URL flags."
            )
        if mail_root is not None:
            payload["filesystem_root"] = mail_root.strip()
    else:
        if mail_root is not None:
            raise click.ClickException("Stalwart mailbox defaults do not accept `--mail-root`.")
        if mail_base_url is not None:
            payload["base_url"] = mail_base_url.strip()
        if mail_jmap_url is not None:
            payload["jmap_url"] = mail_jmap_url.strip()
        if mail_management_url is not None:
            payload["management_url"] = mail_management_url.strip()
    try:
        parsed = parse_declarative_mailbox_config(payload, source=source_label)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if parsed is None:
        return None
    return serialize_declarative_mailbox_config(parsed)


def _stored_mailbox_or_click(
    payload: dict[str, Any] | None,
    *,
    source: str,
) -> Any:
    """Parse one stored mailbox payload or raise one operator-facing error."""

    if payload is None:
        return None
    try:
        return parse_declarative_mailbox_config(payload, source=source)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _resolve_profile_posture_mapping(
    *,
    current: dict[str, Any] | None,
    headless: bool,
    clear_headless: bool,
    no_gateway: bool,
    gateway_port: int | None,
) -> dict[str, Any]:
    """Resolve one persisted launch-posture mapping."""

    if clear_headless and headless:
        raise click.ClickException("`--headless` cannot be combined with `--clear-headless`.")
    if no_gateway and gateway_port is not None:
        raise click.ClickException("`--no-gateway` and `--gateway-port` cannot be combined.")

    payload = dict(current or {})
    if clear_headless:
        payload.pop("headless", None)
    elif headless:
        payload["headless"] = True

    if no_gateway:
        payload["gateway_auto_attach"] = False
        payload.pop("gateway_host", None)
        payload.pop("gateway_port", None)
    elif gateway_port is not None:
        payload["gateway_auto_attach"] = True
        payload["gateway_host"] = "127.0.0.1"
        payload["gateway_port"] = gateway_port

    return payload


def _resolve_relaunch_chat_session_mapping_or_click(
    *,
    mode: str | None,
    session_id: str | None,
) -> dict[str, str] | None:
    """Resolve optional stored relaunch chat-session policy CLI inputs."""

    normalized_mode = mode.strip() if mode is not None else None
    normalized_session_id = session_id.strip() if session_id is not None else None
    if normalized_session_id == "":
        normalized_session_id = None
    if normalized_mode is None:
        if normalized_session_id is not None:
            raise click.ClickException(
                "`--relaunch-chat-session-id` requires `--relaunch-chat-session-mode exact`."
            )
        return None
    if normalized_mode not in _RELAUNCH_CHAT_SESSION_MODES:
        raise click.ClickException(
            "`--relaunch-chat-session-mode` must be one of "
            f"{', '.join(_RELAUNCH_CHAT_SESSION_MODES)}."
        )
    if normalized_mode != "exact" and normalized_session_id is not None:
        raise click.ClickException(
            "`--relaunch-chat-session-id` is only supported with "
            "`--relaunch-chat-session-mode exact`."
        )
    if normalized_mode == "exact" and normalized_session_id is None:
        raise click.ClickException(
            "`--relaunch-chat-session-mode exact` requires `--relaunch-chat-session-id`."
        )
    payload = {"mode": normalized_mode}
    if normalized_session_id is not None:
        payload["id"] = normalized_session_id
    return payload


def _store_launch_profile_from_cli(
    *,
    overlay: HoumaoProjectOverlay,
    profile_name: str,
    profile_lane: str,
    source_kind: str,
    source_name: str,
    operation: _LaunchProfileStoreOperation,
    agent_name: str | None,
    agent_id: str | None,
    workdir: str | None,
    auth: str | None,
    model: str | None,
    reasoning_level: int | None,
    prompt_mode: str | None,
    env_set: tuple[str, ...],
    mail_transport: str | None,
    mail_principal_id: str | None,
    mail_address: str | None,
    mail_root: str | None,
    mail_base_url: str | None,
    mail_jmap_url: str | None,
    mail_management_url: str | None,
    headless: bool,
    clear_headless: bool,
    no_gateway: bool,
    managed_header: bool | None,
    clear_managed_header: bool,
    managed_header_section: tuple[str, ...],
    clear_managed_header_section: tuple[str, ...],
    clear_managed_header_sections: bool,
    gateway_port: int | None,
    relaunch_chat_session_mode: str | None,
    relaunch_chat_session_id: str | None,
    clear_relaunch_chat_session: bool,
    prompt_overlay_mode: str | None,
    prompt_overlay_text: str | None,
    prompt_overlay_file: Path | None,
    clear_prompt_overlay: bool,
    memo_seed_text: str | None,
    memo_seed_file: Path | None,
    memo_seed_dir: Path | None,
    clear_memo_seed: bool,
    gateway_mail_notifier_appendix_text: str | None,
    clear_gateway_mail_notifier_appendix: bool,
    clear_mailbox: bool,
    clear_env: bool,
    clear_agent_name: bool,
    clear_agent_id: bool,
    clear_workdir: bool,
    clear_auth: bool,
    clear_model: bool,
    clear_reasoning_level: bool,
    clear_prompt_mode: bool,
) -> dict[str, object]:
    """Create or update one catalog-backed launch profile from CLI inputs."""

    catalog = ProjectCatalog.from_overlay(overlay)
    if operation == "create":
        try:
            catalog.load_launch_profile(profile_name)
        except FileNotFoundError:
            pass
        else:
            raise click.ClickException(
                f"Launch profile `{profile_name}` already exists in `{overlay.catalog_path}`."
            )
        current = None
    elif operation == "patch":
        current = _load_launch_profile_or_click(
            overlay=overlay,
            name=profile_name,
            expected_lane=profile_lane,
        )
    elif operation == "replace":
        _load_launch_profile_or_click(
            overlay=overlay,
            name=profile_name,
            expected_lane=profile_lane,
        )
        current = None
    else:
        raise click.ClickException(f"Unsupported launch-profile store operation: {operation}.")

    if source_kind == "specialist":
        source = _load_specialist_or_click(overlay=overlay, name=source_name)
        adapter = _load_overlay_tool_adapter(overlay=overlay, tool=source.tool)
    else:
        source = _load_recipe_or_click(overlay=overlay, name=source_name)
        adapter = _load_overlay_tool_adapter(overlay=overlay, tool=source.tool)

    mailbox_mapping = (
        None
        if clear_mailbox
        else _build_profile_mailbox_mapping_or_click(
            mail_transport=mail_transport,
            mail_principal_id=mail_principal_id,
            mail_address=mail_address,
            mail_root=mail_root,
            mail_base_url=mail_base_url,
            mail_jmap_url=mail_jmap_url,
            mail_management_url=mail_management_url,
            source_label=f"{profile_name}:mailbox",
        )
    )
    prompt_overlay = (
        (None, None)
        if clear_prompt_overlay
        else _resolve_prompt_overlay_text_or_click(
            prompt_overlay_mode=prompt_overlay_mode,
            prompt_overlay_text=prompt_overlay_text,
            prompt_overlay_file=prompt_overlay_file,
        )
    )
    if gateway_mail_notifier_appendix_text is not None and clear_gateway_mail_notifier_appendix:
        raise click.ClickException(
            "`--gateway-mail-notifier-appendix-text` cannot be combined with "
            "`--clear-gateway-mail-notifier-appendix`."
        )
    (
        requested_memo_seed_source_kind,
        requested_memo_seed_text,
        requested_memo_seed_source_path,
    ) = _resolve_memo_seed_input_or_click(
        memo_seed_text=memo_seed_text,
        memo_seed_file=memo_seed_file,
        memo_seed_dir=memo_seed_dir,
        clear_memo_seed=clear_memo_seed,
    )
    env_mapping = (
        {}
        if clear_env
        else (
            _parse_launch_profile_env_records_or_click(
                adapter=adapter,
                env_set=env_set,
                source_label=f"{profile_name}:env",
            )
            if env_set
            else None
        )
    )
    resolved_model_input = _resolve_model_name_or_click(model) if model is not None else None
    resolved_managed_header_policy: ManagedHeaderPolicy | None
    requested_section_policy = _managed_header_section_policy_from_options(managed_header_section)
    requested_clear_sections = _managed_header_section_names_from_options(
        clear_managed_header_section
    )

    if current is None:
        if clear_relaunch_chat_session:
            raise click.ClickException(
                "`--clear-relaunch-chat-session` requires an existing launch profile."
            )
        resolved_agent_name = _optional_non_empty_value(agent_name)
        resolved_agent_id = _optional_non_empty_value(agent_id)
        resolved_workdir = _optional_non_empty_value(workdir)
        resolved_auth = _optional_non_empty_value(auth)
        resolved_model_config = _build_model_config_or_click(
            model_name=resolved_model_input,
            reasoning_level=reasoning_level,
        )
        resolved_prompt_mode = _optional_non_empty_value(prompt_mode)
        resolved_mailbox = mailbox_mapping
        resolved_env = env_mapping if env_mapping is not None else {}
        resolved_posture = _resolve_profile_posture_mapping(
            current=None,
            headless=headless,
            clear_headless=clear_headless,
            no_gateway=no_gateway,
            gateway_port=gateway_port,
        )
        resolved_relaunch_chat_session = _resolve_relaunch_chat_session_mapping_or_click(
            mode=relaunch_chat_session_mode,
            session_id=relaunch_chat_session_id,
        )
        resolved_managed_header_policy = (
            _managed_header_policy_from_override(managed_header) or "inherit"
        )
        resolved_managed_header_section_policy = _resolve_managed_header_section_policy_for_storage(
            current=None,
            section_policy=requested_section_policy,
            clear_sections=requested_clear_sections,
            clear_all_sections=clear_managed_header_sections,
        )
        resolved_prompt_overlay_mode, resolved_prompt_overlay_text = prompt_overlay
        if clear_gateway_mail_notifier_appendix:
            raise click.ClickException(
                "`--clear-gateway-mail-notifier-appendix` requires an existing launch profile."
            )
        resolved_gateway_mail_notifier_appendix_text = gateway_mail_notifier_appendix_text
        if clear_memo_seed:
            raise click.ClickException("`--clear-memo-seed` requires an existing memo seed.")
        if requested_memo_seed_source_kind is None:
            resolved_memo_seed_source_kind = None
            resolved_memo_seed_text = None
            resolved_memo_seed_source_path = None
        else:
            resolved_memo_seed_source_kind = requested_memo_seed_source_kind
            resolved_memo_seed_text = requested_memo_seed_text
            resolved_memo_seed_source_path = requested_memo_seed_source_path
    else:
        resolved_agent_name = (
            None
            if clear_agent_name
            else (
                _optional_non_empty_value(agent_name)
                if agent_name is not None
                else current.entry.managed_agent_name
            )
        )
        resolved_agent_id = (
            None
            if clear_agent_id
            else (
                _optional_non_empty_value(agent_id)
                if agent_id is not None
                else current.entry.managed_agent_id
            )
        )
        resolved_workdir = (
            None
            if clear_workdir
            else (
                _optional_non_empty_value(workdir) if workdir is not None else current.entry.workdir
            )
        )
        if clear_auth and auth is not None:
            raise click.ClickException("`--auth` cannot be combined with `--clear-auth`.")
        resolved_auth = (
            None
            if clear_auth
            else (_optional_non_empty_value(auth) if auth is not None else current.entry.auth_name)
        )
        if clear_model and model is not None:
            raise click.ClickException("`--model` cannot be combined with `--clear-model`.")
        if clear_reasoning_level and reasoning_level is not None:
            raise click.ClickException(
                "`--reasoning-level` cannot be combined with `--clear-reasoning-level`."
            )
        resolved_model_config = _merge_model_config_for_storage(
            current_name=current.entry.model_name,
            current_reasoning_level=current.entry.reasoning_level,
            model_name=resolved_model_input,
            reasoning_level=reasoning_level,
            clear_model=clear_model,
            clear_reasoning_level=clear_reasoning_level,
        )
        if clear_prompt_mode and prompt_mode is not None:
            raise click.ClickException(
                "`--prompt-mode` cannot be combined with `--clear-prompt-mode`."
            )
        resolved_prompt_mode = (
            None
            if clear_prompt_mode
            else (
                _optional_non_empty_value(prompt_mode)
                if prompt_mode is not None
                else current.entry.operator_prompt_mode
            )
        )
        resolved_mailbox = (
            mailbox_mapping if mail_transport is not None else current.entry.mailbox_payload
        )
        if clear_mailbox:
            resolved_mailbox = None
        resolved_env = (
            {}
            if clear_env
            else (env_mapping if env_mapping is not None else dict(current.entry.env_payload))
        )
        resolved_posture = _resolve_profile_posture_mapping(
            current=current.entry.posture_payload,
            headless=headless,
            clear_headless=clear_headless,
            no_gateway=no_gateway,
            gateway_port=gateway_port,
        )
        if clear_relaunch_chat_session and (
            relaunch_chat_session_mode is not None or relaunch_chat_session_id is not None
        ):
            raise click.ClickException(
                "`--clear-relaunch-chat-session` cannot be combined with "
                "`--relaunch-chat-session-mode` or `--relaunch-chat-session-id`."
            )
        if clear_relaunch_chat_session:
            resolved_relaunch_chat_session = None
        else:
            requested_relaunch_chat_session = _resolve_relaunch_chat_session_mapping_or_click(
                mode=relaunch_chat_session_mode,
                session_id=relaunch_chat_session_id,
            )
            resolved_relaunch_chat_session = (
                requested_relaunch_chat_session
                if requested_relaunch_chat_session is not None
                else current.entry.relaunch_chat_session_payload
            )
        if clear_managed_header and managed_header is not None:
            raise click.ClickException(
                "`--managed-header` or `--no-managed-header` cannot be combined with "
                "`--clear-managed-header`."
            )
        if clear_managed_header:
            resolved_managed_header_policy = "inherit"
        elif managed_header is not None:
            resolved_managed_header_policy = _managed_header_policy_from_override(managed_header)
        else:
            resolved_managed_header_policy = current.entry.managed_header_policy
        resolved_managed_header_section_policy = _resolve_managed_header_section_policy_for_storage(
            current=getattr(current.entry, "managed_header_section_policy", {}),
            section_policy=requested_section_policy,
            clear_sections=requested_clear_sections,
            clear_all_sections=clear_managed_header_sections,
        )
        if clear_prompt_overlay:
            resolved_prompt_overlay_mode = None
            resolved_prompt_overlay_text = None
        elif prompt_overlay[0] is not None:
            resolved_prompt_overlay_mode, resolved_prompt_overlay_text = prompt_overlay
        else:
            resolved_prompt_overlay_mode = current.entry.prompt_overlay_mode
            resolved_prompt_overlay_text = current.prompt_overlay_text
        if clear_gateway_mail_notifier_appendix:
            resolved_gateway_mail_notifier_appendix_text = None
        elif gateway_mail_notifier_appendix_text is not None:
            resolved_gateway_mail_notifier_appendix_text = gateway_mail_notifier_appendix_text
        else:
            resolved_gateway_mail_notifier_appendix_text = (
                current.gateway_mail_notifier_appendix_text
            )
        if clear_memo_seed:
            if current.memo_seed is None:
                raise click.ClickException(
                    f"Launch profile `{profile_name}` does not store a memo seed."
                )
            resolved_memo_seed_source_kind = None
            resolved_memo_seed_text = None
            resolved_memo_seed_source_path = None
        elif requested_memo_seed_source_kind is not None:
            resolved_memo_seed_source_kind = requested_memo_seed_source_kind
            resolved_memo_seed_text = requested_memo_seed_text
            resolved_memo_seed_source_path = requested_memo_seed_source_path
        elif current.memo_seed is not None:
            resolved_memo_seed_source_kind = current.memo_seed.source_kind
            resolved_memo_seed_text = None
            resolved_memo_seed_source_path = current.memo_seed.source_path
        else:
            resolved_memo_seed_source_kind = None
            resolved_memo_seed_text = None
            resolved_memo_seed_source_path = None

    mutation_requested = any(
        (
            current is None,
            agent_name is not None,
            clear_agent_name,
            agent_id is not None,
            clear_agent_id,
            workdir is not None,
            clear_workdir,
            auth is not None,
            clear_auth,
            model is not None,
            clear_model,
            reasoning_level is not None,
            clear_reasoning_level,
            prompt_mode is not None,
            clear_prompt_mode,
            bool(env_set),
            clear_env,
            mail_transport is not None,
            clear_mailbox,
            headless,
            clear_headless,
            no_gateway,
            managed_header is not None,
            clear_managed_header,
            bool(managed_header_section),
            bool(clear_managed_header_section),
            clear_managed_header_sections,
            gateway_port is not None,
            relaunch_chat_session_mode is not None,
            relaunch_chat_session_id is not None,
            clear_relaunch_chat_session,
            prompt_overlay_mode is not None,
            prompt_overlay_text is not None,
            prompt_overlay_file is not None,
            clear_prompt_overlay,
            memo_seed_text is not None,
            memo_seed_file is not None,
            memo_seed_dir is not None,
            clear_memo_seed,
            gateway_mail_notifier_appendix_text is not None,
            clear_gateway_mail_notifier_appendix,
        )
    )
    if not mutation_requested:
        raise click.ClickException("No launch-profile updates were requested.")

    catalog.store_launch_profile(
        name=profile_name,
        profile_lane=profile_lane,
        source_kind=source_kind,
        source_name=source_name,
        managed_agent_name=resolved_agent_name,
        managed_agent_id=resolved_agent_id,
        workdir=resolved_workdir,
        auth_tool=source.tool,
        auth_name=resolved_auth,
        model_name=resolved_model_config.name if resolved_model_config is not None else None,
        reasoning_level=(
            resolved_model_config.reasoning.level
            if resolved_model_config is not None and resolved_model_config.reasoning is not None
            else None
        ),
        operator_prompt_mode=resolved_prompt_mode,
        env_mapping=resolved_env,
        mailbox_mapping=resolved_mailbox,
        posture_mapping=resolved_posture,
        relaunch_chat_session_mapping=resolved_relaunch_chat_session,
        managed_header_policy=resolved_managed_header_policy,
        managed_header_section_policy=resolved_managed_header_section_policy,
        prompt_overlay_mode=resolved_prompt_overlay_mode,
        prompt_overlay_text=resolved_prompt_overlay_text,
        gateway_mail_notifier_appendix_text=resolved_gateway_mail_notifier_appendix_text,
        memo_seed_source_kind=resolved_memo_seed_source_kind,
        memo_seed_text=resolved_memo_seed_text,
        memo_seed_source_path=resolved_memo_seed_source_path,
    )
    materialize_project_agent_catalog_projection(overlay)
    return _launch_profile_payload(
        overlay=overlay,
        profile_name=profile_name,
        expected_lane=profile_lane,
    )


def _launch_profile_provenance_payload(resolved: Any) -> dict[str, Any]:
    """Return secret-free launch-profile provenance for build and runtime metadata."""

    payload = {
        "name": resolved.entry.name,
        "lane": resolved.entry.profile_lane,
        "source_kind": resolved.entry.source_kind,
        "source_name": resolved.entry.source_name,
        "recipe_name": resolved.recipe_name,
        "prompt_overlay": {
            "mode": resolved.entry.prompt_overlay_mode,
            "present": resolved.prompt_overlay_text is not None,
        },
        "gateway_mail_notifier_appendix": {
            "present": resolved.gateway_mail_notifier_appendix_text is not None,
        },
        "memo_seed": (
            {
                "present": True,
                "source_kind": resolved.memo_seed.source_kind,
                "content_ref": {
                    "content_kind": resolved.memo_seed.content_ref.content_kind,
                    "storage_kind": resolved.memo_seed.content_ref.storage_kind,
                    "relative_path": resolved.memo_seed.content_ref.relative_path,
                },
            }
            if resolved.memo_seed is not None
            else {"present": False}
        ),
    }
    relaunch_payload = launch_profile_relaunch_payload(resolved)
    if relaunch_payload:
        payload["relaunch"] = relaunch_payload
    return payload


def _specialist_payload(
    *,
    overlay: HoumaoProjectOverlay,
    metadata: SpecialistMetadata,
) -> dict[str, object]:
    """Return one structured specialist payload with generated canonical paths."""

    return {
        "name": metadata.name,
        "preset_name": metadata.preset_name,
        "tool": metadata.tool,
        "provider": metadata.provider,
        "credential": metadata.credential_name,
        "setup": metadata.setup_name,
        "role_name": metadata.role_name,
        "skills": list(metadata.skills),
        "skill_bindings": [
            _project_skill_payload(overlay=overlay, metadata=entry)
            for entry in metadata.skill_entries
        ],
        "launch": dict(metadata.launch_payload),
        "metadata_path": str(metadata.metadata_path)
        if metadata.metadata_path is not None
        else None,
        "generated": {
            "role_prompt": str(metadata.resolved_system_prompt_path(overlay)),
            "preset": str(metadata.resolved_preset_path(overlay)),
            "auth": str(metadata.resolved_auth_path(overlay)),
            "skills": [str(path) for path in metadata.resolved_skill_paths(overlay)],
        },
    }


def _project_skill_payload(
    *,
    overlay: HoumaoProjectOverlay,
    metadata: ProjectSkillCatalogEntry,
) -> dict[str, object]:
    """Return one structured project skill payload."""

    return {
        "name": metadata.name,
        "mode": metadata.mode,
        "canonical_path": str(metadata.resolved_canonical_path(overlay)),
        "projection_path": str(metadata.resolved_projection_path(overlay)),
        "source_path": str(metadata.source_path) if metadata.source_path is not None else None,
        "metadata_path": str(metadata.metadata_path)
        if metadata.metadata_path is not None
        else None,
    }


def _load_specialist_or_click(*, overlay: HoumaoProjectOverlay, name: str) -> SpecialistMetadata:
    """Load one specialist definition or raise one operator-facing error."""

    specialist_name = _require_non_empty_name(name, field_name="--name")
    try:
        return load_specialist(overlay=overlay, name=specialist_name)
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


def _remove_specialist_metadata_or_click(*, overlay: HoumaoProjectOverlay, name: str) -> Path:
    """Delete one specialist metadata document or raise one operator-facing error."""

    try:
        return remove_specialist_metadata(overlay=overlay, name=name)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc


def _list_project_instances(
    *,
    overlay: HoumaoProjectOverlay,
    specialists_by_name: dict[str, SpecialistMetadata],
) -> list[dict[str, object]]:
    """Return project-local managed agents as specialist-annotated instances."""

    instances: list[dict[str, object]] = []
    for identity in list_managed_agents(port=None).agents:
        identity_payload = identity.model_dump(mode="json")
        manifest_path_value = identity_payload.get("manifest_path")
        if not isinstance(manifest_path_value, str) or not manifest_path_value.strip():
            continue
        manifest_path = Path(manifest_path_value).resolve()
        if not manifest_path.is_file():
            continue
        try:
            manifest_payload = _load_manifest_payload(manifest_path)
        except Exception:
            continue
        if not _manifest_belongs_to_overlay(overlay=overlay, manifest_payload=manifest_payload):
            continue
        instances.append(
            _instance_payload(
                overlay=overlay,
                identity_payload=identity_payload,
                manifest_payload=manifest_payload,
                specialists_by_name=specialists_by_name,
            )
        )
    return instances


def _instance_payload(
    *,
    overlay: HoumaoProjectOverlay,
    identity_payload: dict[str, object],
    manifest_payload: dict[str, object],
    specialists_by_name: dict[str, SpecialistMetadata],
) -> dict[str, object]:
    """Build one project-local instance payload from managed runtime state."""

    role_name = str(manifest_payload.get("role_name", "")).strip() or None
    tool_name = str(manifest_payload.get("tool", "")).strip() or None
    specialist = specialists_by_name.get(role_name) if role_name is not None else None
    mailbox_payload = _instance_mailbox_payload(manifest_payload)
    easy_profile_name = _instance_easy_profile_name(manifest_payload)
    runtime_payload = manifest_payload.get("runtime")
    return {
        "instance_name": identity_payload.get("agent_name"),
        "agent_id": identity_payload.get("agent_id"),
        "transport": identity_payload.get("transport"),
        "tool": tool_name or identity_payload.get("tool"),
        "role_name": role_name,
        "manifest_path": identity_payload.get("manifest_path"),
        "session_root": identity_payload.get("session_root"),
        "tmux_session_name": identity_payload.get("tmux_session_name"),
        "specialist": specialist.name if specialist is not None else None,
        "easy_profile": easy_profile_name,
        "project_root": str(overlay.project_root),
        "project_agent_def_dir": runtime_payload.get("agent_def_dir")
        if isinstance(runtime_payload, dict)
        else None,
        "memory_root": runtime_payload.get("memory_root")
        if isinstance(runtime_payload, dict)
        else None,
        "memo_file": runtime_payload.get("memo_file")
        if isinstance(runtime_payload, dict)
        else None,
        "pages_dir": runtime_payload.get("pages_dir")
        if isinstance(runtime_payload, dict)
        else None,
        "mailbox": mailbox_payload,
    }


def _instance_easy_profile_name(manifest_payload: dict[str, object]) -> str | None:
    """Return the originating easy-profile name from one runtime manifest when available."""

    launch_profile = _instance_launch_profile_provenance(manifest_payload)
    if not isinstance(launch_profile, dict):
        return None
    lane = launch_profile.get("lane")
    name = launch_profile.get("name")
    if lane != "easy_profile" or not isinstance(name, str) or not name.strip():
        return None
    return name


def _instance_launch_profile_provenance(
    manifest_payload: dict[str, object],
) -> dict[str, Any] | None:
    """Return secret-free launch-profile provenance from one runtime manifest."""

    launch_plan_payload = manifest_payload.get("launch_plan")
    if not isinstance(launch_plan_payload, dict):
        return None
    metadata_payload = launch_plan_payload.get("metadata")
    if not isinstance(metadata_payload, dict):
        return None
    launch_overrides_payload = metadata_payload.get("launch_overrides")
    if not isinstance(launch_overrides_payload, dict):
        return None
    construction_provenance_payload = launch_overrides_payload.get("construction_provenance")
    if not isinstance(construction_provenance_payload, dict):
        return None
    launch_profile_payload = construction_provenance_payload.get("launch_profile")
    if not isinstance(launch_profile_payload, dict):
        return None
    return dict(launch_profile_payload)


def _instance_mailbox_payload(manifest_payload: dict[str, object]) -> dict[str, object] | None:
    """Return one runtime-derived mailbox summary for an instance payload."""

    launch_plan_payload = manifest_payload.get("launch_plan")
    if not isinstance(launch_plan_payload, dict):
        return None
    mailbox_payload = launch_plan_payload.get("mailbox")
    if not isinstance(mailbox_payload, dict):
        return None

    transport = mailbox_payload.get("transport")
    if not isinstance(transport, str) or not transport.strip():
        return None

    if transport == "filesystem":
        address = mailbox_payload.get("address")
        filesystem_root = mailbox_payload.get("filesystem_root")
        if not isinstance(address, str) or not address.strip():
            return None
        if not isinstance(filesystem_root, str) or not filesystem_root.strip():
            return None
        mailbox_root = Path(filesystem_root).resolve()
        mailbox_kind = mailbox_payload.get("mailbox_kind")
        if not isinstance(mailbox_kind, str) or not mailbox_kind.strip():
            mailbox_kind = "in_root"
        mailbox_path_value = mailbox_payload.get("mailbox_path")
        mailbox_dir = (
            Path(mailbox_path_value).resolve()
            if isinstance(mailbox_path_value, str) and mailbox_path_value.strip()
            else mailbox_root / "mailboxes" / address
        )
        return {
            "transport": transport,
            "principal_id": mailbox_payload.get("principal_id"),
            "address": address,
            "mailbox_root": str(mailbox_root),
            "mailbox_kind": mailbox_kind,
            "mailbox_dir": str(mailbox_dir),
            "bindings_version": mailbox_payload.get("bindings_version"),
        }

    return {
        "transport": transport,
        "principal_id": mailbox_payload.get("principal_id"),
        "address": mailbox_payload.get("address"),
        "bindings_version": mailbox_payload.get("bindings_version"),
    }


def _require_manifest_path_for_identity(*, identity_payload: dict[str, object]) -> Path:
    """Return one resolved manifest path from an identity payload."""

    manifest_path_value = identity_payload.get("manifest_path")
    if not isinstance(manifest_path_value, str) or not manifest_path_value.strip():
        raise click.ClickException("Managed agent does not expose a manifest path.")
    manifest_path = Path(manifest_path_value).resolve()
    if not manifest_path.is_file():
        raise click.ClickException(f"Managed agent manifest path is missing: {manifest_path}")
    return manifest_path


def _load_manifest_payload(manifest_path: Path) -> dict[str, object]:
    """Load one manifest payload as a JSON-compatible mapping."""

    payload = load_session_manifest(manifest_path).payload
    if not isinstance(payload, dict):
        raise ValueError(f"{manifest_path}: expected manifest payload to be a mapping.")
    return payload


def _manifest_belongs_to_overlay(
    *,
    overlay: HoumaoProjectOverlay,
    manifest_payload: dict[str, object],
) -> bool:
    """Return whether one manifest payload belongs to the selected project overlay."""

    runtime_payload = manifest_payload.get("runtime")
    if not isinstance(runtime_payload, dict):
        return False
    raw_agent_def_dir = runtime_payload.get("agent_def_dir")
    if not isinstance(raw_agent_def_dir, str) or not raw_agent_def_dir.strip():
        return False
    return Path(raw_agent_def_dir).resolve() == overlay.agents_root


def _load_overlay_tool_adapter(*, overlay: HoumaoProjectOverlay, tool: str) -> ToolAdapter:
    """Load one tool adapter from the project-local agent-definition tree."""

    adapter_path = (_tool_root(overlay=overlay, tool=tool) / "adapter.yaml").resolve()
    if not adapter_path.is_file():
        raise click.ClickException(
            f"Tool `{tool}` is not initialized under the selected project overlay: {adapter_path}"
        )
    try:
        return parse_tool_adapter(adapter_path)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _auth_bundle_root(*, overlay: HoumaoProjectOverlay, tool: str, name: str) -> Path:
    """Return the root directory for one tool-local auth bundle."""

    profile = _load_auth_profile_optional(overlay=overlay, tool=tool, name=name)
    if profile is not None:
        return profile.resolved_projection_path(overlay)
    return (_tool_root(overlay=overlay, tool=tool) / "auth" / name).resolve()


def _auth_bundle_env_file(*, overlay: HoumaoProjectOverlay, tool: str, name: str) -> Path:
    """Return the env-file path for one tool-local auth bundle."""

    return (_auth_bundle_root(overlay=overlay, tool=tool, name=name) / "env" / "vars.env").resolve()


def _overlay_relative_path(*, overlay: HoumaoProjectOverlay, path: Path) -> str:
    """Return one path relative to the overlay root using POSIX separators."""

    return path.resolve().relative_to(overlay.overlay_root).as_posix()


def _relative_file_listing(root: Path) -> list[str]:
    """Return stable relative file paths rooted at one directory."""

    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())


def _default_role_prompt(role_name: str) -> str:
    """Return the default project-local role prompt content."""

    return f"# {role_name}\n\nDescribe the specialist system prompt here.\n"


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    """Load one YAML mapping payload from disk."""

    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise click.ClickException(f"Failed to read `{path}`: {exc}") from exc
    except yaml.YAMLError as exc:
        raise click.ClickException(f"Malformed YAML `{path}`: {exc}") from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise click.ClickException(f"{path}: expected a top-level YAML mapping.")
    return loaded


def _parse_preset_or_click(path: Path) -> Any:
    """Parse one preset definition or raise one operator-facing error."""

    try:
        return parse_agent_preset(path)
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


def _write_yaml_mapping(path: Path, payload: dict[str, object]) -> None:
    """Write one YAML mapping payload to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _resolve_model_name_or_click(
    value: str | None,
    *,
    field_name: str = "--model",
) -> str | None:
    """Return one optional non-empty model name."""

    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise click.ClickException(f"{field_name} must not be empty.")
    return stripped


def _build_model_config_or_click(
    *,
    model_name: str | None,
    reasoning_level: int | None,
) -> ModelConfig | None:
    """Build one normalized model config from CLI inputs."""

    try:
        return normalize_model_config(name=model_name, reasoning_level=reasoning_level)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _resolve_operator_prompt_mode_or_click(
    value: str | None,
    *,
    source: str,
) -> OperatorPromptMode | None:
    """Return one validated operator prompt mode from stored project state."""

    if value is None:
        return None
    if value not in {"as_is", "unattended"}:
        raise click.ClickException(
            f"{source} stores invalid launch.prompt_mode {value!r}; expected `as_is` or "
            "`unattended`."
        )
    return cast(OperatorPromptMode, value)


def _model_mapping_payload(model_config: ModelConfig | None) -> dict[str, object] | None:
    """Return one YAML/JSON-ready payload for optional model config."""

    payload = model_config_to_payload(model_config)
    if payload is None:
        return None
    return payload


def _merge_model_config_for_storage(
    *,
    current_name: str | None,
    current_reasoning_level: int | None,
    model_name: str | None,
    reasoning_level: int | None,
    clear_model: bool,
    clear_reasoning_level: bool,
) -> ModelConfig | None:
    """Resolve one stored model-config mutation on a per-subfield basis."""

    resolved_name = (
        None if clear_model else (model_name if model_name is not None else current_name)
    )
    resolved_reasoning_level = (
        None
        if clear_reasoning_level
        else (reasoning_level if reasoning_level is not None else current_reasoning_level)
    )
    return _build_model_config_or_click(
        model_name=resolved_name,
        reasoning_level=resolved_reasoning_level,
    )


def _resolve_required_prompt_text(
    *,
    system_prompt: str | None,
    system_prompt_file: Path | None,
) -> str:
    """Resolve one required prompt payload from inline or file input."""

    if system_prompt is not None and system_prompt_file is not None:
        raise click.ClickException(
            "Provide at most one of `--system-prompt` or `--system-prompt-file`."
        )
    if system_prompt is not None:
        value = system_prompt.strip()
        if not value:
            raise click.ClickException("`--system-prompt` must not be empty.")
        return value
    if system_prompt_file is not None:
        return system_prompt_file.read_text(encoding="utf-8").rstrip()
    raise click.ClickException("Provide one of `--system-prompt` or `--system-prompt-file`.")


def _optional_non_empty_value(value: str | None) -> str | None:
    """Return one optional non-empty CLI value."""

    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _require_non_empty_name(value: str, *, field_name: str) -> str:
    """Validate one tool, role, setup, skill, or auth-bundle name."""

    candidate = value.strip()
    if not candidate:
        raise click.ClickException(f"{field_name} must not be empty.")
    if "/" in candidate or "\\" in candidate:
        raise click.ClickException(f"{field_name} must not contain path separators.")
    return candidate


__all__ = [
    "os",
    "shutil",
    "Path",
    "Any",
    "Literal",
    "cast",
    "click",
    "yaml",
    "ToolAdapter",
    "parse_agent_preset",
    "parse_tool_adapter",
    "parse_persistent_env_record_specs",
    "resolve_runtime_env_set_specs",
    "validate_persistent_env_records",
    "OperatorPromptMode",
    "ManagedHeaderPolicy",
    "ManagedHeaderSectionName",
    "ManagedHeaderSectionPolicy",
    "parse_managed_header_section_names",
    "parse_managed_header_section_policy_assignments",
    "parse_declarative_mailbox_config",
    "serialize_declarative_mailbox_config",
    "ModelConfig",
    "model_config_to_payload",
    "normalize_model_config",
    "GatewayCurrentExecutionMode",
    "GatewayTuiTrackingTimingOverridesV1",
    "load_session_manifest",
    "AuthProfileCatalogEntry",
    "ProjectCatalog",
    "SpecialistMetadata",
    "TOOL_PROVIDER_MAP",
    "list_specialists",
    "load_specialist",
    "remove_profile_metadata",
    "remove_specialist_metadata",
    "launch_profile_defaults_payload",
    "launch_profile_source_payload",
    "list_resolved_launch_profiles",
    "resolve_launch_profile",
    "HoumaoProjectOverlay",
    "ProjectAwareLocalRoots",
    "bootstrap_project_overlay_at_root",
    "ensure_project_aware_local_roots",
    "ensure_project_agent_compatibility_tree",
    "materialize_project_agent_catalog_projection",
    "resolve_project_init_overlay_root",
    "resolve_project_aware_local_roots",
    "ensure_specialist_credential_bundle",
    "emit_local_launch_completion",
    "launch_managed_agent_locally",
    "emit_cleanup_payload",
    "build_destructive_confirmation_callback",
    "confirm_destructive_action",
    "managed_launch_force_option",
    "overwrite_confirm_option",
    "emit",
    "clear_mailbox_messages_at_root",
    "cleanup_mailbox_root",
    "export_mailbox_root",
    "get_mailbox_account",
    "get_mailbox_message",
    "init_mailbox_root",
    "list_mailbox_accounts",
    "list_mailbox_messages",
    "mailbox_root_status_payload",
    "register_mailbox_at_root",
    "repair_mailbox_root",
    "unregister_mailbox_at_root",
    "list_managed_agents",
    "resolve_managed_agent_target",
    "stop_managed_agent",
    "describe_overlay_bootstrap",
    "describe_overlay_discovery_mode",
    "describe_overlay_root_selection_source",
    "_SUPPORTED_PROJECT_TOOLS",
    "_LaunchProfileStoreOperation",
    "_RELAUNCH_CHAT_SESSION_MODES",
    "_ensure_project_roots",
    "_ensure_project_overlay",
    "_resolve_existing_project_roots",
    "_resolve_existing_project_overlay",
    "_selected_overlay_detail",
    "_status_overlay_bootstrap_detail",
    "_missing_selected_overlay_message",
    "_list_tool_setup_names",
    "_list_tool_bundle_names",
    "_load_auth_profile_or_click",
    "_load_auth_profile_optional",
    "_auth_source_root",
    "_tool_root",
    "_tool_setup_path",
    "_role_root",
    "_presets_root",
    "_preset_path",
    "_list_role_names",
    "_role_summary",
    "_list_named_preset_summaries",
    "_preset_summary",
    "_parse_preset_or_click",
    "_write_role_prompt",
    "_canonical_preset_name",
    "_ensure_role_exists",
    "_ensure_unique_preset_tuple",
    "_write_named_preset",
    "_prepare_specialist_projection_for_replace",
    "_ensure_skill_placeholder",
    "_clone_tool_setup_if_missing",
    "_ensure_placeholder_auth_bundle",
    "_validate_specialist_create_inputs",
    "_resolve_system_prompt_text",
    "_import_skill_directories",
    "_parse_specialist_env_records_or_click",
    "_resolve_instance_env_set_or_click",
    "_load_recipe_or_click",
    "_profile_lane_label",
    "_load_launch_profile_or_click",
    "_resolve_launch_profile_create_operation_or_click",
    "_launch_profile_payload",
    "_launch_profile_payload_from_resolved",
    "_list_launch_profile_payloads",
    "_parse_launch_profile_env_records_or_click",
    "_resolve_prompt_overlay_text_or_click",
    "_managed_header_policy_from_override",
    "_managed_header_section_policy_from_options",
    "_managed_header_section_names_from_options",
    "_resolve_managed_header_section_policy_for_storage",
    "_build_profile_mailbox_mapping_or_click",
    "_stored_mailbox_or_click",
    "_resolve_profile_posture_mapping",
    "_store_launch_profile_from_cli",
    "_launch_profile_provenance_payload",
    "_specialist_payload",
    "_project_skill_payload",
    "_load_specialist_or_click",
    "_remove_specialist_metadata_or_click",
    "_list_project_instances",
    "_instance_payload",
    "_instance_easy_profile_name",
    "_instance_launch_profile_provenance",
    "_instance_mailbox_payload",
    "_require_manifest_path_for_identity",
    "_load_manifest_payload",
    "_manifest_belongs_to_overlay",
    "_load_overlay_tool_adapter",
    "_auth_bundle_root",
    "_auth_bundle_env_file",
    "_overlay_relative_path",
    "_relative_file_listing",
    "_default_role_prompt",
    "_load_yaml_mapping",
    "_write_yaml_mapping",
    "_resolve_model_name_or_click",
    "_build_model_config_or_click",
    "_resolve_operator_prompt_mode_or_click",
    "_model_mapping_payload",
    "_merge_model_config_for_storage",
    "_resolve_required_prompt_text",
    "_optional_non_empty_value",
    "_require_non_empty_name",
]
