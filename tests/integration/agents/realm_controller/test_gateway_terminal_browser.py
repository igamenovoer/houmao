"""Run the bundled browser terminal through gateway admission and a real tmux socket."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
import logging
import os
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import pytest
import uvicorn

from houmao.agents.realm_controller.gateway_admission import (
    GatewayAdmissionMiddleware,
    validate_core_gateway_routes,
)
from houmao.agents.realm_controller.gateway_plugin_host import GatewayPluginHost
from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime
from houmao.agents.realm_controller.gateway_terminal_entry import register_terminal_entry_routes
from houmao.gateway.access import (
    CHALLENGE_HEADER,
    SIGNATURE_HEADER,
    FirstEnrollment,
    GatewayAccessPolicy,
    GatewayAdminKey,
    GatewayChallengeRequest,
    GatewayGrant,
    GatewayOwner,
    GatewayRequestBinding,
    GatewayTarget,
    public_key_text,
    sign_sshsig,
    sshsig_header,
)
from houmao.gateway.authorization_store import AuthorizationStore
from houmao.gateway.operations import ADMIN_ADD, GatewayOperation
from tests.integration.agents.realm_controller.test_gateway_terminal_pty import (
    _Runtime,
    _tmux,
    runtime as runtime,
)


@dataclass(frozen=True)
class _BrowserGateway:
    """Identify one isolated gateway and the first key selected for enrollment."""

    origin: str
    signer_path: Path = field(repr=False)
    enroll_admin: Callable[[], None] = field(repr=False)


class _GatewayErrors(logging.Handler):
    """Capture ASGI errors that happen while the browser disconnects."""

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)
        self.m_errors: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Retain gateway error messages for the fixture teardown assertion."""

        self.m_errors.append(record.getMessage())


