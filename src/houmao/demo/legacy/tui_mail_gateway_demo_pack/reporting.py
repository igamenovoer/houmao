"""Inspect, report, sanitize, and verify helpers for the TUI mail gateway demo pack."""

from __future__ import annotations

import difflib
import json
import re
from typing import Any

from houmao.agents.realm_controller.gateway_storage import read_gateway_notifier_audit_records

from .models import DemoState, REPORT_SCHEMA_VERSION, utc_now_iso

_ABSOLUTE_PATH_PATTERN = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
_RUN_ID_PATTERN = re.compile(r"tui-mail-gateway-\d{8}T\d{6}Z-[a-f0-9]{8}")
_MESSAGE_ID_PATTERN = re.compile(r"msg-\d{8}T\d{6}Z-[a-f0-9]{32}")


def read_notifier_audit_rows(state: DemoState) -> list[dict[str, Any]]:
    """Return raw notifier audit rows for the persisted session when available."""

    queue_path = state.gateway_root / "queue.sqlite"
    if not queue_path.is_file():
        return []
    records = read_gateway_notifier_audit_records(queue_path)
    return [
        {
            "audit_id": record.audit_id,
            "poll_time_utc": record.poll_time_utc,
            "unread_count": record.unread_count,
            "request_admission": record.request_admission,
            "active_execution": record.active_execution,
            "queue_depth": record.queue_depth,
            "outcome": record.outcome,
            "enqueued_request_id": record.enqueued_request_id,
            "detail": record.detail,
            "unread_summary": [
                {
                    "message_ref": item.message_ref,
                    "thread_ref": item.thread_ref,
                    "created_at_utc": item.created_at_utc,
                    "subject": item.subject,
                }
                for item in record.unread_summary
            ],
        }
        for record in records
    ]


def summarize_notifier_audit_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a stable summary of notifier audit behavior."""

    outcomes = [str(row.get("outcome")) for row in rows]
    return {
        "row_count": len(rows),
        "enqueued_mail_work": any(outcome == "enqueued" for outcome in outcomes),
        "poll_errors_present": any(outcome == "poll_error" for outcome in outcomes),
        "last_outcome": outcomes[-1] if outcomes else None,
    }


def build_inspect_snapshot(
    *,
    state: DemoState,
    gateway_status: dict[str, Any],
    notifier_status: dict[str, Any],
    mailbox_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Build one raw inspect snapshot for the current run."""

    audit_rows = read_notifier_audit_rows(state)
    return {
        "generated_at_utc": utc_now_iso(),
        "run_id": state.run_id,
        "selected_tool": state.selected_tool,
        "session": {
            "agent_identity": state.agent_identity,
            "agent_name": state.agent_name,
            "agent_id": state.agent_id,
            "tmux_session_name": state.tmux_session_name,
            "terminal_id": state.terminal_id,
            "session_manifest_path": str(state.session_manifest_path),
            "session_root": str(state.session_root),
            "active": state.active,
        },
        "gateway": {
            "status": gateway_status,
            "notifier": notifier_status,
            "audit_summary": summarize_notifier_audit_rows(audit_rows),
            "audit_rows": audit_rows,
        },
        "mailbox": mailbox_snapshot,
        "harness": {
            "cadence_seconds": state.cadence_seconds,
            "turn_limit": state.turn_limit,
            "delivery_count": state.delivery_count,
            "processed_turn_count": state.processed_turn_count,
            "turns": [
                {
                    "turn_index": turn.turn_index,
                    "subject": turn.subject,
                    "message_id": turn.message_id,
                    "thread_id": turn.thread_id,
                    "delivered_at_utc": turn.delivered_at_utc,
                    "unread_observed_at_utc": turn.unread_observed_at_utc,
                    "read_observed_at_utc": turn.read_observed_at_utc,
                    "mailbox_state_source": turn.mailbox_state_source,
                    "evidence_snapshot_path": (
                        None
                        if turn.evidence_snapshot_path is None
                        else str(turn.evidence_snapshot_path)
                    ),
                    "evidence_tail_path": (
                        None if turn.evidence_tail_path is None else str(turn.evidence_tail_path)
                    ),
                }
                for turn in state.turns
            ],
        },
    }


