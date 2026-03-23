"""Mailbox, managed-turn, and gateway-audit evidence collectors."""

from __future__ import annotations

from dataclasses import dataclass
import re
import sqlite3
from pathlib import Path

from houmao.agents.realm_controller.gateway_storage import (
    GatewayNotifierAuditRecord,
    gateway_paths_from_session_root,
    read_gateway_notifier_audit_records,
)
from houmao.server.config import HoumaoServerConfig
from houmao.server.managed_agents import ManagedHeadlessStore, ManagedHeadlessTurnRecord

from .models import ConversationEvent, ConversationProgressSummary, DemoState

_THREAD_KEY_PATTERN = re.compile(r"^Thread-Key:\s*(?P<thread_key>.+?)\s*$", re.MULTILINE)
_ROUND_PATTERN = re.compile(r"^Round:\s*(?P<round>\d+)\s*$", re.MULTILINE)
_SUBJECT_ROUND_PATTERN = re.compile(r"\bRound\s+(?P<round>\d+)\b")


@dataclass(frozen=True)
class MailboxMessageRecord:
    """Normalized mailbox message evidence for one thread."""

    message_id: str
    thread_id: str
    created_at_utc: str
    subject: str
    sender_address: str
    role: str
    tracked_agent_id: str
    round_index: int


@dataclass(frozen=True)
class ConversationEvidence:
    """Collected evidence needed by inspect and report flows."""

    messages: list[MailboxMessageRecord]
    turn_records_by_role: dict[str, list[ManagedHeadlessTurnRecord]]
    gateway_audits_by_role: dict[str, list[GatewayNotifierAuditRecord]]
    unread_by_role: dict[str, int]
    thread_ids: list[str]
    gateway_enqueued_by_role: dict[str, bool]
    subjects: list[str]


def collect_conversation_evidence(state: DemoState) -> ConversationEvidence:
    """Collect the current mailbox, turn, and gateway evidence."""

    messages = _load_mailbox_messages(state)
    thread_ids = sorted({item.thread_id for item in messages})
    turn_records_by_role = {
        "initiator": _load_turn_records(state, role="initiator"),
        "responder": _load_turn_records(state, role="responder"),
    }
    gateway_audits_by_role = {
        "initiator": _load_gateway_audits(state, role="initiator"),
        "responder": _load_gateway_audits(state, role="responder"),
    }
    unread_by_role = {
        "initiator": _count_unread_messages(
            mailbox_root=state.mailbox_root,
            address=state.initiator.mailbox_address,
            thread_ids=thread_ids,
        ),
        "responder": _count_unread_messages(
            mailbox_root=state.mailbox_root,
            address=state.responder.mailbox_address,
            thread_ids=thread_ids,
        ),
    }
    gateway_enqueued_by_role = {
        role: any(record.outcome == "enqueued" for record in records)
        for role, records in gateway_audits_by_role.items()
    }
    return ConversationEvidence(
        messages=messages,
        turn_records_by_role=turn_records_by_role,
        gateway_audits_by_role=gateway_audits_by_role,
        unread_by_role=unread_by_role,
        thread_ids=thread_ids,
        gateway_enqueued_by_role=gateway_enqueued_by_role,
        subjects=[item.subject for item in messages],
    )


def build_progress_summary(
    state: DemoState,
    evidence: ConversationEvidence,
) -> ConversationProgressSummary:
    """Derive the current progress summary from collected evidence."""

    expected_messages = 2 * state.round_limit
    expected_turns = expected_messages + 1
    completed_turn_count = sum(
        1
        for records in evidence.turn_records_by_role.values()
        for record in records
        if record.status != "active"
    )
    total_turn_count = sum(len(records) for records in evidence.turn_records_by_role.values())
    failures: list[str] = []
    if len(evidence.thread_ids) != 1:
        failures.append(f"expected exactly 1 thread, found {len(evidence.thread_ids)}")
    if len(evidence.messages) != expected_messages:
        failures.append(f"expected {expected_messages} messages, found {len(evidence.messages)}")
    if completed_turn_count != expected_turns:
        failures.append(f"expected {expected_turns} completed turns, found {completed_turn_count}")
    non_zero_unread = {role: count for role, count in evidence.unread_by_role.items() if count != 0}
    if non_zero_unread:
        failures.append(f"expected zero unread mail, found {non_zero_unread}")
    missing_gateway_roles = [
        role for role, observed in evidence.gateway_enqueued_by_role.items() if not observed
    ]
    if missing_gateway_roles:
        failures.append(
            "expected gateway notifier enqueue evidence for both roles, missing "
            + ", ".join(sorted(missing_gateway_roles))
        )
    return ConversationProgressSummary(
        thread_key=state.thread_key or "<unset>",
        thread_ids=list(evidence.thread_ids),
        expected_messages=expected_messages,
        expected_turns=expected_turns,
        message_count=len(evidence.messages),
        completed_turn_count=completed_turn_count,
        total_turn_count=total_turn_count,
        unread_by_role=dict(evidence.unread_by_role),
        gateway_enqueued_by_role=dict(evidence.gateway_enqueued_by_role),
        success=not failures,
        incomplete_reason="; ".join(failures) if failures else None,
    )


