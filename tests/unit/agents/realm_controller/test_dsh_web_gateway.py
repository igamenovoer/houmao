"""Hermetic native Web gateway admission and terminal capability boundaries."""

from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager
import json
import sqlite3
import subprocess
from types import SimpleNamespace
import threading
from unittest.mock import Mock

from fastapi import HTTPException
import pytest

from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.backends.dsh_web_client import DshWebError
from houmao.ag_ui.mapper import AgUiEventMapper
from houmao.ag_ui.runtime import ag_ui_target_transport_family_for_backend
from houmao.agents.realm_controller.gateway_models import (
    GatewayControlInputRequestV1,
    GatewayPromptControlRequestV1,
    GatewayRequestCreateV1,
    GatewayWebActiveTurnV1,
    GatewayStatusV1,
    GatewayTuiTrackingTimingConfigV1,
)
from houmao.agents.realm_controller import runtime as runtime_module
from houmao.agents.realm_controller.gateway_service import (
    GatewayServiceRuntime,
    _NativeWebGatewayAdapter,
)
from houmao.agents.realm_controller.web_observation import WebObservation
from houmao.agents.realm_controller.models import SessionEvent
from houmao.agents.realm_controller.gateway_storage import (
    _ensure_queue_database,
    queue_depth_from_sqlite,
)
from houmao.mailbox.notifier_admission import ReminderOrigin
from houmao.gateway.plugins import PluginDispatchError, PluginEvent
from tests.unit.agents.realm_controller.test_dsh_web_observation import _metadata, _page, _state


@pytest.mark.parametrize("execution_mode", ["detached_process", "tmux_auxiliary_window"])
def test_web_internal_gateway_start_omits_terminal_timing_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, execution_mode: str
) -> None:
    """Resolved defaults do not become explicit terminal options in a Web companion child."""

    captured: list[object] = []
    controller = SimpleNamespace(
        launch_plan=SimpleNamespace(backend="dsh_web", mode="web", working_directory=tmp_path),
        _require_tmux_session_name=lambda: "owned-supervisor",
    )
    paths = SimpleNamespace(gateway_root=tmp_path, log_path=tmp_path / "gateway.log")

    def capture_process(argv: object, **_kwargs: object) -> None:
        """Inspect the child command without spawning a process or touching tmux."""

        captured.append(argv)
        raise OSError("controlled stop before process launch")

    if execution_mode == "detached_process":
        monkeypatch.setattr(runtime_module.subprocess, "Popen", capture_process)
        with pytest.raises(OSError, match="controlled stop"):
            runtime_module._start_gateway_process(
                controller=controller,
                paths=paths,
                host="127.0.0.1",
                port=0,
                execution_mode=execution_mode,
                tui_tracking_timings=GatewayTuiTrackingTimingConfigV1(),
            )
    else:

        def capture_tmux(argv: list[str]) -> subprocess.CompletedProcess[str]:
            """Capture the isolated supervisor command without invoking tmux."""

            captured.append(argv[-1])
            return subprocess.CompletedProcess(argv, 0, stdout="@2\t2\t%4\n", stderr="")

        monkeypatch.setattr(runtime_module, "run_tmux_shared", capture_tmux)
        runtime_module._launch_same_session_gateway_window(
            controller=controller,
            session_name="owned-supervisor",
            paths=paths,
            host="127.0.0.1",
            port=0,
            tui_tracking_timings=GatewayTuiTrackingTimingConfigV1(),
        )
    assert captured and "--tui-" not in str(captured[0])


