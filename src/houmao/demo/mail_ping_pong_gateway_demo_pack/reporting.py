"""Inspect, report, sanitize, and verify helpers for the demo pack."""

from __future__ import annotations

import difflib
import json
import re
from typing import Any

from houmao.server.client import HoumaoServerClient

from .events import ConversationEvidence
from .models import (
    ArtifactReferences,
    ConversationEvent,
    ConversationProgressSummary,
    DemoPaths,
    DemoState,
    GatewayEvidenceSummary,
    InspectSnapshot,
    MailboxEvidenceSummary,
    ParticipantInspectSnapshot,
    ParticipantOutcomeSummary,
    ReportSnapshot,
    utc_now_iso,
)

_ABSOLUTE_PATH_PATTERN = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
_THREAD_KEY_PATTERN = re.compile(r"mail-ping-pong-\d{8}T\d{6}Z-[A-Za-z0-9]+")


def build_inspect_snapshot(
    *,
    state: DemoState,
    progress: ConversationProgressSummary,
    events: list[ConversationEvent],
    client: HoumaoServerClient | None,
) -> InspectSnapshot:
    """Build one inspect snapshot for the current run."""

    participants = {
        "initiator": _participant_inspect_snapshot(
            client=client,
            tracked_agent_id=state.initiator.tracked_agent_id,
        ),
        "responder": _participant_inspect_snapshot(
            client=client,
            tracked_agent_id=state.responder.tracked_agent_id,
        ),
    }
    return InspectSnapshot(
        observed_at_utc=utc_now_iso(),
        demo_state_summary={
            "demo_id": state.demo_id,
            "active": state.active,
            "output_root": str(state.output_root),
            "api_base_url": state.api_base_url,
            "thread_key": state.thread_key,
            "round_limit": state.round_limit,
            "mailbox_root": str(state.mailbox_root),
        },
        progress=progress,
        participants=participants,
        recent_events=events[-12:],
    )


def build_report_snapshot(
    *,
    state: DemoState,
    paths: DemoPaths,
    progress: ConversationProgressSummary,
    evidence: ConversationEvidence,
    inspect_snapshot: InspectSnapshot,
) -> ReportSnapshot:
    """Build one report snapshot from the current evidence."""

    per_role = {
        "initiator": _participant_outcome_summary(
            state=state,
            inspect_snapshot=inspect_snapshot,
            evidence=evidence,
            progress=progress,
            role="initiator",
        ),
        "responder": _participant_outcome_summary(
            state=state,
            inspect_snapshot=inspect_snapshot,
            evidence=evidence,
            progress=progress,
            role="responder",
        ),
    }
    failures = [] if progress.success else [progress.incomplete_reason or "incomplete"]
    return ReportSnapshot(
        status="complete" if progress.success else "incomplete",
        observed_at_utc=utc_now_iso(),
        config={
            "demo_id": state.demo_id,
            "round_limit": state.round_limit,
            "tools": {
                "initiator": state.initiator.tool,
                "responder": state.responder.tool,
            },
            "roles": {
                "initiator": state.initiator.role_name,
                "responder": state.responder.role_name,
            },
            "api_base_url": state.api_base_url,
        },
        outcome={
            "thread_key": state.thread_key,
            "success": progress.success,
            "incomplete_reason": progress.incomplete_reason,
        },
        counts={
            "messages": progress.message_count,
            "completed_turns": progress.completed_turn_count,
            "expected_messages": progress.expected_messages,
            "expected_turns": progress.expected_turns,
        },
        per_role=per_role,
        gateway_evidence=GatewayEvidenceSummary(
            kickoff_request_id=(
                state.kickoff_request.request_id if state.kickoff_request is not None else None
            ),
            later_turn_count=max(progress.total_turn_count - 1, 0),
            notifier_enqueued_by_role=dict(progress.gateway_enqueued_by_role),
            direct_request_count=1 if state.kickoff_request is not None else 0,
        ),
        mailbox_evidence=MailboxEvidenceSummary(
            thread_key=state.thread_key or "<unset>",
            thread_ids=list(progress.thread_ids),
            total_messages=progress.message_count,
            unread_by_role=dict(progress.unread_by_role),
            subjects=list(evidence.subjects),
        ),
        artifact_refs=ArtifactReferences(
            demo_state_path=paths.state_path,
            inspect_path=paths.inspect_path,
            events_path=paths.events_path,
            report_path=paths.report_path,
            sanitized_report_path=paths.sanitized_report_path,
        ),
        failures=failures,
    )


