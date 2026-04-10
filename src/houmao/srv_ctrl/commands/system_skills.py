"""Houmao-owned system-skill installation commands for `houmao-mgr`."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import click

from houmao.agents.system_skills import (
    discover_installed_system_skills,
    install_system_skills_for_home,
    load_system_skill_catalog,
)

from .output import emit

_SYSTEM_SKILLS_HOME_ENV_VAR_BY_TOOL: dict[str, str] = {
    "claude": "CLAUDE_CONFIG_DIR",
    "codex": "CODEX_HOME",
    "gemini": "GEMINI_CLI_HOME",
}
_SYSTEM_SKILLS_PROJECT_DEFAULT_HOME_BY_TOOL: dict[str, Path] = {
    "claude": Path(".claude"),
    "codex": Path(".codex"),
    "gemini": Path("."),
}


@click.group(name="system-skills")
def system_skills_group() -> None:
    """Install and inspect Houmao-owned system skills in resolved tool homes."""


@system_skills_group.command(name="list")
def list_system_skills_command() -> None:
    """List the current installable Houmao-owned skills and named sets."""

    catalog = load_system_skill_catalog()
    payload = {
        "schema_version": catalog.schema_version,
        "skills": [
            {
                "name": record.name,
                "asset_subpath": record.asset_subpath,
                "description": record.description,
            }
            for record in catalog.skills.values()
        ],
        "sets": [
            {
                "name": record.name,
                "description": record.description,
                "skills": list(record.skill_names),
            }
            for record in catalog.sets.values()
        ],
        "auto_install": {
            "managed_launch_sets": list(catalog.auto_install.managed_launch_sets),
            "managed_join_sets": list(catalog.auto_install.managed_join_sets),
            "cli_default_sets": list(catalog.auto_install.cli_default_sets),
        },
    }
    emit(payload, plain_renderer=_render_system_skills_list_plain)


@system_skills_group.command(name="status")
@click.option(
    "--tool", required=True, help="Supported tool identifier (`claude`, `codex`, or `gemini`)."
)
@click.option(
    "--home",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    help="Optional tool home override. Defaults to tool-native env redirect or the project-scoped tool home.",
)
def status_system_skills_command(tool: str, home: Path | None) -> None:
    """Show live Houmao-owned system-skill state for one resolved tool home."""

    resolved_home = _resolve_effective_system_skills_home(tool=tool, home=home)
    installed_records = discover_installed_system_skills(tool=tool, home_path=resolved_home)
    payload = {
        "tool": tool,
        "home_path": str(resolved_home),
        "installed_skills": [record.name for record in installed_records],
        "projected_relative_dirs": [record.projected_relative_dir for record in installed_records],
        "installed_skill_records": [
            {
                "name": record.name,
                "projected_relative_dir": record.projected_relative_dir,
                "projection_mode": record.projection_mode,
            }
            for record in installed_records
        ],
    }
    emit(payload, plain_renderer=_render_system_skills_status_plain)


@system_skills_group.command(name="install")
@click.option(
    "--tool", required=True, help="Supported tool identifier (`claude`, `codex`, or `gemini`)."
)
@click.option(
    "--home",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    help="Optional tool home override. Defaults to tool-native env redirect or the project-scoped tool home.",
)
@click.option(
    "--set", "set_names", multiple=True, help="Repeatable named system-skill set to install."
)
@click.option(
    "--skill", "skill_names", multiple=True, help="Repeatable explicit skill name to install."
)
@click.option(
    "--symlink",
    "use_symlink",
    is_flag=True,
    help="Install selected skills as directory symlinks to the packaged asset roots.",
)
def install_system_skills_command(
    tool: str,
    home: Path | None,
    set_names: tuple[str, ...],
    skill_names: tuple[str, ...],
    use_symlink: bool,
) -> None:
    """Install selected Houmao-owned system skills into one resolved tool home."""

    resolved_home = _resolve_effective_system_skills_home(tool=tool, home=home)
    use_cli_default = not set_names and not skill_names

    try:
        result = install_system_skills_for_home(
            tool=tool,
            home_path=resolved_home,
            set_names=set_names,
            skill_names=skill_names,
            use_cli_default=use_cli_default,
            projection_mode="symlink" if use_symlink else "copy",
        )
        payload = {
            "tool": result.tool,
            "home_path": str(result.home_path),
            "selected_sets": list(result.selected_set_names),
            "explicit_skills": list(result.explicit_skill_names),
            "resolved_skills": list(result.resolved_skill_names),
            "projected_relative_dirs": list(result.projected_relative_dirs),
            "projection_mode": result.projection_mode,
        }
    except OSError as exc:
        raise click.ClickException(str(exc)) from exc
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc

    emit(payload, plain_renderer=_render_system_skills_install_plain)


def _resolve_effective_system_skills_home(*, tool: str, home: Path | None) -> Path:
    """Resolve the effective target home for one system-skills CLI invocation."""

    _validate_supported_system_skills_tool(tool)
    if home is not None:
        return home.expanduser().resolve()

    env_var_name = _SYSTEM_SKILLS_HOME_ENV_VAR_BY_TOOL[tool]
    env_value = os.environ.get(env_var_name)
    if env_value is not None and env_value.strip():
        return Path(env_value.strip()).expanduser().resolve()

    project_default = _SYSTEM_SKILLS_PROJECT_DEFAULT_HOME_BY_TOOL[tool]
    return (Path.cwd().resolve() / project_default).resolve()


def _validate_supported_system_skills_tool(tool: str) -> None:
    """Fail fast when the operator selects an unsupported tool."""

    if tool in _SYSTEM_SKILLS_HOME_ENV_VAR_BY_TOOL:
        return
    supported = ", ".join(f"`{name}`" for name in sorted(_SYSTEM_SKILLS_HOME_ENV_VAR_BY_TOOL))
    raise click.ClickException(
        f"Unsupported tool `{tool}`. Expected one of: {supported}."
    )


def _render_system_skills_list_plain(payload: object) -> None:
    """Render `system-skills list` output in a readable plain-text form."""

    if not isinstance(payload, dict):
        click.echo(str(payload))
        return
    click.echo("Skills:")
    for record in _coerce_mapping_list(payload.get("skills")):
        name = str(record.get("name", ""))
        description = str(record.get("description", "")).strip()
        if description:
            click.echo(f"  - {name}: {description}")
        else:
            click.echo(f"  - {name}")

    click.echo("Sets:")
    auto_install = payload.get("auto_install")
    auto_install_mapping = auto_install if isinstance(auto_install, dict) else {}
    cli_default_sets = set(_coerce_string_list(auto_install_mapping.get("cli_default_sets")))
    managed_launch_sets = set(_coerce_string_list(auto_install_mapping.get("managed_launch_sets")))
    managed_join_sets = set(_coerce_string_list(auto_install_mapping.get("managed_join_sets")))
    for record in _coerce_mapping_list(payload.get("sets")):
        markers: list[str] = []
        name = str(record.get("name", ""))
        if name in cli_default_sets:
            markers.append("cli-default")
        if name in managed_launch_sets:
            markers.append("managed-launch")
        if name in managed_join_sets:
            markers.append("managed-join")
        marker_text = f" [{' '.join(markers)}]" if markers else ""
        skills = ", ".join(_coerce_string_list(record.get("skills")))
        click.echo(f"  - {name}{marker_text}: {skills}")


def _render_system_skills_status_plain(payload: object) -> None:
    """Render `system-skills status` output in a readable plain-text form."""

    if not isinstance(payload, dict):
        click.echo(str(payload))
        return
    click.echo(f"Tool: {payload.get('tool')}")
    click.echo(f"Home: {payload.get('home_path')}")
    installed_skill_records = _coerce_mapping_list(payload.get("installed_skill_records"))
    if not installed_skill_records:
        click.echo("Installed skills: (none)")
        return
    click.echo("Installed skills:")
    for record in installed_skill_records:
        skill_name = str(record.get("name", ""))
        projection_mode = str(record.get("projection_mode", "")).strip()
        projection_suffix = f" ({projection_mode})" if projection_mode else ""
        click.echo(f"  - {skill_name}{projection_suffix}")


def _render_system_skills_install_plain(payload: object) -> None:
    """Render `system-skills install` output in a readable plain-text form."""

    if not isinstance(payload, dict):
        click.echo(str(payload))
        return
    click.echo(
        f"Installed Houmao system skills into {payload.get('home_path')} ({payload.get('tool')})"
    )
    projection_mode = payload.get("projection_mode")
    if projection_mode is not None:
        click.echo(f"Projection mode: {projection_mode}")
    resolved_skills = _coerce_string_list(payload.get("resolved_skills"))
    if resolved_skills:
        click.echo("Resolved skills:")
        for skill_name in resolved_skills:
            click.echo(f"  - {skill_name}")


def _coerce_mapping_list(value: object) -> list[dict[str, Any]]:
    """Return one list of mapping items for renderer use."""

    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            result.append(item)
    return result


def _coerce_string_list(value: object) -> list[str]:
    """Return one list of strings for renderer use."""

    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
