"""Tests for live gateway HTTP client behavior."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
import threading
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from houmao.ag_ui.models import AgUiEventPublishRequest
from houmao.agents.realm_controller import gateway_access_runtime
from houmao.agents.realm_controller.errors import GatewayHttpError, SessionManifestError
from houmao.agents.realm_controller.gateway_client import (
    GATEWAY_RESPECT_PROXY_ENV_VAR,
    GatewayClient,
    GatewayEndpoint,
    gateway_client_respects_proxy_env,
)
from houmao.gateway.access import (
    CHALLENGE_HEADER,
    SIGNATURE_HEADER,
    GatewayAccessError,
    GatewayAccessPolicy,
    GatewayChallengeRequest,
    GatewayClientBinding,
    GatewayGrant,
    GatewayLaunchSeed,
    GatewayOwner,
    GatewayRequestBinding,
    GatewayTarget,
)

from houmao.gateway.authorization_models import Permission, seed_snapshot
from houmao.gateway.authorization_store import AuthorizationStore
from houmao.gateway.file_edits.contracts import FileReadRequest, FileReadResponse
from houmao.gateway.operations import WEB_ENTRY, mailbox_resource
from houmao.gateway.terminal_entry_contracts import (
    GatewayTerminalEntryMode,
    TERMINAL_INTERACT_PATH,
    TERMINAL_VIEW_PATH,
)
from tests.fixtures.gateway_access import fixture_admin_key

_PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "http_proxy",
    "HTTPS_PROXY",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
)


class _HealthHandler(BaseHTTPRequestHandler):
    """Serve a minimal gateway health endpoint."""

    def do_GET(self) -> None:
        """Return the gateway health payload."""

        if self.path != "/health":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        payload = {"protocol_version": "v1", "status": "ok"}
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        """Suppress noisy test-server logs."""


@pytest.mark.parametrize(
    ("status", "body", "reason"),
    [
        (
            401,
            b'{"detail":{"error_code":"proof_required","challenge_path":"/v1/auth/challenge"}}',
            "proof_required",
        ),
        (
            403,
            b'{"detail":{"error_code":"insufficient_authority","message":"private-marker"}}',
            "insufficient_authority",
        ),
        (401, b'{"detail":{"error_code":"insufficient_authority"}}', None),
        (403, b'{"detail":{"error_code":"private-marker"}}', None),
        (403, b'{"detail":{"error_code":["private-marker"]}}', None),
        (
            403,
            b'{"detail":{"error_code":"insufficient_authority","error_code":"private-marker"}}',
            None,
        ),
        (403, b'{"detail":private-marker', None),
        (403, b'{"detail":{"error_code":"insufficient_authority"}}' + b" " * 65536, None),
    ],
)
def test_file_access_refusal_preserves_only_known_reason(
    monkeypatch: pytest.MonkeyPatch, status: int, body: bytes, reason: str | None
) -> None:
    """Keep an allowlisted access reason without rendering the remote error body."""

    def refuse(request: Request, *, timeout: float) -> None:
        """Refuse the exact file operation at the HTTP transport boundary."""

        raise HTTPError(request.full_url, status, "refused", {}, BytesIO(body))

    client = GatewayClient(base_url="http://127.0.0.1:43123", respect_proxy_env=False)
    monkeypatch.setattr(client.m_opener, "open", refuse)
    payload = FileReadRequest(
        target=GatewayTarget(
            owner=GatewayOwner(agent_id="agent", context_id="context"), incarnation="current"
        ),
        presence_id="current",
        mount_id="a" * 32,
        path="release-notes/SKILL.md",
    )
    with pytest.raises(GatewayHttpError) as caught:
        client.request_file_edit("read", payload, FileReadResponse)

    assert caught.value.status_code == status
    assert caught.value.error_code == reason
    assert caught.value.detail == "Gateway proof was refused."
    assert "private-marker" not in str(caught.value)


def test_gateway_client_refuses_redirects_and_retargeting() -> None:
    """Keep requests and signers on their original endpoints."""

    class Redirect(_HealthHandler):
        """Advertise a different valid route under the same test origin."""

        paths: list[str] = []

        def do_GET(self) -> None:
            self.paths.append(self.path)
            self.send_response(307)
            self.send_header("Location", "/redirected")
            self.end_headers()

    with ThreadingHTTPServer(("127.0.0.1", 0), Redirect) as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with pytest.raises(GatewayHttpError, match="redirects are refused") as caught:
                GatewayClient(base_url=f"{base}/selected").health()
            assert caught.value.status_code == 307
            assert Redirect.paths == ["/selected/health"]
            binding = GatewayClientBinding(
                base_url=f"{base}/selected",
                owner=GatewayOwner(agent_id="agent", context_id="context"),
                purpose="caller",
                private_key_path="/unused-private-signer",
            )
            with pytest.raises(ValueError, match="binding differs"):
                GatewayClient(base_url=f"{base}/replacement", binding=binding)
        finally:
            server.shutdown()
            worker.join(timeout=2)
    with pytest.raises(ValueError, match="literal loopback"):
        GatewayClient(base_url="http://gateway.example.org")


def test_client_signs_with_verified_sqlite_registration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Load the exact active owner registration and refuse another generation."""

    issuer = "http://127.0.0.1:43210"
    owner = GatewayOwner(agent_id="self-client", context_id="owner")
    target = GatewayTarget(owner=owner, incarnation="current")
    store = AuthorizationStore(tmp_path / "access", owner)
    store.initialize()
    registration = store.provision_self(target.incarnation)
    policy = GatewayAccessPolicy(
        store=store,
        target=lambda: target,
        current_self=lambda: store.load_self(target.incarnation),
        listener_id="current-listener",
    )
    expected_manifest = tmp_path / "manifest.json"

    def authority(manifest: Path) -> SimpleNamespace:
        """Select the actual fixture key from the owner store."""

        assert manifest == expected_manifest
        return SimpleNamespace(
            target=target,
            load_self_signer=lambda: (
                registration,
                store.load_self_signer(target.incarnation, expected=registration),
            ),
        )

    monkeypatch.setattr(gateway_access_runtime, "gateway_access_for_manifest", authority)
    binding = GatewayClientBinding(
        base_url=issuer,
        owner=owner,
        purpose="caller",
        managed_self_manifest_path=str(expected_manifest),
    )
    client = GatewayClient(
        binding=binding,
        target_incarnation=target.incarnation,
        target_presence_id=policy.listener_id,
    )

    def respond(*, request_obj: Request, method: str, url: str) -> bytes:
        """Issue real listener proof in process."""

        assert method == "POST" and url == f"{issuer}/v1/auth/challenge"
        challenge = policy.issue(
            issuer, GatewayChallengeRequest.model_validate_json(request_obj.data)
        )
        return challenge.model_dump_json().encode()

    monkeypatch.setattr(client, "_open_request", respond)
    proof = client.caller_proof_headers("GET", "/v1/status", b"")
    actor = policy.authenticate(
        issuer=issuer,
        request=GatewayRequestBinding.from_request("GET", "/v1/status", "", b""),
        challenge_id=proof[CHALLENGE_HEADER],
        signature=proof[SIGNATURE_HEADER],
    )
    assert actor.kind == "self"
    assert actor.key_id == registration.key_id
    assert actor.self_registration_revision == registration.registration_revision
    wrong = GatewayClient(
        binding=binding, target_incarnation="different", target_presence_id=policy.listener_id
    )
    with pytest.raises(GatewayHttpError, match="signer binding is unavailable"):
        wrong.caller_proof_headers("GET", "/v1/status", b"")


