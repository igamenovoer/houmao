from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from houmao.agents.realm_controller.backends.tmux_runtime import TmuxPaneRecord
from houmao.server.child_cao import ChildCaoInstallResult
import houmao.server.tui.registry as tui_registry_module
from houmao.server.config import HoumaoServerConfig
from houmao.server.models import (
    HoumaoInstallAgentProfileRequest,
    HoumaoParsedSurface,
    HoumaoRegisterLaunchRequest,
)
from houmao.server.service import HoumaoServerService, ProxyResponse
from houmao.server.tui import (
    KnownSessionRecord,
    OfficialParseResult,
    PaneProcessInspection,
    ResolvedTmuxTarget,
)


def _json_response(payload: object, *, status_code: int = 200) -> ProxyResponse:
    return ProxyResponse(
        status_code=status_code,
        body=json.dumps(payload).encode("utf-8"),
        content_type="application/json",
        json_payload=payload,
    )


class _FakeTransport:
    def __init__(
        self, responses: dict[tuple[str, str, tuple[tuple[str, str], ...]], ProxyResponse]
    ) -> None:
        self.m_responses = responses
        self.m_calls: list[tuple[str, str, tuple[tuple[str, str], ...]]] = []

    def request(
        self,
        *,
        base_url: str,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
    ) -> ProxyResponse:
        del base_url
        key = (method.upper(), path, tuple(sorted((params or {}).items())))
        self.m_calls.append(key)
        try:
            return self.m_responses[key]
        except KeyError as exc:
            raise AssertionError(f"Unexpected proxy call: {key}") from exc


class _FakeChildManager:
    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:9890",
        healthy: bool = True,
        health_status: str | None = "ok",
        service_name: str | None = "cli-agent-orchestrator",
        error: str | None = None,
        ownership_file: Path | None = None,
        install_returncode: int = 0,
        install_stdout: str = "",
        install_stderr: str = "",
    ) -> None:
        self.m_base_url = base_url
        self.m_healthy = healthy
        self.m_health_status = health_status
        self.m_service_name = service_name
        self.m_error = error
        self.m_ownership_file = ownership_file or Path("/tmp/houmao-server-tests-no-ownership")
        self.m_install_returncode = install_returncode
        self.m_install_stdout = install_stdout
        self.m_install_stderr = install_stderr
        self.start_calls = 0
        self.stop_calls = 0
        self.install_calls: list[tuple[str, str, Path | None]] = []

    def start(self) -> None:
        self.start_calls += 1

    def stop(self) -> None:
        self.stop_calls += 1

    def inspect(self) -> object:
        config = type("Config", (), {"base_url": self.m_base_url})()
        status = type(
            "Status",
            (),
            {
                "healthy": self.m_healthy,
                "health_status": self.m_health_status,
                "service": self.m_service_name,
                "error": self.m_error,
            },
        )()
        return type("Inspection", (), {"config": config, "status": status})()

    def ownership_file_path(self) -> Path:
        return self.m_ownership_file

    def install_agent_profile(
        self,
        *,
        agent_source: str,
        provider: str,
        working_directory: Path | None = None,
    ) -> ChildCaoInstallResult:
        self.install_calls.append((agent_source, provider, working_directory))
        return ChildCaoInstallResult(
            agent_source=agent_source,
            provider=provider,
            working_directory=working_directory,
            returncode=self.m_install_returncode,
            stdout=self.m_install_stdout,
            stderr=self.m_install_stderr,
        )


class _FakeTmuxTransportResolver:
    def __init__(self, *, output_text: str) -> None:
        self.m_output_text = output_text
        self.m_resolve_calls: list[tuple[str, str | None]] = []
        self.m_capture_calls = 0

    def resolve_target(self, *, session_name: str, window_name: str | None) -> ResolvedTmuxTarget:
        self.m_resolve_calls.append((session_name, window_name))
        return ResolvedTmuxTarget(
            pane=TmuxPaneRecord(
                pane_id="%9",
                session_name=session_name,
                window_id="@2",
                window_name=window_name or "developer-1",
                pane_index="0",
                pane_active=True,
                pane_pid=4321,
            )
        )

    def capture_text(self, *, target: ResolvedTmuxTarget) -> str:
        assert target.pane.pane_id == "%9"
        self.m_capture_calls += 1
        return self.m_output_text


