"""Runtime-owned mailbox prompt and result helpers."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Literal

from gig_agents.agents.mailbox_runtime_models import MailboxResolvedConfig
from gig_agents.agents.mailbox_runtime_support import (
    MAILBOX_FILESYSTEM_SKILL_REFERENCE,
    MAILBOX_TRANSPORT_FILESYSTEM,
)
from gig_agents.mailbox import resolve_filesystem_mailbox_paths

from .errors import BackendExecutionError, MailboxCommandError, MailboxResultParseError
from .models import LaunchPlan, SessionEvent

MailOperation = Literal["check", "send", "reply"]

MAIL_REQUEST_VERSION = 1
MAIL_RESULT_BEGIN_SENTINEL = "AGENTSYS_MAIL_RESULT_BEGIN"
MAIL_RESULT_END_SENTINEL = "AGENTSYS_MAIL_RESULT_END"


@dataclass(frozen=True)
class MailPromptRequest:
    """Prepared runtime-owned mailbox request."""

    request_id: str
    operation: MailOperation
    prompt: str


def prepare_mail_prompt(
    *,
    launch_plan: LaunchPlan,
    operation: MailOperation,
    args: dict[str, Any],
) -> MailPromptRequest:
    """Build one runtime-owned mailbox prompt for a live session."""

    mailbox = ensure_mailbox_command_ready(launch_plan)
    request_id = generate_mail_request_id()
    request_payload = {
        "version": MAIL_REQUEST_VERSION,
        "request_id": request_id,
        "operation": operation,
        "transport": mailbox.transport,
        "principal_id": mailbox.principal_id,
        "args": args,
        "response_contract": {
            "format": "json",
            "sentinel_begin": MAIL_RESULT_BEGIN_SENTINEL,
            "sentinel_end": MAIL_RESULT_END_SENTINEL,
        },
    }

    prompt = "\n".join(
        [
            (
                "Use the runtime-owned filesystem mailbox skill "
                f"`{MAILBOX_FILESYSTEM_SKILL_REFERENCE}` for this mailbox operation."
            ),
            "Inspect the shared mailbox `rules/` directory first before touching shared mailbox state.",
            "Inspect `rules/scripts/requirements.txt` before invoking a shared Python mailbox helper.",
            "Use shared scripts from `rules/scripts/` for any mailbox step that touches `index.sqlite` or `locks/`.",
            "Follow the mailbox env bindings for the current session. Do not guess paths or sender identity.",
            (
                "Return exactly one JSON result between "
                f"`{MAIL_RESULT_BEGIN_SENTINEL}` and `{MAIL_RESULT_END_SENTINEL}`."
            ),
            "",
            "AGENTSYS_MAIL_REQUEST:",
            "```json",
            json.dumps(request_payload, indent=2, sort_keys=True),
            "```",
        ]
    )
    return MailPromptRequest(
        request_id=request_id,
        operation=operation,
        prompt=prompt,
    )


def ensure_mailbox_command_ready(launch_plan: LaunchPlan) -> MailboxResolvedConfig:
    """Validate that a session can safely run runtime-owned mailbox commands."""

    mailbox = launch_plan.mailbox
    if mailbox is None:
        raise MailboxCommandError("Target session is not mailbox-enabled.")
    if mailbox.transport != MAILBOX_TRANSPORT_FILESYSTEM:
        raise MailboxCommandError(
            f"Mailbox commands only support transport={MAILBOX_TRANSPORT_FILESYSTEM!r} in v1."
        )

    paths = resolve_filesystem_mailbox_paths(mailbox.filesystem_root)
    required_files = (
        paths.protocol_version_file,
        paths.sqlite_path,
        paths.rules_dir / "README.md",
        paths.rules_scripts_dir / "requirements.txt",
        paths.rules_scripts_dir / "deliver_message.py",
        paths.rules_scripts_dir / "register_mailbox.py",
        paths.rules_scripts_dir / "deregister_mailbox.py",
        paths.rules_scripts_dir / "insert_standard_headers.py",
        paths.rules_scripts_dir / "update_mailbox_state.py",
        paths.rules_scripts_dir / "repair_index.py",
    )
    missing = [path for path in required_files if not path.is_file()]
    if missing:
        missing_labels = ", ".join(str(path.relative_to(paths.root)) for path in missing)
        raise MailboxCommandError(
            f"Filesystem mailbox bootstrap assets are missing or incomplete: {missing_labels}"
        )
    return mailbox


def parse_mail_result(
    events: list[SessionEvent],
    *,
    request_id: str,
    operation: MailOperation,
    mailbox: MailboxResolvedConfig,
) -> dict[str, Any]:
    """Extract and validate one mailbox result payload from session events."""

    output_text = "\n".join(
        event.message for event in events if event.message and event.kind != "done"
    )
    return _parse_mail_result_text(
        output_text,
        request_id=request_id,
        operation=operation,
        mailbox=mailbox,
    )


def run_mail_prompt(
    *,
    send_prompt: Callable[[str], list[SessionEvent]],
    prompt_request: MailPromptRequest,
    mailbox: MailboxResolvedConfig,
) -> dict[str, Any]:
    """Run a mailbox prompt through the existing prompt-turn control path."""

    try:
        events = send_prompt(prompt_request.prompt)
    except BackendExecutionError as exc:
        raise _mailbox_command_error_from_backend(exc) from exc

    return parse_mail_result(
        events,
        request_id=prompt_request.request_id,
        operation=prompt_request.operation,
        mailbox=mailbox,
    )


def generate_mail_request_id() -> str:
    """Return a stable request id for one runtime-owned mailbox operation."""

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"mailreq-{timestamp}-{uuid.uuid4().hex[:10]}"


def load_mail_body_file(path: Path) -> str:
    """Load an operator-authored Markdown body file for mail send/reply."""

    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MailboxCommandError(f"Failed to read mailbox body file `{path}`: {exc}") from exc


def validate_attachment_paths(paths: list[Path]) -> list[str]:
    """Validate attachment paths before they are surfaced to the agent."""

    resolved: list[str] = []
    for path in paths:
        if not path.is_file():
            raise MailboxCommandError(f"Attachment path does not exist or is not a file: {path}")
        resolved.append(str(path.resolve()))
    return resolved


def _parse_mail_result_text(
    text: str,
    *,
    request_id: str,
    operation: MailOperation,
    mailbox: MailboxResolvedConfig,
) -> dict[str, Any]:
    begin_count = text.count(MAIL_RESULT_BEGIN_SENTINEL)
    end_count = text.count(MAIL_RESULT_END_SENTINEL)
    if begin_count != 1 or end_count != 1:
        raise MailboxResultParseError(
            "Mailbox result parsing failed: expected exactly one sentinel-delimited payload."
        )

    begin_index = text.find(MAIL_RESULT_BEGIN_SENTINEL)
    end_index = text.find(MAIL_RESULT_END_SENTINEL, begin_index + len(MAIL_RESULT_BEGIN_SENTINEL))
    if begin_index < 0 or end_index < 0 or end_index <= begin_index:
        raise MailboxResultParseError(
            "Mailbox result parsing failed: could not locate a valid sentinel-delimited payload."
        )

    payload_text = text[begin_index + len(MAIL_RESULT_BEGIN_SENTINEL) : end_index].strip()
    if not payload_text:
        raise MailboxResultParseError("Mailbox result parsing failed: sentinel payload was empty.")

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise MailboxResultParseError(
            f"Mailbox result parsing failed: sentinel payload was not valid JSON ({exc})."
        ) from exc
    if not isinstance(payload, dict):
        raise MailboxResultParseError(
            "Mailbox result parsing failed: sentinel payload must be a JSON object."
        )

    payload_request_id = payload.get("request_id")
    if payload_request_id != request_id:
        raise MailboxResultParseError(
            "Mailbox result parsing failed: result request_id did not match the active request."
        )
    payload_operation = payload.get("operation")
    if payload_operation != operation:
        raise MailboxResultParseError(
            "Mailbox result parsing failed: result operation did not match the active request."
        )

    payload_transport = payload.get("transport")
    if payload_transport is not None and payload_transport != mailbox.transport:
        raise MailboxResultParseError(
            "Mailbox result parsing failed: result transport did not match the session mailbox binding."
        )
    payload_principal_id = payload.get("principal_id")
    if payload_principal_id is not None and payload_principal_id != mailbox.principal_id:
        raise MailboxResultParseError(
            "Mailbox result parsing failed: result principal_id did not match the session mailbox binding."
        )
    return payload


def _mailbox_command_error_from_backend(exc: BackendExecutionError) -> MailboxCommandError:
    detail = str(exc).strip() or "unknown backend failure"
    lowered = detail.lower()
    if any(token in lowered for token in ("busy", "in-flight", "already running", "active turn")):
        return MailboxCommandError(
            "Mailbox command could not start because the target session is busy or cannot accept a new turn."
        )
    return MailboxCommandError(f"Mailbox command failed: {detail}")