@pytest.mark.parametrize("backend", ["hermes_tui", "hermes_service"])
@pytest.mark.parametrize("named", [False, True])
def test_detached_hermes_gateway_self_mail_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend: str, named: bool
) -> None:
    """Sign and authorize mail against live daemon authority with a detached terminal."""

    port = 43210
    issuer = f"http://127.0.0.1:{port}"
    owner = GatewayOwner(agent_id="hermes-client", context_id="owner")
    target = GatewayTarget(owner=owner, incarnation="current")
    private_root = tmp_path / "access"
    store = AuthorizationStore(private_root, owner)
    store.initialize()
    registration = store.provision_self(target.incarnation)
    manifest = tmp_path / "manifest.json"
    execution = SimpleNamespace(registry_root=str(tmp_path / "registry"))
    access = gateway_access_runtime.GatewayRuntimeAccess(
        manifest_path=manifest,
        execution_binding=execution,
        target=target,
        private_root=private_root,
        store=store,
        uses_named_hermes_profile=named,
    )
    record = SimpleNamespace(
        identity=SimpleNamespace(backend=backend),
        lifecycle=SimpleNamespace(state="active"),
        generation_id=target.incarnation,
        runtime=SimpleNamespace(manifest_path=str(manifest)),
        execution_binding=execution,
        terminal=SimpleNamespace(current_session_name=None),
    )
    payload = object()
    live = True
    verified_path = manifest

    def daemon_authority(path: Path, selected: object) -> SimpleNamespace:
        """Represent the native verifier at the exact gateway proof boundary."""

        assert path == manifest and selected is payload
        if not live:
            raise SessionManifestError("Current Hermes daemon authority is unavailable.")
        return SimpleNamespace(gateway_root=tmp_path if named else None, fingerprint="b" * 64)

    from houmao.agents.realm_controller import self_manifest

    monkeypatch.setattr(gateway_access_runtime, "gateway_access_for_manifest", lambda _: access)
    monkeypatch.setattr(gateway_access_runtime, "load_gateway_deployment", lambda _: None)
    monkeypatch.setattr(
        gateway_access_runtime, "load_managed_agent_record_by_agent_id", lambda *_, **__: record
    )
    monkeypatch.setattr(gateway_access_runtime, "is_live_agent_record_fresh", lambda _: True)
    monkeypatch.setattr(gateway_access_runtime, "load_registry_mode_authority", lambda _: payload)
    monkeypatch.setattr(
        gateway_access_runtime, "require_live_hermes_daemon_authority", daemon_authority
    )
    monkeypatch.setattr(
        self_manifest,
        "resolve_self_manifest",
        lambda: SimpleNamespace(path=verified_path, record=record, native_authority="b" * 64),
    )
    operator, operator_generation = gateway_access_runtime.owner_gateway_client_binding(
        manifest, port=port, private=True
    )
    assert operator_generation == target.incarnation
    if named:
        assert operator is None
    else:
        assert operator is not None and operator.managed_self_manifest_path == str(manifest)
    binding, generation = gateway_access_runtime.owner_gateway_client_binding(
        manifest, port=port, private=True, prefer_self=True
    )
    assert binding is not None and binding.managed_self_manifest_path == str(manifest)
    policy = GatewayAccessPolicy(
        store=store, target=lambda: target, current_self=access.current_self, listener_id="mail"
    )
    client = GatewayClient(
        binding=binding, target_incarnation=generation, target_presence_id=policy.listener_id
    )
    path = "/v1/mail/offline/list"
    calls: list[str] = []
    permission = Permission(resource=mailbox_resource("offline", "binding"), action="mail.list")

    def respond(*, request_obj: Request, method: str, url: str) -> bytes:
        """Authenticate the request bytes and verify the managed-self grant."""

        assert method == "POST" and request_obj.data is not None
        calls.append(url)
        if url == f"{issuer}/v1/auth/challenge":
            request = GatewayChallengeRequest.model_validate_json(request_obj.data)
            return policy.issue(issuer, request).model_dump_json().encode()
        assert url == f"{issuer}{path}"
        actor = policy.authenticate(
            issuer=issuer,
            request=GatewayRequestBinding.from_request(method, path, "", request_obj.data),
            challenge_id=request_obj.get_header(CHALLENGE_HEADER.capitalize()),
            signature=request_obj.get_header(SIGNATURE_HEADER.capitalize()),
        )
        assert actor.kind == "self"
        assert policy.revalidate(policy.authorize(actor, [permission]))
        return b'{"messages":[]}'

    monkeypatch.setattr(client, "_open_request", respond)
    assert client.request_json("POST", path, body={}) == {"messages": []}
    assert calls == [f"{issuer}/v1/auth/challenge", f"{issuer}{path}"]

    if named:
        calls.clear()
        verified_path = tmp_path / "sibling" / "manifest.json"
        with pytest.raises(GatewayHttpError, match="Gateway signer binding is unavailable"):
            client.caller_proof_headers("POST", path, b"{}")
        assert calls == []
        verified_path = manifest

    proof = client.caller_proof_headers("POST", path, b"{}")
    live = False
    with pytest.raises(GatewayAccessError):
        policy.authenticate(
            issuer=issuer,
            request=GatewayRequestBinding.from_request("POST", path, "", b"{}"),
            challenge_id=proof[CHALLENGE_HEADER],
            signature=proof[SIGNATURE_HEADER],
        )
    calls.clear()
    with pytest.raises(GatewayHttpError, match="signer binding is unavailable"):
        client.request_json("POST", path, body={})
    assert calls == []

    live = True
    proof = client.caller_proof_headers("POST", path, b"{}")
    with store.transaction() as transaction:
        transaction.replace_self(
            target.incarnation,
            expected_revision=registration.registration_revision,
            signer=None,
            actor="owner",
        )
    with pytest.raises(GatewayAccessError):
        policy.authenticate(
            issuer=issuer,
            request=GatewayRequestBinding.from_request("POST", path, "", b"{}"),
            challenge_id=proof[CHALLENGE_HEADER],
            signature=proof[SIGNATURE_HEADER],
        )
    calls.clear()
    with pytest.raises(SessionManifestError, match="signing authority is unavailable"):
        gateway_access_runtime.owner_gateway_client_binding(
            manifest, port=port, private=True, prefer_self=True
        )
    with pytest.raises(GatewayHttpError, match="signer binding is unavailable"):
        client.request_json("POST", path, body={})
    assert calls == []


