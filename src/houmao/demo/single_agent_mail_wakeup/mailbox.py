"""Mailbox delivery and evidence helpers for the single-agent wake-up demo."""

from __future__ import annotations

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
from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox
from houmao.mailbox.managed import DeliveryRequest, deliver_message
from houmao.mailbox.protocol import MailboxMessage, serialize_message_document

from .models import DemoParameters, DemoPaths, DemoState, DeliveryState, utc_now_iso, write_json
from .runtime import build_demo_environment, manager_cli_command, run_json_command

_RUN_ID_PATTERN = "single-agent-mail-wakeup"


class DemoMailboxError(RuntimeError):
    """Raised when mailbox inspection or injection cannot continue safely."""


def build_run_id() -> str:
    """Return one stable run id shared across the demo workflow."""

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{_RUN_ID_PATTERN}-{timestamp}-{uuid4().hex[:8]}"


def build_message_id() -> str:
    """Return one canonical managed-mailbox message id."""

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"msg-{timestamp}-{uuid4().hex}"


def run_token(run_id: str) -> str:
    """Return the short token derived from one persisted run id."""

    return run_id.rsplit("-", 1)[-1]


def default_delivery_subject(*, parameters: DemoParameters, state: DemoState) -> str:
    """Return the canonical auto-delivery subject for one persisted run."""

    return f"{parameters.delivery.subject_prefix} {run_token(state.run_id)}"


def render_body(
    *,
    repo_root: Path,
    body_file: Path,
    state: DemoState,
    subject: str,
) -> str:
    """Render one tracked Markdown body template with run-local substitutions."""

    resolved_body_path = body_file if body_file.is_absolute() else (repo_root / body_file).resolve()
    if not resolved_body_path.is_file():
        raise DemoMailboxError(f"message body file not found: {resolved_body_path}")
    text = resolved_body_path.read_text(encoding="utf-8")
    replacements = {
        "{{RUN_ID}}": state.run_id,
        "{{RUN_TOKEN}}": run_token(state.run_id),
        "{{TOOL}}": state.selected_tool,
        "{{MAILBOX_ADDRESS}}": state.mailbox_address,
        "{{PROJECT_DIR}}": str(state.project_workdir),
        "{{OVERLAY_DIR}}": str(state.overlay_root),
        "{{OUTPUT_FILE_PATH}}": str(state.output_file_path),
        "{{OUTPUT_FILE_CONTENT}}": state.output_file_expected_content,
        "{{MAIL_SUBJECT}}": subject,
    }
    for placeholder, replacement in replacements.items():
        text = text.replace(placeholder, replacement)
    return text


def collect_actor_mail_check(
    *,
    paths: DemoPaths,
    state: DemoState,
    unread_only: bool,
    limit: int = 10,
) -> dict[str, Any]:
    """Return one actor-scoped `agents mail check` payload."""

    env = build_demo_environment(paths=paths)
    command = [
        "agents",
        "mail",
        "check",
        "--agent-name",
        state.agent_name,
        "--limit",
        str(limit),
    ]
    if unread_only:
        command.append("--unread-only")
    return run_json_command(
        manager_cli_command(command),
        cwd=state.project_workdir,
        stdout_path=paths.logs_dir
        / ("actor-mail-check-unread.stdout" if unread_only else "actor-mail-check.stdout"),
        stderr_path=paths.logs_dir
        / ("actor-mail-check-unread.stderr" if unread_only else "actor-mail-check.stderr"),
        env=env,
        timeout_seconds=30.0,
    )


def collect_project_mailbox_messages(
    *,
    paths: DemoPaths,
    state: DemoState,
) -> dict[str, Any]:
    """Return structural project-mailbox message summaries for the demo address."""

    env = build_demo_environment(paths=paths)
    return run_json_command(
        manager_cli_command(
            [
                "project",
                "mailbox",
                "messages",
                "list",
                "--address",
                state.mailbox_address,
            ]
        ),
        cwd=state.project_workdir,
        stdout_path=paths.logs_dir / "project-mailbox-messages-list.stdout",
        stderr_path=paths.logs_dir / "project-mailbox-messages-list.stderr",
        env=env,
        timeout_seconds=30.0,
    )


def collect_project_mailbox_message(
    *,
    paths: DemoPaths,
    state: DemoState,
    message_id: str,
) -> dict[str, Any]:
    """Return one structural project-mailbox message payload for the delivered id."""

    env = build_demo_environment(paths=paths)
    return run_json_command(
        manager_cli_command(
            [
                "project",
                "mailbox",
                "messages",
                "get",
                "--address",
                state.mailbox_address,
                "--message-id",
                message_id,
            ]
        ),
        cwd=state.project_workdir,
        stdout_path=paths.logs_dir / "project-mailbox-message-get.stdout",
        stderr_path=paths.logs_dir / "project-mailbox-message-get.stderr",
        env=env,
        timeout_seconds=30.0,
    )


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
        "expected_content": state.output_file_expected_content,
        "matches_expected_content": False,
        "modified_after_delivery": False,
    }
    if payload["content"] is not None:
        payload["matches_expected_content"] = (
            payload["content"] == state.output_file_expected_content
        )
    if payload["exists"] and delivery is not None:
        delivery_dt = datetime.fromisoformat(delivery.created_at_utc.replace("Z", "+00:00"))
        modified_dt = datetime.fromtimestamp(state.output_file_path.stat().st_mtime, UTC)
        payload["modified_after_delivery"] = modified_dt >= delivery_dt
    return payload


