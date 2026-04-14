"""Integration coverage for the runtime-owned agent gateway contract."""

from __future__ import annotations

import json
import os
import signal
import socket
import sqlite3
import subprocess
import threading
import time
from dataclasses import replace
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, cast
from urllib import request
from urllib.parse import parse_qs, urlparse

import pytest

from houmao.agents.realm_controller import cli
from houmao.agents.realm_controller.backends.cao_rest import CaoSessionState
from houmao.agents.realm_controller.backends.headless_base import (
    HeadlessInteractiveSession,
    HeadlessSessionState,
)
from houmao.agents.realm_controller.gateway_storage import (
    AGENT_GATEWAY_HOST_ENV_VAR,
    AGENT_GATEWAY_PORT_ENV_VAR,
    AGENT_GATEWAY_PROTOCOL_VERSION_ENV_VAR,
    AGENT_GATEWAY_STATE_PATH_ENV_VAR,
    gateway_paths_from_manifest_path,
    read_gateway_notifier_audit_records,
    read_pid_file,
    write_gateway_desired_config,
)
from houmao.agents.realm_controller.gateway_client import GatewayClient, GatewayEndpoint
from houmao.agents.realm_controller.gateway_models import (
    GatewayDesiredConfigV1,
    GatewayMailMessageRequestV1,
    GatewayMailNotifierPutV1,
    GatewayReminderCreateBatchV1,
    GatewayReminderDefinitionV1,
    GatewayReminderSendKeysV1,
)
from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime
from houmao.agents.realm_controller.models import SessionControlResult, SessionEvent
from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox
from houmao.mailbox.filesystem import resolve_active_mailbox_local_sqlite_path
from houmao.mailbox.managed import DeliveryRequest, deliver_message
from houmao.mailbox.protocol import MailboxMessage, serialize_message_document
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR


