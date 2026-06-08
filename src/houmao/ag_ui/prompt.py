"""Deterministic AG-UI run-input to Houmao prompt conversion."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from typing import Any, TypeGuard, cast

from ag_ui.core import RunAgentInput
from pydantic import BaseModel

from houmao.ag_ui.state import JsonObject, JsonValue


class AgUiPromptConversionError(ValueError):
    """Raised when AG-UI input cannot be converted into one Houmao prompt."""


@dataclass(frozen=True)
class AgUiWhitelistedForwardedProps:
    """Forwarded props allowed to affect Houmao runtime controls."""

    chat_session: JsonObject | None = None
    execution: JsonObject | None = None


@dataclass(frozen=True)
class AgUiPromptConversion:
    """Converted Houmao prompt and admitted runtime-control inputs."""

    prompt: str
    primary_message_id: str | None
    primary_message_role: str
    forwarded_props: AgUiWhitelistedForwardedProps


def convert_run_agent_input(run_input: RunAgentInput) -> AgUiPromptConversion:
    """Convert one AG-UI run input into a deterministic Houmao prompt."""

    messages = list(run_input.messages)
    _reject_unsupported_multimodal_messages(messages)
    primary_index = _latest_actionable_message_index(messages)
    if primary_index is None:
        raise AgUiPromptConversionError("AG-UI run input must include a user message or tool result.")

    primary_message = messages[primary_index]
    primary_text = _message_text(primary_message).strip()
    if not primary_text:
        raise AgUiPromptConversionError("AG-UI primary message content must not be empty.")

    whitelisted_forwarded_props = _whitelisted_forwarded_props(run_input.forwarded_props)
    prompt = _render_prompt(
        run_input=run_input,
        messages=messages,
        primary_index=primary_index,
        primary_text=primary_text,
        whitelisted_forwarded_props=whitelisted_forwarded_props,
    )
    return AgUiPromptConversion(
        prompt=prompt,
        primary_message_id=_message_id(primary_message),
        primary_message_role=_message_role(primary_message),
        forwarded_props=whitelisted_forwarded_props,
    )


def _latest_actionable_message_index(messages: Sequence[object]) -> int | None:
    """Return the latest user or tool-result message index."""

    selected: int | None = None
    for index, message in enumerate(messages):
        if _message_role(message) in {"user", "tool"}:
            selected = index
    return selected


def _reject_unsupported_multimodal_messages(messages: Sequence[object]) -> None:
    """Reject any non-text AG-UI input content before gateway admission."""

    for message in messages:
        role = _message_role(message)
        if role != "user":
            continue
        content = getattr(message, "content", None)
        if isinstance(content, str) or content is None:
            continue
        if not _is_non_string_sequence(content):
            continue
        for part in content:
            part_type = str(getattr(part, "type", "")).strip().lower()
            if part_type == "text":
                continue
            label = part_type or type(part).__name__
            raise AgUiPromptConversionError(
                f"Unsupported AG-UI multimodal input content type `{label}`."
            )


def _message_text(message: object) -> str:
    """Return one AG-UI message's text content."""

    content = getattr(message, "content", None)
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if _is_non_string_sequence(content):
        parts: list[str] = []
        for part in content:
            part_type = str(getattr(part, "type", "")).strip().lower()
            if part_type != "text":
                label = part_type or type(part).__name__
                raise AgUiPromptConversionError(
                    f"Unsupported AG-UI multimodal input content type `{label}`."
                )
            text = getattr(part, "text", "")
            parts.append(str(text))
        return "\n".join(part for part in parts if part)
    return str(content)


def _render_prompt(
    *,
    run_input: RunAgentInput,
    messages: Sequence[object],
    primary_index: int,
    primary_text: str,
    whitelisted_forwarded_props: AgUiWhitelistedForwardedProps,
) -> str:
    """Render deterministic Houmao prompt text."""

    primary_message = messages[primary_index]
    sections = [
        "AG-UI task submission",
        "",
        "Primary task:",
        _primary_task_text(primary_message=primary_message, primary_text=primary_text),
        "",
        "Structured AG-UI context:",
        _json_block(
            {
                "threadId": run_input.thread_id,
                "runId": run_input.run_id,
                "parentRunId": run_input.parent_run_id,
                "primaryMessageId": _message_id(primary_message),
                "primaryMessageRole": _message_role(primary_message),
            }
        ),
    ]
    prior_messages = [
        _message_record(message)
        for message in messages[:primary_index]
        if _message_role(message) != "activity"
    ]
    if prior_messages:
        sections.extend(["", "Prior AG-UI messages:", _json_block(prior_messages)])
    if run_input.state:
        sections.extend(["", "AG-UI state:", _json_block(_jsonable(run_input.state))])
    if run_input.context:
        sections.extend(["", "AG-UI context entries:", _json_block(_jsonable(run_input.context))])
    if run_input.tools:
        sections.extend(["", "AG-UI declared tools:", _json_block(_jsonable(run_input.tools))])
    forwarded_context = _forwarded_props_prompt_context(
        run_input.forwarded_props,
        whitelisted_forwarded_props,
    )
    if forwarded_context:
        sections.extend(["", "AG-UI forwarded props:", _json_block(forwarded_context)])
    if run_input.resume is not None:
        sections.extend(["", "AG-UI resume data:", _json_block(_jsonable(run_input.resume))])
    return "\n".join(sections).strip() + "\n"


