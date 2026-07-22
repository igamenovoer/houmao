"""CLI lifecycle for Houmao's static system-skill collection."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import click

from houmao.agents.system_skills import (
    SystemSkillDoctorResult,
    SystemSkillDoctorTarget,
    SystemSkillInstallResult,
    SystemSkillStatusResult,
    SystemSkillUninstallResult,
    SystemSkillUpgradeResult,
    inspect_system_skill_packs,
    inspect_system_skill_doctor,
    install_system_skill_packs_for_home,
    load_system_skill_manifest,
    resolve_system_skill_pack_selection,
    uninstall_system_skill_packs_for_home,
    upgrade_system_skill_packs_for_home,
)
from houmao.srv_ctrl.system_skill_doctor_target import (
    SystemSkillDoctorTargetError,
    resolve_managed_system_skill_doctor_target,
)

from .output import emit


_SYSTEM_SKILLS_HOME_ENV_VAR_BY_TOOL: dict[str, str] = {
    "claude": "CLAUDE_CONFIG_DIR",
    "codex": "CODEX_HOME",
    "copilot": "COPILOT_HOME",
    "kimi": "KIMI_CODE_HOME",
}
_SYSTEM_SKILLS_PROJECT_DEFAULT_HOME_BY_TOOL: dict[str, Path] = {
    "claude": Path(".claude"),
    "codex": Path(".codex"),
    "copilot": Path(".github"),
    "kimi": Path(".kimi-code"),
}
_SYSTEM_SKILLS_UNIVERSAL_TARGET = "universal"
_SUPPORTED_SYSTEM_SKILLS_TARGETS: tuple[str, ...] = (
    "claude",
    "codex",
    "copilot",
    "kimi",
    _SYSTEM_SKILLS_UNIVERSAL_TARGET,
)
_SYSTEM_SKILLS_TARGET_HELP = (
    "Supported target (`claude`, `codex`, `copilot`, `kimi`, or `universal`). "
    "`kimi` means Kimi Code CLI. `universal` installs under `.agents/skills`."
)
_SYSTEM_SKILLS_HOME_HELP = (
    "Optional target home override. Otherwise use the target env redirect or project home; "
    "universal defaults to `~/.agents`."
)


@click.group(name="system-skills")
def system_skills_group() -> None:
    """Install, diagnose, inspect, upgrade, and remove complete actor packs."""


@system_skills_group.command(name="list")
def list_system_skills_command() -> None:
    """List static roots, shared children, pack membership, and activation."""

    manifest = load_system_skill_manifest()
    packs = [
        {
            "pack_id": pack.pack_id,
            "audience": pack.audience,
            "description": pack.description,
            "default_lanes": list(pack.default_lanes),
            "standalone_skills": list(pack.standalone_skill_names),
        }
        for pack in manifest.packs.values()
    ]
    standalone_skills = [
        {
            "name": record.name,
            "role": record.role,
            "activation": record.activation,
            "pack_ids": list(record.pack_ids),
            "commands": list(record.commands),
            "aliases": list(record.aliases),
            "dependencies": list(record.dependencies),
        }
        for record in manifest.standalone_skills.values()
    ]
    shared_routines = [
        {
            "logical_id": routine.logical_id,
            "route_name": routine.route_name,
            "audiences": list(routine.audiences),
            "dependencies": [dependency.logical_id for dependency in routine.dependencies],
            "commands": list(routine.commands),
            "aliases": list(routine.aliases),
            "invocation": f"houmao-shared-routines->{routine.logical_id}",
        }
        for routine in manifest.shared_routines.values()
    ]
    payload = {
        "schema_version": manifest.schema_version,
        "packs": packs,
        "standalone_skills": standalone_skills,
        "shared_routines": shared_routines,
        "overlapping_standalone_skills": [
            record.name
            for record in manifest.standalone_skills.values()
            if len(record.pack_ids) > 1
        ],
        "defaults": {
            "cli": list(manifest.defaults.cli),
            "managed_launch": list(manifest.defaults.managed_launch),
            "managed_join": list(manifest.defaults.managed_join),
        },
        "auto_skill_separate": manifest.auto_skill_name,
    }
    emit(payload, plain_renderer=_render_list_plain)


def _pack_selection_options(command: Any) -> Any:
    """Add current and diagnostic selector options to one lifecycle command."""

    command = click.option(
        "--pack",
        "pack_ids",
        multiple=True,
        help="Repeatable complete actor pack (`admin` or `agent`).",
    )(command)
    command = click.option("--set", "obsolete_sets", multiple=True, hidden=True)(command)
    command = click.option(
        "--skill-set",
        "obsolete_skill_sets",
        multiple=True,
        hidden=True,
    )(command)
    return click.option("--skill", "obsolete_skills", multiple=True, hidden=True)(command)


def _target_options(command: Any) -> Any:
    """Add shared target and home options to one command."""

    command = click.option("--tool", required=True, help=_SYSTEM_SKILLS_TARGET_HELP)(command)
    return click.option(
        "--home",
        type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
        help=_SYSTEM_SKILLS_HOME_HELP,
    )(command)


@system_skills_group.command(name="install")
@_target_options
@_pack_selection_options
@click.option(
    "--symlink",
    "use_symlink",
    is_flag=True,
    help="Link each top-level destination directly to its complete packaged source.",
)
def install_system_skills_command(
    tool: str,
    home: Path | None,
    pack_ids: tuple[str, ...],
    obsolete_sets: tuple[str, ...],
    obsolete_skill_sets: tuple[str, ...],
    obsolete_skills: tuple[str, ...],
    use_symlink: bool,
) -> None:
    """Install complete packs; omission selects the external admin default."""

    _reject_obsolete_selectors(obsolete_sets, obsolete_skill_sets, obsolete_skills)
    tools = _parse_system_skills_tools(tool)
    _validate_home_scope_for_system_skills_tools(tools=tools, home=home)
    _preflight_pack_ids(pack_ids)
    payloads: list[dict[str, object]] = []
    try:
        for tool_name in tools:
            result = install_system_skill_packs_for_home(
                tool=tool_name,
                home_path=_resolve_effective_system_skills_home(tool=tool_name, home=home),
                pack_ids=pack_ids,
                use_cli_default=not pack_ids,
                projection_mode="symlink" if use_symlink else "copy",
            )
            payloads.append(_install_payload(result))
    except (OSError, RuntimeError) as exc:
        raise click.ClickException(str(exc)) from exc
    payload: dict[str, object] = (
        payloads[0] if len(payloads) == 1 else {"tools": list(tools), "installations": payloads}
    )
    emit(payload, plain_renderer=_render_install_plain)


@system_skills_group.command(name="status")
@_target_options
def status_system_skills_command(tool: str, home: Path | None) -> None:
    """Show config integrity, per-pack state, and legacy evidence."""

    tools = _parse_system_skills_tools(tool)
    _validate_home_scope_for_system_skills_tools(tools=tools, home=home)
    payloads = [
        _status_payload(
            inspect_system_skill_packs(
                tool=tool_name,
                home_path=_resolve_effective_system_skills_home(
                    tool=tool_name,
                    home=home,
                ),
            )
        )
        for tool_name in tools
    ]
    payload: dict[str, object] = (
        payloads[0] if len(payloads) == 1 else {"tools": list(tools), "statuses": payloads}
    )
    emit(payload, plain_renderer=_render_status_plain)


@system_skills_group.command(name="doctor")
@click.option(
    "--pack",
    "pack_ids",
    multiple=True,
    help="Repeatable expected pack (`admin` or `agent`); defaults to `agent`.",
)
@click.option("--tool", help=_SYSTEM_SKILLS_TARGET_HELP)
@click.option(
    "--home",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    help=_SYSTEM_SKILLS_HOME_HELP,
)
@click.option("--agent-id", help="Authoritative id of one known local managed agent.")
@click.option("--agent-name", help="Unique friendly name of one known local managed agent.")
def doctor_system_skills_command(
    pack_ids: tuple[str, ...],
    tool: str | None,
    home: Path | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Diagnose expected installed roots and versions without changing them."""

    target = _resolve_system_skills_doctor_target(
        tool=tool,
        home=home,
        agent_id=agent_id,
        agent_name=agent_name,
    )
    try:
        resolve_system_skill_pack_selection(
            load_system_skill_manifest(),
            pack_ids=pack_ids or ("agent",),
        )
    except RuntimeError as exc:
        raise click.UsageError(str(exc)) from exc
    try:
        result = inspect_system_skill_doctor(target=target, pack_ids=pack_ids)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    payload = _doctor_payload(result)
    emit(payload, plain_renderer=_render_doctor_plain)
    if not result.healthy:
        raise click.exceptions.Exit(1)


