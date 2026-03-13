"""Integration coverage for the runtime-owned agent gateway contract."""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import threading
import time
from dataclasses import replace
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, cast
from urllib.parse import parse_qs, urlparse

import pytest

from gig_agents.agents.brain_launch_runtime import cli
from gig_agents.agents.brain_launch_runtime.backends.cao_rest import CaoSessionState
from gig_agents.agents.brain_launch_runtime.gateway_storage import (
    AGENT_GATEWAY_HOST_ENV_VAR,
    AGENT_GATEWAY_PORT_ENV_VAR,
    AGENT_GATEWAY_PROTOCOL_VERSION_ENV_VAR,
    AGENT_GATEWAY_STATE_PATH_ENV_VAR,
    gateway_paths_from_manifest_path,
    load_gateway_status,
    read_pid_file,
)
from gig_agents.agents.brain_launch_runtime.models import SessionControlResult, SessionEvent


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
                "inputs:",
                "  tool: codex",
                "runtime:",
                "  launch_executable: codex",
                "  launch_args: []",
                "  launch_home_selector:",
                "    env_var: CODEX_HOME",
                f"    value: {tmp_path / 'home'}",
                "  cao_parsing_mode: shadow_only",
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


def _pick_unused_loopback_port() -> int:
    """Return one currently free loopback port."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_until(
    predicate: Callable[[], bool],
    *,
    timeout_seconds: float = 5.0,
    interval_seconds: float = 0.05,
) -> None:
    """Poll until a predicate succeeds or the timeout elapses."""

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(interval_seconds)
    raise AssertionError("Timed out waiting for condition.")


def _run_cli_json(
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
) -> tuple[int, dict[str, Any], str]:
    """Run the CLI and parse one JSON object from stdout."""

    exit_code = cli.main(argv)
    captured = capsys.readouterr()
    payload = json.loads(captured.out) if captured.out.strip() else {}
    return exit_code, cast(dict[str, Any], payload), captured.err


def _run_cli_events(
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
) -> tuple[int, list[dict[str, Any]], str]:
    """Run the CLI and parse newline-delimited JSON events from stdout."""

    exit_code = cli.main(argv)
    captured = capsys.readouterr()
    payload = [
        cast(dict[str, Any], json.loads(line)) for line in captured.out.splitlines() if line.strip()
    ]
    return exit_code, payload, captured.err


def _rewrite_manifest_terminal_id(manifest_path: Path, *, terminal_id: str) -> None:
    """Replace the persisted CAO terminal id in both manifest locations."""

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["backend_state"]["terminal_id"] = terminal_id
    payload["cao"]["terminal_id"] = terminal_id
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class _FakeTmuxEnv:
    """In-memory tmux environment store for manifest-path control tests."""

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

    def get(self, *, session_name: str, variable_name: str) -> str | None:
        """Return one stored variable when present."""

        return self.m_values.get(session_name, {}).get(variable_name)


class _FakeCaoSessionRegistry:
    """Shared fake backend state across repeated start and resume calls."""

    def __init__(self, *, api_base_url: str, terminal_id: str) -> None:
        self.m_api_base_url = api_base_url
        self.m_terminal_id = terminal_id
        self.m_session_name = "AGENTSYS-gateway"
        self.m_profile_name = "runtime-profile"
        self.m_profile_path = str(Path("/tmp/runtime-profile.md"))
        self.m_direct_prompts: list[str] = []
        self.m_terminated = False

    def build_state(self, *, parsing_mode: str) -> CaoSessionState:
        """Build the persisted CAO state used by the fake session."""

        return CaoSessionState(
            api_base_url=self.m_api_base_url,
            session_name=self.m_session_name,
            terminal_id=self.m_terminal_id,
            profile_name=self.m_profile_name,
            profile_path=self.m_profile_path,
            parsing_mode=cast(Any, parsing_mode),
            tmux_window_name="developer-1",
            turn_index=0,
        )


class _FakeCaoRestSession:
    """Minimal fake `cao_rest` session for runtime and CLI integration tests."""

    m_registry: _FakeCaoSessionRegistry | None = None

    def __init__(
        self,
        *,
        launch_plan: Any,
        api_base_url: str,
        role_name: str,
        role_prompt: str,
        parsing_mode: str,
        session_manifest_path: Path | None = None,
        agent_def_dir: Path | None = None,
        agent_identity: str | None = None,
        profile_store_dir: Path | None = None,
        poll_interval_seconds: float = 0.4,
        timeout_seconds: float = 120.0,
        prepend_role_text: str | None = None,
        append_role_text: str | None = None,
        substitutions: dict[str, str] | None = None,
        existing_state: CaoSessionState | None = None,
    ) -> None:
        del (
            api_base_url,
            role_name,
            role_prompt,
            session_manifest_path,
            agent_def_dir,
            agent_identity,
            profile_store_dir,
            poll_interval_seconds,
            timeout_seconds,
            prepend_role_text,
            append_role_text,
            substitutions,
        )
        registry = type(self).m_registry
        if registry is None:
            raise AssertionError("Fake CAO registry is not configured.")
        self.m_registry = registry
        self.m_launch_plan = launch_plan
        self.m_state = existing_state or registry.build_state(parsing_mode=parsing_mode)

    @property
    def state(self) -> CaoSessionState:
        """Return the persisted fake CAO state."""

        return self.m_state

    @property
    def startup_warnings(self) -> tuple[str, ...]:
        """Return synthetic startup warnings."""

        return ()

    def update_launch_plan(self, launch_plan: Any) -> None:
        """Update the launch plan during controller persistence flows."""

        self.m_launch_plan = launch_plan

    def send_prompt(self, prompt: str) -> list[SessionEvent]:
        """Record a direct prompt submission without using the gateway."""

        self.m_registry.m_direct_prompts.append(prompt)
        self.m_state = replace(self.m_state, turn_index=self.m_state.turn_index + 1)
        return [
            SessionEvent(
                kind="assistant",
                message=f"direct:{prompt}",
                turn_index=self.m_state.turn_index,
            )
        ]

    def interrupt(self) -> SessionControlResult:
        """Return a successful direct interrupt result."""

        return SessionControlResult(status="ok", action="interrupt", detail="interrupted")

    def terminate(self) -> SessionControlResult:
        """Record session termination."""

        self.m_registry.m_terminated = True
        return SessionControlResult(status="ok", action="terminate", detail="stopped")

    def close(self) -> None:
        """Close the fake session."""

        return


class _FakeCaoApiState:
    """Thread-safe state for the fake CAO HTTP server."""

    def __init__(self, *, terminal_id: str) -> None:
        self.m_terminal_id = terminal_id
        self.m_messages: list[tuple[str, str]] = []
        self.m_interrupt_count = 0
        self.m_lock = threading.Lock()

    def current_terminal_id(self) -> str:
        """Return the current terminal id."""

        with self.m_lock:
            return self.m_terminal_id

    def set_terminal_id(self, terminal_id: str) -> None:
        """Replace the current terminal id."""

        with self.m_lock:
            self.m_terminal_id = terminal_id

    def record_message(self, *, terminal_id: str, message: str) -> None:
        """Record one prompt delivery."""

        with self.m_lock:
            self.m_messages.append((terminal_id, message))

    def record_interrupt(self) -> None:
        """Record one interrupt delivery."""

        with self.m_lock:
            self.m_interrupt_count += 1

    def messages(self) -> list[tuple[str, str]]:
        """Return a snapshot of recorded prompt deliveries."""

        with self.m_lock:
            return list(self.m_messages)

    def interrupt_count(self) -> int:
        """Return the number of recorded interrupts."""

        with self.m_lock:
            return self.m_interrupt_count


class _FakeCaoHttpServer(ThreadingHTTPServer):
    """HTTP server with attached fake CAO state."""

    def __init__(
        self,
        server_address: tuple[str, int],
        state: _FakeCaoApiState,
    ) -> None:
        self.m_state = state
        super().__init__(server_address, _FakeCaoRequestHandler)


class _FakeCaoRequestHandler(BaseHTTPRequestHandler):
    """Expose the tiny subset of CAO endpoints used by the gateway."""

    def do_GET(self) -> None:  # noqa: N802
        """Handle fake CAO `GET` requests."""

        parsed = urlparse(self.path)
        path_parts = parsed.path.strip("/").split("/")
        state = cast(_FakeCaoApiState, cast(_FakeCaoHttpServer, self.server).m_state)
        if len(path_parts) == 2 and path_parts[0] == "terminals":
            terminal_id = path_parts[1]
            if terminal_id != state.current_terminal_id():
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"detail": f"terminal `{terminal_id}` not found"},
                )
                return
            self._send_json(
                HTTPStatus.OK,
                {
                    "id": terminal_id,
                    "name": "developer-1",
                    "provider": "codex",
                    "session_name": "AGENTSYS-gateway",
                    "agent_profile": "runtime-profile",
                    "status": "idle",
                },
            )
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"detail": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        """Handle fake CAO `POST` requests."""

        parsed = urlparse(self.path)
        path_parts = parsed.path.strip("/").split("/")
        query = parse_qs(parsed.query)
        state = cast(_FakeCaoApiState, cast(_FakeCaoHttpServer, self.server).m_state)
        if len(path_parts) == 3 and path_parts[0] == "terminals" and path_parts[2] == "input":
            terminal_id = path_parts[1]
            message = query.get("message", [""])[0]
            state.record_message(terminal_id=terminal_id, message=message)
            self._send_json(HTTPStatus.OK, {"success": True})
            return
        if len(path_parts) == 3 and path_parts[0] == "terminals" and path_parts[2] == "exit":
            state.record_interrupt()
            self._send_json(HTTPStatus.OK, {"success": True})
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


class _FakeCaoServer:
    """Context-managed fake CAO server used by the gateway integration tests."""

    def __init__(self, *, terminal_id: str) -> None:
        self.m_state = _FakeCaoApiState(terminal_id=terminal_id)
        self.m_port = _pick_unused_loopback_port()
        self.m_server = _FakeCaoHttpServer(("127.0.0.1", self.m_port), self.m_state)
        self.m_thread = threading.Thread(
            target=self.m_server.serve_forever,
            name="fake-cao-server",
            daemon=True,
        )

    @property
    def base_url(self) -> str:
        """Return the loopback base URL for the fake CAO server."""

        return f"http://127.0.0.1:{self.m_port}"

    def __enter__(self) -> "_FakeCaoServer":
        """Start the fake CAO server."""

        self.m_thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Stop the fake CAO server."""

        del exc_type, exc, tb
        self.m_server.shutdown()
        self.m_server.server_close()
        self.m_thread.join(timeout=2.0)

    def set_terminal_id(self, terminal_id: str) -> None:
        """Replace the current terminal id reported by the fake server."""

        self.m_state.set_terminal_id(terminal_id)

    def messages(self) -> list[tuple[str, str]]:
        """Return recorded prompt deliveries."""

        return self.m_state.messages()

    def interrupt_count(self) -> int:
        """Return recorded interrupt deliveries."""

        return self.m_state.interrupt_count()


