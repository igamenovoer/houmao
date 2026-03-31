"""Inspect, report, sanitize, and verify helpers for the single-agent wake-up demo."""

from __future__ import annotations

import difflib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from houmao.agents.realm_controller.gateway_storage import read_gateway_notifier_audit_records

from .models import MANAGED_PROJECT_METADATA_NAME, DemoState, REPORT_SCHEMA_VERSION, utc_now_iso

_ABSOLUTE_PATH_PATTERN = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
_RUN_ID_PATTERN = re.compile(r"single-agent-mail-wakeup-\d{8}T\d{6}Z-[a-f0-9]{8}")
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
    specialist: dict[str, Any] | None,
    instance: dict[str, Any] | None,
    agent_show: dict[str, Any] | None,
    agent_state: dict[str, Any] | None,
    gateway_status: dict[str, Any] | None,
    notifier_status: dict[str, Any] | None,
    actor_mail_check: dict[str, Any],
    actor_mail_unread_check: dict[str, Any],
    project_mailbox_list: dict[str, Any] | None,
    project_mailbox_message: dict[str, Any] | None,
    output_payload: dict[str, Any],
) -> dict[str, Any]:
    """Build one raw inspect snapshot for the current run."""

    audit_rows = read_notifier_audit_rows(state)
    queue_state = read_queue_state(state.gateway_root)
    visible_mailbox_dir = state.project_workdir / "skills" / "mailbox"
    managed_project_metadata_path = state.project_workdir / MANAGED_PROJECT_METADATA_NAME
    return {
        "generated_at_utc": utc_now_iso(),
        "run_id": state.run_id,
        "selected_tool": state.selected_tool,
        "provider": state.provider,
        "setup_name": state.setup_name,
        "output_root": str(state.output_root),
        "session": {
            "tracked_agent_id": state.tracked_agent_id,
            "specialist_name": state.specialist_name,
            "agent_name": state.agent_name,
            "agent_id": state.agent_id,
            "tmux_session_name": state.tmux_session_name,
            "terminal_id": state.terminal_id,
            "session_manifest_path": str(state.session_manifest_path),
            "session_root": str(state.session_root),
            "active": state.active,
        },
        "specialist": specialist,
        "instance": instance,
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
        "actor_mail": {
            "check": actor_mail_check,
            "unread_check": actor_mail_unread_check,
        },
        "project_mailbox": {
            "list": project_mailbox_list,
            "message": project_mailbox_message,
        },
        "output_file": output_payload,
        "project": {
            "project_workdir": str(state.project_workdir),
            "overlay_root": str(state.overlay_root),
            "project_mailbox_root": str(state.project_mailbox_root),
            "visible_mailbox_dir": str(visible_mailbox_dir),
            "visible_mailbox_skill_surface_present": visible_mailbox_dir.is_dir(),
            "managed_project_metadata_path": str(managed_project_metadata_path),
            "managed_project_metadata_present": managed_project_metadata_path.is_file(),
        },
        "ownership": {
            "output_root_pack_local": _path_within_pack_root(
                state.output_root, repo_root=state.repo_root
            ),
            "project_root_within_output_root": _path_within_root(
                state.output_root, state.project_workdir
            ),
            "overlay_root_within_output_root": _path_within_root(
                state.output_root, state.overlay_root
            ),
            "runtime_root_within_output_root": _path_within_root(
                state.output_root, state.session_root
            ),
            "output_file_within_project_root": _path_within_root(
                state.project_workdir, state.output_file_path
            ),
        },
        "deliveries": [
            {
                "delivery_index": delivery.delivery_index,
                "subject": delivery.subject,
                "message_id": delivery.message_id,
                "thread_id": delivery.thread_id,
                "message_ref": delivery.message_ref,
                "created_at_utc": delivery.created_at_utc,
                "unread_observed_at_utc": delivery.unread_observed_at_utc,
                "completed_at_utc": delivery.completed_at_utc,
                "observation_source": delivery.observation_source,
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

    gateway_payload = inspect_snapshot["gateway"]
    queue_state = gateway_payload["queue_state"]
    audit_summary = gateway_payload["audit_summary"]
    notifier_status = gateway_payload["notifier"] or {}
    actor_mail_check = inspect_snapshot["actor_mail"]["check"]
    actor_mail_unread_check = inspect_snapshot["actor_mail"]["unread_check"]
    project_mailbox_list = inspect_snapshot["project_mailbox"]["list"] or {}
    project_mailbox_message = inspect_snapshot["project_mailbox"]["message"] or {}
    deliveries = state.deliveries
    canonical_delivery = deliveries[0] if deliveries else None

    full_messages = actor_mail_check.get("messages", [])
    delivered_message_visible = False
    delivered_message_read = False
    if canonical_delivery is not None:
        expected_message_ref = canonical_delivery.message_ref or f"filesystem:{canonical_delivery.message_id}"
        for message in full_messages:
            if not isinstance(message, dict):
                continue
            message_ref = str(message.get("message_ref", ""))
            if message_ref == expected_message_ref or message_ref.endswith(
                f":{canonical_delivery.message_id}"
            ):
                delivered_message_visible = True
                delivered_message_read = not bool(message.get("unread"))
                break

    structural_messages = project_mailbox_list.get("messages", [])
    structural_message_visible = any(
        isinstance(message, dict)
        and canonical_delivery is not None
        and str(message.get("message_id")) == canonical_delivery.message_id
        for message in structural_messages
    )
    structural_message = project_mailbox_message.get("message", {})

    failures: list[str] = []
    if state.delivery_count != 1:
        failures.append(f"expected exactly 1 injected message, found {state.delivery_count}")
    if state.processed_delivery_count != 1:
        failures.append(
            f"expected exactly 1 processed message, found {state.processed_delivery_count}"
        )
    final_unread = int(actor_mail_unread_check.get("unread_count", -1))
    if final_unread != 0:
        failures.append(f"expected final unread count 0, found {final_unread}")
    if not bool(inspect_snapshot["ownership"]["output_root_pack_local"]):
        failures.append("output root is not pack-local")
    if not bool(inspect_snapshot["ownership"]["project_root_within_output_root"]):
        failures.append("project root is not contained inside the selected output root")
    if not bool(inspect_snapshot["ownership"]["overlay_root_within_output_root"]):
        failures.append("overlay root is not contained inside the selected output root")
    if not bool(inspect_snapshot["ownership"]["runtime_root_within_output_root"]):
        failures.append("runtime session root is not contained inside the selected output root")
    if not bool(inspect_snapshot["ownership"]["output_file_within_project_root"]):
        failures.append("output file is not contained inside the copied project root")
    if not bool(inspect_snapshot["project"]["visible_mailbox_skill_surface_present"]):
        failures.append("project-local mailbox skill surface is missing")
    if not bool(inspect_snapshot["project"]["managed_project_metadata_present"]):
        failures.append("managed project metadata is missing")
    if inspect_snapshot["specialist"] is None:
        failures.append("specialist payload is missing")
    else:
        launch = inspect_snapshot["specialist"].get("launch", {})
        if launch.get("prompt_mode") != "unattended":
            failures.append("specialist launch prompt mode is not unattended")
    if inspect_snapshot["instance"] is None:
        failures.append("project easy instance payload is missing")
    if not bool(gateway_payload["status"]):
        failures.append("gateway status payload is missing")
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
    if not delivered_message_visible:
        failures.append("delivered message was not visible in actor-scoped mail check")
    if not delivered_message_read:
        failures.append("delivered message did not become read in actor-scoped mail check")
    output_payload = inspect_snapshot["output_file"]
    if not bool(output_payload.get("exists")):
        failures.append("output file was not created")
    if not bool(output_payload.get("matches_expected_content")):
        failures.append("output file content did not match the expected deterministic payload")
    if not bool(output_payload.get("modified_after_delivery")):
        failures.append("output file timestamp predates the mailbox delivery")
    if not structural_message_visible:
        failures.append("delivered message was not structurally visible in project mailbox list")
    if not bool(structural_message.get("canonical_path")):
        failures.append("project mailbox message payload is missing canonical_path")
    if not bool(structural_message.get("projection_path")):
        failures.append("project mailbox message payload is missing projection_path")
    if canonical_delivery is not None and structural_message.get("message_id") != canonical_delivery.message_id:
        failures.append("project mailbox message payload did not match the delivered message id")

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generated_at_utc": utc_now_iso(),
        "config": {
            "selected_tool": state.selected_tool,
            "provider": state.provider,
            "setup_name": state.setup_name,
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
            "specialist_name": state.specialist_name,
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
        "actor_mail_evidence": {
            "message_count": int(actor_mail_check.get("message_count", 0)),
            "final_unread_count": final_unread,
            "delivered_message_visible": delivered_message_visible,
            "delivered_message_read": delivered_message_read,
        },
        "structural_mailbox_evidence": {
            "message_count": len(structural_messages),
            "delivered_message_visible": structural_message_visible,
            "canonical_path_present": bool(structural_message.get("canonical_path")),
            "projection_path_present": bool(structural_message.get("projection_path")),
        },
        "output_evidence": {
            "exists": bool(output_payload.get("exists")),
            "matches_expected_content": bool(output_payload.get("matches_expected_content")),
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
        if key == "setup_name":
            return "<SETUP_NAME>"
        if key == "generated_at_utc" or (key is not None and key.endswith("_at_utc")):
            return "<TIMESTAMP>"
        if key in {"tracked_agent_id"}:
            return "<TRACKED_AGENT_ID>"
        if key in {"agent_name"}:
            return "<AGENT_NAME>"
        if key in {"specialist_name"}:
            return "<SPECIALIST_NAME>"
        if key in {"message_id"}:
            return "<MESSAGE_ID>"
        if key in {"thread_id", "run_id"}:
            return "<THREAD_ID>" if key == "thread_id" else "<RUN_ID>"
        if key in {"message_ref"}:
            return "<MESSAGE_REF>"
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
    pack_root = repo_root / "scripts" / "demo" / "single-agent-mail-wakeup"
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
