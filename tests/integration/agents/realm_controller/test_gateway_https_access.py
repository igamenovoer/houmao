"""Qualify per-agent gateway access through a real, verified HTTPS reverse proxy."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import IPv4Address
import json
import os
from pathlib import Path
import shutil
from socket import socket as Socket
import ssl
import subprocess
import sys
import threading
from uuid import uuid4

from click.testing import CliRunner
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.x509.oid import NameOID
import httpx
import pytest
import uvicorn

from houmao.agents.realm_controller.run_modes import mode_for_backend
from houmao.agents.realm_controller import gateway_access_runtime, gateway_service, registry_storage
from houmao.agents.realm_controller.agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
)
from houmao.agents.realm_controller.backends.dispatch_control import HeadlessDispatchControl
from houmao.agents.realm_controller.backends.tmux_runtime import set_tmux_session_environment
from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.agents.realm_controller.gateway_models import GatewayAttachContractV1
from houmao.agents.realm_controller.gateway_storage import (
    GatewayCapabilityPublication,
    ensure_gateway_capability,
)
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import (
    HeadlessTurnSessionSelection,
    LaunchPlan,
    RoleInjectionPlan,
)
from houmao.agents.realm_controller.registry_models import (
    ManagedAgentRegistryRecordV3,
    RegistryIdentityV1,
    RegistryGatewayV1,
    RegistryLifecycleV1,
    RegistryLivenessV1,
    RegistryMailboxesV1,
    RegistryMailboxSlotV1,
    RegistryRuntimeV1,
    RegistryTerminalV2,
)
from houmao.agents.realm_controller.registry_storage import (
    load_managed_agent_record_by_agent_id,
    publish_managed_agent_record,
    record_path_for_agent_id,
)
from houmao.agents.realm_controller.runtime import RuntimeSessionController
from houmao.execution.context import observed_local_binding
from houmao.execution.tmux import tmux_server_scope
from houmao.gateway.access import (
    CHALLENGE_HEADER,
    SIGNATURE_HEADER,
    GatewayAccessError,
    GatewayAdminKey,
    GatewayChallenge,
    GatewayChallengeRequest,
    GatewayClientBinding,
    GatewayLaunchSeed,
    GatewayRequestBinding,
    GatewayTarget,
    load_gateway_signer,
    public_key_text,
    sign_sshsig,
    sshsig_header,
)
from houmao.gateway.deployment import GatewayDeployment
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR
from houmao.passive_server import discovery as passive_discovery
from houmao.passive_server.app import create_app as create_passive_app
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.service import PassiveServerService
from houmao.server.managed_agents import ManagedHeadlessAuthorityRecord
from houmao.srv_ctrl.commands.main import cli

_PREFIX = "/agents/tls-fixture"
_AGENT = "tls-access"
_TMUX_SESSION = "HOUMAO-tls-access"


class _FixtureExecution(gateway_service._LocalHeadlessGatewayAdapter):
    """Confirm actual gateway dispatch calls without running a provider workload."""

    def __init__(self, contract: GatewayAttachContractV1, generation: str) -> None:
        """Bind the live fixture's execution identity and prompt collection."""

        self.m_attach_contract: GatewayAttachContractV1 = contract
        self.m_generation: str = generation
        self.m_prompts: list[str] = []
        self.m_dispatch_worker: threading.Thread | None = None
        self.m_finish_dispatch: threading.Event = threading.Event()

    def inspect_target(self) -> gateway_service._GatewayTargetState:
        """Expose a ready execution fixture to the gateway's normal admission path."""

        return gateway_service._GatewayTargetState(
            instance_id=self.m_attach_contract.runtime_session_id or self.m_generation,
            connectivity="connected",
            terminal_surface_eligibility="ready",
            prompt_admission_open=True,
        )

    def capture_plugin_execution_identity(self) -> tuple[str, str]:
        """Fence admission to this fixture generation and body."""

        return self.m_generation, "fixture-body"

    def submit_plugin_event(
        self,
        *,
        prompt: str,
        turn_id: str,
        session_selection: HeadlessTurnSessionSelection | None,
        control: HeadlessDispatchControl,
    ) -> None:
        """Record the literal dispatch and confirm handoff through production control."""

        control.require_allowed()
        self.m_dispatch_worker = threading.current_thread()
        self.m_prompts.append(prompt)
        control.confirm_handoff()
        if not self.m_finish_dispatch.wait(timeout=5.0):
            raise RuntimeError("HTTPS fixture did not release the acknowledged handoff.")

    def cancel_plugin_event(self, control: HeadlessDispatchControl) -> None:
        """Allow the runtime to cancel an unfinished fixture handoff."""

        self.m_finish_dispatch.set()

    def finish_acknowledged_dispatch(self) -> None:
        """Finish the confirmed native turn and wait for owner claim settlement."""

        worker = self.m_dispatch_worker
        assert worker is not None
        self.m_finish_dispatch.set()
        worker.join(timeout=5.0)
        assert not worker.is_alive()
        self.m_finish_dispatch.clear()


@contextmanager
def _isolated_tmux(tmp_path: Path) -> Iterator[Path]:
    """Keep the test's only session on a namespaced private tmux server."""

    executable = shutil.which("tmux")
    if executable is None:
        pytest.skip("tmux is unavailable")
    socket_path = tmp_path / "tmux.sock"
    argv = [executable, "-S", str(socket_path)]
    environment = dict(os.environ)
    environment.pop("TMUX", None)
    environment.pop("TMUX_PANE", None)
    subprocess.run(
        [*argv, "-f", os.devnull, "new-session", "-d", "-s", _TMUX_SESSION, "sleep 120"],
        check=True,
        capture_output=True,
        env=environment,
    )
    try:
        yield socket_path
    finally:
        subprocess.run(
            [*argv, "kill-session", "-t", f"={_TMUX_SESSION}"],
            check=False,
            capture_output=True,
            env=environment,
        )