def gateway_can_accept_work(
    *,
    gateway_status: dict[str, Any],
    actor_mail_snapshot: dict[str, Any],
) -> bool:
    """Return whether the harness may safely inject one new message now."""

    return (
        int(actor_mail_snapshot.get("unread_count", 0)) == 0
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

    subject = default_delivery_subject(parameters=parameters, state=state)
    body_markdown = render_body(
        repo_root=repo_root,
        body_file=parameters.delivery.body_file,
        state=state,
        subject=subject,
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
        subject=subject,
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
        rendered = render_body(
            repo_root=repo_root,
            body_file=selected_body_path,
            state=state,
            subject=subject,
        )
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
    bootstrap_filesystem_mailbox(state.project_mailbox_root, principal=sender)
    bootstrap_filesystem_mailbox(state.project_mailbox_root, principal=recipient)

    delivery_index = state.delivery_count + 1
    message_id = build_message_id()
    thread_id = message_id
    created_at_utc = utc_now_iso()
    staged_message_path = (
        state.project_mailbox_root / "staging" / f"delivery-{delivery_index:03d}-{message_id}.md"
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
    result = deliver_message(state.project_mailbox_root, DeliveryRequest.from_payload(payload))
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
    *,
    delivery: DeliveryState,
    actor_mail_snapshot: dict[str, Any],
) -> DeliveryState:
    """Record observed unread and completion transitions for one delivery."""

    matched_message = None
    expected_message_ref = f"filesystem:{delivery.message_id}"
    for message in actor_mail_snapshot.get("messages", []):
        if not isinstance(message, dict):
            continue
        message_ref = str(message.get("message_ref", "")).strip()
        if message_ref == expected_message_ref or message_ref.endswith(f":{delivery.message_id}"):
            matched_message = message
            break
    if matched_message is None:
        return delivery

    updated = delivery
    message_ref = str(matched_message.get("message_ref", "")).strip() or None
    if message_ref is not None and updated.message_ref is None:
        updated = updated.model_copy(update={"message_ref": message_ref})
    if updated.unread_observed_at_utc is None and bool(matched_message.get("unread")):
        updated = updated.model_copy(
            update={
                "unread_observed_at_utc": utc_now_iso(),
                "observation_source": str(actor_mail_snapshot.get("execution_path", "agents_mail")),
            }
        )
    if updated.completed_at_utc is None and not bool(matched_message.get("unread")):
        if updated.unread_observed_at_utc is None:
            updated = updated.model_copy(update={"unread_observed_at_utc": updated.created_at_utc})
        updated = updated.model_copy(
            update={
                "completed_at_utc": utc_now_iso(),
                "observation_source": str(actor_mail_snapshot.get("execution_path", "agents_mail")),
            }
        )
    return updated


def wait_for_delivery_completion(
    *,
    paths: DemoPaths,
    state: DemoState,
    delivery: DeliveryState,
    timeout_seconds: float,
) -> tuple[DemoState, DeliveryState, dict[str, Any], dict[str, Any]]:
    """Wait until the delivered message is completed and the output file exists."""

    deadline = time.monotonic() + timeout_seconds
    current_state = state
    current_delivery = delivery
    last_actor_mail_snapshot: dict[str, Any] = {}
    while time.monotonic() < deadline:
        actor_mail_snapshot = collect_actor_mail_check(
            paths=paths,
            state=current_state,
            unread_only=False,
        )
        last_actor_mail_snapshot = actor_mail_snapshot
        current_delivery = observe_delivery_state(
            delivery=current_delivery,
            actor_mail_snapshot=actor_mail_snapshot,
        )
        output_payload = collect_output_file_payload(state=current_state, delivery=current_delivery)
        if (
            current_delivery.processed
            and output_payload["exists"]
            and output_payload["matches_expected_content"]
        ):
            current_delivery = capture_delivery_evidence(
                paths=paths,
                state=current_state,
                delivery=current_delivery,
            )
            deliveries = list(current_state.deliveries)
            deliveries[current_delivery.delivery_index - 1] = current_delivery
            current_state = current_state.model_copy(update={"deliveries": deliveries})
            return current_state, current_delivery, actor_mail_snapshot, output_payload
        time.sleep(1.0)
    raise DemoMailboxError(
        "timed out waiting "
        f"{timeout_seconds:.1f}s for delivery `{delivery.message_id}` to complete; "
        f"last actor mail snapshot: unread_count={last_actor_mail_snapshot.get('unread_count')!r}"
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
