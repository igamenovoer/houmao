"""Verify gateway Web entry authority and single-use transitions over HTTP."""

from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

from houmao.agents.realm_controller import gateway_web_entry
from houmao.agents.realm_controller.gateway_models import GatewayWebExecutionIdentityV1
from houmao.agents.realm_controller.gateway_service import _NativeWebGatewayAdapter, create_app
from houmao.agents.realm_controller.gateway_web_entry import (
    WEB_ENTER_PATH,
    WEB_LOGIN_PATH,
    WEB_TICKET_PATH,
    WebEntryBinding,
)
from houmao.gateway.access import (
    GatewayGrant,
    GatewayRequestBinding,
    load_gateway_signer,
    sign_sshsig,
)
from houmao.gateway._web_login import WEB_LOGIN_NAMESPACE, WEB_LOGIN_PROOF_MAX_BYTES
from houmao.gateway.deployment import GatewayDeployment
from houmao.gateway.owner_authority import BACKING_HEADER, RELAY_HEADER, issue_gateway_relay
from tests.fixtures.gateway_access import (
    FixtureGatewayAccess,
    FixtureProofAuth,
    enroll_fixture_admin,
    fixture_admin_key,
    self_fixture_auth,
)
from tests.unit.agents.realm_controller.test_gateway_access_http import _runtime

_ORIGIN = "http://127.0.0.1:43123"
_NATIVE = "http://127.0.0.1:43124"
_LOCATION = f"{_NATIVE}/?token=synthetic-native-secret"
_LOOPBACK = ("127.0.0.1", 45000)


def _client(app: object, **kwargs: object) -> TestClient:
    """Use the real app with a controlled transport address."""

    return TestClient(app, base_url=_ORIGIN, client=_LOOPBACK, follow_redirects=False, **kwargs)


@pytest.fixture
def entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, gateway_fixture_access: FixtureGatewayAccess
):
    """Use the real access policy and runtime binding check with fake native I/O."""

    runtime = _runtime(tmp_path)
    target = gateway_fixture_access.target
    identity = GatewayWebExecutionIdentityV1(
        agent_id=target.owner.agent_id,
        runtime_session_id="runtime",
        generation=target.incarnation,
        host_incarnation="host",
        native_session_id="session",
        agent_incarnation="native-agent",
    )
    binding = WebEntryBinding(target, identity, _NATIVE)
    adapter = object.__new__(_NativeWebGatewayAdapter)
    monkeypatch.setattr(runtime, "m_adapter", adapter)
    native = Mock(return_value=_LOCATION)
    monkeypatch.setattr(adapter, "browser_entry_redirect", native)
    read_binding = Mock(return_value=binding)
    monkeypatch.setattr(runtime, "_web_entry_binding", read_binding)
    app = create_app(runtime=runtime)
    return runtime, app, native, read_binding


def _enroll(client: TestClient, tmp_path: Path) -> tuple[object, Path, FixtureProofAuth]:
    """Enroll a synthetic admin and select its proof for browser entry."""

    key, path = fixture_admin_key(tmp_path, "web-admin")
    enroll_fixture_admin(client, key, path)
    return key, path, FixtureProofAuth(path, purpose="admin")


def _no_disclosure(response, *secrets: str) -> None:
    """Assert neither the result nor its headers reflect private request data."""

    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "location" not in response.headers
    for secret in secrets:
        assert secret not in response.text
        assert secret not in str(response.headers)


def _ticket(client: TestClient, auth: FixtureProofAuth) -> str:
    """Obtain one normal ticket using request-bound SSHSIG proof."""

    response = client.post(WEB_TICKET_PATH, auth=auth)
    assert response.status_code == 200, response.text
    assert set(response.json()) == {"url", "expires_at_utc"}
    _no_disclosure(response, "synthetic-native-secret")
    return response.json()["url"]