def _write(path: Path, text: str) -> None:
    """Write one UTF-8 test fixture file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_brain_manifest(agent_def_dir: Path, tmp_path: Path) -> Path:
    """Create a minimal codex brain manifest and role package."""

    home_path = tmp_path / "home"
    home_path.mkdir(parents=True, exist_ok=True)
    (home_path / "auth.json").write_text('{"session_id":"test-session"}\n', encoding="utf-8")
    env_file = tmp_path / "vars.env"
    env_file.write_text("OPENAI_API_KEY=secret\n", encoding="utf-8")
    manifest_path = tmp_path / "brain.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                "schema_version: 3",
                "inputs:",
                "  tool: codex",
                "  skills: []",
                "  setup: default",
                "  auth: default",
                "  adapter_path: /tmp/tool-adapter.yaml",
                "  preset_path: null",
                "launch_policy:",
                "  operator_prompt_mode: as_is",
                "runtime:",
                f"  runtime_root: {tmp_path}",
                "  home_id: test-home",
                f"  home_path: {home_path}",
                f"  launch_helper: {home_path / 'launch.sh'}",
                "  launch_executable: codex",
                "  launch_home_selector:",
                "    env_var: CODEX_HOME",
                f"    value: {home_path}",
                "  launch_contract:",
                "    adapter_defaults:",
                "      args: []",
                "      tool_params: {}",
                "    requested_overrides:",
                "      preset: null",
                "      direct: null",
                "    tool_metadata:",
                "      tool_params: {}",
                "    construction_provenance:",
                "      adapter_path: /tmp/tool-adapter.yaml",
                "      preset_path: null",
                "      preset_overrides_present: false",
                "      direct_overrides_present: false",
                "  cao_parsing_mode: shadow_only",
                "credentials:",
                f"  auth_path: {tmp_path / 'auth'}",
                "  projected_files: []",
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


def _seed_gateway_defaults_blueprint(
    agent_def_dir: Path,
    *,
    port: int,
) -> Path:
    """Create one blueprint that carries persisted gateway listener defaults."""

    blueprint_path = agent_def_dir / "gpu-blueprint.yaml"
    blueprint_path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "name: gpu",
                "role: r",
                "brain_recipe: recipes/gpu.yaml",
                "gateway:",
                "  host: 127.0.0.1",
                f"  port: {port}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return blueprint_path


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


def _deliver_unread_mailbox_message(
    mailbox_root: Path,
    *,
    message_id: str,
    recipient_principal_id: str,
    recipient_address: str,
) -> str:
    """Deliver one unread filesystem mailbox message for gateway notifier tests."""

    sender = MailboxPrincipal(
        principal_id="HOUMAO-sender",
        address="HOUMAO-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id=recipient_principal_id,
        address=recipient_address,
    )
    bootstrap_filesystem_mailbox(mailbox_root, principal=sender)
    bootstrap_filesystem_mailbox(mailbox_root, principal=recipient)

    staged_message = mailbox_root / "staging" / f"{message_id}.md"
    request = DeliveryRequest.from_payload(
        {
            "staged_message_path": str(staged_message),
            "message_id": message_id,
            "thread_id": message_id,
            "in_reply_to": None,
            "references": [],
            "created_at_utc": "2026-03-16T09:00:00Z",
            "sender": {
                "principal_id": sender.principal_id,
                "address": sender.address,
            },
            "to": [
                {
                    "principal_id": recipient_principal_id,
                    "address": recipient_address,
                }
            ],
            "cc": [],
            "reply_to": [],
            "subject": "Gateway notifier integration message",
            "attachments": [],
            "headers": {},
        }
    )
    message = MailboxMessage(
        message_id=request.message_id,
        thread_id=request.thread_id,
        in_reply_to=request.in_reply_to,
        references=list(request.references),
        created_at_utc=request.created_at_utc,
        sender=request.sender.to_mailbox_principal(),
        to=[principal.to_mailbox_principal() for principal in request.to],
        cc=[principal.to_mailbox_principal() for principal in request.cc],
        reply_to=[principal.to_mailbox_principal() for principal in request.reply_to],
        subject=request.subject,
        body_markdown="Gateway integration body\n",
        attachments=[attachment.to_mailbox_attachment() for attachment in request.attachments],
        headers=dict(request.headers),
    )
    staged_message.parent.mkdir(parents=True, exist_ok=True)
    staged_message.write_text(serialize_message_document(message), encoding="utf-8")
    deliver_message(mailbox_root, request)
    return message_id


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
        self.m_session_name = "HOUMAO-gateway"
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
        tmux_session_name: str | None = None,
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
            tmux_session_name,
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


class _FakeHeadlessSessionRegistry:
    """Shared fake state across repeated headless start and resume calls."""

    def __init__(self, *, session_name: str) -> None:
        self.m_session_name = session_name
        self.m_session_id = "headless-session-1"
        self.m_prompts: list[str] = []
        self.m_prompt_calls: list[tuple[str, str | None]] = []
        self.m_interrupt_count = 0
        self.m_terminated = False


class _FakeCodexHeadlessSession(HeadlessInteractiveSession):
    """Minimal fake headless session for runtime and CLI integration tests."""

    m_registry: _FakeHeadlessSessionRegistry | None = None

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
        registry = type(self).m_registry
        if registry is None:
            raise AssertionError("Fake headless registry is not configured.")
        self.backend = "codex_headless"
        self.m_registry = registry
        self._plan = launch_plan
        session_name = tmux_session_name or registry.m_session_name
        self._state = state or HeadlessSessionState(
            session_id=registry.m_session_id,
            turn_index=0,
            role_bootstrap_applied=True,
            working_directory=str(launch_plan.working_directory),
            tmux_session_name=session_name,
        )
        if self._state.session_id is None:
            self._state.session_id = registry.m_session_id
        if not self._state.working_directory:
            self._state.working_directory = str(launch_plan.working_directory)
        if not self._state.tmux_session_name:
            self._state.tmux_session_name = session_name

    def send_prompt(
        self,
        prompt: str,
        *,
        turn_artifact_dir_name: str | None = None,
    ) -> list[SessionEvent]:
        """Record a direct prompt submission for the fake headless backend."""

        self.m_registry.m_prompts.append(prompt)
        self.m_registry.m_prompt_calls.append((prompt, turn_artifact_dir_name))
        self._state.turn_index += 1
        self._state.session_id = self.m_registry.m_session_id
        return [
            SessionEvent(
                kind="assistant",
                message=f"headless:{prompt}",
                turn_index=self._state.turn_index,
            )
        ]

    def interrupt(self) -> SessionControlResult:
        """Record one fake interrupt."""

        self.m_registry.m_interrupt_count += 1
        return SessionControlResult(status="ok", action="interrupt", detail="interrupted")

    def terminate(self) -> SessionControlResult:
        """Record fake session termination."""

        self.m_registry.m_terminated = True
        return SessionControlResult(status="ok", action="terminate", detail="stopped")

    def close(self) -> None:
        """Close the fake session."""

        return None

    def update_launch_plan(self, launch_plan: Any) -> None:
        """Update the persisted fake launch plan."""

        self._plan = launch_plan


class _FakeLocalInteractiveSession(HeadlessInteractiveSession):
    """Minimal fake local-interactive session for runtime and CLI integration tests."""

    m_registry: _FakeHeadlessSessionRegistry | None = None

    def __init__(
        self,
        *,
        launch_plan: Any,
        role_name: str,
        session_manifest_path: Path,
        agent_def_dir: Path | None = None,
        state: HeadlessSessionState | None = None,
        tmux_session_name: str | None = None,
    ) -> None:
        del role_name, session_manifest_path, agent_def_dir
        registry = type(self).m_registry
        if registry is None:
            raise AssertionError("Fake local-interactive registry is not configured.")
        self.backend = "local_interactive"
        self.m_registry = registry
        self._plan = launch_plan
        session_name = tmux_session_name or registry.m_session_name
        self._state = state or HeadlessSessionState(
            turn_index=0,
            role_bootstrap_applied=True,
            working_directory=str(launch_plan.working_directory),
            tmux_session_name=session_name,
        )
        if not self._state.working_directory:
            self._state.working_directory = str(launch_plan.working_directory)
        if not self._state.tmux_session_name:
            self._state.tmux_session_name = session_name

    def send_prompt(
        self,
        prompt: str,
        *,
        turn_artifact_dir_name: str | None = None,
    ) -> list[SessionEvent]:
        """Record a direct prompt submission for the fake local-interactive backend."""

        self.m_registry.m_prompts.append(prompt)
        self.m_registry.m_prompt_calls.append((prompt, turn_artifact_dir_name))
        self._state.turn_index += 1
        return [
            SessionEvent(
                kind="assistant",
                message=f"local:{prompt}",
                turn_index=self._state.turn_index,
            )
        ]

    def interrupt(self) -> SessionControlResult:
        """Record one fake interrupt."""

        self.m_registry.m_interrupt_count += 1
        return SessionControlResult(status="ok", action="interrupt", detail="interrupted")

    def terminate(self) -> SessionControlResult:
        """Record fake session termination."""

        self.m_registry.m_terminated = True
        return SessionControlResult(status="ok", action="terminate", detail="stopped")

    def close(self) -> None:
        """Close the fake session."""

        return None

    def update_launch_plan(self, launch_plan: Any) -> None:
        """Update the persisted fake launch plan."""

        self._plan = launch_plan


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
        if path_parts[:1] == ["cao"]:
            path_parts = path_parts[1:]
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
                    "session_name": "HOUMAO-gateway",
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
        if path_parts[:1] == ["cao"]:
            path_parts = path_parts[1:]
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
    registry: _FakeCaoSessionRegistry | None,
    tmux_env: _FakeTmuxEnv,
    registry_root: Path,
    headless_registry: _FakeHeadlessSessionRegistry | None = None,
    local_interactive_registry: _FakeHeadlessSessionRegistry | None = None,
) -> None:
    """Install fake CAO session and tmux environment hooks."""

    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root.resolve()))
    if registry is not None:
        _FakeCaoRestSession.m_registry = registry
        monkeypatch.setattr(
            "houmao.agents.realm_controller.runtime.CaoRestSession",
            _FakeCaoRestSession,
        )
        monkeypatch.setattr(
            "houmao.agents.realm_controller.runtime.HoumaoServerRestSession",
            _FakeCaoRestSession,
        )
    if headless_registry is not None:
        _FakeCodexHeadlessSession.m_registry = headless_registry
        monkeypatch.setattr(
            "houmao.agents.realm_controller.runtime.CodexHeadlessSession",
            _FakeCodexHeadlessSession,
        )
    if local_interactive_registry is not None:
        _FakeLocalInteractiveSession.m_registry = local_interactive_registry
        monkeypatch.setattr(
            "houmao.agents.realm_controller.runtime.LocalInteractiveSession",
            _FakeLocalInteractiveSession,
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


def _force_detached_gateway_execution(manifest_path: Path) -> None:
    """Force detached-process execution for REST-backed gateway integration tests."""

    paths = gateway_paths_from_manifest_path(manifest_path)
    if paths is None:
        raise AssertionError("Gateway paths could not be resolved for detached execution setup.")
    write_gateway_desired_config(
        paths.desired_config_path,
        GatewayDesiredConfigV1(desired_execution_mode="detached_process"),
    )


def _assert_raw_cao_start_session_is_retired(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    *,
    extra_args: list[str] | None = None,
) -> None:
    """Assert that public raw `cao_rest` startup is rejected with migration guidance."""

    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)
    argv = [
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
        "http://127.0.0.1:9889",
    ]
    if extra_args is not None:
        argv.extend(extra_args)
    exit_code, payload, err = _run_cli_json(capsys, argv)
    assert exit_code == 2
    assert payload == {}
    assert "Standalone backend='cao_rest' operator workflows are retired" in err


def test_start_session_rejects_retired_raw_cao_backend_even_with_gateway_auto_attach_args(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Raw `cao_rest` startup should stay retired even when gateway args are present."""

    conflict_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conflict_socket.bind(("127.0.0.1", 0))
    conflict_socket.listen(1)
    conflict_port = int(conflict_socket.getsockname()[1])
    try:
        _assert_raw_cao_start_session_is_retired(
            capsys,
            tmp_path,
            extra_args=[
                "--gateway-auto-attach",
                "--gateway-host",
                "127.0.0.1",
                "--gateway-port",
                str(conflict_port),
            ],
        )
    finally:
        conflict_socket.close()