def _provision_runtime(
    tmp_path: Path,
    *,
    tmux_socket: Path,
    advertised_url: str | None,
    agent_id: str = _AGENT,
    session_name: str = _TMUX_SESSION,
    provision_access: bool = True,
) -> tuple[Path, str]:
    """Prepare observed owner authority and normal gateway discovery inputs."""

    owned_runtime = tmp_path / "runtime"
    registry = tmp_path / "registry"
    binding = observed_local_binding(
        working_directory=tmp_path,
        runtime_root=owned_runtime,
        registry_root=registry,
        tmux_socket=str(tmux_socket),
    )
    generation = str(uuid4())
    session_id = "tls-fixture"
    backend = "codex_headless"
    manifest_path = default_manifest_path(owned_runtime, backend, session_id)
    agent_def = tmp_path / "agent-def"
    agent_def.mkdir()
    home_path = tmp_path / "fixture-agent-home"
    home_path.mkdir()
    memory = tmp_path / ".houmao" / "memory" / "agents" / agent_id
    (memory / "pages").mkdir(parents=True)
    brain = _fixture_brain(tmp_path, agent_def=agent_def, home_path=home_path)
    launch = LaunchPlan(
        backend=backend,
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=home_path,
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="native_developer_instructions", role_name="fixture", prompt="fixture role"
        ),
        metadata={"headless_output_format": "jsonl"},
        execution_binding=binding,
    )
    backend_state = {
        "session_id": "fixture-provider-session",
        "turn_index": 0,
        "role_bootstrap_applied": True,
        "working_directory": str(tmp_path),
        "resume_selection_kind": "none",
        "tmux_session_name": session_name,
        "tmux_socket_path": str(tmux_socket),
    }
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch,
            role_name="fixture",
            brain_manifest_path=brain,
            backend_state=backend_state,
            agent_name=session_name,
            agent_id=agent_id,
            tmux_session_name=session_name,
            session_id=session_id,
            agent_def_dir=agent_def,
            registry_generation_id=generation,
            gateway_admin_seed=GatewayLaunchSeed(),
            memory_root=memory,
            memo_file=memory / "memo.md",
            pages_dir=memory / "pages",
        )
    )
    write_session_manifest(manifest_path, payload)
    ensure_gateway_capability(
        GatewayCapabilityPublication(
            manifest_path=manifest_path,
            backend=backend,
            tool="codex",
            session_id=session_id,
            tmux_session_name=session_name,
            working_directory=tmp_path,
            backend_state=backend_state,
            agent_def_dir=agent_def,
        )
    )
    if provision_access:
        gateway_access_runtime.provision_gateway_generation(
            binding=binding, agent_id=agent_id, generation_id=generation, seed=GatewayLaunchSeed()
        )
        gateway_access_runtime.save_gateway_deployment(
            manifest_path,
            GatewayDeployment(public_input_enabled=True, advertised_url=advertised_url),
        )

    now = datetime.now(UTC)
    empty_slot = RegistryMailboxSlotV1(revision="fixture-empty", binding=None)
    record = ManagedAgentRegistryRecordV3(
        agent_name=session_name,
        agent_id=agent_id,
        generation_id=generation,
        execution_binding=binding,
        mode=mode_for_backend(backend),
        identity=RegistryIdentityV1(backend=backend, tool="codex"),
        runtime=RegistryRuntimeV1(
            manifest_path=str(manifest_path),
            session_root=str(manifest_path.parent),
            agent_def_dir=str(agent_def),
        ),
        terminal=RegistryTerminalV2(
            current_session_name=session_name,
            last_session_name=session_name,
            socket_path=str(tmux_socket),
        ),
        lifecycle=RegistryLifecycleV1(
            state="active",
            relaunchable=False,
            state_updated_at=now.isoformat(),
        ),
        liveness=RegistryLivenessV1(
            published_at=now.isoformat(),
            lease_expires_at=(now + timedelta(minutes=3)).isoformat(),
        ),
        mailboxes=RegistryMailboxesV1(offline=empty_slot, online=empty_slot),
        canonical_mail_identity=None,
    )
    publish_managed_agent_record(record, env={HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: str(registry)})
    with tmux_server_scope(tmux_socket):
        set_tmux_session_environment(
            session_name=session_name,
            env_vars={
                AGENT_MANIFEST_PATH_ENV_VAR: str(manifest_path),
                AGENT_DEF_DIR_ENV_VAR: str(agent_def),
            },
        )
    return manifest_path, generation


def _fixture_brain(tmp_path: Path, *, agent_def: Path, home_path: Path) -> Path:
    """Provide the minimal role and empty provider inputs needed to resume for CLI control."""

    role = agent_def / "roles" / "fixture" / "system-prompt.md"
    role.parent.mkdir(parents=True)
    role.write_text("fixture role\n")
    env = tmp_path / "fixture.env"
    env.touch()
    adapter = str(tmp_path / "fixture-adapter.yaml")
    manifest = tmp_path / "brain.yaml"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "inputs": {
                    "tool": "codex",
                    "skills": [],
                    "setup": "default",
                    "auth": "default",
                    "adapter_path": adapter,
                    "preset_path": None,
                },
                "launch_policy": {"operator_prompt_mode": "as_is"},
                "runtime": {
                    "runtime_root": str(tmp_path),
                    "home_id": "tls-fixture",
                    "home_path": str(home_path),
                    "launch_helper": str(home_path / "launch.sh"),
                    "launch_executable": "codex",
                    "launch_home_selector": {"env_var": "CODEX_HOME", "value": str(home_path)},
                    "launch_contract": {
                        "adapter_defaults": {"args": [], "tool_params": {}},
                        "requested_overrides": {"preset": None, "direct": None},
                        "tool_metadata": {"tool_params": {}},
                        "construction_provenance": {
                            "adapter_path": adapter,
                            "preset_path": None,
                            "preset_overrides_present": False,
                            "direct_overrides_present": False,
                        },
                    },
                    "cao_parsing_mode": "shadow_only",
                },
                "credentials": {
                    "auth_path": str(tmp_path / "fixture-no-provider-auth"),
                    "projected_files": [],
                    "env_contract": {"source_file": str(env), "allowlisted_env_vars": []},
                },
            }
        )
    )
    return manifest


