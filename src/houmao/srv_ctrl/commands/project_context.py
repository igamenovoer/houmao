"""Click context helpers for project command selection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import click


@dataclass(frozen=True)
class ProjectCommandContext:
    """Group-level project command selection."""

    project_dir: Path | None = None


PROJECT_CONTEXT_KEY = "project"


def store_project_command_context(ctx: click.Context, *, project_dir: Path | None) -> None:
    """Store the selected project command context on the Click object map."""

    ctx.ensure_object(dict)
    assert isinstance(ctx.obj, dict)
    ctx.obj[PROJECT_CONTEXT_KEY] = ProjectCommandContext(project_dir=project_dir)


def active_project_dir() -> Path | None:
    """Return the active group-level project directory selector when present."""

    ctx = click.get_current_context(silent=True)
    while ctx is not None:
        obj = ctx.obj
        if isinstance(obj, dict):
            project_context = obj.get(PROJECT_CONTEXT_KEY)
            if isinstance(project_context, ProjectCommandContext):
                return project_context.project_dir
        ctx = ctx.parent
    return None
