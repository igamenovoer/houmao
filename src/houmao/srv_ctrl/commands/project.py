"""Repo-local project-overlay commands for `houmao-mgr`."""

from __future__ import annotations

# ruff: noqa: F403,F405
from .project_common import *
from .credentials import project_credentials_group
from .project_definitions import project_presets_group, project_recipes_group, project_roles_group
from .project_easy import easy_project_group
from .project_launch_profiles import project_launch_profiles_group
from .project_mailbox import project_mailbox_group
from .project_tools import project_tools_group


@click.group(name="project")
def project_group() -> None:
    """Manage the selected Houmao project overlay for this invocation."""


project_group.add_command(project_credentials_group)


@project_group.command(name="init")
def init_project_command() -> None:
    """Create or validate the active project overlay, defaulting to `<cwd>/.houmao`."""

    cwd = Path.cwd().resolve()
    try:
        overlay_root = resolve_project_init_overlay_root(cwd=cwd)
        result = bootstrap_project_overlay_at_root(overlay_root)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    emit(
        {
            "project_root": str(result.project_overlay.project_root),
            "overlay_root": str(result.project_overlay.overlay_root),
            "config_path": str(result.project_overlay.config_path),
            "catalog_path": str(result.project_overlay.catalog_path),
            "content_root": str(result.project_overlay.content_root),
            "agent_def_dir": str(result.project_overlay.agents_root),
            "runtime_root": str(result.project_overlay.runtime_root),
            "memory_root": str(result.project_overlay.memory_root),
            "mailbox_root": str(result.project_overlay.mailbox_root),
            "easy_root": str(result.project_overlay.easy_root),
            "created_directories": [str(path) for path in result.created_directories],
            "written_files": [str(path) for path in result.written_files],
            "preserved_files": [str(path) for path in result.preserved_files],
        }
    )


@project_group.command(name="status")
def project_status_command() -> None:
    """Report the selected Houmao project-overlay state for this invocation."""

    cwd = Path.cwd().resolve()
    try:
        roots = resolve_project_aware_local_roots(cwd=cwd)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    overlay = roots.project_overlay
    emit(
        {
            "discovered": overlay is not None,
            "project_root": str(overlay.project_root) if overlay is not None else None,
            "overlay_root": str(roots.overlay_root),
            "overlay_root_source": roots.overlay_root_source,
            "overlay_discovery_mode": roots.overlay_discovery_mode,
            "overlay_discovery_detail": describe_overlay_discovery_mode(
                overlay_discovery_mode=roots.overlay_discovery_mode
            ),
            "selected_overlay_detail": _selected_overlay_detail(roots),
            "config_path": str(overlay.config_path) if overlay is not None else None,
            "catalog_path": str(overlay.catalog_path) if overlay is not None else None,
            "effective_agent_def_dir": str(roots.agent_def_dir),
            "effective_agent_def_dir_source": roots.agent_def_dir_source,
            "project_runtime_root": str(roots.runtime_root),
            "project_memory_root": str(roots.memory_root),
            "project_mailbox_root": str(roots.mailbox_root),
            "project_easy_root": str(roots.easy_root),
            "would_bootstrap_overlay": overlay is None,
            "overlay_bootstrap_detail": _status_overlay_bootstrap_detail(roots),
        }
    )


@project_group.group(name="agents")
def agents_project_group() -> None:
    """Manage project-local agent definition sources."""


agents_project_group.add_command(project_tools_group)
agents_project_group.add_command(project_roles_group)
agents_project_group.add_command(project_presets_group)
agents_project_group.add_command(project_recipes_group)
agents_project_group.add_command(project_launch_profiles_group)
project_group.add_command(easy_project_group)
project_group.add_command(project_mailbox_group)
