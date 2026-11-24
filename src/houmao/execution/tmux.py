"""Operation-scoped tmux selection and checked terminal operations.

The selector belongs to the addressed runtime, rather than to the process
environment. Context variables keep nested operations and concurrent callers
independent without rewriting the enclosing agent's tmux environment.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess

import libtmux
from libtmux.common import escape_trailing_separator
from libtmux.exc import LibTmuxException

_SOCKET_PATH: ContextVar[str | None] = ContextVar("houmao_tmux_socket_path", default=None)
_DISPATCHING: ContextVar[bool] = ContextVar("houmao_libtmux_dispatching", default=False)
_PRIVATE_COMMANDS = frozenset(
    {
        "capture-pane",
        "load-buffer",
        "new-session",
        "new-window",
        "paste-buffer",
        "respawn-pane",
        "send-keys",
        "set-environment",
        "show-environment",
        "show-buffer",
        "split-window",
    }
)
_PANE_FIELDS = (
    "pane_id",
    "session_id",
    "session_name",
    "window_id",
    "window_index",
    "window_name",
    "pane_index",
    "pane_active",
    "pane_dead",
    "pane_pid",
    "pane_width",
    "pane_height",
)
_PANE_FORMAT = "\t".join(f"#{{{name}}}" for name in _PANE_FIELDS)


class _DispatchLogFilter(logging.Filter):
    """Keep libtmux argument and output logging out of Houmao operations."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Leave logging outside adapter calls to the caller's configuration."""

        return not _DISPATCHING.get()


logging.getLogger("libtmux.common").addFilter(_DispatchLogFilter())


class TmuxCommandError(RuntimeError):
    """A tmux action failed, with its exit status when one was available."""

    def __init__(self, message: str, *, returncode: int | None = None) -> None:
        super().__init__(message)
        self.returncode = returncode


class TmuxObservationError(TmuxCommandError):
    """The command did not establish whether the target exists."""


class TmuxObservationUnavailable(TmuxObservationError):
    """The server did not complete the requested observation."""


class TmuxInvalidObservation(TmuxObservationError):
    """The server returned a result that cannot establish a target binding."""


@dataclass(frozen=True)
class TmuxCommandResult:
    """A command result with payload fields omitted from its representation."""

    args: tuple[str, ...] = field(repr=False)
    returncode: int
    stdout: str = field(repr=False)
    stderr: str = field(repr=False)

    def require_success(self) -> None:
        """Raise a checked error, including a status even for a silent failure."""

        if self.returncode != 0:
            detail = f": {self.stderr.strip()}" if self.stderr.strip() else ""
            raise TmuxCommandError(
                f"tmux {self.args[0]} exited with status {self.returncode}{detail}",
                returncode=self.returncode,
            )


@dataclass(frozen=True)
class TmuxPaneRecord:
    """One pane observed in an exact session on the selected server."""

    pane_id: str
    session_name: str
    window_id: str
    window_index: str
    window_name: str
    pane_index: str
    pane_active: bool
    pane_dead: bool = False
    pane_pid: int | None = None
    session_id: str | None = None
    pane_width: int | None = None
    pane_height: int | None = None


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
    default_socket = _native_default_socket(source)
    if not default_socket.is_absolute():
        raise ValueError("TMUX_TMPDIR must be absolute when capturing tmux authority")
    return str(default_socket)


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


