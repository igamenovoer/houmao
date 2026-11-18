"""Verify passive native refresh preserves gateway authority, evidence, and refusals."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from unittest.mock import Mock

from tests.unit.passive_server.contract_client import AdmittedPassiveClient
import pytest

from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.agents.realm_controller.native_refresh_models import (
    CommonPluginObservationV1,
    CommonPluginResourceV1,
    NativeHomeV1,
    NativeRefreshRequestV1,
    NativeRefreshResultV1,
)
from houmao.agents.realm_controller.registry_models import RegistryGatewayV1
from houmao.cao.rest_client import CaoApiError
from houmao.passive_server.app import create_app
from houmao.passive_server.client import PassiveServerClient
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import DiscoveredAgent, _summary_from_record
from houmao.passive_server.service import PassiveServerService
from tests.unit.passive_server.test_discovery import _make_record


def _agent(
    *, agent_id: str = "owner", gateway: bool = True, port: int = 43000, web: bool = True
) -> DiscoveredAgent:
    """Create isolated discovery authority with optional gateway coordinates."""

    record = _make_record(
        agent_id=agent_id,
        agent_name="HOUMAO-alpha",
        backend="dsh_acp",
        tool="dsh",
        session_name=f"isolated-{agent_id}",
    )
    if web:
        record = type(record).model_validate(
            {
                **record.model_dump(mode="python"),
                "identity": {"backend": "dsh_web", "tool": "dsh"},
                "native_surface": {
                    "kind": "web",
                    "origin": "http://127.0.0.1:43001",
                    "native_session_id": "native",
                },
            }
        )
    if gateway:
        record.gateway = RegistryGatewayV1(
            host="127.0.0.1", port=port, state_path="/owned/gateway.json", protocol_version="v1"
        )
    return DiscoveredAgent(record=record, summary=_summary_from_record(record))


def _service(tmp_path: Path, agents: list[DiscoveredAgent]) -> PassiveServerService:
    """Build an inert passive service without starting discovery, tmux, or collectors."""

    service = PassiveServerService(
        config=PassiveServerConfig(runtime_root=tmp_path, registry_root=tmp_path / "registry")
    )
    service.m_discovery.m_index.replace({agent.record.agent_id: agent for agent in agents})
    return service


def _observation(
    freshness: str = "unknown", *, automatic: bool = False
) -> CommonPluginObservationV1:
    """Build explicit common scope without arbitrary native configuration contents."""

    return CommonPluginObservationV1(
        home=NativeHomeV1(
            agent_id="owner",
            backend="dsh_web",
            tool="dsh",
            home_dir="/owned/native-home",
            identity={"agent_id": "owner", "generation": "gen-1", "native_session_id": "native"},
        ),
        resources=[
            CommonPluginResourceV1(
                kind=kind,
                component="native",
                freshness=freshness,
                boundary="next_turn" if automatic else "now",
                complete=True,
                supported=True,
            )
            for kind in ("skills", "mcp")
        ],
        freshness=freshness,
        coverage_complete=True,
        automatic=automatic,
        native_reload=True,
    )


@pytest.mark.parametrize("reference", ["owner", "alpha"])
def test_passive_home_projects_authoritative_descriptor_without_refresh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reference: str
) -> None:
    """Both exact id and unambiguous name preserve the upstream native home."""

    service = _service(tmp_path, [_agent()])
    home = _observation().home
    read = Mock(return_value=home)
    mutate = Mock()
    monkeypatch.setattr(GatewayClient, "get_native_home", read)
    monkeypatch.setattr(GatewayClient, "refresh_native", mutate)
    client = AdmittedPassiveClient(create_app(service=service))
    response = client.get(f"/houmao/agents/{reference}/gateway/native-home")
    assert response.status_code == 200
    assert response.json() == home.model_dump(mode="json")
    read.assert_called_once()
    mutate.assert_not_called()


@pytest.mark.parametrize("freshness", ["pending", "unknown"])
def test_passive_common_get_preserves_200_and_does_not_evaluate_freshness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, freshness: str
) -> None:
    """Incomplete observations are normal upstream results and never cause local native work."""

    service = _service(tmp_path, [_agent()])
    observation = _observation(freshness)
    read = Mock(return_value=observation)
    mutate = Mock()
    monkeypatch.setattr(GatewayClient, "get_common_plugin_state", read)
    monkeypatch.setattr(GatewayClient, "get_native_home", Mock(return_value=observation.home))
    monkeypatch.setattr(GatewayClient, "refresh_native", mutate)
    client = AdmittedPassiveClient(create_app(service=service))
    response = client.get("/houmao/agents/owner/gateway/control/refresh")
    assert response.status_code == 200
    assert response.json() == observation.model_dump(mode="json")
    read.assert_called_once()
    mutate.assert_not_called()


@pytest.mark.parametrize(
    "method,outcome,effects,freshness,status",
    [
        ("noop", "already_current", "absent", "current", 200),
        ("automatic", "automatic", "absent", "unknown", 200),
        ("native_reload", "refreshed", "partial", "current", 200),
        ("native_reload", "partial", "partial", "unknown", 503),
        ("native_reload", "restart_required", "partial", "pending", 409),
        ("none", "busy", "absent", "pending", 409),
        ("none", "unsupported", "absent", "unknown", 501),
        ("native_reload", "outcome_unknown", "unknown", "unknown", 503),
    ],
)
def test_passive_refresh_preserves_typed_outcomes_effects_and_native_only_pending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    outcome: str,
    effects: str,
    freshness: str,
    status: int,
) -> None:
    """The proxy keeps native-only diagnostics and partial facts without overriding common success."""

    service = _service(tmp_path, [_agent()])
    observation = _observation(freshness, automatic=method == "automatic")
    result = NativeRefreshResultV1(
        method=method,
        outcome=outcome,
        observation=observation,
        effects=effects,
        native_settled=outcome != "outcome_unknown",
        native_ready=outcome != "outcome_unknown",
        diagnostics=["native_host_module_pending"],
    )
    native = Mock(return_value=result)
    read = Mock(side_effect=AssertionError("proxy must not evaluate freshness"))
    monkeypatch.setattr(GatewayClient, "refresh_native", native)
    monkeypatch.setattr(GatewayClient, "get_native_home", Mock(return_value=observation.home))
    monkeypatch.setattr(GatewayClient, "get_common_plugin_state", read)
    client = AdmittedPassiveClient(create_app(service=service))
    response = client.post(
        "/houmao/agents/owner/gateway/control/refresh", json={"timeout_seconds": 0.05}
    )
    assert response.status_code == status
    assert response.json() == result.model_dump(mode="json")
    native.assert_called_once_with(NativeRefreshRequestV1(timeout_seconds=0.05))
    read.assert_not_called()


@pytest.mark.parametrize("route", ["native-home", "control/refresh", "post-refresh"])
@pytest.mark.parametrize(
    "condition,status", [("missing", 404), ("ambiguous", 409), ("detached", 502)]
)
def test_passive_refresh_preserves_scoped_resolution_errors_without_gateway_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    condition: str,
    status: int,
) -> None:
    """Missing, ambiguous, and gateway-free agents cannot trigger body controls or auto-attach."""

    agents = [] if condition == "missing" else [_agent(gateway=condition != "detached")]
    if condition == "ambiguous":
        agents.append(_agent(agent_id="other"))
    service = _service(tmp_path, agents)
    factory = Mock(side_effect=AssertionError("no gateway operation expected"))
    monkeypatch.setattr("houmao.passive_server.service.GatewayClient", factory)
    client = AdmittedPassiveClient(create_app(service=service))
    path = f"/houmao/agents/alpha/gateway/{'control/refresh' if route == 'post-refresh' else route}"
    response = client.post(path, json={}) if route == "post-refresh" else client.get(path)
    assert response.status_code == status
    if condition == "ambiguous":
        assert set(response.json()["agent_ids"]) == {"owner", "other"}
    factory.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        {"force": "private-config-value"},
        {"restart": True},
        {"home_dir": "/private/home"},
        {"mcp": {"replacement": "private-config-value"}},
        {"timeout_seconds": 0},
        {"timeout_seconds": 121},
        {"timeout_seconds": "10"},
        {"timeout_seconds": float("inf")},
    ],
)
def test_passive_refresh_rejects_strict_invalid_requests_before_proxying(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: dict[str, object]
) -> None:
    """Shared request validation rejects restart, replacement material, and invalid budgets safely."""

    service = _service(tmp_path, [_agent()])
    native = Mock()
    monkeypatch.setattr(GatewayClient, "refresh_native", native)
    client = AdmittedPassiveClient(create_app(service=service))
    response = client.post(
        "/houmao/agents/owner/gateway/control/refresh",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert "private-config-value" not in response.text
    assert "/private/home" not in response.text
    native.assert_not_called()


@pytest.mark.parametrize(
    "route,method",
    [
        ("native-home", "get_native_home"),
        ("control/refresh", "get_common_plugin_state"),
        ("post-refresh", "refresh_native"),
    ],
)
@pytest.mark.parametrize("upstream_status", [None, 503])
def test_passive_refresh_transport_errors_are_safe_and_never_retried(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    method: str,
    upstream_status: int | None,
) -> None:
    """Lost connectivity is a 502; explicit upstream failure keeps its safe status."""

    service = _service(tmp_path, [_agent()])
    native = Mock(
        side_effect=GatewayHttpError(
            method="POST" if route == "post-refresh" else "GET",
            url="http://127.0.0.1:43000/private-config-value",
            detail="private-config-value",
            status_code=upstream_status,
        )
    )
    monkeypatch.setattr(GatewayClient, method, native)
    if method != "get_native_home":
        monkeypatch.setattr(
            GatewayClient, "get_native_home", Mock(return_value=_observation().home)
        )
    client = AdmittedPassiveClient(create_app(service=service))
    path = f"/houmao/agents/owner/gateway/{'control/refresh' if route == 'post-refresh' else route}"
    response = client.post(path, json={}) if route == "post-refresh" else client.get(path)
    assert response.status_code == (upstream_status or 502)
    assert "private-config-value" not in response.text
    native.assert_called_once()


def test_passive_client_preserves_typed_refusal_budget_and_agent_escaping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The pair client uses one encoded target and enough budget for both proxy hops."""

    result = NativeRefreshResultV1(
        method="native_reload",
        outcome="restart_required",
        observation=_observation("pending"),
        effects="partial",
        diagnostics=["native_host_module_pending"],
    )
    client = PassiveServerClient("http://127.0.0.1:9891")
    send = Mock(
        side_effect=CaoApiError(
            method="POST",
            url="http://127.0.0.1:9891/proxy",
            detail="typed refusal",
            status_code=409,
            payload=result.model_dump(mode="json"),
        )
    )
    monkeypatch.setattr(client, "_request_root_json", send)
    payload = NativeRefreshRequestV1(timeout_seconds=120.0)
    assert client.refresh_managed_agent_gateway_native("agent/name", payload) == result
    send.assert_called_once_with(
        "POST",
        "/houmao/agents/agent%2Fname/gateway/control/refresh",
        json_body=payload.model_dump(mode="json"),
        timeout_seconds=130.0,
    )