@system_skills_group.command(name="upgrade")
@_target_options
@_pack_selection_options
@click.option(
    "--symlink",
    "use_symlink",
    is_flag=True,
    help="Refresh each top-level destination as a direct packaged-source symlink.",
)
def upgrade_system_skills_command(
    tool: str,
    home: Path | None,
    pack_ids: tuple[str, ...],
    obsolete_sets: tuple[str, ...],
    obsolete_skill_sets: tuple[str, ...],
    obsolete_skills: tuple[str, ...],
    use_symlink: bool,
) -> None:
    """Refresh selected packs and conservatively migrate legacy flat paths."""

    _reject_obsolete_selectors(obsolete_sets, obsolete_skill_sets, obsolete_skills)
    tools = _parse_system_skills_tools(tool)
    _validate_home_scope_for_system_skills_tools(tools=tools, home=home)
    _preflight_pack_ids(pack_ids)
    payloads: list[dict[str, object]] = []
    try:
        for tool_name in tools:
            result = upgrade_system_skill_packs_for_home(
                tool=tool_name,
                home_path=_resolve_effective_system_skills_home(tool=tool_name, home=home),
                pack_ids=pack_ids,
                use_cli_default=not pack_ids,
                projection_mode="symlink" if use_symlink else "copy",
            )
            payloads.append(_upgrade_payload(result))
    except (OSError, RuntimeError) as exc:
        raise click.ClickException(str(exc)) from exc
    payload: dict[str, object] = (
        payloads[0] if len(payloads) == 1 else {"tools": list(tools), "upgrades": payloads}
    )
    emit(payload, plain_renderer=_render_upgrade_plain)


