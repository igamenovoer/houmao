"""Describe native human interfaces separately from managed process supervision."""

from __future__ import annotations

from ipaddress import ip_address
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


NativeSurfaceKind = Literal["terminal", "web"]


def validate_web_origin(value: str) -> str:
    """Normalize a clean HTTP loopback origin with an explicit port."""

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        loopback = hostname == "localhost" or (
            hostname is not None and ip_address(hostname).is_loopback
        )
        valid = (
            parsed.scheme == "http"
            and loopback
            and parsed.port is not None
            and 0 < parsed.port <= 65535
            and parsed.path in {"", "/"}
            and parsed.username is None
            and parsed.password is None
            and not any(character.isspace() for character in value)
            and not any(delimiter in value for delimiter in ("?", "#", "\\"))
            and value.rstrip("/") == f"http://{parsed.netloc}"
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("Web native surface requires a token-free HTTP loopback origin")
    return value.rstrip("/")


class TerminalNativeSurfaceV1(BaseModel):
    """Identify an actual terminal interface rather than a supervisor log pane."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    kind: Literal["terminal"] = "terminal"
    tmux_session_name: str = Field(min_length=1)
    pane_id: str | None = None


class WebNativeSurfaceV1(BaseModel):
    """Expose only a loopback browser origin and the exact bound native session."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    kind: Literal["web"] = "web"
    origin: str
    native_session_id: str = Field(min_length=1)

    @field_validator("origin")
    @classmethod
    def _validate_origin(cls, value: str) -> str:
        """Reject signed locations, credentials, remote hosts, and non-origin paths."""

        return validate_web_origin(value)


NativeSurfaceV1 = Annotated[
    TerminalNativeSurfaceV1 | WebNativeSurfaceV1, Field(discriminator="kind")
]
