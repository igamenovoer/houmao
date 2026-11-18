"""Qualify per-agent gateway access through a real, verified HTTPS reverse proxy."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import IPv4Address
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import threading
import time
from uuid import uuid4

from click.testing import CliRunner
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.x509.oid import NameOID
import httpx
import pytest
import uvicorn

from houmao.agents.realm_controller import gateway_access_runtime, gateway_service
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
    RegistryLifecycleV1,
    RegistryLivenessV1,
    RegistryMailboxesV1,
    RegistryMailboxSlotV1,
    RegistryRuntimeV1,
    RegistryTerminalV2,
)
from houmao.agents.realm_controller.registry_storage import publish_managed_agent_record
from houmao.execution.context import observed_local_binding
from houmao.execution.tmux import tmux_server_scope
from houmao.gateway.access import (
    GatewayAdminKey,
    GatewayClientBinding,
    GatewayLaunchSeed,
    public_key_text,
)
from houmao.gateway.deployment import GatewayDeployment
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR
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
        self.m_prompts.append(prompt)
        control.confirm_handoff()

    def cancel_plugin_event(self, *, turn_id: str) -> None:
        """Allow the runtime to cancel an unfinished fixture handoff."""


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
    tmp_path: Path, *, tmux_socket: Path, advertised_url: str
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
    memory = tmp_path / ".houmao" / "memory" / "agents" / _AGENT
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
        "tmux_session_name": _TMUX_SESSION,
        "tmux_socket_path": str(tmux_socket),
    }
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch,
            role_name="fixture",
            brain_manifest_path=brain,
            backend_state=backend_state,
            agent_name=_TMUX_SESSION,
            agent_id=_AGENT,
            tmux_session_name=_TMUX_SESSION,
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
            tmux_session_name=_TMUX_SESSION,
            working_directory=tmp_path,
            backend_state=backend_state,
            agent_def_dir=agent_def,
        )
    )
    gateway_access_runtime.provision_gateway_generation(
        binding=binding, agent_id=_AGENT, generation_id=generation, seed=GatewayLaunchSeed()
    )
    gateway_access_runtime.save_gateway_deployment(
        manifest_path,
        GatewayDeployment(public_input_enabled=True, advertised_url=advertised_url),
    )

    now = datetime.now(UTC)
    empty_slot = RegistryMailboxSlotV1(revision="fixture-empty", binding=None)
    record = ManagedAgentRegistryRecordV3(
        agent_name=_TMUX_SESSION,
        agent_id=_AGENT,
        generation_id=generation,
        execution_binding=binding,
        identity=RegistryIdentityV1(backend=backend, tool="codex"),
        runtime=RegistryRuntimeV1(
            manifest_path=str(manifest_path),
            session_root=str(manifest_path.parent),
            agent_def_dir=str(agent_def),
        ),
        terminal=RegistryTerminalV2(
            current_session_name=_TMUX_SESSION,
            last_session_name=_TMUX_SESSION,
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
            session_name=_TMUX_SESSION,
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
                if name.lower() in {"content-type", "www-authenticate"}:
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
    server = gateway_service._GatewayUvicornServer(
        config, runtime=runtime, requested_host="127.0.0.1"
    )
    worker = threading.Thread(target=server.run, name="tls-fixture-gateway", daemon=True)
    worker.start()
    try:
        deadline = time.monotonic() + 5
        while worker.is_alive() and not server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started
        yield runtime.owner_connect_url, adapters[0]
    finally:
        server.should_exit = True
        worker.join(5.0)
        assert not worker.is_alive()


def test_authenticated_gateway_over_a_verified_https_proxy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Qualify enrollment, signed access, public handoff, and reopening over HTTPS."""

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
) -> None:
    """Use production clients and the maintained CLI against the live endpoints."""

    unsigned = GatewayClient(base_url=advertised, ca_bundle_path=ca)
    local = GatewayClient(base_url=local_url)
    descriptor = unsigned.describe_endpoint()
    assert descriptor.admin_access == "open"
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
    with pytest.raises(GatewayHttpError) as private:
        unsigned.status()
    assert private.value.status_code == 401

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
            purpose="register" if purpose == "register" else "admin",
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
    assert unsigned.describe_endpoint().admin_access == "key_required"
    with pytest.raises(GatewayHttpError) as local_denial:
        local.list_reminders()
    assert local_denial.value.status_code == 401

    first_client = GatewayClient(
        binding=GatewayClientBinding(
            base_url=advertised,
            owner=descriptor.target.owner,
            purpose="admin",
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
    ).store.self_signer_path(descriptor.target.incarnation)
    assert str(self_signer) not in result.output
    assert "SSHSIG" not in result.output

    trust = ssl.create_default_context(cafile=str(ca))
    with httpx.Client(base_url=advertised, verify=trust, trust_env=False) as caller:
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
    assert len(execution.m_prompts) == 2
    assert all(
        prompt.startswith("This request came through the public gateway.")
        for prompt in execution.m_prompts
    )

    second_client.remove_admin_key(first.key_id)
    with pytest.raises(GatewayHttpError) as revoked:
        first_client.status()
    assert revoked.value.status_code == 401
    second_client.remove_admin_key(second.key_id)
    assert unsigned.describe_endpoint().admin_access == "open"
    assert unsigned.list_reminders().reminders == []
    with pytest.raises(GatewayHttpError) as still_private:
        unsigned.status()
    assert still_private.value.status_code == 401