@pytest.mark.parametrize("outcome", ["ticket", "redirect", "native_url", "refused"])
@pytest.mark.parametrize("signed", [False, True], ids=["open", "keyed"])
def test_web_entry_client_uses_selected_direct_authority_and_keeps_native_results_private(
    tmp_path: Path, outcome: str, signed: bool
) -> None:
    """Verify empty-body issuance and refuse redirects and native payloads."""

    admin, signer = fixture_admin_key(tmp_path, "web-entry-admin")
    owner = GatewayOwner(agent_id="web-agent", context_id="web-owner")
    target = GatewayTarget(owner=owner, incarnation="generation-web")
    store = AuthorizationStore(tmp_path / "access", owner)
    store.initialize(seed_snapshot(owner, GatewayLaunchSeed(admin_keys=(admin,) if signed else ())))
    policy = GatewayAccessPolicy(
        store=store, target=lambda: target, current_self=lambda: None, listener_id="web"
    )
    calls: list[tuple[str, str]] = []
    issued_url = ""
    expiry = "2026-11-20T12:00:00.012345+00:00"

    class EntryHandler(_HealthHandler):
        """Serve the expected ticket route and the challenge route for signed requests."""

        def do_GET(self) -> None:
            """Record any unexpected follow or fallback."""

            calls.append(("GET", self.path))
            self.send_error(404)

        def do_POST(self) -> None:
            """Check exact caller authority before returning the configured response."""

            calls.append(("POST", self.path))
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            expected_request = GatewayRequestBinding.from_request(
                "POST", "/v1/web/entry-ticket", "", b""
            )
            if self.path == "/v1/auth/challenge":
                assert signed
                challenge_request = GatewayChallengeRequest.model_validate_json(body)
                assert challenge_request.purpose == "caller"
                assert challenge_request.key_id == admin.key_id
                assert challenge_request.request == expected_request
                challenge = policy.issue(base, challenge_request)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(challenge.model_dump_json().encode())
                return
            assert self.path == "/v1/web/entry-ticket"
            assert body == b""
            if not signed:
                assert self.headers.get(CHALLENGE_HEADER) is None
                assert self.headers.get(SIGNATURE_HEADER) is None
            grant = policy.admit(
                (WEB_ENTRY,),
                issuer=base,
                request=expected_request,
                challenge_id=self.headers.get(CHALLENGE_HEADER),
                signature=self.headers.get(SIGNATURE_HEADER),
            )
            assert isinstance(grant, GatewayGrant)
            assert grant.basis == ("admin" if signed else "open")
            if outcome == "redirect":
                self.send_response(302)
                self.send_header("Location", issued_url)
                self.end_headers()
            elif outcome == "refused":
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b'{"detail":"native-secret"}')
            else:
                url = issued_url if outcome == "ticket" else f"{base}/?token=native-secret"
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"url": url, "expires_at_utc": expiry}).encode())

    with ThreadingHTTPServer(("127.0.0.1", 0), EntryHandler) as server:
        base = f"http://127.0.0.1:{server.server_port}"
        issued_url = f"{base}/v1/web/enter?ticket={'A' * 43}"
        binding = (
            GatewayClientBinding(
                base_url=base, owner=owner, purpose="caller", private_key_path=str(signer)
            )
            if signed
            else None
        )
        client = GatewayClient(
            base_url=base,
            binding=binding,
            target_incarnation=target.incarnation,
            target_presence_id="web",
            respect_proxy_env=False,
        )
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            if outcome == "ticket":
                ticket = client.issue_web_entry_ticket()
                assert ticket.model_dump(mode="json") == {
                    "url": issued_url,
                    "expires_at_utc": expiry,
                }
            else:
                with pytest.raises(GatewayHttpError) as denied:
                    client.issue_web_entry_ticket()
                expected = {
                    "redirect": "redirects are refused",
                    "native_url": "invalid Web entry ticket",
                    "refused": (
                        "currently enrolled admin signer"
                        if signed
                        else "Check its current access policy"
                    ),
                }[outcome]
                assert expected in denied.value.detail
                assert issued_url not in str(denied.value)
                assert "native-secret" not in str(denied.value)
            challenge_calls = [("POST", "/v1/auth/challenge")] if signed else []
            assert calls == [*challenge_calls, ("POST", "/v1/web/entry-ticket")]
        finally:
            server.shutdown()
            worker.join(timeout=2)