def _runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[GatewayServiceRuntime, _NativeWebGatewayAdapter, Mock]:
    """Create a semantic gateway with controlled native authority and no tmux access."""

    native = WebObservation(metadata=_metadata(), state=_state, history=lambda **_: _page(1))
    state = native.refresh()
    adapter = object.__new__(_NativeWebGatewayAdapter)
    adapter.m_attach_contract = SimpleNamespace(backend="dsh_web", native_surface=None)
    adapter.m_attempts = {}
    monkeypatch.setattr(
        adapter,
        "capture_plugin_execution_identity",
        lambda: ("generation", "host", "body", "native"),
    )
    cancelled = Mock()
    monkeypatch.setattr(adapter, "cancel_plugin_event", cancelled)
    runtime = object.__new__(GatewayServiceRuntime)
    runtime.m_adapter = adapter
    runtime.m_attach_contract = adapter.m_attach_contract
    runtime.m_lock = threading.Lock()
    runtime.m_reminder_condition = threading.Condition(runtime.m_lock)
    runtime.m_stop_event = threading.Event()
    runtime.m_worker_thread = threading.current_thread()
    runtime.m_host = "127.0.0.1"
    runtime.m_plugin_host = None
    runtime.m_plugin_dispatch_pending = False
    runtime.m_current_epoch = 1
    runtime.m_direct_prompt_thread = None
    runtime.m_direct_prompt_turn_id = None
    runtime.m_headless_next_prompt_override = None
    runtime.m_tui_tracking = None
    runtime.m_usage_manifest_path = tmp_path / "manifest.json"
    runtime.m_paths = SimpleNamespace(
        events_path=tmp_path / "events.jsonl", queue_path=tmp_path / "queue.sqlite"
    )
    _ensure_queue_database(runtime.m_paths.queue_path)
    status = GatewayStatusV1(
        attach_identity="runtime",
        backend="dsh_acp",
        tmux_session_name="supervisor",
        gateway_health="healthy",
        managed_agent_connectivity="connected",
        managed_agent_recovery="idle",
        request_admission="open",
        terminal_surface_eligibility="unknown",
        active_execution="idle",
        queue_depth=0,
        gateway_host="127.0.0.1",
        gateway_port=43123,
        managed_agent_instance_epoch=1,
        web=state,
        native_surface_kind="web",
        native_surface_eligibility="ready",
    )
    monkeypatch.setattr(runtime, "_refresh_status_snapshot", lambda **_: status)
    monkeypatch.setattr(runtime, "_active_execution_state", lambda: "idle")
    monkeypatch.setattr(runtime, "_next_direct_headless_turn_id_locked", lambda: "operation-one")
    return runtime, adapter, cancelled


def _event() -> PluginEvent:
    """Build a routine owner-bound service notification."""

    return PluginEvent(source_event_id="event-one", text="controlled notification")