@system_skills_group.command(name="uninstall")
@_target_options
@_pack_selection_options
def uninstall_system_skills_command(
    tool: str,
    home: Path | None,
    pack_ids: tuple[str, ...],
    obsolete_sets: tuple[str, ...],
    obsolete_skill_sets: tuple[str, ...],
    obsolete_skills: tuple[str, ...],
) -> None:
    """Remove selected config-owned packs; omission selects all owned packs."""

    _reject_obsolete_selectors(obsolete_sets, obsolete_skill_sets, obsolete_skills)
    tools = _parse_system_skills_tools(tool)
    _validate_home_scope_for_system_skills_tools(tools=tools, home=home)
    _preflight_pack_ids(pack_ids)
    payloads: list[dict[str, object]] = []
    try:
        for tool_name in tools:
            result = uninstall_system_skill_packs_for_home(
                tool=tool_name,
                home_path=_resolve_effective_system_skills_home(tool=tool_name, home=home),
                pack_ids=pack_ids,
            )
            payloads.append(_uninstall_payload(result))
    except (OSError, RuntimeError) as exc:
        raise click.ClickException(str(exc)) from exc
    payload: dict[str, object] = (
        payloads[0] if len(payloads) == 1 else {"tools": list(tools), "uninstallations": payloads}
    )
    emit(payload, plain_renderer=_render_uninstall_plain)