class TmuxServer:
    """Bind one terminal operation's commands to its selected owner socket."""

    def __init__(
        self, socket_path: str | Path | None = None, *, executable: str | None = None
    ) -> None:
        self.m_socket_path: str = (
            capture_tmux_socket_path()
            if socket_path is None
            else validate_tmux_socket_path(socket_path)
        )
        self.m_executable: str | None = executable

    @property
    def socket_path(self) -> str:
        """Return the bound socket without consulting the enclosing environment."""

        return self.m_socket_path

    def command(
        self, args: Sequence[str], *, sensitive: bool = False, no_start: bool = False
    ) -> TmuxCommandResult:
        """Dispatch on the bound libtmux server and preserve the exit status."""

        if not args or args[0].startswith("-"):
            raise ValueError("Expected a tmux subcommand without server options")
        operation, *arguments = args
        private = sensitive or operation in _PRIVATE_COMMANDS
        token = _DISPATCHING.set(True)
        try:
            server = libtmux.Server(socket_path=self.m_socket_path, tmux_bin=self.m_executable)
            result = (
                server.cmd("-N", operation, *arguments)
                if no_start
                else server.cmd(operation, *arguments)
            )
        except (LibTmuxException, OSError, ValueError) as exc:
            raise TmuxCommandError(
                f"Could not run tmux {operation} ({type(exc).__name__})"
            ) from None
        finally:
            _DISPATCHING.reset(token)
        return TmuxCommandResult(
            (operation,) if private else tuple(args),
            result.returncode,
            _lines_to_text(result.stdout) if result.returncode == 0 or not private else "",
            _lines_to_text(result.stderr)
            if not private
            else _private_diagnostic(operation, result.stderr),
        )

    def checked_command(
        self, args: Sequence[str], *, sensitive: bool = False, no_start: bool = False
    ) -> TmuxCommandResult:
        """Require the bound command to succeed without replaying it on failure."""

        result = self.command(args, sensitive=sensitive, no_start=no_start)
        result.require_success()
        return result

    def list_sessions(self, *, allow_missing_server: bool = False) -> set[str]:
        """List exact names, optionally treating a cold socket as empty during startup."""

        result = self._observe_command(["list-sessions", "-F", "#{session_name}"])
        if (
            allow_missing_server
            and result.returncode == 1
            and result.stderr.strip()
            in {
                f"no server running on {self.m_socket_path}",
                f"error connecting to {self.m_socket_path} (No such file or directory)",
            }
        ):
            return set()
        _require_observation(result)
        return set(result.stdout.removesuffix("\n").split("\n")) if result.stdout else set()

    def observe_session(self, session_name: str) -> tuple[TmuxPaneRecord, ...] | None:
        """Observe all panes in the exact session, including inactive windows."""

        result = self._observe_command(
            ["list-panes", "-s", "-t", f"={session_name}:", "-F", _PANE_FORMAT]
        )
        if (
            result.returncode == 1
            and result.stderr.strip()
            in {
                f"can't find session: {session_name}",
                f"can't find window: {session_name}",
            }
            and session_name not in self.list_sessions()
        ):
            return None
        _require_observation(result)
        records = tuple(
            _parse_pane_line(row, session_name)
            for row in result.stdout.removesuffix("\n").split("\n")
        )
        if len({pane.session_id for pane in records}) != 1:
            raise TmuxInvalidObservation("tmux returned inconsistent session-wide pane metadata")
        return records

    def capture_pane(
        self, target: str, *, history: bool = False, escape_sequences: bool = False
    ) -> str:
        """Capture normalized pane text with a checked status."""

        args = ["capture-pane", "-p", "-t", target]
        if history:
            args.extend(["-S", "-", "-E", "-"])
        if escape_sequences:
            args.append("-e")
        return self.checked_command(args).stdout.removesuffix("\n")

    def capture_exact(self, args: Sequence[str]) -> TmuxCommandResult:
        """Capture stdout with trailing blank rows that libtmux discards."""

        if not args or args[0] != "capture-pane":
            raise ValueError("Exact tmux capture requires a capture-pane command")
        return self._native_command(args, operation="capture-pane", sensitive=True)

    def load_buffer(self, name: str, text: str) -> None:
        """Load prompt data through native stdin, which libtmux does not expose."""

        self._native_command(
            ["load-buffer", "-b", name, "-"],
            operation="load-buffer",
            input_text=text,
            sensitive=True,
        ).require_success()

    def paste_buffer(
        self,
        name: str,
        target: str,
        *,
        bracketed: bool = True,
        delete_after: bool = False,
        raw_newlines: bool = False,
    ) -> None:
        """Paste a scoped buffer into the selected pane once."""

        args = ["paste-buffer"]
        if bracketed:
            args.append("-p")
        if delete_after:
            args.append("-d")
        if raw_newlines:
            args.append("-r")
        args.extend(["-b", name, "-t", target])
        self.checked_command(args)

    def delete_buffer(self, name: str) -> None:
        """Delete a named buffer on this server only."""

        self.checked_command(["delete-buffer", "-b", name])

    def send_keys(self, target: str, *keys: str, literal: bool = False) -> None:
        """Send only the requested keys or literal text, without an implicit Enter."""

        args = ["send-keys", "-t", target]
        if literal:
            args.append("-l")
        args.extend(["--", *(escape_trailing_separator(key) for key in keys)])
        self.checked_command(args)

    def start(self, args: Sequence[str], *, environment: Mapping[str, str]) -> TmuxCommandResult:
        """Start with a curated child environment, unavailable through libtmux."""

        command = args[2:] if args and args[0] == "-f" else args
        if not command or command[0] not in {"new-session", "start-server"}:
            raise ValueError("Expected a tmux server or session start command")
        socket = Path(self.m_socket_path)
        # The native default selector creates its private socket directory on first use.
        native_default = (
            socket == _native_default_socket(environment) and not socket.parent.exists()
        )
        return self._native_command(
            args,
            operation="startup",
            environment=environment,
            sensitive=True,
            native_default=native_default,
        )

    def wait_for(self, channel: str, *, timeout_seconds: float | None = None) -> TmuxCommandResult:
        """Use a native client for waits that require a process deadline."""

        args = ["wait-for", escape_trailing_separator(channel)]
        if timeout_seconds is None:
            return self.command(args)
        return self._native_command(args, operation="wait-for", timeout_seconds=timeout_seconds)

    def signal_invocation(self, channel: str) -> list[str]:
        """Build the completion signal sent by a delegated shell process."""

        return self._native_argv(["wait-for", "-S", escape_trailing_separator(channel)])

    def attach_invocation(
        self, target: str, *, detach_others: bool = False, readonly: bool = False
    ) -> list[str]:
        """Build a native attach command for a PTY or inherited-stdio child."""

        args = ["attach-session"]
        if detach_others:
            args.append("-d")
        if readonly:
            args.append("-r")
        args.extend(["-t", escape_trailing_separator(target)])
        argv = self._native_argv(args)
        resolved = shutil.which(argv[0])
        if resolved is not None:
            argv[0] = os.path.abspath(resolved)
        return argv

    def native_environment(self) -> dict[str, str]:
        """Give a delegated child its own environment without inherited selectors."""

        return _without_tmux_selectors(os.environ)

    def _observe_command(self, args: Sequence[str]) -> TmuxCommandResult:
        """Keep failures to launch the observation in its error category."""

        try:
            return self.command(args)
        except TmuxCommandError as exc:
            raise TmuxObservationUnavailable(str(exc), returncode=exc.returncode) from exc

    def _native_argv(self, args: Sequence[str], *, native_default: bool = False) -> list[str]:
        """Build the same socket selection for a named native process feature."""

        selector = ["-L", "default"] if native_default else ["-S", self.m_socket_path]
        return [self.m_executable or "tmux", *selector, *args]

    def _native_command(
        self,
        args: Sequence[str],
        *,
        operation: str,
        input_text: str | None = None,
        environment: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
        sensitive: bool = False,
        native_default: bool = False,
    ) -> TmuxCommandResult:
        """Run a named operation that needs native process controls or output."""

        try:
            completed = subprocess.run(
                self._native_argv(args, native_default=native_default),
                input=input_text,
                env=self.native_environment()
                if environment is None
                else _without_tmux_selectors(environment),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="backslashreplace",
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            raise TmuxCommandError(f"Timed out running tmux {operation}") from None
        except (OSError, ValueError) as exc:
            raise TmuxCommandError(
                f"Could not run tmux {operation} ({type(exc).__name__})"
            ) from None
        return TmuxCommandResult(
            (operation,) if sensitive else tuple(args),
            completed.returncode,
            completed.stdout if completed.returncode == 0 or not sensitive else "",
            completed.stderr if not sensitive else "",
        )


def tmux_command(args: Sequence[str], *, sensitive: bool = False) -> TmuxCommandResult:
    """Dispatch one checked-status command using the current socket authority."""

    return TmuxServer().command(args, sensitive=sensitive)


def _without_tmux_selectors(environment: Mapping[str, str]) -> dict[str, str]:
    """Copy a child environment without inherited client selectors."""

    return {key: value for key, value in environment.items() if key not in {"TMUX", "TMUX_PANE"}}


def _native_default_socket(environment: Mapping[str, str]) -> Path:
    """Compute the socket addressed by tmux's native default name."""

    return Path(environment.get("TMUX_TMPDIR") or "/tmp") / f"tmux-{os.getuid()}" / "default"


def _lines_to_text(lines: Sequence[str]) -> str:
    """Expose normalized libtmux lines to existing text-based callers."""

    return "".join(f"{line}\n" for line in lines)


def _private_diagnostic(operation: str, lines: Sequence[str]) -> str:
    """Preserve the failure category needed to read an optional environment key."""

    if operation == "show-environment" and any(
        line.startswith(("unknown variable:", "unknown-environment:")) for line in lines
    ):
        return "unknown variable\n"
    return ""


def _require_observation(result: TmuxCommandResult) -> None:
    """Turn a nonzero checked status into an unavailable observation."""

    try:
        result.require_success()
    except TmuxCommandError as exc:
        raise TmuxObservationUnavailable(str(exc), returncode=exc.returncode) from exc


def _parse_pane_line(row: str, session_name: str) -> TmuxPaneRecord:
    """Validate a session-wide pane row before trusting its server-local IDs."""

    parts = row.split("\t")
    if len(parts) != len(_PANE_FIELDS):
        raise TmuxInvalidObservation("tmux returned a malformed pane row")
    (
        pane_id,
        session_id,
        observed_name,
        window_id,
        window_index,
        window_name,
        pane_index,
        active,
        dead,
        pid,
        width,
        height,
    ) = parts
    if (
        observed_name != session_name
        or not re.fullmatch(r"%[0-9]+", pane_id)
        or not re.fullmatch(r"\$[0-9]+", session_id)
        or not re.fullmatch(r"@[0-9]+", window_id)
        or not all(
            value.isascii() and value.isdecimal()
            for value in (window_index, pane_index, width, height)
        )
        or (pid and not (pid.isascii() and pid.isdecimal()))
        or active not in {"0", "1"}
        or dead not in {"0", "1"}
    ):
        raise TmuxInvalidObservation("tmux returned invalid pane identity or state")
    return TmuxPaneRecord(
        pane_id=pane_id,
        session_name=observed_name,
        window_id=window_id,
        window_index=window_index,
        window_name=window_name,
        pane_index=pane_index,
        pane_active=active == "1",
        pane_dead=dead == "1",
        pane_pid=int(pid) if pid else None,
        session_id=session_id,
        pane_width=int(width),
        pane_height=int(height),
    )


def enclosing_tmux_session() -> tuple[str, str] | None:
    """Resolve the native caller's session by the socket and id reported in TMUX."""

    context = os.environ.get("TMUX")
    if not context:
        return None
    components = context.rsplit(",", 2)
    if len(components) != 3 or any(
        not re.fullmatch(r"[0-9]+", item) for item in components[1:]
    ):
        raise ValueError("The current tmux context is malformed.")
    socket = validate_tmux_socket_path(components[0])
    result = TmuxServer(socket).checked_command(
        ["display-message", "-p", "-t", f"${components[2]}:", "#{session_name}"]
    )
    name = result.stdout.strip()
    if not name:
        raise TmuxInvalidObservation("Cannot determine the caller's current tmux session")
    return socket, name
