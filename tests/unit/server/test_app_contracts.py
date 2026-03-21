from __future__ import annotations

import ast
import json
from pathlib import Path

from fastapi.routing import APIRoute
from pydantic_core import PydanticUndefined

from houmao.server.app import create_app
from houmao.server.models import (
    ChildCaoStatus,
    HoumaoCurrentInstance,
    HoumaoHeadlessLaunchRequest,
    HoumaoHeadlessLaunchResponse,
    HoumaoHeadlessTurnAcceptedResponse,
    HoumaoHeadlessTurnEventsResponse,
    HoumaoHeadlessTurnRequest,
    HoumaoHeadlessTurnStatusResponse,
    HoumaoHealthResponse,
    HoumaoInstallAgentProfileRequest,
    HoumaoInstallAgentProfileResponse,
    HoumaoManagedAgentActionResponse,
    HoumaoManagedAgentHistoryEntry,
    HoumaoManagedAgentHistoryResponse,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentLastTurnView,
    HoumaoManagedAgentListResponse,
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentTurnView,
    HoumaoParsedSurface,
    HoumaoProbeSnapshot,
    HoumaoRecentTransition,
    HoumaoRegisterLaunchRequest,
    HoumaoRegisterLaunchResponse,
    HoumaoStabilityMetadata,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalStateResponse,
    HoumaoTrackedDiagnostics,
    HoumaoTrackedLastTurn,
    HoumaoTrackedSurface,
    HoumaoTrackedSessionIdentity,
    HoumaoTrackedTurn,
)
from houmao.server.service import ProxyResponse


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _extract_upstream_http_routes() -> set[tuple[str, str]]:
    tree = ast.parse(
        (
            _repo_root()
            / "extern"
            / "tracked"
            / "cli-agent-orchestrator"
            / "src"
            / "cli_agent_orchestrator"
            / "api"
            / "main.py"
        ).read_text(encoding="utf-8")
    )
    routes: set[tuple[str, str]] = set()
    for node in tree.body:
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue
            if not isinstance(decorator.func.value, ast.Name) or decorator.func.value.id != "app":
                continue
            if not decorator.args:
                continue
            path_literal = decorator.args[0]
            if not isinstance(path_literal, ast.Constant) or not isinstance(
                path_literal.value, str
            ):
                continue
            routes.add((decorator.func.attr.upper(), path_literal.value))
    return routes


def _json_response(payload: object, *, status_code: int = 200) -> ProxyResponse:
    return ProxyResponse(
        status_code=status_code,
        body=json.dumps(payload).encode("utf-8"),
        content_type="application/json",
        json_payload=payload,
    )


