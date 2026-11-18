"""Revision-pinned online gateway, proxy client, and operator CLI forwarding."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from click.testing import CliRunner

from houmao.agents.realm_controller.gateway_client import GatewayClient, GatewayEndpoint
from houmao.mailbox.online_binding import OnlineBindingService
from houmao.mailbox.online_models import (
    OnlineAttachRequest,
    OnlineBindingStatus,
    OnlineControlRequest,
)
from houmao.passive_server.client import PassiveServerClient
from houmao.server.client import HoumaoServerClient
from houmao.srv_ctrl.commands.main import cli
from tests.unit.agents.realm_controller.test_gateway_dual_mail import _runtime
from tests.unit.mailbox.test_online_binding import _source
from tests.fixtures.gateway_access import configure_fixture_gateway_access, gateway_fixture_client


def test_gateway_live_controls_require_revision_and_preserve_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        OnlineBindingService,
        "_validate",
        lambda self, config, timeout: SimpleNamespace(
            account_id="account-a", identity_id="identity-a"
        ),
    )
    configure_fixture_gateway_access(tmp_path, monkeypatch)
    runtime = _runtime(tmp_path, monkeypatch, dual=False, enabled=False)
    client = gateway_fixture_client(runtime)
    before = runtime._load_manifest_payload_for_mailbox_support()
    initial = client.get("/v1/mail/online/binding").json()
    assert initial["state"] == "absent"
    request = {
        "expected_revision": initial["revision"],
        "address": "alice@example.test",
        "login_identity": "normal-login",
        "credential_source_ref": str(_source(tmp_path)),
        "jmap_url": "http://127.0.0.1/.well-known/jmap",
    }
    response = client.put("/v1/mail/online/binding", json=request)
    assert response.status_code == 200, response.text
    attached = response.json()
    assert attached["committed"]
    assert client.put("/v1/mail/online/binding", json=request).status_code == 409
    assert client.get("/v1/mail/status").json()["canonical_mail_identity"] == {
        "channel": "online",
        "address": "alice@example.test",
    }
    refresh = client.post(
        "/v1/mail/online/binding/refresh", json={"expected_revision": attached["revision"]}
    )
    assert refresh.status_code == 200, refresh.text
    refreshed = refresh.json()
    reconnect = client.post(
        "/v1/mail/online/binding/reconnect", json={"expected_revision": refreshed["revision"]}
    )
    assert reconnect.status_code == 200
    assert reconnect.json()["revision"] == refreshed["revision"]
    detached = client.request(
        "DELETE", "/v1/mail/online/binding", json={"expected_revision": refreshed["revision"]}
    )
    assert detached.status_code == 200 and detached.json()["state"] == "absent"
    after = runtime._load_manifest_payload_for_mailbox_support()
    assert after.agent_id == before.agent_id and after.runtime == before.runtime
    assert after.backend_state == before.backend_state
    assert "credential" not in response.text and "password" not in response.text


@pytest.mark.parametrize("client_class", [HoumaoServerClient, PassiveServerClient])
def test_pair_clients_preserve_control_body_and_escape_target(
    client_class: type[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    client = client_class("http://127.0.0.1:9889")
    seen: list[tuple[str, str, Any]] = []

    def request(method: str, path: str, model: Any, **kwargs: Any) -> OnlineBindingStatus:
        """Capture protected references without opening the selected source."""
        seen.append((method, path, kwargs.get("json_body")))
        return OnlineBindingStatus(agent_id="a", revision="r", state="absent")

    monkeypatch.setattr(client, "_request_root_model", request)
    control = OnlineControlRequest(expected_revision="r")
    client.get_managed_agent_online_binding("name/with space")
    client.refresh_managed_agent_online_binding("name/with space", control)
    client.reconnect_managed_agent_online_binding("name/with space", control)
    client.detach_managed_agent_online_binding("name/with space", control)
    assert seen[0][:2] == ("GET", "/houmao/agents/name%2Fwith%20space/mail/online/binding")
    assert [row[0] for row in seen] == ["GET", "POST", "POST", "DELETE"]
    assert seen[1][2]["expected_revision"] == "r"


def test_gateway_client_uses_strict_typed_body(monkeypatch: pytest.MonkeyPatch) -> None:
    client = GatewayClient(endpoint=GatewayEndpoint(host="127.0.0.1", port=43123))
    seen: dict[str, Any] = {}

    def request(method: str, path: str, model: Any, **kwargs: Any) -> OnlineBindingStatus:
        """Capture one transport request for its exact scope."""
        seen.update(method=method, path=path, **kwargs)
        return OnlineBindingStatus(agent_id="a", revision="r", state="absent")

    monkeypatch.setattr(client, "_request_model", request)
    candidate = OnlineAttachRequest(
        expected_revision="r",
        address="a@b.test",
        login_identity="login",
        credential_source_ref="/private/account.json",
        base_url="http://127.0.0.1",
    )
    client.attach_online_binding(candidate)
    assert seen["method"] == "PUT" and seen["path"] == "/v1/mail/online/binding"
    assert seen["body"] == candidate.model_dump(mode="json")


@pytest.mark.parametrize("operation", ["status", "attach", "refresh", "reconnect", "detach"])
def test_scoped_online_cli_forwards_pinned_control(
    operation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from houmao.srv_ctrl.commands import managed_agents

    seen: dict[str, Any] = {}
    target = object()
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.mailbox.resolve_managed_agent_target",
        lambda **kwargs: target,
    )
    status = OnlineBindingStatus(agent_id="a", revision="observed-revision", state="absent")
    monkeypatch.setattr(managed_agents, "online_mailbox_status", lambda actual: status)

    def control(actual: Any, action: str, request: Any) -> OnlineBindingStatus:
        """Record the exact operator precondition sent to the gateway."""
        assert actual is target
        seen.update(action=action, request=request)
        return status

    monkeypatch.setattr(managed_agents, "control_online_mailbox", control)
    args = ["agents", "single", "--agent-id", "a", "mailbox", "online", operation]
    if operation == "attach":
        args += [
            "--address",
            "a@b.test",
            "--login-identity",
            "login",
            "--credential-source",
            "/private/account.json",
            "--base-url",
            "http://127.0.0.1",
        ]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    if operation != "status":
        assert seen["request"].expected_revision == "observed-revision"
        assert seen["action"] == operation


def test_gateway_preserves_uncertain_send_receipt_in_old_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from houmao.mailbox.online_authority import OnlineConnectionAuthority
    from houmao.mailbox.stalwart import StalwartMutationError

    monkeypatch.setattr(
        OnlineBindingService,
        "_validate",
        lambda self, config, timeout: SimpleNamespace(
            account_id="account-a", identity_id="identity-a"
        ),
    )
    calls: list[str] = []

    class Client:
        """Model a provider acknowledgement that was lost after draft creation."""

        def send(self, **kwargs: Any) -> Any:
            """Expose uncertainty without automatically submitting again."""
            calls.append("send")
            raise StalwartMutationError(operation="send", outcome="uncertain", email_id="old-draft")

    monkeypatch.setattr(OnlineConnectionAuthority, "_client", lambda *args: Client())
    configure_fixture_gateway_access(tmp_path, monkeypatch)
    runtime = _runtime(tmp_path, monkeypatch, dual=False, enabled=False)
    client = gateway_fixture_client(runtime)
    initial = client.get("/v1/mail/online/binding").json()
    attached = client.put(
        "/v1/mail/online/binding",
        json={
            "expected_revision": initial["revision"],
            "address": "alice@example.test",
            "login_identity": "login",
            "credential_source_ref": str(_source(tmp_path)),
            "base_url": "http://127.0.0.1",
        },
    ).json()
    response = client.post(
        "/v1/mail/online/send",
        json={
            "schema_version": 3,
            "expected_binding_id": attached["binding_id"],
            "to": ["bob@example.test"],
            "subject": "hello",
            "body_content": "body",
        },
    )
    assert response.status_code == 502, response.text
    detail = response.json()["detail"]
    assert detail["outcome"] == "uncertain" and detail["email_id"] == "old-draft"
    assert detail["binding_id"] == attached["binding_id"]
    assert detail["revision"] == attached["revision"]
    assert calls == ["send"]
