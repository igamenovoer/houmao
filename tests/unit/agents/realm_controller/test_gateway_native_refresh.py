"""Verify native refresh admission and typed gateway projection without tmux."""

from __future__ import annotations

from contextlib import nullcontext

import json
from io import BytesIO
from pathlib import Path
import sqlite3
import threading
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

from fastapi import HTTPException
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from houmao.agents.realm_controller.gateway_models import (
    GatewayControlInputRequestV1,
    GatewayPromptControlRequestV1,
    GatewayRequestCreateV1,
    GatewayRequestPayloadSubmitPromptV1,
)
from houmao.agents.realm_controller import gateway_service as service
from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_client import GatewayClient, GatewayEndpoint
from houmao.agents.realm_controller.gateway_plugin_host import GatewayPluginHost
from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime
from houmao.agents.realm_controller.native_refresh_models import (
    CommonPluginObservationV1,
    CommonPluginResourceV1,
    NativeHomeV1,
    NativeRefreshRequestV1,
    NativeRefreshResultV1,
)
from houmao.gateway.plugins import PluginDispatchError
from houmao.gateway.roster import add_admin_key
from tests.unit.agents.realm_controller.test_dsh_web_gateway import _event, _runtime
from houmao.execution.tmux import current_tmux_socket_path, tmux_server_scope
from tests.fixtures.gateway_access import (
    configure_fixture_gateway_access,
    fixture_admin_key,
    gateway_fixture_client,
)


def _observation(freshness: str = "pending", **updates: object) -> CommonPluginObservationV1:
    """Build complete common scope with explicit native readiness for gateway tests."""

    observation = CommonPluginObservationV1(
        home=NativeHomeV1(
            agent_id="agent", backend="dsh_web", tool="dsh", home_dir="/owned/native-home"
        ),
        resources=[
            CommonPluginResourceV1(
                kind=kind,
                component="native",
                freshness=freshness,
                complete=True,
                supported=True,
            )
            for kind in ("skills", "mcp")
        ],
        coverage_complete=True,
        freshness=freshness,
        native_reload=True,
    )
    return observation.model_copy(update=updates)


def _bind_native(
    runtime: GatewayServiceRuntime,
    monkeypatch: pytest.MonkeyPatch,
    observation: CommonPluginObservationV1,
) -> Mock:
    """Bind controlled live native authority without external sessions or files."""

    controller = Mock()
    controller.execution_scope.return_value = nullcontext()
    monkeypatch.setattr(runtime, "_native_refresh_controller", lambda: controller)
    monkeypatch.setattr(service, "observe_common_plugins", lambda _: observation)
    return controller


def test_native_refresh_workers_restore_controller_execution_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read-only and mutating worker threads each restore the selected owner socket."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    before = _observation()
    controller = _bind_native(runtime, monkeypatch, before)
    controller.execution_scope.side_effect = lambda: tmux_server_scope("/owner/worker.sock")
    entered: list[str] = []

    def observe(_: object) -> CommonPluginObservationV1:
        """Verify passive worker selection before returning controlled evidence."""

        assert current_tmux_socket_path() == "/owner/worker.sock"
        entered.append("observe")
        return before

    def refresh(*_args: object, **_kwargs: object) -> NativeRefreshResultV1:
        """Verify mutating handoff independently of the caller's thread context."""

        assert current_tmux_socket_path() == "/owner/worker.sock"
        entered.append("refresh")
        return NativeRefreshResultV1(
            method="native_reload", outcome="refreshed", observation=_observation("current")
        )

    monkeypatch.setattr(service, "observe_common_plugins", observe)
    monkeypatch.setattr(service, "perform_native_refresh", refresh)
    with tmux_server_scope("/operator/enclosing.sock"):
        result = runtime.refresh_native(NativeRefreshRequestV1())
        assert current_tmux_socket_path() == "/operator/enclosing.sock"
    assert result.outcome == "refreshed"
    assert entered == ["observe", "refresh"]


