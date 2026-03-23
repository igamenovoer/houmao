"""Integration coverage for server-managed gateway contracts."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import TracebackType
from typing import Any
from urllib.parse import unquote, urlparse

from houmao.agents.realm_controller.backends.headless_base import (
    HeadlessInteractiveSession,
    HeadlessSessionState,
)
from houmao.agents.realm_controller.gateway_models import GatewayMailNotifierPutV1
from houmao.agents.realm_controller.gateway_storage import (
    gateway_paths_from_manifest_path,
    read_pid_file,
)
from houmao.server.config import HoumaoServerConfig
from houmao.server.models import (
    HoumaoHeadlessLaunchMailboxOptions,
    HoumaoHeadlessLaunchRequest,
)
from houmao.server.service import HoumaoServerService, ProxyResponse
from houmao.owned_paths import AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR


def _write(path: Path, text: str) -> None:
    """Write one UTF-8 test fixture file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_brain_manifest(agent_def_dir: Path, tmp_path: Path) -> Path:
    """Create a minimal codex brain manifest and role package."""

    env_file = tmp_path / "vars.env"
    env_file.write_text("OPENAI_API_KEY=secret\n", encoding="utf-8")
    manifest_path = tmp_path / "brain.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                "schema_version: 2",
                "inputs:",
                "  tool: codex",
                "runtime:",
                "  launch_executable: codex",
                "  launch_home_selector:",
                "    env_var: CODEX_HOME",
                f"    value: {tmp_path / 'home'}",
                "  launch_contract:",
                "    adapter_defaults:",
                "      args: []",
                "      tool_params: {}",
                "    requested_overrides:",
                "      recipe: null",
                "      direct: null",
                "    tool_metadata:",
                "      tool_params: {}",
                "credentials:",
                "  env_contract:",
                f"    source_file: {env_file}",
                "    allowlisted_env_vars:",
                "      - OPENAI_API_KEY",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write(agent_def_dir / "roles/r/system-prompt.md", "Role prompt\n")
    return manifest_path


class _FakeTmuxEnv:
    """In-memory tmux environment store for gateway attach tests."""

    def __init__(self) -> None:
        self.m_values: dict[str, dict[str, str]] = {}

    def set_env(self, *, session_name: str, env_vars: dict[str, str]) -> None:
        """Store or update session environment bindings."""

        bindings = self.m_values.setdefault(session_name, {})
        bindings.update(env_vars)

    def unset_env(self, *, session_name: str, variable_names: list[str]) -> None:
        """Remove selected session environment bindings."""

        bindings = self.m_values.setdefault(session_name, {})
        for name in variable_names:
            bindings.pop(name, None)

    def show_env(
        self, *, session_name: str, variable_name: str
    ) -> subprocess.CompletedProcess[str]:
        """Return tmux-style environment output for one variable."""

        value = self.m_values.get(session_name, {}).get(variable_name)
        if value is None:
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="unknown variable",
            )
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=f"{variable_name}={value}\n",
            stderr="",
        )


class _FakeCodexHeadlessSession(HeadlessInteractiveSession):
    """Minimal fake headless backend for server-managed launch integration."""

    def __init__(
        self,
        *,
        launch_plan: Any,
        role_name: str,
        session_manifest_path: Path,
        agent_def_dir: Path | None = None,
        state: HeadlessSessionState | None = None,
        tmux_session_name: str | None = None,
        output_format: str = "stream-json",
    ) -> None:
        del role_name, session_manifest_path, agent_def_dir, output_format
        self.backend = "codex_headless"
        self._plan = launch_plan
        self._state = state or HeadlessSessionState(
            session_id="headless-session-1",
            turn_index=0,
            role_bootstrap_applied=True,
            working_directory=str(launch_plan.working_directory),
            tmux_session_name=tmux_session_name or "AGENTSYS-headless",
        )
        if not self._state.session_id:
            self._state.session_id = "headless-session-1"

    def send_prompt(self, prompt: str):  # type: ignore[no-untyped-def]
        """Record a fake prompt delivery."""

        self._state.turn_index += 1
        del prompt
        return []

    def interrupt(self):  # type: ignore[no-untyped-def]
        """Return a successful fake interrupt result."""

        return type(
            "InterruptResult",
            (),
            {"status": "ok", "action": "interrupt", "detail": "interrupted"},
        )()

    def terminate(self):  # type: ignore[no-untyped-def]
        """Return a successful fake terminate result."""

        return type(
            "TerminateResult",
            (),
            {"status": "ok", "action": "terminate", "detail": "stopped"},
        )()

    def close(self) -> None:
        """Close the fake backend."""

        return None

    def update_launch_plan(self, launch_plan: Any) -> None:
        """Update the fake launch plan."""

        self._plan = launch_plan


