"""AG-UI adapter boundary for Houmao gateway attachment routes."""

from houmao.ag_ui.connection import AgUiConnectionRecord, AgUiConnectionRegistry
from houmao.ag_ui.encoder import SSE_CONTENT_TYPE, AgUiSseEncoder, encode_sse_event
from houmao.ag_ui.models import (
    AgUiConnectInput,
    AgUiDetachResponse,
    AgUiEventType,
    AgUiRunsUnavailableResponse,
    AgUiStateSnapshotEvent,
    HoumaoAgUiCapabilitiesResponse,
)

__all__ = [
    "AgUiConnectInput",
    "AgUiConnectionRecord",
    "AgUiConnectionRegistry",
    "AgUiDetachResponse",
    "AgUiEventType",
    "AgUiRunsUnavailableResponse",
    "AgUiSseEncoder",
    "AgUiStateSnapshotEvent",
    "HoumaoAgUiCapabilitiesResponse",
    "SSE_CONTENT_TYPE",
    "encode_sse_event",
]
