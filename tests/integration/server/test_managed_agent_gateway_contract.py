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
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from fastapi import HTTPException
import pytest
import uvicorn

from houmao.agents.realm_controller.backends.headless_base import (
    HeadlessInteractiveSession,
    HeadlessSessionState,
)
from houmao.agents.realm_controller.gateway_models import GatewayMailNotifierPutV1
from houmao.agents.realm_controller.gateway_service import (
    GatewayServiceRuntime,
    _GatewayUvicornServer,
    create_app,
)
from houmao.agents.realm_controller.gateway_storage import (
    GatewayCapabilityPublication,
    ensure_gateway_capability,
    gateway_paths_from_manifest_path,
    read_pid_file,
)
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RoleInjectionPlan,
    SessionControlResult,
)
from houmao.agents.realm_controller.registry_storage import resolve_live_agent_record
from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.agents.realm_controller.backends.tmux_runtime import TmuxPaneRecord
from houmao.cao.models import CaoSuccessResponse, CaoTerminal
from houmao.server.config import HoumaoServerConfig
from houmao.server.models import (
    HoumaoHeadlessLaunchMailboxOptions,
    HoumaoHeadlessLaunchRequest,
    HoumaoManagedAgentSubmitPromptRequest,
    HoumaoParsedSurface,
    HoumaoRegisterLaunchRequest,
)
from houmao.server.service import HoumaoServerService, ProxyResponse
from houmao.server.tui.parser import OfficialParseResult
from houmao.server.tui.process import PaneProcessInspection
from houmao.server.tui.transport import ResolvedTmuxTarget
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR


