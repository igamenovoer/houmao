"""AG-UI server-sent-event encoding helpers."""

from __future__ import annotations

from ag_ui.core import BaseEvent

SSE_CONTENT_TYPE = "text/event-stream"


class AgUiSseEncoder:
    """Encode AG-UI events as `text/event-stream` data frames."""

    def content_type(self) -> str:
        """Return the media type produced by this encoder."""

        return SSE_CONTENT_TYPE

    def encode(self, event: BaseEvent, *, event_id: str | None = None) -> str:
        """Return one AG-UI SSE data frame for an event."""

        return encode_sse_event(event, event_id=event_id)


def encode_sse_event(event: BaseEvent, *, event_id: str | None = None) -> str:
    """Encode one AG-UI event as a server-sent-event frame."""

    data_line = f"data: {event.model_dump_json(by_alias=True, exclude_none=True)}"
    if event_id is None:
        return f"{data_line}\n\n"
    safe_event_id = event_id.replace("\r", " ").replace("\n", " ")
    return f"id: {safe_event_id}\n{data_line}\n\n"


def encode_sse_comment(comment: str) -> str:
    """Encode one SSE comment frame for stream keepalive heartbeats."""

    safe_comment = comment.replace("\r", " ").replace("\n", " ")
    return f": {safe_comment}\n\n"
