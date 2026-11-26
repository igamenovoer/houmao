"""Online control validation, immutable credentials, and revision/epoch fences."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    mutate_session_mailbox_binding,
)
from houmao.mailbox.online_binding import OnlineBindingService
from houmao.mailbox.online_models import (
    OnlineAttachRequest,
    OnlineAuthorityContext,
    OnlineBindingError,
    OnlineControlRequest,
)
from houmao.mailbox.online_secrets import prepare_online_credential
from tests.unit.agents.realm_controller.test_mailbox_binding_authority import _manifest, _offline


def _source(root: Path, password: str = "fake-password") -> Path:
    """Write an explicitly selected owner-private hermetic credential source."""
    path = root / "account.json"
    path.write_text(json.dumps({"password": password}))
    path.chmod(0o600)
    return path


def _service(root: Path, monkeypatch: pytest.MonkeyPatch) -> OnlineBindingService:
    """Prepare a running-session authority without a network dependency."""
    path = _manifest(root)
    monkeypatch.setattr(
        OnlineBindingService,
        "_validate",
        lambda self, config, timeout: SimpleNamespace(
            account_id=config.account_id or "account-a",
            identity_id="identity-a",
            api_url=config.jmap_url,
        ),
    )
    return OnlineBindingService.from_context(OnlineAuthorityContext(path, "agent-a", "session-a"))


def _attach(service: OnlineBindingService, source: Path, **kwargs: Any) -> Any:
    """Attach one candidate at the latest explicitly observed revision."""
    return service.attach(
        OnlineAttachRequest(
            expected_revision=service.status().revision,
            address="alice@example.test",
            login_identity="different-login",
            credential_source_ref=str(source),
            jmap_url="http://127.0.0.1/.well-known/jmap",
            **kwargs,
        )
    )


def test_attach_refresh_reconnect_detach_preserve_offline_and_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(tmp_path, monkeypatch)
    context = service.m_authority.context
    original = load_session_manifest(context.manifest_path).payload
    mutate_session_mailbox_binding(
        context.manifest_path,
        channel="offline",
        expected_revision=original["launch_plan"]["mailboxes"]["offline"]["revision"],
        binding=_offline(tmp_path / "mail"),
        agent_id="agent-a",
        session_id="session-a",
    )
    offline = load_session_manifest(context.manifest_path).payload["launch_plan"]["mailboxes"][
        "offline"
    ]
    source = _source(tmp_path)
    attached = _attach(service, source)
    assert attached.committed and attached.available
    assert attached.account_id == "account-a"
    _, binding = service.m_authority.snapshot()
    assert binding is not None and binding.credential_file is not None
    first_copy = binding.credential_file
    assert first_copy != source and first_copy.stat().st_mode & 0o777 == 0o600
    source.write_text(json.dumps({"password": "new-fake-password"}))
    assert json.loads(first_copy.read_text())["password"] == "fake-password"
    refreshed = service.refresh(OnlineControlRequest(expected_revision=attached.revision))
    assert refreshed.binding_id == attached.binding_id
    assert refreshed.revision != attached.revision and refreshed.epoch_id != attached.epoch_id
    assert not first_copy.exists() and source.exists()
    reconnected = service.reconnect(OnlineControlRequest(expected_revision=refreshed.revision))
    assert reconnected.revision == refreshed.revision
    assert reconnected.epoch_id != refreshed.epoch_id
    detached = service.detach(OnlineControlRequest(expected_revision=reconnected.revision))
    assert detached.state == "absent" and detached.committed
    payload = load_session_manifest(context.manifest_path).payload
    assert payload["launch_plan"]["mailboxes"]["offline"] == offline
    assert payload["runtime"] == original["runtime"]
    assert source.exists()
    assert not list((tmp_path / "mailbox-secrets").glob("online-*.json"))
    assert "credential" not in attached.model_dump_json()


def test_rejected_candidate_and_wrong_revision_leave_current_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(tmp_path, monkeypatch)
    source = _source(tmp_path)
    first = _attach(service, source)
    before = load_session_manifest(service.m_authority.context.manifest_path).payload

    def reject(*args: Any, **kwargs: Any) -> Any:
        """Model a safe candidate timeout/authentication rejection."""
        raise OnlineBindingError("candidate_validation_failed", "Candidate rejected")

    monkeypatch.setattr(service, "_validate", reject)
    with pytest.raises(OnlineBindingError, match="Candidate rejected"):
        _attach(service, source)
    with pytest.raises(OnlineBindingError) as exc:
        service.detach(OnlineControlRequest(expected_revision="stale"))
    assert exc.value.code == "mail_binding_conflict"
    assert load_session_manifest(service.m_authority.context.manifest_path).payload == before
    assert service.status().binding_id == first.binding_id
    assert len(list((tmp_path / "mailbox-secrets").glob("online-*.json"))) == 1


def test_explicit_replacement_and_refresh_reject_account_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(tmp_path, monkeypatch)
    source = _source(tmp_path)
    first = _attach(service, source)
    with pytest.raises(OnlineBindingError) as exc:
        _attach(service, source, account_id="account-b")
    assert exc.value.code == "replacement_required"
    monkeypatch.setattr(
        service,
        "_validate",
        lambda config, timeout: SimpleNamespace(
            account_id="account-b", identity_id="identity-b", api_url=config.jmap_url
        ),
    )
    with pytest.raises(OnlineBindingError) as exc:
        service.refresh(OnlineControlRequest(expected_revision=first.revision))
    assert exc.value.code == "account_mismatch"
    replacement = _attach(service, source, account_id="account-b", replace=True)
    assert replacement.binding_id != first.binding_id
    assert replacement.account_id == "account-b"


def test_origin_policy_round_trip_and_scope_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from houmao.agents.mailbox_runtime_support import safe_registry_mailboxes_projection
    from houmao.mailbox.stalwart import StalwartConnectionPolicyError
    from tests.unit.mailbox.fake_notifier_client import (
        FakeNotifierJmapClient,
        install_notifier_client,
    )

    manifest = _manifest(tmp_path)
    service = OnlineBindingService.from_context(
        OnlineAuthorityContext(manifest, "agent-a", "session-a")
    )
    source = _source(tmp_path)
    advertised_origin = "http://api.example.com:10080"
    other_origin = "https://other.example.com"
    seen: list[dict[str, Any]] = []

    class Client(FakeNotifierJmapClient):
        """Report the selected API origin and observe connection reconstruction."""

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            seen.append(kwargs)
            if kwargs["api_origin"] is not None and kwargs["api_origin"] != advertised_origin:
                raise StalwartConnectionPolicyError("jmap_api_origin_changed", "API origin changed")

        def validate_binding(self, *, sender_address: str | None = None) -> Any:
            return replace(
                super().validate_binding(sender_address=sender_address),
                api_url=f"{advertised_origin}/api",
            )

    install_notifier_client(monkeypatch, Client)
    attached = _attach(
        service, source, trusted_jmap_origins=[advertised_origin + "/", other_origin]
    )
    assert attached.api_origin == advertised_origin
    assert attached.trusted_jmap_origins == [advertised_origin, other_origin]
    assert attached.warnings
    _, binding = service.m_authority.snapshot()
    assert binding is not None and binding.pinned_api_origin == advertised_origin
    mailboxes = load_session_manifest(manifest).payload["launch_plan"]["mailboxes"]
    from houmao.agents.mailbox_runtime_support import mailboxes_resolved_config_from_payload

    configs = mailboxes_resolved_config_from_payload(mailboxes, manifest_path=manifest)
    projection = safe_registry_mailboxes_projection(configs)
    assert "origins" not in json.dumps(projection)
    assert advertised_origin not in json.dumps(projection)

    older = mailboxes["online"]["binding"]
    del older["trusted_jmap_origins"], older["api_origin"]
    legacy = mailboxes_resolved_config_from_payload(mailboxes).online.binding
    assert legacy is not None and legacy.trusted_jmap_origins == ()
    assert legacy.pinned_api_origin == "http://127.0.0.1"

    changed = _attach(
        service,
        source,
        trusted_jmap_origins=[advertised_origin, other_origin, "https://upload.example.com"],
    )
    assert changed.binding_id == attached.binding_id and changed.revision != attached.revision
    refreshed = service.refresh(OnlineControlRequest(expected_revision=changed.revision))
    reconnected = service.reconnect(OnlineControlRequest(expected_revision=refreshed.revision))
    assert reconnected.binding_id == attached.binding_id
    assert reconnected.trusted_jmap_origins == changed.trusted_jmap_origins
    assert attached.binding_id is not None
    service.m_authority.capture_connection(expected_binding_id=attached.binding_id)
    assert seen[-1]["allowed_api_origins"] == tuple(changed.trusted_jmap_origins)
    assert seen[-1]["api_origin"] == advertised_origin

    advertised_origin = other_origin
    with pytest.raises(OnlineBindingError, match="API origin changed"):
        service.reconnect(OnlineControlRequest(expected_revision=reconnected.revision))
    assert service.status().binding_id == attached.binding_id
    with pytest.raises(OnlineBindingError, match="--replace"):
        _attach(service, source, trusted_jmap_origins=[other_origin])
    replacement = _attach(service, source, replace=True, trusted_jmap_origins=[other_origin])
    assert replacement.binding_id != attached.binding_id and replacement.api_origin == other_origin


def test_late_observation_is_discarded_after_refresh_or_reconnect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(tmp_path, monkeypatch)
    first = _attach(service, _source(tmp_path))
    authority = service.m_authority
    monkeypatch.setattr(authority, "_client", lambda *args: object())
    captured = authority.capture_connection(expected_binding_id=str(first.binding_id))
    calls: list[str] = []
    assert authority.commit_observation(captured.fence, lambda: calls.append("current"))
    service.reconnect(OnlineControlRequest(expected_revision=first.revision))
    assert not authority.commit_observation(captured.fence, lambda: calls.append("stale"))
    assert calls == ["current"]


def test_first_validated_adoption_pins_legacy_binding_and_copies_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(tmp_path, monkeypatch)
    first = _attach(service, _source(tmp_path))
    slot, binding = service.m_authority.snapshot()
    assert binding is not None
    legacy = replace(binding, account_id=None, identity_id=None)
    mutate_session_mailbox_binding(
        service.m_authority.context.manifest_path,
        channel="online",
        expected_revision=slot.revision,
        binding=legacy,
        agent_id="agent-a",
        session_id="session-a",
    )
    service.adopt(expected_binding_id=str(first.binding_id), timeout_seconds=1)
    _, adopted = service.m_authority.snapshot()
    assert adopted is not None and adopted.account_id == "account-a"
    assert adopted.binding_id == legacy.binding_id
    assert adopted.credential_ref != legacy.credential_ref


def test_private_source_validation_and_request_contract(tmp_path: Path) -> None:
    source = _source(tmp_path)
    source.chmod(0o644)
    with pytest.raises(OnlineBindingError, match="owner-private"):
        prepare_online_credential(source, session_root=tmp_path)
    assert source.exists()
    with pytest.raises(ValidationError):
        OnlineAttachRequest(
            expected_revision="r",
            address="a@b.test",
            login_identity="a",
            credential_source_ref=str(source),
        )
    with pytest.raises(ValidationError):
        OnlineAttachRequest(
            expected_revision="r",
            address="a@b.test",
            login_identity="a",
            credential_source_ref=str(source),
            base_url="http://localhost",
            jmap_url="http://localhost/jmap",
        )


def test_post_commit_projection_failure_reports_confirmed_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(tmp_path, monkeypatch)
    source = _source(tmp_path)
    before = service.status()

    def fail() -> None:
        """Interrupt derived epoch publication after durable CAS."""
        raise OSError("disk failure")

    monkeypatch.setattr(service.m_authority, "advance_epoch", fail)
    result = _attach(service, source)
    assert result.committed and result.revision != before.revision
    assert result.warnings
    assert service.status().binding_id == result.binding_id


def test_started_mutation_outcome_stays_pinned_without_retry(tmp_path: Path) -> None:
    from houmao.mailbox.errors import GatewayMailboxMutationError
    from houmao.mailbox.services import StalwartGatewayMailboxAdapter
    from houmao.mailbox.stalwart import StalwartMutationError
    from tests.unit.agents.realm_controller.test_mailbox_binding_authority import _online

    class Client:
        """Model one provider timeout after it may have accepted the submission."""

        def __init__(self) -> None:
            self.m_calls = 0

        def send(self, **kwargs: Any) -> Any:
            """A timeout creates reconciliation information rather than another send."""
            self.m_calls += 1
            raise StalwartMutationError(operation="send", outcome="uncertain", email_id="draft-a")

    client = Client()
    binding = _online()
    adapter = StalwartGatewayMailboxAdapter(binding, client)  # type: ignore[arg-type]
    with pytest.raises(GatewayMailboxMutationError) as exc:
        adapter.send(
            to_addresses=["bob@example.test"],
            cc_addresses=[],
            subject="hello",
            body_content="body",
            attachments=[],
        )
    assert client.m_calls == 1
    assert exc.value.safe_payload() == {
        "error_code": "mail_mutation_outcome",
        "detail": str(exc.value),
        "operation": "send",
        "outcome": "uncertain",
        "email_id": "draft-a",
        "submission_id": None,
        "agent_id": binding.agent_id,
        "binding_id": binding.binding_id,
        "revision": binding.bindings_version,
    }


def test_confirmed_mutation_receipt_survives_normalization(tmp_path: Path) -> None:
    from houmao.mailbox.services import StalwartGatewayMailboxAdapter
    from tests.unit.agents.realm_controller.test_mailbox_binding_authority import _online

    class Client:
        """Return a known provider acknowledgement and lightweight metadata."""

        def send(self, **kwargs: Any) -> dict[str, Any]:
            """A successful submit exposes both reconciliation identifiers."""
            return {
                "id": "sent-a",
                "receivedAt": "2026-11-14T00:00:00Z",
                "subject": "hello",
                "mutation_receipt": {
                    "operation": "send",
                    "outcome": "confirmed",
                    "email_id": "sent-a",
                    "submission_id": "submission-a",
                },
            }

    binding = _online()
    adapter = StalwartGatewayMailboxAdapter(binding, Client())  # type: ignore[arg-type]
    message = adapter.send(
        to_addresses=["bob@example.test"],
        cc_addresses=[],
        subject="hello",
        body_content="body",
        attachments=[],
    )
    assert message.mutation_receipt is not None
    assert message.mutation_receipt.outcome == "confirmed"
    assert message.mutation_receipt.binding_id == binding.binding_id
    assert message.mutation_receipt.revision == binding.bindings_version
    assert message.mutation_receipt.submission_id == "submission-a"


def test_competing_candidate_controls_have_one_cas_winner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from concurrent.futures import ThreadPoolExecutor
    import threading

    service = _service(tmp_path, monkeypatch)
    source = _source(tmp_path)
    barrier = threading.Barrier(2)

    def validate(config: Any, timeout: float) -> Any:
        """Make both candidates validate the same empty slot before either CAS."""
        barrier.wait(timeout=5)
        return SimpleNamespace(
            account_id="account-a", identity_id="identity-a", api_url=config.jmap_url
        )

    monkeypatch.setattr(service, "_validate", validate)

    def attach() -> str:
        """Record the outcome of one explicitly pinned competing control."""
        try:
            _attach(service, source)
            return "committed"
        except OnlineBindingError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attach), pool.submit(attach)]
        outcomes = [future.result(timeout=10) for future in futures]
    assert sorted(outcomes) == ["committed", "mail_binding_conflict"]
    assert len(list((tmp_path / "mailbox-secrets").glob("online-*.json"))) == 1


def test_closing_admission_rejects_new_requests_before_detach(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from concurrent.futures import ThreadPoolExecutor
    import threading
    import time

    service = _service(tmp_path, monkeypatch)
    attached = _attach(service, _source(tmp_path))
    authority = service.m_authority
    monkeypatch.setattr(authority, "_client", lambda *args: object())
    ready, release = threading.Event(), threading.Event()

    def operation() -> None:
        """Remain admitted while a controller closes future admission."""
        with authority.operation(expected_binding_id=str(attached.binding_id)):
            ready.set()
            assert release.wait(5)

    with ThreadPoolExecutor(max_workers=2) as pool:
        in_flight = pool.submit(operation)
        assert ready.wait(5)
        detach = pool.submit(
            service.detach,
            OnlineControlRequest(expected_revision=attached.revision, timeout_seconds=2.0),
        )
        deadline = time.monotonic() + 1
        while not authority.state().get("closing") and time.monotonic() < deadline:
            time.sleep(0.01)
        assert authority.state()["closing"] is True
        try:
            with pytest.raises(OnlineBindingError) as exc:
                with authority.operation(
                    expected_binding_id=str(attached.binding_id), timeout_seconds=0.2
                ):
                    pytest.fail("Retiring connections cannot admit new effects")
            assert exc.value.code == "online_retirement_busy"
        finally:
            release.set()
        in_flight.result(timeout=5)
        assert detach.result(timeout=5).state == "absent"
