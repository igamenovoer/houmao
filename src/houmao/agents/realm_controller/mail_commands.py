"""Runtime-owned mailbox prompt and result helpers.

Mailbox result parsing is machine-critical. Shadow-mode parsing therefore
prefers explicit schema/sentinel extraction over available text surfaces rather
than assuming best-effort dialog projection fidelity.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Literal

from houmao.agents.mailbox_runtime_models import MailboxResolvedConfig
from houmao.agents.mailbox_runtime_support import (
    MAILBOX_FILESYSTEM_SKILL_REFERENCE,
    MAILBOX_TRANSPORT_FILESYSTEM,
)
from houmao.mailbox import resolve_filesystem_mailbox_paths

from .backends.shadow_parser_core import DialogProjection
from .errors import BackendExecutionError, MailboxCommandError, MailboxResultParseError
from .models import LaunchPlan, SessionEvent

MailOperation = Literal["check", "send", "reply"]

MAIL_REQUEST_VERSION = 1
MAIL_RESULT_BEGIN_SENTINEL = "AGENTSYS_MAIL_RESULT_BEGIN"
MAIL_RESULT_END_SENTINEL = "AGENTSYS_MAIL_RESULT_END"
MAIL_RESULT_SURFACES_PAYLOAD_KEY = "mail_result_surfaces"


@dataclass(frozen=True)
class MailPromptRequest:
    """Prepared runtime-owned mailbox request."""

    request_id: str
    operation: MailOperation
    prompt: str


@dataclass(frozen=True)
class SentinelBlock:
    """One standalone sentinel-delimited result block extracted from a text surface."""

    begin_line: int
    end_line: int
    payload_text: str


@dataclass(frozen=True)
class _MailResultTextSurface:
    """One candidate text surface that may contain a sentinel-delimited result."""

    surface_id: str
    text: str


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
            (
                "Use shared scripts from `rules/scripts/` for any mailbox step that touches "
                "shared `index.sqlite`, mailbox-local `mailbox.sqlite`, or `locks/`."
            ),
            "Follow the mailbox env bindings for the current session. Do not guess paths or sender identity.",
            ("Only mark messages read after the message has actually been processed successfully."),
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

    attempted_inputs: list[_MailResultTextSurface] = []
    seen_inputs: set[str] = set()
    for surface in _mail_result_text_surfaces(events):
        normalized = surface.text.strip()
        if not normalized or normalized in seen_inputs:
            continue
        attempted_inputs.append(surface)
        seen_inputs.add(normalized)

    last_error: MailboxResultParseError | None = None
    for surface in attempted_inputs:
        try:
            return _parse_mail_result_text(
                surface.text,
                request_id=request_id,
                operation=operation,
                mailbox=mailbox,
            )
        except MailboxResultParseError as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise MailboxResultParseError(
        "Mailbox result parsing failed: no event output was available for sentinel extraction."
    )


def build_shadow_mail_result_surface_payloads(
    *,
    raw_output_text: str,
    current_projection: DialogProjection,
    baseline_output_text: str,
    baseline_projection: DialogProjection,
) -> tuple[dict[str, str], ...]:
    """Build post-submit shadow text surfaces for mailbox sentinel extraction."""

    surfaces: list[dict[str, str]] = []
    seen_texts: set[str] = set()
    candidates = (
        (
            "shadow_post_submit.normalized_text",
            _trim_post_submit_text(
                current_projection.normalized_text,
                baseline_projection.normalized_text,
            ),
        ),
        (
            "shadow_post_submit.raw_text",
            _trim_post_submit_text(raw_output_text, baseline_output_text),
        ),
        (
            "shadow_post_submit.dialog_text",
            _trim_post_submit_text(
                current_projection.dialog_text,
                baseline_projection.dialog_text,
            ),
        ),
    )
    for surface_id, text in candidates:
        normalized = text.strip()
        if not normalized or normalized in seen_texts:
            continue
        seen_texts.add(normalized)
        surfaces.append(
            {
                "surface_id": surface_id,
                "text": text,
            }
        )
    return tuple(surfaces)


def shadow_mail_result_contract_reached(surface_payloads: tuple[dict[str, str], ...]) -> bool:
    """Return whether post-submit shadow surfaces contain one standalone sentinel block."""

    for surface in surface_payloads:
        text = surface.get("text")
        if isinstance(text, str) and extract_sentinel_blocks(text):
            return True
    return False


def run_mail_prompt(
    *,
    send_prompt: Callable[[str], list[SessionEvent]] | None,
    send_mail_prompt: Callable[[MailPromptRequest], list[SessionEvent]] | None,
    prompt_request: MailPromptRequest,
    mailbox: MailboxResolvedConfig,
) -> dict[str, Any]:
    """Run a mailbox prompt through the existing prompt-turn control path."""

    try:
        if send_mail_prompt is not None:
            events = send_mail_prompt(prompt_request)
        elif send_prompt is not None:
            events = send_prompt(prompt_request.prompt)
        else:
            raise RuntimeError("Mailbox prompt execution requires a prompt sender.")
    except BackendExecutionError as exc:
        raise _mailbox_command_error_from_backend(exc) from exc

    return parse_mail_result(
        events,
        request_id=prompt_request.request_id,
        operation=prompt_request.operation,
        mailbox=mailbox,
    )


def _event_payload_text_candidates(event: SessionEvent) -> tuple[str, ...]:
    """Return payload-derived text surfaces that may contain the mail sentinel block."""

    payload = event.payload
    if not isinstance(payload, dict):
        return ()

    candidates: list[str] = []
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        candidates.append(output_text)

    dialog_projection = payload.get("dialog_projection")
    if isinstance(dialog_projection, dict):
        normalized_text = dialog_projection.get("normalized_text")
        if isinstance(normalized_text, str) and normalized_text.strip():
            candidates.append(normalized_text)

        raw_text = dialog_projection.get("raw_text")
        if isinstance(raw_text, str) and raw_text.strip():
            candidates.append(raw_text)

        dialog_text = dialog_projection.get("dialog_text")
        if isinstance(dialog_text, str) and dialog_text.strip():
            candidates.append(dialog_text)

    return tuple(candidates)


def _event_mail_result_surface_candidates(event: SessionEvent) -> tuple[_MailResultTextSurface, ...]:
    """Return explicit completion-contract surfaces embedded in one session event."""

    payload = event.payload
    if not isinstance(payload, dict):
        return ()

    raw_surfaces = payload.get(MAIL_RESULT_SURFACES_PAYLOAD_KEY)
    if not isinstance(raw_surfaces, list):
        return ()

    surfaces: list[_MailResultTextSurface] = []
    for index, raw_surface in enumerate(raw_surfaces, start=1):
        if not isinstance(raw_surface, dict):
            continue
        text = raw_surface.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        surface_id = raw_surface.get("surface_id")
        if not isinstance(surface_id, str) or not surface_id.strip():
            surface_id = f"event_mail_result_surfaces[{index}]"
        surfaces.append(_MailResultTextSurface(surface_id=surface_id, text=text))

    return tuple(surfaces)


def _mail_result_text_surfaces(events: list[SessionEvent]) -> tuple[_MailResultTextSurface, ...]:
    """Return ordered candidate surfaces for sentinel extraction.

    Ordering prefers explicit structured payload surfaces first, especially
    closer-to-source shadow surfaces such as ``normalized_text`` and
    ``raw_text``. Event-message aggregates remain available as a fallback for
    CAO-native flows or providers that stream the sentinel block across multiple
    assistant events.
    """

    surfaces: list[_MailResultTextSurface] = []

    for index, event in enumerate(events):
        surfaces.extend(_event_mail_result_surface_candidates(event))
        for payload_index, payload_text in enumerate(_event_payload_text_candidates(event), start=1):
            surfaces.append(
                _MailResultTextSurface(
                    surface_id=f"event[{index}].payload[{payload_index}]",
                    text=payload_text,
                )
            )

    done_messages = [event.message for event in events if event.kind == "done" and event.message]
    if done_messages:
        surfaces.append(
            _MailResultTextSurface(
                surface_id="done_messages_combined",
                text="\n".join(done_messages),
            )
        )

    assistant_messages = [
        event.message for event in events if event.kind != "done" and event.message
    ]
    if assistant_messages:
        surfaces.append(
            _MailResultTextSurface(
                surface_id="assistant_messages_combined",
                text="\n".join(assistant_messages),
            )
        )

    all_messages = [event.message for event in events if event.message]
    if all_messages:
        surfaces.append(
            _MailResultTextSurface(
                surface_id="all_messages_combined",
                text="\n".join(all_messages),
            )
        )

    return tuple(surfaces)


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
    blocks = extract_sentinel_blocks(text)
    if len(blocks) == 0:
        raise MailboxResultParseError(
            "Mailbox result parsing failed: no standalone sentinel-delimited payload found."
        )
    if len(blocks) != 1:
        raise MailboxResultParseError(
            "Mailbox result parsing failed: expected exactly one sentinel-delimited payload."
        )

    payload_text = blocks[0].payload_text
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


def _trim_post_submit_text(current_text: str, baseline_text: str) -> str:
    """Return post-submit text when the current surface preserves the baseline prefix."""

    if baseline_text and current_text.startswith(baseline_text):
        return current_text[len(baseline_text) :]
    return current_text


def extract_sentinel_blocks(text: str) -> list[SentinelBlock]:
    """Extract standalone sentinel-delimited result blocks from *text*.

    A sentinel is considered "standalone" when its line, after stripping
    whitespace, equals the sentinel string exactly.  Sentinel names that
    appear inside prose, JSON string values, or other inline contexts are
    ignored.

    Returns zero or more :class:`SentinelBlock` instances, each carrying
    the raw payload text between the BEGIN and END delimiter lines.
    """

    lines = text.splitlines()
    blocks: list[SentinelBlock] = []
    i = 0
    while i < len(lines):
        if lines[i].strip() == MAIL_RESULT_BEGIN_SENTINEL:
            begin_line = i
            # Scan forward for matching standalone END sentinel.
            j = i + 1
            while j < len(lines):
                if lines[j].strip() == MAIL_RESULT_END_SENTINEL:
                    payload = "\n".join(lines[begin_line + 1 : j]).strip()
                    blocks.append(
                        SentinelBlock(
                            begin_line=begin_line,
                            end_line=j,
                            payload_text=payload,
                        )
                    )
                    i = j + 1
                    break
                j += 1
            else:
                # No matching END found — skip this BEGIN.
                i += 1
        else:
            i += 1
    return blocks


def _mailbox_command_error_from_backend(exc: BackendExecutionError) -> MailboxCommandError:
    detail = str(exc).strip() or "unknown backend failure"
    lowered = detail.lower()
    if any(token in lowered for token in ("busy", "in-flight", "already running", "active turn")):
        return MailboxCommandError(
            "Mailbox command could not start because the target session is busy or cannot accept a new turn."
        )
    return MailboxCommandError(f"Mailbox command failed: {detail}")
