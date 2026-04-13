"""Project-scoped mailbox commands."""

from __future__ import annotations

# ruff: noqa: F403,F405
from .project_common import *


@click.group(name="mailbox")
def project_mailbox_group() -> None:
    """Operate on `mailbox/` under the selected project overlay."""


@project_mailbox_group.command(name="init")
def init_project_mailbox_command() -> None:
    """Bootstrap or validate `mailbox/` under the selected project overlay."""

    roots = _ensure_project_mailbox_roots()
    emit(_project_mailbox_payload(roots=roots, payload=init_mailbox_root(roots.mailbox_root)))


@project_mailbox_group.command(name="status")
def status_project_mailbox_command() -> None:
    """Inspect `mailbox/` under the selected project overlay."""

    roots = _resolve_existing_project_mailbox_roots()
    emit(
        _project_mailbox_payload(
            roots=roots, payload=mailbox_root_status_payload(roots.mailbox_root)
        )
    )


@project_mailbox_group.command(name="register")
@click.option("--address", required=True, help="Full mailbox address.")
@click.option("--principal-id", required=True, help="Mailbox owner principal id.")
@click.option(
    "--mode",
    type=click.Choice(("safe", "force", "stash")),
    default="safe",
    show_default=True,
    help="Filesystem mailbox registration mode.",
)
@overwrite_confirm_option
def register_project_mailbox_command(address: str, principal_id: str, mode: str, yes: bool) -> None:
    """Register one mailbox address under `mailbox/` in the selected project overlay."""

    roots = _ensure_project_mailbox_roots()
    emit(
        _project_mailbox_payload(
            roots=roots,
            payload=register_mailbox_at_root(
                mailbox_root=roots.mailbox_root,
                address=address,
                principal_id=principal_id,
                mode=mode,
                confirm_destructive_replace=build_destructive_confirmation_callback(
                    yes=yes,
                    non_interactive_message=(
                        "Mailbox registration would replace existing durable mailbox state. "
                        "Rerun with `--yes` to confirm overwrite non-interactively or choose "
                        "a non-destructive registration mode."
                    ),
                ),
            ),
        )
    )


@project_mailbox_group.command(name="unregister")
@click.option("--address", required=True, help="Full mailbox address.")
@click.option(
    "--mode",
    type=click.Choice(("deactivate", "purge")),
    default="deactivate",
    show_default=True,
    help="Filesystem mailbox deregistration mode.",
)
def unregister_project_mailbox_command(address: str, mode: str) -> None:
    """Deactivate or purge one mailbox address under `mailbox/` in the selected overlay."""

    roots = _ensure_project_mailbox_roots()
    emit(
        _project_mailbox_payload(
            roots=roots,
            payload=unregister_mailbox_at_root(
                mailbox_root=roots.mailbox_root,
                address=address,
                mode=mode,
            ),
        )
    )


@project_mailbox_group.command(name="repair")
@click.option(
    "--cleanup-staging/--no-cleanup-staging",
    default=True,
    show_default=True,
    help="Clean staging artifacts during repair.",
)
@click.option(
    "--quarantine-staging/--remove-staging",
    default=True,
    show_default=True,
    help="Quarantine staging artifacts instead of deleting them.",
)
def repair_project_mailbox_command(cleanup_staging: bool, quarantine_staging: bool) -> None:
    """Repair `mailbox/` under the selected project overlay."""

    roots = _ensure_project_mailbox_roots()
    emit(
        _project_mailbox_payload(
            roots=roots,
            payload=repair_mailbox_root(
                mailbox_root=roots.mailbox_root,
                cleanup_staging=cleanup_staging,
                quarantine_staging=quarantine_staging,
            ),
        )
    )


@project_mailbox_group.command(name="cleanup")
@click.option(
    "--inactive-older-than-seconds",
    default=0,
    show_default=True,
    type=click.IntRange(min=0),
    help="Only clean inactive registrations older than this threshold.",
)
@click.option(
    "--stashed-older-than-seconds",
    default=0,
    show_default=True,
    type=click.IntRange(min=0),
    help="Only clean stashed registrations older than this threshold.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview inactive or stashed mailbox cleanup candidates without deleting them.",
)
def cleanup_project_mailbox_command(
    inactive_older_than_seconds: int,
    stashed_older_than_seconds: int,
    dry_run: bool,
) -> None:
    """Clean inactive or stashed registrations under `mailbox/` in the selected overlay."""

    roots = _ensure_project_mailbox_roots()
    emit_cleanup_payload(
        _project_mailbox_payload(
            roots=roots,
            payload=cleanup_mailbox_root(
                mailbox_root=roots.mailbox_root,
                inactive_older_than_seconds=inactive_older_than_seconds,
                stashed_older_than_seconds=stashed_older_than_seconds,
                dry_run=dry_run,
            ),
        )
    )