class _AppServiceDouble:
    def __init__(
        self,
        *,
        responses: dict[tuple[str, str, tuple[tuple[str, str], ...]], ProxyResponse] | None = None,
    ) -> None:
        self.m_responses = responses or {}
        self.m_proxy_calls: list[tuple[str, str, tuple[tuple[str, str], ...]]] = []
        self.m_synced_payloads: list[object] = []
        self.m_prompt_submissions: list[tuple[str, str]] = []
        self.m_tracking_debug_events: list[dict[str, object]] = []
        self.m_deleted_sessions: list[str] = []
        self.m_deleted_terminals: list[str] = []
        self.m_install_requests: list[HoumaoInstallAgentProfileRequest] = []
        self.m_register_requests: list[HoumaoRegisterLaunchRequest] = []
        self.m_history_calls: list[tuple[str, int]] = []
        self.m_headless_launch_requests: list[HoumaoHeadlessLaunchRequest] = []
        self.m_managed_agent_history_calls: list[tuple[str, int]] = []
        self.m_stop_calls: list[str] = []
        self.m_turn_requests: list[tuple[str, HoumaoHeadlessTurnRequest]] = []
        self.m_turn_status_calls: list[tuple[str, str]] = []
        self.m_turn_events_calls: list[tuple[str, str]] = []
        self.m_turn_artifact_calls: list[tuple[str, str, str]] = []
        self.m_interrupt_calls: list[str] = []

    def startup(self) -> None:
        return None

    def shutdown(self) -> None:
        return None

    def proxy(
        self, *, method: str, path: str, params: dict[str, str] | None = None
    ) -> ProxyResponse:
        key = (method.upper(), path, tuple(sorted((params or {}).items())))
        self.m_proxy_calls.append(key)
        try:
            return self.m_responses[key]
        except KeyError as exc:
            raise AssertionError(f"Unexpected proxy call: {key}") from exc

    def sync_created_terminal(self, payload: object) -> None:
        self.m_synced_payloads.append(payload)

    def handle_deleted_session(self, session_name: str) -> None:
        self.m_deleted_sessions.append(session_name)

    def handle_deleted_terminal(self, terminal_id: str) -> None:
        self.m_deleted_terminals.append(terminal_id)

    def note_prompt_submission(self, *, terminal_id: str, message: str) -> None:
        self.m_prompt_submissions.append((terminal_id, message))

    def emit_tracking_debug(self, **payload: object) -> None:
        self.m_tracking_debug_events.append(dict(payload))

    def health_response(self) -> HoumaoHealthResponse:
        return HoumaoHealthResponse(
            status="ok",
            service="cli-agent-orchestrator",
            child_cao=ChildCaoStatus(
                api_base_url="http://127.0.0.1:9890",
                healthy=True,
                health_status="ok",
                service="cli-agent-orchestrator",
                error=None,
                derived_port=9890,
                ownership_file="/tmp/child/ownership.json",
            ),
        )

    def current_instance_response(self) -> HoumaoCurrentInstance:
        return HoumaoCurrentInstance(
            pid=12345,
            api_base_url="http://127.0.0.1:9889",
            server_root="/tmp/houmao-server",
            child_cao=ChildCaoStatus(
                api_base_url="http://127.0.0.1:9890",
                healthy=True,
                health_status="ok",
                service="cli-agent-orchestrator",
                error=None,
                derived_port=9890,
                ownership_file="/tmp/child/ownership.json",
            ),
        )

    def install_agent_profile(
        self, request_model: HoumaoInstallAgentProfileRequest
    ) -> HoumaoInstallAgentProfileResponse:
        self.m_install_requests.append(request_model)
        return HoumaoInstallAgentProfileResponse(
            success=True,
            agent_source=request_model.agent_source,
            provider=request_model.provider,
            detail="Pair-owned install completed.",
        )

    def register_launch(
        self, request_model: HoumaoRegisterLaunchRequest
    ) -> HoumaoRegisterLaunchResponse:
        self.m_register_requests.append(request_model)
        terminal_id = request_model.terminal_id or "abcd1234"
        return HoumaoRegisterLaunchResponse(
            success=True,
            session_name=request_model.session_name,
            terminal_id=terminal_id,
        )

    def terminal_state(self, terminal_id: str) -> HoumaoTerminalStateResponse:
        return HoumaoTerminalStateResponse(
            terminal_id=terminal_id,
            tracked_session=HoumaoTrackedSessionIdentity(
                tracked_session_id="cao-gpu",
                session_name="cao-gpu",
                tool="codex",
                tmux_session_name="AGENTSYS-gpu",
                terminal_aliases=[terminal_id],
            ),
            diagnostics=HoumaoTrackedDiagnostics(
                availability="available",
                transport_state="tmux_up",
                process_state="tui_up",
                parse_status="parsed",
                probe_error=None,
                parse_error=None,
            ),
            transport_state="tmux_up",
            process_state="tui_up",
            parse_status="parsed",
            probe_snapshot=HoumaoProbeSnapshot(
                observed_at_utc="2026-03-19T10:00:00+00:00",
                pane_id="%9",
                pane_pid=4321,
                captured_text_hash="abc123",
                captured_text_length=12,
                captured_text_excerpt="hello world",
                matched_process_names=["codex"],
            ),
            probe_error=None,
            parse_error=None,
            parsed_surface=HoumaoParsedSurface(
                parser_family="codex_shadow",
                parser_preset_id="codex",
                parser_preset_version="1.0.0",
                availability="supported",
                business_state="idle",
                input_mode="freeform",
                ui_context="normal_prompt",
                normalized_projection_text="hello world",
                dialog_text="hello world",
                dialog_head="hello world",
                dialog_tail="hello world",
                anomaly_codes=[],
                baseline_invalidated=False,
                operator_blocked_excerpt=None,
            ),
            surface=HoumaoTrackedSurface(
                accepting_input="yes",
                editing_input="no",
                ready_posture="yes",
            ),
            turn=HoumaoTrackedTurn(phase="ready"),
            last_turn=HoumaoTrackedLastTurn(result="none", source="none", updated_at_utc=None),
            stability=HoumaoStabilityMetadata(
                signature="deadbeef",
                stable=True,
                stable_for_seconds=3.0,
                stable_since_utc="2026-03-19T09:59:57+00:00",
            ),
            recent_transitions=[],
        )

    def terminal_history(self, terminal_id: str, *, limit: int) -> HoumaoTerminalHistoryResponse:
        self.m_history_calls.append((terminal_id, limit))
        return HoumaoTerminalHistoryResponse(
            terminal_id=terminal_id,
            tracked_session_id="cao-gpu",
            entries=[
                HoumaoRecentTransition(
                    recorded_at_utc="2026-03-19T10:00:00+00:00",
                    summary=f"limit={limit}",
                    changed_fields=["turn_phase"],
                    diagnostics_availability="available",
                    turn_phase="ready",
                    last_turn_result="none",
                    last_turn_source="none",
                    transport_state="tmux_up",
                    process_state="tui_up",
                    parse_status="parsed",
                    operator_status="ready",
                ),
            ],
        )

    def list_managed_agents(self) -> HoumaoManagedAgentListResponse:
        return HoumaoManagedAgentListResponse(agents=[self.managed_agent("claude-headless-1")])

    def managed_agent(self, agent_ref: str) -> HoumaoManagedAgentIdentity:
        assert agent_ref == "claude-headless-1"
        return HoumaoManagedAgentIdentity(
            tracked_agent_id="claude-headless-1",
            transport="headless",
            tool="claude",
            runtime_session_id="claude-headless-1",
            tmux_session_name="AGENTSYS-gpu",
            manifest_path="/tmp/manifest.json",
            session_root="/tmp/session-root",
            agent_name="AGENTSYS-gpu",
            agent_id="agent-1234",
        )

    def managed_agent_state(self, agent_ref: str) -> HoumaoManagedAgentStateResponse:
        identity = self.managed_agent(agent_ref)
        return HoumaoManagedAgentStateResponse(
            tracked_agent_id=identity.tracked_agent_id,
            identity=identity,
            availability="available",
            turn=HoumaoManagedAgentTurnView(phase="ready", active_turn_id=None),
            last_turn=HoumaoManagedAgentLastTurnView(
                result="none",
                turn_id=None,
                turn_index=None,
                updated_at_utc=None,
            ),
            diagnostics=[],
        )

    def managed_agent_history(
        self,
        agent_ref: str,
        *,
        limit: int,
    ) -> HoumaoManagedAgentHistoryResponse:
        self.m_managed_agent_history_calls.append((agent_ref, limit))
        return HoumaoManagedAgentHistoryResponse(
            tracked_agent_id="claude-headless-1",
            entries=[
                HoumaoManagedAgentHistoryEntry(
                    recorded_at_utc="2026-03-20T09:00:00+00:00",
                    summary=f"managed-limit={limit}",
                    availability="available",
                    turn_phase="ready",
                    last_turn_result="none",
                    turn_id=None,
                )
            ],
        )

    def launch_headless_agent(
        self,
        request_model: HoumaoHeadlessLaunchRequest,
    ) -> HoumaoHeadlessLaunchResponse:
        self.m_headless_launch_requests.append(request_model)
        return HoumaoHeadlessLaunchResponse(
            success=True,
            tracked_agent_id="claude-headless-1",
            identity=self.managed_agent("claude-headless-1"),
            manifest_path="/tmp/manifest.json",
            session_root="/tmp/session-root",
            detail="launched",
        )

    def stop_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentActionResponse:
        self.m_stop_calls.append(agent_ref)
        return HoumaoManagedAgentActionResponse(
            success=True,
            tracked_agent_id="claude-headless-1",
            detail="stopped",
            turn_id=None,
        )

    def submit_headless_turn(
        self,
        agent_ref: str,
        request_model: HoumaoHeadlessTurnRequest,
    ) -> HoumaoHeadlessTurnAcceptedResponse:
        self.m_turn_requests.append((agent_ref, request_model))
        return HoumaoHeadlessTurnAcceptedResponse(
            success=True,
            tracked_agent_id="claude-headless-1",
            turn_id="turn-123",
            turn_index=1,
            status="active",
            detail="accepted",
        )

    def headless_turn_status(
        self,
        agent_ref: str,
        turn_id: str,
    ) -> HoumaoHeadlessTurnStatusResponse:
        self.m_turn_status_calls.append((agent_ref, turn_id))
        return HoumaoHeadlessTurnStatusResponse(
            tracked_agent_id="claude-headless-1",
            turn_id=turn_id,
            turn_index=1,
            status="completed",
            started_at_utc="2026-03-20T09:00:00+00:00",
            completed_at_utc="2026-03-20T09:01:00+00:00",
            returncode=0,
            completion_source="tmux_wait_for",
            stdout_path="/tmp/stdout.jsonl",
            stderr_path="/tmp/stderr.log",
            status_path="/tmp/exitcode",
            history_summary="done",
            error=None,
        )

    def headless_turn_events(
        self,
        agent_ref: str,
        turn_id: str,
    ) -> HoumaoHeadlessTurnEventsResponse:
        self.m_turn_events_calls.append((agent_ref, turn_id))
        return HoumaoHeadlessTurnEventsResponse(
            tracked_agent_id="claude-headless-1",
            turn_id=turn_id,
            entries=[],
        )

    def headless_turn_artifact_text(
        self,
        agent_ref: str,
        turn_id: str,
        *,
        artifact_name: str,
    ) -> str:
        self.m_turn_artifact_calls.append((agent_ref, turn_id, artifact_name))
        return f"{artifact_name}:{turn_id}"

    def interrupt_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentActionResponse:
        self.m_interrupt_calls.append(agent_ref)
        return HoumaoManagedAgentActionResponse(
            success=True,
            tracked_agent_id="claude-headless-1",
            detail="interrupted",
            turn_id="turn-123",
        )