def _install_payload(result: SystemSkillInstallResult) -> dict[str, object]:
    """Return structured install output."""

    return {
        "tool": result.tool,
        "home_path": str(result.home_path),
        "selected_packs": list(result.selected_pack_ids),
        "standalone_skills": list(result.standalone_skill_names),
        "projected_relative_dirs": list(result.projected_relative_dirs),
        "config_path": str(result.config_path),
        "projection_mode": result.projection_mode,
        "owning_pack_ids_by_skill": {
            name: list(owner_ids) for name, owner_ids in result.owning_pack_ids_by_skill.items()
        },
        "removed_packs": list(result.removed_pack_ids),
        "removed_projected_relative_dirs": list(result.removed_projected_relative_dirs),
        "safely_removed_legacy_paths": list(result.safely_removed_legacy_paths),
    }


def _status_payload(result: SystemSkillStatusResult) -> dict[str, object]:
    """Return structured status output."""

    return {
        "tool": result.tool,
        "home_path": str(result.home_path),
        "config": {
            "status": result.config.status,
            "path": str(result.config.path),
            "message": result.config.message,
            "houmao_version": (
                result.config.config.houmao_version if result.config.config is not None else None
            ),
            "selected_packs": (
                list(result.config.config.selected_pack_ids)
                if result.config.config is not None
                else []
            ),
        },
        "members": [
            {
                "name": record.name,
                "role": record.role,
                "activation": record.activation,
                "status": record.status,
                "relative_path": record.relative_path,
                "owning_pack_ids": list(record.owning_pack_ids),
                "projection_mode": record.projection_mode,
                "expected_content_digest": record.expected_content_digest,
            }
            for record in result.members
        ],
        "packs": [
            {
                "pack_id": record.pack_id,
                "audience": record.audience,
                "status": record.status,
                "standalone_skills": list(record.standalone_skill_names),
                "standalone_paths": list(record.standalone_paths),
                "missing_paths": list(record.missing_paths),
                "drifted_paths": list(record.drifted_paths),
                "conflicting_paths": list(record.conflicting_paths),
            }
            for record in result.packs
        ],
        "legacy": {
            "status": result.legacy.status,
            "paths": [
                {
                    "name": record.name,
                    "relative_path": record.relative_path,
                    "classification": record.classification,
                    "content_digest": record.content_digest,
                    "link_target": record.link_target,
                }
                for record in result.legacy.paths
            ],
        },
    }


def _doctor_payload(result: SystemSkillDoctorResult) -> dict[str, object]:
    """Return complete structured doctor output."""

    target = result.target
    return {
        "target": {
            "kind": target.kind,
            "tool": target.tool,
            "home_path": str(target.home_path),
            "agent_id": target.agent_id,
            "agent_name": target.agent_name,
            "lifecycle_state": target.lifecycle_state,
            "session_manifest_path": (
                str(target.session_manifest_path)
                if target.session_manifest_path is not None
                else None
            ),
            "brain_manifest_path": (
                str(target.brain_manifest_path) if target.brain_manifest_path is not None else None
            ),
        },
        "running_houmao_version": result.running_houmao_version,
        "selected_packs": list(result.selected_pack_ids),
        "config": {
            "status": result.config.status,
            "path": str(result.config.path),
            "message": result.config.message,
            "houmao_version": result.config.houmao_version,
            "selected_packs": list(result.config.selected_pack_ids),
        },
        "healthy": result.healthy,
        "members": [
            {
                "name": member.name,
                "role": member.role,
                "expected_packs": list(member.expected_pack_ids),
                "relative_path": member.relative_path,
                "path": str(member.path),
                "healthy": member.healthy,
                "integrity_status": member.integrity_status,
                "expected_content_digest": member.expected_content_digest,
                "observed_content_digest": member.observed_content_digest,
                "observed_version": member.observed_version,
                "version_status": member.version_status,
                "issues": list(member.issues),
                "config": {
                    "present": member.config.present,
                    "projection_mode": member.config.projection_mode,
                    "content_digest": member.config.content_digest,
                    "owning_packs": list(member.config.owning_pack_ids),
                },
            }
            for member in result.members
        ],
    }