def test_runtime_owned_headless_attach_uses_persisted_gateway_defaults(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Later headless attach should resolve host and port from persisted defaults."""

    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)
    blueprint_path = _seed_gateway_defaults_blueprint(agent_def_dir, port=43123)
    headless_registry = _FakeHeadlessSessionRegistry(session_name="HOUMAO-headless")
    tmux_env = _FakeTmuxEnv()
    _install_gateway_runtime_fakes(
        monkeypatch=monkeypatch,
        registry=None,
        tmux_env=tmux_env,
        registry_root=tmp_path / "registry",
        headless_registry=headless_registry,
    )
    captured_attach: dict[str, object] = {}
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._start_gateway_process",
        lambda *, controller, paths, host, port, execution_mode: (
            captured_attach.update(
                {
                    "controller": controller,
                    "paths": paths,
                    "host": host,
                    "port": port,
                    "execution_mode": execution_mode,
                }
            )
            or port
        ),
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
            "--blueprint",
            str(blueprint_path),
            "--backend",
            "codex_headless",
            "--workdir",
            str(tmp_path),
            "--agent-identity",
            headless_registry.m_session_name,
        ],
    )
    assert start_exit == 0
    assert start_err == ""

    manifest_path = Path(str(start_payload["session_manifest"]))
    attach_exit, attach_payload, attach_err = _run_cli_json(
        capsys,
        [
            "attach-gateway",
            "--agent-def-dir",
            str(agent_def_dir),
            "--agent-identity",
            str(manifest_path),
        ],
    )

    assert attach_exit == 0
    assert attach_err == ""
    assert attach_payload["status"] == "ok"
    assert attach_payload["gateway_host"] == "127.0.0.1"
    assert attach_payload["gateway_port"] == 43123
    assert captured_attach["host"] == "127.0.0.1"
    assert captured_attach["port"] == 43123
    assert captured_attach["execution_mode"] == "detached_process"


def test_runtime_owned_headless_between_turn_attach_rebuilds_internal_attach_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Between-turn headless attach should rebuild internal attach metadata from the manifest."""

    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)
    headless_registry = _FakeHeadlessSessionRegistry(session_name="HOUMAO-headless")
    tmux_env = _FakeTmuxEnv()
    _install_gateway_runtime_fakes(
        monkeypatch=monkeypatch,
        registry=None,
        tmux_env=tmux_env,
        registry_root=tmp_path / "registry",
        headless_registry=headless_registry,
    )
    captured_attach: dict[str, object] = {}
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._start_gateway_process",
        lambda *, controller, paths, host, port, execution_mode: (
            captured_attach.update(
                {
                    "controller": controller,
                    "paths": paths,
                    "host": host,
                    "port": port,
                    "execution_mode": execution_mode,
                }
            )
            or 43123
        ),
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
            "codex_headless",
            "--workdir",
            str(tmp_path),
            "--agent-identity",
            headless_registry.m_session_name,
        ],
    )
    assert start_exit == 0
    assert start_err == ""

    manifest_path = Path(str(start_payload["session_manifest"]))
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None

    prompt_exit, prompt_events, prompt_err = _run_cli_events(
        capsys,
        [
            "send-prompt",
            "--agent-def-dir",
            str(agent_def_dir),
            "--agent-identity",
            str(manifest_path),
            "--prompt",
            "between-turn",
        ],
    )
    assert prompt_exit == 0
    assert prompt_err == ""
    assert prompt_events[-1]["message"] == "headless:between-turn"

    paths.attach_path.unlink()
    assert not paths.attach_path.exists()

    attach_exit, attach_payload, attach_err = _run_cli_json(
        capsys,
        [
            "attach-gateway",
            "--agent-def-dir",
            str(agent_def_dir),
            "--agent-identity",
            str(manifest_path),
        ],
    )

    assert attach_exit == 0
    assert attach_err == ""
    assert attach_payload["status"] == "ok"
    assert attach_payload["gateway_host"] == "127.0.0.1"
    assert attach_payload["gateway_port"] == 43123
    assert paths.attach_path.is_file()
    assert captured_attach["host"] == "127.0.0.1"
    assert captured_attach["port"] == 0