def _start(client: TestClient) -> dict[str, str]:
    """Begin a login using the same-origin browser action."""

    response = client.post(WEB_LOGIN_PATH, headers={"Origin": _ORIGIN})
    assert response.status_code == 200, response.text
    return response.json()


def _login_proof(
    login: dict[str, str], path: Path, *, namespace: str = WEB_LOGIN_NAMESPACE
) -> bytes:
    """Sign the exact challenge with a synthetic private key."""

    message = base64.urlsafe_b64decode(login["challenge"] + "===")
    return sign_sshsig(load_gateway_signer(path), message, namespace=namespace)


def _approval(client: TestClient, login: dict[str, str], proof: bytes):
    """Submit a terminal outcome independently of the tab claim."""

    return client.post(f"{WEB_LOGIN_PATH}/{login['attempt_id']}/prove", content=proof)


def _claim(client: TestClient, login: dict[str, str], secret: str | None = None):
    """Poll using the originating tab's private claim header."""

    return client.post(
        f"{WEB_LOGIN_PATH}/{login['attempt_id']}/claim",
        headers={
            "Origin": _ORIGIN,
            "X-Houmao-Web-Claim": login["claim_secret"] if secret is None else secret,
        },
    )


def test_direct_admin_admission_precedes_any_native_access(entry, tmp_path: Path) -> None:
    """Open admin policy, self proof, and delegated authority grant no entry."""

    runtime, app, native, _ = entry
    client = _client(app)
    denied = client.post(WEB_TICKET_PATH, content=b"untrusted-body")
    assert denied.status_code == 401
    assert denied.json()["detail"]["purposes"] == ["admin"]
    _no_disclosure(denied, "untrusted-body")
    assert client.post(WEB_TICKET_PATH, auth=self_fixture_auth(runtime)).status_code == 403
    for header in (RELAY_HEADER, BACKING_HEADER):
        assert client.post(WEB_TICKET_PATH, headers={header: "delegated"}).status_code == 403
    native.assert_not_called()

    key, _, auth = _enroll(client, tmp_path)
    access = runtime.m_access_runtime
    state = access.store.load()
    relay = issue_gateway_relay(
        access.private_root,
        grant=GatewayGrant(
            role="admin",
            target=access.target,
            key_id=key.key_id,
            principal=key.principal,
            enrollment=state.find(key.key_id).enrollment,
            revision=state.revision,
        ),
        request=GatewayRequestBinding.from_request("POST", WEB_TICKET_PATH, "", b""),
    )
    refused = client.post(WEB_TICKET_PATH, headers={RELAY_HEADER: relay})
    assert refused.status_code == 403
    _no_disclosure(refused, relay)
    for supplied in ("?destination=caller-secret", "?ticket=caller-secret"):
        denied = client.post(WEB_TICKET_PATH + supplied, auth=auth)
        assert denied.status_code == 422
        _no_disclosure(denied, "caller-secret")
    denied = client.post(WEB_TICKET_PATH, auth=auth, json={"destination": "caller-secret"})
    assert denied.status_code == 422
    _no_disclosure(denied, "caller-secret")
    native.assert_not_called()
    _ticket(client, auth)
    native.assert_called_once()