def test_web_plugin_event_confirms_native_ready_only_handoff_without_terminal_tracking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An ordinary notification confirms native insertion without creating a replay queue."""

    runtime, adapter, cancelled = _runtime(tmp_path, monkeypatch)
    dispatched = Mock()

    def submit(**kwargs: object) -> None:
        """Confirm only after checking the actual native insertion boundary."""

        dispatched(**kwargs)
        control = kwargs["control"]
        control.require_allowed()
        control.confirm_handoff()

    monkeypatch.setattr(adapter, "submit_plugin_event", submit)
    result = runtime.dispatch_plugin_event(
        _event(), instance_id="owner", binding_id="bound", timeout_seconds=1, is_active=lambda: True
    )
    assert result.source_event_id == "event-one"
    assert dispatched.call_count == 1
    assert dispatched.call_args.kwargs["session_selection"] is None
    assert not cancelled.called
    assert not runtime.m_plugin_dispatch_pending


@pytest.mark.parametrize("posture", ["active", "inbox", "approval", "unknown"])
def test_web_ordinary_event_refuses_closed_native_admission_before_any_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, posture: str
) -> None:
    """Browser work, pending input, questions, and unknown authority never enter a gateway queue."""

    runtime, adapter, cancelled = _runtime(tmp_path, monkeypatch)
    status = runtime._refresh_status_snapshot(active_execution="idle")
    payload = _state()
    payload["admission"] = {
        "ready_only": False,
        "if_no_pending": False,
        "always": True,
        "reason": posture,
    }
    if posture == "active":
        payload["active_turn"] = {"turn": 5, "start_sequence": 19}
    elif posture == "inbox":
        payload["pending_inbox"] = [
            {
                "message_id": "human",
                "placement": "next_turn",
                "operation_id": None,
                "operator": None,
            }
        ]
    elif posture == "approval":
        payload["interaction_waits"] = ["approval"]
    else:
        payload["available"] = False
    observed = WebObservation(
        metadata=_metadata(), state=lambda: payload, history=lambda **_: _page(1)
    ).refresh()
    status.web = observed
    if posture == "unknown":
        status.managed_agent_connectivity = "unavailable"
    dispatch = Mock()
    monkeypatch.setattr(adapter, "submit_plugin_event", dispatch)
    with pytest.raises(PluginDispatchError):
        runtime.dispatch_plugin_event(
            _event(),
            instance_id="owner",
            binding_id="bound",
            timeout_seconds=1,
            is_active=lambda: True,
        )
    dispatch.assert_not_called()
    cancelled.assert_not_called()
    assert runtime.m_direct_prompt_thread is None
    with pytest.raises(HTTPException) as rejected:
        runtime.create_request(
            GatewayRequestCreateV1(kind="submit_prompt", payload={"prompt": "ordinary request"})
        )
    assert rejected.value.status_code == (503 if posture == "unknown" else 409)


@pytest.mark.parametrize("failure", ["human_won", "replacement", "expiry"])
def test_web_ordinary_event_native_refusal_or_execution_loss_never_replays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """A readiness race, replacement, or lost lifetime produces immediate refusal."""

    runtime, adapter, cancelled = _runtime(tmp_path, monkeypatch)
    inserted: list[str] = []
    identities = [("generation", "host", "body", "native")]
    monkeypatch.setattr(adapter, "capture_plugin_execution_identity", lambda: identities[-1])

    def submit(**kwargs: object) -> None:
        """Fail at the guarded native boundary before any inbox insertion."""

        if failure == "replacement":
            identities.append(("generation", "newhost", "newbody", "native"))
        elif failure == "expiry":
            kwargs["control"].cancel()
        kwargs["control"].require_allowed()
        raise BackendExecutionError("Native human work won the true-idle claim")

    dispatch = Mock(side_effect=submit)
    monkeypatch.setattr(adapter, "submit_plugin_event", dispatch)
    with pytest.raises(PluginDispatchError):
        runtime.dispatch_plugin_event(
            _event(),
            instance_id="owner",
            binding_id="bound",
            timeout_seconds=0.2,
            is_active=lambda: True,
        )
    assert inserted == []
    assert dispatch.call_count == 1
    assert cancelled.call_count == 1
    worker = runtime.m_direct_prompt_thread
    if worker is not None:
        worker.join(timeout=1)
    assert runtime.m_direct_prompt_turn_id is None


@pytest.mark.parametrize("policy", ["ready_only", "if_no_pending", "always"])
def test_web_explicit_operator_policy_is_forwarded_only_when_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, policy: str
) -> None:
    """Direct operator requests preserve the native policy instead of upgrading ordinary events."""

    runtime, adapter, _ = _runtime(tmp_path, monkeypatch)
    dispatched = Mock()

    def submit(**kwargs: object) -> None:
        """Acknowledge insertion separately from any later native terminal turn."""

        dispatched(**kwargs)
        kwargs["control"].confirm_handoff()

    monkeypatch.setattr(adapter, "submit_scoped_web_prompt", submit)
    result = runtime.control_prompt(
        GatewayPromptControlRequestV1(prompt="operator", admission_policy=policy)
    )
    assert result.operation_id == "operation-one"
    assert result.admission_policy == policy
    assert dispatched.call_args.kwargs["operator"] is True
    assert dispatched.call_args.kwargs["admission_policy"] == policy


def test_web_gateway_reports_a_redacted_native_control_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Expose only the sanitized native diagnostic alongside the gateway refusal code."""

    runtime, adapter, cancelled = _runtime(tmp_path, monkeypatch)
    submit = Mock(
        side_effect=DshWebError("not_ready", "Human turn active. Bearer private-provider-key")
    )
    monkeypatch.setattr(adapter, "submit_scoped_web_prompt", submit)
    with pytest.raises(HTTPException) as failed:
        runtime.control_prompt(GatewayPromptControlRequestV1(prompt="operator"))
    assert failed.value.status_code == 409
    assert failed.value.detail["error_code"] == "dispatch_failed"
    detail = failed.value.detail["detail"]
    assert "not_ready: Human turn active" in detail
    assert "[REDACTED]" in detail and "private-provider-key" not in detail
    submit.assert_called_once()
    cancelled.assert_called_once()