def build_conversation_events(
    state: DemoState,
    evidence: ConversationEvidence,
) -> list[ConversationEvent]:
    """Build the normalized event stream for the current run."""

    if state.thread_key is None:
        return []
    events: list[ConversationEvent] = []
    if state.kickoff_request is not None:
        events.append(
            ConversationEvent(
                event_type="kickoff_accepted",
                observed_at_utc=state.kickoff_request.submitted_at_utc,
                agent_role="initiator",
                tracked_agent_id=state.initiator.tracked_agent_id,
                thread_key=state.thread_key,
                round_index=1,
                source_kind="managed_request",
                turn_id=state.kickoff_request.headless_turn_id,
                turn_index=state.kickoff_request.headless_turn_index,
                request_id=state.kickoff_request.request_id,
                detail=state.kickoff_request.disposition,
            )
        )
    events.extend(_mailbox_events(state, evidence))
    events.extend(_turn_events(state, evidence))
    events.extend(_gateway_events(state, evidence))
    return sorted(
        events,
        key=lambda item: (
            item.observed_at_utc,
            item.event_type,
            item.agent_role,
            item.turn_index or 0,
            item.message_id or "",
        ),
    )


def _load_mailbox_messages(state: DemoState) -> list[MailboxMessageRecord]:
    """Load messages that belong to the current thread key."""

    if state.thread_key is None:
        return []
    sqlite_path = (state.mailbox_root / "index.sqlite").resolve()
    if not sqlite_path.is_file():
        return []
    role_by_address = {
        state.initiator.mailbox_address: ("initiator", state.initiator.tracked_agent_id),
        state.responder.mailbox_address: ("responder", state.responder.tracked_agent_id),
    }
    query = """
        SELECT
            message_id,
            thread_id,
            created_at_utc,
            subject,
            body_markdown,
            sender_address
        FROM messages
        WHERE subject LIKE ? OR body_markdown LIKE ?
        ORDER BY created_at_utc ASC, message_id ASC
    """
    thread_like = f"%{state.thread_key}%"
    with sqlite3.connect(sqlite_path) as connection:
        rows = connection.execute(
            query, (thread_like, f"%Thread-Key: {state.thread_key}%")
        ).fetchall()
    messages: list[MailboxMessageRecord] = []
    for row in rows:
        sender_address = str(row[5])
        role_payload = role_by_address.get(sender_address)
        if role_payload is None:
            continue
        role, tracked_agent_id = role_payload
        round_index = _extract_round_index(subject=str(row[3]), body_markdown=str(row[4]))
        messages.append(
            MailboxMessageRecord(
                message_id=str(row[0]),
                thread_id=str(row[1]),
                created_at_utc=str(row[2]),
                subject=str(row[3]),
                sender_address=sender_address,
                role=role,
                tracked_agent_id=tracked_agent_id,
                round_index=round_index,
            )
        )
    return messages


def _load_turn_records(state: DemoState, *, role: str) -> list[ManagedHeadlessTurnRecord]:
    """Load managed-turn records for one participant role."""

    participant = state.initiator if role == "initiator" else state.responder
    config = HoumaoServerConfig(
        api_base_url=state.api_base_url,
        runtime_root=state.server.runtime_root,
        startup_child=False,
    )
    store = ManagedHeadlessStore(config=config)
    return store.list_turn_records(tracked_agent_id=participant.tracked_agent_id)


def _load_gateway_audits(state: DemoState, *, role: str) -> list[GatewayNotifierAuditRecord]:
    """Load gateway notifier audits for one participant role."""

    participant = state.initiator if role == "initiator" else state.responder
    queue_path = gateway_paths_from_session_root(session_root=participant.session_root).queue_path
    if not queue_path.is_file():
        return []
    records = read_gateway_notifier_audit_records(queue_path)
    if state.thread_key is None:
        return records
    return [
        record
        for record in records
        if any(state.thread_key in unread.subject for unread in record.unread_summary)
        or (record.detail is not None and state.thread_key in record.detail)
    ]


