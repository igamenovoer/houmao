"""Operation-scoped tmux server selection for execution-bound runtimes.

The selector belongs to the addressed runtime, rather than to the process
environment. Context variables keep nested operations and concurrent callers
independent without rewriting the enclosing agent's tmux environment.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
import os
from pathlib import Path

_SOCKET_PATH: ContextVar[str | None] = ContextVar("houmao_tmux_socket_path", default=None)


def validate_tmux_socket_path(value: str | Path) -> str:
    """Validate an owner-local socket path without resolving it on another host."""

    text = str(value)
    if not text or "\x00" in text or not Path(text).is_absolute():
        raise ValueError("tmux socket_path must be a non-empty absolute owner-local path")
    return text


def current_tmux_socket_path() -> str | None:
    """Return the explicit socket selector for this operation, if bound."""

    return _SOCKET_PATH.get()


def capture_tmux_socket_path(env: Mapping[str, str] | None = None) -> str:
    """Capture the scoped, enclosing, or native owner-default socket selector.

    This performs no tmux operation and does not create a server. Callers persist
    the result at birth or join and restore it for subsequent runtime operations.
    """

    selected = current_tmux_socket_path()
    if selected is not None:
        return selected
    source = os.environ if env is None else env
    inherited = source.get("TMUX", "")
    if inherited:
        # Native TMUX is <socket path>,<server pid>,<session id>. Paths can
        # contain commas, so split the two trailing native fields only.
        components = inherited.rsplit(",", 2)
        if len(components) != 3 or not all(part.isdigit() for part in components[1:]):
            raise ValueError("Cannot capture malformed enclosing TMUX socket authority")
        return validate_tmux_socket_path(components[0])
    root = Path(source.get("TMUX_TMPDIR", "/tmp"))
    if not root.is_absolute():
        raise ValueError("TMUX_TMPDIR must be absolute when capturing tmux authority")
    return str(root / f"tmux-{os.getuid()}" / "default")


@contextmanager
def tmux_server_scope(socket_path: str | Path | None) -> Iterator[None]:
    """Bind a runtime socket, retaining enclosing authority when none is supplied."""

    selected = (
        validate_tmux_socket_path(socket_path)
        if socket_path is not None
        else current_tmux_socket_path()
    )
    token = _SOCKET_PATH.set(selected)
    try:
        yield
    finally:
        _SOCKET_PATH.reset(token)


def tmux_argv(args: Sequence[str]) -> list[str]:
    """Build tmux argv using the operation's explicit socket when available."""

    socket_path = current_tmux_socket_path()
    selector = ["-S", socket_path] if socket_path is not None else []
    return ["tmux", *selector, *args]


def tmux_subprocess_environment() -> dict[str, str] | None:
    """Remove enclosing tmux selectors only for explicitly bound subprocesses."""

    if current_tmux_socket_path() is None:
        return None
    return {key: value for key, value in os.environ.items() if key not in {"TMUX", "TMUX_PANE"}}
