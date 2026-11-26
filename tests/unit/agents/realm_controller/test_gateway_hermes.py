"""Gateway control projects the exact Hermes native admission."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import HTTPException
import pytest

from houmao.agents.realm_controller.backends.hermes_tui import HermesTuiAdmission
from houmao.agents.realm_controller.errors import GatewayError
from houmao.agents.realm_controller.gateway_models import (
    GatewayAttachBackendMetadataHeadlessV1,
    GatewayAttachContractV1,
    GatewayChatSessionSelectorV1,
    GatewayControlInputRequestV1,
    GatewayPromptControlRequestV1,
    GatewayTuiTrackingTimingOverridesV1,
)
from houmao.agents.realm_controller.gateway_service import (
    GatewayServiceRuntime,
    _HermesTuiGatewayAdapter,
)
from houmao.agents.realm_controller.gateway_storage import (
    _ensure_queue_database,
    gateway_paths_from_session_root,
)
from houmao.agents.realm_controller.native_surface import TerminalNativeSurfaceV1
from houmao.gateway.access import GatewayAccessError
from tests.unit.ag_ui.test_service import _ready_service, _status


@pytest.fixture
def hermes_gateway_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> GatewayAttachContractV1:
    """Supply the verified attach inputs for an isolated gateway runtime."""

    contract = GatewayAttachContractV1(
        attach_identity="hermes-agent",
        backend="hermes_tui",
        tmux_session_name="hermes-agent",
        working_directory=str(tmp_path),
        backend_metadata=GatewayAttachBackendMetadataHeadlessV1(tool="hermes"),
        manifest_path=str(tmp_path / "manifest.json"),
        native_surface=TerminalNativeSurfaceV1(tmux_session_name="hermes-agent", pane_id="%2"),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.resolve_internal_gateway_attach_contract",
        lambda paths: contract,
    )
    return contract


@pytest.fixture
def hermes_gateway(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hermes_gateway_contract: GatewayAttachContractV1,
) -> GatewayServiceRuntime:
    """Keep admission and state projection real while substituting owner discovery."""

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=tmp_path, host="127.0.0.1", port=12345
    )
    _ensure_queue_database(runtime.m_paths.queue_path)
    manifest = SimpleNamespace(
        tool="hermes",
        backend="hermes_tui",
        mode="tui",
        native_surface=hermes_gateway_contract.native_surface,
    )
    monkeypatch.setattr(runtime, "_verified_owner_manifest", lambda **kwargs: manifest)
    monkeypatch.setattr(runtime, "_owner_prompt_attempt", lambda _: None)
    return runtime


def test_hermes_gateway_refuses_parser_timing_at_startup(
    tmp_path: Path, hermes_gateway_contract: GatewayAttachContractV1
) -> None:
    """Reject parser timing settings at the gateway's own launch entry point."""

    assert hermes_gateway_contract.backend == "hermes_tui"
    with pytest.raises(GatewayError, match="TUI tracking timings are unsupported for Hermes TUI"):
        GatewayServiceRuntime.from_gateway_root(
            gateway_root=tmp_path,
            host="127.0.0.1",
            port=12345,
            tui_tracking_timings=GatewayTuiTrackingTimingOverridesV1(
                watch_poll_interval_seconds=0.2
            ),
        )


