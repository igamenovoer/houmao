"""Inspect, report, sanitize, and verify helpers for the gateway wake-up demo pack."""

from __future__ import annotations

import difflib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from houmao.agents.realm_controller.gateway_storage import read_gateway_notifier_audit_records

from .models import DemoState, REPORT_SCHEMA_VERSION, utc_now_iso

_ABSOLUTE_PATH_PATTERN = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
_RUN_ID_PATTERN = re.compile(r"gateway-mail-wakeup-\d{8}T\d{6}Z-[a-f0-9]{8}")
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
    """Reduce raw notifier audit rows to stable outcome-summary evidence."""

    outcomes = {
        str(row.get("outcome")) for row in rows if row.get("outcome") not in {None, "empty"}
    }
    return {
        "row_count": len(rows),
        "observed_outcomes": sorted(outcomes),
        "has_enqueued": any(row.get("outcome") == "enqueued" for row in rows),
        "has_poll_error": any(row.get("outcome") == "poll_error" for row in rows),
        "max_unread_count": max((int(row.get("unread_count", 0)) for row in rows), default=0),
        "enqueued_request_id_present": any(
            row.get("enqueued_request_id") is not None
            for row in rows
            if row.get("outcome") == "enqueued"
        ),
    }


def read_queue_state(gateway_root: Path) -> dict[str, Any]:
    """Load notifier-related queue and event evidence from the gateway root."""

    queue_path = gateway_root / "queue.sqlite"
    events_path = gateway_root / "events.jsonl"
    request_rows: list[dict[str, Any]] = []
    if queue_path.is_file():
        with sqlite3.connect(queue_path) as connection:
            rows = connection.execute(
                """
                SELECT request_id, request_kind, state, accepted_at_utc, started_at_utc, finished_at_utc
                FROM gateway_requests
                WHERE request_kind = 'mail_notifier_prompt'
                ORDER BY accepted_at_utc ASC
                """
            ).fetchall()
        request_rows = [
            {
                "request_id": str(row[0]),
                "request_kind": str(row[1]),
                "state": str(row[2]),
                "accepted_at_utc": None if row[3] is None else str(row[3]),
                "started_at_utc": None if row[4] is None else str(row[4]),
                "finished_at_utc": None if row[5] is None else str(row[5]),
            }
            for row in rows
        ]

    events: list[dict[str, Any]] = []
    if events_path.is_file():
        events = [
            _require_mapping(json.loads(line), context=str(events_path))
            for line in events_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    return {
        "request_rows": request_rows,
        "event_kinds": sorted({str(event.get("kind")) for event in events}),
        "has_notifier_request": bool(request_rows),
        "has_completed_notifier_request": any(
            row.get("state") == "completed" for row in request_rows
        ),
    }


def build_inspect_snapshot(
    *,
    state: DemoState,
    agent_show: dict[str, Any] | None,
    agent_state: dict[str, Any] | None,
    gateway_status: dict[str, Any] | None,
    notifier_status: dict[str, Any] | None,
    mailbox_snapshot: dict[str, Any],
    output_payload: dict[str, Any],
) -> dict[str, Any]:
    """Build one raw inspect snapshot for the current run."""

    audit_rows = read_notifier_audit_rows(state)
    queue_state = read_queue_state(state.gateway_root)
    visible_mailbox_dir = state.project_workdir / "skills" / "mailbox"
    return {
        "generated_at_utc": utc_now_iso(),
        "run_id": state.run_id,
        "selected_tool": state.selected_tool,
        "provider": state.provider,
        "selector": state.selector,
        "output_root": str(state.output_root),
        "session": {
            "tracked_agent_id": state.tracked_agent_id,
            "agent_name": state.agent_name,
            "agent_id": state.agent_id,
            "tmux_session_name": state.tmux_session_name,
            "terminal_id": state.terminal_id,
            "session_manifest_path": str(state.session_manifest_path),
            "session_root": str(state.session_root),
            "active": state.active,
        },
        "managed_agent": {
            "show": agent_show,
            "state": agent_state,
        },
        "gateway": {
            "status": gateway_status,
            "notifier": notifier_status,
            "audit_summary": summarize_notifier_audit_rows(audit_rows),
            "audit_rows": audit_rows,
            "queue_state": queue_state,
        },
        "mailbox": mailbox_snapshot,
        "output_file": output_payload,
        "project": {
            "project_workdir": str(state.project_workdir),
            "visible_mailbox_dir": str(visible_mailbox_dir),
            "visible_mailbox_skill_surface_present": visible_mailbox_dir.is_dir(),
            "managed_project_metadata_present": (
                state.project_workdir / ".houmao-demo-project.json"
            ).is_file(),
        },
        "ownership": {
            "output_root_pack_local": _path_within_pack_root(
                state.output_root, repo_root=state.repo_root
            ),
            "mailbox_root_within_output_root": _path_within_root(
                state.output_root, state.output_root / "mailbox"
            ),
            "output_file_within_output_root": _path_within_root(
                state.output_root, state.output_file_path
            ),
        },
        "deliveries": [
            {
                "delivery_index": delivery.delivery_index,
                "subject": delivery.subject,
                "message_id": delivery.message_id,
                "thread_id": delivery.thread_id,
                "created_at_utc": delivery.created_at_utc,
                "unread_observed_at_utc": delivery.unread_observed_at_utc,
                "read_observed_at_utc": delivery.read_observed_at_utc,
                "mailbox_state_source": delivery.mailbox_state_source,
                "processed": delivery.processed,
                "evidence_snapshot_path": (
                    None
                    if delivery.evidence_snapshot_path is None
                    else str(delivery.evidence_snapshot_path)
                ),
                "evidence_tail_path": (
                    None
                    if delivery.evidence_tail_path is None
                    else str(delivery.evidence_tail_path)
                ),
            }
            for delivery in state.deliveries
        ],
    }


def build_report_snapshot(
    *,
    state: DemoState,
    inspect_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Build the stable verification report from one inspect snapshot."""

    mailbox_snapshot = inspect_snapshot["mailbox"]
    gateway_payload = inspect_snapshot["gateway"]
    queue_state = gateway_payload["queue_state"]
    audit_summary = gateway_payload["audit_summary"]
    notifier_status = gateway_payload["notifier"] or {}
    deliveries = state.deliveries
    canonical_delivery = deliveries[0] if deliveries else None
    processed_message_read = canonical_delivery is not None and canonical_delivery.processed

    failures: list[str] = []
    if state.delivery_count != 1:
        failures.append(f"expected exactly 1 injected message, found {state.delivery_count}")
    if state.processed_delivery_count != 1:
        failures.append(
            f"expected exactly 1 processed message, found {state.processed_delivery_count}"
        )
    final_unread = int(mailbox_snapshot.get("unread_count", 0))
    if final_unread != 0:
        failures.append(f"expected final unread count 0, found {final_unread}")
    if not bool(inspect_snapshot["ownership"]["output_root_pack_local"]):
        failures.append("output root is not pack-local")
    if not bool(inspect_snapshot["ownership"]["mailbox_root_within_output_root"]):
        failures.append("mailbox root is not contained inside the selected output root")
    if not bool(inspect_snapshot["ownership"]["output_file_within_output_root"]):
        failures.append("output file is not contained inside the selected output root")
    if not bool(inspect_snapshot["project"]["visible_mailbox_skill_surface_present"]):
        failures.append("project-local mailbox skill surface is missing")
    if not bool(inspect_snapshot["project"]["managed_project_metadata_present"]):
        failures.append("managed project metadata is missing")
    if not bool(notifier_status.get("enabled")):
        failures.append("gateway notifier was not enabled")
    if not bool(audit_summary.get("has_enqueued")):
        failures.append("gateway notifier never enqueued mail work")
    if bool(audit_summary.get("has_poll_error")):
        failures.append("gateway notifier recorded poll errors")
    if not bool(queue_state.get("has_notifier_request")):
        failures.append("gateway queue never recorded a notifier request")
    if not bool(queue_state.get("has_completed_notifier_request")):
        failures.append("gateway queue never completed a notifier request")
    if not processed_message_read:
        failures.append("the canonical delivered message was not observed as read")
    output_payload = inspect_snapshot["output_file"]
    if not bool(output_payload.get("exists")):
        failures.append("output file was not created")
    if not bool(output_payload.get("timestamp_like")):
        failures.append("output file does not contain an RFC3339 timestamp")
    if not bool(output_payload.get("modified_after_delivery")):
        failures.append("output file timestamp predates the mailbox delivery")

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generated_at_utc": utc_now_iso(),
        "config": {
            "selected_tool": state.selected_tool,
            "provider": state.provider,
            "selector": state.selector,
            "notifier_interval_seconds": state.notifier_interval_seconds,
        },
        "counts": {
            "delivery_count": state.delivery_count,
            "processed_delivery_count": state.processed_delivery_count,
            "final_unread_count": final_unread,
        },
        "ownership": inspect_snapshot["ownership"],
        "session": {
            "tracked_agent_id": state.tracked_agent_id,
            "agent_name": state.agent_name,
            "session_manifest_path": str(state.session_manifest_path),
        },
        "gateway_evidence": {
            "attached": gateway_payload["status"] is not None,
            "notifier_enabled": bool(notifier_status.get("enabled")),
            "enqueued_mail_work": bool(audit_summary.get("has_enqueued")),
            "poll_errors_present": bool(audit_summary.get("has_poll_error")),
            "queue_has_notifier_request": bool(queue_state.get("has_notifier_request")),
            "queue_completed_notifier_request": bool(
                queue_state.get("has_completed_notifier_request")
            ),
        },
        "mailbox_evidence": {
            "state_source": str(mailbox_snapshot.get("state_source", "unknown")),
            "message_count": int(mailbox_snapshot.get("message_count", 0)),
            "final_unread_count": final_unread,
            "processed_message_read": processed_message_read,
        },
        "output_evidence": {
            "exists": bool(output_payload.get("exists")),
            "timestamp_like": bool(output_payload.get("timestamp_like")),
            "modified_after_delivery": bool(output_payload.get("modified_after_delivery")),
        },
        "project_evidence": {
            "managed_project_metadata_present": bool(
                inspect_snapshot["project"]["managed_project_metadata_present"]
            ),
            "visible_mailbox_skill_surface_present": bool(
                inspect_snapshot["project"]["visible_mailbox_skill_surface_present"]
            ),
        },
        "deliveries": [
            {
                "delivery_index": delivery.delivery_index,
                "subject": delivery.subject,
                "message_id": delivery.message_id,
                "thread_id": delivery.thread_id,
                "processed": delivery.processed,
            }
            for delivery in deliveries
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
        if key == "provider":
            return "<PROVIDER>"
        if key == "generated_at_utc" or (key is not None and key.endswith("_at_utc")):
            return "<TIMESTAMP>"
        if key in {"tracked_agent_id"}:
            return "<TRACKED_AGENT_ID>"
        if key in {"agent_name"}:
            return "<AGENT_NAME>"
        if key in {"message_id"}:
            return "<MESSAGE_ID>"
        if key in {"thread_id", "run_id"}:
            return "<THREAD_ID>" if key == "thread_id" else "<RUN_ID>"
        if key is not None and (
            key.endswith("_path") or key.endswith("_root") or key.endswith("_dir")
        ):
            return f"<{key.upper()}>"
        if _ABSOLUTE_PATH_PATTERN.match(payload):
            return "<ABSOLUTE_PATH>"
        normalized = _RUN_ID_PATTERN.sub("<RUN_ID>", payload)
        normalized = _MESSAGE_ID_PATTERN.sub("<MESSAGE_ID>", normalized)
        return normalized
    return payload


def validate_report_contract(report: dict[str, Any]) -> None:
    """Require the stable report contract to represent a successful canonical run."""

    outcome = report.get("outcome", {})
    failures = outcome.get("failures", [])
    if outcome.get("status") != "complete" or failures:
        raise ValueError(f"report contract failed: {failures}")
    counts = report["counts"]
    if counts["delivery_count"] != 1:
        raise ValueError("report contract failed: expected exactly 1 injected message")
    if counts["processed_delivery_count"] != 1:
        raise ValueError("report contract failed: expected exactly 1 processed message")
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
            expected_text, actual_text, fromfile="expected", tofile="actual", lineterm=""
        )
    )
    raise ValueError(f"sanitized report mismatch\n{diff}")


def _path_within_pack_root(path: Path, *, repo_root: Path) -> bool:
    pack_root = repo_root / "scripts" / "demo" / "gateway-mail-wakeup-demo-pack"
    return _path_within_root(pack_root, path)


def _path_within_root(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _require_mapping(value: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a JSON object")
    return value
