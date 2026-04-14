from __future__ import annotations

import pytest

from houmao.agents.realm_controller.gateway_models import (
    GatewayControlInputRequestV1,
    GatewayMailNotifierPutV1,
    GatewayMailNotifierStatusV1,
    GatewayReminderCreateBatchV1,
    GatewayReminderDefinitionV1,
    GatewayReminderPutV1,
    GatewayReminderSendKeysV1,
    GatewayRequestPayloadSubmitPromptV1,
)
from houmao.passive_server.client import PassiveServerClient
from houmao.passive_server.models import (
    PassiveHeadlessLaunchRequest,
    PassiveHeadlessLaunchResponse,
    PassiveHeadlessTurnRequest,
)
from houmao.mailbox.protocol import HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE
from houmao.server.client import HoumaoServerClient
from houmao.server.pair_client import (
    UnsupportedPairAuthorityError,
    resolve_pair_authority_client,
)
from houmao.server.models import (
    HoumaoHeadlessLaunchRequest,
    HoumaoHeadlessLaunchResponse,
    HoumaoHeadlessTurnAcceptedResponse,
    HoumaoHeadlessTurnRequest,
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentGatewayPromptControlRequest,
    HoumaoManagedAgentGatewayPromptControlResponse,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentGatewayRequestAcceptedResponse,
    HoumaoManagedAgentGatewayRequestCreate,
    HoumaoManagedAgentMailActionResponse,
    HoumaoManagedAgentMailArchiveRequest,
    HoumaoManagedAgentMailLifecycleResponse,
    HoumaoManagedAgentMailListRequest,
    HoumaoManagedAgentMailListResponse,
    HoumaoManagedAgentMailMarkRequest,
    HoumaoManagedAgentMailPostRequest,
    HoumaoManagedAgentMailReplyRequest,
    HoumaoManagedAgentMailSendRequest,
    HoumaoManagedAgentMailStatusResponse,
    HoumaoManagedAgentRequestAcceptedResponse,
    HoumaoManagedAgentSubmitPromptRequest,
    HoumaoManagedAgentStateResponse,
    HoumaoRegisterLaunchRequest,
    HoumaoRegisterLaunchResponse,
    HoumaoTerminalSnapshotHistoryResponse,
    HoumaoTerminalStateResponse,
)


def test_houmao_server_client_defaults_to_split_compatibility_timeout_budgets() -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")

    assert client.base_url == "http://127.0.0.1:9889"
    assert client.path_prefix == "/cao"
    assert client.timeout_seconds == 15.0
    assert client.create_timeout_seconds == 75.0