def _certificate(tmp_path: Path) -> tuple[Path, ssl.SSLContext]:
    """Create a private CA and a loopback-only leaf outside the checkout."""

    now = datetime.now(UTC)
    ca_key = Ed25519PrivateKey.generate()
    leaf_key = Ed25519PrivateKey.generate()
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Houmao fixture CA")])
    leaf_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Houmao TLS fixture")])

    def certificate_builder(
        subject: x509.Name,
        issuer: x509.Name,
        key: Ed25519PrivateKey,
    ) -> x509.CertificateBuilder:
        """Constrain generated certificates to the fixture lifetime."""

        return (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(minutes=20))
        )

    ca = (
        certificate_builder(ca_name, ca_name, ca_key)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False
        )
        .sign(ca_key, None)
    )
    leaf = (
        certificate_builder(leaf_name, ca_name, leaf_key)
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(IPv4Address("127.0.0.1"))]), critical=False
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False
        )
        .sign(ca_key, None)
    )
    ca_path, cert_path, key_path = (
        tmp_path / "fixture-ca.pem",
        tmp_path / "fixture-cert.pem",
        tmp_path / "fixture-tls.key",
    )
    ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    cert_path.write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    _write_private_key(key_path, leaf_key, private_format=serialization.PrivateFormat.PKCS8)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(cert_path, key_path)
    return ca_path, tls


def _write_private_key(
    path: Path,
    signer: Ed25519PrivateKey,
    *,
    private_format: serialization.PrivateFormat = serialization.PrivateFormat.OpenSSH,
) -> None:
    """Store fixture signing material mode 0600 from its first write."""

    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as target:
        target.write(
            signer.private_bytes(
                serialization.Encoding.PEM, private_format, serialization.NoEncryption()
            )
        )


class _PrefixProxy(BaseHTTPRequestHandler):
    """A deployed HTTPS endpoint with a prefix and an owner-local HTTP backend."""

    backend_port: int | None = None
    forwarded_paths: list[str]

    def do_GET(self) -> None:
        """Proxy GET operations."""

        self._forward()

    def do_POST(self) -> None:
        """Proxy POST operations."""

        self._forward()

    def do_DELETE(self) -> None:
        """Proxy DELETE operations."""

        self._forward()

    def _forward(self) -> None:
        """Strip exactly the declared prefix and supply trusted scheme information."""

        cls = type(self)
        if not self.path.startswith(f"{_PREFIX}/") or cls.backend_port is None:
            self.send_error(404)
            return
        cls.forwarded_paths.append(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else None
        headers = {
            name: value
            for name, value in self.headers.items()
            if name.lower() not in {"connection", "x-forwarded-proto", "x-forwarded-for"}
        }
        headers["X-Forwarded-Proto"] = "https"
        connection = HTTPConnection("127.0.0.1", cls.backend_port, timeout=4)
        try:
            connection.request(self.command, self.path.removeprefix(_PREFIX), body, headers)
            response = connection.getresponse()
            payload = response.read()
            self.send_response(response.status)
            for name, value in response.getheaders():
                if name.lower() in {
                    "cache-control",
                    "content-type",
                    "location",
                    "referrer-policy",
                    "www-authenticate",
                }:
                    self.send_header(name, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        finally:
            connection.close()

    def log_message(self, format: str, *args: object) -> None:
        """Keep fixture request diagnostics free of proof and prompt data."""


@contextmanager
def _serve_gateway(
    manifest_path: Path, monkeypatch: pytest.MonkeyPatch, generation: str
) -> Iterator[tuple[str, _FixtureExecution]]:
    """Serve the production HTTP app and track the assigned loopback listener."""

    adapters: list[_FixtureExecution] = []

    def build_adapter(*, attach_contract: GatewayAttachContractV1) -> _FixtureExecution:
        """Inject only the execution transport, leaving admission and dispatch live."""

        adapter = _FixtureExecution(attach_contract, generation)
        adapters.append(adapter)
        return adapter

    monkeypatch.setattr(gateway_service, "_build_gateway_execution_adapter", build_adapter)
    runtime = gateway_service.GatewayServiceRuntime.from_gateway_root(
        gateway_root=manifest_path.parent / "gateway",
        host="127.0.0.1",
        port=0,
    )
    app = gateway_service.create_app(runtime=runtime)
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=0,
        log_level="error",
        access_log=False,
        proxy_headers=True,
        forwarded_allow_ips="127.0.0.1",
    )
    startup_finished = threading.Event()

    class ReadyServer(gateway_service._GatewayUvicornServer):
        """Wait for both listener binding and production gateway startup."""

        async def startup(self, sockets: list[Socket] | None = None) -> None:
            """Signal readiness after gateway startup diagnostics are written."""

            await super().startup(sockets=sockets)
            startup_finished.set()

    server = ReadyServer(config, runtime=runtime, requested_host="127.0.0.1")
    worker = threading.Thread(target=server.run, name="tls-fixture-gateway", daemon=True)
    worker.start()
    try:
        assert startup_finished.wait(5) and server.started
        yield runtime.owner_connect_url, adapters[0]
    finally:
        server.should_exit = True
        worker.join(5.0)
        assert not worker.is_alive()


@pytest.mark.parametrize("attach", [False, True])
def test_self_status_queries_use_authority_without_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, attach: bool
) -> None:
    """Verify owner-local and signed gateway self queries with publication disabled."""

    monkeypatch.setattr(
        gateway_access_runtime, "resolve_houmao_home_root", lambda: tmp_path / "owner"
    )
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))

    def deny_publication(*args: object, **kwargs: object) -> None:
        pytest.fail("Self status attempted registry or gateway publication")

    with _isolated_tmux(tmp_path) as socket, tmux_server_scope(socket):
        manifest, generation = _provision_runtime(
            tmp_path, tmux_socket=socket, advertised_url="https://127.0.0.1:9443"
        )
        monkeypatch.setenv(AGENT_MANIFEST_PATH_ENV_VAR, str(manifest))
        context = _serve_gateway(manifest, monkeypatch, generation) if attach else nullcontext()
        with context, monkeypatch.context() as observation:
            observation.setattr(registry_storage, "_managed_agent_record_lock", deny_publication)
            observation.setattr(
                RuntimeSessionController, "ensure_gateway_capability", deny_publication
            )
            runner = CliRunner()
            state = runner.invoke(cli, ["--print-json", "agents", "self", "state"])
            assert state.exit_code == 0, state.output
            assert json.loads(state.output)["identity"]["agent_id"] == _AGENT
            mail = runner.invoke(cli, ["--print-json", "agents", "self", "mail", "status"])
            assert mail.exit_code == 0, mail.output
            assert json.loads(mail.output)["execution_path"] == (
                "gateway_backed" if attach else "manager_direct"
            )


