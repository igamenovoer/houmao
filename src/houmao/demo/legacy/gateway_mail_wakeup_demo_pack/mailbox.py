"""Filesystem mailbox delivery and evidence helpers for the gateway wake-up demo pack."""

from __future__ import annotations

import re
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from houmao.agents.realm_controller.backends.tmux_runtime import (
    HEADLESS_AGENT_WINDOW_NAME,
    TmuxCommandError,
    capture_tmux_pane,
    resolve_tmux_pane,
)
from houmao.agents.realm_controller.gateway_models import GatewayMailListRequestV1
from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox
from houmao.mailbox.managed import DeliveryRequest, deliver_message
from houmao.mailbox.protocol import MailboxMessage, serialize_message_document

from .models import DemoParameters, DemoPaths, DemoState, DeliveryState, utc_now_iso, write_json
from .runtime import build_gateway_client

_RUN_ID_PATTERN = "gateway-mail-wakeup"
_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$")


class DemoMailboxError(RuntimeError):
    """Raised when mailbox inspection or injection cannot continue safely."""


def build_run_id() -> str:
    """Return one stable run id shared across injected messages."""

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{_RUN_ID_PATTERN}-{timestamp}-{uuid4().hex[:8]}"


def build_message_id() -> str:
    """Return one canonical managed-mailbox message id."""

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"msg-{timestamp}-{uuid4().hex}"


def render_body(
    *,
    repo_root: Path,
    body_file: Path,
    state: DemoState,
) -> str:
    """Render one tracked Markdown body template with run-local substitutions."""

    resolved_body_path = body_file if body_file.is_absolute() else (repo_root / body_file).resolve()
    if not resolved_body_path.is_file():
        raise DemoMailboxError(f"message body file not found: {resolved_body_path}")
    text = resolved_body_path.read_text(encoding="utf-8")
    replacements = {
        "{{RUN_ID}}": state.run_id,
        "{{TOOL}}": state.selected_tool,
        "{{MAILBOX_ADDRESS}}": state.mailbox_address,
        "{{PROJECT_DIR}}": str(state.project_workdir),
        "{{REPO_ROOT}}": str(repo_root),
        "{{OUTPUT_FILE_PATH}}": str(state.output_file_path),
    }
    for placeholder, replacement in replacements.items():
        text = text.replace(placeholder, replacement)
    return text


def collect_mailbox_snapshot(state: DemoState) -> dict[str, Any]:
    """Return the mailbox state using gateway HTTP first with SQLite fallback."""

    try:
        client = build_gateway_client(state=state)
        response = client.list_mail(GatewayMailListRequestV1(box="inbox", limit=64))
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


def collect_output_file_payload(
    *,
    state: DemoState,
    delivery: DeliveryState | None,
) -> dict[str, Any]:
    """Collect stable output-file evidence for the persisted run."""

    payload = {
        "output_file_path": str(state.output_file_path),
        "exists": state.output_file_path.is_file(),
        "content": (
            state.output_file_path.read_text(encoding="utf-8").strip()
            if state.output_file_path.is_file()
            else None
        ),
        "timestamp_like": False,
        "modified_after_delivery": False,
    }
    if payload["content"] is not None:
        payload["timestamp_like"] = bool(_TIMESTAMP_PATTERN.match(str(payload["content"])))
    if payload["exists"] and delivery is not None:
        delivery_dt = datetime.fromisoformat(delivery.created_at_utc.replace("Z", "+00:00"))
        modified_dt = datetime.fromtimestamp(state.output_file_path.stat().st_mtime, UTC)
        payload["modified_after_delivery"] = modified_dt >= delivery_dt
    return payload


def gateway_can_accept_work(
    *, gateway_status: dict[str, Any], mailbox_snapshot: dict[str, Any]
) -> bool:
    """Return whether the harness may safely inject one new message now."""

    return (
        int(mailbox_snapshot.get("unread_count", 0)) == 0
        and gateway_status.get("request_admission") == "open"
        and gateway_status.get("active_execution") == "idle"
        and int(gateway_status.get("queue_depth", 1)) == 0
    )