def _install_gateway_runtime_fakes(
    *,
    monkeypatch: pytest.MonkeyPatch,
    registry: _FakeCaoSessionRegistry,
    tmux_env: _FakeTmuxEnv,
) -> None:
    """Install fake CAO session and tmux environment hooks."""

    _FakeCaoRestSession.m_registry = registry
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.runtime.CaoRestSession",
        _FakeCaoRestSession,
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.runtime.set_tmux_session_environment_shared",
        tmux_env.set_env,
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.runtime.unset_tmux_session_environment_shared",
        tmux_env.unset_env,
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.runtime.show_tmux_environment_shared",
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


def test_start_session_reports_partial_gateway_auto_attach_failure_on_bind_conflict(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Launch-time auto-attach should keep the session alive on bind conflicts."""

    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)

    with _FakeCaoServer(terminal_id="term-1") as fake_cao:
        registry = _FakeCaoSessionRegistry(api_base_url=fake_cao.base_url, terminal_id="term-1")
        tmux_env = _FakeTmuxEnv()
        _install_gateway_runtime_fakes(
            monkeypatch=monkeypatch,
            registry=registry,
            tmux_env=tmux_env,
        )

        conflict_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conflict_socket.bind(("127.0.0.1", 0))
        conflict_socket.listen(1)
        conflict_port = int(conflict_socket.getsockname()[1])
        try:
            exit_code, payload, err = _run_cli_json(
                capsys,
                [
                    "start-session",
                    "--agent-def-dir",
                    str(agent_def_dir),
                    "--runtime-root",
                    str(runtime_root),
                    "--brain-manifest",
                    str(brain_manifest_path),
                    "--role",
                    "r",
                    "--backend",
                    "cao_rest",
                    "--workdir",
                    str(tmp_path),
                    "--cao-base-url",
                    fake_cao.base_url,
                    "--gateway-auto-attach",
                    "--gateway-host",
                    "127.0.0.1",
                    "--gateway-port",
                    str(conflict_port),
                ],
            )
        finally:
            conflict_socket.close()

        assert exit_code == 2
        assert err == ""
        assert "gateway_auto_attach_error" in payload
        assert "already in use" in str(payload["gateway_auto_attach_error"])

        manifest_path = Path(str(payload["session_manifest"]))
        assert manifest_path.is_file()
        assert Path(str(payload["gateway_root"])).is_dir()
        assert Path(str(payload["gateway_attach_path"])).is_file()

        direct_exit, direct_events, direct_err = _run_cli_events(
            capsys,
            [
                "send-prompt",
                "--agent-def-dir",
                str(agent_def_dir),
                "--agent-identity",
                str(manifest_path),
                "--prompt",
                "still-running",
            ],
        )
        assert direct_exit == 0
        assert direct_err == ""
        assert direct_events[-1]["message"] == "direct:still-running"
        assert registry.m_direct_prompts == ["still-running"]


def test_gateway_cli_contract_covers_attach_control_detach_replacement_and_stop(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """The gateway CLI contract should cover attach, control, detach, and stop flows."""

    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)

    with _FakeCaoServer(terminal_id="term-1") as fake_cao:
        registry = _FakeCaoSessionRegistry(api_base_url=fake_cao.base_url, terminal_id="term-1")
        tmux_env = _FakeTmuxEnv()
        _install_gateway_runtime_fakes(
            monkeypatch=monkeypatch,
            registry=registry,
            tmux_env=tmux_env,
        )

        start_exit, start_payload, start_err = _run_cli_json(
            capsys,
            [
                "start-session",
                "--agent-def-dir",
                str(agent_def_dir),
                "--runtime-root",
                str(runtime_root),
                "--brain-manifest",
                str(brain_manifest_path),
                "--role",
                "r",
                "--backend",
                "cao_rest",
                "--workdir",
                str(tmp_path),
                "--cao-base-url",
                fake_cao.base_url,
            ],
        )
        assert start_exit == 0
        assert start_err == ""

        manifest_path = Path(str(start_payload["session_manifest"]))
        session_name = registry.m_session_name
        paths = gateway_paths_from_manifest_path(manifest_path)
        assert paths is not None

        try:
            offline_exit, offline_status, offline_err = _run_cli_json(
                capsys,
                [
                    "gateway-status",
                    "--agent-def-dir",
                    str(agent_def_dir),
                    "--agent-identity",
                    str(manifest_path),
                ],
            )
            assert offline_exit == 0
            assert offline_err == ""
            assert offline_status["gateway_health"] == "not_attached"

            direct_exit, direct_events, direct_err = _run_cli_events(
                capsys,
                [
                    "send-prompt",
                    "--agent-def-dir",
                    str(agent_def_dir),
                    "--agent-identity",
                    str(manifest_path),
                    "--prompt",
                    "legacy-direct",
                ],
            )
            assert direct_exit == 0
            assert direct_err == ""
            assert direct_events[-1]["message"] == "direct:legacy-direct"
            assert registry.m_direct_prompts == ["legacy-direct"]

            attach_exit, attach_payload, attach_err = _run_cli_json(
                capsys,
                [
                    "attach-gateway",
                    "--agent-def-dir",
                    str(agent_def_dir),
                    "--agent-identity",
                    str(manifest_path),
                    "--gateway-host",
                    "127.0.0.1",
                ],
            )
            assert attach_exit == 0
            assert attach_err == ""
            assert attach_payload["status"] == "ok"
            attach_port = int(attach_payload["gateway_port"])
            assert attach_port > 0
            assert tmux_env.get(session_name=session_name, variable_name=AGENT_GATEWAY_HOST_ENV_VAR)
            assert tmux_env.get(
                session_name=session_name, variable_name=AGENT_GATEWAY_PORT_ENV_VAR
            ) == str(attach_port)

            live_exit, live_status, live_err = _run_cli_json(
                capsys,
                [
                    "gateway-status",
                    "--agent-def-dir",
                    str(agent_def_dir),
                    "--agent-identity",
                    str(manifest_path),
                ],
            )
            assert live_exit == 0
            assert live_err == ""
            assert live_status["gateway_health"] == "healthy"
            assert live_status["request_admission"] == "open"
            assert live_status["gateway_port"] == attach_port
            assert live_status["managed_agent_instance_epoch"] == 1

            prompt_exit, prompt_payload, prompt_err = _run_cli_json(
                capsys,
                [
                    "gateway-send-prompt",
                    "--agent-def-dir",
                    str(agent_def_dir),
                    "--agent-identity",
                    str(manifest_path),
                    "--prompt",
                    "via-gateway",
                ],
            )
            assert prompt_exit == 0
            assert prompt_err == ""
            assert prompt_payload["request_kind"] == "submit_prompt"
            _wait_until(lambda: fake_cao.messages() == [("term-1", "via-gateway")])

            interrupt_exit, interrupt_payload, interrupt_err = _run_cli_json(
                capsys,
                [
                    "gateway-interrupt",
                    "--agent-def-dir",
                    str(agent_def_dir),
                    "--agent-identity",
                    str(manifest_path),
                ],
            )
            assert interrupt_exit == 0
            assert interrupt_err == ""
            assert interrupt_payload["request_kind"] == "interrupt"
            _wait_until(lambda: fake_cao.interrupt_count() == 1)

            detach_exit, detach_payload, detach_err = _run_cli_json(
                capsys,
                [
                    "detach-gateway",
                    "--agent-def-dir",
                    str(agent_def_dir),
                    "--agent-identity",
                    str(manifest_path),
                ],
            )
            assert detach_exit == 0
            assert detach_err == ""
            assert detach_payload["status"] == "ok"
            assert (
                tmux_env.get(session_name=session_name, variable_name=AGENT_GATEWAY_HOST_ENV_VAR)
                is None
            )

            detached_exit, detached_status, detached_err = _run_cli_json(
                capsys,
                [
                    "gateway-status",
                    "--agent-def-dir",
                    str(agent_def_dir),
                    "--agent-identity",
                    str(manifest_path),
                ],
            )
            assert detached_exit == 0
            assert detached_err == ""
            assert detached_status["gateway_health"] == "not_attached"

            reattach_exit, reattach_payload, reattach_err = _run_cli_json(
                capsys,
                [
                    "attach-gateway",
                    "--agent-def-dir",
                    str(agent_def_dir),
                    "--agent-identity",
                    str(manifest_path),
                ],
            )
            assert reattach_exit == 0
            assert reattach_err == ""
            assert reattach_payload["status"] == "ok"
            assert reattach_payload["gateway_port"] == attach_port
            _rewrite_manifest_terminal_id(manifest_path, terminal_id="term-2")
            fake_cao.set_terminal_id("term-2")

            blocked_exit, blocked_status, blocked_err = _run_cli_json(
                capsys,
                [
                    "gateway-status",
                    "--agent-def-dir",
                    str(agent_def_dir),
                    "--agent-identity",
                    str(manifest_path),
                ],
            )
            assert blocked_exit == 0
            assert blocked_err == ""
            assert blocked_status["request_admission"] == "blocked_reconciliation"
            assert blocked_status["managed_agent_instance_epoch"] == 2

            denied_exit = cli.main(
                [
                    "gateway-send-prompt",
                    "--agent-def-dir",
                    str(agent_def_dir),
                    "--agent-identity",
                    str(manifest_path),
                    "--prompt",
                    "blocked",
                ]
            )
            denied_output = capsys.readouterr()
            assert denied_exit == 2
            assert denied_output.out == ""
            assert "status=409" in denied_output.err
            assert "reconciliation" in denied_output.err

            stop_exit, stop_payload, stop_err = _run_cli_json(
                capsys,
                [
                    "stop-session",
                    "--agent-def-dir",
                    str(agent_def_dir),
                    "--agent-identity",
                    str(manifest_path),
                ],
            )
            assert stop_exit == 0
            assert stop_err == ""
            assert stop_payload["status"] == "ok"
            assert registry.m_terminated is True
            assert (
                tmux_env.get(session_name=session_name, variable_name=AGENT_GATEWAY_HOST_ENV_VAR)
                is None
            )

            persisted_status = load_gateway_status(paths.state_path)
            assert persisted_status.gateway_health == "not_attached"
            assert persisted_status.request_admission == "blocked_unavailable"
        finally:
            _best_effort_cleanup_gateway(manifest_path)


def test_gateway_status_cleans_up_stale_live_bindings_after_gateway_crash(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Gateway status should clear stale live bindings after an external crash."""

    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)

    with _FakeCaoServer(terminal_id="term-1") as fake_cao:
        registry = _FakeCaoSessionRegistry(api_base_url=fake_cao.base_url, terminal_id="term-1")
        tmux_env = _FakeTmuxEnv()
        _install_gateway_runtime_fakes(
            monkeypatch=monkeypatch,
            registry=registry,
            tmux_env=tmux_env,
        )

        start_exit, start_payload, start_err = _run_cli_json(
            capsys,
            [
                "start-session",
                "--agent-def-dir",
                str(agent_def_dir),
                "--runtime-root",
                str(runtime_root),
                "--brain-manifest",
                str(brain_manifest_path),
                "--role",
                "r",
                "--backend",
                "cao_rest",
                "--workdir",
                str(tmp_path),
                "--cao-base-url",
                fake_cao.base_url,
            ],
        )
        assert start_exit == 0
        assert start_err == ""

        manifest_path = Path(str(start_payload["session_manifest"]))
        session_name = registry.m_session_name
        paths = gateway_paths_from_manifest_path(manifest_path)
        assert paths is not None

        try:
            attach_exit, attach_payload, attach_err = _run_cli_json(
                capsys,
                [
                    "attach-gateway",
                    "--agent-def-dir",
                    str(agent_def_dir),
                    "--agent-identity",
                    str(manifest_path),
                    "--gateway-port",
                    str(_pick_unused_loopback_port()),
                ],
            )
            assert attach_exit == 0
            assert attach_err == ""
            assert attach_payload["status"] == "ok"

            gateway_pid = read_pid_file(paths.pid_path)
            assert gateway_pid is not None
            os.kill(gateway_pid, signal.SIGKILL)
            time.sleep(0.2)

            status_exit, status_payload, status_err = _run_cli_json(
                capsys,
                [
                    "gateway-status",
                    "--agent-def-dir",
                    str(agent_def_dir),
                    "--agent-identity",
                    str(manifest_path),
                ],
            )
            assert status_exit == 0
            assert status_err == ""
            assert status_payload["gateway_health"] == "not_attached"
            assert (
                tmux_env.get(session_name=session_name, variable_name=AGENT_GATEWAY_HOST_ENV_VAR)
                is None
            )
            assert (
                tmux_env.get(
                    session_name=session_name, variable_name=AGENT_GATEWAY_STATE_PATH_ENV_VAR
                )
                is None
            )
            assert (
                tmux_env.get(session_name=session_name, variable_name=AGENT_GATEWAY_PORT_ENV_VAR)
                is None
            )
            assert (
                tmux_env.get(
                    session_name=session_name,
                    variable_name=AGENT_GATEWAY_PROTOCOL_VERSION_ENV_VAR,
                )
                is None
            )
        finally:
            _best_effort_cleanup_gateway(manifest_path)
