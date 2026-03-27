"""Local managed-session cleanup commands for `houmao-mgr agents`."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import click

from houmao.agents.realm_controller.errors import SessionManifestError

from ..common import emit_json, managed_agent_selector_options
from ..runtime_cleanup import (
    CleanupResolutionError,
    cleanup_managed_session,
    cleanup_managed_session_logs,
    cleanup_managed_session_mailbox,
)


def _cleanup_target_options(function: Callable[..., Any]) -> Callable[..., Any]:
    """Attach the shared managed-session cleanup target options."""

    function = click.option(
        "--session-root",
        type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
        default=None,
        help="Explicit runtime-owned session root for a stopped managed session.",
    )(function)
    function = click.option(
        "--manifest-path",
        type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
        default=None,
        help="Explicit runtime-owned session manifest path for a stopped managed session.",
    )(function)
    return managed_agent_selector_options(function)


@click.group(name="cleanup")
def cleanup_group() -> None:
    """Local managed-session cleanup without `houmao-server`."""


@cleanup_group.command(name="session")
@click.option(
    "--include-job-dir/--no-include-job-dir",
    default=False,
    show_default=True,
    help="Also remove the manifest-persisted `job_dir` when the session is removable.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview removable artifacts without deleting them.",
)
@_cleanup_target_options
def cleanup_session_command(
    include_job_dir: bool,
    dry_run: bool,
    agent_id: str | None,
    agent_name: str | None,
    manifest_path: Path | None,
    session_root: Path | None,
) -> None:
    """Clean one stopped managed-session envelope and optional job dir."""

    _run_and_emit_cleanup(
        lambda: cleanup_managed_session(
            agent_id=agent_id,
            agent_name=agent_name,
            manifest_path=manifest_path,
            session_root=session_root,
            include_job_dir=include_job_dir,
            dry_run=dry_run,
        )
    )


@cleanup_group.command(name="logs")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview removable log-style artifacts without deleting them.",
)
@_cleanup_target_options
def cleanup_logs_command(
    dry_run: bool,
    agent_id: str | None,
    agent_name: str | None,
    manifest_path: Path | None,
    session_root: Path | None,
) -> None:
    """Clean session-local runtime log artifacts for one managed session."""

    _run_and_emit_cleanup(
        lambda: cleanup_managed_session_logs(
            agent_id=agent_id,
            agent_name=agent_name,
            manifest_path=manifest_path,
            session_root=session_root,
            dry_run=dry_run,
        )
    )


@cleanup_group.command(name="mailbox")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview removable session-local mailbox secrets without deleting them.",
)
@_cleanup_target_options
def cleanup_mailbox_command(
    dry_run: bool,
    agent_id: str | None,
    agent_name: str | None,
    manifest_path: Path | None,
    session_root: Path | None,
) -> None:
    """Clean session-local mailbox secret material for one managed session."""

    _run_and_emit_cleanup(
        lambda: cleanup_managed_session_mailbox(
            agent_id=agent_id,
            agent_name=agent_name,
            manifest_path=manifest_path,
            session_root=session_root,
            dry_run=dry_run,
        )
    )


def _run_and_emit_cleanup(build_payload: Callable[[], dict[str, object]]) -> None:
    """Run one cleanup producer and emit the resulting JSON payload."""

    try:
        emit_json(build_payload())
    except (CleanupResolutionError, SessionManifestError) as exc:
        raise click.ClickException(str(exc)) from exc
