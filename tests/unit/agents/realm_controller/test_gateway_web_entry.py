"""Verify gateway Web entry authority and single-use transitions over HTTP."""

from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

from houmao.agents.realm_controller import gateway_web_entry
from houmao.agents.realm_controller.backends.dsh_web import DshWebSession
from houmao.agents.realm_controller.gateway_models import GatewayWebExecutionIdentityV1
from houmao.agents.realm_controller.gateway_service import _NativeWebGatewayAdapter, create_app
from houmao.agents.realm_controller.gateway_web_entry import (
    WEB_ENTER_PATH,
    WEB_LOGIN_PATH,
    WEB_TICKET_PATH,
    WebEntryBinding,
)
from houmao.agents.realm_controller.owner_admission import OwnerAdmissionError
from houmao.gateway.access import (
    CHALLENGE_HEADER,
    SIGNATURE_HEADER,
    GatewayChallengeRequest,
    GatewayRequestBinding,
    load_gateway_signer,
    sign_sshsig,
    sshsig_header,
)
from houmao.gateway._web_login import WEB_LOGIN_NAMESPACE, WEB_LOGIN_PROOF_MAX_BYTES
from houmao.gateway.authorization_models import (
    AuthorizationActor,
    Credential,
    Principal,
    ScopedGrant,
)
from houmao.gateway.operations import WEB_ENTRY
from houmao.gateway.deployment import GatewayDeployment
from houmao.gateway.owner_authority import BACKING_HEADER, RELAY_HEADER, issue_gateway_relay
from tests.fixtures.gateway_access import (
    FixtureGatewayAccess,
    FixtureProofAuth,
    enroll_fixture_admin,
    fixture_admin_key,
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
    return key, path, FixtureProofAuth(path, purpose="caller")


def _no_disclosure(response, *secrets: str) -> None:
    """Assert neither the result nor its headers reflect private request data."""

    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "location" not in response.headers
    for secret in secrets:
        assert secret not in response.text
        assert secret not in str(response.headers)


def _ticket(client: TestClient, auth: FixtureProofAuth | None = None) -> str:
    """Obtain a normal ticket with open admission or request-bound SSHSIG proof."""

    response = client.post(WEB_TICKET_PATH, auth=auth)
    assert response.status_code == 200, response.text
    assert set(response.json()) == {"url", "expires_at_utc"}
    _no_disclosure(response, "synthetic-native-secret")
    return response.json()["url"]


@pytest.fixture
def dashboard_entry(entry, monkeypatch: pytest.MonkeyPatch):
    """Supply verified public metadata and a native observation without a live host."""

    runtime, app, native, read_binding = entry
    identity = read_binding.return_value.execution
    manifest = SimpleNamespace(
        agent_name="Agent <example>",
        agent_id=identity.agent_id,
        registry_generation_id=identity.generation,
        mode="web",
        backend="dsh_web",
        working_directory="/private/example",
    )
    monkeypatch.setattr(runtime, "_verified_owner_manifest", Mock(return_value=manifest))
    monkeypatch.setattr(runtime, "status", Mock(side_effect=AssertionError("Status refresh ran")))
    backend = Mock(spec=DshWebSession)
    backend.observe_web_state_read_only.return_value = {
        "protocol_version": 1,
        "identity": identity.model_dump(),
        "available": True,
        "browser_workspace_id": "owned-workspace",
        "observed_at_utc": datetime.now(UTC).isoformat(),
        "admission": {"ready_only": False},
        "interaction_waits": ["approval"],
    }
    monkeypatch.setattr(runtime.m_adapter, "_browser_entry_backend", Mock(return_value=backend))
    return runtime, app, native, read_binding, manifest, backend


@pytest.mark.parametrize("keyed", [False, True])
def test_dashboard_web_link_follows_existing_admission(dashboard_entry, tmp_path, keyed):
    """Public HTML shows a busy Web agent and lets the live entry route select the flow."""

    runtime, app, native, _, _, backend = dashboard_entry
    client = _client(app)
    if keyed:
        _enroll(client, tmp_path)
    page = client.get("/")
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    _no_disclosure(page, _NATIVE, "synthetic-native-secret", "ticket=", "/private/example")
    assert "Agent &lt;example&gt;" in page.text
    assert "Agent <example>" not in page.text
    assert "<dd>dsh_web</dd>" in page.text
    assert "<dd>web</dd>" in page.text
    assert "<dd>Healthy</dd>" in page.text
    assert "<dd>Available</dd>" in page.text
    assert f'href="{WEB_ENTER_PATH}">Open agent Web UI</a>' in page.text
    backend.observe_web_state_read_only.assert_called_once()
    backend.observe_web_state.assert_not_called()
    backend.browser_entry.assert_not_called()
    native.assert_not_called()
    runtime.status.assert_not_called()

    opened = client.get(WEB_ENTER_PATH)
    if keyed:
        assert "start-login" in opened.text and opened.status_code == 200
        assert client.get("/v1/status").status_code == 401
        native.assert_not_called()
    else:
        assert opened.status_code == 302
        assert opened.headers["location"] == _LOCATION
        native.assert_called_once()


@pytest.mark.parametrize(
    ("mode", "backend"),
    [("headless", "claude_headless"), ("service", "kimi_acp"), ("tui", "local_interactive")],
)
def test_dashboard_non_web_shows_identity_without_entry(dashboard_entry, mode, backend):
    """Describe non-Web modes without querying a native Web surface."""

    _, app, _, _, manifest, observer = dashboard_entry
    manifest.mode, manifest.backend, manifest.agent_name = mode, backend, None
    page = _client(app).get("/")
    assert page.status_code == 200
    assert f"<dd>{manifest.agent_id}</dd>" in page.text
    assert f"<dd>{mode}</dd>" in page.text
    assert f"<dd>{backend}</dd>" in page.text
    assert "has no native Web interface" in page.text
    assert "Open agent Web UI" not in page.text
    observer.observe_web_state_read_only.assert_not_called()


@pytest.mark.parametrize(
    "condition", ["unavailable", "stale", "different", "workspace", "owner", "policy"]
)
def test_dashboard_reports_unavailable_entry(dashboard_entry, gateway_fixture_access, condition):
    """Unavailable authority or mismatched observations leave the public page readable."""

    runtime, app, native, _, _, backend = dashboard_entry
    state = backend.observe_web_state_read_only.return_value
    if condition == "unavailable":
        state["available"] = False
    elif condition == "stale":
        state["observed_at_utc"] = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    elif condition == "different":
        state["identity"]["host_incarnation"] = "replacement"
    elif condition == "workspace":
        state.pop("browser_workspace_id")
    elif condition == "owner":
        runtime._verified_owner_manifest.side_effect = OwnerAdmissionError("unavailable", "private")
    else:
        (gateway_fixture_access.private_root / "authorization.sqlite3").unlink()
    page = _client(app).get("/")
    assert page.status_code == 200
    assert "<dd>Healthy</dd>" in page.text
    assert "unavailable" in page.text
    assert "Open agent Web UI" not in page.text
    native.assert_not_called()


def test_dashboard_proxy_explains_owner_local_entry(dashboard_entry):
    """Proxy readers can see the summary but have no browser entry link."""

    _, app, native, _, _, _ = dashboard_entry
    page = _client(app).get("https://example.test/", headers={"X-Forwarded-Proto": "https"})
    assert page.status_code == 200
    assert "private TCP forward" in page.text
    assert "Open agent Web UI" not in page.text
    native.assert_not_called()


@pytest.mark.parametrize("change", ["enrollment", "native"])
def test_dashboard_link_rechecks_live_authority_on_click(dashboard_entry, tmp_path, change):
    """Viewing the page creates no grant that could outlive a later change."""

    _, app, native, _, _, _ = dashboard_entry
    client = _client(app)
    assert f'href="{WEB_ENTER_PATH}"' in client.get("/").text
    if change == "enrollment":
        _enroll(client, tmp_path)
        response = client.get(WEB_ENTER_PATH)
        assert response.status_code == 200 and "start-login" in response.text
        native.assert_not_called()
    else:
        native.side_effect = RuntimeError("stale native binding")
        response = client.get(WEB_ENTER_PATH)
        assert response.status_code == 409
        _no_disclosure(response, "stale native binding", "synthetic-native-secret")


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


@pytest.mark.parametrize(
    "location",
    [_LOCATION, f"{_NATIVE}/sessions/session#token=synthetic-native-secret"],
    ids=["dsh", "kimi"],
)
def test_bare_entry_redirects_anonymously(entry, location: str) -> None:
    """Open Web entry passes the verified provider destination to the browser."""

    _, app, native, read_binding = entry
    native.return_value = location

    response = _client(app).get(WEB_ENTER_PATH)

    assert response.status_code == 302
    assert response.headers["location"] == location
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.text == ""
    native.assert_called_once_with(read_binding.return_value)


@pytest.mark.parametrize(
    ("method", "path", "enrollment_status"),
    [("GET", WEB_ENTER_PATH, 410), ("POST", WEB_TICKET_PATH, 403)],
)
@pytest.mark.parametrize("change", ["enrollment", "replacement"])
def test_open_entry_rechecks_authority_after_native_lookup(
    entry, tmp_path: Path, change: str, method: str, path: str, enrollment_status: int
) -> None:
    """A changed roster or native binding withdraws the open destination."""

    _, app, native, read_binding = entry
    client = _client(app)

    def change_during_lookup(binding: WebEntryBinding) -> str:
        """Update live state after the owner has selected the Web execution."""

        if change == "enrollment":
            _enroll(_client(app), tmp_path)
        else:
            identity = binding.execution.model_copy(update={"host_incarnation": "new"})
            read_binding.return_value = replace(binding, execution=identity)
        return _LOCATION

    native.side_effect = change_during_lookup
    response = client.request(method, path)
    assert response.status_code == (enrollment_status if change == "enrollment" else 409)
    _no_disclosure(response, "synthetic-native-secret")
    native.assert_called_once()
    if change == "enrollment":
        page = client.get(WEB_ENTER_PATH)
        assert page.status_code == 200 and "start-login" in page.text
        native.assert_called_once()


def test_missing_policy_denies_entry(entry, gateway_fixture_access: FixtureGatewayAccess) -> None:
    """Loss of initialized state leaves both browser and ticket grants unavailable."""

    _, app, native, _ = entry
    client = _client(app)
    ticket = _ticket(client)
    (gateway_fixture_access.private_root / "authorization.sqlite3").unlink()
    for response in (
        client.get(WEB_ENTER_PATH),
        client.post(WEB_TICKET_PATH),
        client.get(ticket),
    ):
        assert response.status_code == 503
        assert response.json()["detail"]["error_code"] == "policy_unavailable"
        _no_disclosure(response, "synthetic-native-secret", ticket)
    native.assert_called_once()


def test_direct_ticket_admission_precedes_any_native_access(entry, tmp_path: Path) -> None:
    """Only an open unsigned request or a directly signed admin can issue a ticket."""

    runtime, app, native, _ = entry
    client = _client(app)
    denied = client.post(WEB_TICKET_PATH, content=b"untrusted-body")
    assert denied.status_code == 422
    _no_disclosure(denied, "untrusted-body")
    denied = client.post(WEB_TICKET_PATH, headers={CHALLENGE_HEADER: "malformed"})
    assert denied.status_code == 401
    assert denied.json()["detail"]["purposes"] == ["caller"]
    _no_disclosure(denied, "malformed")
    key, _, auth = _enroll(client, tmp_path)
    policy = runtime._require_access_policy()
    challenge = policy.issue(
        _ORIGIN,
        GatewayChallengeRequest(
            purpose="caller",
            key_id=runtime._access_self().key_id,
            request=GatewayRequestBinding.from_request("POST", WEB_TICKET_PATH, "", b""),
        ),
    )
    signer = load_gateway_signer(
        runtime.m_access_runtime.self_store.self_signer_path(challenge.target.incarnation)
    )
    self_proof = {
        CHALLENGE_HEADER: challenge.challenge_id,
        SIGNATURE_HEADER: sshsig_header(sign_sshsig(signer, challenge.signing_bytes())),
    }
    assert client.post(WEB_TICKET_PATH, headers=self_proof).status_code == 403
    for header in (RELAY_HEADER, BACKING_HEADER):
        assert client.post(WEB_TICKET_PATH, headers={header: "delegated"}).status_code == 403
    assert client.post(WEB_TICKET_PATH, headers={"Forwarded": "proto=http"}).status_code == 403
    native.assert_not_called()

    denied = client.post(WEB_TICKET_PATH)
    assert denied.status_code == 401
    assert denied.json()["detail"]["purposes"] == ["caller"]
    _no_disclosure(denied, "synthetic-native-secret")
    access = runtime.m_access_runtime
    policy = runtime._require_access_policy()
    key_entry = access.store.snapshot().find_credential(key.key_id)
    assert key_entry is not None
    grant = policy.authorize(AuthorizationActor.from_credential(key_entry), (WEB_ENTRY,))
    relay = issue_gateway_relay(
        access.private_root,
        grant=grant,
        request=GatewayRequestBinding.from_request("POST", WEB_TICKET_PATH, "", b""),
        receiver_id=policy.listener_id,
        permissions=(WEB_ENTRY,),
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


def test_scoped_web_caller_loses_unredeemed_ticket_when_grant_is_revoked(entry, tmp_path) -> None:
    """Allow an exact Web entry grant and retire the ticket without revoking its signer."""

    runtime, app, native, _ = entry
    client = _client(app)
    _enroll(client, tmp_path)
    scoped_key, scoped_signer = fixture_admin_key(tmp_path, "web-reviewer")
    store = runtime._require_access_policy().store
    principal = Principal(principal_id="reviewer", kind="operator", label="Reviewer")
    credential = Credential(principal_id=principal.principal_id, public_key=scoped_key.public_key)
    store.update(
        lambda state: state.model_copy(
            update={
                "principals": (*state.principals, principal),
                "credentials": (*state.credentials, credential),
            }
        ),
        actor="owner",
        action="test.web.enroll",
    )
    auth = FixtureProofAuth(scoped_signer)
    assert client.post(WEB_TICKET_PATH, auth=auth).status_code == 403
    native.assert_not_called()
    store.update(
        lambda state: state.model_copy(
            update={
                "grants": (ScopedGrant(principal_id=principal.principal_id, permission=WEB_ENTRY),),
            }
        ),
        actor="owner",
        action="test.web.grant",
    )
    ticket = _ticket(client, auth)
    store.update(
        lambda state: state.model_copy(update={"grants": ()}),
        actor="owner",
        action="test.web.revoke",
    )
    response = client.get(ticket)
    assert response.status_code == 410
    assert store.snapshot().find_credential(credential.key_id) is not None
    native.assert_called_once()
    _no_disclosure(response, "synthetic-native-secret", ticket)


def test_open_ticket_expires_in_one_minute_and_redeems_once(entry) -> None:
    """Open issuance keeps the regular ticket shape and one-time exchange."""

    _, app, native, _ = entry
    client = _client(app)
    before = datetime.now(UTC)
    issued = client.post(WEB_TICKET_PATH)
    after = datetime.now(UTC)

    assert issued.status_code == 200
    assert set(issued.json()) == {"url", "expires_at_utc"}
    _no_disclosure(issued, "synthetic-native-secret")
    expiry = datetime.fromisoformat(issued.json()["expires_at_utc"])
    assert before + timedelta(seconds=60) <= expiry <= after + timedelta(seconds=60)
    url = issued.json()["url"]
    assert client.get(url).headers["location"] == _LOCATION
    refused = client.get(url)
    assert refused.status_code == 410
    _no_disclosure(refused, "synthetic-native-secret", url)
    assert native.call_count == 2


@pytest.mark.parametrize("reopen", [False, True])
def test_anonymous_ticket_rejects_a_changed_roster(entry, tmp_path: Path, reopen: bool) -> None:
    """Anonymous tickets require the exact still-open revision at redemption."""

    _, app, native, _ = entry
    client = _client(app)
    ticket = _ticket(client)
    key, _, admin = _enroll(client, tmp_path)
    if reopen:
        assert client.delete(f"/v1/admin/keys/{key.key_id}", auth=admin).status_code == 204

    response = client.get(ticket)
    assert response.status_code == 410
    _no_disclosure(response, "synthetic-native-secret", ticket)
    native.assert_called_once()
    if reopen:
        assert client.get(_ticket(client)).status_code == 302


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


@pytest.mark.parametrize("signed", [False, True])
def test_issued_ticket_rechecks_lifetime_after_io(entry, tmp_path, monkeypatch, signed):
    """A response that finishes after the original deadline cannot redirect."""

    _, app, native, _ = entry
    clock = Mock(return_value=1000.0)
    monkeypatch.setattr(gateway_web_entry, "time", type("Clock", (), {"monotonic": clock}))
    client = _client(app)
    auth = _enroll(client, tmp_path)[2] if signed else None
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
        client.get(WEB_ENTER_PATH, headers={"X-Forwarded-Host": "fake-proxy"}),
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
    _, path, _ = _enroll(client, tmp_path)
    page = client.get(WEB_ENTER_PATH)
    assert page.status_code == 200
    assert "start-login" in page.text
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert "fixture-agent" in page.text
    _no_disclosure(page, "synthetic-native-secret")
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
    self_signer = runtime.m_access_runtime.self_store.self_signer_path(
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
