from __future__ import annotations

import ast
import json
from pathlib import Path

from fastapi.testclient import TestClient
from fastapi.routing import APIRoute
from pydantic_core import PydanticUndefined

from houmao.agents.realm_controller.gateway_models import (
    GatewayControlInputRequestV1,
    GatewayControlInputResultV1,
    GatewayMailNotifierPutV1,
    GatewayMailNotifierStatusV1,
    GatewayReminderCreateBatchV1,
    GatewayReminderCreateResultV1,
    GatewayReminderDeleteResultV1,
    GatewayReminderListV1,
    GatewayReminderPutV1,
    GatewayReminderSendKeysV1,
    GatewayReminderV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayStatusV1,
    GatewayTuiTrackingTimingOverridesV1,
)
from houmao.server.app import create_app
from houmao.server.models import (
    HoumaoCurrentInstance,
    HoumaoHeadlessLaunchRequest,
    HoumaoHeadlessLaunchResponse,
    HoumaoHeadlessTurnAcceptedResponse,
    HoumaoHeadlessTurnEventsResponse,
    HoumaoHeadlessTurnRequest,
    HoumaoHeadlessTurnStatusResponse,
    HoumaoHealthResponse,
    HoumaoManagedAgentActionResponse,
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentGatewayAttachRequest,
    HoumaoManagedAgentGatewayPromptControlRequest,
    HoumaoManagedAgentGatewayPromptControlResponse,
    HoumaoManagedAgentGatewayRequestAcceptedResponse,
    HoumaoManagedAgentGatewayRequestCreate,
    HoumaoManagedAgentHistoryEntry,
    HoumaoManagedAgentHistoryResponse,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentLastTurnView,
    HoumaoManagedAgentListResponse,
    HoumaoManagedAgentMailActionResponse,
    HoumaoManagedAgentMailCheckRequest,
    HoumaoManagedAgentMailCheckResponse,
    HoumaoManagedAgentMailReplyRequest,
    HoumaoManagedAgentMailSendRequest,
    HoumaoManagedAgentMailStateRequest,
    HoumaoManagedAgentMailStateResponse,
    HoumaoManagedAgentMailStatusResponse,
    HoumaoManagedAgentRequestAcceptedResponse,
    HoumaoManagedAgentSubmitPromptRequest,
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentTurnView,
    HoumaoParsedSurface,
    HoumaoProbeSnapshot,
    HoumaoRecentTransition,
    HoumaoRegisterLaunchRequest,
    HoumaoRegisterLaunchResponse,
    HoumaoStabilityMetadata,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalSnapshotHistoryEntry,
    HoumaoTerminalSnapshotHistoryResponse,
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
        self.m_register_requests: list[HoumaoRegisterLaunchRequest] = []
        self.m_history_calls: list[tuple[str, int]] = []
        self.m_headless_launch_requests: list[HoumaoHeadlessLaunchRequest] = []
        self.m_managed_agent_history_calls: list[tuple[str, int]] = []
        self.m_managed_agent_request_calls: list[tuple[str, object]] = []
        self.m_stop_calls: list[str] = []
        self.m_turn_requests: list[tuple[str, HoumaoHeadlessTurnRequest]] = []
        self.m_turn_status_calls: list[tuple[str, str]] = []
        self.m_turn_events_calls: list[tuple[str, str]] = []
        self.m_turn_artifact_calls: list[tuple[str, str, str]] = []
        self.m_interrupt_calls: list[str] = []
        self.m_gateway_status_calls: list[str] = []
        self.m_gateway_attach_calls: list[
            tuple[str, HoumaoManagedAgentGatewayAttachRequest | None]
        ] = []
        self.m_gateway_detach_calls: list[str] = []
        self.m_gateway_tui_state_calls: list[str] = []
        self.m_gateway_tui_history_calls: list[tuple[str, int]] = []
        self.m_gateway_tui_note_prompt_calls: list[tuple[str, str]] = []
        self.m_gateway_prompt_control_calls: list[
            tuple[str, HoumaoManagedAgentGatewayPromptControlRequest]
        ] = []
        self.m_gateway_request_calls: list[tuple[str, HoumaoManagedAgentGatewayRequestCreate]] = []
        self.m_gateway_control_calls: list[tuple[str, GatewayControlInputRequestV1]] = []
        self.m_gateway_notifier_get_calls: list[str] = []
        self.m_gateway_notifier_put_calls: list[tuple[str, GatewayMailNotifierPutV1]] = []
        self.m_gateway_notifier_delete_calls: list[str] = []
        self.m_gateway_reminders_get_calls: list[str] = []
        self.m_gateway_reminders_create_calls: list[tuple[str, GatewayReminderCreateBatchV1]] = []
        self.m_gateway_reminder_get_calls: list[tuple[str, str]] = []
        self.m_gateway_reminder_put_calls: list[tuple[str, str, GatewayReminderPutV1]] = []
        self.m_gateway_reminder_delete_calls: list[tuple[str, str]] = []
        self.m_mail_status_calls: list[str] = []
        self.m_mail_check_calls: list[tuple[str, HoumaoManagedAgentMailCheckRequest]] = []
        self.m_mail_send_calls: list[tuple[str, HoumaoManagedAgentMailSendRequest]] = []
        self.m_mail_reply_calls: list[tuple[str, HoumaoManagedAgentMailReplyRequest]] = []
        self.m_mail_state_calls: list[tuple[str, HoumaoManagedAgentMailStateRequest]] = []

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
        )

    def current_instance_response(self) -> HoumaoCurrentInstance:
        return HoumaoCurrentInstance(
            pid=12345,
            api_base_url="http://127.0.0.1:9889",
            server_root="/tmp/houmao-server",
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
                tmux_session_name="HOUMAO-gpu",
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
            tmux_session_name="HOUMAO-gpu",
            manifest_path="/tmp/manifest.json",
            session_root="/tmp/session-root",
            agent_name="HOUMAO-gpu",
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

    def managed_agent_state_detail(self, agent_ref: str) -> HoumaoManagedAgentDetailResponse:
        summary_state = self.managed_agent_state(agent_ref)
        return HoumaoManagedAgentDetailResponse(
            tracked_agent_id=summary_state.tracked_agent_id,
            identity=summary_state.identity,
            summary_state=summary_state,
            detail={
                "transport": "headless",
                "runtime_resumable": True,
                "tmux_session_live": True,
                "can_accept_prompt_now": True,
                "interruptible": False,
                "turn": summary_state.turn,
                "last_turn": summary_state.last_turn,
                "active_turn_started_at_utc": None,
                "active_turn_interrupt_requested_at_utc": None,
                "last_turn_status": None,
                "last_turn_started_at_utc": None,
                "last_turn_completed_at_utc": None,
                "last_turn_completion_source": None,
                "last_turn_returncode": None,
                "last_turn_history_summary": None,
                "last_turn_error": None,
                "mailbox": None,
                "gateway": None,
                "diagnostics": [],
            },
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

    def submit_managed_agent_request(
        self,
        agent_ref: str,
        request_model: object,
    ) -> HoumaoManagedAgentRequestAcceptedResponse:
        self.m_managed_agent_request_calls.append((agent_ref, request_model))
        return HoumaoManagedAgentRequestAcceptedResponse(
            success=True,
            tracked_agent_id="claude-headless-1",
            request_id="mreq-123",
            request_kind="submit_prompt",
            disposition="accepted",
            detail="accepted",
            headless_turn_id="turn-123",
            headless_turn_index=1,
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
            completion_source="process_exit",
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

    def managed_agent_gateway_status(self, agent_ref: str) -> GatewayStatusV1:
        self.m_gateway_status_calls.append(agent_ref)
        return GatewayStatusV1(
            attach_identity="claude-headless-1",
            backend="claude_headless",
            tmux_session_name="HOUMAO-gpu",
            gateway_health="not_attached",
            managed_agent_connectivity="connected",
            managed_agent_recovery="idle",
            request_admission="open",
            terminal_surface_eligibility="ready",
            active_execution="idle",
            queue_depth=0,
            gateway_host=None,
            gateway_port=None,
            managed_agent_instance_epoch=1,
            managed_agent_instance_id="claude-headless-1",
        )

    def attach_managed_agent_gateway(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentGatewayAttachRequest | None = None,
    ) -> GatewayStatusV1:
        self.m_gateway_attach_calls.append((agent_ref, request_model))
        return self.managed_agent_gateway_status(agent_ref)

    def detach_managed_agent_gateway(self, agent_ref: str) -> GatewayStatusV1:
        self.m_gateway_detach_calls.append(agent_ref)
        return self.managed_agent_gateway_status(agent_ref)

    def get_managed_agent_gateway_tui_state(self, agent_ref: str) -> HoumaoTerminalStateResponse:
        self.m_gateway_tui_state_calls.append(agent_ref)
        return self.terminal_state("headless123")

    def get_managed_agent_gateway_tui_history(
        self,
        agent_ref: str,
        *,
        limit: int = 100,
    ) -> HoumaoTerminalSnapshotHistoryResponse:
        self.m_gateway_tui_history_calls.append((agent_ref, limit))
        state = self.terminal_state("headless123")
        return HoumaoTerminalSnapshotHistoryResponse(
            terminal_id=state.terminal_id,
            tracked_session_id=state.tracked_session.tracked_session_id,
            entries=[
                HoumaoTerminalSnapshotHistoryEntry(
                    recorded_at_utc="2026-03-19T10:00:00+00:00",
                    diagnostics=state.diagnostics,
                    probe_snapshot=state.probe_snapshot,
                    parsed_surface=state.parsed_surface,
                    surface=state.surface,
                    turn=state.turn,
                    last_turn=state.last_turn,
                    stability=state.stability.model_copy(update={"signature": f"history-{limit}"}),
                )
            ],
        )

    def note_managed_agent_gateway_tui_prompt(
        self,
        agent_ref: str,
        *,
        prompt: str,
    ) -> HoumaoTerminalStateResponse:
        self.m_gateway_tui_note_prompt_calls.append((agent_ref, prompt))
        return self.terminal_state("headless123")

    def submit_managed_agent_gateway_request(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentGatewayRequestCreate,
    ) -> HoumaoManagedAgentGatewayRequestAcceptedResponse:
        self.m_gateway_request_calls.append((agent_ref, request_model))
        return HoumaoManagedAgentGatewayRequestAcceptedResponse(
            request_id="greq-123",
            request_kind=request_model.kind,
            state="accepted",
            accepted_at_utc="2026-03-24T16:00:00+00:00",
            queue_depth=1,
            managed_agent_instance_epoch=2,
        )

    def control_managed_agent_gateway_prompt(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentGatewayPromptControlRequest,
    ) -> HoumaoManagedAgentGatewayPromptControlResponse:
        self.m_gateway_prompt_control_calls.append((agent_ref, request_model))
        return HoumaoManagedAgentGatewayPromptControlResponse(
            sent=True,
            forced=request_model.force,
            detail="Prompt dispatched.",
        )

    def send_managed_agent_gateway_control_input(
        self,
        agent_ref: str,
        request_model: GatewayControlInputRequestV1,
    ) -> GatewayControlInputResultV1:
        self.m_gateway_control_calls.append((agent_ref, request_model))
        return GatewayControlInputResultV1(detail="control input delivered")

    def get_managed_agent_gateway_mail_notifier(
        self,
        agent_ref: str,
    ) -> GatewayMailNotifierStatusV1:
        self.m_gateway_notifier_get_calls.append(agent_ref)
        return GatewayMailNotifierStatusV1(
            enabled=False,
            interval_seconds=None,
            supported=True,
            support_error=None,
            last_poll_at_utc=None,
            last_notification_at_utc=None,
            last_error=None,
        )

    def put_managed_agent_gateway_mail_notifier(
        self,
        agent_ref: str,
        request_model: GatewayMailNotifierPutV1,
    ) -> GatewayMailNotifierStatusV1:
        self.m_gateway_notifier_put_calls.append((agent_ref, request_model))
        return GatewayMailNotifierStatusV1(
            enabled=True,
            interval_seconds=request_model.interval_seconds,
            supported=True,
            support_error=None,
            last_poll_at_utc=None,
            last_notification_at_utc=None,
            last_error=None,
        )

    def delete_managed_agent_gateway_mail_notifier(
        self,
        agent_ref: str,
    ) -> GatewayMailNotifierStatusV1:
        self.m_gateway_notifier_delete_calls.append(agent_ref)
        return GatewayMailNotifierStatusV1(
            enabled=False,
            interval_seconds=None,
            supported=True,
            support_error=None,
            last_poll_at_utc=None,
            last_notification_at_utc=None,
            last_error=None,
        )

    def list_managed_agent_gateway_reminders(
        self,
        agent_ref: str,
    ) -> GatewayReminderListV1:
        self.m_gateway_reminders_get_calls.append(agent_ref)
        reminder = GatewayReminderV1(
            reminder_id="greminder-1",
            mode="one_off",
            delivery_kind="prompt",
            title="Check inbox",
            prompt="Review the inbox now.",
            ranking=0,
            paused=False,
            selection_state="effective",
            delivery_state="scheduled",
            created_at_utc="2026-04-09T00:00:00+00:00",
            next_due_at_utc="2026-04-09T00:05:00+00:00",
        )
        return GatewayReminderListV1(
            effective_reminder_id=reminder.reminder_id,
            reminders=[reminder],
        )

    def create_managed_agent_gateway_reminders(
        self,
        agent_ref: str,
        request_model: GatewayReminderCreateBatchV1,
    ) -> GatewayReminderCreateResultV1:
        self.m_gateway_reminders_create_calls.append((agent_ref, request_model))
        return self.list_managed_agent_gateway_reminders(agent_ref)

    def get_managed_agent_gateway_reminder(
        self,
        agent_ref: str,
        reminder_id: str,
    ) -> GatewayReminderV1:
        self.m_gateway_reminder_get_calls.append((agent_ref, reminder_id))
        return GatewayReminderV1(
            reminder_id=reminder_id,
            mode="one_off",
            delivery_kind="prompt",
            title="Check inbox",
            prompt="Review the inbox now.",
            ranking=0,
            paused=False,
            selection_state="effective",
            delivery_state="scheduled",
            created_at_utc="2026-04-09T00:00:00+00:00",
            next_due_at_utc="2026-04-09T00:05:00+00:00",
        )

    def put_managed_agent_gateway_reminder(
        self,
        agent_ref: str,
        reminder_id: str,
        request_model: GatewayReminderPutV1,
    ) -> GatewayReminderV1:
        self.m_gateway_reminder_put_calls.append((agent_ref, reminder_id, request_model))
        return GatewayReminderV1(
            reminder_id=reminder_id,
            mode=request_model.mode,
            delivery_kind="send_keys" if request_model.send_keys is not None else "prompt",
            title=request_model.title,
            prompt=request_model.prompt,
            send_keys=request_model.send_keys,
            ranking=request_model.ranking,
            paused=request_model.paused,
            selection_state="effective",
            delivery_state="scheduled",
            created_at_utc="2026-04-09T00:00:00+00:00",
            next_due_at_utc="2026-04-09T00:05:00+00:00",
            interval_seconds=request_model.interval_seconds,
        )

    def delete_managed_agent_gateway_reminder(
        self,
        agent_ref: str,
        reminder_id: str,
    ) -> GatewayReminderDeleteResultV1:
        self.m_gateway_reminder_delete_calls.append((agent_ref, reminder_id))
        return GatewayReminderDeleteResultV1(reminder_id=reminder_id, detail="deleted")

    def managed_agent_mail_status(self, agent_ref: str) -> HoumaoManagedAgentMailStatusResponse:
        self.m_mail_status_calls.append(agent_ref)
        return HoumaoManagedAgentMailStatusResponse(
            transport="filesystem",
            principal_id="agent-1234",
            address="agent@agents.localhost",
            bindings_version="v1",
        )

    def check_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailCheckRequest,
    ) -> HoumaoManagedAgentMailCheckResponse:
        self.m_mail_check_calls.append((agent_ref, request_model))
        return HoumaoManagedAgentMailCheckResponse(
            transport="filesystem",
            principal_id="agent-1234",
            address="agent@agents.localhost",
            unread_only=request_model.unread_only,
            message_count=0,
            unread_count=0,
            messages=[],
        )

    def send_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailSendRequest,
    ) -> HoumaoManagedAgentMailActionResponse:
        self.m_mail_send_calls.append((agent_ref, request_model))
        return HoumaoManagedAgentMailActionResponse(
            operation="send",
            transport="filesystem",
            principal_id="agent-1234",
            address="agent@agents.localhost",
            message={
                "message_ref": "msg-123",
                "thread_ref": "thread-1",
                "created_at_utc": "2026-03-24T16:00:00+00:00",
                "subject": request_model.subject,
                "unread": False,
                "body_preview": request_model.body_content,
                "body_text": request_model.body_content,
                "sender": {"address": "agent@agents.localhost"},
                "to": [{"address": request_model.to[0]}],
                "cc": [],
                "reply_to": [],
                "attachments": [],
            },
        )

    def reply_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailReplyRequest,
    ) -> HoumaoManagedAgentMailActionResponse:
        self.m_mail_reply_calls.append((agent_ref, request_model))
        return HoumaoManagedAgentMailActionResponse(
            operation="reply",
            transport="filesystem",
            principal_id="agent-1234",
            address="agent@agents.localhost",
            message={
                "message_ref": request_model.message_ref,
                "thread_ref": "thread-1",
                "created_at_utc": "2026-03-24T16:00:00+00:00",
                "subject": "reply",
                "unread": False,
                "body_preview": request_model.body_content,
                "body_text": request_model.body_content,
                "sender": {"address": "agent@agents.localhost"},
                "to": [{"address": "peer@agents.localhost"}],
                "cc": [],
                "reply_to": [],
                "attachments": [],
            },
        )

    def update_managed_agent_mail_state(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailStateRequest,
    ) -> HoumaoManagedAgentMailStateResponse:
        self.m_mail_state_calls.append((agent_ref, request_model))
        return HoumaoManagedAgentMailStateResponse(
            transport="filesystem",
            principal_id="agent-1234",
            address="agent@agents.localhost",
            message_ref=request_model.message_ref,
            read=request_model.read,
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
        agent_name="HOUMAO-gpu",
    )
    state_response = state_route.endpoint(terminal_id="abcd1234")
    history_response = history_route.endpoint(terminal_id="abcd1234", limit=3)

    assert health_response.houmao_service == "houmao-server"
    assert health_response.child_cao is None
    assert current_instance_response.api_base_url == "http://127.0.0.1:9889"
    assert current_instance_response.child_cao is None

    assert register_response.success is True
    assert service.m_register_requests[0].session_name == "cao-gpu"
    assert service.m_register_requests[0].tool == "codex"
    assert service.m_register_requests[0].agent_name == "HOUMAO-gpu"
    assert state_response.terminal_id == "abcd1234"
    assert history_response.entries[0].summary == "limit=3"
    assert service.m_history_calls == [("abcd1234", 3)]