def build_report_snapshot(
    *,
    state: DemoState,
    inspect_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Build the stable verification report from one inspect snapshot."""

    mailbox_snapshot = inspect_snapshot["mailbox"]
    gateway_payload = inspect_snapshot["gateway"]
    audit_summary = gateway_payload["audit_summary"]
    turns = state.turns
    snapshot_count = sum(1 for turn in turns if turn.evidence_snapshot_path is not None)
    tail_count = sum(1 for turn in turns if turn.evidence_tail_path is not None)
    failures: list[str] = []
    if state.delivery_count != state.turn_limit:
        failures.append(
            f"expected {state.turn_limit} injected messages, found {state.delivery_count}"
        )
    if state.processed_turn_count != state.turn_limit:
        failures.append(
            f"expected {state.turn_limit} processed turns, found {state.processed_turn_count}"
        )
    final_unread = int(mailbox_snapshot.get("unread_count", 0))
    if final_unread != 0:
        failures.append(f"expected final unread count 0, found {final_unread}")
    if snapshot_count != state.turn_limit:
        failures.append(f"expected {state.turn_limit} tmux snapshots, found {snapshot_count}")
    if tail_count != state.turn_limit:
        failures.append(f"expected {state.turn_limit} tmux tails, found {tail_count}")
    if not bool(gateway_payload["notifier"].get("enabled")):
        failures.append("gateway notifier was not enabled")
    if not bool(audit_summary.get("enqueued_mail_work")):
        failures.append("gateway notifier never enqueued mail work")
    if bool(audit_summary.get("poll_errors_present")):
        failures.append("gateway notifier recorded poll errors")

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generated_at_utc": utc_now_iso(),
        "config": {
            "selected_tool": state.selected_tool,
            "cadence_seconds": state.cadence_seconds,
            "turn_limit": state.turn_limit,
        },
        "counts": {
            "injected_messages": state.delivery_count,
            "processed_turns": state.processed_turn_count,
            "final_unread_count": final_unread,
        },
        "session": {
            "agent_identity": state.agent_identity,
            "tmux_session_name": state.tmux_session_name,
            "session_manifest_path": str(state.session_manifest_path),
        },
        "gateway_evidence": {
            "notifier_enabled": bool(gateway_payload["notifier"].get("enabled")),
            "enqueued_mail_work": bool(audit_summary.get("enqueued_mail_work")),
            "poll_errors_present": bool(audit_summary.get("poll_errors_present")),
        },
        "mailbox_evidence": {
            "message_count": int(mailbox_snapshot.get("message_count", 0)),
            "unread_count": final_unread,
            "state_source": str(mailbox_snapshot.get("state_source", "unknown")),
        },
        "human_review_evidence": {
            "snapshot_count": snapshot_count,
            "tail_count": tail_count,
        },
        "turns": [
            {
                "turn_index": turn.turn_index,
                "message_id": turn.message_id,
                "thread_id": turn.thread_id,
                "processed": turn.processed,
                "snapshot_present": turn.evidence_snapshot_path is not None,
                "tail_present": turn.evidence_tail_path is not None,
            }
            for turn in turns
        ],
        "outcome": {
            "status": "complete" if not failures else "incomplete",
            "failures": failures,
        },
    }


def sanitize_report(payload: Any, *, key: str | None = None) -> Any:
    """Sanitize one report payload for reproducible snapshot comparison."""

    if isinstance(payload, dict):
        return {
            child_key: sanitize_report(child_value, key=child_key)
            for child_key, child_value in payload.items()
        }
    if isinstance(payload, list):
        return [sanitize_report(item, key=key) for item in payload]
    if isinstance(payload, str):
        if key == "selected_tool":
            return "<TOOL>"
        if key == "generated_at_utc" or (key is not None and key.endswith("_at_utc")):
            return "<TIMESTAMP>"
        if key in {"agent_identity", "tmux_session_name"}:
            return f"<{key.upper()}>"
        if key in {"message_id"}:
            return "<MESSAGE_ID>"
        if key in {"thread_id", "run_id"}:
            return "<THREAD_ID>" if key == "thread_id" else "<RUN_ID>"
        if key is not None and (key.endswith("_path") or key.endswith("_root")):
            return f"<{key.upper()}>"
        if _ABSOLUTE_PATH_PATTERN.match(payload):
            return "<ABSOLUTE_PATH>"
        normalized = _RUN_ID_PATTERN.sub("<RUN_ID>", payload)
        normalized = _MESSAGE_ID_PATTERN.sub("<MESSAGE_ID>", normalized)
        return normalized
    return payload


def validate_report_contract(report: dict[str, Any]) -> None:
    """Require the stable report contract to represent a successful three-turn run."""

    outcome = report.get("outcome", {})
    failures = outcome.get("failures", [])
    if outcome.get("status") != "complete" or failures:
        raise ValueError(f"report contract failed: {failures}")
    counts = report["counts"]
    if counts["injected_messages"] != 3:
        raise ValueError("report contract failed: expected 3 injected messages")
    if counts["processed_turns"] != 3:
        raise ValueError("report contract failed: expected 3 processed turns")
    if counts["final_unread_count"] != 0:
        raise ValueError("report contract failed: final unread count must be 0")


def verify_sanitized_report(actual: Any, expected: Any) -> None:
    """Require the sanitized report to match the expected snapshot exactly."""

    if actual == expected:
        return
    actual_text = json.dumps(actual, indent=2, sort_keys=True).splitlines()
    expected_text = json.dumps(expected, indent=2, sort_keys=True).splitlines()
    diff = "\n".join(
        difflib.unified_diff(
            expected_text,
            actual_text,
            fromfile="expected",
            tofile="actual",
            lineterm="",
        )
    )
    raise ValueError(f"sanitized report mismatch:\n{diff}")
