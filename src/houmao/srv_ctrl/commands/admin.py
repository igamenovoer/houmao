"""Local maintenance commands for `houmao-srv-ctrl`."""

from __future__ import annotations

from datetime import timedelta

import click

from houmao.agents.realm_controller.registry_storage import cleanup_stale_live_agent_records

from .common import emit_json


@click.group(name="admin")
def admin_group() -> None:
    """Local maintenance commands; these do not call `houmao-server`."""


@admin_group.command(name="cleanup-registry")
@click.option(
    "--grace-seconds",
    default=300,
    type=int,
    help="Extra grace period after lease expiry before removing stale directories.",
)
def cleanup_registry_command(grace_seconds: int) -> None:
    """Remove stale shared-registry live-agent directories on the local host."""

    if grace_seconds < 0:
        raise click.ClickException("`--grace-seconds` must be >= 0.")

    result = cleanup_stale_live_agent_records(
        grace_period=timedelta(seconds=grace_seconds),
    )
    removed_agent_ids = tuple(
        getattr(result, "removed_agent_ids", getattr(result, "removed_agent_keys", ()))
    )
    preserved_agent_ids = tuple(
        getattr(result, "preserved_agent_ids", getattr(result, "preserved_agent_keys", ()))
    )
    failed_agent_ids = tuple(
        getattr(result, "failed_agent_ids", getattr(result, "failed_agent_keys", ()))
    )
    emit_json(
        {
            "failed_agent_ids": list(failed_agent_ids),
            "failed_count": len(failed_agent_ids),
            "grace_seconds": grace_seconds,
            "preserved_agent_ids": list(preserved_agent_ids),
            "preserved_count": len(preserved_agent_ids),
            "registry_root": str(result.registry_root),
            "removed_agent_ids": list(removed_agent_ids),
            "removed_count": len(removed_agent_ids),
        }
    )
