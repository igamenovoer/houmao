"""Local maintenance commands for `houmao-mgr`."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any, Callable

import click

from houmao.agents.realm_controller.registry_storage import cleanup_stale_live_agent_records

from .cleanup_support import CleanupAction, build_cleanup_payload
from .common import emit_json
from .runtime_cleanup import (
    CleanupResolutionError,
    cleanup_runtime_builds,
    cleanup_runtime_logs,
    cleanup_runtime_mailbox_credentials,
    cleanup_runtime_sessions,
)


def _runtime_root_option(function: Callable[..., Any]) -> Callable[..., Any]:
    """Attach the shared runtime-root option."""

    return click.option(
        "--runtime-root",
        type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
        default=None,
        help=(
            "Runtime root override. Defaults to `AGENTSYS_GLOBAL_RUNTIME_DIR` or the shared "
            "Houmao runtime root."
        ),
    )(function)


def _registry_tmux_check_option(function: Callable[..., Any]) -> Callable[..., Any]:
    """Attach the shared registry tmux-check opt-out option."""

    return click.option(
        "--no-tmux-check",
        is_flag=True,
        help=(
            "Disable local tmux liveness checks for tmux-backed records; by default cleanup "
            "verifies the owning tmux session locally."
        ),
    )(function)


@click.group(name="admin")
def admin_group() -> None:
    """Local maintenance commands; these do not call `houmao-server`."""


@admin_group.group(name="cleanup")
def cleanup_group() -> None:
    """Grouped local cleanup commands for registry and runtime maintenance."""


@cleanup_group.command(name="registry")
@click.option(
    "--grace-seconds",
    default=300,
    show_default=True,
    type=click.IntRange(min=0),
    help="Extra grace period after lease expiry before removing stale directories.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview stale shared-registry records without deleting them.",
)
@_registry_tmux_check_option
def cleanup_registry_command(
    grace_seconds: int,
    dry_run: bool,
    no_tmux_check: bool,
) -> None:
    """Clean stale shared-registry live-agent directories on the local host."""

    emit_json(
        _registry_cleanup_payload(
            grace_seconds=grace_seconds,
            dry_run=dry_run,
            probe_local_tmux=(not no_tmux_check),
        )
    )


@admin_group.command(name="cleanup-registry")
@click.option(
    "--grace-seconds",
    default=300,
    show_default=True,
    type=click.IntRange(min=0),
    help="Extra grace period after lease expiry before removing stale directories.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview stale shared-registry records without deleting them.",
)
@_registry_tmux_check_option
def cleanup_registry_alias_command(
    grace_seconds: int,
    dry_run: bool,
    no_tmux_check: bool,
) -> None:
    """Compatibility alias for `houmao-mgr admin cleanup registry`."""

    emit_json(
        _registry_cleanup_payload(
            grace_seconds=grace_seconds,
            dry_run=dry_run,
            probe_local_tmux=(not no_tmux_check),
        )
    )


@cleanup_group.group(name="runtime")
def cleanup_runtime_group() -> None:
    """Host-scoped cleanup of runtime-owned local artifacts."""


@cleanup_runtime_group.command(name="sessions")
@_runtime_root_option
@click.option(
    "--older-than-seconds",
    default=0,
    show_default=True,
    type=click.IntRange(min=0),
    help="Only remove removable session envelopes older than this threshold.",
)
@click.option(
    "--include-job-dir/--no-include-job-dir",
    default=False,
    show_default=True,
    help="Also remove manifest-persisted job directories for removable sessions.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview removable session envelopes without deleting them.",
)
def cleanup_runtime_sessions_command(
    runtime_root: Path | None,
    older_than_seconds: int,
    include_job_dir: bool,
    dry_run: bool,
) -> None:
    """Clean stopped or malformed runtime session envelopes."""

    _emit_runtime_cleanup(
        cleanup_runtime_sessions(
            runtime_root=runtime_root,
            older_than_seconds=older_than_seconds,
            include_job_dir=include_job_dir,
            dry_run=dry_run,
        )
    )


@cleanup_runtime_group.command(name="builds")
@_runtime_root_option
@click.option(
    "--older-than-seconds",
    default=0,
    show_default=True,
    type=click.IntRange(min=0),
    help="Only remove unreferenced build artifacts older than this threshold.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview removable build artifacts without deleting them.",
)
def cleanup_runtime_builds_command(
    runtime_root: Path | None,
    older_than_seconds: int,
    dry_run: bool,
) -> None:
    """Clean unreferenced or broken build manifest-home pairs."""

    _emit_runtime_cleanup(
        cleanup_runtime_builds(
            runtime_root=runtime_root,
            older_than_seconds=older_than_seconds,
            dry_run=dry_run,
        )
    )


@cleanup_runtime_group.command(name="logs")
@_runtime_root_option
@click.option(
    "--older-than-seconds",
    default=0,
    show_default=True,
    type=click.IntRange(min=0),
    help="Only remove runtime log artifacts older than this threshold.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview removable runtime log artifacts without deleting them.",
)
def cleanup_runtime_logs_command(
    runtime_root: Path | None,
    older_than_seconds: int,
    dry_run: bool,
) -> None:
    """Clean log-style runtime artifacts while preserving durable state."""

    _emit_runtime_cleanup(
        cleanup_runtime_logs(
            runtime_root=runtime_root,
            older_than_seconds=older_than_seconds,
            dry_run=dry_run,
        )
    )


@cleanup_runtime_group.command(name="mailbox-credentials")
@_runtime_root_option
@click.option(
    "--older-than-seconds",
    default=0,
    show_default=True,
    type=click.IntRange(min=0),
    help="Only remove unreferenced credential files older than this threshold.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview removable credential files without deleting them.",
)
def cleanup_runtime_mailbox_credentials_command(
    runtime_root: Path | None,
    older_than_seconds: int,
    dry_run: bool,
) -> None:
    """Clean unreferenced runtime-owned Stalwart credential files."""

    _emit_runtime_cleanup(
        cleanup_runtime_mailbox_credentials(
            runtime_root=runtime_root,
            older_than_seconds=older_than_seconds,
            dry_run=dry_run,
        )
    )


def _emit_runtime_cleanup(payload: dict[str, object]) -> None:
    """Emit one runtime cleanup payload with consistent click error handling."""

    try:
        emit_json(payload)
    except CleanupResolutionError as exc:
        raise click.ClickException(str(exc)) from exc


def _registry_cleanup_payload(
    *,
    grace_seconds: int,
    dry_run: bool,
    probe_local_tmux: bool,
) -> dict[str, object]:
    """Return the structured payload for registry cleanup commands."""

    result = cleanup_stale_live_agent_records(
        grace_period=timedelta(seconds=grace_seconds),
        dry_run=dry_run,
        probe_local_tmux=probe_local_tmux,
    )
    planned_actions: list[CleanupAction] = []
    applied_actions: list[CleanupAction] = []
    blocked_actions: list[CleanupAction] = []
    preserved_actions: list[CleanupAction] = []

    for action in result.actions:
        normalized = CleanupAction(
            artifact_kind="registry_live_agent_record",
            path=action.path,
            proposed_action="remove" if action.outcome != "preserved" else "preserve",
            reason=action.reason,
            details={"agent_id": action.agent_id},
        )
        if action.outcome == "planned":
            planned_actions.append(normalized)
        elif action.outcome == "removed":
            applied_actions.append(normalized)
        elif action.outcome == "failed":
            blocked_actions.append(normalized)
        else:
            preserved_actions.append(normalized)

    payload = build_cleanup_payload(
        dry_run=dry_run,
        scope={
            "kind": "registry_cleanup",
            "registry_root": str(result.registry_root),
            "grace_seconds": grace_seconds,
        },
        resolution={
            "authority": "registry_root",
            "probe_local_tmux": probe_local_tmux,
        },
        planned_actions=planned_actions,
        applied_actions=applied_actions,
        blocked_actions=blocked_actions,
        preserved_actions=preserved_actions,
        extra_summary={
            "removed_count": len(result.removed_agent_ids),
            "planned_count": len(result.planned_agent_ids),
            "failed_count": len(result.failed_agent_ids),
            "preserved_count": len(result.preserved_agent_ids),
        },
    )
    payload.update(
        {
            "registry_root": str(result.registry_root),
            "removed_agent_ids": list(result.removed_agent_ids),
            "planned_agent_ids": list(result.planned_agent_ids),
            "preserved_agent_ids": list(result.preserved_agent_ids),
            "failed_agent_ids": list(result.failed_agent_ids),
            "grace_seconds": grace_seconds,
            "probe_local_tmux": probe_local_tmux,
        }
    )
    return payload