def _write(path: Path, text: str) -> None:
    """Write one UTF-8 test fixture file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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


def _json_proxy_response(payload: object, *, status_code: int = 200) -> ProxyResponse:
    """Build one JSON proxy response payload for integration doubles."""

    body = json.dumps(payload).encode("utf-8")
    return ProxyResponse(
        status_code=status_code,
        body=body,
        content_type="application/json",
        json_payload=payload,
    )


def _sample_cao_plan(tmp_path: Path) -> LaunchPlan:
    """Return a minimal fake `cao_rest` launch plan."""

    return LaunchPlan(
        backend="cao_rest",
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="cao_profile",
            role_name="role",
            prompt="role prompt",
        ),
        metadata={},
    )


def _seed_cao_gateway_root(
    tmp_path: Path,
    *,
    terminal_id: str = "term-123",
) -> Path:
    """Create a minimal gateway-capable `cao_rest` session root."""

    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_sample_cao_plan(tmp_path),
            role_name="role",
            brain_manifest_path=tmp_path / "brain.yaml",
            agent_name="HOUMAO-gpu",
            agent_id=derive_agent_id_from_name("HOUMAO-gpu"),
            tmux_session_name="HOUMAO-gpu",
            backend_state={
                "api_base_url": "http://127.0.0.1:9889",
                "session_name": "cao-rest-1",
                "terminal_id": terminal_id,
                "profile_name": "runtime-profile",
                "profile_path": str(tmp_path / "runtime-profile.md"),
                "parsing_mode": "shadow_only",
                "turn_index": 1,
                "tmux_window_name": "developer-1",
            },
        )
    )
    write_session_manifest(manifest_path, payload)
    paths = ensure_gateway_capability(
        GatewayCapabilityPublication(
            manifest_path=manifest_path,
            backend="cao_rest",
            tool="codex",
            session_id="cao-rest-1",
            tmux_session_name="HOUMAO-gpu",
            working_directory=tmp_path,
            backend_state={
                "api_base_url": "http://127.0.0.1:9889",
                "terminal_id": terminal_id,
                "profile_name": "runtime-profile",
                "profile_path": str(tmp_path / "runtime-profile.md"),
                "parsing_mode": "shadow_only",
                "tmux_window_name": "developer-1",
            },
            agent_def_dir=tmp_path / "agents",
        )
    )
    return paths.gateway_root


def _seed_brain_manifest(agent_def_dir: Path, tmp_path: Path) -> Path:
    """Create a minimal codex brain manifest and role package."""

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
                f"  home_path: {tmp_path / 'home'}",
                f"  launch_helper: {tmp_path / 'home' / 'launch.sh'}",
                "  launch_executable: codex",
                "  launch_home_selector:",
                "    env_var: CODEX_HOME",
                f"    value: {tmp_path / 'home'}",
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


class _RecordingTuiTransport:
    """Minimal in-memory CAO-compatible transport for TUI integration tests."""

    def __init__(self, *, session_name: str, terminal_id: str) -> None:
        self.m_session_name = session_name
        self.m_terminal_id = terminal_id
        self.m_calls: list[tuple[str, str, tuple[tuple[str, str], ...]]] = []
        self.m_direct_messages: list[str] = []
        self.m_interrupt_count = 0

    def request(
        self,
        *,
        base_url: str,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
    ) -> ProxyResponse:
        """Handle one proxied compatibility request."""

        del base_url
        normalized_params = tuple(sorted((params or {}).items()))
        self.m_calls.append((method, path, normalized_params))
        if method == "GET" and path == f"/terminals/{self.m_terminal_id}":
            return _json_proxy_response(
                CaoTerminal(
                    id=self.m_terminal_id,
                    name="developer-1",
                    provider="codex",
                    session_name=self.m_session_name,
                    agent_profile="runtime-profile",
                    status="idle",
                ).model_dump(mode="json")
            )
        if method == "POST" and path == f"/terminals/{self.m_terminal_id}/input":
            self.m_direct_messages.append(dict(normalized_params).get("message", ""))
            return _json_proxy_response(CaoSuccessResponse(success=True).model_dump(mode="json"))
        if method == "POST" and path == f"/terminals/{self.m_terminal_id}/exit":
            self.m_interrupt_count += 1
            return _json_proxy_response(CaoSuccessResponse(success=True).model_dump(mode="json"))
        if method == "DELETE" and path == f"/sessions/{self.m_session_name}":
            return _json_proxy_response({"success": True, "detail": "session deleted"})
        raise AssertionError(f"Unexpected transport request: {method} {path} {normalized_params}")


class _FakeTmuxTransportResolver:
    """Deterministic tmux resolver for direct TUI fallback state refresh."""

    def __init__(self, *, output_text: str) -> None:
        self.m_output_text = output_text

    def resolve_target(
        self,
        *,
        session_name: str,
        window_name: str | None,
        window_index: str | None = None,
    ) -> ResolvedTmuxTarget:
        """Return one fixed tmux target."""

        return ResolvedTmuxTarget(
            pane=TmuxPaneRecord(
                pane_id="%9",
                session_name=session_name,
                window_id="@2",
                window_index=window_index or "1",
                window_name=window_name or "developer-1",
                pane_index="0",
                pane_active=True,
                pane_dead=False,
                pane_pid=4321,
            )
        )

    def capture_text(self, *, target: ResolvedTmuxTarget) -> str:
        """Return the fixed tmux pane text fixture."""

        assert target.pane.pane_id == "%9"
        return self.m_output_text


class _FakeProcessInspector:
    """Return a fixed process-inspection result for direct TUI refresh."""

    def __init__(self, inspection: PaneProcessInspection) -> None:
        self.m_inspection = inspection

    def inspect(self, *, tool: str, pane_pid: int | None) -> PaneProcessInspection:
        """Return the configured inspection."""

        del tool, pane_pid
        return self.m_inspection


class _FakeParserAdapter:
    """Return a fixed parsed surface for direct TUI refresh."""

    def __init__(self, result: OfficialParseResult) -> None:
        self.m_result = result

    def supports_tool(self, *, tool: str) -> bool:
        """Report support for the addressed tool."""

        del tool
        return True

    def capture_baseline(self, *, tool: str, output_text: str) -> int:
        """Return a fixed baseline offset."""

        del tool, output_text
        return 17

    def parse(self, *, tool: str, output_text: str, baseline_pos: int) -> OfficialParseResult:
        """Return the configured parse result."""

        del tool, output_text, baseline_pos
        return self.m_result


def _ready_surface() -> HoumaoParsedSurface:
    """Return one parsed ready Codex surface for direct TUI refresh."""

    return HoumaoParsedSurface(
        parser_family="codex_shadow",
        parser_preset_id="codex",
        parser_preset_version="1.0.0",
        availability="supported",
        business_state="idle",
        input_mode="freeform",
        ui_context="normal_prompt",
        normalized_projection_text="ready prompt",
        dialog_text="ready prompt",
        dialog_head="ready prompt",
        dialog_tail="ready prompt",
        anomaly_codes=[],
        baseline_invalidated=False,
        operator_blocked_excerpt=None,
    )


_CODEX_READY_RAW_SNAPSHOT = "› \n\n  ? for shortcuts            100% context left\n"


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
            tmux_session_name=tmux_session_name or "HOUMAO-headless",
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


class _FakeGatewayTuiClient:
    """Tiny fake CAO client used by the in-process live gateway."""

    def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
        del timeout_seconds
        self.m_base_url = base_url
        self.submitted_prompts: list[tuple[str, str]] = []
        self.interrupt_count = 0

    def get_terminal(self, terminal_id: str) -> CaoTerminal:
        """Return one fake terminal record."""

        return CaoTerminal(
            id=terminal_id,
            name="developer-1",
            provider="codex",
            session_name="cao-rest-1",
            agent_profile="runtime-profile",
            status="idle",
        )

    def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
        """Record one live gateway prompt delivery."""

        self.submitted_prompts.append((terminal_id, message))
        return CaoSuccessResponse(success=True)

    def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
        """Record one live gateway interrupt delivery."""

        del terminal_id
        self.interrupt_count += 1
        return CaoSuccessResponse(success=True)


class _FakeGatewayHeadlessSession:
    """Fake in-process headless backend used by the live gateway integration tests."""

    def __init__(self, *, block_prompt: bool = False) -> None:
        self.state = type(
            "State",
            (),
            {
                "turn_index": 0,
                "tmux_session_name": "HOUMAO-headless",
                "session_id": "headless-session-1",
            },
        )()
        self.prompt_calls: list[tuple[str, str | None]] = []
        self.block_prompt = block_prompt
        self.started_event = threading.Event()
        self.release_event = threading.Event()

    def send_prompt(
        self,
        prompt: str,
        *,
        turn_artifact_dir_name: str | None = None,
    ) -> list[object]:
        """Record one prompt delivery through the live headless gateway."""

        self.prompt_calls.append((prompt, turn_artifact_dir_name))
        self.started_event.set()
        if self.block_prompt:
            self.release_event.wait(timeout=5.0)
        self.state.turn_index += 1
        return []

    def interrupt(self) -> SessionControlResult:
        """Return a successful interrupt result."""

        return SessionControlResult(status="ok", action="interrupt", detail="interrupted")


class _FakeGatewayHeadlessController:
    """Fake resumed runtime controller used by the live headless gateway."""

    def __init__(self, session: _FakeGatewayHeadlessSession) -> None:
        self.backend_session = session
        self.persist_manifest_calls: list[bool] = []

    def persist_manifest(self, *, refresh_registry: bool = True) -> None:
        """Record one manifest persistence request."""

        self.persist_manifest_calls.append(refresh_registry)

    def interrupt(self) -> SessionControlResult:
        """Return a successful interrupt result."""

        return SessionControlResult(status="ok", action="interrupt", detail="interrupted")


class _FakeGatewayTrackingRuntime:
    """Configurable fake gateway-owned TUI tracking runtime."""

    m_template_state: object | None = None
    m_template_history: object | None = None
    m_started_session_ids: list[str] = []
    m_stopped_session_ids: list[str] = []
    m_prompt_notes: list[str] = []

    def __init__(self, *, identity: object, **_: object) -> None:
        self.m_identity = identity
        state = type(self).m_template_state
        history = type(self).m_template_history
        if state is None or history is None:
            raise AssertionError("Fake gateway tracking template state is not configured.")
        self.m_state = state
        self.m_history = history

    @classmethod
    def reset(cls) -> None:
        """Reset class-level bookkeeping between tests."""

        cls.m_template_state = None
        cls.m_template_history = None
        cls.m_started_session_ids = []
        cls.m_stopped_session_ids = []
        cls.m_prompt_notes = []

    def start(self) -> None:
        """Record gateway-owned tracker startup."""

        tracked_session_id = getattr(self.m_identity, "tracked_session_id", None)
        if isinstance(tracked_session_id, str):
            type(self).m_started_session_ids.append(tracked_session_id)

    def stop(self) -> None:
        """Record gateway-owned tracker shutdown."""

        tracked_session_id = getattr(self.m_identity, "tracked_session_id", None)
        if isinstance(tracked_session_id, str):
            type(self).m_stopped_session_ids.append(tracked_session_id)

    def current_state(self):  # type: ignore[no-untyped-def]
        """Return the configured tracked state."""

        return self.m_state

    def history(self, *, limit: int):  # type: ignore[no-untyped-def]
        """Return the configured tracked history."""

        del limit
        return self.m_history

    def note_prompt_submission(self, *, message: str):  # type: ignore[no-untyped-def]
        """Record prompt evidence on the gateway-owned tracker."""

        type(self).m_prompt_notes.append(message)
        return self.m_state


class _LiveGatewayServer:
    """Run one in-process live gateway HTTP server for integration tests."""

    def __init__(self, *, gateway_root: Path) -> None:
        self.m_gateway_root = gateway_root
        self.m_runtime = GatewayServiceRuntime.from_gateway_root(
            gateway_root=gateway_root,
            host="127.0.0.1",
            port=0,
        )
        config = uvicorn.Config(
            create_app(runtime=self.m_runtime),
            host="127.0.0.1",
            port=0,
            log_level="warning",
            access_log=False,
        )
        self.m_server = _GatewayUvicornServer(
            config,
            runtime=self.m_runtime,
            requested_host="127.0.0.1",
        )
        self.m_thread = threading.Thread(
            target=self.m_server.run,
            name="live-gateway-server",
            daemon=True,
        )
        self.m_port: int | None = None

    @property
    def port(self) -> int:
        """Return the bound gateway TCP port."""

        if self.m_port is None:
            raise AssertionError("Live gateway server has not started yet.")
        return self.m_port

    def __enter__(self) -> "_LiveGatewayServer":
        """Start the in-process live gateway server."""

        self.m_thread.start()
        manifest_path = self.m_gateway_root.parent / "manifest.json"
        paths = gateway_paths_from_manifest_path(manifest_path)
        if paths is None:
            raise AssertionError("Gateway paths could not be resolved for live gateway test.")

        def _started() -> bool:
            if not paths.current_instance_path.is_file():
                return False
            payload = json.loads(paths.current_instance_path.read_text(encoding="utf-8"))
            port = payload.get("port")
            if not isinstance(port, int) or port <= 0:
                return False
            self.m_port = port
            return True

        _wait_until(_started)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Stop the in-process live gateway server."""

        del exc_type, exc, tb
        self.m_server.should_exit = True
        self.m_thread.join(timeout=5.0)


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
        "tmux_session_name": "HOUMAO-headless",
        "tmux_window_name": "agent",
        "manifest_path": "/tmp/manifest.json",
        "session_root": "/tmp/session-root",
        "agent_name": "HOUMAO-headless",
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

    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root.resolve()))
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
                agent_name="HOUMAO-headless",
                agent_id=None,
                mailbox=HoumaoHeadlessLaunchMailboxOptions(
                    transport="filesystem",
                    filesystem_root=str(mailbox_root.resolve()),
                    address="HOUMAO-headless@agents.localhost",
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


def test_tui_managed_agent_request_handoff_prefers_live_gateway_and_falls_back_after_stop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """TUI managed-agent requests should hand off cleanly between direct and live gateway control."""

    gateway_root = _seed_cao_gateway_root(tmp_path, terminal_id="abcd1234")
    session_root = gateway_root.parent
    manifest_path = session_root / "manifest.json"
    transport = _RecordingTuiTransport(session_name="cao-rest-1", terminal_id="abcd1234")
    monkeypatch.setattr("houmao.server.service.tmux_session_exists", lambda **_kwargs: True)

    service = HoumaoServerService(
        config=HoumaoServerConfig(
            api_base_url="http://127.0.0.1:9889",
            runtime_root=tmp_path,
            startup_child=False,
        ),
        transport=transport,
        child_manager=_NoopChildManager(),
        transport_resolver=_FakeTmuxTransportResolver(output_text=_CODEX_READY_RAW_SNAPSHOT),
        process_inspector=_FakeProcessInspector(
            PaneProcessInspection(
                process_state="tui_up",
                matched_process_names=["codex"],
                matched_processes=(),
            )
        ),
        parser_adapter=_FakeParserAdapter(
            OfficialParseResult(parsed_surface=_ready_surface(), parse_error=None)
        ),
    )
    service.register_launch(
        HoumaoRegisterLaunchRequest(
            session_name="cao-rest-1",
            terminal_id="abcd1234",
            tool="codex",
            tmux_session_name="HOUMAO-gpu",
            tmux_window_name="developer-1",
            manifest_path=str(manifest_path),
            session_root=str(session_root),
            agent_name="HOUMAO-gpu",
            agent_id="agent-1234",
        )
    )
    direct_state = service.refresh_terminal_state("abcd1234")
    assert direct_state.diagnostics.availability == "available"

    direct_accepted = service.submit_managed_agent_request(
        "cao-rest-1",
        HoumaoManagedAgentSubmitPromptRequest(prompt="direct-before-gateway"),
    )
    assert direct_accepted.disposition == "accepted"
    assert transport.m_direct_messages == ["direct-before-gateway"]

    fake_gateway_client = _FakeGatewayTuiClient(base_url="http://unused")
    _FakeGatewayTrackingRuntime.reset()
    _FakeGatewayTrackingRuntime.m_template_state = service.terminal_state("abcd1234")
    _FakeGatewayTrackingRuntime.m_template_history = service.terminal_history("abcd1234", limit=5)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_gateway_client,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.SingleSessionTrackingRuntime",
        _FakeGatewayTrackingRuntime,
    )

    with _LiveGatewayServer(gateway_root=gateway_root):
        detail = service.managed_agent_state_detail("cao-rest-1")
        assert detail.detail.transport == "tui"
        assert detail.detail.terminal_id == "abcd1234"

        gateway_accepted = service.submit_managed_agent_request(
            "cao-rest-1",
            HoumaoManagedAgentSubmitPromptRequest(prompt="through-gateway"),
        )
        assert gateway_accepted.disposition == "accepted"
        _wait_until(
            lambda: fake_gateway_client.submitted_prompts == [("abcd1234", "through-gateway")]
        )
        assert transport.m_direct_messages == ["direct-before-gateway"]
        assert _FakeGatewayTrackingRuntime.m_started_session_ids == ["cao-rest-1"]
        assert _FakeGatewayTrackingRuntime.m_prompt_notes == ["through-gateway"]

    fallback_accepted = service.submit_managed_agent_request(
        "cao-rest-1",
        HoumaoManagedAgentSubmitPromptRequest(prompt="after-gateway-stop"),
    )
    assert fallback_accepted.disposition == "accepted"
    assert transport.m_direct_messages == [
        "direct-before-gateway",
        "after-gateway-stop",
    ]
    assert fake_gateway_client.submitted_prompts == [("abcd1234", "through-gateway")]
    assert _FakeGatewayTrackingRuntime.m_stopped_session_ids == ["cao-rest-1"]


