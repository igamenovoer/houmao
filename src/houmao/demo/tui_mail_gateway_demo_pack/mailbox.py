"""Mailbox, drive-loop, and evidence helpers for the TUI mail gateway demo pack."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from houmao.agents.realm_controller.backends.tmux_runtime import TmuxCommandError, capture_tmux_pane
from houmao.agents.realm_controller.gateway_models import GatewayMailCheckRequestV1
from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox
from houmao.mailbox.managed import DeliveryRequest, deliver_message
from houmao.mailbox.protocol import MailboxMessage, serialize_message_document

from .models import DemoParameters, DemoPaths, DemoState, TurnState, utc_now_iso, write_json
from .runtime import build_gateway_client

_RUN_ID_PATTERN = "tui-mail-gateway"


class DemoMailboxError(RuntimeError):
    """Raised when mailbox inspection or injection cannot continue safely."""


def build_run_id() -> str:
    """Return one stable run id shared across all injected messages."""

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{_RUN_ID_PATTERN}-{timestamp}-{uuid4().hex[:8]}"


def build_message_id() -> str:
    """Return one canonical managed-mailbox message id."""

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"msg-{timestamp}-{uuid4().hex}"


def render_turn_body(
    *,
    repo_root: Path,
    template_path: Path,
    state: DemoState,
    turn_index: int,
) -> str:
    """Render one tracked turn template with run-local substitutions."""

    text = template_path.read_text(encoding="utf-8")
    replacements = {
        "{{RUN_ID}}": state.run_id,
        "{{TURN_INDEX}}": str(turn_index),
        "{{TURN_LIMIT}}": str(state.turn_limit),
        "{{TOOL}}": state.selected_tool,
        "{{MAILBOX_ADDRESS}}": state.mailbox_address,
        "{{PROJECT_DIR}}": str(state.project_workdir),
        "{{REPO_ROOT}}": str(repo_root),
    }
    for placeholder, replacement in replacements.items():
        text = text.replace(placeholder, replacement)
    return text


def collect_gateway_status(state: DemoState) -> dict[str, Any]:
    """Return the compact live gateway status payload."""

    client = build_gateway_client(state=state)
    status = client.status()
    payload = status.model_dump(mode="json")
    return {"state_source": "http", **payload}


def collect_notifier_status(state: DemoState) -> dict[str, Any]:
    """Return the live gateway notifier status payload."""

    client = build_gateway_client(state=state)
    status = client.get_mail_notifier()
    payload = status.model_dump(mode="json")
    return {"state_source": "http", **payload}


def collect_mailbox_snapshot(state: DemoState) -> dict[str, Any]:
    """Return the shared mailbox state using HTTP first with SQLite fallback."""

    try:
        client = build_gateway_client(state=state)
        response = client.check_mail(GatewayMailCheckRequestV1(unread_only=False, limit=64))
        return {
            "state_source": "gateway",
            "principal_id": response.principal_id,
            "address": response.address,
            "message_count": response.message_count,
            "unread_count": response.unread_count,
            "messages": [message.model_dump(mode="json") for message in response.messages],
        }
    except Exception:
        return _collect_mailbox_snapshot_from_sqlite(state=state)


def _collect_mailbox_snapshot_from_sqlite(state: DemoState) -> dict[str, Any]:
    """Return one mailbox snapshot from the local mailbox SQLite projection."""

    local_sqlite = (
        state.output_root / "mailbox" / "mailboxes" / state.mailbox_address / "mailbox.sqlite"
    )
    if not local_sqlite.is_file():
        raise DemoMailboxError(f"mailbox SQLite not found: {local_sqlite}")
    query = """
        SELECT
            message_id,
            thread_id,
            created_at_utc,
            subject,
            is_read
        FROM message_state
        WHERE is_deleted = 0
          AND is_archived = 0
        ORDER BY created_at_utc ASC, message_id ASC
    """
    with sqlite3.connect(local_sqlite) as connection:
        rows = connection.execute(query).fetchall()
    messages = [
        {
            "message_ref": str(row[0]),
            "thread_ref": str(row[1]),
            "created_at_utc": str(row[2]),
            "subject": str(row[3]),
            "unread": not bool(row[4]),
        }
        for row in rows
    ]
    unread_count = sum(1 for row in rows if not bool(row[4]))
    return {
        "state_source": "sqlite_fallback",
        "principal_id": state.mailbox_principal_id,
        "address": state.mailbox_address,
        "message_count": len(messages),
        "unread_count": unread_count,
        "messages": messages,
    }


def gateway_can_accept_work(
    *, gateway_status: dict[str, Any], mailbox_snapshot: dict[str, Any]
) -> bool:
    """Return whether the harness may safely inject one new message on this tick."""

    return (
        int(mailbox_snapshot.get("unread_count", 0)) == 0
        and gateway_status.get("request_admission") == "open"
        and gateway_status.get("active_execution") == "idle"
        and int(gateway_status.get("queue_depth", 1)) == 0
    )


def deliver_turn_message(
    *,
    repo_root: Path,
    paths: DemoPaths,
    parameters: DemoParameters,
    state: DemoState,
    turn_index: int,
) -> TurnState:
    """Stage and deliver one tracked turn message without direct SQLite mutation."""

    template_path = parameters.delivery.turn_files[turn_index - 1]
    resolved_template_path = (repo_root / template_path).resolve()
    if not resolved_template_path.is_file():
        raise DemoMailboxError(f"turn template not found: {resolved_template_path}")

    sender = MailboxPrincipal(
        principal_id=parameters.delivery.sender_principal_id,
        address=parameters.delivery.sender_address,
    )
    recipient = MailboxPrincipal(
        principal_id=state.mailbox_principal_id,
        address=state.mailbox_address,
    )
    bootstrap_filesystem_mailbox(paths.mailbox_root, principal=sender)
    bootstrap_filesystem_mailbox(paths.mailbox_root, principal=recipient)

    message_id = build_message_id()
    thread_id = state.run_id
    created_at_utc = utc_now_iso()
    subject = parameters.delivery.subject_template.format(
        run_id=state.run_id,
        turn_index=turn_index,
        turn_limit=state.turn_limit,
        tool=state.selected_tool,
    )
    body_markdown = render_turn_body(
        repo_root=repo_root,
        template_path=resolved_template_path,
        state=state,
        turn_index=turn_index,
    )
    staged_message_path = paths.deliveries_dir / "staged" / f"turn-{turn_index:03d}-{message_id}.md"
    payload_path = paths.deliveries_dir / "payloads" / f"turn-{turn_index:03d}.json"
    delivery_artifact_path = paths.deliveries_dir / f"delivery-{turn_index:03d}.json"
    message = MailboxMessage.model_validate(
        {
            "message_id": message_id,
            "thread_id": thread_id,
            "in_reply_to": None,
            "references": [],
            "created_at_utc": created_at_utc,
            "from": sender,
            "to": [recipient],
            "cc": [],
            "reply_to": [],
            "subject": subject,
            "body_markdown": body_markdown,
            "attachments": [],
            "headers": {},
        }
    )
    staged_message_path.parent.mkdir(parents=True, exist_ok=True)
    staged_message_path.write_text(serialize_message_document(message), encoding="utf-8")
    payload = {
        "staged_message_path": str(staged_message_path),
        "message_id": message_id,
        "thread_id": thread_id,
        "in_reply_to": None,
        "references": [],
        "created_at_utc": created_at_utc,
        "sender": {
            "principal_id": sender.principal_id,
            "address": sender.address,
        },
        "to": [
            {
                "principal_id": recipient.principal_id,
                "address": recipient.address,
            }
        ],
        "cc": [],
        "reply_to": [],
        "subject": subject,
        "attachments": [],
        "headers": {},
    }
    write_json(payload_path, payload)
    result = deliver_message(paths.mailbox_root, DeliveryRequest.from_payload(payload))
    write_json(
        delivery_artifact_path,
        {
            "turn_index": turn_index,
            "template_path": str(resolved_template_path),
            "subject": subject,
            "message_id": message_id,
            "thread_id": thread_id,
            "created_at_utc": created_at_utc,
            "result": result,
        },
    )
    return TurnState(
        turn_index=turn_index,
        template_path=resolved_template_path,
        subject=subject,
        message_id=message_id,
        thread_id=thread_id,
        staged_message_path=staged_message_path,
        payload_path=payload_path,
        delivery_artifact_path=delivery_artifact_path,
        delivered_at_utc=created_at_utc,
    )


def observe_unread_delivery(*, turn: TurnState, mailbox_snapshot: dict[str, Any]) -> TurnState:
    """Record the first observed unread state for one delivered message when present."""

    if turn.unread_observed_at_utc is not None:
        return turn
    for message in mailbox_snapshot.get("messages", []):
        if message.get("message_ref") != turn.message_id:
            continue
        if bool(message.get("unread")):
            return turn.model_copy(
                update={
                    "unread_observed_at_utc": utc_now_iso(),
                    "mailbox_state_source": str(mailbox_snapshot.get("state_source", "unknown")),
                }
            )
    return turn


def detect_processed_turns(
    *,
    state: DemoState,
    mailbox_snapshot: dict[str, Any],
) -> tuple[DemoState, list[TurnState]]:
    """Update turn state from observed read transitions and return newly completed turns."""

    messages_by_id = {
        str(message.get("message_ref")): message for message in mailbox_snapshot.get("messages", [])
    }
    updated_turns: list[TurnState] = []
    completed_turns: list[TurnState] = []
    for turn in state.turns:
        updated_turn = observe_unread_delivery(turn=turn, mailbox_snapshot=mailbox_snapshot)
        message = messages_by_id.get(updated_turn.message_id)
        if (
            updated_turn.read_observed_at_utc is None
            and message is not None
            and not bool(message.get("unread"))
        ):
            if updated_turn.unread_observed_at_utc is None:
                updated_turn = updated_turn.model_copy(
                    update={"unread_observed_at_utc": updated_turn.delivered_at_utc}
                )
            updated_turn = updated_turn.model_copy(
                update={
                    "read_observed_at_utc": utc_now_iso(),
                    "mailbox_state_source": str(mailbox_snapshot.get("state_source", "unknown")),
                }
            )
            completed_turns.append(updated_turn)
        updated_turns.append(updated_turn)
    return state.model_copy(update={"turns": updated_turns}), completed_turns


def capture_turn_evidence(
    *,
    paths: DemoPaths,
    state: DemoState,
    turn: TurnState,
) -> TurnState:
    """Capture one best-effort tmux pane snapshot and tail for a processed turn."""

    turn_dir = paths.evidence_dir / f"turn-{turn.turn_index:03d}"
    turn_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = turn_dir / "tmux-pane.txt"
    tail_path = turn_dir / "tmux-pane.tail.txt"
    metadata_path = turn_dir / "evidence.json"
    collected_at_utc = utc_now_iso()
    capture_error: str | None = None
    capture_text = ""
    try:
        capture_text = capture_tmux_pane(target=state.tmux_session_name)
    except TmuxCommandError as exc:
        capture_error = str(exc)
    snapshot_path.write_text(capture_text, encoding="utf-8")
    tail_lines = capture_text.splitlines()[-80:]
    tail_path.write_text("\n".join(tail_lines) + ("\n" if tail_lines else ""), encoding="utf-8")
    write_json(
        metadata_path,
        {
            "turn_index": turn.turn_index,
            "collected_at_utc": collected_at_utc,
            "tmux_session_name": state.tmux_session_name,
            "snapshot_path": str(snapshot_path),
            "tail_path": str(tail_path),
            "capture_error": capture_error,
        },
    )
    return turn.model_copy(
        update={
            "evidence_snapshot_path": snapshot_path,
            "evidence_tail_path": tail_path,
            "evidence_collected_at_utc": collected_at_utc,
        }
    )
