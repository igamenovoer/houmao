"""Shared browser entry routes and ticket model for managed tmux terminals."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


GatewayTerminalEntryMode = Literal["view", "interact"]

TERMINAL_VIEW_PATH = "/v1/terminal/view"
TERMINAL_INTERACT_PATH = "/v1/admin/terminal/attach"
TERMINAL_ASSET_PATH = "/v1/terminal/assets/{name}"
TERMINAL_VIEW_TICKET_PATH = TERMINAL_VIEW_PATH + "/ticket"
TERMINAL_INTERACT_TICKET_PATH = TERMINAL_INTERACT_PATH + "/ticket"
TERMINAL_VIEW_STREAM_PATH = TERMINAL_VIEW_PATH + "/stream"
TERMINAL_INTERACT_STREAM_PATH = TERMINAL_INTERACT_PATH + "/stream"
TERMINAL_LOGIN_PATH = TERMINAL_INTERACT_PATH + "/login"
TERMINAL_LOGIN_PROVE_PATH = TERMINAL_LOGIN_PATH + "/{attempt_id}/prove"
TERMINAL_LOGIN_CLAIM_PATH = TERMINAL_LOGIN_PATH + "/{attempt_id}/claim"


def is_terminal_entry_path(path: str) -> bool:
    """Recognize terminal transport paths for error and security headers."""

    return path in {TERMINAL_VIEW_PATH, TERMINAL_INTERACT_PATH} or path.startswith(
        (TERMINAL_VIEW_PATH + "/", TERMINAL_INTERACT_PATH + "/", "/v1/terminal/assets/")
    )


class GatewayTerminalEntryTicketV1(BaseModel):
    """Return a private single-use browser URL, its mode, and the UTC expiry."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)

    url: str = Field(min_length=1, repr=False)
    expires_at_utc: str = Field(
        pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?(Z|\+00:00)$"
    )
    mode: GatewayTerminalEntryMode

    @field_validator("expires_at_utc")
    @classmethod
    def _validate_expiry(cls, value: str) -> str:
        """Require a real date and time in the gateway's UTC format."""

        datetime.fromisoformat(value)
        return value