class _FakeProcessInspector:
    def __init__(self, inspection: PaneProcessInspection) -> None:
        self.m_inspection = inspection
        self.m_calls: list[tuple[str, int | None]] = []

    def inspect(self, *, tool: str, pane_pid: int | None) -> PaneProcessInspection:
        self.m_calls.append((tool, pane_pid))
        return self.m_inspection


class _FakeParserAdapter:
    def __init__(self, results: list[OfficialParseResult], *, supports_tool: bool = True) -> None:
        self.m_results = results
        self.m_supports_tool = supports_tool
        self.m_capture_baseline_calls: list[tuple[str, str]] = []
        self.m_parse_calls: list[tuple[str, int]] = []

    def supports_tool(self, *, tool: str) -> bool:
        del tool
        return self.m_supports_tool

    def capture_baseline(self, *, tool: str, output_text: str) -> int:
        self.m_capture_baseline_calls.append((tool, output_text))
        return 17

    def parse(self, *, tool: str, output_text: str, baseline_pos: int) -> OfficialParseResult:
        self.m_parse_calls.append((tool, baseline_pos))
        del output_text
        return self.m_results.pop(0)


class _FakeKnownSessionRegistry:
    def __init__(self, records: dict[str, KnownSessionRecord] | None = None) -> None:
        self.m_records = records or {}

    def load_live_sessions(self) -> dict[str, KnownSessionRecord]:
        return dict(self.m_records)


def _ready_surface() -> HoumaoParsedSurface:
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


def _processing_surface() -> HoumaoParsedSurface:
    return HoumaoParsedSurface(
        parser_family="codex_shadow",
        parser_preset_id="codex",
        parser_preset_version="1.0.0",
        availability="supported",
        business_state="working",
        input_mode="closed",
        ui_context="normal_prompt",
        normalized_projection_text="processing",
        dialog_text="processing",
        dialog_head="processing",
        dialog_tail="processing",
        anomaly_codes=[],
        baseline_invalidated=False,
        operator_blocked_excerpt=None,
    )


def test_register_launch_persists_registration_and_creates_dormant_tracker(tmp_path: Path) -> None:
    transport = _FakeTransport(
        {
            ("GET", "/sessions/cao-gpu/terminals", ()): _json_response(
                [
                    {
                        "id": "abcd1234",
                        "name": "gpu",
                        "provider": "codex",
                        "session_name": "cao-gpu",
                        "agent_profile": "runtime-profile",
                        "status": "idle",
                    }
                ]
            ),
            ("GET", "/terminals/abcd1234", ()): _json_response(
                {
                    "id": "abcd1234",
                    "name": "gpu",
                    "provider": "codex",
                    "session_name": "cao-gpu",
                    "agent_profile": "runtime-profile",
                    "status": "idle",
                }
            ),
        }
    )
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=transport,
        child_manager=_FakeChildManager(),
    )

    response = service.register_launch(
        HoumaoRegisterLaunchRequest(
            session_name="cao-gpu",
            tool="codex",
            manifest_path="/tmp/manifest.json",
            session_root="/tmp/session-root",
            agent_name="AGENTSYS-gpu",
            agent_id="AGENTSYS-gpu",
            tmux_session_name="AGENTSYS-gpu",
        )
    )

    assert response.success is True
    assert response.terminal_id == "abcd1234"
    state = service.terminal_state("abcd1234")
    assert state.terminal_id == "abcd1234"
    assert state.tracked_session.session_name == "cao-gpu"
    assert state.tracked_session.tool == "codex"
    assert state.transport_state == "tmux_missing"
    registration_path = (
        tmp_path
        / "houmao_servers"
        / "127.0.0.1-9889"
        / "sessions"
        / "cao-gpu"
        / "registration.json"
    )
    payload = json.loads(registration_path.read_text(encoding="utf-8"))
    assert payload["terminal_id"] == "abcd1234"