def _upgrade_payload(result: SystemSkillUpgradeResult) -> dict[str, object]:
    """Return structured upgrade output."""

    payload = _install_payload(result.install)
    payload["legacy_before"] = {
        "status": result.legacy_before.status,
        "paths": [
            {
                "name": record.name,
                "relative_path": record.relative_path,
                "classification": record.classification,
            }
            for record in result.legacy_before.paths
        ],
    }
    payload["preserved_legacy_paths"] = list(result.preserved_legacy_paths)
    return payload


def _uninstall_payload(result: SystemSkillUninstallResult) -> dict[str, object]:
    """Return structured uninstall output."""

    return {
        "tool": result.tool,
        "home_path": str(result.home_path),
        "requested_packs": list(result.requested_pack_ids),
        "removed_packs": list(result.removed_pack_ids),
        "absent_packs": list(result.absent_pack_ids),
        "removed_projected_relative_dirs": list(result.removed_projected_relative_dirs),
        "retained_shared_skills": list(result.retained_shared_skill_names),
        "preserved_conflicting_paths": list(result.preserved_conflicting_paths),
        "config_path": str(result.config_path),
    }


def _render_list_plain(payload: object) -> None:
    """Render static collection and pack inventory."""

    mapping = _mapping(payload)
    click.echo("Houmao system-skill packs:")
    for pack in _mapping_list(mapping.get("packs")):
        lanes = ", ".join(_string_list(pack.get("default_lanes"))) or "explicit only"
        click.echo(f"  - {pack.get('pack_id')} ({pack.get('audience')}): defaults={lanes}")
        click.echo(f"      members: {', '.join(_string_list(pack.get('standalone_skills')))}")
    click.echo("Standalone skills:")
    for record in _mapping_list(mapping.get("standalone_skills")):
        owners = ", ".join(_string_list(record.get("pack_ids")))
        click.echo(
            f"  - {record.get('name')} ({record.get('role')}, "
            f"activation={record.get('activation')}, packs={owners})"
        )
    shared = _mapping_list(mapping.get("shared_routines"))
    click.echo(f"Shared parent-scoped routines: {len(shared)}")
    for record in shared:
        click.echo(f"  - {record.get('logical_id')}: {record.get('invocation')}")
    click.echo("Managed auto skill remains separate: houmao-auto-system-prompt")


def _render_install_plain(payload: object) -> None:
    """Render one or multiple install results."""

    mapping = _mapping(payload)
    installations = _mapping_list(mapping.get("installations")) or [mapping]
    for item in installations:
        click.echo(
            f"Installed packs for {item.get('tool')}: {', '.join(_string_list(item.get('selected_packs')))}"
        )
        click.echo(f"Home: {item.get('home_path')}")
        click.echo(f"Skill config: {item.get('config_path')}")
        click.echo(f"Projection mode: {item.get('projection_mode')}")
        for path in _string_list(item.get("projected_relative_dirs")):
            click.echo(f"  - {path}")


def _render_status_plain(payload: object) -> None:
    """Render one or multiple status results."""

    mapping = _mapping(payload)
    statuses = _mapping_list(mapping.get("statuses")) or [mapping]
    for item in statuses:
        click.echo(f"Tool: {item.get('tool')}")
        click.echo(f"Home: {item.get('home_path')}")
        config = _mapping(item.get("config"))
        click.echo(f"Skill config: {config.get('status')} ({config.get('path')})")
        for pack in _mapping_list(item.get("packs")):
            click.echo(f"  - {pack.get('pack_id')}: {pack.get('status')}")
        for member in _mapping_list(item.get("members")):
            owners = ", ".join(_string_list(member.get("owning_pack_ids"))) or "none"
            click.echo(f"      {member.get('name')}: {member.get('status')} (owners={owners})")
        legacy = _mapping(item.get("legacy"))
        click.echo(f"Legacy flat state: {legacy.get('status')}")
        for record in _mapping_list(legacy.get("paths")):
            click.echo(f"  - {record.get('relative_path')}: {record.get('classification')}")