@pytest.mark.parametrize(
    ("base", "purpose", "proxy_env", "reason"),
    [
        ("http://127.0.0.1:43123", None, True, "direct owner-local gateway"),
        ("http://127.0.0.1:43123", "caller", True, "direct owner-local gateway"),
        ("http://127.0.0.1:43123/prefix", "caller", False, "direct owner-local gateway"),
        ("https://gateway.example/agents/web", "caller", False, "direct owner-local gateway"),
    ],
)
def test_web_entry_client_requires_direct_authority_before_contacting_gateway(
    base: str, purpose: str | None, proxy_env: bool, reason: str
) -> None:
    """Reject proxy-selected issuance before signer access."""

    binding = None
    if purpose is not None:
        binding = GatewayClientBinding.model_validate(
            {
                "base_url": base,
                "owner": {"agent_id": "web-agent", "context_id": "web-owner"},
                "purpose": purpose,
                "private_key_path": "/unused-private-signer",
            }
        )
    client = GatewayClient(base_url=base, binding=binding, respect_proxy_env=proxy_env)
    with pytest.raises(ValueError, match=reason):
        client.issue_web_entry_ticket()


def test_web_entry_client_refuses_a_delegated_proof_source() -> None:
    """Refuse to consult a relay proof source for Web entry."""

    def unexpected_proof(method: str, path: str, body: bytes) -> dict[str, str]:
        """Fail if Web ticket issuance asks for delegated authority."""

        pytest.fail("Web entry consulted a delegated proof source")

    client = GatewayClient(
        base_url="http://127.0.0.1:43123", request_proof=unexpected_proof, respect_proxy_env=False
    )
    with pytest.raises(ValueError, match="direct gateway caller"):
        client.issue_web_entry_ticket()


