"""Explicit project-structure migration command."""

from __future__ import annotations

from houmao.project.migration import apply_project_migration, detect_project_migration_plan

# ruff: noqa: F403,F405
from .project_common import *


@click.command(name="migrate")
@click.option(
    "--apply",
    "apply_changes",
    is_flag=True,
    help="Apply the detected migration plan in place.",
)
def migrate_project_command(apply_changes: bool) -> None:
    """Plan or apply a supported project-structure migration."""

    overlay = _resolve_existing_project_overlay()
    try:
        if apply_changes:
            result = apply_project_migration(overlay)
            emit(result.to_payload())
            return
        plan = detect_project_migration_plan(overlay)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    emit(plan.to_payload())
