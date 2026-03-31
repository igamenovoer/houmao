"""Runtime-owned mailbox prompt and result helpers.

Sentinel parsing remains available for preview and diagnostics, but TUI-mediated
mail commands now complete on request lifecycle rather than exact mailbox-result
schema recovery.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Literal, cast

from houmao.agents.mailbox_runtime_models import MailboxResolvedConfig
from houmao.agents.mailbox_runtime_support import (
    mailbox_gateway_skill_name,
    mailbox_skill_name,
    projected_mailbox_skill_document_path,
    mailbox_gateway_skill_reference,
    mailbox_skill_reference,
    resolve_live_mailbox_binding,
)
from houmao.mailbox import resolve_filesystem_mailbox_paths
from houmao.agents.mailbox_runtime_models import (
    FilesystemMailboxResolvedConfig,
)

from .backends.shadow_parser_core import DialogProjection
from .errors import BackendExecutionError, MailboxCommandError, MailboxResultParseError
from .models import LaunchPlan, SessionEvent

MailOperation = Literal["check", "send", "reply", "mark-read"]
MailCommandOperation = Literal["status", "check", "send", "reply", "mark-read"]
MailExecutionPath = Literal["manager_direct", "gateway_backed", "tui_submission"]
MailSubmissionStatus = Literal["submitted", "rejected", "busy", "interrupted", "tui_error"]

MAIL_REQUEST_VERSION = 1
MAIL_RESULT_BEGIN_SENTINEL = "HOUMAO_MAIL_RESULT_BEGIN"
MAIL_RESULT_END_SENTINEL = "HOUMAO_MAIL_RESULT_END"
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


_TUI_SUBMISSION_ERROR_DETAIL_MAX_CHARS = 400


def build_verified_mail_command_result(
    *,
    operation: MailCommandOperation,
    execution_path: Literal["manager_direct", "gateway_backed"],
    payload: object,
) -> dict[str, Any]:
    """Build one authoritative manager mail result envelope."""

    normalized = _normalize_mail_payload(payload)
    result: dict[str, Any] = {
        "schema_version": int(normalized.get("schema_version", 1)),
        "operation": operation,
        "authoritative": True,
        "status": "verified",
        "execution_path": execution_path,
    }
    result.update(normalized)
    result["operation"] = operation
    result["authoritative"] = True
    result["status"] = "verified"
    result["execution_path"] = execution_path
    return result


def build_tui_submission_result(
    *,
    prompt_request: MailPromptRequest,
    mailbox: MailboxResolvedConfig,
    events: list[SessionEvent] | None = None,
    status: MailSubmissionStatus | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    """Build one non-authoritative TUI submission result envelope."""

    effective_status = status or _tui_submission_status_from_events(events)
    result: dict[str, Any] = {
        "schema_version": 1,
        "operation": prompt_request.operation,
        "authoritative": False,
        "status": effective_status,
        "execution_path": "tui_submission",
        "transport": mailbox.transport,
        "principal_id": mailbox.principal_id,
        "address": mailbox.address,
        "bindings_version": mailbox.bindings_version,
        "request_id": prompt_request.request_id,
        "verification_required": True,
        "verification_paths": _verification_paths_for_mailbox(mailbox),
    }
    if detail is not None and detail.strip():
        result["detail"] = detail.strip()
    if events:
        submitted_event = next((event for event in events if event.kind == "submitted"), None)
        if submitted_event is not None:
            result["submitted_at_utc"] = submitted_event.timestamp_utc

        diagnostics = _tui_submission_diagnostics_from_events(events)
        if diagnostics:
            result["tui_diagnostics"] = diagnostics

        preview_payload = _preview_mail_result_from_events(
            events,
            request_id=prompt_request.request_id,
            operation=prompt_request.operation,
            mailbox=mailbox,
        )
        if preview_payload is not None:
            result["preview_result"] = preview_payload
    return result


def build_tui_submission_result_from_backend_error(
    *,
    prompt_request: MailPromptRequest,
    mailbox: MailboxResolvedConfig,
    exc: BackendExecutionError,
) -> dict[str, Any]:
    """Normalize one backend execution failure into a submission-only result."""

    status, detail = _classify_tui_submission_backend_error(exc)
    return build_tui_submission_result(
        prompt_request=prompt_request,
        mailbox=mailbox,
        status=status,
        detail=detail,
    )


def prepare_mail_prompt(
    *,
    launch_plan: LaunchPlan,
    operation: MailOperation,
    args: dict[str, Any],
    prefer_live_gateway: bool = False,
    tmux_session_name: str | None = None,
) -> MailPromptRequest:
    """Build one runtime-owned mailbox prompt for a live session."""

    mailbox = ensure_mailbox_command_ready(
        launch_plan,
        tmux_session_name=tmux_session_name,
    )
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
    prompt_lines = _mail_prompt_instruction_lines(
        launch_plan=launch_plan,
        mailbox=mailbox,
        operation=operation,
        args=args,
        prefer_live_gateway=prefer_live_gateway,
    )
    prompt_lines.extend(
        [
            "The sentinel JSON is machine-owned. Do not paste raw helper output directly when it omits required contract keys.",
            "Return only the contracted fields and omit long paths or verbose nested helper payloads from the sentinel block.",
            "Use this exact result shape:",
            "```json",
            json.dumps(
                _mail_result_contract_template(
                    request_id=request_id,
                    operation=operation,
                    mailbox=mailbox,
                ),
                indent=2,
                sort_keys=True,
            ),
            "```",
            (
                "Return exactly one JSON result between "
                f"`{MAIL_RESULT_BEGIN_SENTINEL}` and `{MAIL_RESULT_END_SENTINEL}`."
            ),
            "",
            "HOUMAO_MAIL_REQUEST:",
            "```json",
            json.dumps(request_payload, indent=2, sort_keys=True),
            "```",
        ]
    )
    prompt = "\n".join(prompt_lines)
    return MailPromptRequest(
        request_id=request_id,
        operation=operation,
        prompt=prompt,
    )


def ensure_mailbox_command_ready(
    launch_plan: LaunchPlan,
    *,
    tmux_session_name: str | None = None,
) -> MailboxResolvedConfig:
    """Validate that a session can safely run runtime-owned mailbox commands."""

    mailbox = launch_plan.mailbox
    if mailbox is None:
        raise MailboxCommandError("Target session is not mailbox-enabled.")
    del tmux_session_name
    try:
        mailbox = resolve_live_mailbox_binding(durable_mailbox=mailbox).mailbox
    except ValueError as exc:
        raise MailboxCommandError(
            "Target session mailbox binding is not actionable through the persisted runtime "
            f"mailbox binding: {exc}"
        ) from exc
    if isinstance(mailbox, FilesystemMailboxResolvedConfig):
        paths = resolve_filesystem_mailbox_paths(mailbox.filesystem_root)
        required_files = (
            paths.protocol_version_file,
            paths.sqlite_path,
            paths.rules_dir / "README.md",
            paths.rules_protocols_dir / "filesystem-mailbox-v1.md",
        )
        missing = [path for path in required_files if not path.is_file()]
        if missing:
            missing_labels = ", ".join(str(path.relative_to(paths.root)) for path in missing)
            raise MailboxCommandError(
                f"Filesystem mailbox bootstrap assets are missing or incomplete: {missing_labels}"
            )
        return mailbox

    credential_file = mailbox.credential_file
    if credential_file is None or not credential_file.is_file():
        raise MailboxCommandError(
            "Stalwart mailbox bootstrap is incomplete: the session credential file is missing."
        )
    return mailbox


def _mail_prompt_instruction_lines(
    *,
    launch_plan: LaunchPlan,
    mailbox: MailboxResolvedConfig,
    operation: MailOperation,
    args: dict[str, Any],
    prefer_live_gateway: bool,
) -> list[str]:
    skill_name = mailbox_skill_name(mailbox)
    gateway_skill_name = mailbox_gateway_skill_name()
    gateway_skill_path = projected_mailbox_skill_document_path(
        tool=launch_plan.tool,
        home_path=launch_plan.home_path,
        skill_reference=mailbox_gateway_skill_reference(),
    )
    transport_skill_path = projected_mailbox_skill_document_path(
        tool=launch_plan.tool,
        home_path=launch_plan.home_path,
        skill_reference=mailbox_skill_reference(mailbox),
    )
    installed_skill_lines: list[str]
    if gateway_skill_path.is_file() and transport_skill_path.is_file():
        installed_skill_lines = [
            (
                f"Use the installed Houmao mailbox gateway skill `{gateway_skill_name}` for "
                "this mailbox operation."
            ),
            (
                "Use the installed runtime-owned Houmao mailbox skills directly. Do not search "
                "the repository for a `skills/.../SKILL.md` path and do not infer any skill "
                "install location from the current working directory."
            ),
            (
                f"Use the transport-specific Houmao mailbox skill `{skill_name}` only for "
                "transport-local context and no-gateway fallback."
            ),
        ]
    else:
        installed_skill_lines = [
            "Houmao mailbox skills are not installed for this session.",
            "Use the resolver and the supported mailbox contract directly for this operation.",
        ]
    lines = [
        *installed_skill_lines,
        (
            "Before any direct mailbox access, resolve current mailbox state through the "
            "manager-owned helper `pixi run houmao-mgr agents mail resolve-live`."
        ),
        (
            "Use only the structured fields returned by that helper. Do not guess sender "
            "identity or mailbox endpoints, and do not scrape tmux state directly."
        ),
        "Only mark messages read after the message has actually been processed successfully.",
    ]
    if prefer_live_gateway:
        lines.append(
            "Prefer the live gateway mailbox facade for shared mailbox operations, and obtain the exact `/v1/mail/*` endpoint from the `gateway.base_url` returned by the runtime-owned `resolve-live` helper."
        )

    if isinstance(mailbox, FilesystemMailboxResolvedConfig):
        lines.extend(
            [
                "Inspect the shared mailbox `rules/` directory first for mailbox-local policy guidance.",
                (
                    "Treat shared `rules/` content as policy guidance, not as the ordinary public "
                    "execution contract for send, reply, check, or mark-read workflows."
                ),
            ]
        )
    elif not prefer_live_gateway:
        lines.extend(
            [
                "Use the returned `mailbox.stalwart.*` fields for direct mailbox access when no live gateway mailbox facade is available.",
                "Do not use filesystem mailbox `rules/`, SQLite paths, lock files, or projection assumptions for this transport.",
            ]
        )
    return lines


def _filesystem_send_payload_template(args: dict[str, Any]) -> dict[str, Any] | None:
    """Return one concrete `deliver_message.py` payload template when possible."""

    sender = args.get("resolved_sender")
    to = args.get("resolved_to")
    cc = args.get("resolved_cc")
    subject = args.get("subject")
    body_content = args.get("body_content")
    attachments = args.get("attachments")
    if not isinstance(sender, dict) or not isinstance(to, list) or not isinstance(cc, list):
        return None
    if not isinstance(subject, str) or not isinstance(body_content, str):
        return None
    if not isinstance(attachments, list):
        attachments = []
    return {
        "staged_message_path": "<resolve-live.mailbox.filesystem.root>/staging/<message-id>.md",
        "message_id": "msg-YYYYMMDDTHHMMSSZ-<uuid4-no-dashes>",
        "thread_id": "msg-YYYYMMDDTHHMMSSZ-<uuid4-no-dashes>",
        "created_at_utc": "YYYY-MM-DDTHH:MM:SSZ",
        "sender": sender,
        "to": to,
        "cc": cc,
        "reply_to": [],
        "subject": subject,
        "attachments": attachments,
        "headers": {},
    }


def _mail_result_contract_template(
    *,
    request_id: str,
    operation: MailOperation,
    mailbox: MailboxResolvedConfig,
) -> dict[str, Any]:
    """Return the exact machine result contract template for one operation."""

    payload: dict[str, Any] = {
        "ok": True,
        "request_id": request_id,
        "operation": operation,
        "transport": mailbox.transport,
        "principal_id": mailbox.principal_id,
    }
    if operation == "send":
        payload["message_id"] = "msg-YYYYMMDDTHHMMSSZ-<uuid4-no-dashes>"
        payload["recipient_count"] = 1
    elif operation == "reply":
        payload["message_id"] = "msg-YYYYMMDDTHHMMSSZ-<uuid4-no-dashes>"
    elif operation == "mark-read":
        payload["message_ref"] = "<opaque message_ref>"
        payload["read"] = True
    elif operation == "check":
        payload["message_count"] = 0
        payload["messages"] = []
    return payload


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
        if not isinstance(text, str):
            continue
        if not extract_sentinel_blocks(text):
            continue
        return True
    return False


def shadow_mail_result_for_request_reached(
    surface_payloads: tuple[dict[str, str], ...],
    *,
    request_id: str,
    operation: MailOperation,
    mailbox: MailboxResolvedConfig,
) -> bool:
    """Return whether one shadow surface contains a parseable result for the active request."""

    for surface in surface_payloads:
        text = surface.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        try:
            _parse_mail_result_text(
                text,
                request_id=request_id,
                operation=operation,
                mailbox=mailbox,
            )
        except MailboxResultParseError:
            continue
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
        return build_tui_submission_result_from_backend_error(
            prompt_request=prompt_request,
            mailbox=mailbox,
            exc=exc,
        )

    return build_tui_submission_result(
        prompt_request=prompt_request,
        mailbox=mailbox,
        events=events,
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


def _event_mail_result_surface_candidates(
    event: SessionEvent,
) -> tuple[_MailResultTextSurface, ...]:
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
        for payload_index, payload_text in enumerate(
            _event_payload_text_candidates(event), start=1
        ):
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


def _normalize_mail_payload(payload: object) -> dict[str, Any]:
    """Normalize one model-like payload into a JSON-compatible dict."""

    if isinstance(payload, dict):
        return dict(payload)
    model_dump = getattr(payload, "model_dump", None)
    if callable(model_dump):
        normalized = model_dump(mode="json")
        if isinstance(normalized, dict):
            return normalized
    raise TypeError(f"Unsupported mail payload type: {type(payload)!r}")


def _tui_submission_status_from_events(
    events: list[SessionEvent] | None,
) -> MailSubmissionStatus:
    """Infer submission-only status from one TUI event stream."""

    if not events:
        return "submitted"
    explicit_status = _event_payload_submission_status(events)
    if explicit_status is not None:
        return explicit_status
    last_payload = _last_event_payload(events)
    canonical_status = last_payload.get("canonical_runtime_status")
    if canonical_status == "waiting_user_answer":
        return "rejected"
    if canonical_status == "interrupted":
        return "interrupted"
    if canonical_status == "error":
        return "tui_error"
    if any(event.kind == "interrupted" for event in events):
        return "interrupted"
    return "submitted"


def _event_payload_submission_status(
    events: list[SessionEvent],
) -> MailSubmissionStatus | None:
    """Return one explicit submission status surfaced by a backend event payload."""

    for event in reversed(events):
        payload = event.payload
        if not isinstance(payload, dict):
            continue
        status = payload.get("mail_submission_status")
        if status in {"submitted", "rejected", "busy", "interrupted", "tui_error"}:
            return cast(MailSubmissionStatus, status)
    return None


def _last_event_payload(events: list[SessionEvent]) -> dict[str, Any]:
    """Return the last dict payload present in one event list."""

    for event in reversed(events):
        if isinstance(event.payload, dict):
            return event.payload
    return {}


def _tui_submission_diagnostics_from_events(events: list[SessionEvent]) -> dict[str, Any]:
    """Extract compact TUI diagnostics from one event stream."""

    payload = _last_event_payload(events)
    if not payload:
        return {}
    diagnostics: dict[str, Any] = {}
    for key in (
        "canonical_runtime_status",
        "raw_backend_status",
        "parsing_mode",
        "parser_family",
        "output_source_mode",
        "surface_assessment",
        "mode_diagnostics",
    ):
        if key in payload:
            diagnostics[key] = payload[key]
    return diagnostics


def _preview_mail_result_from_events(
    events: list[SessionEvent],
    *,
    request_id: str,
    operation: MailOperation,
    mailbox: MailboxResolvedConfig,
) -> dict[str, Any] | None:
    """Return one optional non-authoritative parsed preview payload."""

    try:
        return parse_mail_result(
            events,
            request_id=request_id,
            operation=operation,
            mailbox=mailbox,
        )
    except MailboxCommandError:
        return None


def _verification_paths_for_mailbox(mailbox: MailboxResolvedConfig) -> list[str]:
    """Return generic follow-up verification guidance for one submission-only result."""

    paths = [
        "Use manager-owned follow-up such as `houmao-mgr agents mail status` or `houmao-mgr agents mail check` when that authority is available.",
    ]
    if mailbox.transport == "filesystem":
        paths.append(
            "Inspect the shared filesystem mailbox state or canonical message documents if transport-owned confirmation is required."
        )
    else:
        paths.append(
            "Verify through the transport-native mailbox state for the active email service."
        )
    return paths


def _classify_tui_submission_backend_error(
    exc: BackendExecutionError,
) -> tuple[MailSubmissionStatus, str]:
    """Map one backend execution failure to a non-authoritative submission status."""

    detail = str(exc).strip() or "unknown backend failure"
    lowered = detail.lower()
    if any(token in lowered for token in ("busy", "in-flight", "already running", "active turn")):
        return "busy", detail
    if any(
        token in lowered
        for token in (
            "operator interaction",
            "interactive user selection",
            "awaiting_operator",
            "waiting_user_answer",
        )
    ):
        return "rejected", detail
    if "interrupt" in lowered:
        return "interrupted", detail
    trimmed = detail
    if len(trimmed) > _TUI_SUBMISSION_ERROR_DETAIL_MAX_CHARS:
        trimmed = f"{trimmed[:_TUI_SUBMISSION_ERROR_DETAIL_MAX_CHARS].rstrip()}..."
    return "tui_error", trimmed