def _primary_task_text(*, primary_message: object, primary_text: str) -> str:
    """Render the current user task or tool-result payload."""

    role = _message_role(primary_message)
    if role == "tool":
        tool_call_id = getattr(primary_message, "tool_call_id", None)
        if tool_call_id is None:
            return f"Tool result:\n{primary_text}"
        return f"Tool result for toolCallId `{tool_call_id}`:\n{primary_text}"
    return primary_text


def _message_record(message: object) -> JsonObject:
    """Return a deterministic JSON projection for one AG-UI message."""

    payload = _jsonable(message)
    if isinstance(payload, dict):
        return payload
    return {"value": payload}


def _whitelisted_forwarded_props(value: object) -> AgUiWhitelistedForwardedProps:
    """Extract forwarded props allowed to affect gateway runtime controls."""

    forwarded = _mapping(value)
    houmao = _mapping(forwarded.get("houmao")) if forwarded is not None else None
    if houmao is None:
        return AgUiWhitelistedForwardedProps()
    chat_session = _json_object_or_none(houmao.get("chatSession", houmao.get("chat_session")))
    execution = _json_object_or_none(houmao.get("execution"))
    return AgUiWhitelistedForwardedProps(chat_session=chat_session, execution=execution)


def _forwarded_props_prompt_context(
    value: object,
    whitelisted: AgUiWhitelistedForwardedProps,
) -> JsonObject | None:
    """Return non-secret forwarded-prop metadata for inert prompt context."""

    forwarded = _mapping(value)
    if forwarded is None:
        return None
    omitted: list[str] = []
    for key in sorted(str(key) for key in forwarded):
        if key != "houmao":
            omitted.append(key)
    houmao = _mapping(forwarded.get("houmao"))
    if houmao is not None:
        for key in sorted(str(key) for key in houmao):
            if key not in {"chatSession", "chat_session", "execution"}:
                omitted.append(f"houmao.{key}")
    context: JsonObject = {}
    allowed: JsonObject = {}
    if whitelisted.chat_session is not None:
        allowed["chatSession"] = whitelisted.chat_session
    if whitelisted.execution is not None:
        allowed["execution"] = whitelisted.execution
    if allowed:
        context["allowedHoumaoControls"] = allowed
    if omitted:
        context["omittedForwardedPropKeys"] = cast(JsonValue, omitted)
    return context or None


def _json_object_or_none(value: object) -> JsonObject | None:
    """Return a JSON object when the input is mapping-like."""

    mapping = _mapping(value)
    if mapping is None:
        return None
    return {str(key): _jsonable(item) for key, item in mapping.items()}


def _json_block(value: object) -> str:
    """Return stable fenced JSON text without Markdown-dependent parsing."""

    return json.dumps(_jsonable(value), sort_keys=True, indent=2)


def _jsonable(value: object) -> JsonValue:
    """Return a JSON-compatible projection for a Pydantic or Python value."""

    if isinstance(value, BaseModel):
        return _jsonable(value.model_dump(mode="json", by_alias=True, exclude_none=True))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if _is_non_string_sequence(value):
        return [_jsonable(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def _mapping(value: object) -> Mapping[str, Any] | None:
    """Return a mapping view for dict-like values."""

    if isinstance(value, Mapping):
        return cast(Mapping[str, Any], value)
    return None


def _is_non_string_sequence(value: object) -> TypeGuard[Sequence[object]]:
    """Return whether value is a sequence but not string-like."""

    return isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray)


def _message_role(message: object) -> str:
    """Return one AG-UI message role."""

    return str(getattr(message, "role", ""))


def _message_id(message: object) -> str | None:
    """Return one AG-UI message id when present."""

    value = getattr(message, "id", None)
    if value is None:
        return None
    return str(value)
