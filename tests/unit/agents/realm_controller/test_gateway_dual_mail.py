"""Dual-channel gateway admission, status, and periodic reminder contracts."""

from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import threading

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
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
from houmao.gateway.access import public_key_text
from houmao.mailbox.policy import (
    GatewayMailPolicyRequest,
    MailPolicyReceipt,
    MailPolicyUpdate,
    SignedMailPolicyUpdate,
    apply_mail_policy,
    initialize_mail_policy,
    read_mail_policy_receipt,
    set_mail_policy_owner,
    sign_mail_policy_update,
)
from houmao.mailbox.stalwart_policy import StalwartPolicyConnector
from tests.fixtures.gateway_access import (
    FixtureProofAuth,
    enroll_fixture_admin,
    enroll_fixture_caller,
    fixture_admin_key,
    gateway_fixture_client,
)
from tests.unit.agents.realm_controller.test_gateway_support import (
    _FakeCaoRestClient,
    _deliver_unread_mailbox_message,
    _sample_cao_plan_with_stalwart_mailbox,
    _seed_cao_gateway_root,
    _test_binding_id,
)

pytestmark = pytest.mark.usefixtures("gateway_fixture_access")


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
    client = gateway_fixture_client(runtime)
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
    client = gateway_fixture_client(runtime)
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
    client = gateway_fixture_client(runtime)
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


def test_mail_policy_http_requires_gateway_admin_and_independent_owner_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise real gateway admission and the backend's separately trusted owner key."""

    runtime = _runtime(tmp_path, monkeypatch)
    client = TestClient(create_app(runtime=runtime), base_url=runtime.owner_connect_url)
    assert runtime.m_deployment is not None
    runtime.m_deployment = runtime.m_deployment.model_copy(
        update={"stalwart_policy_url": "https://policy.example.invalid"}
    )
    binding_id = runtime._load_mailbox_config(channel="online").binding_id
    backend_id = "test-mail-authority"
    policy_path = tmp_path / "mail-policy.sqlite"
    mailbox_owner = Ed25519PrivateKey.generate()
    foreign_signer = Ed25519PrivateKey.generate()
    with closing(sqlite3.connect(policy_path)) as db, db:
        initialize_mail_policy(db)
        set_mail_policy_owner(db, binding_id, public_key_text(mailbox_owner.public_key()))
    relayed: list[SignedMailPolicyUpdate] = []

    def apply(
        _connector: StalwartPolicyConnector, signed: SignedMailPolicyUpdate
    ) -> MailPolicyReceipt:
        """Apply exactly what the gateway relays inside the backend's writer fence."""

        relayed.append(signed)
        with closing(sqlite3.connect(policy_path)) as db, db:
            return apply_mail_policy(
                db, backend_id=backend_id, binding_id=binding_id, request=signed
            )

    monkeypatch.setattr(StalwartPolicyConnector, "apply", apply)
    path = "/v1/mail/online/policy/apply"
    update = MailPolicyUpdate(
        backend_id=backend_id,
        binding_id=binding_id,
        expected_revision=0,
        operation_id="rule-apply-first",
        blocked_senders=("blocked@example.test",),
    )

    def request_payload(
        signed: SignedMailPolicyUpdate, *, expected: str = binding_id
    ) -> dict[str, object]:
        """Build the public relay document with an independent binding pin."""

        return GatewayMailPolicyRequest(
            expected_binding_id=expected, signed_update=signed
        ).model_dump(mode="json")

    signed = sign_mail_policy_update(update, mailbox_owner)
    assert (
        client.post(path, json=request_payload(signed, expected="replacement")).status_code == 409
    )
    wrong_binding = sign_mail_policy_update(
        update.model_copy(update={"binding_id": "replacement"}), mailbox_owner
    )
    assert client.post(path, json=request_payload(wrong_binding)).status_code == 409
    assert relayed == []

    forged = sign_mail_policy_update(update, foreign_signer)
    rejected = client.post(path, json=request_payload(forged))
    assert rejected.status_code == 403
    assert rejected.json()["detail"]["error_code"] == "owner_authority_required"
    opened = client.post(path, json=request_payload(signed))
    assert opened.status_code == 200, opened.text
    assert MailPolicyReceipt.model_validate(opened.json()) == MailPolicyReceipt(
        status="applied", operation_id=update.operation_id, revision=1
    )
    assert relayed == [forged, signed]

    admin, admin_signer = fixture_admin_key(tmp_path, "relay-admin")
    enroll_fixture_admin(client, admin, admin_signer)
    caller, caller_signer = fixture_admin_key(tmp_path, "relay-requester")
    enroll_fixture_caller(runtime, caller, permissions=())
    second = sign_mail_policy_update(
        update.model_copy(update={"expected_revision": 1, "operation_id": "rule-apply-second"}),
        mailbox_owner,
    )
    assert client.post(path, json=request_payload(second)).status_code == 401
    assert (
        client.post(
            path, json=request_payload(second), auth=FixtureProofAuth(caller_signer)
        ).status_code
        == 403
    )
    assert relayed == [forged, signed]
    admin_auth = FixtureProofAuth(admin_signer)
    forged_second = sign_mail_policy_update(second.update, foreign_signer)
    rejected = client.post(path, json=request_payload(forged_second), auth=admin_auth)
    assert rejected.status_code == 403
    assert rejected.json()["detail"]["error_code"] == "owner_authority_required"
    keyed = client.post(path, json=request_payload(second), auth=admin_auth)
    assert keyed.status_code == 200, keyed.text
    assert keyed.json()["revision"] == 2
    assert relayed == [forged, signed, forged_second, second]
    with closing(sqlite3.connect(policy_path)) as db:
        committed = read_mail_policy_receipt(
            db, binding_id=binding_id, operation_id=second.update.operation_id
        )
    assert committed is not None
    assert committed == MailPolicyReceipt.model_validate(keyed.json())


