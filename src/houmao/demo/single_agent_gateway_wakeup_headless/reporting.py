"""Inspect, report, sanitize, and verify helpers for the headless wake-up demo."""

from __future__ import annotations

import difflib
import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from houmao.agents.mailbox_runtime_support import (
    mailbox_primary_skill_references,
    mailbox_skills_destination_for_tool,
    projected_mailbox_skill_document_path,
)
from houmao.agents.realm_controller.gateway_storage import read_gateway_notifier_audit_records

from .models import MANAGED_PROJECT_METADATA_NAME, DemoState, REPORT_SCHEMA_VERSION, utc_now_iso

_ABSOLUTE_PATH_PATTERN = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
_RUN_ID_PATTERN = re.compile(r"single-agent-gateway-wakeup-headless-\d{8}T\d{6}Z-[a-f0-9]{8}")
_MESSAGE_ID_PATTERN = re.compile(r"msg-\d{8}T\d{6}Z-[a-f0-9]{32}")
_DELIVERY_SUBJECT_PATTERN = re.compile(
    r"^(Single-agent gateway wake-up headless demo) [a-f0-9]{8}$"
)


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


def collect_headless_runtime_snapshot(
    *,
    state: DemoState,
    agent_show: dict[str, Any] | None,
    agent_state: dict[str, Any] | None,
) -> dict[str, Any]:
    """Collect headless-runtime detail plus durable turn-artifact evidence."""

    show_payload = agent_show if isinstance(agent_show, dict) else {}
    state_payload = agent_state if isinstance(agent_state, dict) else {}
    detail_payload = show_payload.get("detail")
    detail = (
        dict(detail_payload)
        if isinstance(detail_payload, dict) and detail_payload.get("transport") == "headless"
        else None
    )
    summary_payload = show_payload.get("summary_state")
    summary_state = dict(summary_payload) if isinstance(summary_payload, dict) else {}
    last_turn = None
    for candidate in (
        None if detail is None else detail.get("last_turn"),
        state_payload.get("last_turn"),
        summary_state.get("last_turn"),
    ):
        if isinstance(candidate, dict):
            last_turn = dict(candidate)
            break

    selected_turn_id = None
    if last_turn is not None:
        candidate_turn_id = str(last_turn.get("turn_id") or "").strip()
        if candidate_turn_id:
            selected_turn_id = candidate_turn_id

    turn_artifacts_root = state.headless_turn_artifacts_root
    latest_turn_dir: Path | None = None
    if selected_turn_id is not None:
        candidate_dir = (turn_artifacts_root / selected_turn_id).resolve()
        if candidate_dir.is_dir():
            latest_turn_dir = candidate_dir
    if latest_turn_dir is None and turn_artifacts_root.is_dir():
        directories = sorted(
            [candidate for candidate in turn_artifacts_root.iterdir() if candidate.is_dir()],
            reverse=True,
        )
        if directories:
            latest_turn_dir = directories[0].resolve()
            if selected_turn_id is None:
                selected_turn_id = latest_turn_dir.name

    stdout_path = None if latest_turn_dir is None else (latest_turn_dir / "stdout.jsonl").resolve()
    stderr_path = None if latest_turn_dir is None else (latest_turn_dir / "stderr.log").resolve()
    exitcode_path = None if latest_turn_dir is None else (latest_turn_dir / "exitcode").resolve()
    stdout_present = stdout_path is not None and stdout_path.is_file()
    stderr_present = stderr_path is not None and stderr_path.is_file()
    exitcode_present = exitcode_path is not None and exitcode_path.is_file()
    artifact_returncode = _read_turn_exitcode(exitcode_path) if exitcode_present else None
    artifact_completed_at_utc = (
        _isoformat_from_mtime(exitcode_path)
        if exitcode_present and exitcode_path is not None
        else None
    )
    artifact_completion_source = (
        _completion_source_from_stdout(stdout_path)
        if stdout_present and stdout_path is not None
        else None
    )
    detail_last_turn_status = None if detail is None else detail.get("last_turn_status")
    detail_last_turn_completed_at_utc = (
        None if detail is None else detail.get("last_turn_completed_at_utc")
    )
    detail_last_turn_completion_source = (
        None if detail is None else detail.get("last_turn_completion_source")
    )
    detail_last_turn_returncode = None if detail is None else detail.get("last_turn_returncode")
    detail_last_turn_result = None if last_turn is None else last_turn.get("result")

    effective_last_turn_status = detail_last_turn_status
    if artifact_returncode is not None:
        effective_last_turn_status = "completed" if artifact_returncode == 0 else "failed"

    effective_last_turn_completed_at_utc = detail_last_turn_completed_at_utc
    if artifact_completed_at_utc is not None:
        effective_last_turn_completed_at_utc = artifact_completed_at_utc

    effective_last_turn_completion_source = detail_last_turn_completion_source
    if (
        effective_last_turn_completion_source in {None, ""}
        and artifact_completion_source is not None
    ):
        effective_last_turn_completion_source = artifact_completion_source

    effective_last_turn_returncode = detail_last_turn_returncode
    if artifact_returncode is not None:
        effective_last_turn_returncode = artifact_returncode

    effective_last_turn_result = detail_last_turn_result
    if artifact_returncode is not None:
        effective_last_turn_result = "success" if artifact_returncode == 0 else "known_failure"

    effective_can_accept_prompt_now = (
        False if detail is None else bool(detail.get("can_accept_prompt_now"))
    )
    effective_interruptible = False if detail is None else bool(detail.get("interruptible"))
    if effective_last_turn_status in {"completed", "failed"}:
        effective_can_accept_prompt_now = True
        effective_interruptible = False

    return {
        "detail_transport": None if detail is None else detail.get("transport"),
        "detail_runtime_resumable": False
        if detail is None
        else bool(detail.get("runtime_resumable")),
        "detail_tmux_session_live": False
        if detail is None
        else bool(detail.get("tmux_session_live")),
        "detail_can_accept_prompt_now": effective_can_accept_prompt_now,
        "detail_interruptible": effective_interruptible,
        "last_turn_result": effective_last_turn_result,
        "last_turn_turn_id": None if last_turn is None else last_turn.get("turn_id"),
        "last_turn_turn_index": None if last_turn is None else last_turn.get("turn_index"),
        "last_turn_status": effective_last_turn_status,
        "last_turn_completed_at_utc": effective_last_turn_completed_at_utc,
        "last_turn_completion_source": effective_last_turn_completion_source,
        "last_turn_returncode": effective_last_turn_returncode,
        "last_turn_history_summary": (
            None if detail is None else detail.get("last_turn_history_summary")
        ),
        "last_turn_error": None if detail is None else detail.get("last_turn_error"),
        "turn_artifacts_root": str(turn_artifacts_root),
        "turn_artifacts_root_present": turn_artifacts_root.is_dir(),
        "latest_turn_id": selected_turn_id,
        "latest_turn_dir": None if latest_turn_dir is None else str(latest_turn_dir),
        "latest_turn_dir_present": latest_turn_dir is not None and latest_turn_dir.is_dir(),
        "latest_turn_stdout_path": None if stdout_path is None else str(stdout_path),
        "latest_turn_stdout_present": stdout_present,
        "latest_turn_stdout_non_empty": (
            stdout_present and stdout_path is not None and stdout_path.stat().st_size > 0
        ),
        "latest_turn_stderr_path": None if stderr_path is None else str(stderr_path),
        "latest_turn_stderr_present": stderr_present,
        "latest_turn_exitcode_path": None if exitcode_path is None else str(exitcode_path),
        "latest_turn_exitcode_present": exitcode_present,
    }