def _compat_route_inventory() -> set[tuple[str, str]]:
    app = create_app(service=_AppServiceDouble())
    routes: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/cao/"):
            continue
        for method in route.methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            routes.add((method, route.path))
    return routes


def _extract_namespaced_upstream_http_routes() -> set[tuple[str, str]]:
    return {(method, f"/cao{path}") for method, path in _extract_upstream_http_routes()}


def _route(path: str, method: str, *, app=None) -> APIRoute:
    resolved_app = app or create_app(service=_AppServiceDouble())
    for route in resolved_app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path == path and method.upper() in route.methods:
            return route
    raise AssertionError(f"Route not found: {method.upper()} {path}")


def _query_contract(route: APIRoute) -> dict[str, dict[str, object]]:
    contract: dict[str, dict[str, object]] = {}
    for param in route.dependant.query_params:
        le_constraint = None
        for metadata in param.field_info.metadata:
            if hasattr(metadata, "le"):
                le_constraint = metadata.le
        contract[param.alias] = {
            "required": param.default is PydanticUndefined,
            "default": None if param.default is PydanticUndefined else param.default,
            "le": le_constraint,
        }
    return contract


def test_compat_route_inventory_matches_pinned_upstream() -> None:
    assert _compat_route_inventory() == _extract_namespaced_upstream_http_routes()