def test_houmao_extension_routes_omit_child_metadata_when_service_returns_none() -> None:
    """Wire responses should omit null child metadata for no-child mode."""

    class _NoChildServiceDouble(_AppServiceDouble):
        def health_response(self) -> HoumaoHealthResponse:
            return HoumaoHealthResponse(
                status="ok",
                service="cli-agent-orchestrator",
                child_cao=None,
            )

        def current_instance_response(self) -> HoumaoCurrentInstance:
            return HoumaoCurrentInstance(
                pid=12345,
                api_base_url="http://127.0.0.1:9889",
                server_root="/tmp/houmao-server",
                child_cao=None,
            )

    with TestClient(create_app(service=_NoChildServiceDouble())) as client:
        health_response = client.get("/health")
        current_instance_response = client.get("/houmao/server/current-instance")

    assert health_response.status_code == 200
    assert health_response.json() == {
        "status": "ok",
        "service": "cli-agent-orchestrator",
        "houmao_service": "houmao-server",
    }
    assert current_instance_response.status_code == 200
    assert current_instance_response.json() == {
        "schema_version": 1,
        "status": "ok",
        "pid": 12345,
        "api_base_url": "http://127.0.0.1:9889",
        "server_root": "/tmp/houmao-server",
        "started_at_utc": current_instance_response.json()["started_at_utc"],
    }


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
    detail_route = _route("/houmao/agents/{agent_ref}/state/detail", "GET", app=app)
    history_route = _route("/houmao/agents/{agent_ref}/history", "GET", app=app)
    request_route = _route("/houmao/agents/{agent_ref}/requests", "POST", app=app)
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
    gateway_status_route = _route("/houmao/agents/{agent_ref}/gateway", "GET", app=app)
    gateway_attach_route = _route("/houmao/agents/{agent_ref}/gateway/attach", "POST", app=app)
    gateway_detach_route = _route("/houmao/agents/{agent_ref}/gateway/detach", "POST", app=app)
    gateway_tui_state_route = _route(
        "/houmao/agents/{agent_ref}/gateway/tui/state",
        "GET",
        app=app,
    )
    gateway_tui_history_route = _route(
        "/houmao/agents/{agent_ref}/gateway/tui/history",
        "GET",
        app=app,
    )
    gateway_tui_note_prompt_route = _route(
        "/houmao/agents/{agent_ref}/gateway/tui/note-prompt",
        "POST",
        app=app,
    )
    gateway_request_route = _route(
        "/houmao/agents/{agent_ref}/gateway/requests",
        "POST",
        app=app,
    )
    gateway_prompt_control_route = _route(
        "/houmao/agents/{agent_ref}/gateway/control/prompt",
        "POST",
        app=app,
    )
    gateway_control_route = _route(
        "/houmao/agents/{agent_ref}/gateway/control/send-keys",
        "POST",
        app=app,
    )
    gateway_notifier_get_route = _route(
        "/houmao/agents/{agent_ref}/gateway/mail-notifier",
        "GET",
        app=app,
    )
    gateway_notifier_put_route = _route(
        "/houmao/agents/{agent_ref}/gateway/mail-notifier",
        "PUT",
        app=app,
    )
    gateway_notifier_delete_route = _route(
        "/houmao/agents/{agent_ref}/gateway/mail-notifier",
        "DELETE",
        app=app,
    )
    gateway_reminders_list_route = _route(
        "/houmao/agents/{agent_ref}/gateway/reminders",
        "GET",
        app=app,
    )
    gateway_reminders_create_route = _route(
        "/houmao/agents/{agent_ref}/gateway/reminders",
        "POST",
        app=app,
    )
    gateway_reminder_get_route = _route(
        "/houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}",
        "GET",
        app=app,
    )
    gateway_reminder_put_route = _route(
        "/houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}",
        "PUT",
        app=app,
    )
    gateway_reminder_delete_route = _route(
        "/houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}",
        "DELETE",
        app=app,
    )
    mail_status_route = _route("/houmao/agents/{agent_ref}/mail/status", "GET", app=app)
    mail_check_route = _route("/houmao/agents/{agent_ref}/mail/check", "POST", app=app)
    mail_send_route = _route("/houmao/agents/{agent_ref}/mail/send", "POST", app=app)
    mail_reply_route = _route("/houmao/agents/{agent_ref}/mail/reply", "POST", app=app)
    mail_state_route = _route("/houmao/agents/{agent_ref}/mail/state", "POST", app=app)

    assert list_route.endpoint().agents[0].tracked_agent_id == "claude-headless-1"
    assert get_route.endpoint(agent_ref="claude-headless-1").transport == "headless"
    assert state_route.endpoint(agent_ref="claude-headless-1").availability == "available"
    assert detail_route.endpoint(agent_ref="claude-headless-1").detail.transport == "headless"
    assert (
        history_route.endpoint(agent_ref="claude-headless-1", limit=5).entries[0].summary
        == "managed-limit=5"
    )
    request_response = request_route.endpoint(
        agent_ref="claude-headless-1",
        request_model=HoumaoManagedAgentSubmitPromptRequest(prompt="hello"),
    )
    assert request_response.request_id == "mreq-123"

    launch_response = launch_route.endpoint(
        request_model=HoumaoHeadlessLaunchRequest(
            tool="claude",
            working_directory="/tmp/work",
            agent_def_dir="/tmp/agents",
            brain_manifest_path="/tmp/brain.yaml",
            role_name="gpu-kernel-coder",
            agent_name="HOUMAO-gpu",
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
    assert (
        turn_status_route.endpoint(agent_ref="claude-headless-1", turn_id="turn-123").status
        == "completed"
    )
    assert (
        turn_events_route.endpoint(agent_ref="claude-headless-1", turn_id="turn-123").entries == []
    )
    assert (
        stdout_route.endpoint(agent_ref="claude-headless-1", turn_id="turn-123").body
        == b"stdout:turn-123"
    )
    assert (
        stderr_route.endpoint(agent_ref="claude-headless-1", turn_id="turn-123").body
        == b"stderr:turn-123"
    )
    assert interrupt_route.endpoint(agent_ref="claude-headless-1").detail == "interrupted"
    assert (
        gateway_status_route.endpoint(agent_ref="claude-headless-1").gateway_health
        == "not_attached"
    )
    assert (
        gateway_attach_route.endpoint(
            agent_ref="claude-headless-1",
            request_model=HoumaoManagedAgentGatewayAttachRequest(
                execution_mode="detached_process",
                tui_tracking_timings=GatewayTuiTrackingTimingOverridesV1(
                    stale_active_recovery_seconds=6.0,
                    final_stable_active_recovery_seconds=18.0,
                ),
            ),
        ).request_admission
        == "open"
    )
    assert gateway_detach_route.endpoint(agent_ref="claude-headless-1").request_admission == "open"
    assert (
        gateway_tui_state_route.endpoint(agent_ref="claude-headless-1").terminal_id == "headless123"
    )
    gateway_tui_history = gateway_tui_history_route.endpoint(
        agent_ref="claude-headless-1",
        limit=7,
    )
    assert gateway_tui_history.entries[0].stability.signature == "history-7"
    assert (
        gateway_tui_note_prompt_route.endpoint(
            agent_ref="claude-headless-1",
            request_model=GatewayRequestPayloadSubmitPromptV1(prompt="hello"),
        ).terminal_id
        == "headless123"
    )
    gateway_request_response = gateway_request_route.endpoint(
        agent_ref="claude-headless-1",
        request_model=HoumaoManagedAgentGatewayRequestCreate(
            kind="submit_prompt",
            payload=GatewayRequestPayloadSubmitPromptV1(prompt="hello"),
        ),
    )
    assert gateway_request_response.request_id == "greq-123"
    gateway_prompt_control_response = gateway_prompt_control_route.endpoint(
        agent_ref="claude-headless-1",
        request_model=HoumaoManagedAgentGatewayPromptControlRequest(prompt="hello", force=True),
    )
    assert gateway_prompt_control_response.sent is True
    assert gateway_prompt_control_response.forced is True
    gateway_control_response = gateway_control_route.endpoint(
        agent_ref="claude-headless-1",
        request_model=GatewayControlInputRequestV1(sequence="<[Escape]>"),
    )
    assert gateway_control_response.action == "control_input"
    notifier_status = gateway_notifier_get_route.endpoint(agent_ref="claude-headless-1")
    assert notifier_status.enabled is False
    notifier_enabled = gateway_notifier_put_route.endpoint(
        agent_ref="claude-headless-1",
        request_model=GatewayMailNotifierPutV1(interval_seconds=60),
    )
    assert notifier_enabled.enabled is True
    assert gateway_notifier_delete_route.endpoint(agent_ref="claude-headless-1").enabled is False
    assert (
        gateway_reminders_list_route.endpoint(agent_ref="claude-headless-1").effective_reminder_id
        == "greminder-1"
    )
    assert (
        gateway_reminders_create_route.endpoint(
            agent_ref="claude-headless-1",
            request_model=GatewayReminderCreateBatchV1(
                reminders=[
                    {
                        "mode": "one_off",
                        "title": "Check inbox",
                        "prompt": "Review the inbox now.",
                        "ranking": 0,
                        "start_after_seconds": 60,
                    }
                ]
            ),
        ).effective_reminder_id
        == "greminder-1"
    )
    assert (
        gateway_reminder_get_route.endpoint(
            agent_ref="claude-headless-1",
            reminder_id="greminder-1",
        ).reminder_id
        == "greminder-1"
    )
    assert (
        gateway_reminder_put_route.endpoint(
            agent_ref="claude-headless-1",
            reminder_id="greminder-1",
            request_model=GatewayReminderPutV1(
                mode="one_off",
                title="Check inbox later",
                send_keys=GatewayReminderSendKeysV1(
                    sequence="<[Escape]>",
                    ensure_enter=False,
                ),
                ranking=-1,
                deliver_at_utc="2026-04-09T12:00:00+00:00",
            ),
        ).ranking
        == -1
    )
    assert (
        gateway_reminder_delete_route.endpoint(
            agent_ref="claude-headless-1",
            reminder_id="greminder-1",
        ).deleted
        is True
    )
    assert mail_status_route.endpoint(agent_ref="claude-headless-1").principal_id == "agent-1234"
    mail_check_response = mail_check_route.endpoint(
        agent_ref="claude-headless-1",
        request_model=HoumaoManagedAgentMailCheckRequest(unread_only=True, limit=5),
    )
    assert mail_check_response.unread_only is True
    mail_send_response = mail_send_route.endpoint(
        agent_ref="claude-headless-1",
        request_model=HoumaoManagedAgentMailSendRequest(
            to=["peer@agents.localhost"],
            subject="status",
            body_content="hello",
        ),
    )
    assert mail_send_response.operation == "send"
    mail_reply_response = mail_reply_route.endpoint(
        agent_ref="claude-headless-1",
        request_model=HoumaoManagedAgentMailReplyRequest(
            message_ref="msg-123",
            body_content="reply",
        ),
    )
    assert mail_reply_response.operation == "reply"
    mail_state_response = mail_state_route.endpoint(
        agent_ref="claude-headless-1",
        request_model=HoumaoManagedAgentMailStateRequest(
            message_ref="filesystem:msg-123",
            read=True,
        ),
    )
    assert mail_state_response.read is True
    assert len(service.m_gateway_control_calls) == 1
    assert len(service.m_gateway_prompt_control_calls) == 1
    assert service.m_gateway_prompt_control_calls[0][0] == "claude-headless-1"
    assert service.m_gateway_prompt_control_calls[0][1].prompt == "hello"
    assert service.m_gateway_control_calls[0][0] == "claude-headless-1"
    assert service.m_gateway_control_calls[0][1].sequence == "<[Escape]>"
    assert service.m_gateway_attach_calls == [
        (
            "claude-headless-1",
            HoumaoManagedAgentGatewayAttachRequest(
                execution_mode="detached_process",
                tui_tracking_timings=GatewayTuiTrackingTimingOverridesV1(
                    stale_active_recovery_seconds=6.0,
                    final_stable_active_recovery_seconds=18.0,
                ),
            ),
        )
    ]
    assert service.m_gateway_tui_state_calls == ["claude-headless-1"]
    assert service.m_gateway_tui_history_calls == [("claude-headless-1", 7)]
    assert service.m_gateway_tui_note_prompt_calls == [("claude-headless-1", "hello")]
    assert service.m_mail_state_calls == [
        (
            "claude-headless-1",
            HoumaoManagedAgentMailStateRequest(
                message_ref="filesystem:msg-123",
                read=True,
            ),
        )
    ]