def test_web_new_session_is_explicit_ready_only_and_uses_guarded_backend_reset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicit new request forwards reset intent under the unchanged owned host."""

    runtime, adapter, _ = _runtime(tmp_path, monkeypatch)
    identities = [("generation", "host", "body", "native")]
    monkeypatch.setattr(adapter, "capture_plugin_execution_identity", lambda: identities[-1])
    dispatched = Mock()

    def submit(**kwargs: object) -> None:
        """Simulate the exact new binding returned by guarded native reset."""

        dispatched(**kwargs)
        identities.append(("generation", "host", "new-body", "new-native"))
        kwargs["control"].confirm_handoff()

    monkeypatch.setattr(adapter, "submit_scoped_web_prompt", submit)
    result = runtime.control_prompt(
        GatewayPromptControlRequestV1(
            prompt="new conversation",
            chat_session={"mode": "new"},
        )
    )
    assert result.sent
    assert dispatched.call_args.kwargs["session_selection"].mode == "new"
    assert dispatched.call_args.kwargs["operator"] is True
    with pytest.raises(HTTPException) as caught:
        runtime.control_prompt(
            GatewayPromptControlRequestV1(
                prompt="must refuse",
                admission_policy="always",
                chat_session={"mode": "new"},
            )
        )
    assert caught.value.status_code == 422
    assert dispatched.call_count == 1


@pytest.mark.parametrize("route", ["keys", "state", "history", "note"])
def test_web_terminal_routes_explicitly_report_supported_native_inspection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    """Unsupported terminal operations never touch a supervisor pane."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    with pytest.raises(HTTPException) as caught:
        if route == "keys":
            runtime.send_control_input(GatewayControlInputRequestV1(sequence="<[C-c]>"))
        elif route == "state":
            runtime.get_tui_state()
        elif route == "history":
            runtime.get_tui_history(limit=10)
        else:
            runtime.note_tui_prompt_submission(prompt="forbidden")
    assert caught.value.status_code == 501
    assert caught.value.detail["error_code"] == "unsupported_capability"
    assert caught.value.detail["supported_state_route"] == "/v1/control/web/state"


def test_web_ag_ui_activity_preserves_shared_native_state_without_output_ownership_claim() -> None:
    """Common consumers receive a Web activity snapshot instead of terminal text."""

    state = WebObservation(
        metadata=_metadata(), state=_state, history=lambda **_: _page(1)
    ).refresh()
    mapper = AgUiEventMapper(thread_id="thread", run_id="run", parent_run_id=None)
    events = mapper.map_web_observation(state, sequence_index=0)
    assert ag_ui_target_transport_family_for_backend("dsh_web") == "web"
    assert len(events) == 1
    event = events[0].model_dump(mode="json")
    assert event["activity_type"] == "houmao.web.state"
    assert '"source": "houmao.web"' in event["content"]
    assert '"native_session_id": "native"' in event["content"]
    assert "editing_input" not in event["content"]