@pytest.mark.parametrize("new_port", [43123, 43125])
def test_ticket_consumption_refuses_other_listener_and_racing_redemptions(
    entry, tmp_path, monkeypatch, new_port
):
    """Only one browser gets the native credential, even on concurrent GETs."""

    runtime, app, native, _ = entry
    client = _client(app)
    _, _, auth = _enroll(client, tmp_path)
    ticket = _ticket(client, auth)
    target = entry[3].return_value
    replacement = _runtime(tmp_path / "replacement")
    monkeypatch.setattr(replacement, "m_port", new_port)
    monkeypatch.setattr(replacement, "m_adapter", runtime.m_adapter)
    monkeypatch.setattr(replacement, "_web_entry_binding", lambda: target)
    restarted = TestClient(
        create_app(runtime=replacement), base_url=replacement.owner_connect_url, client=_LOOPBACK
    )
    issued_query = ticket.partition("?")[2]
    refused = restarted.get(f"{WEB_ENTER_PATH}?{issued_query}")
    assert refused.status_code == 410
    _no_disclosure(refused, ticket, "synthetic-native-secret")

    for suffix in ("&ticket=duplicate", "&url=caller-secret"):
        refused = client.get(ticket + suffix)
        assert refused.status_code == 410
        assert f'href="{WEB_ENTER_PATH}"' in refused.text
        _no_disclosure(refused, ticket, "duplicate", "caller-secret")
    slash_alias = client.get(f"{WEB_ENTER_PATH}/?{issued_query}")
    assert slash_alias.status_code == 404
    _no_disclosure(slash_alias, ticket, issued_query)

    with ThreadPoolExecutor(max_workers=2) as workers:
        responses = list(workers.map(lambda _: client.get(ticket), range(2)))
    assert sorted(response.status_code for response in responses) == [302, 410]
    redirect = next(response for response in responses if response.status_code == 302)
    assert redirect.headers["location"] == _LOCATION
    assert redirect.headers["referrer-policy"] == "no-referrer"
    assert native.call_count == 2


def test_native_entry_ignores_prompt_admission_and_refuses_unavailable_targets(
    entry, tmp_path, monkeypatch
):
    """Live browser entry neither admits a prompt nor recovers a stopped target."""

    runtime, app, native, _ = entry
    client = _client(app)
    admission = Mock(side_effect=AssertionError("Web entry called prompt admission"))
    monkeypatch.setattr(runtime, "_reserve_prompt", admission)
    lifecycle = Mock(side_effect=AssertionError("Web entry called lifecycle"))
    monkeypatch.setattr(runtime, "start", lifecycle)
    _, _, auth = _enroll(client, tmp_path)
    monkeypatch.setattr(runtime, "_active_execution_state", lambda: "running")
    ticket = _ticket(client, auth)
    assert client.get(ticket).status_code == 302
    native.side_effect = RuntimeError("native host stopped")
    assert client.post(WEB_TICKET_PATH, auth=auth).status_code == 409
    monkeypatch.setattr(runtime, "m_adapter", object())
    assert client.post(WEB_TICKET_PATH, auth=auth).status_code == 409
    assert client.post(WEB_LOGIN_PATH, headers={"Origin": _ORIGIN}).status_code == 409
    assert native.call_count == 3
    admission.assert_not_called()
    lifecycle.assert_not_called()


def test_issued_ticket_rechecks_lifetime_after_io(entry, tmp_path, monkeypatch):
    """A response that finishes after the original deadline cannot redirect."""

    _, app, native, _ = entry
    clock = Mock(return_value=1000.0)
    monkeypatch.setattr(gateway_web_entry, "time", type("Clock", (), {"monotonic": clock}))
    client = _client(app)
    _, _, auth = _enroll(client, tmp_path)
    ticket = _ticket(client, auth)

    def expires_during_io(_):
        clock.return_value = 1060.0
        return _LOCATION

    native.side_effect = expires_during_io
    assert client.get(ticket).status_code == 410
    assert client.get(ticket).status_code == 410
    assert native.call_count == 2


@pytest.mark.parametrize(
    "changes",
    [
        {"generation": "replacement"},
        {"host_incarnation": "replacement"},
        {"agent_incarnation": "replacement"},
    ],
)
def test_stale_web_binding_is_refused_before_native_io(entry, tmp_path, changes):
    """The same port or conversation ID never retargets an existing ticket."""

    _, app, native, read_binding = entry
    client = _client(app)
    _, _, auth = _enroll(client, tmp_path)
    ticket = _ticket(client, auth)
    old = read_binding.return_value
    read_binding.return_value = replace(old, execution=old.execution.model_copy(update=changes))
    refused = client.get(ticket)
    assert refused.status_code == 410
    _no_disclosure(refused, ticket, "synthetic-native-secret")
    native.assert_called_once()