def sanitize_report(payload: Any, *, key: str | None = None, parent_key: str | None = None) -> Any:
    """Sanitize one report payload for reproducible snapshot comparison."""

    if isinstance(payload, dict):
        return {
            child_key: sanitize_report(child_value, key=child_key, parent_key=key)
            for child_key, child_value in payload.items()
        }
    if isinstance(payload, list):
        if key == "thread_ids":
            return ["<THREAD_ID>" for _ in payload]
        return [sanitize_report(item, key=None, parent_key=key) for item in payload]
    if isinstance(payload, str):
        if key == "observed_at_utc" or (key is not None and key.endswith("_at_utc")):
            return "<TIMESTAMP>"
        if key in {"tracked_agent_id"}:
            return "<TRACKED_AGENT_ID>"
        if key in {"kickoff_request_id"}:
            return "<REQUEST_ID>"
        if key == "thread_key":
            return "<THREAD_KEY>"
        if key in {"api_base_url"}:
            return "<API_BASE_URL>"
        if key is not None and (key.endswith("_path") or key.endswith("_root")):
            return f"<{key.upper()}>"
        if _ABSOLUTE_PATH_PATTERN.match(payload):
            return "<ABSOLUTE_PATH>"
        normalized = _THREAD_KEY_PATTERN.sub("<THREAD_KEY>", payload)
        return normalized
    return payload


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


def _participant_inspect_snapshot(
    *,
    client: HoumaoServerClient | None,
    tracked_agent_id: str,
) -> ParticipantInspectSnapshot:
    """Collect one live inspect snapshot or return a redacted offline fallback."""

    if client is None:
        fallback = {
            "availability": "unavailable",
            "detail": "live inspection unavailable",
            "tracked_agent_id": tracked_agent_id,
        }
        return ParticipantInspectSnapshot(
            state=fallback,
            detail=fallback,
            gateway_status={"gateway_health": "unknown"},
            gateway_mail_notifier={"enabled": False, "supported": False},
        )
    try:
        state_payload = client.get_managed_agent_state(tracked_agent_id).model_dump(mode="json")
        detail_payload = client.get_managed_agent_state_detail(tracked_agent_id).model_dump(
            mode="json"
        )
        gateway_status = client.get_managed_agent_gateway_status(tracked_agent_id).model_dump(
            mode="json"
        )
        gateway_mail_notifier = client.get_managed_agent_gateway_mail_notifier(
            tracked_agent_id
        ).model_dump(mode="json")
    except Exception as exc:
        fallback = {
            "availability": "error",
            "detail": str(exc),
            "tracked_agent_id": tracked_agent_id,
        }
        return ParticipantInspectSnapshot(
            state=fallback,
            detail=fallback,
            gateway_status={"gateway_health": "unavailable", "detail": str(exc)},
            gateway_mail_notifier={"enabled": False, "supported": False, "detail": str(exc)},
        )
    return ParticipantInspectSnapshot(
        state=state_payload,
        detail=detail_payload,
        gateway_status=gateway_status,
        gateway_mail_notifier=gateway_mail_notifier,
    )


def _participant_outcome_summary(
    *,
    state: DemoState,
    inspect_snapshot: InspectSnapshot,
    evidence: ConversationEvidence,
    progress: ConversationProgressSummary,
    role: str,
) -> ParticipantOutcomeSummary:
    """Build one stable per-role outcome summary."""

    participant = state.initiator if role == "initiator" else state.responder
    participant_inspect = inspect_snapshot.participants[role]
    state_payload = participant_inspect.state
    gateway_status = participant_inspect.gateway_status
    notifier_payload = participant_inspect.gateway_mail_notifier
    message_count = sum(1 for item in evidence.messages if item.role == role)
    completed_turn_count = sum(
        1 for record in evidence.turn_records_by_role[role] if record.status != "active"
    )
    last_turn = state_payload.get("last_turn", {})
    last_turn_result = str(last_turn.get("result", "none"))
    return ParticipantOutcomeSummary(
        tool=participant.tool,
        role_name=participant.role_name,
        tracked_agent_id=participant.tracked_agent_id,
        message_count=message_count,
        completed_turn_count=completed_turn_count,
        unread_count=progress.unread_by_role.get(role, 0),
        notifier_enabled=bool(notifier_payload.get("enabled")),
        gateway_health=str(gateway_status.get("gateway_health", "unknown")),
        gateway_enqueued=progress.gateway_enqueued_by_role.get(role, False),
        last_turn_result=last_turn_result,
    )