@pytest.mark.parametrize(("mode", "action"), [("any_inbox", "archive"), ("unread_only", "read")])
def test_queued_mail_reminder_refuses_stale_inbox_before_native_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, action: str
) -> None:
    """Make a queued Inbox sample ineligible and verify that no prompt reaches the body."""

    runtime = _runtime(tmp_path, monkeypatch, dual=False)
    message_id = _deliver_unread_mailbox_message(tmp_path)
    adapter = runtime._mailbox_adapter_locked(channel="offline")
    reference = adapter.scope.encode(f"filesystem:{message_id}")
    client = gateway_fixture_client(runtime)
    monkeypatch.setattr(runtime, "_notifier_block_detail_locked", lambda **kwargs: None)
    activated = client.put("/v1/mail-notifier/offline", json={"interval_seconds": 60, "mode": mode})
    assert activated.status_code == 200, activated.text
    runtime._run_notifier_cycle(channel="offline")
    queued = runtime._take_next_request()
    assert queued is not None and queued.request_kind == "mail_notifier_prompt"
    with runtime._mail_reminder_effect_lease(queued.request_id):
        pass

    body: dict[str, object] = {"expected_binding_id": adapter.scope.binding_id}
    body.update(
        {"message_refs": [reference]} if action == "archive" else {"message_ref": reference}
    )
    changed = client.post(f"/v1/mail/offline/{action}", json=body)
    assert changed.status_code == 200, changed.text
    submitted: list[object] = []
    monkeypatch.setattr(runtime, "_submit_prompt_via_adapter", lambda **kw: submitted.append(kw))
    runtime._execute_request(request_record=queued)
    assert submitted == []
    with closing(sqlite3.connect(runtime.m_paths.queue_path)) as db:
        state, error_detail = db.execute(
            "SELECT state, error_detail FROM gateway_requests WHERE request_id = ?",
            (queued.request_id,),
        ).fetchone()
    assert state == "failed"
    assert "Inbox sample changed before dispatch" in error_detail


def test_channels_keep_independent_configuration_and_periodic_reminders(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime(tmp_path, monkeypatch)
    _deliver_unread_mailbox_message(tmp_path)
    client = gateway_fixture_client(runtime)

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
    response = gateway_fixture_client(runtime).post(
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