@pytest.mark.parametrize(
    "method",
    [
        "get_managed_agent_gateway_native_home",
        "get_managed_agent_gateway_common_plugin_state",
        "refresh_managed_agent_gateway_native",
    ],
)
def test_passive_client_suppresses_invalid_upstream_detail_without_retry(
    monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    """Malformed upstream error payloads cannot leak native configuration through pair errors."""

    client = PassiveServerClient("http://127.0.0.1:9891")
    send = Mock(
        side_effect=CaoApiError(
            method="POST",
            url="http://127.0.0.1:9891/proxy",
            detail="private-config-value",
            status_code=503,
            payload={"detail": "private-config-value"},
        )
    )
    monkeypatch.setattr(client, "_request_root_json", send)
    callback = getattr(client, method)
    args = ("owner", NativeRefreshRequestV1()) if method.startswith("refresh_") else ("owner",)
    with pytest.raises(CaoApiError) as error:
        callback(*args)
    assert "private-config-value" not in str(error.value)
    assert error.value.status_code == 503
    send.assert_called_once()


def test_passive_http_projects_actual_typed_gateway_refusal_without_retry(tmp_path: Path) -> None:
    """Real gateway HTTP errors retain their typed partial effects through the passive route."""

    result = NativeRefreshResultV1(
        method="native_reload",
        outcome="restart_required",
        observation=_observation("pending"),
        effects="partial",
        diagnostics=["native_host_module_pending"],
    )
    received: list[tuple[str, dict[str, object]]] = []

    class Handler(BaseHTTPRequestHandler):
        """Expose one controlled native gateway refusal on a loopback socket."""

        def do_GET(self) -> None:
            """Bind the reached native authority before the single refresh mutation."""

            assert self.path == "/v1/native-home"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(result.observation.home.model_dump_json().encode())

        def do_POST(self) -> None:
            """Record one request and return a valid typed non-success body."""

            assert self.headers.get("If-Match"), "Native refresh must bind its captured home"
            received.append(
                (self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            )
            self.send_response(409)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(result.model_dump_json().encode())

        def log_message(self, format: str, *args: object) -> None:
            """Keep deterministic server tests quiet."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        service = _service(tmp_path, [_agent(port=server.server_port)])
        client = AdmittedPassiveClient(create_app(service=service))
        response = client.post(
            "/houmao/agents/owner/gateway/control/refresh", json={"timeout_seconds": 0.1}
        )
        assert response.status_code == 409
        assert response.json() == result.model_dump(mode="json")
        assert received == [("/v1/control/refresh", {"schema_version": 1, "timeout_seconds": 0.1})]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_passive_native_home_selection_keeps_distinct_gateway_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Choosing another agent cannot reuse the first gateway's native-home result."""

    service = _service(tmp_path, [_agent(port=43000), _agent(agent_id="other", port=43002)])
    clients = {43000: Mock(), 43002: Mock()}
    for port, identity in ((43000, "owner"), (43002, "other")):
        clients[port].get_native_home.return_value = _observation().home.model_copy(
            update={
                "agent_id": identity,
                "home_dir": f"/owned/{identity}/native-home",
                "identity": {
                    "agent_id": identity,
                    "generation": "gen-1",
                    "native_session_id": "native",
                },
            }
        )
    factory = Mock(side_effect=lambda *, endpoint: clients[endpoint.port])
    monkeypatch.setattr("houmao.passive_server.service.GatewayClient", factory)
    client = AdmittedPassiveClient(create_app(service=service))
    for identity in ("owner", "other"):
        response = client.get(f"/houmao/agents/{identity}/gateway/native-home")
        assert response.status_code == 200
        assert response.json()["agent_id"] == identity
        assert response.json()["home_dir"] == f"/owned/{identity}/native-home"
    assert factory.call_count == 2
    clients[43000].get_native_home.assert_called_once()
    clients[43002].get_native_home.assert_called_once()


@pytest.mark.parametrize(
    "method,path",
    [
        ("get_managed_agent_gateway_native_home", "native-home"),
        ("get_managed_agent_gateway_common_plugin_state", "control/refresh"),
    ],
)
def test_passive_client_reads_shared_contracts_with_encoded_target(
    monkeypatch: pytest.MonkeyPatch, method: str, path: str
) -> None:
    """Typed reads preserve home/common observations without invoking mutation."""

    expected = _observation().home if path == "native-home" else _observation()
    client = PassiveServerClient("http://127.0.0.1:9891")
    send = Mock(return_value=(expected.model_dump(mode="json"), 200, "http://127.0.0.1:9891/read"))
    monkeypatch.setattr(client, "_request_root_json", send)
    assert getattr(client, method)("agent/name") == expected
    send.assert_called_once_with(
        "GET", f"/houmao/agents/agent%2Fname/gateway/{path}", json_body=None, timeout_seconds=None
    )


@pytest.mark.parametrize(
    "bad_response", [{"private": "private-config-value"}, ValueError("private-config-value")]
)
def test_passive_client_hides_invalid_success_response(
    monkeypatch: pytest.MonkeyPatch, bad_response: object
) -> None:
    """Malformed JSON or model fields produce a fixed safe error with no replay."""

    client = PassiveServerClient("http://127.0.0.1:9891")
    send = Mock()
    if isinstance(bad_response, ValueError):
        send.side_effect = bad_response
    else:
        send.return_value = (bad_response, 200, "http://127.0.0.1:9891/read")
    monkeypatch.setattr(client, "_request_root_json", send)
    with pytest.raises(CaoApiError) as error:
        client.refresh_managed_agent_gateway_native("owner", NativeRefreshRequestV1())
    assert "private-config-value" not in str(error.value)
    send.assert_called_once()


@pytest.mark.parametrize("route", ["native-home", "control/refresh", "post-refresh"])
@pytest.mark.parametrize(
    "mismatch",
    [
        "agent_id",
        "identity_agent_id",
        "backend",
        "tool",
        "generation",
        "native_session_id",
        "missing_generation",
    ],
)
def test_passive_native_proxy_refuses_wrong_gateway_before_any_body_control(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, route: str, mismatch: str
) -> None:
    """A healthy reused port never grants authority over a different native execution."""

    service = _service(tmp_path, [_agent()])
    home = _observation().home.model_copy(deep=True)
    if mismatch in {"agent_id", "backend", "tool"}:
        home = home.model_copy(update={mismatch: "different-selected-execution"})
    elif mismatch == "missing_generation":
        home.identity.pop("generation")
    else:
        home.identity["agent_id" if mismatch == "identity_agent_id" else mismatch] = (
            "different-execution"
        )
    read = Mock(return_value=home)
    common = Mock(side_effect=AssertionError("wrong native execution must not be observed"))
    refresh = Mock(side_effect=AssertionError("wrong native execution must not be refreshed"))
    bind = Mock()
    monkeypatch.setattr(GatewayClient, "get_native_home", read)
    monkeypatch.setattr(GatewayClient, "get_common_plugin_state", common)
    monkeypatch.setattr(GatewayClient, "refresh_native", refresh)
    monkeypatch.setattr(GatewayClient, "bind_native_home", bind)
    client = AdmittedPassiveClient(create_app(service=service))
    path = f"/houmao/agents/owner/gateway/{'control/refresh' if route == 'post-refresh' else route}"
    response = client.post(path, json={}) if route == "post-refresh" else client.get(path)
    assert response.status_code == 502
    assert response.json() == {"detail": "Agent gateway native authority does not match selection"}
    read.assert_called_once()
    common.assert_not_called()
    refresh.assert_not_called()
    bind.assert_not_called()


@pytest.mark.parametrize("route", ["control/refresh", "post-refresh", "before-refresh"])
@pytest.mark.parametrize("changed", ["home_dir", "generation", "native_session_id"])
def test_passive_native_proxy_checks_returned_execution_against_captured_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, route: str, changed: str
) -> None:
    """A response from a changed execution cannot be relabelled as the selected native home."""

    service = _service(tmp_path, [_agent()])
    captured = _observation().home
    observation = _observation()
    changed_home = captured.model_copy(deep=True)
    if changed == "home_dir":
        changed_home.home_dir = "/different/private-native-home"
    else:
        changed_home.identity[changed] = "different-execution"
    observation.home = changed_home
    result = NativeRefreshResultV1(
        method="native_reload",
        outcome="partial",
        effects="partial",
        observation=_observation() if route == "before-refresh" else observation,
        before=observation if route == "before-refresh" else None,
    )
    monkeypatch.setattr(GatewayClient, "get_native_home", Mock(return_value=captured))
    bind = Mock()
    monkeypatch.setattr(GatewayClient, "bind_native_home", bind)
    monkeypatch.setattr(GatewayClient, "get_common_plugin_state", Mock(return_value=observation))
    mutate = Mock(return_value=result)
    monkeypatch.setattr(GatewayClient, "refresh_native", mutate)
    client = AdmittedPassiveClient(create_app(service=service))
    response = (
        client.get("/houmao/agents/owner/gateway/control/refresh")
        if route == "control/refresh"
        else client.post("/houmao/agents/owner/gateway/control/refresh", json={})
    )
    assert response.status_code == 502
    assert response.json() == {"detail": "Agent gateway native authority changed during request"}
    assert "/different/private-native-home" not in response.text
    bind.assert_called_once_with(captured)
    assert mutate.call_count == (0 if route == "control/refresh" else 1)


def test_passive_headless_scope_does_not_require_a_nonexistent_live_native_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The headless managed envelope can expose unknown future state between workers."""

    service = _service(tmp_path, [_agent(web=False)])
    observation = _observation()
    observation.home.backend = "dsh_acp"
    observation.home.identity.pop("native_session_id")
    monkeypatch.setattr(GatewayClient, "get_native_home", Mock(return_value=observation.home))
    monkeypatch.setattr(GatewayClient, "get_common_plugin_state", Mock(return_value=observation))
    bind = Mock()
    monkeypatch.setattr(GatewayClient, "bind_native_home", bind)
    response = AdmittedPassiveClient(create_app(service=service)).get(
        "/houmao/agents/owner/gateway/control/refresh"
    )
    assert response.status_code == 200
    assert response.json() == observation.model_dump(mode="json")
    bind.assert_called_once_with(observation.home)


def test_passive_conditional_refresh_refuses_replacement_after_prefetch(tmp_path: Path) -> None:
    """The native If-Match guard prevents a later replacement from receiving the mutation."""

    home = _observation().home
    received: list[str] = []
    mutated: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        """Replace captured authority between GET and POST on the same controlled port."""

        def do_GET(self) -> None:
            """Return the selected native home before replacement."""

            received.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(home.model_dump_json().encode())

        def do_POST(self) -> None:
            """Refuse a conditional mutation after the controlled execution changed."""

            received.append(self.path)
            self.rfile.read(int(self.headers["Content-Length"]))
            if not self.headers.get("If-Match"):
                mutated.append("unfenced-native-replacement")
            self.send_response(412)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"detail":"private-replacement-identity"}')

        def log_message(self, format: str, *args: object) -> None:
            """Keep controlled loopback transport output private and deterministic."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        service = _service(tmp_path, [_agent(port=server.server_port)])
        response = AdmittedPassiveClient(create_app(service=service)).post(
            "/houmao/agents/owner/gateway/control/refresh", json={"timeout_seconds": 0.1}
        )
        assert response.status_code == 412
        assert received == ["/v1/native-home", "/v1/control/refresh"]
        assert not mutated
        assert "private-replacement-identity" not in response.text
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