@pytest.mark.parametrize("outcome", ["ticket", "redirect", "wrong-mode", "wrong-origin", "refused"])
@pytest.mark.parametrize(
    ("mode", "signed"),
    [("view", False), ("interact", False), ("interact", True)],
    ids=["view", "open-interact", "keyed-interact"],
)
def test_terminal_entry_client_requests_the_exact_owner_local_ticket(
    tmp_path: Path, outcome: str, mode: GatewayTerminalEntryMode, signed: bool
) -> None:
    """Exercise direct viewing and both interactive proof modes against a live endpoint."""

    admin, signer = fixture_admin_key(tmp_path, "terminal-entry-admin")
    owner = GatewayOwner(agent_id="terminal-agent", context_id="terminal-owner")
    target = GatewayTarget(owner=owner, incarnation="terminal-generation")
    store = AuthorizationStore(tmp_path / "access", owner)
    roster = (admin,) if mode == "view" or signed else ()
    store.initialize(seed_snapshot(owner, GatewayLaunchSeed(admin_keys=roster)))
    policy = GatewayAccessPolicy(
        store=store, target=lambda: target, current_self=lambda: None, listener_id="terminal"
    )
    interactive = mode == "interact"
    entry_path = TERMINAL_INTERACT_PATH if interactive else TERMINAL_VIEW_PATH
    ticket_path = f"{entry_path}/ticket"
    calls: list[tuple[str, str]] = []
    expiry = "2026-11-20T12:00:00.012345Z"

    class EntryHandler(_HealthHandler):
        """Verify the empty-body terminal request using a real proof verifier."""

        def do_GET(self) -> None:
            """Record any follow or fallback from the ticket request."""

            calls.append(("GET", self.path))
            self.send_error(404)

        def do_POST(self) -> None:
            """Check the route and caller before returning the configured response."""

            calls.append(("POST", self.path))
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            expected = GatewayRequestBinding.from_request("POST", ticket_path, "", b"")
            if self.path == "/v1/auth/challenge":
                assert signed
                request = GatewayChallengeRequest.model_validate_json(body)
                assert request.purpose == "caller"
                assert request.key_id == admin.key_id
                assert request.request == expected
                challenge = policy.issue(base, request)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(challenge.model_dump_json().encode())
                return

            assert self.path == ticket_path
            assert body == b""
            caller = policy.authenticate(
                issuer=base,
                request=expected,
                challenge_id=self.headers.get(CHALLENGE_HEADER),
                signature=self.headers.get(SIGNATURE_HEADER),
            )
            assert caller.kind == ("credential" if signed else "anonymous")
            assert caller.key_id == (admin.key_id if signed else None)
            if outcome == "redirect":
                self.send_response(302)
                self.send_header("Location", issued_url)
                self.end_headers()
                return
            if outcome == "refused":
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b'{"detail":"private-terminal-marker"}')
                return
            document = {"url": issued_url, "expires_at_utc": expiry, "mode": mode}
            if outcome == "wrong-mode":
                document["mode"] = "view" if interactive else "interact"
            if outcome == "wrong-origin":
                document["url"] = (
                    f"http://localhost:{server.server_port}{entry_path}#ticket={'b' * 43}"
                )
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(document).encode())

    with ThreadingHTTPServer(("127.0.0.1", 0), EntryHandler) as server:
        base = f"http://127.0.0.1:{server.server_port}"
        issued_url = f"{base}{entry_path}#ticket={'b' * 43}"
        binding = (
            GatewayClientBinding(
                base_url=base, owner=owner, purpose="caller", private_key_path=str(signer)
            )
            if signed
            else None
        )
        client = GatewayClient(
            base_url=base,
            binding=binding,
            target_incarnation=target.incarnation,
            target_presence_id="terminal",
            respect_proxy_env=False,
        )
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            if outcome == "ticket":
                ticket = client.issue_terminal_entry_ticket(mode=mode)
                assert ticket.model_dump(mode="json") == {
                    "url": issued_url,
                    "expires_at_utc": expiry,
                    "mode": mode,
                }
            else:
                with pytest.raises(GatewayHttpError) as denied:
                    client.issue_terminal_entry_ticket(mode=mode)
                assert "#ticket=" not in str(denied.value)
                assert "private-terminal-marker" not in str(denied.value)
            challenge_calls = [("POST", "/v1/auth/challenge")] if signed else []
            assert calls == [*challenge_calls, ("POST", ticket_path)]
        finally:
            server.shutdown()
            worker.join(timeout=2)


