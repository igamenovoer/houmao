"""Exercise selected-agent policy, caller relay, and scoped backing admission."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import threading
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
import pytest

from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.agents.realm_controller.registry_models import RegistryGatewayV1
from houmao.agents.realm_controller.usage_models import UsagePage
from houmao.cao.rest_client import CaoApiError
from houmao.execution.context import observed_local_binding
from houmao.gateway.access import (
    CHALLENGE_HEADER,
    SIGNATURE_HEADER,
    GatewayAccessError,
    GatewayAccessPolicy,
    GatewayAccessStore,
    GatewayAdminKey,
    GatewayChallenge,
    GatewayChallengeRequest,
    GatewayClientBinding,
    GatewayOwner,
    GatewayRequestBinding,
    GatewayTarget,
    load_gateway_signer,
    public_key_text,
    sign_sshsig,
    sshsig_header,
)
from houmao.gateway.authorization_models import AuthorizationDecision, Permission
from houmao.gateway.authorization_store import AuthorizationStore
from houmao.gateway.deployment import GatewayEndpointDescriptor
from houmao.gateway.operations import ADMIN_ADD, CORE_OPERATIONS, INTERRUPT, PROMPT, STATUS
from houmao.gateway.owner_authority import (
    BACKING_HEADER,
    RELAY_HEADER,
    PassiveBackingBinding,
    consume_gateway_relay,
    issue_gateway_relay,
    issue_passive_backing,
    provision_passive_backing,
)
from houmao.gateway.roster import remove_admin_key
from houmao.passive_server.admission import CURRENT_ADMISSION, PassiveAccessTarget
from houmao.passive_server.app import create_app
from houmao.passive_server.client import PassiveServerClient
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import DiscoveredAgent, _summary_from_record
from houmao.passive_server.models import PassiveAgentActionResponse
from houmao.passive_server.service import PassiveServerService
from houmao.server.managed_agents import ManagedHeadlessAuthorityRecord
from houmao.server.models import HoumaoManagedAgentGatewayInternalHeadlessPromptRequest
from tests.fixtures.gateway_access import enroll_fixture_caller
from tests.unit.passive_server.test_discovery import _make_record
from tests.unit.passive_server.test_headless_service import _FakeHeadlessBackendSession


@dataclass
class _Target:
    """Real roster and keys with a synthetic current execution body."""

    client: TestClient
    service: PassiveServerService
    policy: GatewayAccessPolicy
    receiver: GatewayAccessPolicy
    store: AuthorizationStore
    runtime: SimpleNamespace
    record: DiscoveredAgent
    tracked_ref: str

    @property
    def base(self) -> str:
        """Return the tracked direct target route prefix."""

        return f"/houmao/agents/{self.tracked_ref}"

    @property
    def admin_base(self) -> str:
        """Return the published target prefix used by live proxy routes."""

        return f"/houmao/agents/{self.runtime.target.owner.agent_id}"

    def sign(
        self,
        path: str,
        *,
        method: str = "GET",
        body: bytes = b"",
        admin: Ed25519PrivateKey | None = None,
    ) -> dict[str, str]:
        """Obtain the passive challenge over HTTP and sign its exact binding."""

        parsed = urlsplit(path)
        request = GatewayRequestBinding.from_request(method, parsed.path, parsed.query, body)
        signer = admin or load_gateway_signer(
            self.runtime.self_store.self_signer_path(self.runtime.target.incarnation)
        )
        source = GatewayChallengeRequest(
            purpose="caller", key_id=_admin_entry(signer).key_id, request=request
        )
        prefix = parsed.path.split("/")[0:4]
        response = self.client.post(
            "/".join(prefix) + "/auth/challenge", json=source.model_dump(mode="json")
        )
        assert response.status_code == 200, response.json()
        challenge = GatewayChallenge.model_validate_json(response.content)
        return {
            CHALLENGE_HEADER: challenge.challenge_id,
            SIGNATURE_HEADER: sshsig_header(sign_sshsig(signer, challenge.signing_bytes())),
        }


def _admin_entry(key: Ed25519PrivateKey) -> GatewayAdminKey:
    """Build the registered public identity corresponding to a fixture signer."""

    return GatewayAdminKey(principal="operator", public_key=public_key_text(key.public_key()))


def _enroll(target: _Target, signer: Ed25519PrivateKey) -> GatewayAdminKey:
    """Commit the first member through the shared proof and mutation code."""

    candidate = _admin_entry(signer)
    body = candidate.model_dump_json().encode()
    bound = GatewayRequestBinding.from_request("POST", "/v1/admin/keys", "", body)
    issuer = "http://127.0.0.1:43000"
    challenge = target.policy.issue(
        issuer, GatewayChallengeRequest(purpose="register", request=bound, proposed_key=candidate)
    )
    grant = target.policy.admit(
        (ADMIN_ADD,),
        issuer=issuer,
        request=bound,
        challenge_id=challenge.challenge_id,
        signature=sshsig_header(sign_sshsig(signer, challenge.signing_bytes())),
        registration=True,
    )
    return target.policy.add_key(grant, candidate)


@pytest.fixture
def target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _Target:
    """Create independently bound retained and live discovery evidence."""

    config = PassiveServerConfig(
        runtime_root=tmp_path / "runtime", registry_root=tmp_path / "registry"
    )
    project_root = tmp_path / "project"
    project_root.mkdir()
    execution = observed_local_binding(
        working_directory=project_root,
        runtime_root=config.runtime_root,
        registry_root=config.registry_root,
        tmux_socket=None,
    )
    service = PassiveServerService(config)
    manifest_path = config.runtime_root / "agent" / "manifest.json"
    record = _make_record(agent_id="protected-agent", agent_name="HOUMAO-protected")
    record.execution_binding = execution
    record.runtime.manifest_path = str(manifest_path)
    record.gateway = RegistryGatewayV1(
        host="127.0.0.1", port=43000, state_path="/owner/state.json", protocol_version="v1"
    )
    discovered = DiscoveredAgent(record=record, summary=_summary_from_record(record))
    service.m_discovery.index.replace({record.agent_id: discovered})
    tracked_ref = "tracked-protected"
    service.m_headless.m_store.ensure_directories()
    service.m_headless.m_store.write_authority(
        ManagedHeadlessAuthorityRecord(
            tracked_agent_id=tracked_ref,
            backend="codex_headless",
            tool="codex",
            agent_id=record.agent_id,
            agent_name=record.agent_name,
            manifest_path=str(manifest_path),
            session_root=str(manifest_path.parent),
            tmux_session_name="isolated-protected",
            agent_def_dir=str(project_root),
            created_at_utc="now",
            updated_at_utc="now",
        )
    )
    owner = GatewayOwner(agent_id=record.agent_id, context_id=execution.context_id)
    binding = GatewayTarget(owner=owner, incarnation=record.generation_id)
    root = tmp_path / "access"
    store = AuthorizationStore(root, owner)
    store.initialize()
    self_store = GatewayAccessStore.from_root(root, owner=owner)
    own_key = self_store.provision_self(binding.incarnation)
    runtime = SimpleNamespace(
        target=binding,
        private_root=root,
        store=store,
        self_store=self_store,
        execution_binding=execution,
        require_current=lambda: None,
        current_self=lambda: own_key,
    )
    policy = GatewayAccessPolicy(
        store=store,
        target=lambda: binding,
        current_self=lambda: own_key,
        listener_id=service.m_access_listener_id,
    )
    receiver = GatewayAccessPolicy(
        store=store,
        target=lambda: binding,
        current_self=lambda: own_key,
        listener_id="gateway-listener",
    )
    monkeypatch.setattr(
        GatewayClient,
        "describe_endpoint",
        lambda _: GatewayEndpointDescriptor(
            protocol="v1",
            target=binding,
            presence_id=receiver.listener_id,
            admin_mode=store.snapshot().admin_mode,
            advertised_url=None,
        ),
    )
    monkeypatch.setattr(
        "houmao.passive_server.service.gateway_access_for_manifest", lambda _: runtime
    )
    client = TestClient(create_app(service=service), base_url=config.api_base_url)
    return _Target(client, service, policy, receiver, store, runtime, discovered, tracked_ref)


def test_retained_policy_survives_missing_discovery_and_checks_before_validation(
    target: _Target, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retained direct authority protects lifecycle and turns even without discovery."""

    target.service.m_discovery.index.replace({})
    calls = []
    monkeypatch.setattr(
        target.service.m_headless,
        "turn_artifact_text",
        lambda *args: calls.append(args) or "artifact",
    )
    usage = UsagePage(runtime_session_id="fixture-runtime")
    monkeypatch.setattr(target.service.m_headless, "get_usage", lambda *_args, **_kwargs: usage)
    assert target.client.post(f"{target.base}/gateway/detach").status_code == 501
    assert target.client.get(f"{target.base}/usage").json() == usage.model_dump(mode="json")
    artifact = f"{target.base}/turns/one/artifacts/stdout"
    assert target.client.get(artifact).text == "artifact"
    signer = Ed25519PrivateKey.generate()
    _enroll(target, signer)
    rejected = target.client.post(f"{target.base}/turns", content=b"{broken")
    assert rejected.status_code == 401
    assert f"{target.base}/auth/challenge" in rejected.headers["WWW-Authenticate"]
    assert target.client.get(artifact).status_code == 401
    assert len(calls) == 1
    assert target.client.get(f"{target.base}/usage").status_code == 401
    assert target.client.get(artifact, headers=target.sign(artifact)).status_code == 403
    assert (
        target.client.get(artifact, headers=target.sign(artifact, admin=signer)).text == "artifact"
    )
    attach = f"{target.base}/gateway/attach"
    assert (
        target.client.post(
            attach, headers=target.sign(attach, method="POST", admin=signer)
        ).status_code
        == 501
    )