def test_refresh_terminal_state_uses_direct_tmux_process_and_parser(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    transport = _FakeTransport(
        {
            ("GET", "/terminals/abcd1234", ()): _json_response(
                {
                    "id": "abcd1234",
                    "name": "gpu",
                    "provider": "codex",
                    "session_name": "cao-gpu",
                    "agent_profile": "runtime-profile",
                    "status": "idle",
                }
            )
        }
    )
    tmux_transport = _FakeTmuxTransportResolver(output_text="visible tmux text")
    process_inspector = _FakeProcessInspector(
        PaneProcessInspection(
            process_state="tui_up",
            matched_process_names=["codex"],
            matched_processes=(),
        )
    )
    parser_adapter = _FakeParserAdapter(
        [OfficialParseResult(parsed_surface=_ready_surface(), parse_error=None)]
    )
    monkeypatch.setattr("houmao.server.service.tmux_session_exists", lambda **_: True)
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=transport,
        child_manager=_FakeChildManager(),
        transport_resolver=tmux_transport,
        process_inspector=process_inspector,
        parser_adapter=parser_adapter,
    )
    service.register_launch(
        HoumaoRegisterLaunchRequest(
            session_name="cao-gpu",
            terminal_id="abcd1234",
            tool="codex",
            tmux_session_name="AGENTSYS-gpu",
        )
    )
    transport.m_calls.clear()

    state = service.refresh_terminal_state("abcd1234")

    assert state.transport_state == "tmux_up"
    assert state.process_state == "tui_up"
    assert state.parse_status == "parsed"
    assert state.operator_state.status == "ready"
    assert state.parsed_surface is not None
    assert state.parsed_surface.normalized_projection_text == "ready prompt"
    assert state.probe_snapshot is not None
    assert state.probe_snapshot.pane_id == "%9"
    assert state.probe_snapshot.matched_process_names == ["codex"]
    assert state.lifecycle_timing.completion_stability_seconds == 1.0
    assert state.lifecycle_timing.unknown_to_stalled_timeout_seconds == 30.0
    assert transport.m_calls == []
    assert tmux_transport.m_resolve_calls == [("AGENTSYS-gpu", None)]
    assert process_inspector.m_calls == [("codex", 4321)]
    assert parser_adapter.m_capture_baseline_calls == [("codex", "visible tmux text")]
    assert parser_adapter.m_parse_calls == [("codex", 17)]


def test_refresh_terminal_state_records_tui_down_but_keeps_tracker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("houmao.server.service.tmux_session_exists", lambda **_: True)
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=_FakeTransport(
            {
                ("GET", "/terminals/abcd1234", ()): _json_response(
                    {
                        "id": "abcd1234",
                        "name": "gpu",
                        "provider": "codex",
                        "session_name": "cao-gpu",
                        "agent_profile": "runtime-profile",
                        "status": "idle",
                    }
                )
            }
        ),
        child_manager=_FakeChildManager(),
        transport_resolver=_FakeTmuxTransportResolver(output_text="unused"),
        process_inspector=_FakeProcessInspector(
            PaneProcessInspection(
                process_state="tui_down",
                matched_process_names=[],
                matched_processes=(),
            )
        ),
        parser_adapter=_FakeParserAdapter([], supports_tool=True),
    )
    service.register_launch(
        HoumaoRegisterLaunchRequest(
            session_name="cao-gpu",
            terminal_id="abcd1234",
            tool="codex",
            tmux_session_name="AGENTSYS-gpu",
        )
    )

    state = service.refresh_terminal_state("abcd1234")

    assert state.process_state == "tui_down"
    assert state.parse_status == "skipped_tui_down"
    assert state.operator_state.status == "tui_down"
    assert service.terminal_state("abcd1234").operator_state.status == "tui_down"