def test_hermes_gateway_never_uses_terminal_tracking_when_native_authority_is_lost(
    hermes_gateway: GatewayServiceRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep terminal handoff and suspend semantic admission after native connection loss."""

    tracker = Mock(side_effect=AssertionError("Hermes must not create a parser tracker"))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.SingleSessionTrackingRuntime", tracker
    )
    adapter = hermes_gateway.m_adapter
    assert isinstance(adapter, _HermesTuiGatewayAdapter)
    monkeypatch.setattr(adapter, "_owner", Mock(side_effect=OSError("native unavailable")))
    reserve = Mock()
    monkeypatch.setattr(hermes_gateway, "_reserve_prompt", reserve)

    hermes_gateway._start_tui_tracking_locked()
    status = hermes_gateway.status()
    assert status.request_admission == "blocked_unavailable"
    assert status.observation is not None
    assert status.observation.source == "tui_native"
    assert status.observation.terminal_attachment == "unverified"
    assert status.observation.can_accept_prompt_now is False
    assert isinstance(status.native_surface, TerminalNativeSurfaceV1)
    assert status.native_surface.pane_id == "%2"
    with pytest.raises(HTTPException) as unavailable:
        hermes_gateway.control_prompt(GatewayPromptControlRequestV1(prompt="literal text"))
    assert unavailable.value.status_code == 503
    reserve.assert_not_called()
    for inspect in (
        hermes_gateway.get_tui_state,
        lambda: hermes_gateway.get_tui_history(limit=10),
        lambda: hermes_gateway.note_tui_prompt_submission(prompt="literal text"),
    ):
        with pytest.raises(HTTPException) as refused:
            inspect()
        assert refused.value.status_code == 501
        assert refused.value.detail["supported_state_route"] == "/v1/status"
    tracker.assert_not_called()
    assert hermes_gateway.m_tui_tracking is None


def test_hermes_gateway_refuses_keys_and_prompt_time_session_controls(
    hermes_gateway: GatewayServiceRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject raw keys and a session override before any native dispatch."""

    adapter = hermes_gateway.m_adapter
    assert isinstance(adapter, _HermesTuiGatewayAdapter)
    ready = _ready_service().model_copy(update={"source": "tui_native"})
    monkeypatch.setattr(
        adapter, "_owner", lambda: (SimpleNamespace(observe_managed_tui=lambda: ready), None)
    )
    send_keys, reserve = Mock(), Mock()
    monkeypatch.setattr(adapter, "send_control_input", send_keys)
    monkeypatch.setattr(hermes_gateway, "_reserve_prompt", reserve)
    with pytest.raises(HTTPException) as raw_keys:
        hermes_gateway.send_control_input(GatewayControlInputRequestV1(sequence="Enter"))
    assert raw_keys.value.status_code == 501
    assert raw_keys.value.detail["error_code"] == "unsupported_capability"
    send_keys.assert_not_called()

    with pytest.raises(HTTPException) as selection:
        hermes_gateway.control_prompt(
            GatewayPromptControlRequestV1(
                prompt="literal text", chat_session=GatewayChatSessionSelectorV1(mode="new")
            )
        )
    assert selection.value.status_code == 422
    assert selection.value.detail["error_code"] == "unsupported_control"
    reserve.assert_not_called()


@pytest.mark.parametrize("state", ["queued", "running", "busy"])
def test_hermes_direct_prompt_uses_the_verified_native_receipt(
    monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    """Never claim execution started just because an input entered the native queue."""

    runtime = GatewayServiceRuntime.__new__(GatewayServiceRuntime)
    runtime.m_lock = threading.Lock()
    runtime.m_tui_tracking = None
    adapter = _HermesTuiGatewayAdapter.__new__(_HermesTuiGatewayAdapter)
    runtime.m_adapter = adapter
    observation = _ready_service().model_copy(
        update={"source": "tui_native", "can_accept_prompt_now": state != "busy"}
    )
    status = _status(backend="hermes_tui", mode="tui", observation=observation)
    monkeypatch.setattr(runtime, "_active_execution_state", lambda: "idle")
    monkeypatch.setattr(runtime, "_refresh_status_snapshot", lambda **kwargs: status)
    monkeypatch.setattr(runtime, "_next_direct_headless_turn_id_locked", lambda: "request-1")
    monkeypatch.setattr(
        runtime, "_reserve_prompt", lambda **kwargs: SimpleNamespace(request_id="request-1")
    )
    monkeypatch.setattr(runtime, "fence_access", lambda *args, **kwargs: None)
    monkeypatch.setattr(runtime, "m_paths", None, raising=False)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.append_gateway_event",
        lambda *args, **kwargs: None,
    )
    submitted = []

    def submit(**kwargs: object) -> HermesTuiAdmission:
        """Return the native admission produced after the gateway's idle check."""

        submitted.append(kwargs["prompt"])
        return HermesTuiAdmission.model_validate(
            {
                "request_id": "request-1",
                "generation_id": "generation-1",
                "native_session_id": "session-1",
                "input_digest": "digest",
                "submission_id": "input-1",
                "daemon_instance_id": "daemon-1",
                "native_admission_id": "native-1",
                "status": state,
            }
        )

    request = GatewayPromptControlRequestV1(prompt="literal text")
    monkeypatch.setattr(adapter, "submit_claimed_prompt", submit)
    if state == "busy":
        with pytest.raises(HTTPException) as exc:
            runtime.control_prompt(request)
        assert exc.value.status_code == 409
        assert submitted == []
        return
    result = runtime.control_prompt(request)
    assert submitted == ["literal text"]
    assert result.native_prompt_id == "native-1"
    assert result.sent is (state == "running")
    assert result.outcome == ("queued" if state == "queued" else "handed_off")


def test_hermes_rechecks_retained_authority_without_claiming_effect_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recovery of a lost receipt stays within its one authorized effect."""

    runtime = GatewayServiceRuntime.__new__(GatewayServiceRuntime)
    fenced = []
    current = True
    monkeypatch.setattr(runtime, "fence_access", lambda grant, **values: fenced.append(values))
    monkeypatch.setattr(runtime, "_native_access_is_current", lambda grant: current)
    authorize = runtime._hermes_prompt_authorizer(None, operation_id="request-1")
    authorize()
    authorize()
    current = False
    with pytest.raises(GatewayAccessError) as exc:
        authorize()
    assert exc.value.status_code == 409
    assert fenced == [{"operation_id": "request-1"}]


@pytest.mark.parametrize("kind", ["submit_prompt", "mail_notifier_prompt"])
def test_hermes_gateway_restart_observes_queue_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Keep a native admission observing through restart and settle it without another submit."""

    runtime = GatewayServiceRuntime.__new__(GatewayServiceRuntime)
    runtime.m_paths = gateway_paths_from_session_root(session_root=tmp_path)
    runtime.m_attach_contract = SimpleNamespace(backend="hermes_tui")
    runtime.m_lock = threading.Lock()
    runtime.m_reminder_condition = threading.Condition(runtime.m_lock)
    _ensure_queue_database(runtime.m_paths.queue_path)
    with sqlite3.connect(runtime.m_paths.queue_path) as connection:
        connection.execute(
            "INSERT INTO gateway_requests (request_id, request_kind, payload_json, state, "
            "accepted_at_utc, started_at_utc, managed_agent_instance_epoch) "
            "VALUES ('request-1', ?, '{}', 'running', 'created', 'taken', 1)",
            (kind,),
        )

    admission = HermesTuiAdmission.model_validate(
        {
            "request_id": "request-1",
            "generation_id": "generation-1",
            "native_session_id": "session-1",
            "input_digest": "digest",
            "submission_id": "input-1",
            "daemon_instance_id": "daemon-1",
            "native_admission_id": "native-1",
            "status": "queued",
        }
    )
    adapter = _HermesTuiGatewayAdapter.__new__(_HermesTuiGatewayAdapter)
    monkeypatch.setattr(adapter, "read_admission", lambda request_id: admission)
    monkeypatch.setattr(runtime, "_log", lambda message: None)
    monkeypatch.setattr(runtime, "_active_execution_state", lambda: "idle")
    monkeypatch.setattr(runtime, "_refresh_status_snapshot", lambda **kwargs: None)
    runtime._record_hermes_queue_admission("request-1", admission)
    runtime._mark_running_requests_failed()
    runtime._refresh_hermes_queue_admissions(adapter)

    def stored() -> tuple[str, str | None, dict[str, object]]:
        """Read the settled or observing request from the shared queue."""

        with sqlite3.connect(runtime.m_paths.queue_path) as connection:
            state, started_at, result = connection.execute(
                "SELECT state, started_at_utc, result_json FROM gateway_requests"
            ).fetchone()
        return state, started_at, json.loads(result)

    state, started_at, result = stored()
    assert (state, started_at, result["outcome"]) == ("observing", None, "queued")
    admission = admission.model_copy(update={"status": "completed", "output_text": "Exact result"})
    runtime._refresh_hermes_queue_admissions(adapter)
    state, started_at, result = stored()
    assert (state, result["assistant_text"], result["native_turn_ids"]) == (
        "completed",
        "Exact result",
        ["native-1"],
    )
    events = [json.loads(line) for line in runtime.m_paths.events_path.read_text().splitlines()]
    assert [event["kind"] for event in events] == ["native_admission", "completed"]