class _FakeManagedAgentApiServer(ThreadingHTTPServer):
    """Tiny loopback server exposing managed-agent detail for gateway health."""

    def __init__(self, server_address: tuple[str, int]) -> None:
        super().__init__(server_address, _FakeManagedAgentApiHandler)


class _FakeManagedAgentApiHandler(BaseHTTPRequestHandler):
    """Serve the subset of managed-agent routes used by the gateway."""

    def do_GET(self) -> None:  # noqa: N802
        """Handle fake managed-agent `GET` requests."""

        parsed = urlparse(self.path)
        path_parts = parsed.path.strip("/").split("/")
        if (
            len(path_parts) == 5
            and path_parts[0] == "houmao"
            and path_parts[1] == "agents"
            and path_parts[3] == "state"
            and path_parts[4] == "detail"
        ):
            agent_ref = unquote(path_parts[2])
            payload = _managed_agent_detail_payload(agent_ref)
            self._send_json(HTTPStatus.OK, payload)
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"detail": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        """Handle fake managed-agent `POST` requests."""

        parsed = urlparse(self.path)
        path_parts = parsed.path.strip("/").split("/")
        if (
            len(path_parts) == 4
            and path_parts[0] == "houmao"
            and path_parts[1] == "agents"
            and path_parts[3] == "requests"
        ):
            agent_ref = unquote(path_parts[2])
            self._send_json(
                HTTPStatus.OK,
                {
                    "success": True,
                    "tracked_agent_id": agent_ref,
                    "request_id": "mreq-1",
                    "request_kind": "submit_prompt",
                    "disposition": "accepted",
                    "detail": "accepted",
                    "headless_turn_id": None,
                    "headless_turn_index": None,
                },
            )
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"detail": "not found"})

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        """Silence request logging during tests."""

        del format, args
        return

    def _send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        """Send one JSON response body."""

        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class _ManagedAgentApiServer:
    """Context-managed fake managed-agent API server."""

    def __init__(self) -> None:
        self.m_server = _FakeManagedAgentApiServer(("127.0.0.1", 0))
        self.m_port = int(self.m_server.server_address[1])
        self.m_thread = threading.Thread(
            target=self.m_server.serve_forever,
            name="fake-managed-agent-api",
            daemon=True,
        )

    @property
    def base_url(self) -> str:
        """Return the loopback base URL for the fake managed-agent API."""

        return f"http://127.0.0.1:{self.m_port}"

    def __enter__(self) -> "_ManagedAgentApiServer":
        """Start the fake managed-agent API server."""

        self.m_thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Stop the fake managed-agent API server."""

        del exc_type, exc, tb
        self.m_server.shutdown()
        self.m_server.server_close()
        self.m_thread.join(timeout=2.0)


class _NoopTransport:
    """Transport stub for service integration tests."""

    def request(
        self,
        *,
        base_url: str,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
    ) -> ProxyResponse:
        """Reject unexpected transport calls."""

        del base_url, method, path, params
        raise AssertionError(
            "Unexpected transport request in managed-agent gateway integration test."
        )


class _NoopChildManager:
    """Child-manager stub for service integration tests."""

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def inspect(self) -> object:
        config = type("Config", (), {"base_url": "http://127.0.0.1:9890"})()
        status = type(
            "Status",
            (),
            {
                "healthy": True,
                "health_status": "ok",
                "service": "cli-agent-orchestrator",
                "error": None,
            },
        )()
        return type("Inspection", (), {"config": config, "status": status})()

    def ownership_file_path(self) -> Path:
        return Path("/tmp/houmao-server-integration-no-ownership")


def _managed_agent_detail_payload(agent_ref: str) -> dict[str, object]:
    """Return one managed-agent detail payload for the fake server."""

    identity = {
        "tracked_agent_id": agent_ref,
        "transport": "headless",
        "tool": "codex",
        "session_name": None,
        "terminal_id": None,
        "runtime_session_id": agent_ref,
        "tmux_session_name": "AGENTSYS-headless",
        "tmux_window_name": "agent",
        "manifest_path": "/tmp/manifest.json",
        "session_root": "/tmp/session-root",
        "agent_name": "AGENTSYS-headless",
        "agent_id": None,
    }
    summary_state = {
        "tracked_agent_id": agent_ref,
        "identity": identity,
        "availability": "available",
        "turn": {"phase": "ready", "active_turn_id": None},
        "last_turn": {
            "result": "none",
            "turn_id": None,
            "turn_index": None,
            "updated_at_utc": None,
        },
        "diagnostics": [],
        "mailbox": None,
        "gateway": None,
    }
    detail = {
        "transport": "headless",
        "runtime_resumable": True,
        "tmux_session_live": True,
        "can_accept_prompt_now": True,
        "interruptible": False,
        "turn": {"phase": "ready", "active_turn_id": None},
        "last_turn": {
            "result": "none",
            "turn_id": None,
            "turn_index": None,
            "updated_at_utc": None,
        },
        "active_turn_started_at_utc": None,
        "active_turn_interrupt_requested_at_utc": None,
        "last_turn_status": None,
        "last_turn_started_at_utc": None,
        "last_turn_completed_at_utc": None,
        "last_turn_completion_source": None,
        "last_turn_returncode": None,
        "last_turn_history_summary": None,
        "last_turn_error": None,
        "mailbox": None,
        "gateway": None,
        "diagnostics": [],
    }
    return {
        "tracked_agent_id": agent_ref,
        "identity": identity,
        "summary_state": summary_state,
        "detail": detail,
    }


def _install_runtime_headless_fakes(
    *,
    monkeypatch: Any,
    tmux_env: _FakeTmuxEnv,
    registry_root: Path,
) -> None:
    """Install fake headless runtime and tmux environment hooks."""

    monkeypatch.setenv(AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root.resolve()))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.CodexHeadlessSession",
        _FakeCodexHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        tmux_env.set_env,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.unset_tmux_session_environment_shared",
        tmux_env.unset_env,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.show_tmux_environment_shared",
        tmux_env.show_env,
    )


def _best_effort_cleanup_gateway(manifest_path: Path) -> None:
    """Terminate any still-running gateway process for the addressed session."""

    paths = gateway_paths_from_manifest_path(manifest_path)
    if paths is None:
        return
    pid = read_pid_file(paths.pid_path)
    if pid is None:
        return
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        return
    time.sleep(0.1)


def test_server_managed_gateway_attach_is_idempotent_and_projects_notifier_control(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    """Server-managed attach should be idempotent and notifier control should proxy live gateway state."""

    agent_def_dir = tmp_path / "repo"
    mailbox_root = tmp_path / "mailbox"
    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)
    tmux_env = _FakeTmuxEnv()
    _install_runtime_headless_fakes(
        monkeypatch=monkeypatch,
        tmux_env=tmux_env,
        registry_root=tmp_path / "registry",
    )

    with _ManagedAgentApiServer() as managed_api:
        service = HoumaoServerService(
            config=HoumaoServerConfig(
                api_base_url=managed_api.base_url,
                runtime_root=tmp_path,
                startup_child=False,
            ),
            transport=_NoopTransport(),
            child_manager=_NoopChildManager(),
        )
        assert service.health_response().child_cao is None
        assert service.current_instance_response().child_cao is None

        response = service.launch_headless_agent(
            HoumaoHeadlessLaunchRequest(
                tool="codex",
                working_directory=str(tmp_path.resolve()),
                agent_def_dir=str(agent_def_dir.resolve()),
                brain_manifest_path=str(brain_manifest_path.resolve()),
                role_name="r",
                agent_name="AGENTSYS-headless",
                agent_id=None,
                mailbox=HoumaoHeadlessLaunchMailboxOptions(
                    transport="filesystem",
                    filesystem_root=str(mailbox_root.resolve()),
                    address="AGENTSYS-headless@agents.localhost",
                ),
            )
        )

        manifest_path = Path(response.manifest_path)
        paths = gateway_paths_from_manifest_path(manifest_path)
        assert paths is not None

        try:
            first_status = service.attach_managed_agent_gateway(response.tracked_agent_id)
            assert first_status.gateway_health == "healthy"
            assert first_status.gateway_host == "127.0.0.1"
            assert first_status.gateway_port is not None
            first_pid = read_pid_file(paths.pid_path)
            assert first_pid is not None

            second_status = service.attach_managed_agent_gateway(response.tracked_agent_id)
            assert second_status.gateway_health == "healthy"
            assert second_status.gateway_host == first_status.gateway_host
            assert second_status.gateway_port == first_status.gateway_port
            second_pid = read_pid_file(paths.pid_path)
            assert second_pid == first_pid

            initial_notifier = service.get_managed_agent_gateway_mail_notifier(
                response.tracked_agent_id
            )
            assert initial_notifier.supported is True
            assert initial_notifier.enabled is False

            enabled_notifier = service.put_managed_agent_gateway_mail_notifier(
                response.tracked_agent_id,
                GatewayMailNotifierPutV1(interval_seconds=60),
            )
            assert enabled_notifier.supported is True
            assert enabled_notifier.enabled is True
            assert enabled_notifier.interval_seconds == 60

            disabled_notifier = service.delete_managed_agent_gateway_mail_notifier(
                response.tracked_agent_id
            )
            assert disabled_notifier.supported is True
            assert disabled_notifier.enabled is False
        finally:
            try:
                service.detach_managed_agent_gateway(response.tracked_agent_id)
            finally:
                _best_effort_cleanup_gateway(manifest_path)