def test_missing_initialized_policy_remains_closed(target: _Target) -> None:
    """A known target with unavailable policy refuses unsigned protected calls."""

    target.service.m_discovery.index.replace({})
    documents = tuple(target.runtime.private_root.rglob("authorization.sqlite3"))
    assert len(documents) == 1
    documents[0].unlink()
    assert target.client.post(f"{target.base}/gateway/detach").status_code == 503
    assert target.client.get(f"{target.base}/usage").status_code == 503


def test_signed_proxy_relays_translated_operation_once(
    target: _Target, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The downstream request carries the admitted principal and transformed bytes."""

    signer = Ed25519PrivateKey.generate()
    _enroll(target, signer)
    received = []

    def receive(_client: GatewayClient, *, request_obj: object, method: str, url: str) -> bytes:
        parts = urlsplit(url)
        headers = {name.lower(): value for name, value in request_obj.header_items()}
        assert CHALLENGE_HEADER.lower() not in headers and SIGNATURE_HEADER.lower() not in headers
        assert b'"kind": "submit_prompt"' in request_obj.data
        binding = GatewayRequestBinding.from_request(
            method, parts.path, parts.query, request_obj.data
        )
        token = headers[RELAY_HEADER.lower()]
        grant = consume_gateway_relay(
            target.runtime.private_root,
            target=target.runtime.target,
            request=binding,
            token=token,
            policy=target.receiver,
            permissions=(PROMPT,),
        )
        received.append((binding, grant, token))
        return (
            b'{"request_id":"fixture-request","request_kind":"submit_prompt",'
            b'"state":"accepted","accepted_at_utc":"now","queue_depth":1,"managed_agent_instance_epoch":1}'
        )

    monkeypatch.setattr(GatewayClient, "_open_request", receive)
    path = f"{target.admin_base}/requests"
    body = b'{"prompt":"translated"}'
    proof = target.sign(path, method="POST", body=body, admin=signer)
    response = target.client.post(
        path, content=body, headers={**proof, "Content-Type": "application/json"}
    )
    assert response.status_code == 200, response.text
    assert len(received) == 1
    request, grant, token = received[0]
    assert request.path == "/v1/requests"
    assert grant.actor.key_id == _admin_entry(signer).key_id
    assert grant.basis == "admin"
    assert grant.listener_id == target.receiver.listener_id
    assert grant.permissions == (PROMPT,)
    with pytest.raises(GatewayAccessError, match="proof"):
        consume_gateway_relay(
            target.runtime.private_root,
            target=target.runtime.target,
            request=request,
            token=token,
            policy=target.receiver,
            permissions=(PROMPT,),
        )
    assert target.client.post(path, content=body, headers=proof).status_code == 401
    assert len(received) == 1


def test_private_proxy_preserves_anonymous_caller(
    target: _Target, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both ingresses use the empty roster without adding a credential."""

    def receive(_client: GatewayClient, *, request_obj: Request, method: str, url: str) -> bytes:
        parts = urlsplit(url)
        assert parts.path == "/v1/memory/memo"
        assert method == "GET"
        headers = {name.lower(): value for name, value in request_obj.header_items()}
        assert not headers.keys() & {
            CHALLENGE_HEADER.lower(),
            SIGNATURE_HEADER.lower(),
            BACKING_HEADER.lower(),
        }
        binding = GatewayRequestBinding.from_request(method, parts.path, parts.query, b"")
        grant = consume_gateway_relay(
            target.runtime.private_root,
            target=target.runtime.target,
            request=binding,
            token=headers[RELAY_HEADER.lower()],
            policy=target.receiver,
            permissions=CORE_OPERATIONS[method, parts.path].permissions(b""),
        )
        admission = CURRENT_ADMISSION.get()
        assert admission is not None and admission.grant is not None
        assert grant.actor.kind == "anonymous" and grant.basis == "open"
        assert grant.open_epoch == admission.grant.open_epoch
        return b'{"memo_file":"memo.md","content":"fixture memo"}'

    monkeypatch.setattr(GatewayClient, "_open_request", receive)
    response = target.client.get(f"{target.admin_base}/gateway/memory/memo")
    assert response.status_code == 200, response.text
    assert response.json()["content"] == "fixture memo"


@pytest.mark.parametrize("reopen", [False, True])
def test_anonymous_proxy_rechecks_open_epoch_at_gateway(
    target: _Target, monkeypatch: pytest.MonkeyPatch, reopen: bool
) -> None:
    """Closing open access retires prior anonymous relay evidence even if it reopens."""

    calls = []

    def receive(_client: GatewayClient, *, request_obj: Request, method: str, url: str) -> bytes:
        headers = {name.lower(): value for name, value in request_obj.header_items()}
        calls.append(method)
        enrolled = _enroll(target, Ed25519PrivateKey.generate())
        if reopen:
            target.store.update(
                lambda state: remove_admin_key(state, enrolled.key_id),
                actor="fixture-owner",
                action="admin.key.remove",
            )
        parts = urlsplit(url)
        binding = GatewayRequestBinding.from_request(
            method, parts.path, parts.query, request_obj.data or b""
        )
        try:
            consume_gateway_relay(
                target.runtime.private_root,
                target=target.runtime.target,
                request=binding,
                token=headers[RELAY_HEADER.lower()],
                policy=target.receiver,
                permissions=(PROMPT,),
            )
        except GatewayAccessError as exc:
            raise GatewayHttpError(
                method=method,
                url=url,
                status_code=exc.status_code,
                detail="untrusted upstream diagnostic",
            ) from None
        pytest.fail("Downstream admission accepted stale anonymous relay")

    monkeypatch.setattr(GatewayClient, "_open_request", receive)
    response = target.client.post(f"{target.admin_base}/requests", json={"prompt": "fixture"})
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"].endswith(f'{target.admin_base}/auth/challenge"')
    assert "untrusted" not in response.text
    assert calls == ["POST"]


@pytest.mark.parametrize(("action", "denied"), [(PROMPT, INTERRUPT), (INTERRUPT, PROMPT)])
def test_queue_proxy_distinguishes_prompt_and_interrupt_for_scoped_callers(
    target: _Target, monkeypatch: pytest.MonkeyPatch, action: Permission, denied: Permission
) -> None:
    """Both variants share one gateway route and apply their distinct effects."""

    _enroll(target, Ed25519PrivateKey.generate())
    signer = Ed25519PrivateKey.generate()
    key = _admin_entry(signer).model_copy(update={"principal": "scoped-peer"})
    enroll_fixture_caller(
        SimpleNamespace(m_access_runtime=target.runtime), key, permissions=(action,)
    )
    path = f"{target.admin_base}/gateway/requests"
    reached = []

    def receive(_client: GatewayClient, *, request_obj: Request, method: str, url: str) -> bytes:
        """Admit the downstream queue operation based on the received body."""

        parts = urlsplit(url)
        assert parts.path == "/v1/requests"
        headers = {name.lower(): value for name, value in request_obj.header_items()}
        body = request_obj.data or b""
        grant = consume_gateway_relay(
            target.runtime.private_root,
            target=target.runtime.target,
            request=GatewayRequestBinding.from_request(method, parts.path, parts.query, body),
            token=headers[RELAY_HEADER.lower()],
            policy=target.receiver,
            permissions=CORE_OPERATIONS[method, parts.path].permissions(body),
        )
        reached.append(grant.permissions)
        kind = "interrupt" if action == INTERRUPT else "submit_prompt"
        return (
            f'{{"request_id":"fixture-request","request_kind":"{kind}",'
            '"state":"accepted","accepted_at_utc":"now","queue_depth":1,"managed_agent_instance_epoch":1}'
        ).encode()

    def send(permission: Permission):
        """Prove the exact queue request for one prompt or interrupt."""

        body = (
            b'{"kind":"interrupt","payload":{}}'
            if permission == INTERRUPT
            else b'{"kind":"submit_prompt","payload":{"prompt":"fixture"}}'
        )
        proof = target.sign(path, method="POST", body=body, admin=signer)
        return target.client.post(
            path, content=body, headers={**proof, "Content-Type": "application/json"}
        )

    monkeypatch.setattr(GatewayClient, "_open_request", receive)
    assert send(denied).status_code == 403
    assert send(action).status_code == 200
    assert reached == [(action,)]


@pytest.mark.parametrize(
    ("method", "route", "effect"),
    [("GET", "/usage", "get_usage"), ("POST", "/stop", "stop_managed")],
)
def test_direct_anonymous_access_rechecks_roster_before_effect(
    target: _Target, monkeypatch: pytest.MonkeyPatch, method: str, route: str, effect: str
) -> None:
    """An open grant expires if the roster changes after ingress admission."""

    target.service.m_discovery.index.replace({})
    require_current = target.service.require_access_target_current

    def enroll_after_ingress(selected: PassiveAccessTarget) -> None:
        require_current(selected)
        if CURRENT_ADMISSION.get() is None:
            _enroll(target, Ed25519PrivateKey.generate())

    monkeypatch.setattr(target.service, "require_access_target_current", enroll_after_ingress)
    monkeypatch.setattr(
        target.service.m_headless,
        effect,
        lambda *_args, **_kwargs: pytest.fail("Stale anonymous grant reached the direct body"),
    )
    response = target.client.request(method, f"{target.base}{route}")
    assert response.status_code == 401, response.text
    assert response.headers["WWW-Authenticate"].endswith(f'{target.base}/auth/challenge"')


@pytest.mark.parametrize("role", ["self", "admin"])
def test_relay_rejects_ended_generation_or_reenrolled_key(target: _Target, role: str) -> None:
    """A consumed passive signature cannot survive retirement of its exact grant."""

    private = Ed25519PrivateKey.generate()
    key = _enroll(target, private) if role == "admin" else None
    if role == "self":
        _enroll(target, Ed25519PrivateKey.generate())
    request = GatewayRequestBinding.from_request("GET", "/v1/status", "", b"")
    issuer = target.service.m_config.api_base_url
    signer = (
        private
        if key
        else load_gateway_signer(
            target.runtime.self_store.self_signer_path(target.runtime.target.incarnation)
        )
    )
    challenge = target.policy.issue(
        issuer,
        GatewayChallengeRequest(
            purpose="caller", request=request, key_id=_admin_entry(signer).key_id
        ),
    )
    grant = target.policy.admit(
        (STATUS,),
        issuer=issuer,
        request=request,
        challenge_id=challenge.challenge_id,
        signature=sshsig_header(sign_sshsig(signer, challenge.signing_bytes())),
    )
    assert isinstance(grant, AuthorizationDecision)
    token = issue_gateway_relay(
        target.runtime.private_root,
        grant=grant,
        request=request,
        receiver_id=target.receiver.listener_id,
        permissions=(STATUS,),
    )
    if key is not None:
        target.store.update(
            lambda state: remove_admin_key(state, key.key_id),
            actor="fixture-owner",
            action="admin.key.remove",
        )
        _enroll(target, private)
    else:
        target.receiver.m_self = lambda: None
    with pytest.raises(GatewayAccessError) as refused:
        consume_gateway_relay(
            target.runtime.private_root,
            target=target.runtime.target,
            token=token,
            request=request,
            policy=target.receiver,
            permissions=(STATUS,),
        )
    assert refused.value.status_code == 401


@pytest.mark.parametrize("changed", ["listener", "path", "query", "body", "action"])
def test_relay_is_consumed_only_for_exact_gateway_receiver_and_request(
    target: _Target, changed: str
) -> None:
    """A replacement or altered request cannot consume one-use caller authority."""

    request = GatewayRequestBinding.from_request("POST", "/v1/requests", "", b"{}")
    grant = target.policy.admit(
        (PROMPT, INTERRUPT), issuer=target.service.m_config.api_base_url, request=request
    )
    assert isinstance(grant, AuthorizationDecision)
    token = issue_gateway_relay(
        target.runtime.private_root,
        grant=grant,
        request=request,
        receiver_id=target.receiver.listener_id,
        permissions=(PROMPT,),
    )
    receiver = target.receiver
    if changed == "listener":
        receiver = GatewayAccessPolicy(
            store=target.store,
            target=lambda: target.runtime.target,
            current_self=target.runtime.current_self,
            listener_id="replacement",
        )
    transformed = GatewayRequestBinding.from_request(
        "POST",
        "/v1/control/prompt" if changed == "path" else request.path,
        "changed=1" if changed == "query" else request.query,
        b"altered" if changed == "body" else b"{}",
    )
    with pytest.raises(GatewayAccessError) as refused:
        consume_gateway_relay(
            target.runtime.private_root,
            target=target.runtime.target,
            request=transformed,
            token=token,
            policy=receiver,
            permissions=(INTERRUPT if changed == "action" else PROMPT,),
        )
    assert refused.value.status_code == (403 if changed == "action" else 401)
    with pytest.raises(GatewayAccessError) as replay:
        consume_gateway_relay(
            target.runtime.private_root,
            target=target.runtime.target,
            request=request,
            token=token,
            policy=target.receiver,
            permissions=(PROMPT,),
        )
    assert replay.value.status_code == 401


def test_invalid_supplied_proof_denies_open_access_before_gateway(
    target: _Target, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit malformed caller proof has no unsigned retry."""

    def unexpected(*_args: object, **_kwargs: object) -> None:
        """A proof refusal must precede a gateway connection."""

        pytest.fail("Malformed proof reached the gateway")

    monkeypatch.setattr(GatewayClient, "describe_endpoint", unexpected)
    response = target.client.post(
        f"{target.admin_base}/requests",
        json={"prompt": "fixture"},
        headers={CHALLENGE_HEADER: "stale", SIGNATURE_HEADER: "invalid"},
    )
    assert response.status_code == 401


def test_backing_grant_is_independent_of_roster_and_scoped_to_backing_routes(
    target: _Target, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Enrollment leaves service backing valid and unrelated operations reject it."""

    calls = []
    monkeypatch.setattr(
        target.service.m_headless,
        "interrupt_managed",
        lambda ref: (
            calls.append(ref) or PassiveAgentActionResponse(agent_id=ref, detail="interrupted")
        ),
    )
    binding = PassiveBackingBinding(
        target=target.runtime.target,
        api_base_url=target.service.m_config.api_base_url,
        tracked_agent_id=target.tracked_ref,
    )
    provision_passive_backing(target.runtime.private_root, binding)
    path = f"{target.base}/gateway/internal/interrupt"
    request = GatewayRequestBinding.from_request("POST", path, "", b"")
    token = issue_passive_backing(target.runtime.private_root, binding=binding, request=request)
    assert target.client.post(path).status_code == 403
    assert (
        target.client.post(f"{target.base}/interrupt", headers={BACKING_HEADER: token}).status_code
        == 403
    )
    _enroll(target, Ed25519PrivateKey.generate())
    response = target.client.post(path, headers={BACKING_HEADER: token})
    assert response.status_code == 200
    assert calls == [target.tracked_ref]
    assert target.client.post(path, headers={BACKING_HEADER: token}).status_code == 401
    with pytest.raises(GatewayAccessError) as failure:
        issue_passive_backing(
            target.runtime.private_root,
            binding=binding,
            request=GatewayRequestBinding.from_request("POST", f"{target.base}/stop", "", b""),
        )
    assert failure.value.status_code == 403


def test_passive_typed_client_signs_only_selected_protected_requests(
    target: _Target,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The typed client validates ingress challenges before sending any signature."""

    signer = Ed25519PrivateKey.generate()
    _enroll(target, signer)
    key_path = tmp_path / "admin-signing-key"
    key_path.write_bytes(
        signer.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.OpenSSH,
            serialization.NoEncryption(),
        )
    )
    key_path.chmod(0o600)
    binding = GatewayClientBinding(
        base_url=target.service.m_config.api_base_url,
        owner=target.runtime.target.owner,
        purpose="caller",
        private_key_path=str(key_path),
    )
    monkeypatch.setattr(
        target.service.m_headless, "turn_artifact_text", lambda *_: "fixture artifact"
    )
    requests = []

    class _Ingress:
        """Send the exact urllib request to the real ASGI routes within the fixture."""

        def open(self, outgoing: object, *, timeout: float) -> BytesIO:
            headers = dict(outgoing.header_items())
            requests.append((outgoing.full_url, {name.lower() for name in headers}))
            response = target.client.request(
                outgoing.method, outgoing.full_url, headers=headers, content=outgoing.data
            )
            stream = BytesIO(response.content)
            if response.status_code >= 300:
                raise HTTPError(
                    outgoing.full_url,
                    response.status_code,
                    response.reason_phrase,
                    response.headers,
                    stream,
                )
            stream.status = response.status_code
            return stream

    def make_client(selected: GatewayClientBinding) -> PassiveServerClient:
        """Make the maintained Python client using the fixture-owned ingress."""

        client = PassiveServerClient(binding.base_url, binding=selected)
        assert client.m_signed_transport is not None
        client.m_signed_transport.m_opener = _Ingress()
        return client

    client = make_client(binding)
    assert client.list_managed_agents().agents
    assert SIGNATURE_HEADER.lower() not in requests[-1][1]
    assert (
        client.get_headless_turn_artifact_text(target.tracked_ref, "turn", artifact_name="stdout")
        == "fixture artifact"
    )
    assert requests[-2][0].endswith(f"{target.base}/auth/challenge")
    assert SIGNATURE_HEADER.lower() in requests[-1][1]
    foreign_owner = GatewayOwner(agent_id="another-agent", context_id=binding.owner.context_id)
    retargeted = make_client(binding.model_copy(update={"owner": foreign_owner}))
    length = len(requests)
    with pytest.raises(CaoApiError, match="endpoint differs from the binding"):
        retargeted.get_headless_turn_artifact_text(
            target.tracked_ref, "turn", artifact_name="stdout"
        )
    assert len(requests) == length + 1
    assert SIGNATURE_HEADER.lower() not in requests[-1][1]


def test_backing_dispatch_returns_after_confirmed_handoff(
    target: _Target, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valid service proof starts one fenced turn while completion stays asynchronous."""

    headless = target.service.m_headless
    authority = headless.access_authority(target.tracked_ref)
    assert authority is not None
    backend = _FakeHeadlessBackendSession()
    backend.m_dispatch_control = None
    backend._runner = SimpleNamespace(set_dispatch_control=lambda _: None)
    release = threading.Event()
    finished = threading.Event()

    def dispatch(prompt: str, *, turn_artifact_dir_name: str, **_kwargs: object) -> list:
        """Confirm the simulated process handoff and wait for the test to finish it."""

        assert prompt == "fixture handoff"
        assert backend.m_dispatch_control is not None
        backend.m_dispatch_control.confirm_handoff()
        assert release.wait(timeout=5)
        manifest = Path(authority.manifest_path)
        turn_dir = manifest.parent / f"{manifest.stem}.turn-artifacts" / turn_artifact_dir_name
        (turn_dir / "exitcode").write_text("0\n", encoding="utf-8")
        finished.set()
        return []

    handle = SimpleNamespace(
        authority=authority,
        turn_worker=None,
        controller=SimpleNamespace(backend_session=backend, send_prompt=dispatch),
    )
    headless.m_handles[target.tracked_ref] = handle
    monkeypatch.setattr(
        "houmao.passive_server.headless.gateway_access_for_manifest", lambda _: target.runtime
    )
    monkeypatch.setattr(headless, "access_body_is_live", lambda *args, **kwargs: True)
    monkeypatch.setattr(headless, "_reconcile_usage", lambda _: None)
    binding = PassiveBackingBinding(
        target=target.runtime.target,
        api_base_url=target.service.m_config.api_base_url,
        tracked_agent_id=target.tracked_ref,
    )
    provision_passive_backing(target.runtime.private_root, binding)
    route = f"{target.base}/gateway/internal/headless-prompt"
    body = (
        HoumaoManagedAgentGatewayInternalHeadlessPromptRequest(
            prompt="fixture handoff", turn_id="one-turn"
        )
        .model_dump_json()
        .encode()
    )
    proof = issue_passive_backing(
        target.runtime.private_root,
        binding=binding,
        request=GatewayRequestBinding.from_request("POST", route, "", body),
    )
    try:
        response = target.client.post(
            route, content=body, headers={BACKING_HEADER: proof, "Content-Type": "application/json"}
        )
        assert response.status_code == 200, response.text
        assert handle.turn_worker.is_alive()
        assert not finished.is_set()
        assert (
            target.client.post(route, content=body, headers={BACKING_HEADER: proof}).status_code
            == 401
        )
    finally:
        release.set()
        if handle.turn_worker is not None:
            handle.turn_worker.join(timeout=5)
    assert finished.is_set()
