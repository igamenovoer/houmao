"""Verify exact gateway terminal route classification and request framing."""

from __future__ import annotations

from unittest.mock import Mock

from fastapi import FastAPI, Request, WebSocket
from fastapi.testclient import TestClient
import pytest
from starlette.websockets import WebSocketDisconnect

from houmao.agents.realm_controller.errors import GatewayError
from houmao.agents.realm_controller.gateway_admission import (
    GatewayAdmissionMiddleware,
    validate_core_gateway_routes,
)
from houmao.agents.realm_controller.gateway_plugin_host import GatewayPluginHost
from houmao.gateway.access import CHALLENGE_HEADER, SIGNATURE_HEADER
from houmao.gateway.operations import CORE_TERMINAL_WEBSOCKETS, TERMINAL_INTERACT
from houmao.gateway.owner_authority import BACKING_HEADER, RELAY_HEADER
from houmao.gateway.terminal_entry_contracts import (
    TERMINAL_ASSET_PATH,
    TERMINAL_INTERACT_PATH,
    TERMINAL_INTERACT_STREAM_PATH,
    TERMINAL_INTERACT_TICKET_PATH,
    TERMINAL_VIEW_PATH,
    TERMINAL_VIEW_STREAM_PATH,
    TERMINAL_VIEW_TICKET_PATH,
)


async def _terminal_socket(websocket: WebSocket) -> None:
    """Report classified permission to verify selection before handler dispatch."""

    await websocket.accept()
    await websocket.send_json(websocket.state.gateway_terminal_permission.model_dump(mode="json"))
    await websocket.close()


@pytest.fixture
def terminal_router() -> tuple[TestClient, Mock, Mock]:
    """Install real gateway admission and inert terminal endpoints."""

    gateway = FastAPI(openapi_url=None, docs_url=None, redoc_url=None, redirect_slashes=False)
    for path in CORE_TERMINAL_WEBSOCKETS:
        gateway.add_api_websocket_route(path, _terminal_socket)

    async def entry(request: Request) -> dict[str, bool]:
        """Tell the test whether request proof escaped the middleware."""

        return {"proof_received": CHALLENGE_HEADER in request.headers}

    for path in (TERMINAL_VIEW_PATH, TERMINAL_INTERACT_PATH, TERMINAL_ASSET_PATH):
        gateway.add_api_route(path, entry, methods=["GET"])
    for path in (TERMINAL_VIEW_TICKET_PATH, TERMINAL_INTERACT_TICKET_PATH):
        gateway.add_api_route(path, entry, methods=["POST"])

    validate_core_gateway_routes(list(gateway.routes))
    plugin_host = Mock(spec=GatewayPluginHost)
    plugin_host.route_permission.return_value = None
    admit = Mock(return_value=None)
    log_denial = Mock()
    gateway.add_middleware(
        GatewayAdmissionMiddleware,
        gateway=gateway,
        plugin_host=plugin_host,
        admit=admit,
        reserve_public_input=Mock(side_effect=AssertionError("Terminal used public input budget")),
        log_denial=log_denial,
    )
    return TestClient(gateway), admit, log_denial


@pytest.mark.parametrize("path", tuple(CORE_TERMINAL_WEBSOCKETS))
def test_gateway_classifies_exact_terminal_websocket_before_dispatch(
    terminal_router: tuple[TestClient, Mock, Mock], path: str
) -> None:
    """Carry the route-specific marker to the stream handler without HTTP admission."""

    client, admit, _ = terminal_router
    with client.websocket_connect(path) as stream:
        assert stream.receive_json() == CORE_TERMINAL_WEBSOCKETS[path].model_dump(mode="json")
    admit.assert_not_called()


@pytest.mark.parametrize(
    "path",
    ["/v1/plugins/example/socket", f"{TERMINAL_VIEW_STREAM_PATH}/", "/v1/terminal/%76iew/stream"],
)
def test_gateway_refuses_websocket_without_exact_route(
    terminal_router: tuple[TestClient, Mock, Mock], path: str
) -> None:
    """Reject unmapped paths and alternative spellings before forwarding."""

    client, admit, _ = terminal_router
    with pytest.raises(WebSocketDisconnect) as refused, client.websocket_connect(path):
        pytest.fail("Unclassified WebSocket was dispatched.")
    assert refused.value.code == 1008
    admit.assert_not_called()


