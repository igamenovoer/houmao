"""AG-UI server-sent-event encoding helpers."""

from __future__ import annotations

from ag_ui.core import BaseEvent

SSE_CONTENT_TYPE = "text/event-stream"


class AgUiSseEncoder:
    """Encode AG-UI events as `text/event-stream` data frames."""

    def content_type(self) -> str:
        """Return the media type produced by this encoder."""

        return SSE_CONTENT_TYPE

    def encode(self, event: BaseEvent) -> str:
        """Return one AG-UI SSE data frame for an event."""

        return encode_sse_event(event)


def encode_sse_event(event: BaseEvent) -> str:
    """Encode one AG-UI event as `data: <camelCase-json>\\n\\n`."""

    return f"data: {event.model_dump_json(by_alias=True, exclude_none=True)}\n\n"


def encode_sse_comment(comment: str) -> str:
    """Encode one SSE comment frame for stream keepalive heartbeats."""

    safe_comment = comment.replace("\r", " ").replace("\n", " ")
    return f": {safe_comment}\n\n"