def test_poll_known_session_marks_tmux_missing_and_requests_worker_exit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("houmao.server.service.tmux_session_exists", lambda **_: False)
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=_FakeTransport(
            {
                ("GET", "/terminals/abcd1234", ()): _json_response(
                    {
                        "id": "abcd1234",
                        "name": "gpu",
                        "provider": "codex",
                        "session_name": "cao-gpu",
                        "agent_profile": "runtime-profile",
                        "status": "idle",
                    }
                )
            }
        ),
        child_manager=_FakeChildManager(),
    )
    service.register_launch(
        HoumaoRegisterLaunchRequest(
            session_name="cao-gpu",
            terminal_id="abcd1234",
            tool="codex",
            tmux_session_name="AGENTSYS-gpu",
        )
    )

    keep_running = service.poll_known_session("cao-gpu")

    assert keep_running is False
    state = service.terminal_state("abcd1234")
    assert state.transport_state == "tmux_missing"
    assert state.parse_status == "transport_unavailable"


def test_terminal_history_returns_recent_in_memory_transitions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("houmao.server.service.tmux_session_exists", lambda **_: True)
    parser_adapter = _FakeParserAdapter(
        [
            OfficialParseResult(parsed_surface=_ready_surface(), parse_error=None),
            OfficialParseResult(parsed_surface=_processing_surface(), parse_error=None),
        ]
    )
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=_FakeTransport(
            {
                ("GET", "/terminals/abcd1234", ()): _json_response(
                    {
                        "id": "abcd1234",
                        "name": "gpu",
                        "provider": "codex",
                        "session_name": "cao-gpu",
                        "agent_profile": "runtime-profile",
                        "status": "idle",
                    }
                )
            }
        ),
        child_manager=_FakeChildManager(),
        transport_resolver=_FakeTmuxTransportResolver(output_text="visible tmux text"),
        process_inspector=_FakeProcessInspector(
            PaneProcessInspection(
                process_state="tui_up",
                matched_process_names=["codex"],
                matched_processes=(),
            )
        ),
        parser_adapter=parser_adapter,
    )
    service.register_launch(
        HoumaoRegisterLaunchRequest(
            session_name="cao-gpu",
            terminal_id="abcd1234",
            tool="codex",
            tmux_session_name="AGENTSYS-gpu",
        )
    )

    service.refresh_terminal_state("abcd1234")
    service.refresh_terminal_state("abcd1234")
    history = service.terminal_history("abcd1234", limit=1)

    assert len(history.entries) == 1
    assert history.entries[0].operator_status == "processing"
    assert "operator_status" in history.entries[0].changed_fields


def test_startup_persists_current_instance_and_child_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ownership_file = tmp_path / "child-cao" / "ownership.json"
    ownership_file.parent.mkdir(parents=True, exist_ok=True)
    ownership_file.write_text("{}\n", encoding="utf-8")
    child_manager = _FakeChildManager(ownership_file=ownership_file)
    monkeypatch.setattr(
        "houmao.server.tui.supervisor.TuiTrackingSupervisor.start", lambda self: None
    )
    monkeypatch.setattr(
        "houmao.server.tui.supervisor.TuiTrackingSupervisor.request_reconcile",
        lambda self: None,
    )
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=_FakeTransport({}),
        child_manager=child_manager,
    )

    service.startup()

    current_instance_path = (
        tmp_path / "houmao_servers" / "127.0.0.1-9889" / "run" / "current-instance.json"
    )
    current_instance = json.loads(current_instance_path.read_text(encoding="utf-8"))
    health = service.health_response()

    assert child_manager.start_calls == 1
    assert current_instance["status"] == "ok"
    assert current_instance["api_base_url"] == "http://127.0.0.1:9889"
    assert current_instance["child_cao"]["api_base_url"] == "http://127.0.0.1:9890"
    assert current_instance["child_cao"]["derived_port"] == 9890
    assert current_instance["child_cao"]["ownership_file"] == str(ownership_file)
    assert health.status == "ok"
    assert health.houmao_service == "houmao-server"
    assert health.child_cao is not None
    assert health.child_cao.healthy is True