@pytest.mark.parametrize("exercise_web_entry", [False, True], ids=["public-input", "web-entry"])
def test_authenticated_gateway_over_a_verified_https_proxy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exercise_web_entry: bool,
) -> None:
    """Qualify signed access and the selected public or owner-local operation over HTTPS."""

    ca, tls = _certificate(tmp_path)
    monkeypatch.setattr(
        gateway_access_runtime, "resolve_houmao_home_root", lambda: tmp_path / "owner"
    )
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)

    class Proxy(_PrefixProxy):
        """Keep per-run proxy routing and observations isolated."""

        forwarded_paths: list[str] = []

    with ThreadingHTTPServer(("127.0.0.1", 0), Proxy) as proxy, _isolated_tmux(tmp_path) as socket:
        proxy.socket = tls.wrap_socket(proxy.socket, server_side=True)
        advertised = f"https://127.0.0.1:{proxy.server_port}{_PREFIX}"
        manifest, generation = _provision_runtime(
            tmp_path,
            tmux_socket=socket,
            advertised_url=advertised,
        )
        monkeypatch.setenv(AGENT_MANIFEST_PATH_ENV_VAR, str(manifest))
        with _serve_gateway(manifest, monkeypatch, generation) as (owner_url, execution):
            Proxy.backend_port = int(owner_url.rsplit(":", 1)[-1])
            proxy_worker = threading.Thread(target=proxy.serve_forever, daemon=True)
            proxy_worker.start()
            try:
                _exercise_access(
                    tmp_path,
                    ca=ca,
                    advertised=advertised,
                    local_url=owner_url,
                    manifest=manifest,
                    socket_path=socket,
                    execution=execution,
                    exercise_web_entry=exercise_web_entry,
                )
                assert f"{_PREFIX}/v1/auth/challenge" in Proxy.forwarded_paths
                assert f"{_PREFIX}/v1/admin/keys" in Proxy.forwarded_paths
            finally:
                proxy.shutdown()
                proxy_worker.join(5.0)