def test_runtime_owned_local_interactive_gateway_link_uses_persisted_defaults(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Later local-interactive gateway start should honor persisted defaults."""

    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)
    blueprint_path = _seed_gateway_defaults_blueprint(agent_def_dir, port=43123)
    local_registry = _FakeHeadlessSessionRegistry(session_name="HOUMAO-local")
    tmux_env = _FakeTmuxEnv()
    _install_gateway_runtime_fakes(
        monkeypatch=monkeypatch,
        registry=None,
        tmux_env=tmux_env,
        registry_root=tmp_path / "registry",
        local_interactive_registry=local_registry,
    )
    captured_attach: dict[str, object] = {}
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._start_gateway_process",
        lambda *, controller, paths, host, port, execution_mode: (
            captured_attach.update(
                {
                    "controller": controller,
                    "paths": paths,
                    "host": host,
                    "port": port,
                    "execution_mode": execution_mode,
                }
            )
            or port
        ),
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
            "--blueprint",
            str(blueprint_path),
            "--role",
            "r",
            "--backend",
            "local_interactive",
            "--workdir",
            str(tmp_path),
            "--agent-identity",
            local_registry.m_session_name,
        ],
    )
    assert start_exit == 0
    assert start_err == ""

    manifest_path = Path(str(start_payload["session_manifest"]))
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

    attach_exit, attach_payload, attach_err = _run_cli_json(
        capsys,
        [
            "attach-gateway",
            "--agent-def-dir",
            str(agent_def_dir),
            "--agent-identity",
            str(manifest_path),
        ],
    )

    assert attach_exit == 0
    assert attach_err == ""
    assert attach_payload["status"] == "ok"
    assert attach_payload["gateway_host"] == "127.0.0.1"
    assert attach_payload["gateway_port"] == 43123
    assert captured_attach["host"] == "127.0.0.1"
    assert captured_attach["port"] == 43123
    assert captured_attach["execution_mode"] == "detached_process"
    assert getattr(captured_attach["controller"], "launch_plan").backend == "local_interactive"


def test_gateway_cli_contract_rejects_retired_raw_cao_backend_startup(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Gateway CLI coverage should not rely on retired raw `cao_rest` startup."""

    _assert_raw_cao_start_session_is_retired(capsys, tmp_path)


def test_gateway_http_mail_notifier_routes_follow_manifest_mailbox_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Live gateway notifier routes should use the manifest-backed mailbox contract."""

    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    mailbox_root = tmp_path / "mailbox"
    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)

    with _FakeCaoServer(terminal_id="term-1") as fake_cao:
        registry = _FakeCaoSessionRegistry(api_base_url=fake_cao.base_url, terminal_id="term-1")
        tmux_env = _FakeTmuxEnv()
        _install_gateway_runtime_fakes(
            monkeypatch=monkeypatch,
            registry=registry,
            tmux_env=tmux_env,
            registry_root=tmp_path / "registry",
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
                "houmao_server_rest",
                "--workdir",
                str(tmp_path),
                "--houmao-base-url",
                fake_cao.base_url,
                "--mailbox-transport",
                "filesystem",
                "--mailbox-root",
                str(mailbox_root),
                "--mailbox-address",
                "HOUMAO-gateway@agents.localhost",
            ],
        )
        assert start_exit == 0
        assert start_err == ""

        manifest_path = Path(str(start_payload["session_manifest"]))
        paths = gateway_paths_from_manifest_path(manifest_path)
        assert paths is not None
        _force_detached_gateway_execution(manifest_path)

        try:
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

            client = GatewayClient(
                endpoint=GatewayEndpoint(
                    host="127.0.0.1",
                    port=int(attach_payload["gateway_port"]),
                )
            )

            initial_status = client.get_mail_notifier()
            assert initial_status.supported is True
            assert initial_status.enabled is False

            enabled_status = client.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=60))
            assert enabled_status.supported is True
            assert enabled_status.enabled is True
            assert enabled_status.interval_seconds == 60

            disabled_status = client.delete_mail_notifier()
            assert disabled_status.supported is True
            assert disabled_status.enabled is False

            _wait_until(lambda: paths.log_path.is_file())
            log_text = paths.log_path.read_text(encoding="utf-8")
            assert "mail notifier enabled interval_seconds=60" in log_text
            assert "mail notifier disabled" in log_text
        finally:
            _best_effort_cleanup_gateway(manifest_path)


def test_gateway_runtime_mail_notifier_repeats_when_prompt_ready_returns(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Manifest-backed notifier polling should repeat for unchanged unread mail."""

    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    mailbox_root = tmp_path / "mailbox"
    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)

    with _FakeCaoServer(terminal_id="term-1") as fake_cao:
        registry = _FakeCaoSessionRegistry(api_base_url=fake_cao.base_url, terminal_id="term-1")
        tmux_env = _FakeTmuxEnv()
        _install_gateway_runtime_fakes(
            monkeypatch=monkeypatch,
            registry=registry,
            tmux_env=tmux_env,
            registry_root=tmp_path / "registry",
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
                "houmao_server_rest",
                "--workdir",
                str(tmp_path),
                "--houmao-base-url",
                fake_cao.base_url,
                "--mailbox-transport",
                "filesystem",
                "--mailbox-root",
                str(mailbox_root),
                "--mailbox-address",
                "HOUMAO-gateway@agents.localhost",
            ],
        )
        assert start_exit == 0
        assert start_err == ""

        manifest_path = Path(str(start_payload["session_manifest"]))
        captured_attach: dict[str, object] = {}
        monkeypatch.setattr(
            "houmao.agents.realm_controller.runtime._start_gateway_process",
            lambda *, controller, paths, host, port, execution_mode: (
                captured_attach.update(
                    {
                        "controller": controller,
                        "paths": paths,
                        "host": host,
                        "port": port,
                        "execution_mode": execution_mode,
                    }
                )
                or port
            ),
        )

        attach_exit, _attach_payload, attach_err = _run_cli_json(
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

        paths = cast(Any, captured_attach["paths"])
        message_id = _deliver_unread_mailbox_message(
            mailbox_root,
            message_id="msg-20260316T090000Z-33333333333333333333333333333333",
            recipient_principal_id=str(start_payload["mailbox"]["principal_id"]),
            recipient_address=str(start_payload["mailbox"]["address"]),
        )

        readiness = {"busy": True}
        monkeypatch.setattr(
            GatewayServiceRuntime,
            "_tui_prompt_not_ready_reasons_locked",
            lambda self: (
                ["turn.phase='active'", "surface.accepting_input='no'"] if readiness["busy"] else []
            ),
        )

        runtime = GatewayServiceRuntime.from_gateway_root(
            gateway_root=paths.gateway_root,
            host="127.0.0.1",
            port=_pick_unused_loopback_port(),
        )
        runtime.start()
        try:
            runtime.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=1))

            time.sleep(1.3)
            assert fake_cao.messages() == []

            readiness["busy"] = False
            _wait_until(lambda: len(fake_cao.messages()) >= 1, timeout_seconds=5.0)
            first_prompt = fake_cao.messages()[0][1]
            assert message_id not in first_prompt
            assert (
                "List unread mail through the shared gateway mailbox API for this round."
                in first_prompt
            )
            assert f"GET http://127.0.0.1:{runtime.m_port}/v1/mail/status" in first_prompt

            readiness["busy"] = True
            prompt_count = len(fake_cao.messages())
            time.sleep(1.3)
            assert len(fake_cao.messages()) == prompt_count

            readiness["busy"] = False
            _wait_until(lambda: len(fake_cao.messages()) >= prompt_count + 1, timeout_seconds=5.0)
            repeated_prompt = fake_cao.messages()[-1][1]
            assert message_id not in repeated_prompt
            assert (
                "List unread mail through the shared gateway mailbox API for this round."
                in repeated_prompt
            )
        finally:
            runtime.shutdown()

        audit_rows = read_gateway_notifier_audit_records(paths.queue_path)
        busy_rows = [row for row in audit_rows if row.outcome == "busy_skip"]
        enqueued_rows = [row for row in audit_rows if row.outcome == "enqueued"]
        assert busy_rows
        assert len(enqueued_rows) >= 2
        assert not any(row.outcome == "dedup_skip" for row in audit_rows)
        assert any(row.detail is not None and "not prompt-ready" in row.detail for row in busy_rows)
        assert enqueued_rows[-1].unread_summary[0].message_ref == f"filesystem:{message_id}"