def test_create_session_route_query_contract_matches_pinned_upstream_expectations() -> None:
    contract = _query_contract(_route("/cao/sessions", "POST"))

    assert contract == {
        "provider": {"required": True, "default": None, "le": None},
        "agent_profile": {"required": True, "default": None, "le": None},
        "session_name": {"required": False, "default": None, "le": None},
        "working_directory": {"required": False, "default": None, "le": None},
    }


def test_inbox_messages_route_query_contract_matches_pinned_upstream_expectations() -> None:
    contract = _query_contract(_route("/cao/terminals/{terminal_id}/inbox/messages", "GET"))

    assert contract == {
        "limit": {"required": False, "default": 10, "le": 100},
        "status": {"required": False, "default": None, "le": None},
    }


def test_output_route_query_contract_matches_pinned_upstream_expectations() -> None:
    contract = _query_contract(_route("/cao/terminals/{terminal_id}/output", "GET"))

    assert contract == {
        "mode": {"required": False, "default": "full", "le": None},
    }


def test_create_session_endpoint_forwards_expected_request_surface() -> None:
    expected_call = (
        "POST",
        "/sessions",
        (
            ("agent_profile", "gpu-kernel-coder"),
            ("provider", "codex"),
            ("working_directory", "/tmp/workspace"),
        ),
    )
    response_payload = {
        "id": "abcd1234",
        "name": "gpu",
        "provider": "codex",
        "session_name": "cao-gpu",
        "agent_profile": "gpu-kernel-coder",
        "status": "idle",
    }
    service = _AppServiceDouble(
        responses={expected_call: _json_response(response_payload, status_code=201)}
    )
    app = create_app(service=service)
    route = next(
        candidate
        for candidate in app.routes
        if isinstance(candidate, APIRoute)
        and candidate.path == "/cao/sessions"
        and "POST" in candidate.methods
    )

    response = route.endpoint(
        provider="codex",
        agent_profile="gpu-kernel-coder",
        working_directory="/tmp/workspace",
    )

    assert response.status_code == 201
    assert service.m_proxy_calls == [expected_call]
    assert service.m_synced_payloads == [response_payload]


