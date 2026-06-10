from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from houmao.ag_ui.capabilities import build_ag_ui_capabilities
from houmao.ag_ui.connection import AgUiConnectionRecord
from houmao.ag_ui.state import build_houmao_state_snapshot
from houmao.agents.realm_controller.gateway_models import GatewayStatusV1


def _status(**overrides: object) -> GatewayStatusV1:
    """Return one healthy gateway status sample."""

    values: dict[str, object] = {
        "attach_identity": "agent-1",
        "backend": "local_interactive",
        "tmux_session_name": "tmux-agent-1",
        "gateway_health": "healthy",
        "managed_agent_connectivity": "connected",
        "managed_agent_recovery": "idle",
        "request_admission": "open",
        "terminal_surface_eligibility": "ready",
        "active_execution": "idle",
        "execution_mode": "detached_process",
        "queue_depth": 0,
        "gateway_host": "127.0.0.1",
        "gateway_port": 43123,
        "managed_agent_instance_epoch": 1,
        "managed_agent_instance_id": "instance-1",
    }
    values.update(overrides)
    return GatewayStatusV1.model_validate(values)


@dataclass
class _Runtime:
    """Small runtime fake that exposes gateway status only."""

    status_payload: object

    def status(self) -> object:
        """Return the configured fake status."""

        return self.status_payload


def test_capabilities_are_conservative_and_state_lifecycle_boundary() -> None:
    response = build_ag_ui_capabilities(_Runtime(_status()))
    dumped = response.model_dump(mode="json", by_alias=True)

    capabilities = dumped["capabilities"]
    assert capabilities["transport"]["streaming"] is True
    assert capabilities["transport"]["websocket"] is False
    assert capabilities["transport"]["httpBinary"] is False
    assert capabilities["transport"]["resumable"] is True
    assert capabilities["state"]["snapshots"] is True
    assert capabilities["state"]["deltas"] is False
    assert capabilities["tools"]["supported"] is False
    assert capabilities["tools"]["clientProvided"] is False
    assert capabilities["multimodal"]["input"]["image"] is False
    assert capabilities["multimodal"]["input"]["file"] is False
    assert capabilities["multimodal"]["output"]["image"] is False
    assert capabilities["custom"]["houmao"]["replaySupport"] == "event_log_since_cursor"

    houmao = dumped["houmao"]
    assert houmao["features"]["httpSse"] is True
    assert houmao["features"]["guiConnect"] is True
    assert houmao["features"]["textInputParsing"] is True
    assert houmao["features"]["stateSnapshots"] is True
    assert houmao["features"]["taskRunSubmission"] is True
    assert houmao["features"]["stateDeltas"] is False
    assert houmao["features"]["frontendToolExecution"] is False
    assert houmao["features"]["generatedGraphics"] is False
    assert houmao["features"]["openGenerativeUi"] is False
    assert houmao["features"]["multimodalInput"] is False
    assert houmao["agentLifecycleManagedByGui"] is False
    assert (
        "does not start, stop, restart, abort, interrupt, or shut down"
        in houmao["lifecycleBoundary"]
    )
    assert houmao["replaySupport"] == "event_log_since_cursor"


def test_capabilities_can_report_snapshot_only_when_replay_is_disabled() -> None:
    response = build_ag_ui_capabilities(_Runtime(_status()), replay_enabled=False)
    dumped = response.model_dump(mode="json", by_alias=True)

    assert dumped["capabilities"]["transport"]["resumable"] is False
    assert dumped["capabilities"]["custom"]["houmao"]["replaySupport"] == "current_snapshot_only"
    assert dumped["houmao"]["replaySupport"] == "current_snapshot_only"


def test_capabilities_report_headless_graphics_tool_metadata() -> None:
    response = build_ag_ui_capabilities(_Runtime(_status(backend="codex_headless")))
    dumped = response.model_dump(mode="json", by_alias=True)

    assert dumped["houmao"]["features"]["taskRunSubmission"] is True
    assert dumped["houmao"]["features"]["generatedGraphics"] is True
    assert dumped["houmao"]["gateway"]["graphicsToolName"] == "houmao_render_graphic"
    assert dumped["capabilities"]["tools"]["supported"] is True
    assert dumped["capabilities"]["tools"]["items"][0]["name"] == "houmao_render_graphic"
    assert dumped["capabilities"]["tools"]["clientProvided"] is False
    assert dumped["capabilities"]["custom"]["houmao"]["graphics"]["toolName"] == (
        "houmao_render_graphic"
    )


def test_state_snapshot_includes_connection_and_compact_gateway_status() -> None:
    connection = AgUiConnectionRecord(
        connection_id="agui-1",
        thread_id="thread-1",
        run_id="run-1",
        parent_run_id="run-parent",
        last_seen_event_id="event-9",
        created_at_utc=datetime(2026, 6, 8, 1, 2, 3, tzinfo=UTC),
    )

    snapshot = build_houmao_state_snapshot(status=_status(queue_depth=3), connection=connection)
    houmao = snapshot["houmao"]
    assert isinstance(houmao, dict)
    assert houmao["connection"] == {
        "connectionId": "agui-1",
        "threadId": "thread-1",
        "runId": "run-1",
        "createdAtUtc": "2026-06-08T01:02:03Z",
        "detached": False,
        "parentRunId": "run-parent",
        "lastSeenEventId": "event-9",
    }
    assert houmao["gateway"]["availability"] == "healthy"
    assert houmao["gateway"]["managedAgentConnectivity"] == "connected"
    assert houmao["gateway"]["targetTransportFamily"] == "tmux"
    assert houmao["activeExecution"] == {
        "state": "idle",
        "queueDepth": 3,
        "requestAdmission": "open",
    }


class _SensitiveStatus:
    """Status-like object with extra sensitive fields the sanitizer must ignore."""

    attach_identity = "agent-1"
    backend = "cao_rest"
    tmux_session_name = "tmux-agent-1"
    gateway_health = "healthy"
    managed_agent_connectivity = "connected"
    managed_agent_recovery = "idle"
    request_admission = "open"
    terminal_surface_eligibility = "ready"
    active_execution = "running"
    execution_mode = "detached_process"
    queue_depth = 1
    gateway_host = "127.0.0.1"
    gateway_port = 43123
    gateway_tmux_window_id = None
    gateway_tmux_window_index = None
    gateway_tmux_pane_id = None
    managed_agent_instance_epoch = 2
    managed_agent_instance_id = "term-1"
    mailbox_message_content = "mailbox body secret"
    memory_page_content = "memory page secret"
    raw_terminal_history = "terminal scrollback secret"
    credentials = {"authorization": "Bearer secret-token", "cookies": "session=secret"}
    raw_prompt_text = "raw prompt secret"
    forwarded_props = {"authorization": "Bearer unmanaged-secret"}


def test_state_snapshot_omits_sensitive_runtime_state() -> None:
    connection = AgUiConnectionRecord(
        connection_id="agui-1",
        thread_id="thread-1",
        run_id="run-1",
        created_at_utc=datetime(2026, 6, 8, tzinfo=UTC),
    )

    snapshot = build_houmao_state_snapshot(status=_SensitiveStatus(), connection=connection)
    rendered = json.dumps(snapshot, sort_keys=True)

    assert "mailbox body secret" not in rendered
    assert "memory page secret" not in rendered
    assert "terminal scrollback secret" not in rendered
    assert "secret-token" not in rendered
    assert "cookies" not in rendered
    assert "raw prompt secret" not in rendered
    assert "unmanaged-secret" not in rendered
    assert snapshot["houmao"]["gateway"]["targetTransportFamily"] == "http_rest"
