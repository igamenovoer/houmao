"""Gateway accounting HTTP, client, and lifecycle boundary tests."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient
import pytest

from houmao.agents.realm_controller.gateway_client import GatewayClient, GatewayEndpoint
from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime, create_app
from houmao.agents.realm_controller.usage_models import (
    UsageCapability,
    UsageCollectionHealth,
    UsagePage,
    UsageRecord,
)
from houmao.agents.realm_controller.usage_store import UsageStoreError


def _page() -> UsagePage:
    """Build a page containing qualified native usage and a durable end position."""

    return UsagePage(
        runtime_session_id="runtime-a",
        stream_id="stream-a",
        capability=UsageCapability(
            status="available",
            turn_recording=True,
            source_kinds=["native_session_log"],
            observed_scopes=["request", "turn"],
        ),
        collection=UsageCollectionHealth(status="degraded", diagnostics=["source_unreadable"]),
        records=[
            UsageRecord(
                agent_id="agent-a",
                runtime_session_id="runtime-a",
                turn_id="native-a",
                backend="local_interactive",
                provider="codex",
                turn_origin="native_observed",
                outcome="completed",
            )
        ],
        next_cursor="opaque+end/position=",
        has_more=False,
    )


def _client(callback: Mock) -> TestClient:
    """Create a gateway app with a read-only accounting service stand-in."""

    runtime = SimpleNamespace(get_usage=callback, emit_diagnostic=Mock())
    return TestClient(create_app(runtime=runtime))


def test_gateway_usage_returns_tui_history_and_preserves_end_cursor() -> None:
    """TUI records and degraded collection metadata share the gateway page contract."""

    callback = Mock(return_value=_page())
    response = _client(callback).get("/v1/usage", params={"after": "prior", "limit": 2})
    assert response.status_code == 200
    assert response.json() == _page().model_dump(mode="json")
    callback.assert_called_once_with(after="prior", limit=2)


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 501}, {"after": ""}])
def test_gateway_usage_rejects_invalid_pagination_before_reading(params: dict[str, object]) -> None:
    """Invalid query inputs cannot become an unbounded accounting query."""

    callback = Mock(return_value=UsagePage())
    assert _client(callback).get("/v1/usage", params=params).status_code == 422
    callback.assert_not_called()


@pytest.mark.parametrize(
    ("error", "status"),
    [(ValueError("invalid cursor"), 422), (UsageStoreError("private/path.sqlite3"), 503)],
)
def test_gateway_usage_errors_have_safe_status_and_detail(error: Exception, status: int) -> None:
    """Store failures remain explicit without disclosing a private source path."""

    response = _client(Mock(side_effect=error)).get("/v1/usage")
    assert response.status_code == status
    assert "private/path" not in response.text


def test_gateway_usage_does_not_acquire_execution_lock_or_run_collection() -> None:
    """Indexed accounting reads do not touch execution locks or collector lifecycle."""

    runtime = GatewayServiceRuntime.__new__(GatewayServiceRuntime)
    runtime.m_usage_error = None
    service = Mock()
    service.get_usage.return_value = _page()
    runtime.m_usage_service = service
    runtime.m_lock = Mock(side_effect=AssertionError("execution lock acquired"))
    assert runtime.get_usage(after="position", limit=1) == _page()
    service.get_usage.assert_called_once_with(after="position", limit=1)
    service.start.assert_not_called()
    service.reconcile.assert_not_called()


def test_gateway_usage_collection_follows_gateway_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gateway replacement starts its collector and shutdown releases it."""

    lock = threading.Lock()
    service = Mock()
    access = Mock()
    runtime = SimpleNamespace(
        m_lock=lock,
        m_reminder_condition=threading.Condition(lock),
        m_paths=SimpleNamespace(),
        m_host="127.0.0.1",
        m_port=19891,
        m_attach_contract=SimpleNamespace(attach_identity="agent-a", backend="claude_headless"),
        m_adapter=Mock(),
        m_access_runtime=access,
        _current_access=lambda: access,
        m_usage_service=service,
        m_file_edit_thread=None,
        m_stop_event=threading.Event(),
        m_terminal_shutdown=threading.Event(),
        m_tui_tracking=None,
        m_diagnostic_logger=Mock(),
        _mark_running_requests_failed=Mock(),
        _initialize_instance_state=Mock(),
        _refresh_status_snapshot=Mock(),
        _start_tui_tracking_locked=Mock(),
        _drop_pending_reminders_locked=Mock(),
        _flush_rate_limited_logs=Mock(),
        _log=Mock(),
        _worker_loop=lambda: None,
        _reminder_loop=lambda: None,
        _notifier_loop=lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.refresh_gateway_manifest_publication",
        Mock(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.delete_gateway_current_instance", Mock()
    )
    GatewayServiceRuntime.start(runtime)
    access.require_self_signing_state.assert_called_once()
    service.start.assert_called_once()
    GatewayServiceRuntime.shutdown(runtime)
    service.stop.assert_called_once()


def test_gateway_usage_client_encodes_cursor_and_validates_page() -> None:
    """Client query encoding preserves opaque cursors and parses the shared page model."""

    queries: list[dict[str, list[str]]] = []

    class Handler(BaseHTTPRequestHandler):
        """Return a valid accounting page through a real local HTTP boundary."""

        def do_GET(self) -> None:
            """Record query values and serve typed accounting JSON."""

            target = urlsplit(self.path)
            assert target.path == "/v1/usage"
            queries.append(parse_qs(target.query))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(_page().model_dump(mode="json")).encode())

        def log_message(self, format: str, *args: object) -> None:
            """Suppress the local HTTP test log."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        client = GatewayClient(endpoint=GatewayEndpoint(host="127.0.0.1", port=server.server_port))
        assert client.get_usage(after="opaque+cursor/position=", limit=2) == _page()
        assert queries == [{"after": ["opaque+cursor/position="], "limit": ["2"]}]
    finally:
        server.shutdown()
        worker.join(timeout=2)
        server.server_close()


def test_gateway_usage_prompt_registers_before_dispatch_and_abandons_on_failure() -> None:
    """Queued TUI submissions reserve accounting identity before the adapter receives input."""

    calls: list[str] = []
    runtime = GatewayServiceRuntime.__new__(GatewayServiceRuntime)
    runtime.m_attach_contract = SimpleNamespace(backend="local_interactive")
    runtime.m_tui_tracking = None
    runtime.m_usage_service = SimpleNamespace(
        register_managed_turn=lambda **_: calls.append("register") or "managed-a",
        abandon_managed_turn=lambda _: calls.append("abandon"),
    )

    def fail_dispatch(**_: object) -> None:
        """Fail after proving the accounting reservation already exists."""

        assert calls == ["register"]
        calls.append("dispatch")
        raise RuntimeError("dispatch failed")

    runtime.m_adapter = SimpleNamespace(submit_prompt=fail_dispatch)
    with pytest.raises(RuntimeError, match="dispatch failed"):
        runtime._submit_prompt_via_adapter(
            prompt="private prompt",
            turn_id="managed-a",
            session_selection=None,
            execution_model=None,
            note_prompt_submission=True,
        )
    assert calls == ["register", "dispatch", "abandon"]