def test_gateway_http_reminder_routes_are_ephemeral_and_do_not_expand_request_kinds(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Live gateway reminders should stay in memory and not extend `/v1/requests` kinds."""

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
            registry_root=tmp_path / "registry",
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
                "houmao_server_rest",
                "--workdir",
                str(tmp_path),
                "--houmao-base-url",
                fake_cao.base_url,
            ],
        )
        assert start_exit == 0
        assert start_err == ""

        manifest_path = Path(str(start_payload["session_manifest"]))
        _force_detached_gateway_execution(manifest_path)
        try:
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

            endpoint = GatewayEndpoint(
                host="127.0.0.1",
                port=int(attach_payload["gateway_port"]),
            )
            client = GatewayClient(endpoint=endpoint)

            scheduled_result = client.create_reminders(
                GatewayReminderCreateBatchV1(
                    reminders=[
                        GatewayReminderDefinitionV1(
                            mode="one_off",
                            title="integration scheduled reminder",
                            prompt="integration scheduled reminder",
                            ranking=0,
                            start_after_seconds=60,
                        )
                    ]
                )
            )
            scheduled_reminder = scheduled_result.reminders[0]
            assert (
                client.get_reminder(reminder_id=scheduled_reminder.reminder_id).reminder_id
                == scheduled_reminder.reminder_id
            )
            assert [reminder.reminder_id for reminder in client.list_reminders().reminders] == [
                scheduled_reminder.reminder_id
            ]

            delete_result = client.delete_reminder(reminder_id=scheduled_reminder.reminder_id)
            assert delete_result.deleted is True
            assert client.list_reminders().reminders == []

            send_keys_request = request.Request(
                url=f"http://{endpoint.host}:{endpoint.port}/v1/reminders",
                method="POST",
                headers={"Content-Type": "application/json"},
                data=json.dumps(
                    GatewayReminderCreateBatchV1(
                        reminders=[
                            GatewayReminderDefinitionV1(
                                mode="one_off",
                                title="unsupported send keys reminder",
                                send_keys=GatewayReminderSendKeysV1(sequence="<[Escape]>"),
                                ranking=0,
                                start_after_seconds=60,
                            )
                        ]
                    ).model_dump(mode="json")
                ).encode("utf-8"),
            )
            with pytest.raises(Exception) as send_keys_exc_info:
                request.urlopen(send_keys_request, timeout=5.0)
            send_keys_error = send_keys_exc_info.value
            assert getattr(send_keys_error, "code", None) == 422

            delivered_result = client.create_reminders(
                GatewayReminderCreateBatchV1(
                    reminders=[
                        GatewayReminderDefinitionV1(
                            mode="one_off",
                            title="integration delivered reminder",
                            prompt="integration delivered reminder",
                            ranking=0,
                            start_after_seconds=0.1,
                        )
                    ]
                )
            )
            delivered_reminder = delivered_result.reminders[0]

            _wait_until(
                lambda: any(
                    message == "integration delivered reminder"
                    for _, message in fake_cao.messages()
                ),
                timeout_seconds=5.0,
            )
            assert client.list_reminders().reminders == []

            invalid_request = request.Request(
                url=f"http://{endpoint.host}:{endpoint.port}/v1/requests",
                method="POST",
                headers={"Content-Type": "application/json"},
                data=json.dumps(
                    {
                        "schema_version": 1,
                        "kind": "reminder_prompt",
                        "payload": {"prompt": "should fail"},
                    }
                ).encode("utf-8"),
            )
            with pytest.raises(Exception) as exc_info:
                request.urlopen(invalid_request, timeout=5.0)
            error = exc_info.value
            assert getattr(error, "code", None) == 422
            assert delivered_reminder.reminder_id not in {
                reminder.reminder_id for reminder in client.list_reminders().reminders
            }
        finally:
            _best_effort_cleanup_gateway(manifest_path)


def test_gateway_http_mail_read_route_marks_message_read_through_live_gateway(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Live gateway `/v1/mail/read` should mark one filesystem message read."""

    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    mailbox_root = tmp_path / "mailbox"
    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)

    with _FakeCaoServer(terminal_id="term-1") as fake_cao:
        registry = _FakeCaoSessionRegistry(api_base_url=fake_cao.base_url, terminal_id="term-1")
        tmux_env = _FakeTmuxEnv()
        _install_gateway_runtime_fakes(
            monkeypatch=monkeypatch,
            registry=registry,
            tmux_env=tmux_env,
            registry_root=tmp_path / "registry",
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
                "houmao_server_rest",
                "--workdir",
                str(tmp_path),
                "--houmao-base-url",
                fake_cao.base_url,
                "--mailbox-transport",
                "filesystem",
                "--mailbox-root",
                str(mailbox_root),
                "--mailbox-address",
                "HOUMAO-gateway@agents.localhost",
            ],
        )
        assert start_exit == 0
        assert start_err == ""

        manifest_path = Path(str(start_payload["session_manifest"]))
        _force_detached_gateway_execution(manifest_path)
        try:
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

            message_id = _deliver_unread_mailbox_message(
                mailbox_root,
                message_id="msg-20260316T090000Z-44444444444444444444444444444444",
                recipient_principal_id=str(start_payload["mailbox"]["principal_id"]),
                recipient_address=str(start_payload["mailbox"]["address"]),
            )
            client = GatewayClient(
                endpoint=GatewayEndpoint(
                    host="127.0.0.1",
                    port=int(attach_payload["gateway_port"]),
                )
            )

            state_response = client.read_mail(
                GatewayMailMessageRequestV1(
                    message_ref=f"filesystem:{message_id}",
                )
            )

            assert state_response.transport == "filesystem"
            assert state_response.operation == "read"
            assert state_response.message.message_ref == f"filesystem:{message_id}"
            assert state_response.message.read is True

            local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
                mailbox_root,
                address=str(start_payload["mailbox"]["address"]),
            )
            with sqlite3.connect(local_sqlite_path) as connection:
                row = connection.execute(
                    "SELECT is_read FROM message_state WHERE message_id = ?",
                    (message_id,),
                ).fetchone()
            assert row == (1,)
        finally:
            _best_effort_cleanup_gateway(manifest_path)


