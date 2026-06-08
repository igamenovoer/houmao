"""Validated Houmao graphics artifacts for CopilotKit AG-UI rendering."""

from __future__ import annotations

import base64
from collections.abc import Mapping
import json
import re
from typing import Any, Literal, cast
from urllib.parse import urlparse

from ag_ui.core import BaseEvent, ToolCallArgsEvent, ToolCallEndEvent, ToolCallResultEvent, ToolCallStartEvent
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from houmao.ag_ui.state import JsonObject, JsonValue
from houmao.agents.realm_controller.backends.headless_output import CanonicalHeadlessEvent

HOUMAO_RENDER_GRAPHIC_TOOL_NAME = "houmao_render_graphic"
"""AG-UI tool-call name used by CopilotKit graphics renderers."""

HoumaoGraphicFormat = Literal["svg", "html_fragment", "image_url", "image_data_uri", "chart_json"]

_UNSAFE_INLINE_PATTERNS = (
    re.compile(r"<\s*script\b", re.IGNORECASE),
    re.compile(r"\son[a-z0-9_-]+\s*=", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"<\s*iframe\b", re.IGNORECASE),
)


class HoumaoGraphicArtifact(BaseModel):
    """Typed graphics artifact payload streamed through AG-UI tool calls."""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        populate_by_name=True,
    )

    title: str
    description: str | None = None
    format: HoumaoGraphicFormat
    content: Any = None
    content_url: str | None = None
    alt_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        """Require a non-empty graphics title."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be empty")
        return stripped

    @field_validator("description", "content_url", "alt_text")
    @classmethod
    def _optional_text_stripped(cls, value: str | None) -> str | None:
        """Normalize optional text fields."""

        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def _validate_format_payload(self) -> "HoumaoGraphicArtifact":
        """Validate format-specific content and safety rules."""

        if self.format == "svg":
            content = _required_string_content(self.content, field_name="content")
            _reject_unsafe_inline_content(content)
            if "<svg" not in content.lower():
                raise ValueError("svg content must contain an <svg element")
            return self
        if self.format == "html_fragment":
            content = _required_string_content(self.content, field_name="content")
            _reject_unsafe_inline_content(content)
            return self
        if self.format == "image_url":
            if self.content_url is None:
                raise ValueError("image_url graphics require contentUrl")
            _validate_safe_http_url(self.content_url)
            return self
        if self.format == "image_data_uri":
            content = _required_string_content(self.content, field_name="content")
            _validate_safe_image_data_uri(content)
            return self
        if self.format == "chart_json":
            self.content = _validated_chart_json_content(self.content)
            return self
        raise ValueError(f"Unsupported graphics format `{self.format}`.")


def extract_graphic_artifact_from_headless_event(
    event: CanonicalHeadlessEvent,
) -> HoumaoGraphicArtifact | None:
    """Return a validated graphic when a canonical event carries one explicitly."""

    if event.kind not in {"action_request", "action_result"}:
        return None
    data = event.data or {}
    if str(data.get("name", "")).strip() != HOUMAO_RENDER_GRAPHIC_TOOL_NAME:
        return None
    for key in ("arguments", "artifact", "result", "output"):
        candidate = data.get(key)
        payload = _payload_mapping(candidate)
        if payload is not None:
            return HoumaoGraphicArtifact.model_validate(payload)
    return None


def graphic_artifact_to_tool_events(
    *,
    artifact: HoumaoGraphicArtifact,
    parent_message_id: str,
    tool_call_id: str,
    emit_result: bool = False,
) -> list[BaseEvent]:
    """Build a CopilotKit-compatible AG-UI tool-call sequence for one artifact."""

    events: list[BaseEvent] = [
        ToolCallStartEvent(
            tool_call_id=tool_call_id,
            tool_call_name=HOUMAO_RENDER_GRAPHIC_TOOL_NAME,
            parent_message_id=parent_message_id,
        ),
        ToolCallArgsEvent(
            tool_call_id=tool_call_id,
            delta=artifact.model_dump_json(by_alias=True, exclude_none=True),
        ),
        ToolCallEndEvent(tool_call_id=tool_call_id),
    ]
    if emit_result:
        events.append(
            ToolCallResultEvent(
                message_id=f"{tool_call_id}:result",
                tool_call_id=tool_call_id,
                role="tool",
                content=json.dumps(
                    normalized_graphic_result_summary(artifact),
                    sort_keys=True,
                ),
            )
        )
    return events


def normalized_graphic_result_summary(artifact: HoumaoGraphicArtifact) -> JsonObject:
    """Return a compact normalized graphic result summary."""

    summary: JsonObject = {
        "title": artifact.title,
        "format": artifact.format,
    }
    if artifact.description is not None:
        summary["description"] = artifact.description
    if artifact.alt_text is not None:
        summary["altText"] = artifact.alt_text
    if artifact.content_url is not None:
        summary["contentUrl"] = artifact.content_url
    return summary


def _payload_mapping(value: object) -> Mapping[str, Any] | None:
    """Return one mapping payload, parsing JSON strings when needed."""

    if isinstance(value, Mapping):
        return cast(Mapping[str, Any], value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, Mapping):
            return cast(Mapping[str, Any], parsed)
    return None


def _required_string_content(value: object, *, field_name: str) -> str:
    """Require one string content field."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _reject_unsafe_inline_content(content: str) -> None:
    """Reject inline SVG or HTML content that contains unsafe constructs."""

    for pattern in _UNSAFE_INLINE_PATTERNS:
        if pattern.search(content):
            raise ValueError("graphics inline content contains unsafe script, handler, or URL data")


def _validate_safe_http_url(value: str) -> None:
    """Require an HTTP(S) URL without embedded script schemes."""

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("image_url graphics require a safe http or https contentUrl")
    if "javascript:" in value.lower():
        raise ValueError("image_url graphics must not use javascript URLs")


def _validate_safe_image_data_uri(value: str) -> None:
    """Require a safe base64 image data URI."""

    header, separator, encoded = value.partition(",")
    lowered_header = header.lower()
    if separator != "," or not lowered_header.startswith("data:image/"):
        raise ValueError("image_data_uri graphics require an image data URI")
    if "svg" in lowered_header or "html" in lowered_header:
        raise ValueError("image_data_uri graphics must not embed svg or html content")
    if ";base64" not in lowered_header:
        raise ValueError("image_data_uri graphics must be base64 encoded")
    try:
        base64.b64decode(encoded, validate=True)
    except ValueError as exc:
        raise ValueError("image_data_uri graphics contain invalid base64 data") from exc


def _validated_chart_json_content(value: object) -> JsonValue:
    """Return validated chart JSON content."""

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("chart_json graphics content must be valid JSON") from exc
        if not isinstance(parsed, dict | list):
            raise ValueError("chart_json graphics content must be a JSON object or array")
        return cast(JsonValue, parsed)
    if isinstance(value, dict | list):
        return value
    raise ValueError("chart_json graphics content must be a JSON object, array, or JSON string")
