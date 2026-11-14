"""Dual-channel gateway admission, status, and periodic reminder contracts."""

from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import threading

from fastapi.testclient import TestClient
import pytest

from houmao.agents.mailbox_runtime_models import StalwartMailboxResolvedConfig
from houmao.mailbox.stalwart import (
    runtime_stalwart_credential_path,
    materialize_stalwart_session_credential,
)
from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime, create_app
from houmao.agents.realm_controller.gateway_storage import (
    read_gateway_mail_notifier_record,
    read_gateway_notifier_audit_records,
    write_gateway_mail_notifier_record,
)
from houmao.agents.realm_controller.manifest import (
    default_manifest_path,
    load_session_manifest,
    mutate_session_mailbox_binding,
)
from tests.unit.agents.realm_controller.test_gateway_support import (
    _FakeCaoRestClient,
    _deliver_unread_mailbox_message,
    _sample_cao_plan_with_stalwart_mailbox,
    _seed_cao_gateway_root,
    _test_binding_id,
)


def _runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, dual: bool = True, enabled: bool = True
) -> GatewayServiceRuntime:
    """Prepare launch-owned slots and a fake body, without starting workers."""

    root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=enabled)
    if dual:
        manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
        payload = load_session_manifest(manifest_path).payload
        binding = _sample_cao_plan_with_stalwart_mailbox(tmp_path).mailboxes.online.binding
        assert isinstance(binding, StalwartMailboxResolvedConfig)
        credential = runtime_stalwart_credential_path(tmp_path, binding.credential_ref)
        credential.parent.mkdir(parents=True, exist_ok=True)
        credential.write_text(json.dumps({"password": "hermetic-fixture-password"}))
        credential.chmod(0o600)
        materialize_stalwart_session_credential(
            runtime_root=tmp_path,
            session_root=manifest_path.parent,
            credential_ref=binding.credential_ref,
        )
        mutate_session_mailbox_binding(
            manifest_path,
            channel="online",
            expected_revision=payload["launch_plan"]["mailboxes"]["online"]["revision"],
            binding=replace(binding, credential_file=credential),
            agent_id=payload["agent_id"],
            session_id="cao-rest-1",
        )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: _FakeCaoRestClient(base_url="http://localhost:9889"),
    )
    return GatewayServiceRuntime.from_gateway_root(gateway_root=root, host="127.0.0.1", port=43123)


def test_empty_summary_and_explicit_channel_binding_admission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime(tmp_path, monkeypatch, dual=False, enabled=False)
    client = TestClient(create_app(runtime=runtime))
    response = client.get("/v1/mail/status")
    assert response.status_code == 200
    assert response.json()["offline"] is None
    assert response.json()["online"] is None
    assert response.json()["canonical_mail_identity"] is None
    assert client.post("/v1/mail/list", json={}).status_code == 404
    assert client.post("/v1/mail/offline/list", json={}).status_code == 422
    assert client.post("/v1/mail/guess/list", json={"expected_binding_id": "x"}).status_code == 422


def test_online_outage_preserves_canonical_identity_and_offline_operations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime(tmp_path, monkeypatch)
    client = TestClient(create_app(runtime=runtime))
    binding = runtime._load_mailbox_config(channel="online")
    assert isinstance(binding, StalwartMailboxResolvedConfig)
    assert binding.credential_file is not None
    binding.credential_file.unlink()
    summary = client.get("/v1/mail/status").json()
    assert summary["canonical_mail_identity"]["channel"] == "online"
    assert summary["online"]["available"] is False
    assert summary["offline"]["available"] is True
    assert "post" in summary["offline"]["supported_operations"]
    assert "post" not in summary["online"]["supported_operations"]
    assert (
        client.post(
            "/v1/mail/offline/list",
            json={
                "expected_binding_id": summary["offline"]["binding_id"],
            },
        ).status_code
        == 200
    )