def test_session_path_routes_percent_encode_before_proxy() -> None:
    get_session_call = ("GET", "/sessions/cao%20gpu", ())
    create_terminal_call = (
        "POST",
        "/sessions/cao%20gpu/terminals",
        (
            ("agent_profile", "gpu-kernel-coder"),
            ("provider", "codex"),
            ("working_directory", "/tmp/workspace"),
        ),
    )
    service = _AppServiceDouble(
        responses={
            get_session_call: _json_response({"id": "cao gpu", "terminals": []}),
            create_terminal_call: _json_response(
                {
                    "id": "abcd1234",
                    "name": "gpu",
                    "provider": "codex",
                    "session_name": "cao gpu",
                    "agent_profile": "gpu-kernel-coder",
                    "status": "idle",
                },
                status_code=201,
            ),
        }
    )
    app = create_app(service=service)
    get_route = next(
        candidate
        for candidate in app.routes
        if isinstance(candidate, APIRoute)
        and candidate.path == "/cao/sessions/{session_name}"
        and "GET" in candidate.methods
    )
    create_terminal_route = next(
        candidate
        for candidate in app.routes
        if isinstance(candidate, APIRoute)
        and candidate.path == "/cao/sessions/{session_name}/terminals"
        and "POST" in candidate.methods
    )

    get_response = get_route.endpoint(session_name="cao gpu")
    create_terminal_response = create_terminal_route.endpoint(
        session_name="cao gpu",
        provider="codex",
        agent_profile="gpu-kernel-coder",
        working_directory="/tmp/workspace",
    )

    assert get_response.status_code == 200
    assert create_terminal_response.status_code == 201
    assert service.m_proxy_calls == [get_session_call, create_terminal_call]


def test_output_endpoint_forwards_mode_query_to_child() -> None:
    expected_call = ("GET", "/terminals/abcd1234/output", (("mode", "tail"),))
    service = _AppServiceDouble(
        responses={expected_call: _json_response({"output": "tail text", "mode": "tail"})}
    )
    app = create_app(service=service)
    route = next(
        candidate
        for candidate in app.routes
        if isinstance(candidate, APIRoute)
        and candidate.path == "/cao/terminals/{terminal_id}/output"
        and "GET" in candidate.methods
    )

    response = route.endpoint(terminal_id="abcd1234", mode="tail")

    assert response.status_code == 200
    assert service.m_proxy_calls == [expected_call]