def test_nonlocal_ingress_and_secret_failures_are_sanitized(entry, tmp_path, monkeypatch):
    """Advertised, forwarded, nonloopback and cross-origin paths reject entry."""

    runtime, app, native, _ = entry
    events = Mock(wraps=runtime.emit_diagnostic)
    monkeypatch.setattr(runtime, "emit_diagnostic", events)
    client = _client(app)
    _, _, auth = _enroll(client, tmp_path)
    ticket = _ticket(client, auth)
    monkeypatch.setattr(
        runtime,
        "m_deployment",
        GatewayDeployment(advertised_url="https://example.test/gateway", bind_host="127.0.0.1"),
    )
    for response in (
        client.get("https://example.test/v1/web/enter?ticket=advertised-secret"),
        client.post("https://example.test" + WEB_TICKET_PATH, auth=auth),
        client.get(ticket, headers={"X-Forwarded-Host": "fake-proxy"}),
        client.get(ticket, headers={"Forwarded": "proto=http"}),
        TestClient(app, base_url=_ORIGIN, client=("192.0.2.1", 45000)).get(ticket),
        client.post(WEB_LOGIN_PATH, headers={"Origin": "https://elsewhere.test"}),
        client.post(WEB_LOGIN_PATH),
    ):
        assert response.status_code == 403
        _no_disclosure(response, ticket, "advertised-secret")
    native.assert_called_once()
    native.side_effect = RuntimeError("provider-error-with-private-credential")
    refused = client.get(ticket)
    assert refused.status_code == 410
    _no_disclosure(refused, "provider-error-with-private-credential", ticket)
    report = client.get("/v1/endpoint").text + repr(events.call_args_list)
    diagnostic = runtime.m_paths.diagnostic_log_path
    if diagnostic.exists():
        report += diagnostic.read_text()
    for secret in (ticket, "advertised-secret", "provider-error-with-private-credential"):
        assert secret not in report


def test_interactive_login_binds_proof_and_tab_and_claims_once(entry, tmp_path):
    """Only an enrolled signature on this attempt can unblock its tab."""

    runtime, app, _, _ = entry
    client = _client(app)
    page = client.get(WEB_ENTER_PATH)
    assert page.status_code == 200
    assert "start-login" in page.text
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert "fixture-agent" in page.text
    _no_disclosure(page, "synthetic-native-secret")
    _, path, _ = _enroll(client, tmp_path)
    _, outsider = fixture_admin_key(tmp_path, "outsider")
    login = _start(client)
    challenge = json.loads(base64.urlsafe_b64decode(login["challenge"] + "==="))
    assert challenge["issuer"] == _ORIGIN
    assert challenge["path"] == f"{WEB_LOGIN_PATH}/{login['attempt_id']}/prove"
    assert challenge["purpose"] == WEB_LOGIN_NAMESPACE
    assert challenge["method"] == "POST"
    assert challenge["listener"] == runtime.m_presence_id
    assert challenge["execution"]["native_session_id"] == "session"
    assert login["claim_secret"] not in json.dumps(challenge)
    assert _claim(client, login).status_code == 202
    assert _claim(client, login, "a" * 43).status_code == 403
    assert _approval(client, login, b"x" * (WEB_LOGIN_PROOF_MAX_BYTES + 1)).status_code == 413
    assert (
        _approval(client, login, _login_proof(login, path, namespace="wrong-purpose")).status_code
        == 401
    )
    assert _approval(client, login, _login_proof(_start(client), path)).status_code == 401
    approve = _approval(client, login, _login_proof(login, outsider) + _login_proof(login, path))
    assert approve.json() == {"status": "approved"}
    assert approve.status_code == 200
    _no_disclosure(approve, login["claim_secret"], "synthetic-native-secret")
    assert _approval(client, login, _login_proof(login, path)).status_code == 410
    assert _claim(client, login, "b" * 43).status_code == 403
    with ThreadPoolExecutor(max_workers=2) as workers:
        claims = list(workers.map(lambda _: _claim(client, login), range(2)))
    assert sorted(response.status_code for response in claims) == [200, 410]
    result = next(response for response in claims if response.status_code == 200)
    _no_disclosure(result, login["claim_secret"], "synthetic-native-secret")
    assert client.get(result.json()["url"]).headers["location"] == _LOCATION