@pytest.mark.parametrize("path", ["/v1/plugins/example/socket", TERMINAL_VIEW_STREAM_PATH])
def test_gateway_rejects_plugin_or_duplicate_websocket_registrations(path: str) -> None:
    """Reject all new sockets outside the fixed core pair, including duplicate paths."""

    gateway = FastAPI(openapi_url=None)
    gateway.add_api_websocket_route(TERMINAL_VIEW_STREAM_PATH, _terminal_socket)
    gateway.add_api_websocket_route(path, _terminal_socket)
    with pytest.raises(GatewayError, match="unclassified WebSocket route"):
        validate_core_gateway_routes(list(gateway.routes))


@pytest.mark.parametrize("header", [RELAY_HEADER, BACKING_HEADER])
@pytest.mark.parametrize("path", [TERMINAL_INTERACT_STREAM_PATH, TERMINAL_VIEW_STREAM_PATH])
def test_gateway_rejects_alternate_authority_on_terminal_websockets(
    terminal_router: tuple[TestClient, Mock, Mock], header: str, path: str
) -> None:
    """Keep relay and backing credentials outside both terminal streams."""

    client, admit, _ = terminal_router
    with (
        pytest.raises(WebSocketDisconnect) as refused,
        client.websocket_connect(path, headers={header: "private-origin-proof"}),
    ):
        pytest.fail("WebSocket with alternate authority was dispatched.")
    assert refused.value.code == 1008
    admit.assert_not_called()


@pytest.mark.parametrize("header", [RELAY_HEADER, BACKING_HEADER])
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", TERMINAL_VIEW_PATH),
        ("GET", TERMINAL_INTERACT_PATH),
        ("GET", TERMINAL_ASSET_PATH.format(name="client.js")),
        ("POST", TERMINAL_VIEW_TICKET_PATH),
        ("POST", TERMINAL_INTERACT_TICKET_PATH),
    ],
)
def test_gateway_rejects_alternate_authority_on_terminal_http_routes(
    terminal_router: tuple[TestClient, Mock, Mock], header: str, method: str, path: str
) -> None:
    """Refuse transport claims before stripping headers or calling the verifier."""

    client, admit, log_denial = terminal_router
    refused = client.request(method, path, headers={header: "private-origin-proof"})
    assert refused.status_code == 403
    assert refused.json()["detail"]["error_code"] == "direct_terminal_access_required"
    assert refused.headers["cache-control"] == "no-store"
    assert refused.headers["referrer-policy"] == "no-referrer"
    assert "private-origin-proof" not in refused.text
    admit.assert_not_called()
    log_denial.assert_called_once()


@pytest.mark.parametrize("path", [TERMINAL_VIEW_TICKET_PATH, TERMINAL_INTERACT_TICKET_PATH])
def test_gateway_rejects_nonempty_terminal_ticket_body(
    terminal_router: tuple[TestClient, Mock, Mock], path: str
) -> None:
    """Reject an unexpected body before admission, including an empty JSON object."""

    client, admit, _ = terminal_router
    refused = client.post(path, content=b"{}")
    assert refused.status_code == 413
    assert refused.json()["detail"]["error_code"] == "request_body_too_large"
    assert refused.headers["referrer-policy"] == "no-referrer"
    admit.assert_not_called()


def test_gateway_keeps_terminal_view_unsigned_and_protects_admin_ticket(
    terminal_router: tuple[TestClient, Mock, Mock],
) -> None:
    """Invoke the HTTP authorization callback only for the administrator ticket."""

    client, admit, _ = terminal_router
    viewer = client.post(TERMINAL_VIEW_TICKET_PATH)
    assert viewer.status_code == 200
    assert viewer.headers["cache-control"] == "no-store"
    assert viewer.headers["referrer-policy"] == "no-referrer"
    admit.assert_not_called()

    headers = {CHALLENGE_HEADER: "challenge", SIGNATURE_HEADER: "signature"}
    refused = client.post(TERMINAL_VIEW_TICKET_PATH, headers=headers)
    assert refused.status_code == 403
    admit.assert_not_called()

    administrator = client.post(TERMINAL_INTERACT_TICKET_PATH, headers=headers)
    assert administrator.status_code == 200
    assert administrator.json() == {"proof_received": False}
    admit.assert_called_once()
    observed = admit.call_args.kwargs
    assert observed["operation"].permission == TERMINAL_INTERACT
    assert observed["body"] == b""
    assert observed["proof"] == headers
