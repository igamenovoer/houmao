"""Tests for per-rendered-block notifier audit persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from houmao.agents.realm_controller.gateway_storage import (
    GatewayNotifierAuditRenderedBlockEntry,
    append_gateway_notifier_audit_record,
    read_gateway_notifier_audit_records,
)


def _seed_queue_db(sqlite_path: Path) -> None:
    """Bootstrap the queue schema by writing one trivial audit row."""

    append_gateway_notifier_audit_record(
        sqlite_path,
        poll_time_utc="2026-04-27T12:00:00Z",
        unread_count=0,
        unread_digest=None,
        unread_summary=(),
        request_admission=None,
        active_execution=None,
        queue_depth=None,
        outcome="empty",
    )


def test_append_persists_rendered_block_entries(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "queue.sqlite"
    entries = (
        GatewayNotifierAuditRenderedBlockEntry(
            message_ref="filesystem:msg-a",
            rendered=True,
            auth_scheme="none",
            auth_outcome="skipped",
            auth_detail="no verifier configured",
            block_chars=42,
            block_truncated=False,
        ),
        GatewayNotifierAuditRenderedBlockEntry(
            message_ref="filesystem:msg-b",
            rendered=False,
            auth_scheme="shared-token",
            auth_outcome="failed",
            auth_detail="notify_auth.token did not match any allowlisted shared secret",
            block_chars=0,
            block_truncated=False,
        ),
    )

    record = append_gateway_notifier_audit_record(
        sqlite_path,
        poll_time_utc="2026-04-27T12:00:00Z",
        unread_count=2,
        unread_digest="digest-1",
        unread_summary=(),
        request_admission=None,
        active_execution=None,
        queue_depth=None,
        outcome="enqueued",
        enqueued_request_id="gwreq-1",
        rendered_block_entries=entries,
    )

    assert record.rendered_block_entries == entries

    loaded = read_gateway_notifier_audit_records(sqlite_path)
    assert len(loaded) == 1
    assert loaded[0].rendered_block_entries == entries


def test_append_default_emits_empty_rendered_block_entries(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "queue.sqlite"

    record = append_gateway_notifier_audit_record(
        sqlite_path,
        poll_time_utc="2026-04-27T12:00:00Z",
        unread_count=1,
        unread_digest="digest-empty",
        unread_summary=(),
        request_admission=None,
        active_execution=None,
        queue_depth=None,
        outcome="empty",
    )

    assert record.rendered_block_entries == ()
    loaded = read_gateway_notifier_audit_records(sqlite_path)
    assert loaded[0].rendered_block_entries == ()


def test_audit_rendered_block_entry_does_not_echo_token_in_detail(
    tmp_path: Path,
) -> None:
    sqlite_path = tmp_path / "queue.sqlite"
    sensitive_token = "very-secret-token-must-not-leak"
    entries = (
        GatewayNotifierAuditRenderedBlockEntry(
            message_ref="filesystem:msg-a",
            rendered=False,
            auth_scheme="shared-token",
            auth_outcome="failed",
            # The audit detail intentionally never contains the rejected token.
            auth_detail="notify_auth.token did not match any allowlisted shared secret",
            block_chars=0,
            block_truncated=False,
        ),
    )

    append_gateway_notifier_audit_record(
        sqlite_path,
        poll_time_utc="2026-04-27T12:00:00Z",
        unread_count=1,
        unread_digest=None,
        unread_summary=(),
        request_admission=None,
        active_execution=None,
        queue_depth=None,
        outcome="enqueued",
        rendered_block_entries=entries,
    )

    # Read raw JSON cell to confirm the verifier rejection detail does not
    # contain the supplied token text.
    with sqlite3.connect(sqlite_path) as connection:
        row = connection.execute(
            "SELECT rendered_block_entries_json FROM gateway_notifier_audit"
            " ORDER BY audit_id DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    raw_json = str(row[0])
    assert sensitive_token not in raw_json


def test_rendered_block_entry_is_a_frozen_dataclass() -> None:
    entry = GatewayNotifierAuditRenderedBlockEntry(
        message_ref="filesystem:msg-a",
        rendered=True,
        auth_scheme="none",
        auth_outcome="skipped",
        auth_detail=None,
        block_chars=10,
        block_truncated=False,
    )
    with pytest.raises(Exception):
        entry.rendered = False  # type: ignore[misc]