def _count_unread_messages(*, mailbox_root: Path, address: str, thread_ids: list[str]) -> int:
    """Count unread messages for one mailbox within the selected thread ids."""

    if not thread_ids:
        return 0
    local_sqlite = mailbox_root / "mailboxes" / address / "mailbox.sqlite"
    if not local_sqlite.is_file():
        return 0
    placeholders = ", ".join("?" for _ in thread_ids)
    query = f"""
        SELECT COUNT(*)
        FROM message_state
        WHERE thread_id IN ({placeholders})
          AND is_read = 0
          AND is_deleted = 0
          AND is_archived = 0
    """
    with sqlite3.connect(local_sqlite) as connection:
        row = connection.execute(query, tuple(thread_ids)).fetchone()
    return int(row[0]) if row is not None else 0


def _mailbox_events(state: DemoState, evidence: ConversationEvidence) -> list[ConversationEvent]:
    """Convert mailbox messages into normalized events."""

    if state.thread_key is None:
        return []
    return [
        ConversationEvent(
            event_type="mail_sent",
            observed_at_utc=message.created_at_utc,
            agent_role=message.role,
            tracked_agent_id=message.tracked_agent_id,
            thread_key=state.thread_key,
            round_index=message.round_index,
            source_kind="mailbox_message",
            message_id=message.message_id,
            thread_id=message.thread_id,
            subject=message.subject,
        )
        for message in evidence.messages
    ]


def _turn_events(state: DemoState, evidence: ConversationEvidence) -> list[ConversationEvent]:
    """Convert managed turn records into normalized events."""

    if state.thread_key is None:
        return []
    events: list[ConversationEvent] = []
    for role, records in evidence.turn_records_by_role.items():
        tracked_agent_id = (
            state.initiator.tracked_agent_id
            if role == "initiator"
            else state.responder.tracked_agent_id
        )
        for record in records:
            observed_at = record.completed_at_utc or record.started_at_utc
            round_index = min(record.turn_index, state.round_limit)
            events.append(
                ConversationEvent(
                    event_type="turn_completed" if record.status != "active" else "turn_active",
                    observed_at_utc=observed_at,
                    agent_role=role,  # type: ignore[arg-type]
                    tracked_agent_id=tracked_agent_id,
                    thread_key=state.thread_key,
                    round_index=round_index,
                    source_kind="managed_turn_record",
                    turn_id=record.turn_id,
                    turn_index=record.turn_index,
                    detail=record.status,
                )
            )
    return events


def _gateway_events(state: DemoState, evidence: ConversationEvidence) -> list[ConversationEvent]:
    """Convert gateway notifier audit records into normalized events."""

    if state.thread_key is None:
        return []
    events: list[ConversationEvent] = []
    for role, records in evidence.gateway_audits_by_role.items():
        tracked_agent_id = (
            state.initiator.tracked_agent_id
            if role == "initiator"
            else state.responder.tracked_agent_id
        )
        for record in records:
            round_index = _audit_round_index(record)
            event_type = "gateway_enqueued" if record.outcome == "enqueued" else "gateway_poll"
            subject = record.unread_summary[0].subject if record.unread_summary else None
            events.append(
                ConversationEvent(
                    event_type=event_type,
                    observed_at_utc=record.poll_time_utc,
                    agent_role=role,  # type: ignore[arg-type]
                    tracked_agent_id=tracked_agent_id,
                    thread_key=state.thread_key,
                    round_index=round_index,
                    source_kind="gateway_notifier_audit",
                    request_id=record.enqueued_request_id,
                    subject=subject,
                    detail=record.outcome,
                )
            )
    return events


def _extract_round_index(*, subject: str, body_markdown: str) -> int:
    """Extract one round index from the stable message contract."""

    body_match = _ROUND_PATTERN.search(body_markdown)
    if body_match is not None:
        return int(body_match.group("round"))
    subject_match = _SUBJECT_ROUND_PATTERN.search(subject)
    if subject_match is not None:
        return int(subject_match.group("round"))
    return 1


def _audit_round_index(record: GatewayNotifierAuditRecord) -> int:
    """Infer one round index from notifier audit data."""

    for unread in record.unread_summary:
        subject_match = _SUBJECT_ROUND_PATTERN.search(unread.subject)
        if subject_match is not None:
            return int(subject_match.group("round"))
    return 1