def test_shutdown_stops_child_manager_when_started(tmp_path: Path) -> None:
    child_manager = _FakeChildManager()
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=_FakeTransport({}),
        child_manager=child_manager,
    )

    service.shutdown()

    assert child_manager.stop_calls == 1


def test_install_agent_profile_routes_through_child_manager(tmp_path: Path) -> None:
    child_manager = _FakeChildManager()
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=_FakeTransport({}),
        child_manager=child_manager,
    )

    response = service.install_agent_profile(
        HoumaoInstallAgentProfileRequest(
            agent_source="projection-demo",
            provider="codex",
            working_directory=str(tmp_path),
        )
    )

    assert response.success is True
    assert child_manager.install_calls == [("projection-demo", "codex", tmp_path.resolve())]
    assert "Pair-owned install completed" in response.detail


def test_install_agent_profile_returns_explicit_failure_without_child_path_leak(
    tmp_path: Path,
) -> None:
    child_manager = _FakeChildManager(
        install_returncode=7,
        install_stdout="internal success path /tmp/hidden/home",
        install_stderr="internal failure path /tmp/hidden/home",
    )
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=_FakeTransport({}),
        child_manager=child_manager,
    )

    with pytest.raises(HTTPException) as exc_info:
        service.install_agent_profile(
            HoumaoInstallAgentProfileRequest(
                agent_source="projection-demo",
                provider="codex",
                working_directory=str(tmp_path),
            )
        )

    assert exc_info.value.status_code == 502
    assert "Pair-owned install failed through managed child CAO state" in str(exc_info.value.detail)
    assert "/tmp/hidden/home" not in str(exc_info.value.detail)


def test_register_launch_rejects_invalid_registration_session_name(tmp_path: Path) -> None:
    transport = _FakeTransport({})
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=transport,
        child_manager=_FakeChildManager(),
    )

    with pytest.raises(HTTPException, match="Invalid server-owned registration session name"):
        service.register_launch(
            HoumaoRegisterLaunchRequest(
                session_name="../../escaped",
                terminal_id="abcd1234",
                tool="codex",
            )
        )

    assert transport.m_calls == []


def test_remove_registration_dir_stays_contained_under_sessions_root(tmp_path: Path) -> None:
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=_FakeTransport({}),
        child_manager=_FakeChildManager(),
    )
    escaped_root = tmp_path / "houmao_servers" / "escaped"
    escaped_root.mkdir(parents=True, exist_ok=True)
    escaped_registration = escaped_root / "registration.json"
    escaped_registration.write_text("{}\n", encoding="utf-8")

    service._remove_registration_dir(session_name="../../escaped")

    assert escaped_registration.exists() is True


def test_handle_poll_exception_records_probe_error_state(tmp_path: Path) -> None:
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=_FakeTransport(
            {
                ("GET", "/terminals/abcd1234", ()): _json_response(
                    {
                        "id": "abcd1234",
                        "name": "gpu",
                        "provider": "codex",
                        "session_name": "cao-gpu",
                        "agent_profile": "runtime-profile",
                        "status": "idle",
                    }
                )
            }
        ),
        child_manager=_FakeChildManager(),
    )
    service.register_launch(
        HoumaoRegisterLaunchRequest(
            session_name="cao-gpu",
            terminal_id="abcd1234",
            tool="codex",
            tmux_session_name="AGENTSYS-gpu",
        )
    )

    service.handle_poll_exception("cao-gpu", RuntimeError("boom"))

    state = service.terminal_state("abcd1234")
    assert state.transport_state == "probe_error"
    assert state.process_state == "probe_error"
    assert state.parse_status == "probe_error"
    assert state.probe_error is not None
    assert state.probe_error.kind == "tracking_runtime_error"


