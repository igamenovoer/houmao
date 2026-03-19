from __future__ import annotations

from houmao.server.client import HoumaoServerClient
from houmao.server.models import HoumaoTerminalStateResponse


def test_terminal_state_parses_lifecycle_authority_metadata(monkeypatch) -> None:
    payload = {
        "terminal_id": "abcd1234",
        "tracked_session": {
            "tracked_session_id": "cao-gpu",
            "session_name": "cao-gpu",
            "tool": "codex",
            "tmux_session_name": "AGENTSYS-gpu",
            "terminal_aliases": ["abcd1234"],
        },
        "transport_state": "tmux_up",
        "process_state": "tui_up",
        "parse_status": "parsed",
        "probe_snapshot": None,
        "probe_error": None,
        "parse_error": None,
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
        "operator_state": {
            "status": "ready",
            "readiness_state": "ready",
            "completion_state": "inactive",
            "detail": "Supported TUI is ready for input.",
            "projection_changed": False,
            "updated_at_utc": "2026-03-19T10:00:00+00:00",
        },
        "lifecycle_timing": {
            "readiness_unknown_elapsed_seconds": None,
            "completion_unknown_elapsed_seconds": None,
            "completion_candidate_elapsed_seconds": None,
            "unknown_to_stalled_timeout_seconds": 30.0,
            "completion_stability_seconds": 1.0,
        },
        "lifecycle_authority": {
            "completion_authority": "unanchored_background",
            "turn_anchor_state": "absent",
            "completion_monitoring_armed": False,
            "detail": "No active server-owned turn anchor is armed.",
            "anchor_armed_at_utc": None,
            "anchor_lost_at_utc": None,
            "anchor_loss_reason": None,
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

    def _request_model(method: str, path: str, model: type[HoumaoTerminalStateResponse], **kwargs):
        del method, path, kwargs
        return model.model_validate(payload)

    monkeypatch.setattr(client, "_request_model", _request_model)

    state = client.terminal_state("abcd1234")

    assert state.lifecycle_authority.completion_authority == "unanchored_background"
    assert state.lifecycle_authority.turn_anchor_state == "absent"