def _http_client(
    runtime: GatewayServiceRuntime, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> TestClient:
    """Expose real route validation without gateway background services."""

    configure_fixture_gateway_access(tmp_path, monkeypatch)
    runtime.m_paths.gateway_root = tmp_path
    runtime.m_manifest_path = tmp_path / "manifest.json"
    runtime.m_access_runtime = None
    runtime.m_access_policy = None
    runtime.m_port = 43123
    runtime.m_presence_id = "refresh-test-listener"
    runtime.m_native_refresh_active = False
    runtime.m_plugin_lifecycle_deferred = True

    def prepare_host(app: FastAPI) -> None:
        """Stage the default empty plugin inventory in the fixture root."""

        host = GatewayPluginHost()
        host.m_gateway_root = tmp_path
        runtime.m_plugin_host = host
        host.stage(app)

    monkeypatch.setattr(runtime, "prepare_plugin_host", prepare_host)
    monkeypatch.setattr(runtime, "emit_diagnostic", Mock())
    return gateway_fixture_client(runtime)


def test_native_refresh_rechecks_open_authority_after_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A first-key enrollment that wins the observation race prevents native effects."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    client = _http_client(runtime, tmp_path, monkeypatch)
    observation = _observation()
    _bind_native(runtime, monkeypatch, observation)
    admin, _ = fixture_admin_key(tmp_path, "native-owner")
    store = runtime._require_access_policy().store
    native = Mock()

    def observe(_: object) -> CommonPluginObservationV1:
        """Change the roster while the authorized request prepares its mutation."""

        store.update(
            lambda state: add_admin_key(state, admin), actor="owner", action="admin.key.add"
        )
        return observation

    monkeypatch.setattr(service, "observe_common_plugins", observe)
    monkeypatch.setattr(service, "plan_native_refresh", lambda _: None)
    monkeypatch.setattr(service, "perform_native_refresh", native)
    response = client.post("/v1/control/refresh", json={})
    assert response.status_code in {403, 409}
    assert store.snapshot().admin_mode == "keyed"
    native.assert_not_called()
    assert not runtime.m_native_refresh_active


@pytest.mark.parametrize("uncertain", [False, True])
def test_native_refresh_blocks_ordinary_prompt_and_plugin_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, uncertain: bool
) -> None:
    """A reservation rejects managed input even when native state still looks idle."""

    runtime, adapter, _ = _runtime(tmp_path, monkeypatch)
    runtime.m_native_refresh_active = not uncertain
    runtime.m_native_refresh_uncertain = uncertain
    dispatched = Mock()
    monkeypatch.setattr(adapter, "submit_plugin_event", dispatched)
    for policy in ("ready_only", "if_no_pending", "always"):
        with pytest.raises(HTTPException) as error:
            runtime.control_prompt(
                GatewayPromptControlRequestV1(prompt="work", admission_policy=policy)
            )
        assert error.value.status_code == 409
    with pytest.raises(HTTPException) as error:
        runtime.create_request(
            GatewayRequestCreateV1(
                kind="submit_prompt", payload=GatewayRequestPayloadSubmitPromptV1(prompt="work")
            )
        )
    assert error.value.status_code == 409
    with pytest.raises(PluginDispatchError) as error:
        runtime.dispatch_plugin_event(
            _event(),
            instance_id="owner",
            binding_id="bound",
            timeout_seconds=1,
            is_active=lambda: True,
        )
    assert error.value.status_code == 409
    dispatched.assert_not_called()
    with sqlite3.connect(runtime.m_paths.queue_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM gateway_requests").fetchone()[0] == 0


def test_native_refresh_allows_interrupt_ahead_of_older_queued_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recovery remains executable while ordinary queued work waits for settlement."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    runtime.m_native_refresh_active = True
    runtime.m_native_refresh_uncertain = False
    with sqlite3.connect(runtime.m_paths.queue_path) as connection:
        for name, kind, payload in (
            ("older", "submit_prompt", {"prompt": "work"}),
            ("interrupt", "interrupt", {}),
        ):
            connection.execute(
                "INSERT INTO gateway_requests "
                "(request_id,request_kind,payload_json,state,accepted_at_utc,managed_agent_instance_epoch) "
                "VALUES (?,?,?,'accepted',?,1)",
                (name, kind, json.dumps(payload), "2026-11-17T00:00:00Z"),
            )
        connection.commit()
    chosen = runtime._take_next_request()
    assert chosen is not None and chosen.request_id == "interrupt"
    with sqlite3.connect(runtime.m_paths.queue_path) as connection:
        assert (
            connection.execute(
                "SELECT state FROM gateway_requests WHERE request_id='older'"
            ).fetchone()[0]
            == "accepted"
        )
    assert GatewayServiceRuntime._active_execution_state(runtime) == "running"


def test_native_refresh_blocks_raw_input_for_terminal_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Raw input cannot bypass a managed refresh reservation."""

    runtime, adapter, _ = _runtime(tmp_path, monkeypatch)
    runtime.m_attach_contract.backend = "local_interactive"
    runtime.m_native_refresh_active = True
    runtime.m_native_refresh_uncertain = False
    sent = Mock()
    monkeypatch.setattr(adapter, "send_control_input", sent)
    with pytest.raises(HTTPException) as error:
        runtime.send_control_input(GatewayControlInputRequestV1(sequence="unsafe text"))
    assert error.value.status_code == 409
    sent.assert_not_called()


def test_native_refresh_does_not_commit_notifier_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Notifier admission retains no ordinary work while refresh owns its boundary."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    runtime.m_native_refresh_active = False
    runtime.m_native_refresh_uncertain = True
    assert (
        runtime._enqueue_internal_prompt(
            prompt="notification", scope_key="scope", cycle_key="cycle", origin=Mock()
        )
        is None
    )
    with sqlite3.connect(runtime.m_paths.queue_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM gateway_requests").fetchone()[0] == 0


def test_native_refresh_defers_reminder_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A native refresh reservation prevents a due reminder from waking the agent."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    runtime.m_native_refresh_active = True
    runtime.m_native_refresh_uncertain = False
    baseline = runtime.status()
    monkeypatch.setattr(
        runtime,
        "_active_execution_state",
        lambda: GatewayServiceRuntime._active_execution_state(runtime),
    )
    monkeypatch.setattr(
        runtime,
        "_refresh_status_snapshot",
        lambda *, active_execution: baseline.model_copy(
            update={"active_execution": active_execution}
        ),
    )
    monkeypatch.setattr(runtime, "_effective_due_reminder_locked", lambda: SimpleNamespace())
    deferred = Mock()

    def stop_after_deferral(*args: object, **kwargs: object) -> None:
        """Bound the actual reminder loop after its first admission decision."""

        deferred(*args, **kwargs)
        runtime.m_stop_event.set()

    monkeypatch.setattr(runtime, "_record_reminder_deferral_locked", stop_after_deferral)
    submitted = Mock()
    monkeypatch.setattr(runtime, "_submit_prompt_via_adapter", submitted)
    runtime._reminder_loop()
    deferred.assert_called_once()
    submitted.assert_not_called()


@pytest.mark.parametrize(
    "method,outcome", [("noop", "already_current"), ("automatic", "automatic")]
)
def test_readonly_refresh_plan_succeeds_during_active_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method: str, outcome: str
) -> None:
    """Already current and qualified automatic results do not reserve native mutation."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    observation = _observation("current", automatic=method == "automatic")
    _bind_native(runtime, monkeypatch, observation)
    runtime.m_native_refresh_active = True
    expected = NativeRefreshResultV1(method=method, outcome=outcome, observation=observation)
    monkeypatch.setattr(service, "plan_native_refresh", lambda _: expected)
    native = Mock()
    monkeypatch.setattr(service, "perform_native_refresh", native)
    assert runtime.refresh_native(NativeRefreshRequestV1()) == expected
    assert runtime.m_native_refresh_active
    native.assert_not_called()


def test_refresh_timeout_keeps_guard_until_actual_settlement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lost confirmation cannot admit input; healthy settlement need not prove freshness."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    observation = _observation()
    _bind_native(runtime, monkeypatch, observation)
    monkeypatch.setattr(service, "plan_native_refresh", lambda _: None)
    entered = threading.Event()
    finish = threading.Event()
    calls = Mock()

    def native(*args: object, **kwargs: object) -> NativeRefreshResultV1:
        """Hold a native operation past its caller budget, then settle with unknown freshness."""

        calls(*args, **kwargs)
        entered.set()
        assert finish.wait(timeout=2)
        return NativeRefreshResultV1(
            method="native_reload",
            outcome="partial",
            observation=_observation("unknown"),
            effects="partial",
        )

    monkeypatch.setattr(service, "perform_native_refresh", native)
    try:
        result = runtime.refresh_native(NativeRefreshRequestV1(timeout_seconds=0.02))
        assert entered.is_set()
        assert result.outcome == "outcome_unknown"
        assert not result.native_settled and not result.native_ready
        assert runtime.m_native_refresh_active
        assert runtime.m_lock.acquire(timeout=0.1)
        runtime.m_lock.release()
        assert runtime.health().status == "ok"
        refusal = runtime.refresh_native(NativeRefreshRequestV1(timeout_seconds=0.02))
        assert refusal.outcome == "busy"
        calls.assert_called_once()
    finally:
        finish.set()
        runtime.m_native_refresh_thread.join(timeout=2)
    assert not runtime.m_native_refresh_active
    assert not runtime.m_native_refresh_uncertain


@pytest.mark.parametrize("pending", ["prompt_control", "queued_prompt"])
def test_mutating_refresh_refuses_already_admitted_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pending: str
) -> None:
    """A native reload cannot overtake accepted ordinary input or dispatch preparation."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    _bind_native(runtime, monkeypatch, _observation())
    monkeypatch.setattr(service, "plan_native_refresh", lambda _: None)
    native = Mock()
    monkeypatch.setattr(service, "perform_native_refresh", native)
    if pending == "prompt_control":
        runtime.m_prompt_control_inflight = 1
        monkeypatch.setattr(
            runtime,
            "_active_execution_state",
            lambda: GatewayServiceRuntime._active_execution_state(runtime),
        )
    else:
        with sqlite3.connect(runtime.m_paths.queue_path) as connection:
            connection.execute(
                "INSERT INTO gateway_requests "
                "(request_id,request_kind,payload_json,state,accepted_at_utc,managed_agent_instance_epoch) "
                "VALUES ('older','submit_prompt','{}','accepted','2026-11-17T00:00:00Z',1)"
            )
            connection.commit()
    result = runtime.refresh_native(NativeRefreshRequestV1())
    assert result.outcome == "busy"
    assert result.effects == "absent"
    native.assert_not_called()


def test_passive_observation_releases_uncertain_guard_only_on_settled_readiness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Current freshness alone cannot clear a live or uncertain native maintenance operation."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    current = _observation("current", native_settled=False, native_ready=False)
    _bind_native(runtime, monkeypatch, current)
    runtime.m_native_refresh_active = False
    runtime.m_native_refresh_uncertain = True
    assert runtime.observe_common_plugins().freshness == "current"
    assert runtime.m_native_refresh_uncertain
    monkeypatch.setattr(service, "observe_common_plugins", lambda _: _observation("unknown"))
    assert runtime.observe_common_plugins().freshness == "unknown"
    assert not runtime.m_native_refresh_uncertain
    runtime.m_native_refresh_active = True
    runtime.observe_common_plugins()
    assert runtime.m_native_refresh_active


def test_passive_read_started_during_refresh_cannot_clear_later_uncertainty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale ready snapshot cannot settle an operation that completed during the read."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    _bind_native(runtime, monkeypatch, _observation("current"))
    runtime.m_native_refresh_active = True
    runtime.m_native_refresh_uncertain = False

    def stale_read(_: object) -> CommonPluginObservationV1:
        """Model readiness captured before a native reload reports uncertain effects."""

        runtime.m_native_refresh_active = False
        runtime.m_native_refresh_uncertain = True
        return _observation("current")

    monkeypatch.setattr(service, "observe_common_plugins", stale_read)
    runtime.observe_common_plugins()
    assert runtime.m_native_refresh_uncertain


@pytest.mark.parametrize(
    "outcome,status_code",
    [("refreshed", 200), ("restart_required", 409), ("unsupported", 501), ("partial", 503)],
)
def test_refresh_http_preserves_typed_effects_and_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str, status_code: int
) -> None:
    """HTTP refusal codes retain typed observations and partial native effects."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    result = NativeRefreshResultV1(
        method="native_reload",
        outcome=outcome,
        observation=_observation("current" if outcome == "refreshed" else "unknown"),
        effects="confirmed" if outcome == "refreshed" else "partial",
        diagnostics=["native_extension_requires_restart"],
    )
    refresh = Mock(return_value=result)
    monkeypatch.setattr(runtime, "refresh_native", refresh)
    client = _http_client(runtime, tmp_path, monkeypatch)
    response = client.post("/v1/control/refresh", json={"timeout_seconds": 0.1})
    assert response.status_code == status_code
    assert response.json() == result.model_dump(mode="json")
    refresh.assert_called_once()
    assert refresh.call_args.args == (NativeRefreshRequestV1(timeout_seconds=0.1),)
    assert refresh.call_args.kwargs["expected_home_etag"] is None
    authority = refresh.call_args.kwargs["authority"]
    assert [permission.action for permission in authority.permissions] == ["native.refresh.apply"]


