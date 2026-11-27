"""Stock Hermes plugin copied into each managed profile by Houmao."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import socket
from typing import Protocol
from collections.abc import Callable


_ORIGIN_ENV = "HOUMAO_HERMES_TOOL_ORIGIN"


class _PluginContext(Protocol):
    """The stock session environment hook used by this plugin."""

    def register_session_env(
        self, names: list[str], resolver: Callable[[str], dict[str, str | None]]
    ) -> None:
        """Register a resolver for local tool spawns in this profile."""


def register(ctx: _PluginContext) -> None:
    """Install the profile-scoped resolver using Hermes's public plugin hook."""

    socket_path = Path(__file__).with_name("broker-socket").read_text(encoding="utf-8").strip()
    runtime = importlib.import_module("hermes_constants")
    sessions = importlib.import_module("gateway.session_context")

    def resolve(session_id: str) -> dict[str, str | None]:
        """Issue evidence only in the native profile and session selected for this child."""

        try:
            if (
                not runtime.get_hermes_home_override()
                or sessions.bound_session_env("HERMES_SESSION_ID") != session_id
            ):
                return {_ORIGIN_ENV: None}
            request = json.dumps(
                {"op": "issue", "home": str(runtime.hermes_home_key()), "session": session_id}
            )
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
                peer.settimeout(2)
                peer.connect(socket_path)
                peer.sendall(request.encode() + b"\n")
                with peer.makefile("rb") as stream:
                    response = stream.readline(257)
            token = json.loads(response) if len(response) <= 256 else None
            if isinstance(token, str) and len(token) == 64 and token.isascii():
                return {_ORIGIN_ENV: token}
        except (OSError, ValueError):
            pass
        return {_ORIGIN_ENV: None}

    ctx.register_session_env([_ORIGIN_ENV], resolve)