def _exercise_access(
    tmp_path: Path,
    *,
    ca: Path,
    advertised: str,
    local_url: str,
    manifest: Path,
    socket_path: Path,
    execution: _FixtureExecution,
    exercise_web_entry: bool,
) -> None:
    """Use production clients and the maintained CLI against the live endpoints."""

    unsigned = GatewayClient(base_url=advertised, ca_bundle_path=ca)
    local = GatewayClient(base_url=local_url)
    descriptor = unsigned.describe_endpoint()
    assert descriptor.admin_mode == "open"
    assert descriptor.proof_protocol == "sshsig-v2"
    assert descriptor.advertised_url == advertised
    assert set(descriptor.public_operations) == {"messages", "public_prompt"}
    assert unsigned.health().model_dump() == {"protocol_version": "v1", "status": "ok"}
    assert unsigned.list_reminders().reminders == []
    with pytest.raises(GatewayHttpError):
        GatewayClient(base_url=advertised).health()
    with pytest.raises(GatewayHttpError):
        GatewayClient(
            base_url=advertised.replace("127.0.0.1", "localhost"),
            ca_bundle_path=ca,
        ).health()
    assert unsigned.status().gateway_health == "healthy"
    if exercise_web_entry:
        trust = ssl.create_default_context(cafile=str(ca))
        with httpx.Client(base_url=advertised, verify=trust, trust_env=False) as caller:
            for response in (caller.get("/v1/web/enter"), caller.post("/v1/web/entry-ticket")):
                assert response.status_code == 403
                assert "location" not in response.headers

    def admin_client(
        principal: str,
        purpose: str,
    ) -> tuple[GatewayAdminKey, GatewayClient, Path]:
        """Create a fixture key and bind its signer to the verified proxy endpoint."""

        signer = Ed25519PrivateKey.generate()
        path = tmp_path / f"{principal}.key"
        _write_private_key(path, signer)
        key = GatewayAdminKey(principal=principal, public_key=public_key_text(signer.public_key()))
        binding = GatewayClientBinding(
            base_url=advertised,
            owner=descriptor.target.owner,
            purpose="register" if purpose == "register" else "caller",
            private_key_path=str(path),
            ca_bundle_path=str(ca),
        )
        return (
            key,
            GatewayClient(
                binding=binding,
                target_incarnation=descriptor.target.incarnation,
                registration_key=key if purpose == "register" else None,
            ),
            path,
        )

    first, register, first_path = admin_client("first", "register")
    second, second_client, _ = admin_client("second", "admin")
    assert register.add_admin_key(first) == first.key_id
    keyed = unsigned.describe_endpoint()
    assert keyed.admin_mode == "keyed"
    assert keyed.proof_protocol == "sshsig-v2"
    with pytest.raises(GatewayHttpError) as private:
        unsigned.status()
    assert private.value.status_code == 401
    with pytest.raises(GatewayHttpError) as local_denial:
        local.list_reminders()
    assert local_denial.value.status_code == 401

    first_client = GatewayClient(
        binding=GatewayClientBinding(
            base_url=advertised,
            owner=descriptor.target.owner,
            purpose="caller",
            private_key_path=str(first_path),
            ca_bundle_path=str(ca),
        ),
        target_incarnation=descriptor.target.incarnation,
    )
    assert first_client.add_admin_key(second) == second.key_id
    first_client.status()
    second_client.status()

    with tmux_server_scope(socket_path):
        result = CliRunner().invoke(cli, ["--print-json", "agents", "self", "mail", "status"])
    assert result.exit_code == 0, result.output
    cli_payload = json.loads(result.output)
    assert cli_payload["execution_path"] == "gateway_backed"
    self_signer = gateway_access_runtime.gateway_access_for_manifest(
        manifest
    ).self_store.self_signer_path(descriptor.target.incarnation)
    assert str(self_signer) not in result.output
    assert "SSHSIG" not in result.output

    trust = ssl.create_default_context(cafile=str(ca))
    with httpx.Client(base_url=advertised, verify=trust, trust_env=False) as caller:
        if exercise_web_entry:
            _assert_web_entry_requires_direct_ingress(caller, first, first_path, advertised)
            first_client.status()
            assert execution.m_prompts == []
            return
        refused = caller.post(
            "/v1/requests", content=b"{", headers={"Content-Type": "application/json"}
        )
        assert refused.status_code == 401
        assert "/v1/auth/challenge" in refused.headers["WWW-Authenticate"]
        for route, event, content in (
            ("/v1/messages", "contact-1", {"text": "Read this notice when available."}),
            ("/v1/public/prompt", "contact-2", {"prompt": "Reply by approved mail if permitted."}),
        ):
            response = caller.post(route, json={"source_event_id": event, **content})
            assert response.status_code == 200, response.text
            assert response.json() == {"disposition": "dispatched", "source_event_id": event}
            execution.finish_acknowledged_dispatch()
    assert len(execution.m_prompts) == 2
    assert all(
        prompt.startswith("This request came through the public gateway.")
        for prompt in execution.m_prompts
    )

    second_client.remove_admin_key(first.key_id)
    with pytest.raises(GatewayHttpError) as revoked:
        first_client.status()
    assert revoked.value.status_code == 403
    second_client.remove_admin_key(second.key_id)
    assert unsigned.describe_endpoint().admin_mode == "open"
    assert unsigned.list_reminders().reminders == []
    assert unsigned.status().gateway_health == "healthy"


def _assert_web_entry_requires_direct_ingress(
    caller: httpx.Client, admin: GatewayAdminKey, signer_path: Path, advertised: str
) -> None:
    """Send valid request-bound proof through the proxy and check the Web origin refusal."""

    path = "/v1/web/entry-ticket"
    binding = GatewayRequestBinding.from_request("POST", path, "", b"")
    challenge_request = GatewayChallengeRequest(
        purpose="caller", key_id=admin.key_id, request=binding
    )
    challenge_result = caller.post(
        "/v1/auth/challenge", json=challenge_request.model_dump(mode="json")
    )
    challenge = GatewayChallenge.model_validate_json(challenge_result.raise_for_status().content)
    assert (challenge.issuer, challenge.key_id, challenge.request) == (
        advertised,
        admin.key_id,
        binding,
    )
    signature = sign_sshsig(load_gateway_signer(signer_path), challenge.signing_bytes())
    responses = (
        caller.get("/v1/web/enter"),
        caller.get("/v1/web/enter", params={"ticket": "A" * 43}),
        caller.post(
            path,
            headers={
                CHALLENGE_HEADER: challenge.challenge_id,
                SIGNATURE_HEADER: sshsig_header(signature),
            },
        ),
    )
    for response in responses:
        assert response.status_code == 403
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert "location" not in response.headers
        assert "owner-local" in response.text or "owner_local_web_entry_required" in response.text


_PEER_AGENT = "tls-cross-account-peer"
_PEER_SESSION = "HOUMAO-tls-cross-account-peer"
# Run the second managed fixture and its signers inside the other account.
_PEER_SCRIPT = """
import json
from pathlib import Path
import runpy
import sys
from uuid import uuid4

from houmao.agents.realm_controller import gateway_access_runtime
from houmao.agents.realm_controller.manifest import load_session_manifest, update_session_manifest
from houmao.agents.realm_controller.registry_storage import (
    load_managed_agent_record_by_agent_id,
    publish_managed_agent_record,
)
from houmao.cao.rest_client import CaoApiError
from houmao.gateway.access import GatewayClientBinding, GatewayOwner
from houmao.passive_server.client import PassiveServerClient
from houmao.srv_ctrl.commands.main import cli

operation, root, fixture_path, *arguments = sys.argv[1:]
root = Path(root)
gateway_access_runtime.resolve_houmao_home_root = lambda: root / "owner"
if operation == "provision":
    fixture = runpy.run_path(fixture_path)
    fixture["_provision_runtime"](
        root, tmux_socket=root / "tmux.sock", advertised_url=None,
        agent_id=fixture["_PEER_AGENT"], session_name=fixture["_PEER_SESSION"],
    )
elif operation == "relaunch":
    current = load_managed_agent_record_by_agent_id(arguments[0])
    assert current is not None and current.execution_binding is not None
    manifest = Path(current.runtime.manifest_path)
    generation = str(uuid4())
    gateway_access_runtime.provision_gateway_generation(
        binding=current.execution_binding, agent_id=current.agent_id, generation_id=generation,
    )
    runtime = dict(load_session_manifest(manifest).payload["runtime"])
    runtime["registry_generation_id"] = generation
    update_session_manifest(manifest, {"registry_generation_id": generation, "runtime": runtime})
    publish_managed_agent_record(
        current.model_copy(update={"generation_id": generation}),
        expected_generation_id=current.generation_id,
    )
elif operation == "cli":
    cli.main(args=arguments)
elif operation == "passive":
    url, agent_id, context_id, generation, route = arguments
    client = PassiveServerClient(
        url,
        binding=GatewayClientBinding(
            base_url=url, owner=GatewayOwner(agent_id=agent_id, context_id=context_id),
            purpose="caller", private_key_path=str(root / "peer-key"),
        ),
        target_incarnation=generation,
    )
    try:
        _, status, _ = client._request_root_json("GET", f"/houmao/agents/{agent_id}/{route}")
    except CaoApiError as error:
        status = error.status_code
    print(json.dumps({"status": status}))
"""


