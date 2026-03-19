from __future__ import annotations

import ast
import json
from pathlib import Path

from fastapi.routing import APIRoute
from pydantic_core import PydanticUndefined

from houmao.cao.models import CaoTerminal, CaoTerminalStatus
from houmao.server.app import create_app
from houmao.server.models import (
    ChildCaoStatus,
    HoumaoCurrentInstance,
    HoumaoExternalActivity,
    HoumaoHealthResponse,
    HoumaoOperatorState,
    HoumaoOwnedWork,
    HoumaoRawObservation,
    HoumaoRegisterLaunchRequest,
    HoumaoRegisterLaunchResponse,
    HoumaoTerminalHistoryEntry,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalStateResponse,
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
            if not isinstance(path_literal, ast.Constant) or not isinstance(path_literal.value, str):
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
        self.m_deleted_sessions: list[str] = []
        self.m_deleted_terminals: list[str] = []
        self.m_register_requests: list[HoumaoRegisterLaunchRequest] = []
        self.m_history_calls: list[tuple[str, int]] = []

    def startup(self) -> None:
        return None

    def shutdown(self) -> None:
        return None

    def proxy(self, *, method: str, path: str, params: dict[str, str] | None = None) -> ProxyResponse:
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

    def register_launch(self, request_model: HoumaoRegisterLaunchRequest) -> HoumaoRegisterLaunchResponse:
        self.m_register_requests.append(request_model)
        terminal_id = request_model.terminal_id or "abcd1234"
        return HoumaoRegisterLaunchResponse(
            success=True,
            session_name=request_model.session_name,
            terminal_id=terminal_id,
        )

    def terminal_state(self, terminal_id: str) -> HoumaoTerminalStateResponse:
        return HoumaoTerminalStateResponse(
            terminal=CaoTerminal(
                id=terminal_id,
                name="gpu",
                provider="codex",
                session_name="cao-gpu",
                agent_profile="runtime-profile",
                status=CaoTerminalStatus.IDLE,
            ),
            raw_observation=HoumaoRawObservation(
                observed_at_utc="2026-03-19T10:00:00+00:00",
                terminal_id=terminal_id,
                session_name="cao-gpu",
                backend_status="idle",
                output_hash="abc123",
                output_length=12,
                output_excerpt="hello world",
            ),
            owned_work=HoumaoOwnedWork(state="idle"),
            external_activity=HoumaoExternalActivity(),
            operator_state=HoumaoOperatorState(
                status="ready",
                detail="Terminal status is `idle`.",
                updated_at_utc="2026-03-19T10:00:00+00:00",
            ),
        )

    def terminal_history(self, terminal_id: str, *, limit: int) -> HoumaoTerminalHistoryResponse:
        self.m_history_calls.append((terminal_id, limit))
        return HoumaoTerminalHistoryResponse(
            terminal_id=terminal_id,
            entries=[
                HoumaoTerminalHistoryEntry(
                    recorded_at_utc="2026-03-19T10:00:00+00:00",
                    kind="sample",
                    payload={"limit": limit},
                )
            ],
        )


def _compat_route_inventory() -> set[tuple[str, str]]:
    app = create_app(service=_AppServiceDouble())
    routes: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path.startswith("/houmao/"):
            continue
        for method in route.methods:
            routes.add((method, route.path))
    return routes


def _route(path: str, method: str) -> APIRoute:
    app = create_app(service=_AppServiceDouble())
    for route in app.routes:
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
    assert _compat_route_inventory() == _extract_upstream_http_routes()


def test_create_session_route_query_contract_matches_pinned_upstream_expectations() -> None:
    contract = _query_contract(_route("/sessions", "POST"))

    assert contract == {
        "provider": {"required": True, "default": None, "le": None},
        "agent_profile": {"required": True, "default": None, "le": None},
        "session_name": {"required": False, "default": None, "le": None},
        "working_directory": {"required": False, "default": None, "le": None},
    }


def test_inbox_messages_route_query_contract_matches_pinned_upstream_expectations() -> None:
    contract = _query_contract(_route("/terminals/{terminal_id}/inbox/messages", "GET"))

    assert contract == {
        "limit": {"required": False, "default": 10, "le": 100},
        "status": {"required": False, "default": None, "le": None},
    }


def test_output_route_query_contract_matches_pinned_upstream_expectations() -> None:
    contract = _query_contract(_route("/terminals/{terminal_id}/output", "GET"))

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
        and candidate.path == "/sessions"
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
        and candidate.path == "/sessions/{session_name}"
        and "GET" in candidate.methods
    )
    create_terminal_route = next(
        candidate
        for candidate in app.routes
        if isinstance(candidate, APIRoute)
        and candidate.path == "/sessions/{session_name}/terminals"
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
        and candidate.path == "/terminals/{terminal_id}/output"
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
        and candidate.path == "/terminals/{terminal_id}/inbox/messages"
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
        and candidate.path == "/terminals/{terminal_id}/input"
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
        if isinstance(candidate, APIRoute) and candidate.path == "/health" and "GET" in candidate.methods
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

    assert register_response.success is True
    assert service.m_register_requests[0].session_name == "cao-gpu"
    assert service.m_register_requests[0].tool == "codex"
    assert service.m_register_requests[0].agent_name == "AGENTSYS-gpu"

    assert state_response.terminal.id == "abcd1234"

    assert history_response.entries[0].payload["limit"] == 3
    assert service.m_history_calls == [("abcd1234", 3)]