@pytest.mark.parametrize(
    ("base_url", "proxy_env"),
    [("http://127.0.0.1:43123", True), ("https://gateway.example", False)],
)
def test_terminal_entry_client_refuses_proxy_and_remote_interaction(
    base_url: str, proxy_env: bool
) -> None:
    """Allow unsigned requests only on the direct numeric owner-local origin."""

    client = GatewayClient(base_url=base_url, respect_proxy_env=proxy_env)
    with pytest.raises(ValueError, match="direct owner-local gateway"):
        client.issue_terminal_entry_ticket(mode="interact")


def test_terminal_entry_client_refuses_relay_and_self_interaction() -> None:
    """Reject delegated or managed-self proof before dispatching the HTTP request."""

    base = "http://127.0.0.1:43123"

    def unexpected_proof(method: str, path: str, body: bytes) -> dict[str, str]:
        """Fail if terminal entry requests relay proof."""

        pytest.fail("Terminal entry consulted a delegated proof source")

    relay = GatewayClient(base_url=base, request_proof=unexpected_proof, respect_proxy_env=False)
    with pytest.raises(ValueError, match="direct owner-local gateway"):
        relay.issue_terminal_entry_ticket(mode="interact")
    binding = GatewayClientBinding(
        base_url=base,
        owner=GatewayOwner(agent_id="terminal-agent", context_id="terminal-owner"),
        purpose="caller",
        managed_self_manifest_path="/unused-runtime/manifest.json",
    )
    managed_self = GatewayClient(base_url=base, binding=binding, respect_proxy_env=False)
    with pytest.raises(ValueError, match="direct gateway caller signer"):
        managed_self.issue_terminal_entry_ticket(mode="interact")


