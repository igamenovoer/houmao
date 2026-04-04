"""Houmao-owned system-skill installation commands for `houmao-mgr`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from houmao.agents.system_skills import (
    SYSTEM_SKILL_STATE_SCHEMA_VERSION,
    install_system_skills_for_home,
    load_system_skill_catalog,
    load_system_skill_install_state,
    system_skill_state_path_for_home,
)

from .output import emit


@click.group(name="system-skills")
def system_skills_group() -> None:
    """Install and inspect Houmao-owned system skills in explicit tool homes."""


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
    required=True,
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    help="Explicit tool home path to inspect.",
)
def status_system_skills_command(tool: str, home: Path) -> None:
    """Show Houmao-owned system-skill install state for one explicit tool home."""

    state = load_system_skill_install_state(tool=tool, home_path=home)
    state_path = system_skill_state_path_for_home(home)
    payload = {
        "tool": tool,
        "home_path": str(home.resolve()),
        "state_path": str(state_path),
        "state_exists": state is not None,
        "state_schema_version": SYSTEM_SKILL_STATE_SCHEMA_VERSION if state is not None else None,
        "installed_skills": [record.name for record in state.installed_skills]
        if state is not None
        else [],
        "projected_relative_dirs": (
            [record.projected_relative_dir for record in state.installed_skills]
            if state is not None
            else []
        ),
    }
    emit(payload, plain_renderer=_render_system_skills_status_plain)


@system_skills_group.command(name="install")
@click.option(
    "--tool", required=True, help="Supported tool identifier (`claude`, `codex`, or `gemini`)."
)
@click.option(
    "--home",
    required=True,
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    help="Explicit tool home path to update.",
)
@click.option(
    "--set", "set_names", multiple=True, help="Repeatable named system-skill set to install."
)
@click.option(
    "--skill", "skill_names", multiple=True, help="Repeatable explicit skill name to install."
)
@click.option(
    "--default",
    "use_default",
    is_flag=True,
    help="Install the packaged CLI-default system-skill set list.",
)
def install_system_skills_command(
    tool: str,
    home: Path,
    set_names: tuple[str, ...],
    skill_names: tuple[str, ...],
    use_default: bool,
) -> None:
    """Install selected Houmao-owned system skills into one explicit tool home."""

    if not use_default and not set_names and not skill_names:
        raise click.ClickException(
            "Select at least one system skill via `--default`, `--set`, or `--skill`."
        )

    try:
        result = install_system_skills_for_home(
            tool=tool,
            home_path=home,
            set_names=set_names,
            skill_names=skill_names,
            use_cli_default=use_default,
        )
        payload = {
            "tool": result.tool,
            "home_path": str(result.home_path),
            "state_path": str(result.state_path),
            "selected_sets": list(result.selected_set_names),
            "explicit_skills": list(result.explicit_skill_names),
            "resolved_skills": list(result.resolved_skill_names),
            "projected_relative_dirs": list(result.projected_relative_dirs),
        }
    except OSError as exc:
        raise click.ClickException(str(exc)) from exc
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc

    emit(payload, plain_renderer=_render_system_skills_install_plain)


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
    click.echo(f"State: {'present' if payload.get('state_exists') else 'missing'}")
    installed_skills = _coerce_string_list(payload.get("installed_skills"))
    if not installed_skills:
        click.echo("Installed skills: (none)")
        return
    click.echo("Installed skills:")
    for skill_name in installed_skills:
        click.echo(f"  - {skill_name}")


def _render_system_skills_install_plain(payload: object) -> None:
    """Render `system-skills install` output in a readable plain-text form."""

    if not isinstance(payload, dict):
        click.echo(str(payload))
        return
    click.echo(
        f"Installed Houmao system skills into {payload.get('home_path')} ({payload.get('tool')})"
    )
    click.echo(f"State path: {payload.get('state_path')}")
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