def _read_turn_exitcode(path: Path) -> int | None:
    """Read one persisted headless turn exit code when available."""

    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _completion_source_from_stdout(path: Path) -> str | None:
    """Extract one completion-source hint from persisted stdout events."""

    try:
        for line in reversed(path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            payload = _require_mapping(json.loads(line), context=str(path))
            nested_payload = payload.get("payload")
            if not isinstance(nested_payload, dict):
                continue
            value = nested_payload.get("completion_source")
            if isinstance(value, str) and value.strip():
                return value.strip()
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return None


def _isoformat_from_mtime(path: Path) -> str:
    """Return one UTC ISO-8601 timestamp from filesystem mtime."""

    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat(timespec="seconds")


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
    headless_runtime = collect_headless_runtime_snapshot(
        state=state,
        agent_show=agent_show,
        agent_state=agent_state,
    )
    runtime_skill_destination_dir = state.brain_home_path / mailbox_skills_destination_for_tool(
        state.selected_tool
    )
    runtime_skill_document_paths = [
        projected_mailbox_skill_document_path(
            tool=state.selected_tool,
            home_path=state.brain_home_path,
            skill_reference=skill_reference,
        )
        for skill_reference in mailbox_primary_skill_references(tool=state.selected_tool)
    ]
    runtime_mailbox_skill_surface_present = all(
        skill_path.is_file() for skill_path in runtime_skill_document_paths
    )
    project_mailbox_skill_mirror_dir = state.project_workdir / "skills" / "mailbox"
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
            "headless": headless_runtime,
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
            "runtime_skill_destination_dir": str(runtime_skill_destination_dir),
            "runtime_mailbox_skill_surface_present": runtime_mailbox_skill_surface_present,
            "project_mailbox_skill_mirror_dir": str(project_mailbox_skill_mirror_dir),
            "project_mailbox_skill_mirror_present": project_mailbox_skill_mirror_dir.is_dir(),
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
    headless_runtime = inspect_snapshot["managed_agent"]["headless"] or {}
    deliveries = state.deliveries
    canonical_delivery = deliveries[0] if deliveries else None

    full_messages = actor_mail_check.get("messages", [])
    delivered_message_visible = False
    delivered_message_read = False
    if canonical_delivery is not None:
        expected_message_ref = (
            canonical_delivery.message_ref or f"filesystem:{canonical_delivery.message_id}"
        )
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
    if not bool(inspect_snapshot["project"]["runtime_mailbox_skill_surface_present"]):
        failures.append("runtime-owned mailbox skill surface is missing")
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
    if headless_runtime.get("detail_transport") != "headless":
        failures.append("managed-agent detail did not report headless transport")
    if headless_runtime.get("last_turn_result") != "success":
        failures.append("managed-agent last turn did not complete successfully")
    if headless_runtime.get("last_turn_status") != "completed":
        failures.append("managed-agent detail did not record a completed headless turn")
    if not bool(headless_runtime.get("turn_artifacts_root_present")):
        failures.append("headless turn-artifacts root is missing")
    if not bool(headless_runtime.get("latest_turn_dir_present")):
        failures.append("latest headless turn-artifact directory is missing")
    if not (
        bool(headless_runtime.get("latest_turn_stdout_present"))
        or bool(headless_runtime.get("latest_turn_exitcode_present"))
    ):
        failures.append("latest headless turn artifacts are missing stdout and exitcode evidence")
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
    if (
        canonical_delivery is not None
        and structural_message.get("message_id") != canonical_delivery.message_id
    ):
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
        "headless_runtime_evidence": {
            "detail_transport": headless_runtime.get("detail_transport"),
            "detail_runtime_resumable": bool(headless_runtime.get("detail_runtime_resumable")),
            "detail_tmux_session_live": bool(headless_runtime.get("detail_tmux_session_live")),
            "detail_can_accept_prompt_now": bool(
                headless_runtime.get("detail_can_accept_prompt_now")
            ),
            "last_turn_result": headless_runtime.get("last_turn_result"),
            "last_turn_status": headless_runtime.get("last_turn_status"),
            "last_turn_completed_at_utc_present": bool(
                headless_runtime.get("last_turn_completed_at_utc")
            ),
            "last_turn_completion_source_present": bool(
                headless_runtime.get("last_turn_completion_source")
            ),
            "last_turn_returncode_zero": headless_runtime.get("last_turn_returncode") in {None, 0},
            "turn_artifacts_root_present": bool(
                headless_runtime.get("turn_artifacts_root_present")
            ),
            "latest_turn_dir_present": bool(headless_runtime.get("latest_turn_dir_present")),
            "latest_turn_stdout_present": bool(headless_runtime.get("latest_turn_stdout_present")),
            "latest_turn_stdout_non_empty": bool(
                headless_runtime.get("latest_turn_stdout_non_empty")
            ),
            "latest_turn_exitcode_present": bool(
                headless_runtime.get("latest_turn_exitcode_present")
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
            "runtime_mailbox_skill_surface_present": bool(
                inspect_snapshot["project"]["runtime_mailbox_skill_surface_present"]
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
        if key == "subject":
            subject_match = _DELIVERY_SUBJECT_PATTERN.match(payload)
            if subject_match is not None:
                return f"{subject_match.group(1)} <RUN_ID>"
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
    pack_root = repo_root / "scripts" / "demo" / "single-agent-gateway-wakeup-headless"
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