class _ProxyHealthHandler(BaseHTTPRequestHandler):
    """Serve gateway health from an HTTP proxy test double."""

    paths: list[str] = []

    def do_GET(self) -> None:
        """Return a valid gateway health payload and capture the proxy request path."""

        self.__class__.paths.append(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        payload = {"protocol_version": "v1", "status": "ok"}
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        """Suppress noisy test-server logs."""


class _AgUiEventsHandler(BaseHTTPRequestHandler):
    """Capture one AG-UI publish request and return a valid response."""

    request_path: str | None = None
    request_payload: dict[str, object] | None = None

    def do_POST(self) -> None:
        """Capture the AG-UI publish request."""

        self.__class__.request_path = self.path
        length = int(self.headers.get("Content-Length", "0"))
        self.__class__.request_payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if self.path != "/v1/ag-ui/events":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        payload = {
            "status": "accepted",
            "acceptedCount": 1,
            "storedCount": 0,
            "deliveredCount": 0,
            "replay": "none",
            "threadId": "thread-1",
        }
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        """Suppress noisy test-server logs."""


def test_gateway_client_respects_proxy_env_only_for_one() -> None:
    """Gateway proxy handling is enabled only by the exact opt-in value."""

    assert gateway_client_respects_proxy_env({}) is False
    assert gateway_client_respects_proxy_env({GATEWAY_RESPECT_PROXY_ENV_VAR: ""}) is False
    assert gateway_client_respects_proxy_env({GATEWAY_RESPECT_PROXY_ENV_VAR: "true"}) is False
    assert gateway_client_respects_proxy_env({GATEWAY_RESPECT_PROXY_ENV_VAR: "1"}) is True


def test_gateway_client_bypasses_environment_proxy_for_loopback(
    monkeypatch,
) -> None:
    """Gateway health checks must connect directly to the loopback listener."""

    for key in _PROXY_ENV_KEYS:
        monkeypatch.setenv(key, "http://127.0.0.1:9")
    monkeypatch.delenv(GATEWAY_RESPECT_PROXY_ENV_VAR, raising=False)
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)

    server = ThreadingHTTPServer(("127.0.0.1", 0), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = GatewayClient(
            endpoint=GatewayEndpoint(host="127.0.0.1", port=server.server_port),
            timeout_seconds=0.5,
        )

        health = client.health()
    finally:
        server.shutdown()
        thread.join(timeout=2.0)
        server.server_close()

    assert health.status == "ok"
    assert health.protocol_version == "v1"
    assert os.environ.get("NO_PROXY") is None
    assert os.environ.get("no_proxy") is None


def test_gateway_client_proxy_opt_in_uses_environment_proxy(
    monkeypatch,
) -> None:
    """Gateway proxy opt-in uses normal proxy handling from the caller environment."""

    _ProxyHealthHandler.paths = []
    proxy = ThreadingHTTPServer(("127.0.0.1", 0), _ProxyHealthHandler)
    proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
    proxy_thread.start()
    proxy_url = f"http://127.0.0.1:{proxy.server_port}"
    for key in _PROXY_ENV_KEYS:
        monkeypatch.setenv(key, proxy_url)
    monkeypatch.setenv(GATEWAY_RESPECT_PROXY_ENV_VAR, "1")
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)

    try:
        client = GatewayClient(
            endpoint=GatewayEndpoint(host="127.0.0.1", port=9),
            timeout_seconds=0.5,
        )

        health = client.health()
    finally:
        proxy.shutdown()
        proxy_thread.join(timeout=2.0)
        proxy.server_close()

    assert health.status == "ok"
    assert health.protocol_version == "v1"
    assert _ProxyHealthHandler.paths == ["http://127.0.0.1:9/health"]


