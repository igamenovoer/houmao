"""Exercise durable Mail decisions in isolated actual CCCC process homes.

Native Rust tests interrupt the implementation at each journal write boundary.
The crash-image cases here restore those precise on-disk images using a genuine
HTTP-committed read fact, then verify a fresh daemon's journal recovery. They do
not add a fault endpoint or environment hook to the production provider.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any
import uuid

import pytest

from tests.integration.cccc.test_receiver_recovery import (
    _Provider,
    _result,
    provider as provider,
)


def _mail(provider: _Provider, text: str = "synthetic Mail") -> str:
    """Append deferred correspondence through the current normal sender grant."""

    result = _result(
        provider.rpc(
            "sender",
            "mail.send",
            {"operation_id": uuid.uuid4().hex, "to": ["receiver"], "text": text},
        )
    )
    return str(result["event"]["id"])


def _read(provider: _Provider, operation: str, cursor: str = "") -> dict[str, Any]:
    """Make exactly one explicit consuming request with its caller-selected identity."""

    return _result(
        provider.rpc(
            "receiver",
            "mail.read",
            {"operation_id": operation, "expected_cursor": cursor, "limit": 1},
        )
    )


def _write_private(path: Path, value: object) -> None:
    """Publish one explicit crash-image document durably while its provider is stopped."""

    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def test_read_response_loss_reconciles_after_actual_daemon_crash(provider: _Provider) -> None:
    """A committed response treated as lost is recovered without consuming the following batch."""

    first, second = _mail(provider), _mail(provider)
    operation = uuid.uuid4().hex
    _read(provider, operation)  # Deliberately discard the batch as a lost HTTP response.
    provider.crash()
    provider.start()
    receipt = _result(provider.rpc("receiver", "mail.read-receipts", {"operation_id": operation}))
    assert receipt["found"] and receipt["receipt"]["event_ids"] == [first]
    repeated = _read(provider, operation)
    assert repeated["outcome"] == "already_completed" and repeated["messages"] == []
    assert repeated["receipt"] == receipt["receipt"]
    recovered = _result(provider.rpc("receiver", "chat.history", {"event_id": first}))
    assert recovered["messages"][0]["id"] == first
    assert _result(provider.rpc("receiver", "mail.peek"))["messages"][0]["id"] == second
    assert _result(provider.rpc("receiver", "mail.cursor"))["cursor"]["event_id"] == first


@pytest.mark.parametrize("published_cursor", [False, True], ids=["after-read-fact", "after-cursor"])
def test_actual_native_journal_recovers_a_durable_boundary_image(
    provider: _Provider, published_cursor: bool
) -> None:
    """Recover a genuine native read decision with its exact pending marker left behind."""

    first, second = _mail(provider), _mail(provider)
    group_path = provider.m_root / "data/groups" / provider.group
    cursor_path = group_path / "state/read_cursors.json"
    before = json.loads(cursor_path.read_text()) if cursor_path.exists() else None
    operation = uuid.uuid4().hex
    committed = _read(provider, operation)
    after = json.loads(cursor_path.read_text())
    facts = [json.loads(line) for line in (group_path / "ledger.jsonl").read_text().splitlines()]
    fact = next(event for event in facts if event["id"] == committed["receipt"]["read_event_id"])
    assert fact["kind"] == "mail.read" and fact["data"]["operation"]["event_ids"] == [first]
    provider.crash()
    if not published_cursor:
        if before is None:
            cursor_path.unlink()
        else:
            _write_private(cursor_path, before)
    expected = (
        (before or {})
        .get("cursors", {})
        .get("receiver", {"event_id": "", "ts": "", "updated_at": ""})
    )
    marker = {
        "schema": 1,
        "group_id": provider.group,
        "actor_id": "receiver",
        "expected": expected,
        "target": after["cursors"]["receiver"],
        "operation": fact["data"]["operation"],
    }
    _write_private(group_path / "state/read_cursors.pending.json", marker)
    provider.start()
    receipt = _result(provider.rpc("receiver", "mail.read-receipts", {"operation_id": operation}))
    assert receipt["found"] and receipt["receipt"] == committed["receipt"]
    assert _result(provider.rpc("receiver", "mail.cursor"))["cursor"]["event_id"] == first
    assert _result(provider.rpc("receiver", "mail.peek"))["messages"][0]["id"] == second
    assert _read(provider, operation)["outcome"] == "already_completed"
    assert not (group_path / "state/read_cursors.pending.json").exists()


def test_empty_decision_survives_restart_and_new_mail(provider: _Provider) -> None:
    """An empty completed ID cannot become a fresh read when new correspondence appears."""

    operation = uuid.uuid4().hex
    original = _read(provider, operation)
    assert original["outcome"] == "empty"
    provider.crash()
    provider.start()
    event = _mail(provider)
    repeated = _read(provider, operation)
    assert repeated["outcome"] == "already_completed"
    assert repeated["receipt"] == original["receipt"]
    assert _result(provider.rpc("receiver", "mail.peek"))["messages"][0]["id"] == event
    assert _result(provider.rpc("receiver", "mail.cursor"))["cursor"]["event_id"] == ""


def test_recreated_actor_cannot_reconcile_previous_generation(provider: _Provider) -> None:
    """A reused display name grants no access to the former registration's operation receipts."""

    operation = uuid.uuid4().hex
    original = _read(provider, operation)
    old = provider.m_grants["receiver"]
    _result(provider.client.delete(f"/api/v1/groups/{provider.group}/actors/receiver"))
    new = provider.add_actor("receiver")
    assert new["actor_generation"] != original["receipt"]["actor_generation"]
    assert provider.rpc(
        "receiver", "mail.read-receipts", {"operation_id": operation}, grant=old
    ).status_code in {401, 422}
    assert (
        _result(provider.rpc("receiver", "mail.read-receipts", {"operation_id": operation}))[
            "found"
        ]
        is False
    )
    assert _read(provider, operation)["outcome"] == "empty"


def test_read_decisions_remain_authoritative_after_native_ledger_compaction(
    provider: _Provider,
) -> None:
    """Archived retained segments preserve both empty and consumed operation identities."""

    empty_operation = uuid.uuid4().hex
    empty = _read(provider, empty_operation)
    first, second = _mail(provider), _mail(provider)
    operation = uuid.uuid4().hex
    consumed = _read(provider, operation)
    result = subprocess.run(
        [
            str(provider.m_binary),
            "ledger",
            "compact",
            "--group",
            provider.group,
            "--reason",
            "qualification",
        ],
        env=provider.m_environment,
        cwd=provider.m_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, "Native retained-ledger compaction failed"
    assert json.loads(result.stdout)["compacted"] is True
    provider.crash()
    provider.start()
    for selected, original in ((empty_operation, empty), (operation, consumed)):
        receipt = _result(
            provider.rpc("receiver", "mail.read-receipts", {"operation_id": selected})
        )
        assert receipt["found"] and receipt["receipt"] == original["receipt"]
        assert _read(provider, selected)["outcome"] == "already_completed"
    assert consumed["receipt"]["event_ids"] == [first]
    assert _result(provider.rpc("receiver", "mail.peek"))["messages"][0]["id"] == second