@pytest.mark.parametrize("cause", ["expiry", "revoked", "replacement"])
def test_interactive_login_revalidates_approval_and_ticket(entry, tmp_path, monkeypatch, cause):
    """Approval and subsequent tickets stop working after execution or authority changes."""

    _, app, native, read_binding = entry
    client = _client(app)
    key, path, auth = _enroll(client, tmp_path)
    clock = Mock(return_value=1000.0)
    monkeypatch.setattr(gateway_web_entry, "time", type("Clock", (), {"monotonic": clock}))
    login = _start(client)
    assert _approval(client, login, _login_proof(login, path)).status_code == 200
    ticket = _ticket(client, auth)
    if cause == "expiry":
        clock.return_value = 1120.0
    if cause == "revoked":
        assert client.delete(f"/v1/admin/keys/{key.key_id}", auth=auth).status_code == 204
        enroll_fixture_admin(client, key, path)
    if cause == "replacement":
        old = read_binding.return_value
        read_binding.return_value = replace(
            old, execution=old.execution.model_copy(update={"host_incarnation": "new"})
        )
    assert _claim(client, login).status_code == 410
    assert client.get(ticket).status_code == 410
    assert native.call_count == 3


def test_web_entry_store_has_bounded_capacity(entry, tmp_path, monkeypatch):
    """Bound both stores, prune expired entries and keep normal entry available."""

    _, app, _, _ = entry
    clock = Mock(return_value=1000.0)
    monkeypatch.setattr(gateway_web_entry, "time", type("Clock", (), {"monotonic": clock}))
    monkeypatch.setattr(gateway_web_entry, "_CAPACITY", 1)
    client = _client(app)
    _, _, auth = _enroll(client, tmp_path)
    _ticket(client, auth)
    login = _start(client)
    assert client.post(WEB_TICKET_PATH, auth=auth).status_code == 429
    assert client.post(WEB_LOGIN_PATH, headers={"Origin": _ORIGIN}).status_code == 429
    clock.return_value = 1120.0
    assert _claim(client, login).status_code == 410
    _ticket(client, auth)
    _start(client)


def test_new_listener_drops_pending_logins_and_refuses_delegated_proof(
    entry, tmp_path, monkeypatch
):
    """A pending challenge exists only in the gateway listener that issued it."""

    runtime, app, _, read_binding = entry
    client = _client(app)
    _, path, _ = _enroll(client, tmp_path)
    login = _start(client)
    proof = _login_proof(login, path)
    proof_path = f"{WEB_LOGIN_PATH}/{login['attempt_id']}/prove"
    self_signer = runtime._require_access_policy().store.self_signer_path(
        read_binding.return_value.target.incarnation
    )
    assert _approval(client, login, _login_proof(login, self_signer)).status_code == 401
    assert (
        client.post(proof_path, headers={RELAY_HEADER: "delegated"}, content=proof).status_code
        == 403
    )
    replacement = _runtime(tmp_path / "replacement")
    monkeypatch.setattr(replacement, "m_adapter", runtime.m_adapter)
    monkeypatch.setattr(replacement, "_web_entry_binding", read_binding)
    restarted = _client(create_app(runtime=replacement))
    assert _approval(restarted, login, proof).status_code == 410
    assert _claim(restarted, login).status_code == 410
    assert _approval(client, login, proof).status_code == 200
