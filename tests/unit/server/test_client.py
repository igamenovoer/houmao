from __future__ import annotations

from houmao.agents.realm_controller.gateway_models import (
    GatewayMailNotifierPutV1,
    GatewayMailNotifierStatusV1,
)
from houmao.server.client import HoumaoServerClient
from houmao.server.models import (
    HoumaoHeadlessLaunchRequest,
    HoumaoHeadlessLaunchResponse,
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentRequestAcceptedResponse,
    HoumaoManagedAgentSubmitPromptRequest,
    HoumaoManagedAgentStateResponse,
    HoumaoTerminalStateResponse,
)


def test_terminal_state_parses_simplified_tracked_state_contract(monkeypatch) -> None:
    payload = {
        "terminal_id": "abcd1234",
        "tracked_session": {
            "tracked_session_id": "cao-gpu",
            "session_name": "cao-gpu",
            "tool": "codex",
            "tmux_session_name": "AGENTSYS-gpu",
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
        agent_name="AGENTSYS-gpu",
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
            "tmux_session_name": "AGENTSYS-gpu",
            "tmux_window_name": "agent",
            "manifest_path": "/tmp/manifest.json",
            "session_root": "/tmp/session-root",
            "agent_name": "AGENTSYS-gpu",
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
            "tmux_session_name": "AGENTSYS-gpu",
            "tmux_window_name": "agent",
            "manifest_path": "/tmp/manifest.json",
            "session_root": "/tmp/session-root",
            "agent_name": "AGENTSYS-gpu",
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

    state = client.get_managed_agent_state("AGENTSYS gpu/1")

    assert state.tracked_agent_id == "claude-headless-1"
    assert recorded == {
        "method": "GET",
        "path": "/houmao/agents/AGENTSYS%20gpu%2F1/state",
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
            "tmux_session_name": "AGENTSYS-gpu",
            "tmux_window_name": "agent",
            "manifest_path": "/tmp/manifest.json",
            "session_root": "/tmp/session-root",
            "agent_name": "AGENTSYS-gpu",
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
                "tmux_session_name": "AGENTSYS-gpu",
                "tmux_window_name": "agent",
                "manifest_path": "/tmp/manifest.json",
                "session_root": "/tmp/session-root",
                "agent_name": "AGENTSYS-gpu",
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

    detail = client.get_managed_agent_state_detail("AGENTSYS gpu/1")

    assert detail.tracked_agent_id == "claude-headless-1"
    assert recorded == {
        "method": "GET",
        "path": "/houmao/agents/AGENTSYS%20gpu%2F1/state/detail",
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

    response = client.submit_managed_agent_request("AGENTSYS gpu/1", request_model)

    assert response.request_id == "mreq-123"
    assert recorded == {
        "method": "POST",
        "path": "/houmao/agents/AGENTSYS%20gpu%2F1/requests",
        "kwargs": {"json_body": request_model.model_dump(mode="json")},
    }


def test_put_managed_agent_gateway_mail_notifier_posts_json_body(monkeypatch) -> None:
    client = HoumaoServerClient("http://127.0.0.1:9889")
    request_model = GatewayMailNotifierPutV1(interval_seconds=60)
    recorded: dict[str, object] = {}
    response_payload = {
        "schema_version": 1,
        "enabled": True,
        "interval_seconds": 60,
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

    response = client.put_managed_agent_gateway_mail_notifier("AGENTSYS gpu/1", request_model)

    assert response.enabled is True
    assert recorded == {
        "method": "PUT",
        "path": "/houmao/agents/AGENTSYS%20gpu%2F1/gateway/mail-notifier",
        "kwargs": {"json_body": request_model.model_dump(mode="json")},
    }


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
        "kwargs": {"params": None},
    }