def test_gateway_http_mail_notifier_persists_queryable_audit_rows(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Live gateway notifier polling should persist queryable audit history."""

    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    mailbox_root = tmp_path / "mailbox"
    brain_manifest_path = _seed_brain_manifest(agent_def_dir, tmp_path)

    with _FakeCaoServer(terminal_id="term-1") as fake_cao:
        registry = _FakeCaoSessionRegistry(api_base_url=fake_cao.base_url, terminal_id="term-1")
        tmux_env = _FakeTmuxEnv()
        _install_gateway_runtime_fakes(
            monkeypatch=monkeypatch,
            registry=registry,
            tmux_env=tmux_env,
            registry_root=tmp_path / "registry",
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
                "houmao_server_rest",
                "--workdir",
                str(tmp_path),
                "--houmao-base-url",
                fake_cao.base_url,
                "--mailbox-transport",
                "filesystem",
                "--mailbox-root",
                str(mailbox_root),
                "--mailbox-address",
                "HOUMAO-gateway@agents.localhost",
            ],
        )
        assert start_exit == 0
        assert start_err == ""

        manifest_path = Path(str(start_payload["session_manifest"]))
        captured_attach: dict[str, object] = {}
        monkeypatch.setattr(
            "houmao.agents.realm_controller.runtime._start_gateway_process",
            lambda *, controller, paths, host, port, execution_mode: (
                captured_attach.update(
                    {
                        "controller": controller,
                        "paths": paths,
                        "host": host,
                        "port": port,
                        "execution_mode": execution_mode,
                    }
                )
                or port
            ),
        )

        attach_exit, _attach_payload, attach_err = _run_cli_json(
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

        paths = cast(Any, captured_attach["paths"])
        message_id = _deliver_unread_mailbox_message(
            mailbox_root,
            message_id="msg-20260316T090000Z-33333333333333333333333333333333",
            recipient_principal_id=str(start_payload["mailbox"]["principal_id"]),
            recipient_address=str(start_payload["mailbox"]["address"]),
        )
        monkeypatch.setattr(
            GatewayServiceRuntime,
            "_tui_prompt_not_ready_reasons_locked",
            lambda self: [],
        )

        runtime = GatewayServiceRuntime.from_gateway_root(
            gateway_root=paths.gateway_root,
            host="127.0.0.1",
            port=_pick_unused_loopback_port(),
        )
        runtime.start()
        try:
            enabled_status = runtime.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=1))
            assert enabled_status.enabled is True

            _wait_until(lambda: bool(fake_cao.messages()), timeout_seconds=5.0)
            _wait_until(
                lambda: any(
                    row.outcome == "enqueued"
                    for row in read_gateway_notifier_audit_records(paths.queue_path)
                ),
                timeout_seconds=5.0,
            )

            audit_rows = read_gateway_notifier_audit_records(paths.queue_path)
            enqueued_rows = [row for row in audit_rows if row.outcome == "enqueued"]
            assert enqueued_rows
            assert enqueued_rows[-1].unread_count == 1
            assert enqueued_rows[-1].unread_summary[0].message_ref == f"filesystem:{message_id}"
            assert enqueued_rows[-1].enqueued_request_id is not None
            assert fake_cao.messages()
            latest_prompt = fake_cao.messages()[-1][1]
            assert message_id not in latest_prompt
            assert (
                "List unread mail through the shared gateway mailbox API for this round."
                in latest_prompt
            )
        finally:
            runtime.shutdown()


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
            registry_root=tmp_path / "registry",
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
                "houmao_server_rest",
                "--workdir",
                str(tmp_path),
                "--houmao-base-url",
                fake_cao.base_url,
            ],
        )
        assert start_exit == 0
        assert start_err == ""

        manifest_path = Path(str(start_payload["session_manifest"]))
        session_name = registry.m_session_name
        paths = gateway_paths_from_manifest_path(manifest_path)
        assert paths is not None
        _force_detached_gateway_execution(manifest_path)

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