def test_gateway_client_posts_ag_ui_events_with_aliases() -> None:
    """Gateway AG-UI publish uses the live gateway route and camel-case JSON."""

    _AgUiEventsHandler.request_path = None
    _AgUiEventsHandler.request_payload = None
    server = ThreadingHTTPServer(("127.0.0.1", 0), _AgUiEventsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = GatewayClient(
            endpoint=GatewayEndpoint(host="127.0.0.1", port=server.server_port),
            timeout_seconds=0.5,
        )

        response = client.publish_ag_ui_events(
            AgUiEventPublishRequest(
                thread_id="thread-1",
                events=[
                    {
                        "type": "TEXT_MESSAGE_START",
                        "messageId": "message-1",
                        "role": "assistant",
                    }
                ],
            )
        )
    finally:
        server.shutdown()
        thread.join(timeout=2.0)
        server.server_close()

    assert response.status == "accepted"
    assert response.accepted_count == 1
    assert response.stored_count == 0
    assert response.delivered_count == 0
    assert response.replay == "none"
    assert _AgUiEventsHandler.request_path == "/v1/ag-ui/events"
    assert _AgUiEventsHandler.request_payload == {
        "threadId": "thread-1",
        "events": [
            {
                "type": "TEXT_MESSAGE_START",
                "messageId": "message-1",
                "role": "assistant",
            }
        ],
    }
