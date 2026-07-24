"""Repo-local project-overlay commands for `houmao-mgr`."""

from __future__ import annotations

# ruff: noqa: F403,F405
from .project_common import *
from .credentials import project_credentials_group
from houmao.project.migration import detect_project_migration_plan
from .project_easy import easy_instance_group, easy_profile_group, easy_specialist_group
from .project_mailbox import project_mailbox_group
from .project_agent_definitions import project_agent_definitions_group
from .project_migrate import migrate_project_command
from .project_skills import project_skills_group
from .project_context import active_project_dir, store_project_command_context


@click.group(name="project")
@click.option(
    "--project-dir",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Human-facing project directory; selects `<project-dir>/.houmao`.",
)
@click.pass_context
def project_group(ctx: click.Context, project_dir: Path | None) -> None:
    """Manage first-class local Houmao project workflows."""

    store_project_command_context(ctx, project_dir=project_dir)


project_group.add_command(project_credentials_group)
project_group.add_command(project_skills_group)
project_group.add_command(project_agent_definitions_group)
project_group.add_command(migrate_project_command)


@project_group.command(name="init")
def init_project_command() -> None:
    """Create or validate the active project overlay, defaulting to `<cwd>/.houmao`."""

    cwd = Path.cwd().resolve()
    try:
        overlay_root = resolve_project_init_overlay_root(
            cwd=cwd,
            project_dir=active_project_dir(),
        )
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
            "native_agent_projection_root": str(result.project_overlay.agents_root),
            "runtime_root": str(result.project_overlay.runtime_root),
            "memory_root": str(result.project_overlay.memory_root),
            "mailbox_root": str(result.project_overlay.mailbox_root),
            "specialists_root": str(result.project_overlay.specialists_root),
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
        roots = resolve_project_aware_local_roots(cwd=cwd, project_dir=active_project_dir())
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    overlay = roots.project_overlay
    migration_payload = (
        detect_project_migration_plan(overlay).to_payload() if overlay is not None else None
    )
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
            "native_agent_projection_root": str(roots.agent_def_dir),
            "native_agent_projection_source": roots.agent_def_dir_source,
            "project_runtime_root": str(roots.runtime_root),
            "project_memory_root": str(roots.memory_root),
            "project_mailbox_root": str(roots.mailbox_root),
            "project_specialists_root": str(roots.easy_root / "specialists"),
            "requires_project_init": overlay is None,
            "would_bootstrap_overlay": False,
            "overlay_bootstrap_detail": _status_overlay_bootstrap_detail(roots),
            "migration": migration_payload,
        }
    )


project_group.add_command(easy_specialist_group, name="specialist")
project_group.add_command(easy_profile_group, name="profile")
project_group.add_command(easy_instance_group, name="agents")
project_group.add_command(project_mailbox_group)