def _render_doctor_plain(payload: object) -> None:
    """Render concise health and corrective evidence for one doctor target."""

    mapping = _mapping(payload)
    target = _mapping(mapping.get("target"))
    label = target.get("agent_id") or target.get("home_path")
    click.echo(f"System-skill doctor target: {label}")
    click.echo(f"Tool/home: {target.get('tool')} / {target.get('home_path')}")
    click.echo(f"Expected Houmao release: {mapping.get('running_houmao_version')}")
    click.echo(f"Expected packs: {', '.join(_string_list(mapping.get('selected_packs')))}")
    config = _mapping(mapping.get("config"))
    click.echo(f"Skill config: {config.get('status')} ({config.get('path')})")
    click.echo(f"Health: {'healthy' if mapping.get('healthy') else 'unhealthy'}")
    failed = [
        member for member in _mapping_list(mapping.get("members")) if not member.get("healthy")
    ]
    if not failed:
        click.echo(
            f"Checked members: {len(_mapping_list(mapping.get('members')))} complete and current"
        )
        return
    click.echo("Failures:")
    for member in failed:
        click.echo(
            f"  - {member.get('name')}: integrity={member.get('integrity_status')}, "
            f"version={member.get('version_status')}, observed={member.get('observed_version')}"
        )
        for issue in _string_list(member.get("issues")):
            click.echo(f"      {issue}")


def _render_upgrade_plain(payload: object) -> None:
    """Render one or multiple upgrade results."""

    mapping = _mapping(payload)
    upgrades = _mapping_list(mapping.get("upgrades")) or [mapping]
    for item in upgrades:
        click.echo(
            f"Upgraded packs for {item.get('tool')}: {', '.join(_string_list(item.get('selected_packs')))}"
        )
        click.echo(f"Skill config: {item.get('config_path')}")
        removed = _string_list(item.get("safely_removed_legacy_paths"))
        preserved = _string_list(item.get("preserved_legacy_paths"))
        click.echo(f"Safely removed legacy paths: {len(removed)}")
        click.echo(f"Preserved legacy conflicts: {len(preserved)}")
        for path in preserved:
            click.echo(f"  - {path}")


def _render_uninstall_plain(payload: object) -> None:
    """Render one or multiple uninstall results."""

    mapping = _mapping(payload)
    uninstallations = _mapping_list(mapping.get("uninstallations")) or [mapping]
    for item in uninstallations:
        click.echo(
            f"Removed packs for {item.get('tool')}: {', '.join(_string_list(item.get('removed_packs'))) or '(none)'}"
        )
        click.echo(f"Home: {item.get('home_path')}")
        conflicts = _string_list(item.get("preserved_conflicting_paths"))
        retained = _string_list(item.get("retained_shared_skills"))
        if retained:
            click.echo(f"Retained shared skills: {', '.join(retained)}")
        if conflicts:
            click.echo("Preserved conflicts:")
            for path in conflicts:
                click.echo(f"  - {path}")


def _reject_obsolete_selectors(
    obsolete_sets: tuple[str, ...],
    obsolete_skill_sets: tuple[str, ...],
    obsolete_skills: tuple[str, ...],
) -> None:
    """Render one clear migration diagnostic for removed selectors."""

    if obsolete_sets or obsolete_skill_sets or obsolete_skills:
        raise click.ClickException(
            "Individual `--skill` and set-based `--set`/`--skill-set` selectors were removed. "
            "Use repeatable `--pack admin|agent`; houmao-shared-routines is a standalone pack "
            "member, not an independent pack selector."
        )


def _preflight_pack_ids(pack_ids: tuple[str, ...]) -> None:
    """Validate explicit pack ids before a multi-tool mutation."""

    if not pack_ids:
        return
    try:
        resolve_system_skill_pack_selection(load_system_skill_manifest(), pack_ids=pack_ids)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc


