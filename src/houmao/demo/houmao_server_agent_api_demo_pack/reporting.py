"""Report building and sanitization for the agent API demo pack."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping


_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$")
_ABSOLUTE_PATH_PATTERN = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
_PATH_KEYS = {
    "repo_root",
    "pack_dir",
    "run_root",
    "control_dir",
    "expected_report_path",
}
_PLACEHOLDER_KEYS = {
    "api_base_url": "<API_BASE_URL>",
    "tracked_agent_id": "<TRACKED_AGENT_ID>",
    "session_name": "<SESSION_NAME>",
    "terminal_id": "<TERMINAL_ID>",
    "tmux_window_name": "<TMUX_WINDOW_NAME>",
    "request_id": "<REQUEST_ID>",
    "headless_turn_id": "<HEADLESS_TURN_ID>",
    "generated_at_utc": "<TIMESTAMP>",
    "started_at_utc": "<TIMESTAMP>",
    "updated_at_utc": "<TIMESTAMP>",
    "completed_at_utc": "<TIMESTAMP>",
    "pid": "<PID>",
    "prompt_text": "<PROMPT_TEXT>",
}


def _mapping(value: Any, *, context: str) -> dict[str, Any]:
    """Return one mapping or raise a validation error."""

    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be a mapping")
    return dict(value)


def _history_entry_count(history_payload: Any) -> int:
    """Return the entry count from one history payload."""

    if not isinstance(history_payload, Mapping):
        return 0
    entries = history_payload.get("entries")
    if isinstance(entries, list):
        return len(entries)
    entry_count = history_payload.get("entry_count")
    return int(entry_count) if isinstance(entry_count, int) else 0


def _detail_transport(route_payload: Mapping[str, Any]) -> str | None:
    """Return the detailed transport from one route-verification payload."""

    detail = route_payload.get("detail")
    if not isinstance(detail, Mapping):
        return None
    detail_payload = detail.get("detail")
    if not isinstance(detail_payload, Mapping):
        return None
    transport = detail_payload.get("transport")
    return str(transport) if isinstance(transport, str) and transport.strip() else None


def build_report(
    *,
    state_payload: Mapping[str, Any],
    report_path: Path,
) -> dict[str, Any]:
    """Build one raw report from the persisted demo state."""

    state = _mapping(state_payload, context="state_payload")
    lanes_payload = _mapping(state.get("lanes", {}), context="state.lanes")
    preflight_payload = (
        _mapping(state.get("preflight", {}), context="preflight")
        if isinstance(state.get("preflight"), Mapping)
        else {}
    )
    server_payload = (
        _mapping(state.get("server", {}), context="server")
        if isinstance(state.get("server"), Mapping)
        else {}
    )
    shared_routes = state.get("shared_routes")
    shared_routes_payload = dict(shared_routes) if isinstance(shared_routes, Mapping) else None
    executables_payload = (
        _mapping(preflight_payload.get("executables", {}), context="preflight.executables")
        if isinstance(preflight_payload.get("executables"), Mapping)
        else {}
    )
    health_payload = (
        _mapping(server_payload.get("health", {}), context="server.health")
        if isinstance(server_payload.get("health"), Mapping)
        else {}
    )

    lanes_report: dict[str, Any] = {}
    for lane_id, lane_raw in sorted(lanes_payload.items()):
        lane = _mapping(lane_raw, context=f"lane {lane_id}")
        route_payload = (
            _mapping(lane.get("route_verification"), context=f"{lane_id}.route_verification")
            if isinstance(lane.get("route_verification"), Mapping)
            else {}
        )
        prompt_payload = (
            _mapping(lane.get("prompt_verification"), context=f"{lane_id}.prompt_verification")
            if isinstance(lane.get("prompt_verification"), Mapping)
            else {}
        )
        interrupt_payload = (
            _mapping(
                lane.get("interrupt_verification"),
                context=f"{lane_id}.interrupt_verification",
            )
            if isinstance(lane.get("interrupt_verification"), Mapping)
            else {}
        )
        stop_payload = (
            _mapping(lane.get("stop_result"), context=f"{lane_id}.stop_result")
            if isinstance(lane.get("stop_result"), Mapping)
            else {}
        )
        prompt_accepted = prompt_payload.get("accepted")
        interrupt_accepted = interrupt_payload.get("accepted")
        headless_turn = prompt_payload.get("headless_turn")
        headless_turn_status: str | None = None
        if isinstance(headless_turn, Mapping):
            status_payload = headless_turn.get("status")
            if isinstance(status_payload, Mapping):
                status_value = status_payload.get("status")
                if isinstance(status_value, str) and status_value.strip():
                    headless_turn_status = status_value

        lanes_report[str(lane_id)] = {
            "tool": lane.get("tool"),
            "transport": lane.get("transport"),
            "route": {
                "identity_present": bool(route_payload.get("identity")),
                "detail_transport": _detail_transport(route_payload),
                "history_captured": _history_entry_count(route_payload.get("history")) >= 0
                and "history" in route_payload,
            },
            "prompt": {
                "requested": bool(prompt_payload),
                "prompt_text": prompt_payload.get("prompt"),
                "disposition": (
                    prompt_accepted.get("disposition")
                    if isinstance(prompt_accepted, Mapping)
                    else None
                ),
                "request_kind": (
                    prompt_accepted.get("request_kind")
                    if isinstance(prompt_accepted, Mapping)
                    else None
                ),
                "state_progress_observed": bool(prompt_payload.get("state_after")),
                "headless_turn_status": headless_turn_status,
                "headless_turn_terminal": (
                    None
                    if headless_turn_status is None
                    else headless_turn_status in {"completed", "failed", "interrupted"}
                ),
            },
            "interrupt": {
                "requested": bool(interrupt_payload),
                "disposition": (
                    interrupt_accepted.get("disposition")
                    if isinstance(interrupt_accepted, Mapping)
                    else None
                ),
                "request_kind": (
                    interrupt_accepted.get("request_kind")
                    if isinstance(interrupt_accepted, Mapping)
                    else None
                ),
                "follow_up_state_captured": bool(interrupt_payload.get("state_after")),
                "history_captured_after": bool(interrupt_payload.get("history_after")),
            },
            "stop": {
                "attempted": bool(stop_payload),
                "managed_stop_status": (
                    stop_payload.get("managed_stop", {}).get("status")
                    if isinstance(stop_payload.get("managed_stop"), Mapping)
                    else None
                ),
                "managed_stop_error": stop_payload.get("managed_stop_error"),
            },
        }

    report = {
        "pack": "houmao-server-agent-api-demo-pack",
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "repo_root": state.get("repo_root"),
        "pack_dir": state.get("pack_dir"),
        "run_root": state.get("run_root"),
        "active": bool(state.get("active")),
        "selected_lanes": list(state.get("selected_lane_ids", [])),
        "steps": dict(state.get("steps", {})),
        "preflight": {
            "checked_executables": sorted(executables_payload.keys()),
            "available_executables": sorted(
                key
                for key, value in executables_payload.items()
                if isinstance(value, str) and value.strip()
            ),
            "credentials_present": bool(
                list(preflight_payload.get("credential_env_var_names", []))
            ),
            "missing": list(preflight_payload.get("missing", [])),
        },
        "server": {
            "api_base_url": server_payload.get("api_base_url"),
            "pid": server_payload.get("pid"),
            "health_status": health_payload.get("status"),
            "credentials_present": bool(
                list(server_payload.get("credential_env_var_names", []))
            ),
        },
        "shared_routes": (
            None
            if shared_routes_payload is None
            else {
                "listed_agent_count": len(list(shared_routes_payload.get("listed_agent_ids", []))),
                "expected_agent_count": len(
                    list(shared_routes_payload.get("expected_agent_ids", []))
                ),
                "missing_agent_count": len(
                    list(shared_routes_payload.get("missing_agent_ids", []))
                ),
                "history_limit": shared_routes_payload.get("history_limit"),
            }
        ),
        "lanes": lanes_report,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _sanitize_string(value: str, *, key: str | None) -> str:
    """Sanitize one string leaf value."""

    if key in _PLACEHOLDER_KEYS:
        return _PLACEHOLDER_KEYS[key]
    if key in _PATH_KEYS:
        return "<ABSOLUTE_PATH>"
    if _TIMESTAMP_PATTERN.match(value):
        return "<TIMESTAMP>"
    if _ABSOLUTE_PATH_PATTERN.match(value):
        return "<ABSOLUTE_PATH>"
    return value


def sanitize_report(payload: Any, *, key: str | None = None) -> Any:
    """Recursively sanitize one raw demo-pack report."""

    if isinstance(payload, Mapping):
        return {
            str(child_key): sanitize_report(child_value, key=str(child_key))
            for child_key, child_value in payload.items()
        }
    if isinstance(payload, list):
        return [sanitize_report(item, key=None) for item in payload]
    if isinstance(payload, str):
        return _sanitize_string(payload, key=key)
    if isinstance(payload, int) and key == "pid":
        return "<PID>"
    return payload


def verify_sanitized_report(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    """Require the sanitized report to match the expected contract."""

    if actual != expected:
        raise ValueError(
            "sanitized report mismatch\n"
            f"expected:\n{json.dumps(expected, indent=2, sort_keys=True)}\n"
            f"actual:\n{json.dumps(actual, indent=2, sort_keys=True)}"
        )