def test_fresh_send_conflict_has_no_backend_side_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime(tmp_path, monkeypatch)
    client = TestClient(create_app(runtime=runtime))
    before = list((tmp_path / "mailbox" / "messages").rglob("*.md"))
    response = client.post(
        "/v1/mail/offline/send",
        json={
            "expected_binding_id": "obsolete-registration",
            "to": ["HOUMAO-gpu@agents.localhost"],
            "subject": "must not send",
            "body_content": "body",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["error_code"] == "mail_binding_conflict"
    assert list((tmp_path / "mailbox" / "messages").rglob("*.md")) == before


def test_channels_keep_independent_configuration_and_periodic_reminders(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime(tmp_path, monkeypatch)
    _deliver_unread_mailbox_message(tmp_path)
    client = TestClient(create_app(runtime=runtime))

    from tests.unit.mailbox.fake_notifier_client import install_notifier_client

    install_notifier_client(monkeypatch)
    now = ["2026-11-14T00:01:01Z"]
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.now_utc_iso", lambda: now[0]
    )
    monkeypatch.setattr(runtime, "_notifier_block_detail_locked", lambda **kwargs: None)
    for channel, mode in (("offline", "any_inbox"), ("online", "unread_only")):
        result = client.put(
            f"/v1/mail-notifier/{channel}",
            json={
                "interval_seconds": 60,
                "mode": mode,
                "appendix_text": f"{channel} appendix",
            },
        )
        assert result.status_code == 200
    for index in range(2):
        now[0] = f"2026-11-14T00:0{index + 1}:01Z"
        for channel in ("offline", "online"):
            runtime._run_notifier_cycle(channel=channel)
            with sqlite3.connect(runtime.m_paths.queue_path) as connection:
                # Model a body finishing this round before the next eligible cycle.
                connection.execute("UPDATE gateway_requests SET state = 'completed'")
    audit = read_gateway_notifier_audit_records(runtime.m_paths.queue_path)
    for channel in ("offline", "online"):
        key = runtime._mail_notifier_scope_key(channel)
        assert (
            len([row for row in audit if row.scope_key == key and row.outcome == "enqueued"]) == 2
        )
    client.delete("/v1/mail-notifier/online")
    offline = client.get("/v1/mail-notifier/offline").json()
    online = client.get("/v1/mail-notifier/online").json()
    assert offline["enabled"] is True
    assert offline["mode"] == "any_inbox"
    assert offline["appendix_text"] == "offline appendix"
    assert online["enabled"] is False
    assert online["appendix_text"] == "online appendix"
    record = read_gateway_mail_notifier_record(
        runtime.m_paths.queue_path, scope_key=runtime._mail_notifier_scope_key("offline")
    )
    assert record.last_notification_at_utc is not None


def test_mail_network_io_does_not_hold_terminal_control_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime(tmp_path, monkeypatch)
    acquired = threading.Event()

    from tests.unit.mailbox.fake_notifier_client import (
        FakeNotifierJmapClient,
        install_notifier_client,
    )

    class FakeJmap(FakeNotifierJmapClient):
        def query_metadata_page(self, **kwargs):
            def acquire() -> None:
                with runtime.m_lock:
                    acquired.set()

            thread = threading.Thread(target=acquire)
            thread.start()
            assert acquired.wait(1)
            thread.join(1)
            return super().query_metadata_page(**kwargs)

    install_notifier_client(monkeypatch, FakeJmap)
    response = TestClient(create_app(runtime=runtime)).post(
        "/v1/mail/online/list",
        json={
            "expected_binding_id": _test_binding_id(tmp_path, "online"),
        },
    )
    assert response.status_code == 200
    assert acquired.is_set()


def test_online_canonical_change_preserves_offline_compaction_eligibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime(tmp_path, monkeypatch, dual=False)
    message_id = _deliver_unread_mailbox_message(tmp_path)
    adapter = runtime._mailbox_adapter_locked(channel="offline")
    reference = adapter.scope.encode(f"filesystem:{message_id}")
    key = runtime._mail_notifier_scope_key("offline")
    # Model a completed compaction in the current continuous eligibility stretch.
    write_gateway_mail_notifier_record(
        runtime.m_paths.queue_path,
        scope_key=key,
        enabled=True,
        interval_seconds=60,
        pre_notification_context_action="compact",
        compacted_eligible_message_refs=(reference,),
    )
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    payload = load_session_manifest(manifest_path).payload
    online = _sample_cao_plan_with_stalwart_mailbox(tmp_path).mailboxes.online.binding
    assert isinstance(online, StalwartMailboxResolvedConfig)
    mutate_session_mailbox_binding(
        manifest_path,
        channel="online",
        expected_revision=payload["launch_plan"]["mailboxes"]["online"]["revision"],
        binding=online,
        agent_id=payload["agent_id"],
        session_id="cao-rest-1",
    )
    assert runtime._mail_notifier_scope_key("offline") == key
    compact_calls: list[str] = []
    monkeypatch.setattr(
        runtime, "_dispatch_tui_compaction_only", lambda **kwargs: compact_calls.append("compact")
    )
    monkeypatch.setattr(runtime, "_notifier_block_detail_locked", lambda **kwargs: None)
    runtime._run_notifier_cycle(channel="offline")
    assert compact_calls == []
    record = read_gateway_mail_notifier_record(runtime.m_paths.queue_path, scope_key=key)
    assert record.compacted_eligible_message_refs == (reference,)
    assert record.last_notification_at_utc is not None