def test_terminal_state_parses_simplified_tracked_state_contract(monkeypatch) -> None:
    payload = {
        "terminal_id": "abcd1234",
        "tracked_session": {
            "tracked_session_id": "cao-gpu",
            "session_name": "cao-gpu",
            "tool": "codex",
            "tmux_session_name": "HOUMAO-gpu",
            "terminal_aliases": ["abcd1234"],
        },
        "diagnostics": {
            "availability": "available",
            "transport_state": "tmux_up",
            "process_state": "tui_up",
            "parse_status": "parsed",
            "probe_error": None,
            "parse_error": None,
        },
        "probe_snapshot": None,
        "parsed_surface": {
            "parser_family": "codex_shadow",
            "parser_preset_id": "codex",
            "parser_preset_version": "1.0.0",
            "availability": "supported",
            "business_state": "idle",
            "input_mode": "freeform",
            "ui_context": "normal_prompt",
            "normalized_projection_text": "ready prompt",
            "dialog_text": "ready prompt",
            "dialog_head": "ready prompt",
            "dialog_tail": "ready prompt",
            "anomaly_codes": [],
            "baseline_invalidated": False,
            "operator_blocked_excerpt": None,
        },
        "surface": {
            "accepting_input": "yes",
            "editing_input": "no",
            "ready_posture": "yes",
        },
        "turn": {"phase": "ready"},
        "last_turn": {
            "result": "none",
            "source": "none",
            "updated_at_utc": None,
        },
        "stability": {
            "signature": "deadbeef",
            "stable": True,
            "stable_for_seconds": 3.0,
            "stable_since_utc": "2026-03-19T09:59:57+00:00",
        },
        "recent_transitions": [],
    }
    client = HoumaoServerClient("http://127.0.0.1:9889")

    def _request_root_model(
        method: str,
        path: str,
        model: type[HoumaoTerminalStateResponse],
        **kwargs,
    ):
        del method, path, kwargs
        return model.model_validate(payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    state = client.terminal_state("abcd1234")

    assert state.diagnostics.availability == "available"
    assert state.surface.ready_posture == "yes"
    assert state.turn.phase == "ready"
    assert state.last_turn.result == "none"


def test_launch_headless_agent_posts_resolved_json_body(monkeypatch) -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")
    request_model = HoumaoHeadlessLaunchRequest(
        tool="claude",
        working_directory="/tmp/work",
        agent_def_dir="/tmp/agents",
        brain_manifest_path="/tmp/brain.yaml",
        role_name="gpu-kernel-coder",
        agent_name="HOUMAO-gpu",
        agent_id=None,
    )
    recorded: dict[str, object] = {}
    response_payload = {
        "success": True,
        "tracked_agent_id": "claude-headless-1",
        "identity": {
            "tracked_agent_id": "claude-headless-1",
            "transport": "headless",
            "tool": "claude",
            "session_name": None,
            "terminal_id": None,
            "runtime_session_id": "claude-headless-1",
            "tmux_session_name": "HOUMAO-gpu",
            "tmux_window_name": "agent",
            "manifest_path": "/tmp/manifest.json",
            "session_root": "/tmp/session-root",
            "agent_name": "HOUMAO-gpu",
            "agent_id": None,
        },
        "manifest_path": "/tmp/manifest.json",
        "session_root": "/tmp/session-root",
        "detail": "launched",
    }

    def _request_root_model(
        method: str,
        path: str,
        model: type[HoumaoHeadlessLaunchResponse],
        **kwargs,
    ):
        recorded["method"] = method
        recorded["path"] = path
        recorded["kwargs"] = kwargs
        return model.model_validate(response_payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    response = client.launch_headless_agent(request_model)

    assert response.tracked_agent_id == "claude-headless-1"
    assert recorded == {
        "method": "POST",
        "path": "/houmao/agents/headless/launches",
        "kwargs": {
            "json_body": request_model.model_dump(mode="json"),
        },
    }


def test_register_launch_posts_to_root_houmao_route(monkeypatch) -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")
    request_model = HoumaoRegisterLaunchRequest(
        session_name="cao-gpu",
        terminal_id="abcd1234",
        tool="claude",
        manifest_path="/tmp/manifest.json",
        session_root="/tmp/session-root",
        agent_name="HOUMAO-gpu",
        agent_id="agent-1234",
        tmux_session_name="cao-gpu",
        tmux_window_name="gpu-1",
    )
    recorded: dict[str, object] = {}
    response_payload = {
        "success": True,
        "session_name": "cao-gpu",
        "terminal_id": "abcd1234",
    }

    def _request_root_model(
        method: str,
        path: str,
        model: type[HoumaoRegisterLaunchResponse],
        **kwargs,
    ):
        recorded["method"] = method
        recorded["path"] = path
        recorded["kwargs"] = kwargs
        return model.model_validate(response_payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    response = client.register_launch(request_model)

    assert response.success is True
    assert response.session_name == "cao-gpu"
    assert response.terminal_id == "abcd1234"
    assert recorded == {
        "method": "POST",
        "path": "/houmao/launches/register",
        "kwargs": {
            "params": {
                "session_name": "cao-gpu",
                "terminal_id": "abcd1234",
                "tool": "claude",
                "manifest_path": "/tmp/manifest.json",
                "session_root": "/tmp/session-root",
                "agent_name": "HOUMAO-gpu",
                "agent_id": "agent-1234",
                "tmux_session_name": "cao-gpu",
                "tmux_window_name": "gpu-1",
            }
        },
    }


def test_get_managed_agent_state_percent_encodes_alias(monkeypatch) -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")
    recorded: dict[str, object] = {}
    payload = {
        "tracked_agent_id": "claude-headless-1",
        "identity": {
            "tracked_agent_id": "claude-headless-1",
            "transport": "headless",
            "tool": "claude",
            "session_name": None,
            "terminal_id": None,
            "runtime_session_id": "claude-headless-1",
            "tmux_session_name": "HOUMAO-gpu",
            "tmux_window_name": "agent",
            "manifest_path": "/tmp/manifest.json",
            "session_root": "/tmp/session-root",
            "agent_name": "HOUMAO-gpu",
            "agent_id": None,
        },
        "availability": "available",
        "turn": {"phase": "ready", "active_turn_id": None},
        "last_turn": {
            "result": "none",
            "turn_id": None,
            "turn_index": None,
            "updated_at_utc": None,
        },
        "diagnostics": [],
    }

    def _request_root_model(
        method: str,
        path: str,
        model: type[HoumaoManagedAgentStateResponse],
        **kwargs,
    ):
        recorded["method"] = method
        recorded["path"] = path
        recorded["kwargs"] = kwargs
        return model.model_validate(payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    state = client.get_managed_agent_state("HOUMAO gpu/1")

    assert state.tracked_agent_id == "claude-headless-1"
    assert recorded == {
        "method": "GET",
        "path": "/houmao/agents/HOUMAO%20gpu%2F1/state",
        "kwargs": {},
    }


def test_get_managed_agent_state_detail_percent_encodes_alias(monkeypatch) -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")
    recorded: dict[str, object] = {}
    payload = {
        "tracked_agent_id": "claude-headless-1",
        "identity": {
            "tracked_agent_id": "claude-headless-1",
            "transport": "headless",
            "tool": "claude",
            "session_name": None,
            "terminal_id": None,
            "runtime_session_id": "claude-headless-1",
            "tmux_session_name": "HOUMAO-gpu",
            "tmux_window_name": "agent",
            "manifest_path": "/tmp/manifest.json",
            "session_root": "/tmp/session-root",
            "agent_name": "HOUMAO-gpu",
            "agent_id": None,
        },
        "summary_state": {
            "tracked_agent_id": "claude-headless-1",
            "identity": {
                "tracked_agent_id": "claude-headless-1",
                "transport": "headless",
                "tool": "claude",
                "session_name": None,
                "terminal_id": None,
                "runtime_session_id": "claude-headless-1",
                "tmux_session_name": "HOUMAO-gpu",
                "tmux_window_name": "agent",
                "manifest_path": "/tmp/manifest.json",
                "session_root": "/tmp/session-root",
                "agent_name": "HOUMAO-gpu",
                "agent_id": None,
            },
            "availability": "available",
            "turn": {"phase": "ready", "active_turn_id": None},
            "last_turn": {
                "result": "none",
                "turn_id": None,
                "turn_index": None,
                "updated_at_utc": None,
            },
            "diagnostics": [],
            "mailbox": None,
            "gateway": None,
        },
        "detail": {
            "transport": "headless",
            "runtime_resumable": True,
            "tmux_session_live": True,
            "can_accept_prompt_now": True,
            "interruptible": False,
            "turn": {"phase": "ready", "active_turn_id": None},
            "last_turn": {
                "result": "none",
                "turn_id": None,
                "turn_index": None,
                "updated_at_utc": None,
            },
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
    }

    def _request_root_model(
        method: str,
        path: str,
        model: type[HoumaoManagedAgentDetailResponse],
        **kwargs,
    ):
        recorded["method"] = method
        recorded["path"] = path
        recorded["kwargs"] = kwargs
        return model.model_validate(payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    detail = client.get_managed_agent_state_detail("HOUMAO gpu/1")

    assert detail.tracked_agent_id == "claude-headless-1"
    assert recorded == {
        "method": "GET",
        "path": "/houmao/agents/HOUMAO%20gpu%2F1/state/detail",
        "kwargs": {},
    }


def test_submit_managed_agent_request_posts_typed_json_body(monkeypatch) -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")
    request_model = HoumaoManagedAgentSubmitPromptRequest(prompt="hello")
    recorded: dict[str, object] = {}
    response_payload = {
        "success": True,
        "tracked_agent_id": "claude-headless-1",
        "request_id": "mreq-123",
        "request_kind": "submit_prompt",
        "disposition": "accepted",
        "detail": "accepted",
        "headless_turn_id": "turn-1",
        "headless_turn_index": 1,
    }

    def _request_root_model(
        method: str,
        path: str,
        model: type[HoumaoManagedAgentRequestAcceptedResponse],
        **kwargs,
    ):
        recorded["method"] = method
        recorded["path"] = path
        recorded["kwargs"] = kwargs
        return model.model_validate(response_payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    response = client.submit_managed_agent_request("HOUMAO gpu/1", request_model)

    assert response.request_id == "mreq-123"
    assert recorded == {
        "method": "POST",
        "path": "/houmao/agents/HOUMAO%20gpu%2F1/requests",
        "kwargs": {"json_body": request_model.model_dump(mode="json")},
    }


def test_submit_managed_agent_gateway_request_posts_typed_json_body(monkeypatch) -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")
    request_model = HoumaoManagedAgentGatewayRequestCreate(
        kind="submit_prompt",
        payload=GatewayRequestPayloadSubmitPromptV1(prompt="hello"),
    )
    recorded: dict[str, object] = {}
    response_payload = {
        "request_id": "greq-123",
        "request_kind": "submit_prompt",
        "state": "accepted",
        "accepted_at_utc": "2026-03-24T16:00:00+00:00",
        "queue_depth": 1,
        "managed_agent_instance_epoch": 2,
    }

    def _request_root_model(
        method: str,
        path: str,
        model: type[HoumaoManagedAgentGatewayRequestAcceptedResponse],
        **kwargs,
    ):
        recorded["method"] = method
        recorded["path"] = path
        recorded["kwargs"] = kwargs
        return model.model_validate(response_payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    response = client.submit_managed_agent_gateway_request("HOUMAO gpu/1", request_model)

    assert response.request_id == "greq-123"
    assert recorded == {
        "method": "POST",
        "path": "/houmao/agents/HOUMAO%20gpu%2F1/gateway/requests",
        "kwargs": {"json_body": request_model.model_dump(mode="json")},
    }


def test_control_managed_agent_gateway_prompt_posts_typed_json_body(monkeypatch) -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")
    request_model = HoumaoManagedAgentGatewayPromptControlRequest(prompt="hello", force=True)
    recorded: dict[str, object] = {}
    response_payload = {
        "status": "ok",
        "action": "submit_prompt",
        "sent": True,
        "forced": True,
        "detail": "Prompt dispatched.",
    }

    def _request_root_model(
        method: str,
        path: str,
        model: type[HoumaoManagedAgentGatewayPromptControlResponse],
        **kwargs,
    ):
        recorded["method"] = method
        recorded["path"] = path
        recorded["kwargs"] = kwargs
        return model.model_validate(response_payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    response = client.control_managed_agent_gateway_prompt("HOUMAO gpu/1", request_model)

    assert response.sent is True
    assert recorded == {
        "method": "POST",
        "path": "/houmao/agents/HOUMAO%20gpu%2F1/gateway/control/prompt",
        "kwargs": {"json_body": request_model.model_dump(mode="json")},
    }


def test_send_managed_agent_gateway_control_input_posts_json_body(monkeypatch) -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")
    request_model = GatewayControlInputRequestV1(
        sequence="<[Escape]>",
        escape_special_keys=False,
    )
    recorded: dict[str, object] = {}
    response_payload = {
        "status": "ok",
        "action": "control_input",
        "detail": "delivered",
    }

    def _request_root_model(
        method: str,
        path: str,
        model: type[object],
        **kwargs,
    ):
        recorded["method"] = method
        recorded["path"] = path
        recorded["kwargs"] = kwargs
        return model.model_validate(response_payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    response = client.send_managed_agent_gateway_control_input("HOUMAO gpu/1", request_model)

    assert response.action == "control_input"
    assert recorded == {
        "method": "POST",
        "path": "/houmao/agents/HOUMAO%20gpu%2F1/gateway/control/send-keys",
        "kwargs": {"json_body": request_model.model_dump(mode="json")},
    }


def test_put_managed_agent_gateway_mail_notifier_posts_json_body(monkeypatch) -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")
    request_model = GatewayMailNotifierPutV1(interval_seconds=60, mode="unread_only")
    recorded: dict[str, object] = {}
    response_payload = {
        "schema_version": 1,
        "enabled": True,
        "interval_seconds": 60,
        "mode": "unread_only",
        "supported": True,
        "support_error": None,
        "last_poll_at_utc": None,
        "last_notification_at_utc": None,
        "last_error": None,
    }

    def _request_root_model(
        method: str,
        path: str,
        model: type[GatewayMailNotifierStatusV1],
        **kwargs,
    ):
        recorded["method"] = method
        recorded["path"] = path
        recorded["kwargs"] = kwargs
        return model.model_validate(response_payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    response = client.put_managed_agent_gateway_mail_notifier("HOUMAO gpu/1", request_model)

    assert response.enabled is True
    assert response.mode == "unread_only"
    assert recorded == {
        "method": "PUT",
        "path": "/houmao/agents/HOUMAO%20gpu%2F1/gateway/mail-notifier",
        "kwargs": {"json_body": request_model.model_dump(mode="json")},
    }


def test_get_managed_agent_mail_status_percent_encodes_alias(monkeypatch) -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")
    recorded: dict[str, object] = {}
    response_payload = {
        "schema_version": 1,
        "transport": "filesystem",
        "principal_id": "agent-1234",
        "address": "agent@agents.localhost",
        "bindings_version": "v1",
    }

    def _request_root_model(
        method: str,
        path: str,
        model: type[HoumaoManagedAgentMailStatusResponse],
        **kwargs,
    ):
        recorded["method"] = method
        recorded["path"] = path
        recorded["kwargs"] = kwargs
        return model.model_validate(response_payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    response = client.get_managed_agent_mail_status("HOUMAO gpu/1")

    assert response.principal_id == "agent-1234"
    assert recorded == {
        "method": "GET",
        "path": "/houmao/agents/HOUMAO%20gpu%2F1/mail/status",
        "kwargs": {},
    }


def test_list_managed_agent_mail_posts_json_body(monkeypatch) -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")
    request_model = HoumaoManagedAgentMailListRequest(read_state="unread", limit=5)
    recorded: dict[str, object] = {}
    response_payload = {
        "schema_version": 1,
        "transport": "filesystem",
        "principal_id": "agent-1234",
        "address": "agent@agents.localhost",
        "box": "inbox",
        "message_count": 0,
        "open_count": 0,
        "unread_count": 0,
        "messages": [],
    }

    def _request_root_model(
        method: str,
        path: str,
        model: type[HoumaoManagedAgentMailListResponse],
        **kwargs,
    ):
        recorded["method"] = method
        recorded["path"] = path
        recorded["kwargs"] = kwargs
        return model.model_validate(response_payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    response = client.list_managed_agent_mail("HOUMAO gpu/1", request_model)

    assert response.box == "inbox"
    assert recorded == {
        "method": "POST",
        "path": "/houmao/agents/HOUMAO%20gpu%2F1/mail/list",
        "kwargs": {"json_body": request_model.model_dump(mode="json")},
    }


def test_send_post_and_reply_managed_agent_mail_post_json_body(monkeypatch) -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")
    recorded: list[dict[str, object]] = []
    send_request = HoumaoManagedAgentMailSendRequest(
        to=["peer@agents.localhost"],
        subject="status",
        body_content="hello",
    )
    post_request = HoumaoManagedAgentMailPostRequest(
        subject="operator note",
        body_content="operator body",
    )
    assert post_request.reply_policy == HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE
    reply_request = HoumaoManagedAgentMailReplyRequest(
        message_ref="msg-123",
        body_content="reply",
    )
    response_payload = {
        "schema_version": 1,
        "operation": "send",
        "transport": "filesystem",
        "principal_id": "agent-1234",
        "address": "agent@agents.localhost",
        "message": {
            "message_ref": "msg-123",
            "thread_ref": "thread-1",
            "created_at_utc": "2026-03-24T16:00:00+00:00",
            "subject": "status",
            "unread": False,
            "body_preview": "hello",
            "body_text": "hello",
            "sender": {"address": "agent@agents.localhost"},
            "to": [{"address": "peer@agents.localhost"}],
            "cc": [],
            "reply_to": [],
            "attachments": [],
        },
    }

    def _request_root_model(
        method: str,
        path: str,
        model: type[HoumaoManagedAgentMailActionResponse],
        **kwargs,
    ):
        recorded.append({"method": method, "path": path, "kwargs": kwargs})
        payload = dict(response_payload)
        if path.endswith("/post"):
            payload["operation"] = "post"
        if path.endswith("/reply"):
            payload["operation"] = "reply"
        return model.model_validate(payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    send_response = client.send_managed_agent_mail("HOUMAO gpu/1", send_request)
    post_response = client.post_managed_agent_mail("HOUMAO gpu/1", post_request)
    reply_response = client.reply_managed_agent_mail("HOUMAO gpu/1", reply_request)

    assert send_response.operation == "send"
    assert post_response.operation == "post"
    assert reply_response.operation == "reply"
    assert recorded == [
        {
            "method": "POST",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/mail/send",
            "kwargs": {"json_body": send_request.model_dump(mode="json")},
        },
        {
            "method": "POST",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/mail/post",
            "kwargs": {"json_body": post_request.model_dump(mode="json")},
        },
        {
            "method": "POST",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/mail/reply",
            "kwargs": {"json_body": reply_request.model_dump(mode="json")},
        },
    ]


def test_mark_and_archive_managed_agent_mail_post_json_body(monkeypatch) -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")
    recorded: list[dict[str, object]] = []
    mark_request = HoumaoManagedAgentMailMarkRequest(
        message_refs=["filesystem:msg-123"],
        read=True,
        answered=True,
    )
    archive_request = HoumaoManagedAgentMailArchiveRequest(message_refs=["filesystem:msg-123"])

    def _request_root_model(
        method: str,
        path: str,
        model: type[HoumaoManagedAgentMailLifecycleResponse],
        **kwargs,
    ):
        recorded.append({"method": method, "path": path, "kwargs": kwargs})
        operation = "archive" if path.endswith("/archive") else "mark"
        return model.model_validate(
            {
                "schema_version": 1,
                "operation": operation,
                "transport": "filesystem",
                "principal_id": "agent-1234",
                "address": "agent@agents.localhost",
                "message_count": 1,
                "messages": [
                    {
                        "message_ref": "filesystem:msg-123",
                        "thread_ref": "thread-1",
                        "created_at_utc": "2026-03-24T16:00:00+00:00",
                        "subject": "status",
                        "read": True,
                        "answered": True,
                        "archived": operation == "archive",
                        "box": "archive" if operation == "archive" else "inbox",
                        "unread": False,
                        "body_preview": "hello",
                        "sender": {"address": "agent@agents.localhost"},
                        "to": [{"address": "peer@agents.localhost"}],
                        "cc": [],
                        "reply_to": [],
                        "attachments": [],
                    }
                ],
            }
        )

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    mark_response = client.mark_managed_agent_mail("HOUMAO gpu/1", mark_request)
    archive_response = client.archive_managed_agent_mail("HOUMAO gpu/1", archive_request)

    assert mark_response.operation == "mark"
    assert archive_response.operation == "archive"
    assert recorded == [
        {
            "method": "POST",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/mail/mark",
            "kwargs": {"json_body": mark_request.model_dump(mode="json")},
        },
        {
            "method": "POST",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/mail/archive",
            "kwargs": {"json_body": archive_request.model_dump(mode="json")},
        },
    ]


def test_get_session_uses_explicit_cao_prefix(monkeypatch) -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")
    recorded: dict[str, object] = {}
    payload = {
        "session": {"id": "cao-gpu", "name": "cao-gpu", "status": "attached"},
        "terminals": [],
    }

    def _request_json(method: str, path: str, **kwargs):
        recorded["method"] = method
        recorded["path"] = path
        recorded["kwargs"] = kwargs
        return payload, 200, "http://127.0.0.1:9889/cao/sessions/cao-gpu"

    monkeypatch.setattr(client, "_request_json", _request_json)

    detail = client.get_session("cao-gpu")

    assert detail.session.id == "cao-gpu"
    assert recorded == {
        "method": "GET",
        "path": "/sessions/cao-gpu",
        "kwargs": {"params": None, "timeout_seconds": None},
    }


def test_resolve_pair_authority_client_selects_passive_server(monkeypatch) -> None:
    def _request_root_model(self, method: str, path: str, model: type[object], **kwargs):
        del self, method, kwargs
        assert path == "/health"
        return model.model_validate({"status": "ok", "houmao_service": "houmao-passive-server"})

    monkeypatch.setattr(HoumaoServerClient, "_request_root_model", _request_root_model)

    resolution = resolve_pair_authority_client(base_url="http://127.0.0.1:9891")

    assert isinstance(resolution.client, PassiveServerClient)
    assert resolution.health.houmao_service == "houmao-passive-server"


def test_resolve_pair_authority_client_rejects_unknown_pair_identity(monkeypatch) -> None:
    def _request_root_model(self, method: str, path: str, model: type[object], **kwargs):
        del self, method, kwargs
        assert path == "/health"
        return model.model_validate({"status": "ok", "houmao_service": "raw-cao"})

    monkeypatch.setattr(HoumaoServerClient, "_request_root_model", _request_root_model)

    with pytest.raises(UnsupportedPairAuthorityError, match="unsupported houmao_service"):
        resolve_pair_authority_client(base_url="http://127.0.0.1:9891")


def test_passive_server_client_routes_state_detail_and_history_to_compatibility_paths(
    monkeypatch,
) -> None:
    client = PassiveServerClient("http://127.0.0.1:9891")
    recorded: list[dict[str, object]] = []
    identity_payload = {
        "tracked_agent_id": "tracked-alpha",
        "transport": "headless",
        "tool": "claude",
        "session_name": None,
        "terminal_id": None,
        "runtime_session_id": "tracked-alpha",
        "tmux_session_name": "HOUMAO-alpha",
        "tmux_window_name": "agent",
        "manifest_path": "/tmp/manifest.json",
        "session_root": "/tmp/session-root",
        "agent_name": "HOUMAO-alpha",
        "agent_id": "published-alpha",
    }
    state_payload = {
        "tracked_agent_id": "tracked-alpha",
        "identity": identity_payload,
        "availability": "available",
        "turn": {"phase": "ready", "active_turn_id": None},
        "last_turn": {
            "result": "none",
            "turn_id": None,
            "turn_index": None,
            "updated_at_utc": None,
        },
        "diagnostics": [],
        "mailbox": None,
        "gateway": None,
    }
    detail_payload = {
        "tracked_agent_id": "tracked-alpha",
        "identity": identity_payload,
        "summary_state": state_payload,
        "detail": {
            "transport": "headless",
            "runtime_resumable": True,
            "tmux_session_live": True,
            "can_accept_prompt_now": True,
            "interruptible": False,
            "turn": {"phase": "ready", "active_turn_id": None},
            "last_turn": {
                "result": "none",
                "turn_id": None,
                "turn_index": None,
                "updated_at_utc": None,
            },
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
    }
    history_payload = {
        "tracked_agent_id": "tracked-alpha",
        "entries": [
            {
                "recorded_at_utc": "2026-03-26T09:00:00+00:00",
                "summary": "turn completed",
                "availability": "available",
                "turn_phase": "ready",
                "last_turn_result": "success",
                "turn_id": "turn-0001",
            }
        ],
    }

    def _request_root_model(method: str, path: str, model: type[object], **kwargs):
        recorded.append({"method": method, "path": path, "kwargs": kwargs})
        if path.endswith("/managed-state"):
            return model.model_validate(state_payload)
        if path.endswith("/managed-state/detail"):
            return model.model_validate(detail_payload)
        if path.endswith("/managed-history"):
            return model.model_validate(history_payload)
        raise AssertionError(f"unexpected path {path}")

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    state = client.get_managed_agent_state("HOUMAO gpu/1")
    detail = client.get_managed_agent_state_detail("HOUMAO gpu/1")
    history = client.get_managed_agent_history("HOUMAO gpu/1", limit=5)

    assert state.tracked_agent_id == "tracked-alpha"
    assert detail.detail.transport == "headless"
    assert history.entries[0].turn_id == "turn-0001"
    assert recorded == [
        {
            "method": "GET",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/managed-state",
            "kwargs": {},
        },
        {
            "method": "GET",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/managed-state/detail",
            "kwargs": {},
        },
        {
            "method": "GET",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/managed-history",
            "kwargs": {"params": {"limit": "5"}},
        },
    ]


def test_passive_server_client_submit_headless_turn_normalizes_response(monkeypatch) -> None:
    client = PassiveServerClient("http://127.0.0.1:9891")
    recorded: dict[str, object] = {}
    request_model = HoumaoHeadlessTurnRequest(prompt="hello")
    response_payload = {
        "status": "ok",
        "tracked_agent_id": "tracked-alpha",
        "turn_id": "turn-0001",
        "turn_index": 1,
        "turn_status": "completed",
        "detail": "accepted",
    }

    def _request_root_model(method: str, path: str, model: type[object], **kwargs):
        recorded["method"] = method
        recorded["path"] = path
        recorded["kwargs"] = kwargs
        return model.model_validate(response_payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    response = client.submit_headless_turn("HOUMAO gpu/1", request_model)

    assert response == HoumaoHeadlessTurnAcceptedResponse(
        success=True,
        tracked_agent_id="tracked-alpha",
        turn_id="turn-0001",
        turn_index=1,
        status="completed",
        detail="accepted",
    )
    assert recorded == {
        "method": "POST",
        "path": "/houmao/agents/HOUMAO%20gpu%2F1/turns",
        "kwargs": {
            "json_body": PassiveHeadlessTurnRequest(
                prompt=request_model.prompt,
                chat_session=request_model.chat_session,
            ).model_dump(mode="json")
        },
    }


def test_passive_server_client_launch_passive_headless_agent_posts_request_model(
    monkeypatch,
) -> None:
    client = PassiveServerClient("http://127.0.0.1:9891")
    recorded: dict[str, object] = {}
    request_model = PassiveHeadlessLaunchRequest(
        tool="claude",
        working_directory="/tmp/workdir",
        agent_def_dir="/tmp/agents",
        brain_manifest_path="/tmp/brain/manifest.json",
        role_name="server-api-smoke",
        agent_name="HOUMAO-headless",
        agent_id="published-headless",
    )
    response_payload = {
        "status": "ok",
        "tracked_agent_id": "tracked-headless",
        "agent_name": "HOUMAO-headless",
        "manifest_path": "/tmp/brain/manifest.json",
        "session_root": "/tmp/session-root",
        "detail": "launch accepted",
    }

    def _request_root_model(method: str, path: str, model: type[object], **kwargs):
        recorded["method"] = method
        recorded["path"] = path
        recorded["kwargs"] = kwargs
        return model.model_validate(response_payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    response = client.launch_passive_headless_agent(request_model)

    assert response == PassiveHeadlessLaunchResponse(
        status="ok",
        tracked_agent_id="tracked-headless",
        agent_name="HOUMAO-headless",
        manifest_path="/tmp/brain/manifest.json",
        session_root="/tmp/session-root",
        detail="launch accepted",
    )
    assert recorded == {
        "method": "POST",
        "path": "/houmao/agents/headless/launches",
        "kwargs": {"json_body": request_model.model_dump(mode="json")},
    }


def test_passive_server_client_normalizes_headless_managed_prompt_submission(
    monkeypatch,
) -> None:
    client = PassiveServerClient("http://127.0.0.1:9891")
    identity = HoumaoManagedAgentIdentity(
        tracked_agent_id="tracked-alpha",
        transport="headless",
        tool="claude",
        session_name=None,
        terminal_id=None,
        runtime_session_id="tracked-alpha",
        tmux_session_name="HOUMAO-alpha",
        tmux_window_name="agent",
        manifest_path="/tmp/manifest.json",
        session_root="/tmp/session-root",
        agent_name="HOUMAO-alpha",
        agent_id="published-alpha",
    )

    monkeypatch.setattr(client, "get_managed_agent", lambda agent_ref: identity)
    monkeypatch.setattr(
        client,
        "submit_headless_turn",
        lambda agent_ref, request_model: HoumaoHeadlessTurnAcceptedResponse(
            success=True,
            tracked_agent_id="tracked-alpha",
            turn_id="turn-0001",
            turn_index=1,
            status="completed",
            detail=f"accepted:{request_model.prompt}:{agent_ref}",
        ),
    )

    response = client.submit_managed_agent_request(
        "published-alpha",
        HoumaoManagedAgentSubmitPromptRequest(prompt="hello"),
    )

    assert response.request_id == "headless-turn:turn-0001"
    assert response.headless_turn_id == "turn-0001"
    assert response.headless_turn_index == 1
    assert response.detail == "accepted:hello:published-alpha"


def test_passive_server_client_gateway_send_keys_and_mail_notifier_routes(monkeypatch) -> None:
    client = PassiveServerClient("http://127.0.0.1:9891")
    recorded: list[dict[str, object]] = []
    request_model = GatewayControlInputRequestV1(sequence="abc", escape_special_keys=True)
    notifier_put = GatewayMailNotifierPutV1(interval_seconds=45, mode="unread_only")
    control_payload = {
        "status": "ok",
        "action": "control_input",
        "detail": "queued",
    }
    notifier_payload = {
        "schema_version": 1,
        "enabled": True,
        "interval_seconds": 45,
        "mode": "unread_only",
        "supported": True,
        "support_error": None,
        "last_poll_at_utc": None,
        "last_notification_at_utc": None,
        "last_error": None,
    }
    notifier_disabled_payload = {
        "schema_version": 1,
        "enabled": False,
        "interval_seconds": None,
        "mode": "unread_only",
        "supported": True,
        "support_error": None,
        "last_poll_at_utc": None,
        "last_notification_at_utc": None,
        "last_error": None,
    }

    def _request_root_model(method: str, path: str, model: type[object], **kwargs):
        recorded.append({"method": method, "path": path, "kwargs": kwargs})
        if path.endswith("/gateway/control/send-keys"):
            return model.model_validate(control_payload)
        if method == "DELETE":
            return model.model_validate(notifier_disabled_payload)
        return model.model_validate(notifier_payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    control = client.send_managed_agent_gateway_control_input("HOUMAO gpu/1", request_model)
    notifier_status = client.get_managed_agent_gateway_mail_notifier("HOUMAO gpu/1")
    notifier_enabled = client.put_managed_agent_gateway_mail_notifier("HOUMAO gpu/1", notifier_put)
    notifier_disabled = client.delete_managed_agent_gateway_mail_notifier("HOUMAO gpu/1")

    assert control.detail == "queued"
    assert notifier_status.enabled is True
    assert notifier_enabled.interval_seconds == 45
    assert notifier_enabled.mode == "unread_only"
    assert notifier_disabled.enabled is False
    assert notifier_disabled.mode == "unread_only"
    assert recorded == [
        {
            "method": "POST",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/gateway/control/send-keys",
            "kwargs": {"json_body": request_model.model_dump(mode="json")},
        },
        {
            "method": "GET",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/gateway/mail-notifier",
            "kwargs": {},
        },
        {
            "method": "PUT",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/gateway/mail-notifier",
            "kwargs": {"json_body": notifier_put.model_dump(mode="json")},
        },
        {
            "method": "DELETE",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/gateway/mail-notifier",
            "kwargs": {},
        },
    ]


@pytest.mark.parametrize(
    ("client_type", "base_url"),
    [
        (HoumaoServerClient, "http://127.0.0.1:9889"),
        (PassiveServerClient, "http://127.0.0.1:9891"),
    ],
)
def test_pair_clients_gateway_reminder_routes(client_type, base_url, monkeypatch) -> None:
    client = client_type(base_url)
    recorded: list[dict[str, object]] = []
    create_request = GatewayReminderCreateBatchV1(
        reminders=[
            GatewayReminderDefinitionV1(
                mode="one_off",
                title="Check inbox",
                prompt="Review the inbox now.",
                ranking=0,
                start_after_seconds=60,
            )
        ]
    )
    update_request = GatewayReminderPutV1(
        mode="one_off",
        title="Check inbox later",
        send_keys=GatewayReminderSendKeysV1(sequence="<[Escape]>", ensure_enter=False),
        ranking=-1,
        deliver_at_utc="2026-04-09T12:00:00+00:00",
    )
    list_payload = {
        "schema_version": 1,
        "effective_reminder_id": "greminder-1",
        "reminders": [
            {
                "schema_version": 1,
                "reminder_id": "greminder-1",
                "mode": "one_off",
                "delivery_kind": "prompt",
                "title": "Check inbox",
                "prompt": "Review the inbox now.",
                "send_keys": None,
                "ranking": 0,
                "paused": False,
                "selection_state": "effective",
                "delivery_state": "scheduled",
                "created_at_utc": "2026-04-09T00:00:00+00:00",
                "next_due_at_utc": "2026-04-09T00:01:00+00:00",
                "interval_seconds": None,
                "last_started_at_utc": None,
                "blocked_by_reminder_id": None,
            }
        ],
    }
    detail_payload = list_payload["reminders"][0] | {"title": "Check inbox later", "ranking": -1}
    delete_payload = {
        "schema_version": 1,
        "status": "ok",
        "action": "delete_reminder",
        "reminder_id": "greminder-1",
        "deleted": True,
        "detail": "deleted",
    }

    def _request_root_model(method: str, path: str, model: type[object], **kwargs):
        recorded.append({"method": method, "path": path, "kwargs": kwargs})
        if method == "GET" and path.endswith("/gateway/reminders"):
            return model.model_validate(list_payload)
        if method == "POST":
            return model.model_validate(list_payload)
        if method == "PUT":
            return model.model_validate(detail_payload)
        if method == "DELETE":
            return model.model_validate(delete_payload)
        return model.model_validate(detail_payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    reminders = client.list_managed_agent_gateway_reminders("HOUMAO gpu/1")
    created = client.create_managed_agent_gateway_reminders("HOUMAO gpu/1", create_request)
    detail = client.get_managed_agent_gateway_reminder("HOUMAO gpu/1", "greminder-1")
    updated = client.put_managed_agent_gateway_reminder(
        "HOUMAO gpu/1", "greminder-1", update_request
    )
    deleted = client.delete_managed_agent_gateway_reminder("HOUMAO gpu/1", "greminder-1")

    assert reminders.effective_reminder_id == "greminder-1"
    assert created.reminders[0].reminder_id == "greminder-1"
    assert detail.reminder_id == "greminder-1"
    assert updated.ranking == -1
    assert deleted.reminder_id == "greminder-1"
    assert recorded == [
        {
            "method": "GET",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/gateway/reminders",
            "kwargs": {},
        },
        {
            "method": "POST",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/gateway/reminders",
            "kwargs": {"json_body": create_request.model_dump(mode="json")},
        },
        {
            "method": "GET",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/gateway/reminders/greminder-1",
            "kwargs": {},
        },
        {
            "method": "PUT",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/gateway/reminders/greminder-1",
            "kwargs": {"json_body": update_request.model_dump(mode="json")},
        },
        {
            "method": "DELETE",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/gateway/reminders/greminder-1",
            "kwargs": {},
        },
    ]


def test_houmao_server_client_gateway_tui_routes(monkeypatch) -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")
    recorded: list[dict[str, object]] = []
    state_payload = {
        "terminal_id": "headless123",
        "tracked_session": {
            "tracked_session_id": "tracked-agent",
            "session_name": "tracked-agent",
            "tool": "codex",
            "tmux_session_name": "HOUMAO-gpu",
            "terminal_aliases": ["headless123"],
        },
        "diagnostics": {
            "availability": "available",
            "transport_state": "tmux_up",
            "process_state": "tui_up",
            "parse_status": "parsed",
            "probe_error": None,
            "parse_error": None,
        },
        "probe_snapshot": None,
        "parsed_surface": None,
        "surface": {
            "accepting_input": "yes",
            "editing_input": "no",
            "ready_posture": "yes",
        },
        "turn": {"phase": "ready"},
        "last_turn": {"result": "none", "source": "none", "updated_at_utc": None},
        "stability": {
            "signature": "sig-1",
            "stable": True,
            "stable_for_seconds": 3.0,
            "stable_since_utc": "2026-03-27T00:00:00+00:00",
        },
        "recent_transitions": [],
    }
    history_payload = {
        "terminal_id": "headless123",
        "tracked_session_id": "tracked-agent",
        "entries": [
            {
                "recorded_at_utc": "2026-03-27T00:00:00+00:00",
                "diagnostics": state_payload["diagnostics"],
                "probe_snapshot": None,
                "parsed_surface": None,
                "surface": state_payload["surface"],
                "turn": state_payload["turn"],
                "last_turn": state_payload["last_turn"],
                "stability": state_payload["stability"],
            }
        ],
    }

    def _request_root_model(method: str, path: str, model: type[object], **kwargs):
        recorded.append({"method": method, "path": path, "kwargs": kwargs})
        if path.endswith("/gateway/tui/history?limit=7"):
            return model.model_validate(history_payload)
        return model.model_validate(state_payload)

    monkeypatch.setattr(client, "_request_root_model", _request_root_model)

    state = client.get_managed_agent_gateway_tui_state("HOUMAO gpu/1")
    history = client.get_managed_agent_gateway_tui_history("HOUMAO gpu/1", limit=7)
    noted = client.note_managed_agent_gateway_tui_prompt("HOUMAO gpu/1", prompt="hello")

    assert isinstance(state, HoumaoTerminalStateResponse)
    assert isinstance(history, HoumaoTerminalSnapshotHistoryResponse)
    assert noted.terminal_id == "headless123"
    assert recorded == [
        {
            "method": "GET",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/gateway/tui/state",
            "kwargs": {},
        },
        {
            "method": "GET",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/gateway/tui/history?limit=7",
            "kwargs": {},
        },
        {
            "method": "POST",
            "path": "/houmao/agents/HOUMAO%20gpu%2F1/gateway/tui/note-prompt",
            "kwargs": {
                "json_body": GatewayRequestPayloadSubmitPromptV1(prompt="hello").model_dump(
                    mode="json"
                )
            },
        },
    ]