def test_server_managed_headless_gateway_flow_covers_registry_and_degraded_control(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Server-managed headless agents should publish registry state, use live gateway control, and clean up on stop."""

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

        response = service.launch_headless_agent(
            HoumaoHeadlessLaunchRequest(
                tool="codex",
                working_directory=str(tmp_path.resolve()),
                agent_def_dir=str(agent_def_dir.resolve()),
                brain_manifest_path=str(brain_manifest_path.resolve()),
                role_name="r",
                agent_name="HOUMAO-headless",
                agent_id="agent-headless-1",
                mailbox=HoumaoHeadlessLaunchMailboxOptions(
                    transport="filesystem",
                    filesystem_root=str(mailbox_root.resolve()),
                    address="HOUMAO-headless@agents.localhost",
                ),
            )
        )

        manifest_path = Path(response.manifest_path)
        assert resolve_live_agent_record("agent-headless-1") is not None

        detail_without_gateway = service.managed_agent_state_detail(response.tracked_agent_id)
        assert detail_without_gateway.detail.transport == "headless"
        assert detail_without_gateway.summary_state.gateway is not None
        assert detail_without_gateway.summary_state.gateway.gateway_health == "not_attached"

        fake_session = _FakeGatewayHeadlessSession()
        fake_controller = _FakeGatewayHeadlessController(fake_session)
        gateway_root = manifest_path.parent / "gateway"
        paths = gateway_paths_from_manifest_path(manifest_path)
        assert paths is not None
        monkeypatch.setattr(
            "houmao.agents.realm_controller.gateway_service.HeadlessInteractiveSession",
            _FakeGatewayHeadlessSession,
        )
        monkeypatch.setattr(
            "houmao.agents.realm_controller.gateway_service.resume_runtime_session",
            lambda **_kwargs: fake_controller,
        )
        monkeypatch.setattr(
            "houmao.agents.realm_controller.gateway_service.tmux_session_exists",
            lambda **_kwargs: True,
        )

        try:
            with _LiveGatewayServer(gateway_root=gateway_root):
                detail_with_gateway = service.managed_agent_state_detail(response.tracked_agent_id)
                assert detail_with_gateway.detail.transport == "headless"
                assert detail_with_gateway.summary_state.gateway is not None
                assert detail_with_gateway.summary_state.gateway.gateway_health == "healthy"

                healthy_status_payload = json.loads(paths.state_path.read_text(encoding="utf-8"))
                healthy_current_instance_payload = json.loads(
                    paths.current_instance_path.read_text(encoding="utf-8")
                )

                accepted = service.submit_managed_agent_request(
                    response.tracked_agent_id,
                    HoumaoManagedAgentSubmitPromptRequest(prompt="through-gateway"),
                )
                assert accepted.disposition == "accepted"
                assert accepted.headless_turn_id is not None
                _wait_until(
                    lambda: (
                        fake_session.prompt_calls
                        == [("through-gateway", accepted.headless_turn_id)]
                    )
                )

            paths.state_path.write_text(
                json.dumps(healthy_status_payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            paths.current_instance_path.parent.mkdir(parents=True, exist_ok=True)
            paths.current_instance_path.write_text(
                json.dumps(healthy_current_instance_payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            degraded_detail = service.managed_agent_state_detail(response.tracked_agent_id)
            assert degraded_detail.detail.transport == "headless"
            with pytest.raises(HTTPException, match="attached gateway is unreachable") as exc_info:
                service.submit_managed_agent_request(
                    response.tracked_agent_id,
                    HoumaoManagedAgentSubmitPromptRequest(prompt="after-crash"),
                )
            assert exc_info.value.status_code == 503

            stop_response = service.stop_managed_agent(response.tracked_agent_id)
            assert stop_response.success is True
            assert resolve_live_agent_record("agent-headless-1") is None
        finally:
            fake_session.release_event.set()
