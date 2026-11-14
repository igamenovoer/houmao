"""Durable cycle admission, periodic reminders, and stale queued wakeups."""

import json
from pathlib import Path
import sqlite3
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
import pytest

from houmao.agents.realm_controller.gateway_service import create_app
from houmao.agents.realm_controller.manifest import mutate_session_mailbox_binding
from houmao.mailbox.notifier_admission import ReminderOrigin, admit_mail_reminder
from tests.unit.agents.realm_controller.test_gateway_dual_mail import _runtime
from tests.unit.agents.realm_controller.test_gateway_support import _deliver_unread_mailbox_message


def test_cycle_and_pending_request_admission_commit_atomically(tmp_path: Path) -> None:
    """Concurrent attempts insert once, and a failed queue insert admits no cycle."""

    path = tmp_path / "queue.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE gateway_requests(request_id TEXT PRIMARY KEY,request_kind TEXT,payload_json TEXT,state TEXT,accepted_at_utc TEXT,managed_agent_instance_epoch INTEGER)"
        )
        connection.execute(
            "CREATE TABLE gateway_mail_notifier(scope_key TEXT PRIMARY KEY,last_poll_at_utc TEXT,last_notification_at_utc TEXT,last_notified_digest TEXT,last_error TEXT)"
        )

    def attempt(index: int) -> bool:
        """Compete for one due cycle without an in-process scheduler lock."""
        return admit_mail_reminder(
            path,
            scope_key="owner-offline",
            cycle_key="60:1",
            origin=ReminderOrigin("owner", "offline", "binding", "revision"),
            request_id=f"request-{index}",
            payload_json=json.dumps({"prompt": "work"}),
            accepted_at_utc="2026-11-14T00:01:00Z",
            managed_agent_instance_epoch=0,
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        assert sum(executor.map(attempt, range(4))) == 1
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM gateway_requests").fetchone()[0] == 1
        connection.execute(
            "CREATE TRIGGER fail_admission BEFORE INSERT ON mail_reminder_admission WHEN NEW.scope_key='other' BEGIN SELECT RAISE(ABORT, 'injected admission failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="injected admission failure"):
        admit_mail_reminder(
            path,
            scope_key="other",
            cycle_key="60:2",
            origin=ReminderOrigin("other", "offline", "binding", "revision"),
            request_id="failed",
            payload_json="{}",
            accepted_at_utc="now",
            managed_agent_instance_epoch=0,
        )
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM gateway_requests").fetchone()[0] == 1
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM mail_reminder_admission WHERE scope_key='other'"
            ).fetchone()[0]
            == 0
        )


def test_unchanged_mail_reminds_each_due_cycle_and_old_pending_scope_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No digest permanently suppresses work; old revisions cannot reach the body."""

    runtime = _runtime(tmp_path, monkeypatch, dual=False)
    _deliver_unread_mailbox_message(tmp_path)
    monkeypatch.setattr(runtime, "_notifier_block_detail_locked", lambda **kwargs: None)
    now = ["2026-11-14T00:01:01Z"]
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.now_utc_iso", lambda: now[0]
    )
    client = TestClient(create_app(runtime=runtime))
    assert client.put("/v1/mail-notifier/offline", json={"interval_seconds": 60}).status_code == 200
    runtime._run_notifier_cycle(channel="offline")
    runtime._run_notifier_cycle(channel="offline")
    with sqlite3.connect(runtime.m_paths.queue_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM gateway_requests").fetchone()[0] == 1
        connection.execute("UPDATE gateway_requests SET state='completed'")
    runtime._run_notifier_cycle(channel="offline")
    with sqlite3.connect(runtime.m_paths.queue_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM gateway_requests").fetchone()[0] == 1
    now[0] = "2026-11-14T00:02:01Z"
    runtime._run_notifier_cycle(channel="offline")
    payload = runtime._load_manifest_payload_for_mailbox_support()
    assert runtime.m_manifest_path is not None
    mutate_session_mailbox_binding(
        runtime.m_manifest_path,
        channel="offline",
        expected_revision=payload.launch_plan.mailboxes.offline.revision,
        binding=None,
        agent_id=payload.agent_id,
        session_id=payload.runtime.session_id,
    )
    assert runtime._take_next_request() is None
    with sqlite3.connect(runtime.m_paths.queue_path) as connection:
        states = [
            row[0]
            for row in connection.execute(
                "SELECT state FROM gateway_requests ORDER BY accepted_at_utc"
            )
        ]
    assert states == ["completed", "failed"]


def test_origin_storage_failure_refuses_dispatch_without_killing_fence_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unavailable local origin never authorizes a body effect."""

    from houmao.agents.realm_controller.errors import GatewayError

    runtime = _runtime(tmp_path, monkeypatch, dual=False)

    def unavailable(*args, **kwargs):
        """Inject a transient failure before an immutable origin can be read."""
        raise sqlite3.OperationalError("injected origin read failure")

    monkeypatch.setattr("houmao.mailbox.notifier_admission.reminder_origin", unavailable)
    assert not runtime._mail_reminder_origin_is_current("pending")
    with pytest.raises(GatewayError, match="storage is unavailable"):
        with runtime._mail_reminder_effect_lease("pending"):
            pytest.fail("Missing origin storage must refuse the body effect")


def test_online_credential_outage_preserves_enabled_notifier_and_recovers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An operational credential outage does not rewrite notifier configuration."""

    from houmao.agents.realm_controller.gateway_storage import read_gateway_mail_notifier_record
    from tests.unit.mailbox.fake_notifier_client import install_notifier_client

    runtime = _runtime(tmp_path, monkeypatch)
    install_notifier_client(monkeypatch)
    monkeypatch.setattr(runtime, "_notifier_block_detail_locked", lambda **kwargs: None)
    client = TestClient(create_app(runtime=runtime))
    assert client.put("/v1/mail-notifier/online", json={"interval_seconds": 60}).status_code == 200
    binding = runtime._load_mailbox_config(channel="online")
    assert binding.credential_file is not None
    credential = binding.credential_file
    contents = credential.read_bytes()
    credential.unlink()
    runtime._run_notifier_cycle(channel="online")
    key = runtime._mail_notifier_scope_key("online")
    record = read_gateway_mail_notifier_record(runtime.m_paths.queue_path, scope_key=key)
    assert record.enabled and record.interval_seconds == 60 and record.last_error
    credential.write_bytes(contents)
    credential.chmod(0o600)
    runtime._run_notifier_cycle(channel="online")
    record = read_gateway_mail_notifier_record(runtime.m_paths.queue_path, scope_key=key)
    assert record.enabled and record.last_error is None and record.last_notification_at_utc