def deliver_configured_automatic_message(
    *,
    repo_root: Path,
    paths: DemoPaths,
    parameters: DemoParameters,
    state: DemoState,
) -> DeliveryState:
    """Deliver the tracked automatic wake-up message."""

    body_markdown = render_body(
        repo_root=repo_root, body_file=parameters.delivery.body_file, state=state
    )
    resolved_body_path = (
        parameters.delivery.body_file
        if parameters.delivery.body_file.is_absolute()
        else (repo_root / parameters.delivery.body_file).resolve()
    )
    return deliver_rendered_message(
        paths=paths,
        parameters=parameters,
        state=state,
        subject=parameters.delivery.subject,
        body_markdown=body_markdown,
        body_source_path=resolved_body_path,
    )


def deliver_manual_message(
    *,
    repo_root: Path,
    paths: DemoPaths,
    parameters: DemoParameters,
    state: DemoState,
    subject: str,
    body_content: str | None,
    body_file: Path | None,
) -> DeliveryState:
    """Deliver one manual message through the filesystem mailbox boundary."""

    if body_content is not None and body_file is not None:
        raise DemoMailboxError("pass either `body_content` or `body_file`, not both")
    if body_content is not None:
        rendered = body_content
        source_path = None
    else:
        selected_body_path = body_file or parameters.delivery.body_file
        rendered = render_body(repo_root=repo_root, body_file=selected_body_path, state=state)
        source_path = (
            selected_body_path
            if selected_body_path.is_absolute()
            else (repo_root / selected_body_path).resolve()
        )
    return deliver_rendered_message(
        paths=paths,
        parameters=parameters,
        state=state,
        subject=subject,
        body_markdown=rendered,
        body_source_path=source_path,
    )


def deliver_rendered_message(
    *,
    paths: DemoPaths,
    parameters: DemoParameters,
    state: DemoState,
    subject: str,
    body_markdown: str,
    body_source_path: Path | None,
) -> DeliveryState:
    """Stage and deliver one already-rendered filesystem mailbox message."""

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

    delivery_index = state.delivery_count + 1
    message_id = build_message_id()
    thread_id = message_id
    created_at_utc = utc_now_iso()
    staged_message_path = (
        paths.mailbox_root / "staging" / f"delivery-{delivery_index:03d}-{message_id}.md"
    )
    payload_path = paths.deliveries_dir / "payloads" / f"delivery-{delivery_index:03d}.json"
    delivery_artifact_path = paths.deliveries_dir / f"delivery-{delivery_index:03d}.json"
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
            "delivery_index": delivery_index,
            "body_source_path": None if body_source_path is None else str(body_source_path),
            "subject": subject,
            "message_id": message_id,
            "thread_id": thread_id,
            "created_at_utc": created_at_utc,
            "result": result,
        },
    )
    return DeliveryState(
        delivery_index=delivery_index,
        subject=subject,
        message_id=message_id,
        thread_id=thread_id,
        created_at_utc=created_at_utc,
        body_source_path=body_source_path,
        staged_message_path=staged_message_path,
        payload_path=payload_path,
        delivery_artifact_path=delivery_artifact_path,
    )