def test_supervisor_reconcile_releases_missing_session_from_live_lookup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry = _FakeKnownSessionRegistry()
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=_FakeTransport(
            {
                ("GET", "/terminals/abcd1234", ()): _json_response(
                    {
                        "id": "abcd1234",
                        "name": "gpu",
                        "provider": "codex",
                        "session_name": "cao-gpu",
                        "agent_profile": "runtime-profile",
                        "status": "idle",
                    }
                )
            }
        ),
        child_manager=_FakeChildManager(),
        known_session_registry=registry,
    )
    service.register_launch(
        HoumaoRegisterLaunchRequest(
            session_name="cao-gpu",
            terminal_id="abcd1234",
            tool="codex",
            tmux_session_name="AGENTSYS-gpu",
        )
    )
    registry.m_records = {
        "cao-gpu": KnownSessionRecord(
            tracked_session_id="cao-gpu",
            session_name="cao-gpu",
            tool="codex",
            terminal_id="abcd1234",
            tmux_session_name="AGENTSYS-gpu",
            tmux_window_name="developer-1",
            manifest_path=None,
            session_root=None,
            agent_name=None,
            agent_id=None,
        )
    }
    monkeypatch.setattr("houmao.server.tui.supervisor.SessionWatchWorker.start", lambda self: None)
    monkeypatch.setattr(
        "houmao.server.tui.supervisor.SessionWatchWorker.stop", lambda self, *, join=True: None
    )
    monkeypatch.setattr(
        "houmao.server.tui.supervisor.SessionWatchWorker.is_alive", lambda self: True
    )

    service.m_supervisor._reconcile_once()
    registry.m_records = {}
    service.m_supervisor._reconcile_once()

    with pytest.raises(HTTPException, match="Unknown terminal `abcd1234`"):
        service.terminal_state("abcd1234")


def test_refresh_terminal_state_uses_registration_window_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    transport = _FakeTransport(
        {
            ("GET", "/terminals/abcd1234", ()): _json_response(
                {
                    "id": "abcd1234",
                    "name": "gpu",
                    "provider": "codex",
                    "session_name": "cao-gpu",
                    "agent_profile": "runtime-profile",
                    "status": "idle",
                }
            )
        }
    )
    tmux_transport = _FakeTmuxTransportResolver(output_text="visible tmux text")
    process_inspector = _FakeProcessInspector(
        PaneProcessInspection(
            process_state="tui_up",
            matched_process_names=["codex"],
            matched_processes=(),
        )
    )
    parser_adapter = _FakeParserAdapter(
        [OfficialParseResult(parsed_surface=_ready_surface(), parse_error=None)]
    )
    monkeypatch.setattr("houmao.server.service.tmux_session_exists", lambda **_: True)
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=transport,
        child_manager=_FakeChildManager(),
        transport_resolver=tmux_transport,
        process_inspector=process_inspector,
        parser_adapter=parser_adapter,
    )
    service.register_launch(
        HoumaoRegisterLaunchRequest(
            session_name="cao-gpu",
            terminal_id="abcd1234",
            tool="codex",
            tmux_session_name="AGENTSYS-gpu",
            tmux_window_name="developer-1",
        )
    )

    service.refresh_terminal_state("abcd1234")

    assert tmux_transport.m_resolve_calls == [("AGENTSYS-gpu", "developer-1")]


def test_register_launch_enriches_dormant_tracker_window_name_from_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        "houmao.server.tui.registry._load_manifest_metadata",
        lambda *, manifest_path: tui_registry_module._ManifestMetadata(
            tool=None,
            terminal_id=None,
            tmux_session_name=None,
            tmux_window_name="developer-2",
            session_root=(manifest_path.parent / "session-root").resolve(),
        ),
    )
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=_FakeTransport(
            {
                ("GET", "/terminals/abcd1234", ()): _json_response(
                    {
                        "id": "abcd1234",
                        "name": "gpu",
                        "provider": "codex",
                        "session_name": "cao-gpu",
                        "agent_profile": "runtime-profile",
                        "status": "idle",
                    }
                )
            }
        ),
        child_manager=_FakeChildManager(),
    )

    service.register_launch(
        HoumaoRegisterLaunchRequest(
            session_name="cao-gpu",
            terminal_id="abcd1234",
            tool="codex",
            tmux_session_name="AGENTSYS-gpu",
            manifest_path=str(manifest_path),
        )
    )

    state = service.terminal_state("abcd1234")
    assert state.tracked_session.tmux_window_name == "developer-2"