def test_inbox_messages_endpoint_forwards_status_filter_to_child() -> None:
    expected_call = (
        "GET",
        "/terminals/abcd1234/inbox/messages",
        (("limit", "10"), ("status", "invalid_status")),
    )
    service = _AppServiceDouble(
        responses={
            expected_call: _json_response(
                {
                    "detail": "Invalid status: invalid_status. Valid values: pending, delivered, failed"
                },
                status_code=400,
            )
        }
    )
    app = create_app(service=service)
    route = next(
        candidate
        for candidate in app.routes
        if isinstance(candidate, APIRoute)
        and candidate.path == "/cao/terminals/{terminal_id}/inbox/messages"
        and "GET" in candidate.methods
    )

    response = route.endpoint(terminal_id="abcd1234", limit=10, status="invalid_status")

    assert response.status_code == 400
    assert service.m_proxy_calls == [expected_call]


def test_send_input_records_prompt_submission_on_success() -> None:
    proxy_call = (
        "POST",
        "/terminals/abcd1234/input",
        (("message", "Explain the failure."),),
    )
    service = _AppServiceDouble(
        responses={proxy_call: _json_response({"success": True}, status_code=200)}
    )
    app = create_app(service=service)
    route = next(
        candidate
        for candidate in app.routes
        if isinstance(candidate, APIRoute)
        and candidate.path == "/cao/terminals/{terminal_id}/input"
        and "POST" in candidate.methods
    )

    response = route.endpoint(terminal_id="abcd1234", message="Explain the failure.")

    assert response.status_code == 200
    assert service.m_proxy_calls == [proxy_call]
    assert service.m_prompt_submissions == [("abcd1234", "Explain the failure.")]


def test_houmao_extension_routes_delegate_to_service_methods() -> None:
    service = _AppServiceDouble()
    app = create_app(service=service)
    health_route = next(
        candidate
        for candidate in app.routes
        if isinstance(candidate, APIRoute)
        and candidate.path == "/health"
        and "GET" in candidate.methods
    )
    current_instance_route = next(
        candidate
        for candidate in app.routes
        if isinstance(candidate, APIRoute)
        and candidate.path == "/houmao/server/current-instance"
        and "GET" in candidate.methods
    )
    register_route = next(
        candidate
        for candidate in app.routes
        if isinstance(candidate, APIRoute)
        and candidate.path == "/houmao/launches/register"
        and "POST" in candidate.methods
    )
    install_route = next(
        candidate
        for candidate in app.routes
        if isinstance(candidate, APIRoute)
        and candidate.path == "/houmao/agent-profiles/install"
        and "POST" in candidate.methods
    )
    state_route = next(
        candidate
        for candidate in app.routes
        if isinstance(candidate, APIRoute)
        and candidate.path == "/houmao/terminals/{terminal_id}/state"
        and "GET" in candidate.methods
    )
    history_route = next(
        candidate
        for candidate in app.routes
        if isinstance(candidate, APIRoute)
        and candidate.path == "/houmao/terminals/{terminal_id}/history"
        and "GET" in candidate.methods
    )

    health_response = health_route.endpoint()
    current_instance_response = current_instance_route.endpoint()
    install_response = install_route.endpoint(
        agent_source="projection-demo",
        provider="codex",
        working_directory="/tmp/workspace",
    )
    register_response = register_route.endpoint(
        session_name="cao-gpu",
        tool="codex",
        terminal_id="abcd1234",
        agent_name="AGENTSYS-gpu",
    )
    state_response = state_route.endpoint(terminal_id="abcd1234")
    history_response = history_route.endpoint(terminal_id="abcd1234", limit=3)

    assert health_response.houmao_service == "houmao-server"
    assert health_response.child_cao is not None
    assert health_response.child_cao.derived_port == 9890

    assert current_instance_response.api_base_url == "http://127.0.0.1:9889"

    assert install_response.success is True
    assert service.m_install_requests == [
        HoumaoInstallAgentProfileRequest(
            agent_source="projection-demo",
            provider="codex",
            working_directory="/tmp/workspace",
        )
    ]

    assert register_response.success is True
    assert service.m_register_requests[0].session_name == "cao-gpu"
    assert service.m_register_requests[0].tool == "codex"
    assert service.m_register_requests[0].agent_name == "AGENTSYS-gpu"
    assert state_response.terminal_id == "abcd1234"
    assert history_response.entries[0].summary == "limit=3"
    assert service.m_history_calls == [("abcd1234", 3)]