@pytest.fixture
def browser_gateway(
    runtime: _Runtime, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[_BrowserGateway]:
    """Serve the dashboard and terminal using one isolated binding and an open roster."""

    target = runtime.target()
    signer = Ed25519PrivateKey.generate()
    signer_path = tmp_path / "browser-admin"
    with os.fdopen(
        os.open(signer_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
    ) as key_file:
        key_file.write(
            signer.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.OpenSSH,
                serialization.NoEncryption(),
            )
        )
    owner = GatewayOwner(agent_id=target.agent_id, context_id="browser-fixture")
    gateway_target = GatewayTarget(owner=owner, incarnation=target.generation)
    store = AuthorizationStore(tmp_path / "browser-access", owner)
    store.initialize()
    first_key = GatewayAdminKey(
        principal="browser-admin", public_key=public_key_text(signer.public_key())
    )
    policy = GatewayAccessPolicy(
        store=store,
        target=lambda: gateway_target,
        current_self=lambda: None,
        listener_id="browser-fixture-gateway",
    )
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
        dashboard_runtime = object.__new__(GatewayServiceRuntime)
        dashboard_runtime.m_port = listener.getsockname()[1]
        dashboard_runtime.m_manifest_path = runtime.manifest_path
        manifest = runtime.manifest.model_copy(update={"mode": "tui", "backend": "hermes_tui"})
        monkeypatch.setattr(dashboard_runtime, "_verified_owner_manifest", lambda: manifest)
        monkeypatch.setattr(
            dashboard_runtime,
            "endpoint_descriptor",
            lambda *, read_only: SimpleNamespace(
                target=gateway_target, admin_mode=store.snapshot(read_only=read_only).admin_mode
            ),
        )
        app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None, redirect_slashes=False)
        register_terminal_entry_routes(
            app,
            issuer=lambda: origin,
            listener=lambda: policy.listener_id,
            agent_id=target.agent_id,
            resolve_target=runtime.target,
            policy=lambda: policy,
        )

        @app.get("/", response_class=HTMLResponse)
        def dashboard(request: Request) -> str:
            """Use production dashboard discovery with the fixture's live tmux authority."""

            return dashboard_runtime.dashboard(request)

        @app.get("/health")
        def client_sizes() -> str:
            """Expose native client dimensions on the fixture listener for assertions."""

            return _tmux(
                runtime.socket,
                "list-clients",
                "-t",
                target.session_id,
                "-F",
                "#{client_width}x#{client_height}\t#{client_flags}",
            )

        def admit(
            *,
            request: Request,
            operation: GatewayOperation,
            binding: GatewayRequestBinding,
            proof: dict[str, str],
            body: bytes,
        ) -> GatewayGrant | FirstEnrollment:
            """Use the ordinary signed gateway policy for protected fixture routes."""

            return policy.admit(
                operation.permissions(body),
                issuer=origin,
                request=binding,
                challenge_id=proof.get(CHALLENGE_HEADER),
                signature=proof.get(SIGNATURE_HEADER),
            )

        def enroll_admin() -> None:
            """Prove and enroll the first administrator under the current empty roster."""

            assert store.snapshot().admin_mode == "open"
            assert len(runtime.clients().splitlines()) == 1, "Open browser attach was already gone"
            binding = GatewayRequestBinding.from_request(
                "POST", "/v1/admin/keys", "", first_key.model_dump_json().encode()
            )
            challenge = policy.issue(
                origin,
                GatewayChallengeRequest(
                    purpose="register", request=binding, proposed_key=first_key
                ),
            )
            proof = policy.admit(
                (ADMIN_ADD,),
                issuer=origin,
                request=binding,
                challenge_id=challenge.challenge_id,
                signature=sshsig_header(sign_sshsig(signer, challenge.signing_bytes())),
                registration=True,
            )
            assert isinstance(proof, FirstEnrollment)
            policy.add_key(proof, first_key)
            assert store.snapshot().admin_mode == "keyed"

        validate_core_gateway_routes(list(app.routes))
        plugins = Mock(spec=GatewayPluginHost)
        plugins.route_permission.return_value = None
        app.add_middleware(
            GatewayAdmissionMiddleware,
            gateway=app,
            plugin_host=plugins,
            admit=admit,
            reserve_public_input=Mock(side_effect=AssertionError("Terminal used public input")),
            log_denial=Mock(),
        )
        server = uvicorn.Server(
            uvicorn.Config(app, log_level="error", access_log=False, proxy_headers=False)
        )
        diagnostics = _GatewayErrors()
        gateway_logger = logging.getLogger("uvicorn.error")
        gateway_logger.addHandler(diagnostics)
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.02)
            assert server.started, "Browser fixture failed to start"
            yield _BrowserGateway(origin, signer_path, enroll_admin)
            cleanup_deadline = time.monotonic() + 6
            while runtime.clients() and time.monotonic() < cleanup_deadline:
                time.sleep(0.02)
            assert not runtime.clients(), "A browser attach client survived disconnect"
            assert runtime.target() == target
        finally:
            server.should_exit = True
            thread.join(timeout=6)
            gateway_logger.removeHandler(diagnostics)
            assert not thread.is_alive(), "Browser fixture failed to stop"
        assert not diagnostics.m_errors, diagnostics.m_errors


def test_chromium_renders_and_operates_isolated_terminal(
    browser_gateway: _BrowserGateway, tmp_path: Path
) -> None:
    """Verify open interaction, first enrollment, keyed sign-in, and anonymous viewing."""

    bun = shutil.which("bun")
    if bun is None or shutil.which("ssh-keygen") is None or shutil.which("curl") is None:
        pytest.skip("Bun Playwright, OpenSSH, or curl test tooling is unavailable")
    env = {name: value for name, value in os.environ.items() if name not in {"TMUX", "TMUX_PANE"}}
    driver = Path(__file__).with_name("gateway_terminal_browser_driver.ts")
    ready = tmp_path / "open-terminal-ready"
    deadline = time.monotonic() + 50
    with subprocess.Popen(
        [bun, str(driver), browser_gateway.origin, str(browser_gateway.signer_path), str(ready)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as result:
        try:
            while not ready.is_file() and result.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            if ready.is_file():
                browser_gateway.enroll_admin()
            _, errors = result.communicate(timeout=max(0.1, deadline - time.monotonic()))
        finally:
            if result.poll() is None:
                result.kill()
                result.communicate()
        if result.returncode == 77:
            pytest.skip("The installed Chromium test browser is unavailable")
        assert result.returncode == 0, errors
        assert ready.is_file(), "The anonymous browser never operated the terminal"