@project_mailbox_group.command(name="clear-messages")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview delivered-message clearing without deleting mail.",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Confirm delivered-message clearing non-interactively.",
)
def clear_project_mailbox_messages_command(dry_run: bool, yes: bool) -> None:
    """Clear delivered messages under `mailbox/` while preserving registrations."""

    if not dry_run:
        confirm_destructive_action(
            prompt=(
                "Clear all delivered messages from the selected project mailbox root while "
                "preserving mailbox registrations?"
            ),
            yes=yes,
            non_interactive_message=(
                "Project mailbox message clearing would delete delivered messages. Rerun with "
                "`--yes` to confirm non-interactively or use `--dry-run` to preview."
            ),
            cancelled_message="Project mailbox message clearing cancelled.",
        )
    roots = _ensure_project_mailbox_roots()
    emit_cleanup_payload(
        _project_mailbox_payload(
            roots=roots,
            payload=clear_mailbox_messages_at_root(
                mailbox_root=roots.mailbox_root,
                dry_run=dry_run,
            ),
        )
    )


@project_mailbox_group.command(name="export")
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    help="New archive directory to create for the project mailbox export.",
)
@click.option(
    "--all-accounts",
    is_flag=True,
    help="Export every registration row and every indexed canonical message.",
)
@click.option(
    "--address",
    "addresses",
    multiple=True,
    help="Full mailbox address to export; repeat for multiple selected accounts.",
)
@click.option(
    "--symlink-mode",
    type=click.Choice(("materialize", "preserve")),
    default="materialize",
    show_default=True,
    help="Materialize symlinks by default, or preserve archive-internal projection symlinks.",
)
def export_project_mailbox_command(
    output_dir: Path,
    all_accounts: bool,
    addresses: tuple[str, ...],
    symlink_mode: str,
) -> None:
    """Export selected project mailbox state into a portable archive directory."""

    roots = _resolve_existing_project_mailbox_roots()
    emit(
        _project_mailbox_payload(
            roots=roots,
            payload=export_mailbox_root(
                mailbox_root=roots.mailbox_root,
                output_dir=output_dir,
                all_accounts=all_accounts,
                addresses=addresses,
                symlink_mode=symlink_mode,
            ),
        )
    )


@project_mailbox_group.group(name="accounts")
def project_mailbox_accounts_group() -> None:
    """Inspect mailbox registrations under `mailbox/` in the selected overlay."""


@project_mailbox_accounts_group.command(name="list")
def list_project_mailbox_accounts_command() -> None:
    """List mailbox accounts under `mailbox/` in the selected overlay."""

    roots = _resolve_existing_project_mailbox_roots()
    emit(
        _project_mailbox_payload(
            roots=roots, payload=list_mailbox_accounts(mailbox_root=roots.mailbox_root)
        )
    )


@project_mailbox_accounts_group.command(name="get")
@click.option("--address", required=True, help="Full mailbox address.")
def get_project_mailbox_account_command(address: str) -> None:
    """Inspect one mailbox account under `mailbox/` in the selected overlay."""

    roots = _resolve_existing_project_mailbox_roots()
    try:
        payload = get_mailbox_account(mailbox_root=roots.mailbox_root, address=address)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    emit(_project_mailbox_payload(roots=roots, payload=payload))


@project_mailbox_group.group(name="messages")
def project_mailbox_messages_group() -> None:
    """Inspect structural message projections under `mailbox/` in the selected overlay."""


@project_mailbox_messages_group.command(name="list")
@click.option("--address", required=True, help="Full mailbox address.")
def list_project_mailbox_messages_command(address: str) -> None:
    """List structurally projected messages for one project-local mailbox address."""

    roots = _resolve_existing_project_mailbox_roots()
    try:
        payload = list_mailbox_messages(mailbox_root=roots.mailbox_root, address=address)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    emit(_project_mailbox_payload(roots=roots, payload=payload))


@project_mailbox_messages_group.command(name="get")
@click.option("--address", required=True, help="Full mailbox address.")
@click.option("--message-id", required=True, help="Canonical mailbox message id.")
def get_project_mailbox_message_command(address: str, message_id: str) -> None:
    """Get one structurally projected message for a project-local mailbox address."""

    roots = _resolve_existing_project_mailbox_roots()
    try:
        payload = get_mailbox_message(
            mailbox_root=roots.mailbox_root,
            address=address,
            message_id=message_id,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    emit(_project_mailbox_payload(roots=roots, payload=payload))


def _ensure_project_mailbox_roots() -> ProjectAwareLocalRoots:
    """Return ensured project roots for stateful project-mailbox commands."""

    return _ensure_project_roots()


def _resolve_existing_project_mailbox_roots() -> ProjectAwareLocalRoots:
    """Return existing project roots for non-creating project-mailbox commands."""

    return _resolve_existing_project_roots(fallback_label="shared mailbox root")


def _project_mailbox_payload(
    *,
    roots: ProjectAwareLocalRoots,
    payload: dict[str, object],
) -> dict[str, object]:
    """Extend one project-mailbox payload with selected-overlay wording fields."""

    return {
        **payload,
        "selected_overlay_root": str(roots.overlay_root),
        "selected_overlay_detail": _selected_overlay_detail(roots),
        "mailbox_root_detail": "Selected `mailbox/` under the selected project overlay.",
        "project_overlay_bootstrapped": roots.created_overlay,
        "overlay_bootstrap_detail": describe_overlay_bootstrap(
            created_overlay=roots.created_overlay,
            overlay_exists=roots.project_overlay is not None,
        ),
    }