def test_web_public_request_returns_after_native_admission_and_stores_only_operation_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Accepted Web requests observe admitted execution instead of entering a replay queue."""

    runtime, adapter, _ = _runtime(tmp_path, monkeypatch)
    finish = threading.Event()
    workers = []
    dispatched = Mock()

    def submit(**kwargs: object) -> None:
        """Keep real completion pending after the native handoff acknowledgement."""

        workers.append(threading.current_thread())
        dispatched(**kwargs)
        kwargs["control"].confirm_handoff()
        assert finish.wait(2)

    monkeypatch.setattr(adapter, "submit_scoped_web_prompt", submit)
    try:
        accepted = runtime.create_request(
            GatewayRequestCreateV1(
                kind="submit_prompt", payload={"prompt": "private executable input"}
            )
        )
        assert accepted.queue_depth == 0
        with sqlite3.connect(runtime.m_paths.queue_path) as connection:
            row = connection.execute(
                "SELECT state,payload_json FROM gateway_requests WHERE request_id=?",
                (accepted.request_id,),
            ).fetchone()
        assert row[0] == "observing"
        assert "private executable input" not in row[1] and "prompt" not in row[1]
        assert queue_depth_from_sqlite(runtime.m_paths.queue_path) == 0
        assert dispatched.call_args.kwargs["operator"] is False
        assert dispatched.call_args.kwargs["admission_policy"] == "ready_only"
        runtime._mark_running_requests_failed()
    finally:
        finish.set()
        for worker in workers:
            worker.join(timeout=2)
    with sqlite3.connect(runtime.m_paths.queue_path) as connection:
        assert connection.execute("SELECT state FROM gateway_requests").fetchone()[0] == "uncertain"
    assert dispatched.call_count == 1


@pytest.mark.parametrize("entrypoint", ["direct", "request", "plugin"])
def test_kimi_web_reports_a_native_queue_race_without_replaying(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entrypoint: str
) -> None:
    """One stock native queue acknowledgement remains visible to the caller."""

    runtime, adapter, _ = _runtime(tmp_path, monkeypatch)
    metadata = _metadata().model_copy(update={"tool": "kimi"})
    adapter.m_attach_contract.backend = "kimi_web"
    adapter.m_attach_contract.backend_metadata = metadata
    finish = threading.Event()
    calls: list[str] = []
    workers: list[threading.Thread] = []
    claim = Mock(generation_id="generation", mode="web")

    def reserve(*, request_id: str, **_kwargs: object) -> object:
        """Record this operation as the only existing managed owner attempt."""

        claim.turn_dir = tmp_path / "manifest.turn-artifacts" / request_id
        return claim

    def submit(*, turn_id: str, control: object, **_kwargs: object) -> None:
        """Acknowledge Kimi accepting the competing input as queued."""

        workers.append(threading.current_thread())
        calls.append(turn_id)
        claim.turn_dir.mkdir(parents=True)
        (claim.turn_dir / "web-receipt.json").write_text(
            json.dumps(
                {
                    "operation_id": turn_id,
                    "identity": metadata.identity.model_dump(mode="json"),
                    "status": "queued",
                    "message_id": "msg_native-queue",
                }
            )
        )
        control.confirm_durable_handoff()
        assert finish.wait(2)

    monkeypatch.setattr(runtime, "_reserve_prompt", reserve)
    monkeypatch.setattr(adapter, "submit_scoped_web_prompt", submit)
    try:
        if entrypoint == "direct":
            result = runtime.control_prompt(GatewayPromptControlRequestV1(prompt="ordinary"))
            assert result.outcome == "queued" and result.sent is False
        elif entrypoint == "request":
            request = GatewayRequestCreateV1(
                kind="submit_prompt", payload={"prompt": "ordinary", "turn_id": "run-queue"}
            )
            result = runtime.create_request(request)
            assert result.native_admission == "queued"
            assert result.request_id == "run-queue" and result.queue_depth == 0
        else:
            result = runtime.dispatch_plugin_event(
                _event(),
                instance_id="owner",
                binding_id="bound",
                timeout_seconds=1,
                is_active=lambda: True,
            )
            assert result.native_admission == "queued"
        assert result.native_prompt_id == "msg_native-queue"
        assert len(calls) == 1
        assert queue_depth_from_sqlite(runtime.m_paths.queue_path) == 0
    finally:
        finish.set()
        for worker in workers:
            worker.join(timeout=2)


@pytest.mark.parametrize("outcome", ["completed", "failed", "interrupted", None])
def test_web_public_request_completion_uses_proven_native_terminal_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str | None
) -> None:
    """Admission success does not turn failed or missing native terminal evidence into success."""

    runtime, adapter, _ = _runtime(tmp_path, monkeypatch)
    adapter.m_agent_def_dir = tmp_path
    adapter.m_manifest_path = tmp_path / "manifest.json"
    backend = Mock()
    control = None
    finish = threading.Event()
    finished = threading.Event()

    def configure(selected: object) -> None:
        """Capture the actual adapter's request-scoped native control."""

        nonlocal control
        control = selected

    def send(*, turn_artifact_dir_name: str, **_kwargs: object) -> list[SessionEvent]:
        """Return native terminal evidence after independently confirming insertion."""

        assert control is not None
        control.confirm_handoff()
        assert finish.wait(2)
        if outcome is None:
            return []
        observed = runtime._refresh_status_snapshot(active_execution="idle").web
        assert observed is not None
        identity = observed.identity.model_dump(mode="json")
        artifact_dir = tmp_path / "manifest.turn-artifacts" / turn_artifact_dir_name
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "web-result.json").write_text(
            json.dumps(
                {
                    "operation_id": turn_artifact_dir_name,
                    "outcome": outcome,
                    "identity": identity,
                    "receipt": {
                        "operation_id": turn_artifact_dir_name,
                        "identity": identity,
                        "status": "terminal",
                        "turns": [1],
                    },
                }
            )
        )
        return [
            SessionEvent(
                kind="done", message="Native result", turn_index=1, payload={"outcome": outcome}
            )
        ]

    backend.configure_request_dispatch.side_effect = configure
    backend.close_control_connection.side_effect = finished.set
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.resume_runtime_session",
        lambda **_: SimpleNamespace(backend_session=backend, send_web_prompt=send),
    )
    accepted = runtime.create_request(
        GatewayRequestCreateV1(kind="submit_prompt", payload={"prompt": "admitted input"})
    )
    worker = runtime.m_direct_prompt_thread
    finish.set()
    assert finished.wait(2)
    if worker is not None:
        worker.join(timeout=2)
    with sqlite3.connect(runtime.m_paths.queue_path) as connection:
        state, durable_result = connection.execute(
            "SELECT state,result_json FROM gateway_requests WHERE request_id=?",
            (accepted.request_id,),
        ).fetchone()
    if outcome is None:
        assert state == "uncertain"
        assert json.loads(durable_result)["outcome"] == "uncertain"
    else:
        assert state == ("completed" if outcome == "completed" else "failed")
        assert json.loads(durable_result) == {
            "operation_id": accepted.request_id,
            "source": "web_native",
            "outcome": outcome,
            "native_session_id": "native",
            "native_turn_ids": ["1"],
            "identity": _metadata().identity.model_dump(mode="json"),
        }