@dataclass(frozen=True)
class _PeerAccount:
    """Run a synthetic source agent as a previously provisioned separate OS user."""

    username: str
    root: Path

    def run(self, *argv: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run without ambient credentials, terminal coordinates, or config roots."""

        return subprocess.run(
            [
                "sudo",
                "-n",
                "-u",
                self.username,
                "--",
                "env",
                "-i",
                "PATH=/usr/bin:/bin",
                "PYTHONDONTWRITEBYTECODE=1",
                f"{HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR}={self.root / 'registry'}",
                *argv,
            ],
            cwd=self.root if os.access(self.root, os.X_OK) else "/tmp",
            capture_output=True,
            text=True,
            check=check,
            timeout=20,
        )

    def python(
        self, operation: str, *args: str, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        """Run the fixture or its actual manager and typed passive client."""

        return self.run(
            sys.executable,
            "-c",
            _PEER_SCRIPT,
            operation,
            str(self.root),
            str(Path(__file__).resolve()),
            *args,
            check=check,
        )


@contextmanager
def _provision_peer_account(username: str) -> Iterator[tuple[_PeerAccount, dict[str, str]]]:
    """Start an isolated tmux server and managed fixture under the second UID."""

    identity = subprocess.run(
        ["sudo", "-n", "-u", username, "--", "id", "-u"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert int(identity.stdout) != os.geteuid()
    directory = subprocess.run(
        ["sudo", "-n", "-u", username, "--", "mktemp", "-d", "/tmp/houmao-access-peer.XXXXXXXX"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    root = Path(directory.stdout.strip())
    assert root.parent == Path("/tmp") and root.name.startswith("houmao-access-peer.")
    peer = _PeerAccount(username, root)
    socket = root / "tmux.sock"
    try:
        peer.run(
            "tmux",
            "-S",
            str(socket),
            "-f",
            os.devnull,
            "new-session",
            "-d",
            "-s",
            _PEER_SESSION,
            "sleep 120",
        )
        peer.python("provision")
        peer.run("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(root / "peer-key"))
        provisioned = peer.python(
            "cli",
            "--print-json",
            "agents",
            "single",
            "--agent-id",
            _PEER_AGENT,
            "access",
            "peer-signer",
            "--key",
            str(root / "peer-key"),
        )
        yield peer, json.loads(provisioned.stdout)
    finally:
        peer.run("tmux", "-S", str(socket), "kill-session", "-t", f"={_PEER_SESSION}", check=False)
        peer.run("rm", "-rf", "--", str(root))


@contextmanager
def _serve_passive_target(
    tmp_path: Path,
    manifest: Path,
    *,
    track_detached_usage: bool,
) -> Iterator[str]:
    """Serve genuine passive routing, with retained headless authority when detached."""

    with Socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        base_url = f"http://127.0.0.1:{listener.getsockname()[1]}"
        config = PassiveServerConfig(
            api_base_url=base_url,
            runtime_root=tmp_path / "runtime",
            registry_root=tmp_path / "registry",
            discovery_poll_interval_seconds=0.1,
        )
        service = PassiveServerService(config)
        if track_detached_usage:
            service.m_headless.m_store.ensure_directories()
            service.m_headless.m_store.write_authority(
                ManagedHeadlessAuthorityRecord(
                    tracked_agent_id=_AGENT,
                    backend="codex_headless",
                    tool="codex",
                    agent_id=_AGENT,
                    agent_name=_TMUX_SESSION,
                    manifest_path=str(manifest),
                    session_root=str(manifest.parent),
                    tmux_session_name=_TMUX_SESSION,
                    agent_def_dir=str(tmp_path / "agent-def"),
                    created_at_utc=datetime.now(UTC).isoformat(),
                    updated_at_utc=datetime.now(UTC).isoformat(),
                )
            )
        ready = threading.Event()

        class ReadyPassive(uvicorn.Server):
            """Wait for discovery service startup and listener setup."""

            async def startup(self, sockets: list[Socket] | None = None) -> None:
                """Release the test after the live passive endpoint is ready."""

                await super().startup(sockets=sockets)
                ready.set()

        server = ReadyPassive(
            uvicorn.Config(
                create_passive_app(service=service),
                log_level="error",
                access_log=False,
            )
        )
        worker = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        worker.start()
        try:
            assert ready.wait(5) and server.started
            yield base_url
        finally:
            server.should_exit = True
            worker.join(5)
            assert not worker.is_alive()


@contextmanager
def _publish_fixture_gateway(base_url: str, manifest: Path) -> Iterator[None]:
    """Publish the real listener alongside the isolated synthetic runtime record."""

    record = load_managed_agent_record_by_agent_id(_AGENT)
    assert record is not None and record.gateway is None
    descriptor = GatewayClient(base_url=base_url).describe_endpoint()
    connection = RegistryGatewayV1(
        host="127.0.0.1",
        port=int(base_url.rsplit(":", 1)[1]),
        state_path=str(manifest.parent / "gateway" / "state.json"),
        protocol_version="v1",
        owner_connect_url=base_url,
        endpoint_descriptor=descriptor,
    )
    publish_managed_agent_record(record.model_copy(update={"gateway": connection}))
    try:
        yield
    finally:
        publish_managed_agent_record(record)


def _target_access_cli(*arguments: str) -> dict[str, object]:
    """Run the owner-side policy workflow and return its receipt."""

    result = CliRunner().invoke(
        cli, ["--print-json", "agents", "single", "--agent-id", _AGENT, "access", *arguments]
    )
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _peer_gateway_call(
    peer: _PeerAccount,
    base_url: str,
    *,
    path: str,
    expected_status: int,
) -> str:
    """Invoke the remote peer CLI with an explicit canonical target and listener."""

    descriptor = GatewayClient(base_url=base_url).describe_endpoint()
    result = peer.python(
        "cli",
        "--print-json",
        "agents",
        "single",
        "--agent-id",
        descriptor.target.owner.agent_id,
        "access",
        "request",
        "--url",
        base_url,
        "--context-id",
        descriptor.target.owner.context_id,
        "--generation",
        descriptor.target.incarnation,
        "--presence",
        descriptor.presence_id,
        "--source-agent-id",
        _PEER_AGENT,
        "GET",
        path,
        check=False,
    )
    if expected_status == 200:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode == 1 and f"HTTP {expected_status}" in result.stderr, result.stderr
    assert str(peer.root) not in result.stderr
    return result.stdout


def _peer_passive_call(
    peer: _PeerAccount,
    base_url: str,
    *,
    target: GatewayTarget,
    route: str,
    expected_status: int,
) -> None:
    """Check the same enrolled source from a signed passive request."""

    result = peer.python(
        "passive",
        base_url,
        target.owner.agent_id,
        target.owner.context_id,
        target.incarnation,
        route,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"status": expected_status}


def test_cross_account_peer_policy_on_distinct_tmux_servers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify live and detached target policy using a key held only by a separate account."""

    peer_user = os.environ.get("HOUMAO_TEST_PEER_USER")
    if not peer_user:
        pytest.skip("Set HOUMAO_TEST_PEER_USER to an existing account accessible with sudo -n -u")
    monkeypatch.setattr(
        gateway_access_runtime, "resolve_houmao_home_root", lambda: tmp_path / "owner"
    )
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    with _provision_peer_account(peer_user) as (peer, public), _isolated_tmux(tmp_path) as socket:
        observe_sessions = passive_discovery._get_live_tmux_session_names

        def isolated_discovery(socket_path: str | None = None) -> set[str] | None:
            """Constrain every discovery probe, including the default scan, to the fixture."""

            assert socket_path in {None, str(socket)}
            return observe_sessions(str(socket))

        monkeypatch.setattr(passive_discovery, "_get_live_tmux_session_names", isolated_discovery)
        manifest, generation = _provision_runtime(tmp_path, tmux_socket=socket, advertised_url=None)
        assert socket != peer.root / "tmux.sock"
        access = gateway_access_runtime.gateway_access_for_manifest(manifest)
        policy_path = access.private_root / "authorization.sqlite3"
        assert peer.run("test", "-r", str(policy_path), check=False).returncode == 1
        assert not os.access(peer.root / "peer-key", os.R_OK)
        assert public["logical_agent_id"] == _PEER_AGENT

        key_path = tmp_path / "peer.pub"
        key_path.write_text(public["public_key"], encoding="utf-8")
        admin_secret = Ed25519PrivateKey.generate()
        admin_private_key = tmp_path / "admin.key"
        admin_public_key = tmp_path / "admin.pub"
        _write_private_key(admin_private_key, admin_secret)
        admin_public_key.write_text(public_key_text(admin_secret.public_key()), encoding="utf-8")

        with _serve_gateway(manifest, monkeypatch, generation) as (url, _):
            unsigned = GatewayClient(base_url=url)
            before = unsigned.describe_endpoint()
            assert before.admin_mode == "open"
            assert unsigned.status().gateway_health == "healthy"
            admin = _target_access_cli(
                "admin-add",
                "--first",
                "--signer",
                str(admin_private_key),
                "--principal",
                "owner-admin",
                "--public-key",
                str(admin_public_key),
            )
            assert admin["admin_mode"] == "keyed"
            assert (
                _target_access_cli(
                    "principal-add",
                    "peer",
                    "--kind",
                    "agent",
                    "--label",
                    "Independent peer",
                    "--logical-agent-id",
                    public["logical_agent_id"],
                )["admin_mode"]
                == "keyed"
            )
            assert (
                _target_access_cli("credential-enroll", "peer", "--public-key", str(key_path))[
                    "key_id"
                ]
                == public["key_id"]
            )
            _target_access_cli(
                "role-put",
                "observe",
                "--permission",
                "agent",
                "agent.status.read",
                "--permission",
                "agent",
                "agent.usage.read",
            )
            _target_access_cli("role-assign", "peer", "observe")
            state = _peer_gateway_call(peer, url, path="/v1/status", expected_status=200)
            assert json.loads(state)["gateway_health"] == "healthy"
            peer.run(
                "tmux",
                "-S",
                str(peer.root / "tmux.sock"),
                "respawn-pane",
                "-k",
                "-t",
                f"{_PEER_SESSION}:0.0",
                "sleep 120",
            )
            peer.python("relaunch", _PEER_AGENT)
            _peer_gateway_call(peer, url, path="/v1/status", expected_status=200)
            _peer_gateway_call(peer, url, path="/v1/reminders", expected_status=403)
            with (
                _publish_fixture_gateway(url, manifest),
                _serve_passive_target(tmp_path, manifest, track_detached_usage=False) as passive,
            ):
                _peer_passive_call(
                    peer, passive, target=before.target, route="gateway", expected_status=200
                )
                _peer_passive_call(
                    peer,
                    passive,
                    target=before.target,
                    route="gateway/reminders",
                    expected_status=403,
                )

        with _serve_passive_target(tmp_path, manifest, track_detached_usage=True) as passive:
            _peer_passive_call(
                peer, passive, target=before.target, route="usage", expected_status=200
            )
            with httpx.Client(base_url=passive, trust_env=False) as unsigned_passive:
                assert unsigned_passive.get(f"/houmao/agents/{_AGENT}/usage").status_code == 401

            with _serve_gateway(manifest, monkeypatch, generation) as (url, _):
                current = GatewayClient(base_url=url).describe_endpoint()
                assert (current.target, current.admin_mode) == (before.target, "keyed")
                assert current.presence_id != before.presence_id
                _peer_gateway_call(peer, url, path="/v1/status", expected_status=200)
                _target_access_cli("role-revoke", "peer", "observe")
                _peer_gateway_call(peer, url, path="/v1/status", expected_status=403)
                _peer_passive_call(
                    peer, passive, target=before.target, route="usage", expected_status=403
                )
                _target_access_cli("credential-revoke", public["key_id"])
                _peer_gateway_call(peer, url, path="/v1/status", expected_status=401)
                removed = _target_access_cli(
                    "admin-remove", str(admin["key_id"]), "--signer", str(admin_private_key)
                )
                assert removed["admin_mode"] == "open" and removed["removed"] is True
                _peer_gateway_call(peer, url, path="/v1/status", expected_status=401)
                assert GatewayClient(base_url=url).status().gateway_health == "healthy"

            with httpx.Client(base_url=passive, trust_env=False) as anonymous:
                assert anonymous.get(f"/houmao/agents/{_AGENT}/usage").status_code == 200


@pytest.mark.parametrize("mode", ["open", "keyed"])
def test_explicit_reprovisioning_bypasses_retired_discovery_and_roster(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    """Use current owner manifest authority when retired registry records cannot be selected."""

    monkeypatch.setattr(
        gateway_access_runtime, "resolve_houmao_home_root", lambda: tmp_path / "owner"
    )
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    with _isolated_tmux(tmp_path) as socket:
        manifest, generation = _provision_runtime(
            tmp_path,
            tmux_socket=socket,
            advertised_url=None,
            provision_access=False,
        )
        access = gateway_access_runtime.gateway_access_for_manifest(manifest)
        digest = hashlib.sha256(access.owner.model_dump_json().encode()).hexdigest()
        legacy_root = access.private_root / digest
        legacy_root.mkdir(mode=0o700, parents=True)
        access.private_root.chmod(0o700)
        legacy_marker = access.private_root / f"{digest}.initialized"
        legacy_marker.touch(mode=0o600)
        legacy_marker.write_text("houmao-gateway-access-v1\n")
        old_key = GatewayAdminKey(
            principal="retired-key",
            public_key=public_key_text(Ed25519PrivateKey.generate().public_key()),
        )
        old_roster = legacy_root / "admin.json"
        old_roster.touch(mode=0o600)
        old_roster.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "owner": access.owner.model_dump(mode="json"),
                    "revision": 0,
                    "keys": [{"key": old_key.model_dump(mode="json"), "enrollment": 0}],
                }
            )
        )
        preserved = old_roster.read_bytes()

        record = record_path_for_agent_id(_AGENT)
        obsolete = json.loads(record.read_bytes())
        obsolete["gateway"] = {
            "host": "127.0.0.1",
            "port": 45000,
            "state_path": str(manifest.parent / "state.json"),
            "protocol_version": "v1",
            "owner_connect_url": "http://127.0.0.1:45000",
            "endpoint_descriptor": {
                "protocol": "v1",
                "target": access.target.model_dump(mode="json"),
                "presence_id": "retired-listener",
                "advertised_url": None,
                "admin_access": "key_required",
                "private_proof": "self_or_admin",
            },
        }
        record.write_text(json.dumps(obsolete))

        runner = CliRunner()
        command = ["--print-json", "agents", "single", "--agent-id", _AGENT, "access", "init"]
        refused = runner.invoke(cli, [*command, "--empty"])
        assert refused.exit_code == 1 and "verified local execution owner" in refused.output
        mismatched = [
            *command[:3],
            "--agent-id",
            "different-agent",
            "access",
            "init",
            "--manifest",
            str(manifest),
            "--empty",
        ]
        denied = runner.invoke(cli, mismatched)
        assert denied.exit_code == 1 and "verified local execution owner" in denied.output
        with pytest.raises(GatewayAccessError, match="unavailable"):
            access.store.snapshot()
        with pytest.raises(GatewayAccessError) as automatic:
            access.store.initialize()
        assert automatic.value.code == "retired_policy_requires_owner_init"

        if mode == "keyed":
            current_key = GatewayAdminKey(
                principal="current-operator",
                public_key=public_key_text(Ed25519PrivateKey.generate().public_key()),
            )
            seed = tmp_path / "explicit.json"
            seed.touch(mode=0o600)
            seed.write_text(GatewayLaunchSeed(admin_keys=(current_key,)).model_dump_json())
            initial = ["--seed", str(seed)]
        else:
            initial = ["--empty"]
        result = runner.invoke(cli, [*command, "--manifest", str(manifest), *initial])
        assert result.exit_code == 0, result.output
        state = access.store.snapshot()
        assert json.loads(result.output)["admin_mode"] == state.admin_mode == mode
        assert state.find_credential(old_key.key_id) is None
        assert access.self_store.load_self(generation).owner == access.owner
        assert old_roster.read_bytes() == preserved