def observe_delivery_state(
    *, delivery: DeliveryState, mailbox_snapshot: dict[str, Any]
) -> DeliveryState:
    """Record observed unread and read transitions for one delivery."""

    matched_message = None
    for message in mailbox_snapshot.get("messages", []):
        message_ref = str(message.get("message_ref", "")).strip()
        if message_ref == delivery.message_id or message_ref.endswith(f":{delivery.message_id}"):
            matched_message = message
            break
    if matched_message is None:
        return delivery

    updated = delivery
    if updated.unread_observed_at_utc is None and bool(matched_message.get("unread")):
        updated = updated.model_copy(
            update={
                "unread_observed_at_utc": utc_now_iso(),
                "mailbox_state_source": str(mailbox_snapshot.get("state_source", "unknown")),
            }
        )
    if updated.read_observed_at_utc is None and not bool(matched_message.get("unread")):
        if updated.unread_observed_at_utc is None:
            updated = updated.model_copy(update={"unread_observed_at_utc": updated.created_at_utc})
        updated = updated.model_copy(
            update={
                "read_observed_at_utc": utc_now_iso(),
                "mailbox_state_source": str(mailbox_snapshot.get("state_source", "unknown")),
            }
        )
    return updated


def wait_for_delivery_completion(
    *,
    paths: DemoPaths,
    state: DemoState,
    delivery: DeliveryState,
    timeout_seconds: float,
) -> tuple[DemoState, DeliveryState, dict[str, Any]]:
    """Wait until the delivered message becomes read and the output file exists."""

    deadline = time.monotonic() + timeout_seconds
    current_state = state
    current_delivery = delivery
    while time.monotonic() < deadline:
        mailbox_snapshot = collect_mailbox_snapshot(current_state)
        current_delivery = observe_delivery_state(
            delivery=current_delivery,
            mailbox_snapshot=mailbox_snapshot,
        )
        output_payload = collect_output_file_payload(state=current_state, delivery=current_delivery)
        if current_delivery.processed and output_payload["exists"]:
            current_delivery = capture_delivery_evidence(
                paths=paths,
                state=current_state,
                delivery=current_delivery,
            )
            deliveries = list(current_state.deliveries)
            deliveries[current_delivery.delivery_index - 1] = current_delivery
            current_state = current_state.model_copy(update={"deliveries": deliveries})
            return current_state, current_delivery, output_payload
        time.sleep(1.0)
    raise DemoMailboxError(
        f"timed out waiting {timeout_seconds:.1f}s for delivery `{delivery.message_id}` to complete"
    )


def capture_delivery_evidence(
    *,
    paths: DemoPaths,
    state: DemoState,
    delivery: DeliveryState,
) -> DeliveryState:
    """Capture one best-effort tmux pane snapshot and tail for a processed delivery."""

    if state.tmux_session_name is None:
        return delivery
    delivery_dir = paths.evidence_dir / f"delivery-{delivery.delivery_index:03d}"
    delivery_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = delivery_dir / "tmux-pane.txt"
    tail_path = delivery_dir / "tmux-pane.tail.txt"
    metadata_path = delivery_dir / "evidence.json"

    payload: dict[str, Any] = {
        "delivery_index": delivery.delivery_index,
        "message_id": delivery.message_id,
        "tmux_session_name": state.tmux_session_name,
    }
    try:
        pane = resolve_tmux_pane(
            session_name=state.tmux_session_name,
            window_name=HEADLESS_AGENT_WINDOW_NAME,
            window_index="0",
        )
        full_text = capture_tmux_pane(target=pane.pane_id)
        snapshot_path.write_text(full_text, encoding="utf-8")
        tail_lines = full_text.splitlines()[-80:]
        tail_path.write_text("\n".join(tail_lines) + ("\n" if tail_lines else ""), encoding="utf-8")
        payload.update(
            {
                "status": "captured",
                "pane_id": pane.pane_id,
                "snapshot_path": str(snapshot_path),
                "tail_path": str(tail_path),
            }
        )
        write_json(metadata_path, payload)
        return delivery.model_copy(
            update={
                "evidence_snapshot_path": snapshot_path,
                "evidence_tail_path": tail_path,
                "evidence_collected_at_utc": utc_now_iso(),
            }
        )
    except (RuntimeError, TmuxCommandError) as exc:
        payload.update({"status": "capture_failed", "detail": str(exc)})
        write_json(metadata_path, payload)
        return delivery