def _parse_system_skills_tools(raw_tool: str) -> tuple[str, ...]:
    """Parse a single or comma-separated target selector."""

    tools: list[str] = []
    for raw_part in raw_tool.split(","):
        tool = raw_part.strip()
        if not tool:
            raise click.ClickException(
                "Invalid --tool value: comma-separated lists cannot contain empty entries."
            )
        _validate_supported_system_skills_tool(tool)
        if tool in tools:
            raise click.ClickException(f"Duplicate tool `{tool}` in --tool.")
        tools.append(tool)
    return tuple(tools)


def _validate_home_scope_for_system_skills_tools(
    *,
    tools: tuple[str, ...],
    home: Path | None,
) -> None:
    """Reject one home override applied ambiguously to multiple tools."""

    if len(tools) > 1 and home is not None:
        raise click.ClickException("--home can only be used when --tool names exactly one tool.")


def _resolve_effective_system_skills_home(*, tool: str, home: Path | None) -> Path:
    """Resolve the target-native effective home."""

    _validate_supported_system_skills_tool(tool)
    if home is not None:
        return home.expanduser().resolve()
    if tool == _SYSTEM_SKILLS_UNIVERSAL_TARGET:
        return (Path.home() / ".agents").resolve()
    env_name = _SYSTEM_SKILLS_HOME_ENV_VAR_BY_TOOL[tool]
    env_value = os.environ.get(env_name)
    if env_value is not None and env_value.strip():
        return Path(env_value.strip()).expanduser().resolve()
    return (Path.cwd() / _SYSTEM_SKILLS_PROJECT_DEFAULT_HOME_BY_TOOL[tool]).resolve()


def _resolve_system_skills_doctor_target(
    *,
    tool: str | None,
    home: Path | None,
    agent_id: str | None,
    agent_name: str | None,
) -> SystemSkillDoctorTarget:
    """Validate doctor selector modes and resolve one inspection target."""

    has_agent_selector = agent_id is not None or agent_name is not None
    if agent_id is not None and agent_name is not None:
        raise click.UsageError("Use exactly one of --agent-id or --agent-name.")
    if has_agent_selector:
        if tool is not None or home is not None:
            raise click.UsageError(
                "Managed-agent selectors cannot be combined with --tool or --home."
            )
        try:
            target = resolve_managed_system_skill_doctor_target(
                agent_id=agent_id,
                agent_name=agent_name,
            )
        except SystemSkillDoctorTargetError as exc:
            raise click.UsageError(str(exc)) from exc
        _validate_system_skills_doctor_tool(target.tool)
        return target
    if tool is None:
        raise click.UsageError(
            "Choose one doctor target: --tool [--home] or exactly one of --agent-id/--agent-name."
        )
    if "," in tool:
        raise click.UsageError("Doctor --tool accepts exactly one supported tool.")
    _validate_system_skills_doctor_tool(tool)
    return SystemSkillDoctorTarget(
        kind="explicit-home",
        tool=tool,
        home_path=_resolve_effective_system_skills_home(tool=tool, home=home),
    )


def _validate_system_skills_doctor_tool(tool: str) -> None:
    """Validate one doctor tool using usage-error exit semantics."""

    try:
        _validate_supported_system_skills_tool(tool)
    except click.ClickException as exc:
        raise click.UsageError(exc.format_message()) from exc


def _validate_supported_system_skills_tool(tool: str) -> None:
    """Reject unsupported and misleading target aliases."""

    if tool in _SUPPORTED_SYSTEM_SKILLS_TARGETS:
        return
    if tool == "kimi-code":
        raise click.ClickException("Unsupported target `kimi-code`; use `kimi` for Kimi Code CLI.")
    supported = ", ".join(_SUPPORTED_SYSTEM_SKILLS_TARGETS)
    raise click.ClickException(
        f"Unsupported system-skill target `{tool}`. Expected one of: {supported}."
    )


def _mapping(value: object) -> dict[str, Any]:
    """Return a renderer-safe mapping."""

    return value if isinstance(value, dict) else {}


def _mapping_list(value: object) -> list[dict[str, Any]]:
    """Return a renderer-safe list of mappings."""

    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: object) -> list[str]:
    """Return a renderer-safe list of strings."""

    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
