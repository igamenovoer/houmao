"""Shared tmux primitives for runtime backends and identity resolution."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping

from ..agent_identity import AGENT_NAMESPACE_PREFIX, derive_auto_agent_name_base


class TmuxCommandError(RuntimeError):
    """Raised when a tmux command cannot be executed reliably."""


class TmuxControlInputError(ValueError):
    """Signal invalid mixed control-input syntax or unsupported key tokens.

    Notes
    -----
    This exception is raised when parsing detects malformed or unsupported
    exact `<[key-name]>` control-input tokens.
    """


@dataclass(frozen=True)
class TmuxControlInputSegment:
    """One parsed control-input segment for tmux delivery.

    Attributes
    ----------
    kind:
        Segment category, either literal text or one supported special key.
    value:
        Payload for the segment. Literal segments keep the raw text while
        special segments store the tmux key name.
    """

    kind: Literal["literal", "special"]
    value: str


_TMUX_SPECIAL_KEY_TOKEN_RE = re.compile(r"<\[([^\s<>\[\]]+)\]>")
_SUPPORTED_TMUX_SPECIAL_KEYS: frozenset[str] = frozenset(
    {
        "BSpace",
        "C-c",
        "C-d",
        "C-z",
        "Down",
        "Enter",
        "Escape",
        "Left",
        "Right",
        "Tab",
        "Up",
    }
)


def ensure_tmux_available() -> None:
    """Fail fast when tmux is not available on PATH."""

    if shutil.which("tmux") is None:
        raise TmuxCommandError("`tmux` was not found on PATH.")


def list_tmux_sessions() -> set[str]:
    """Return active tmux session names."""

    result = run_tmux(["list-sessions", "-F", "#{session_name}"])
    if result.returncode != 0:
        detail = tmux_error_detail(result)
        lowered = detail.lower()
        if "no server running" in lowered or "failed to connect to server" in lowered:
            return set()
        raise TmuxCommandError(
            "Failed to list tmux sessions: "
            f"{detail or 'unknown tmux error'}"
        )
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def create_tmux_session(*, session_name: str, working_directory: Path) -> None:
    """Create a detached tmux session with a fixed working directory."""

    result = run_tmux(
        [
            "new-session",
            "-d",
            "-s",
            session_name,
            "-c",
            str(working_directory),
        ]
    )
    if result.returncode == 0:
        return
    detail = tmux_error_detail(result)
    raise TmuxCommandError(
        f"Failed to create tmux session `{session_name}`: "
        f"{detail or 'unknown tmux error'}"
    )


def cleanup_tmux_session(*, session_name: str) -> None:
    """Best-effort tmux session cleanup."""

    try:
        kill_tmux_session(session_name=session_name)
    except TmuxCommandError:
        return


def kill_tmux_session(*, session_name: str) -> None:
    """Terminate a tmux session and fail if tmux reports an error."""

    result = run_tmux(["kill-session", "-t", session_name])
    if result.returncode == 0:
        return
    detail = tmux_error_detail(result)
    raise TmuxCommandError(
        f"Failed to kill tmux session `{session_name}`: "
        f"{detail or 'unknown tmux error'}"
    )


def has_tmux_session(*, session_name: str) -> subprocess.CompletedProcess[str]:
    """Return raw tmux `has-session` command output."""

    return run_tmux(["has-session", "-t", session_name])


def set_tmux_session_environment(
    *, session_name: str, env_vars: Mapping[str, str]
) -> None:
    """Set multiple tmux session environment variables."""

    for key, value in env_vars.items():
        result = run_tmux(["set-environment", "-t", session_name, key, value])
        if result.returncode == 0:
            continue
        detail = tmux_error_detail(result)
        raise TmuxCommandError(
            f"Failed to set tmux environment variable `{key}` in session "
            f"`{session_name}`: {detail or 'unknown tmux error'}"
        )


def show_tmux_environment(
    *, session_name: str, variable_name: str
) -> subprocess.CompletedProcess[str]:
    """Return raw tmux `show-environment` output for one variable."""

    return run_tmux(["show-environment", "-t", session_name, variable_name])


def wait_for_tmux_signal(
    *, signal_name: str, timeout_seconds: float | None = None
) -> subprocess.CompletedProcess[str]:
    """Wait for a tmux wait-for signal."""

    return run_tmux(["wait-for", signal_name], timeout_seconds=timeout_seconds)


def parse_tmux_control_input(
    *, sequence: str, escape_special_keys: bool = False
) -> tuple[TmuxControlInputSegment, ...]:
    """Parse a mixed literal/special-key tmux input sequence.

    Parameters
    ----------
    sequence:
        Raw caller-provided control-input string.
    escape_special_keys:
        When true, disable special-key token parsing for the entire string.

    Returns
    -------
    tuple[TmuxControlInputSegment, ...]
        Ordered literal/special segments ready for tmux delivery.

    Raises
    ------
    TmuxControlInputError
        Raised when the sequence is empty or contains an unsupported exact
        `<[key-name]>` token.
    """

    if not sequence:
        raise TmuxControlInputError("Control-input sequence must not be empty.")
    if escape_special_keys:
        return (TmuxControlInputSegment(kind="literal", value=sequence),)

    segments: list[TmuxControlInputSegment] = []
    cursor = 0
    for match in _TMUX_SPECIAL_KEY_TOKEN_RE.finditer(sequence):
        if match.start() > cursor:
            segments.append(
                TmuxControlInputSegment(
                    kind="literal",
                    value=sequence[cursor : match.start()],
                )
            )

        token = match.group(0)
        key_name = match.group(1)
        if key_name not in _SUPPORTED_TMUX_SPECIAL_KEYS:
            raise TmuxControlInputError(
                f"Unsupported control-input token {token!r}. "
                "Supported exact key names: "
                f"{', '.join(sorted(_SUPPORTED_TMUX_SPECIAL_KEYS))}."
            )
        segments.append(TmuxControlInputSegment(kind="special", value=key_name))
        cursor = match.end()

    if cursor < len(sequence):
        segments.append(
            TmuxControlInputSegment(kind="literal", value=sequence[cursor:])
        )

    return tuple(segment for segment in segments if segment.value)


def send_tmux_control_input(
    *, target: str, segments: tuple[TmuxControlInputSegment, ...]
) -> None:
    """Deliver parsed control-input segments to a tmux target in order.

    Parameters
    ----------
    target:
        Tmux target accepted by `tmux send-keys`, typically a resolved window id.
    segments:
        Parsed control-input sequence to deliver left-to-right.

    Raises
    ------
    TmuxCommandError
        Raised when tmux rejects any segment delivery command.
    """

    for segment in segments:
        if segment.kind == "literal":
            result = run_tmux(["send-keys", "-t", target, "-l", segment.value])
        else:
            result = run_tmux(["send-keys", "-t", target, segment.value])
        if result.returncode == 0:
            continue
        detail = tmux_error_detail(result)
        raise TmuxCommandError(
            "Failed to send tmux control input "
            f"to `{target}`: {detail or 'unknown tmux error'}"
        )


def generate_tmux_session_name(
    *,
    tool: str,
    role_name: str,
    existing_sessions: set[str] | None = None,
) -> str:
    """Generate a canonical `AGENTSYS-...` tmux session name."""

    occupied = existing_sessions if existing_sessions is not None else list_tmux_sessions()
    base = derive_auto_agent_name_base(tool=tool, role_name=role_name)
    primary = f"{AGENT_NAMESPACE_PREFIX}{base}"
    if primary not in occupied:
        return primary

    for suffix in range(2, 10_000):
        candidate = f"{primary}-{suffix}"
        if candidate not in occupied:
            return candidate

    raise TmuxCommandError(
        "Failed to auto-generate a unique AGENTSYS session name after 9999 attempts."
    )


def run_tmux(
    args: list[str], *, timeout_seconds: float | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a tmux command with normalized invocation behavior."""

    try:
        return subprocess.run(
            ["tmux", *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except OSError as exc:
        raise TmuxCommandError(f"Failed to run tmux command `{args}`: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise TmuxCommandError(f"Timed out running tmux command `{args}`") from exc


def tmux_error_detail(result: subprocess.CompletedProcess[str]) -> str:
    """Extract concise stderr/stdout detail from a tmux command result."""

    return (result.stderr or result.stdout or "").strip()