def test_root_cao_routes_are_removed_from_public_inventory() -> None:
    app = create_app(service=_AppServiceDouble())

    with_root_sessions = any(
        isinstance(route, APIRoute) and route.path == "/sessions" for route in app.routes
    )
    with_root_terminals = any(
        isinstance(route, APIRoute) and route.path == "/terminals/{terminal_id}"
        for route in app.routes
    )

    assert with_root_sessions is False
    assert with_root_terminals is False


def test_managed_agent_routes_delegate_to_service_methods() -> None:
    service = _AppServiceDouble()
    app = create_app(service=service)
    list_route = _route("/houmao/agents", "GET", app=app)
    get_route = _route("/houmao/agents/{agent_ref}", "GET", app=app)
    state_route = _route("/houmao/agents/{agent_ref}/state", "GET", app=app)
    history_route = _route("/houmao/agents/{agent_ref}/history", "GET", app=app)
    launch_route = _route("/houmao/agents/headless/launches", "POST", app=app)
    stop_route = _route("/houmao/agents/{agent_ref}/stop", "POST", app=app)
    turns_route = _route("/houmao/agents/{agent_ref}/turns", "POST", app=app)
    turn_status_route = _route("/houmao/agents/{agent_ref}/turns/{turn_id}", "GET", app=app)
    turn_events_route = _route(
        "/houmao/agents/{agent_ref}/turns/{turn_id}/events",
        "GET",
        app=app,
    )
    stdout_route = _route(
        "/houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout",
        "GET",
        app=app,
    )
    stderr_route = _route(
        "/houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stderr",
        "GET",
        app=app,
    )
    interrupt_route = _route("/houmao/agents/{agent_ref}/interrupt", "POST", app=app)

    assert list_route.endpoint().agents[0].tracked_agent_id == "claude-headless-1"
    assert get_route.endpoint(agent_ref="claude-headless-1").transport == "headless"
    assert state_route.endpoint(agent_ref="claude-headless-1").availability == "available"
    assert history_route.endpoint(agent_ref="claude-headless-1", limit=5).entries[0].summary == "managed-limit=5"

    launch_response = launch_route.endpoint(
        request_model=HoumaoHeadlessLaunchRequest(
            tool="claude",
            working_directory="/tmp/work",
            agent_def_dir="/tmp/agents",
            brain_manifest_path="/tmp/brain.yaml",
            role_name="gpu-kernel-coder",
            agent_name="AGENTSYS-gpu",
            agent_id=None,
        )
    )
    assert launch_response.tracked_agent_id == "claude-headless-1"
    assert service.m_headless_launch_requests[0].tool == "claude"

    assert stop_route.endpoint(agent_ref="claude-headless-1").detail == "stopped"
    turn_response = turns_route.endpoint(
        agent_ref="claude-headless-1",
        request_model=HoumaoHeadlessTurnRequest(prompt="hello"),
    )
    assert turn_response.turn_id == "turn-123"
    assert turn_status_route.endpoint(agent_ref="claude-headless-1", turn_id="turn-123").status == "completed"
    assert turn_events_route.endpoint(agent_ref="claude-headless-1", turn_id="turn-123").entries == []
    assert stdout_route.endpoint(agent_ref="claude-headless-1", turn_id="turn-123").body == b"stdout:turn-123"
    assert stderr_route.endpoint(agent_ref="claude-headless-1", turn_id="turn-123").body == b"stderr:turn-123"
    assert interrupt_route.endpoint(agent_ref="claude-headless-1").detail == "interrupted"