def test_web_public_interrupt_is_immediate_and_never_becomes_later_cancellation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A control request completes now, without an executable gateway queue entry."""

    runtime, adapter, _ = _runtime(tmp_path, monkeypatch)
    status = runtime._refresh_status_snapshot(active_execution="idle")
    status.web.active_turn = GatewayWebActiveTurnV1(turn=3, start_sequence=19)
    interrupt = Mock()
    monkeypatch.setattr(adapter, "interrupt_captured", interrupt)
    result = runtime.create_request(GatewayRequestCreateV1(kind="interrupt", payload={}))
    interrupt.assert_called_once()
    assert interrupt.call_args.args[0].active_turn.start_sequence == 19
    assert result.queue_depth == 0
    with sqlite3.connect(runtime.m_paths.queue_path) as connection:
        state, payload = connection.execute(
            "SELECT state,payload_json FROM gateway_requests"
        ).fetchone()
    assert state == "completed" and "operation_id" in json.loads(payload)
    assert runtime.m_direct_prompt_thread is None


def test_web_mailbox_cycles_use_immediate_native_admission_and_metadata_only_storage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Periodic owner-bound reminders release their effect lease at native acknowledgement."""

    runtime, adapter, _ = _runtime(tmp_path, monkeypatch)
    delivered = Mock()
    workers = []
    held = threading.Event()
    release = threading.Event()

    @contextmanager
    def lease(_request_id: str):
        """Keep the captured origin admitted only through immediate handoff."""

        held.set()
        try:
            yield
        finally:
            held.clear()

    def submit(**kwargs: object) -> None:
        """Confirm native insertion while the immutable origin effect lease is held."""

        workers.append(threading.current_thread())
        assert held.is_set()
        delivered(**kwargs)
        kwargs["control"].confirm_handoff()
        assert release.wait(2)

    monkeypatch.setattr(runtime, "_mail_reminder_effect_lease", lease)
    monkeypatch.setattr(adapter, "submit_scoped_web_prompt", submit)
    for cycle in ("cycle-one", "cycle-two"):
        release.clear()
        try:
            with runtime.m_lock:
                request_id = runtime._enqueue_internal_prompt(
                    prompt="private mailbox reminder",
                    scope_key="owner/offline/binding",
                    cycle_key=cycle,
                    origin=ReminderOrigin("owner", "offline", "binding", "revision"),
                    execution_identity=("generation", "host", "body", "native"),
                )
            assert request_id is not None and not held.is_set()
            with sqlite3.connect(runtime.m_paths.queue_path) as connection:
                payload = connection.execute(
                    "SELECT payload_json FROM gateway_requests WHERE request_id=?", (request_id,)
                ).fetchone()[0]
            assert "private mailbox reminder" not in payload and "prompt" not in payload
        finally:
            release.set()
            workers[-1].join(timeout=2)
    assert delivered.call_count == 2
    assert all(
        call.kwargs["operator"] is False and call.kwargs["admission_policy"] == "ready_only"
        for call in delivered.call_args_list
    )
    with runtime.m_lock:
        assert (
            runtime._enqueue_internal_prompt(
                prompt="duplicate",
                scope_key="owner/offline/binding",
                cycle_key="cycle-two",
                origin=ReminderOrigin("owner", "offline", "binding", "revision"),
            )
            is None
        )
    assert delivered.call_count == 2