@pytest.mark.parametrize(
    "payload",
    [
        {"force": "private-config-value"},
        {"restart": True},
        {"unknown": True},
        {"timeout_seconds": 0},
        {"timeout_seconds": 121},
        {"timeout_seconds": "10"},
        {"timeout_seconds": float("inf")},
    ],
)
def test_refresh_http_rejects_invalid_input_before_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: dict[str, object]
) -> None:
    """Strict validation refuses force/restart, unknown fields, and invalid budgets safely."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    refresh = Mock()
    monkeypatch.setattr(runtime, "refresh_native", refresh)
    client = _http_client(runtime, tmp_path, monkeypatch)
    encoded = json.dumps(payload)
    response = client.post(
        "/v1/control/refresh", content=encoded, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert "private-config-value" not in response.text
    refresh.assert_not_called()


@pytest.mark.parametrize("freshness", ["pending", "unknown"])
def test_common_plugin_get_is_passive_and_returns_200_for_incomplete_freshness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, freshness: str
) -> None:
    """Observation does not initiate refresh or convert pending evidence into server failure."""

    runtime, adapter, _ = _runtime(tmp_path, monkeypatch)
    observation = _observation(freshness)
    controller = _bind_native(runtime, monkeypatch, observation)
    monkeypatch.setattr(service, "inspect_native_home", lambda _: observation.home)
    recoverable_inspection = Mock()
    monkeypatch.setattr(adapter, "inspect_target", recoverable_inspection)
    native = Mock()
    monkeypatch.setattr(service, "perform_native_refresh", native)
    client = _http_client(runtime, tmp_path, monkeypatch)
    assert client.get("/v1/native-home").json() == observation.home.model_dump(mode="json")
    response = client.get("/v1/control/refresh")
    assert response.status_code == 200
    assert response.json()["freshness"] == freshness
    native.assert_not_called()
    controller.assert_not_called()
    recoverable_inspection.assert_not_called()


def test_pair_managed_gateway_reports_unknown_scope_and_unsupported_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A gateway without local controller preserves qualified home but invents no refresh path."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    runtime.m_adapter = object.__new__(service._ServerManagedHeadlessGatewayAdapter)
    runtime.m_manifest_path = tmp_path / "manifest.json"
    home = _observation().home
    inspect = Mock(return_value=home)
    monkeypatch.setattr(service, "inspect_native_home_from_manifest", inspect)
    controller = Mock()
    monkeypatch.setattr(runtime, "_native_refresh_controller", controller)
    native = Mock()
    monkeypatch.setattr(service, "perform_native_refresh", native)
    client = _http_client(runtime, tmp_path, monkeypatch)
    assert client.get("/v1/native-home").json() == home.model_dump(mode="json")
    observation = client.get("/v1/control/refresh")
    assert observation.status_code == 200
    assert observation.json()["freshness"] == "unknown"
    assert {item["kind"] for item in observation.json()["resources"]} == {"skills", "mcp"}
    result = client.post("/v1/control/refresh", json={})
    assert result.status_code == 501
    assert result.json()["outcome"] == "unsupported"
    controller.assert_not_called()
    native.assert_not_called()


@pytest.mark.parametrize("status_code,outcome", [(409, "restart_required"), (503, "partial")])
def test_refresh_client_preserves_typed_refusal_and_uses_requested_budget(
    status_code: int, outcome: str
) -> None:
    """Typed non-success HTTP bodies keep partial evidence without any retry."""

    result = NativeRefreshResultV1(
        method="native_reload",
        outcome=outcome,
        observation=_observation("unknown"),
        effects="partial",
        diagnostics=["native_host_modules_pending"],
    )
    client = GatewayClient(endpoint=GatewayEndpoint(host="127.0.0.1", port=43000))
    client.m_opener = Mock()
    client.m_opener.open.side_effect = HTTPError(
        "http://127.0.0.1:43000/v1/control/refresh",
        status_code,
        "native refusal",
        {},
        BytesIO(result.model_dump_json().encode()),
    )
    assert client.refresh_native(NativeRefreshRequestV1(timeout_seconds=100.0)) == result
    client.m_opener.open.assert_called_once()
    request = client.m_opener.open.call_args.args[0]
    assert request.method == "POST"
    assert request.full_url.endswith("/v1/control/refresh")
    assert json.loads(request.data) == {"schema_version": 1, "timeout_seconds": 100.0}
    assert client.m_opener.open.call_args.kwargs["timeout"] == 105.0


@pytest.mark.parametrize(
    "bad_body", [b"invalid private-config-value", b'{"detail":"private-config-value"}']
)
def test_refresh_client_does_not_expose_invalid_refusal_body(bad_body: bytes) -> None:
    """Malformed native refusal cannot leak a private config or exception body."""

    client = GatewayClient(endpoint=GatewayEndpoint(host="127.0.0.1", port=43000))
    client.m_opener = Mock()
    client.m_opener.open.side_effect = HTTPError(
        "http://127.0.0.1:43000/v1/control/refresh", 503, "failure", {}, BytesIO(bad_body)
    )
    with pytest.raises(GatewayHttpError) as error:
        client.refresh_native(NativeRefreshRequestV1())
    assert "private-config-value" not in str(error.value)
    assert error.value.status_code == 503
    client.m_opener.open.assert_called_once()


def test_refresh_client_does_not_retry_after_lost_confirmation() -> None:
    """Transport timeout reports a safe error and leaves operation settlement to the gateway."""

    client = GatewayClient(endpoint=GatewayEndpoint(host="127.0.0.1", port=43000))
    client.m_opener = Mock()
    client.m_opener.open.side_effect = URLError("private-config-value")
    with pytest.raises(GatewayHttpError) as error:
        client.refresh_native(NativeRefreshRequestV1(timeout_seconds=0.01))
    assert "private-config-value" not in str(error.value)
    assert "not retried" in str(error.value)
    client.m_opener.open.assert_called_once()


@pytest.mark.parametrize("method", ["get_native_home", "get_common_plugin_state"])
@pytest.mark.parametrize("payload", [b'{"private":"private-config-value"}', b"\xff"])
def test_native_read_client_hides_invalid_response_contents(method: str, payload: bytes) -> None:
    """Read failures preserve privacy even before a passive-server proxy sanitizes them."""

    client = GatewayClient(endpoint=GatewayEndpoint(host="127.0.0.1", port=43000))
    client.m_opener = Mock()
    client.m_opener.open.return_value = BytesIO(payload)
    with pytest.raises(GatewayHttpError) as error:
        getattr(client, method)()
    assert "private-config-value" not in str(error.value)
    client.m_opener.open.assert_called_once()
