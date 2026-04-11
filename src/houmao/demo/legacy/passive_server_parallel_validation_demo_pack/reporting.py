"""Report building and sanitization for the passive-server parallel validation demo pack."""

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
    "agent_def_dir",
    "shared_runtime_root",
    "registry_root",
    "jobs_root",
    "workdir",
    "manifest_path",
    "session_root",
    "expected_report_path",
    "stdout_log_path",
    "stderr_log_path",
}
_PLACEHOLDER_KEYS = {
    "api_base_url": "<API_BASE_URL>",
    "tracked_agent_id": "<TRACKED_AGENT_ID>",
    "agent_id": "<AGENT_ID>",
    "agent_name": "<AGENT_NAME>",
    "tmux_session_name": "<TMUX_SESSION_NAME>",
    "session_name": "<SESSION_NAME>",
    "request_id": "<REQUEST_ID>",
    "turn_id": "<TURN_ID>",
    "headless_turn_id": "<HEADLESS_TURN_ID>",
    "generated_at_utc": "<TIMESTAMP>",
    "started_at_utc": "<TIMESTAMP>",
    "updated_at_utc": "<TIMESTAMP>",
    "completed_at_utc": "<TIMESTAMP>",
    "published_at": "<TIMESTAMP>",
    "lease_expires_at": "<TIMESTAMP>",
    "stable_since_utc": "<TIMESTAMP>",
    "recorded_at_utc": "<TIMESTAMP>",
    "pid": "<PID>",
    "prompt_text": "<PROMPT_TEXT>",
}


def _mapping(value: Any, *, context: str) -> dict[str, Any]:
    """Return one mapping or raise a validation error."""

    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be a mapping")
    return dict(value)


def _phase_status(result: Mapping[str, Any] | None) -> str:
    """Return a stable phase status string."""

    if result is None:
        return "not_run"
    if bool(result.get("ok")):
        return "passed"
    return "failed"


def _history_summary(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a stable history summary from one normalized payload."""

    if payload is None:
        return {
            "entry_count": 0,
            "latest_turn_phase": None,
            "latest_last_turn_result": None,
            "latest_summary": None,
        }
    return {
        "entry_count": payload.get("entry_count", 0),
        "latest_turn_phase": payload.get("latest_turn_phase"),
        "latest_last_turn_result": payload.get("latest_last_turn_result"),
        "latest_summary": payload.get("latest_summary"),
    }


def build_report(
    *,
    state_payload: Mapping[str, Any],
    report_path: Path,
) -> dict[str, Any]:
    """Build one raw report from the persisted parallel-validation state."""

    state = _mapping(state_payload, context="state_payload")
    authorities = _mapping(state.get("authorities", {}), context="authorities")
    inspect_result = (
        _mapping(state.get("inspect_result"), context="inspect_result")
        if isinstance(state.get("inspect_result"), Mapping)
        else None
    )
    gateway_result = (
        _mapping(state.get("gateway_result"), context="gateway_result")
        if isinstance(state.get("gateway_result"), Mapping)
        else None
    )
    headless_result = (
        _mapping(state.get("headless_result"), context="headless_result")
        if isinstance(state.get("headless_result"), Mapping)
        else None
    )
    stop_result = (
        _mapping(state.get("stop_result"), context="stop_result")
        if isinstance(state.get("stop_result"), Mapping)
        else None
    )
    shared_agent = _mapping(state.get("shared_agent", {}), context="shared_agent")
    headless_agent_raw = state.get("headless_agent")
    headless_agent = dict(headless_agent_raw) if isinstance(headless_agent_raw, Mapping) else None

    authority_summary: dict[str, Any] = {}
    for authority_name in ("old_server", "passive_server"):
        authority_payload = authorities.get(authority_name)
        if isinstance(authority_payload, Mapping):
            authority_summary[authority_name] = {
                "api_base_url": authority_payload.get("api_base_url"),
                "houmao_service": authority_payload.get("houmao_service"),
                "pid": authority_payload.get("pid"),
                "health_status": authority_payload.get("health", {}).get("status")
                if isinstance(authority_payload.get("health"), Mapping)
                else None,
            }

    report = {
        "pack": "passive-server-parallel-validation-demo-pack",
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "repo_root": state.get("repo_root"),
        "pack_dir": state.get("pack_dir"),
        "run_root": state.get("run_root"),
        "provider": state.get("provider"),
        "tool": state.get("tool"),
        "agent_profile": state.get("agent_profile"),
        "active": bool(state.get("active")),
        "steps": dict(state.get("steps", {})),
        "preflight": {
            "checked_executables": sorted(
                dict(state.get("preflight", {})).get("executables", {}).keys()
                if isinstance(dict(state.get("preflight", {})).get("executables"), Mapping)
                else []
            ),
            "missing": list(dict(state.get("preflight", {})).get("missing", [])),
            "ports": dict(dict(state.get("config", {})).get("ports", {})),
        },
        "authorities": authority_summary,
        "shared_agent": {
            "agent_id": shared_agent.get("agent_id"),
            "agent_name": shared_agent.get("agent_name"),
            "tmux_session_name": shared_agent.get("tmux_session_name"),
            "manifest_path": shared_agent.get("manifest_path"),
        },
        "headless_agent": (
            None
            if headless_agent is None
            else {
                "agent_id": headless_agent.get("agent_id"),
                "agent_name": headless_agent.get("agent_name"),
                "manifest_path": headless_agent.get("manifest_path"),
            }
        ),
        "phases": {
            "inspect": {
                "status": _phase_status(inspect_result),
                "list_visibility_ok": None
                if inspect_result is None
                else inspect_result.get("list_ok"),
                "resolve_visibility_ok": None
                if inspect_result is None
                else inspect_result.get("resolve_ok"),
                "comparisons": None
                if inspect_result is None
                else inspect_result.get("comparison_summary"),
                "old_history": None
                if inspect_result is None
                else _history_summary(inspect_result.get("old_history_normalized")),
                "passive_history": None
                if inspect_result is None
                else _history_summary(inspect_result.get("passive_history_normalized")),
            },
            "gateway": {
                "status": _phase_status(gateway_result),
                "gateway_attached": None
                if gateway_result is None
                else gateway_result.get("gateway_attached"),
                "request_id": None
                if gateway_result is None
                else gateway_result.get("accepted", {}).get("request_id")
                if isinstance(gateway_result.get("accepted"), Mapping)
                else None,
                "old_progress_ok": None
                if gateway_result is None
                else gateway_result.get("old_progress_observed"),
                "passive_progress_ok": None
                if gateway_result is None
                else gateway_result.get("passive_progress_observed"),
            },
            "headless": {
                "status": _phase_status(headless_result),
                "launch_ok": None if headless_result is None else headless_result.get("launch_ok"),
                "old_visibility_ok": None
                if headless_result is None
                else headless_result.get("old_visibility_ok"),
            },
            "stop": {
                "status": _phase_status(stop_result),
                "passive_absent": None
                if stop_result is None
                else stop_result.get("passive_absent"),
                "old_absent": None if stop_result is None else stop_result.get("old_absent"),
                "registry_absent": None
                if stop_result is None
                else stop_result.get("registry_absent"),
                "tmux_absent": None if stop_result is None else stop_result.get("tmux_absent"),
            },
        },
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
