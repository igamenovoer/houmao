"""Shared tmux primitives for runtime backends and identity resolution."""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Literal, Mapping

from ..agent_identity import (
    derive_auto_agent_name_base,
    derive_tmux_session_name,
    normalize_agent_identity_name,
)
from ..errors import SessionManifestError

if TYPE_CHECKING:
    import libtmux


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


@dataclass(frozen=True)
class TmuxPaneRecord:
    """One tmux pane record resolved from `list-panes` output."""

    pane_id: str
    session_name: str
    window_id: str
    window_index: str
    window_name: str
    pane_index: str
    pane_active: bool
    pane_dead: bool = False
    pane_pid: int | None = None


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
HEADLESS_AGENT_WINDOW_INDEX: Final[str] = "0"
HEADLESS_AGENT_WINDOW_NAME: Final[str] = "agent"
_TMUX_PANE_DEAD_FORMAT: Final[str] = "#{pane_dead}"
_TMUX_PANE_PID_FORMAT: Final[str] = "#{pane_pid}"


def ensure_tmux_available() -> None:
    """Fail fast when tmux is not available on PATH."""

    if shutil.which("tmux") is None:
        raise TmuxCommandError("`tmux` was not found on PATH.")


def list_tmux_sessions() -> set[str]:
    """Return active tmux session names."""

    try:
        return {
            session.session_name.strip()
            for session in _libtmux_server().sessions
            if isinstance(session.session_name, str) and session.session_name.strip()
        }
    except Exception as exc:  # noqa: BLE001
        detail = str(exc).strip().lower()
        if "no server running" in detail or "failed to connect to server" in detail:
            return set()
        raise TmuxCommandError(
            f"Failed to list tmux sessions: {str(exc).strip() or 'unknown tmux error'}"
        ) from exc


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
        f"Failed to create tmux session `{session_name}`: {detail or 'unknown tmux error'}"
    )


def headless_agent_window_target(*, session_name: str) -> str:
    """Return the stable tmux window target for one headless agent surface."""

    return f"{session_name}:{HEADLESS_AGENT_WINDOW_INDEX}"


def headless_agent_pane_target(*, session_name: str) -> str:
    """Return the stable tmux pane target for one headless agent surface."""

    return f"{headless_agent_window_target(session_name=session_name)}.0"


def prepare_headless_agent_window(*, session_name: str) -> None:
    """Rename and select the stable primary tmux surface for headless sessions."""

    window_target = headless_agent_window_target(session_name=session_name)
    for args, description in (
        (
            ["rename-window", "-t", window_target, HEADLESS_AGENT_WINDOW_NAME],
            "rename",
        ),
        (
            ["select-window", "-t", window_target],
            "select",
        ),
    ):
        result = run_tmux(args)
        if result.returncode == 0:
            continue
        detail = tmux_error_detail(result)
        raise TmuxCommandError(
            f"Failed to {description} tmux headless agent window `{window_target}`: "
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
        f"Failed to kill tmux session `{session_name}`: {detail or 'unknown tmux error'}"
    )


def has_tmux_session(*, session_name: str) -> subprocess.CompletedProcess[str]:
    """Return raw tmux `has-session` command output."""

    return run_tmux(["has-session", "-t", session_name])


def tmux_session_exists(*, session_name: str) -> bool:
    """Return whether one tmux session currently exists."""

    return has_tmux_session(session_name=session_name).returncode == 0


def set_tmux_session_environment(*, session_name: str, env_vars: Mapping[str, str]) -> None:
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


def unset_tmux_session_environment(*, session_name: str, variable_names: list[str]) -> None:
    """Unset multiple tmux session environment variables."""

    for variable_name in variable_names:
        result = run_tmux(["set-environment", "-t", session_name, "-u", variable_name])
        if result.returncode == 0:
            continue
        detail = tmux_error_detail(result)
        raise TmuxCommandError(
            f"Failed to unset tmux environment variable `{variable_name}` in session "
            f"`{session_name}`: {detail or 'unknown tmux error'}"
        )


def show_tmux_environment(
    *, session_name: str, variable_name: str
) -> subprocess.CompletedProcess[str]:
    """Return raw tmux `show-environment` output for one variable."""

    return run_tmux(["show-environment", "-t", session_name, variable_name])


def read_tmux_session_environment_value(*, session_name: str, variable_name: str) -> str | None:
    """Return one optional tmux session environment value."""

    result = show_tmux_environment(session_name=session_name, variable_name=variable_name)
    if result.returncode != 0:
        detail = tmux_error_detail(result).lower()
        if "unknown variable" in detail or "unknown-environment" in detail:
            return None
        raise TmuxCommandError(
            f"Failed to read tmux environment variable `{variable_name}` from "
            f"`{session_name}`: {tmux_error_detail(result) or 'unknown tmux error'}"
        )

    line = (result.stdout or "").strip()
    if not line or line.startswith("-"):
        return None
    expected_prefix = f"{variable_name}="
    if not line.startswith(expected_prefix):
        raise TmuxCommandError(
            f"Unexpected tmux environment output for `{variable_name}` in `{session_name}`: {line}"
        )
    value = line[len(expected_prefix) :].strip()
    return value or None


def list_tmux_clients(*, session_name: str) -> tuple[str, ...]:
    """Return attached tmux client identifiers for one session."""

    session = _require_libtmux_session(session_name=session_name)
    result = session.cmd("list-clients", "-F", "#{client_tty}")
    if result.returncode != 0:
        detail = _libtmux_cmd_detail(result)
        lowered = detail.lower()
        if "no current client" in lowered or "no server running" in lowered:
            return ()
        raise TmuxCommandError(
            f"Failed to list tmux clients for `{session_name}`: {detail or 'unknown tmux error'}"
        )
    return tuple(line.strip() for line in result.stdout if str(line).strip())


def attach_tmux_session(*, session_name: str) -> None:
    """Attach the caller terminal to one tmux session through libtmux."""

    session = _require_libtmux_session(session_name=session_name)
    attach_method = getattr(session, "attach", None)
    try:
        if callable(attach_method):
            attach_method()
            return
        result = session.cmd("attach-session")
    except Exception as exc:  # noqa: BLE001
        raise TmuxCommandError(
            f"Failed to attach tmux session `{session_name}`: "
            f"{str(exc).strip() or 'unknown tmux error'}"
        ) from exc
    if result.returncode != 0:
        detail = _libtmux_cmd_detail(result)
        raise TmuxCommandError(
            f"Failed to attach tmux session `{session_name}`: {detail or 'unknown tmux error'}"
        )


def list_tmux_panes(*, session_name: str) -> tuple[TmuxPaneRecord, ...]:
    """Return pane records for all panes in one tmux session."""

    session = _require_libtmux_session(session_name=session_name)
    return tuple(
        _tmux_pane_record_from_libtmux_pane(pane=pane, session_name=session_name)
        for pane in session.panes
    )


def resolve_tmux_pane(
    *,
    session_name: str,
    pane_id: str | None = None,
    window_id: str | None = None,
    window_index: str | None = None,
    window_name: str | None = None,
) -> TmuxPaneRecord:
    """Resolve one tmux pane from explicit pane/window identity.

    Parameters
    ----------
    session_name:
        Tmux session to search across.
    pane_id:
        Optional exact pane identifier.
    window_id:
        Optional exact window identifier.
    window_index:
        Optional window index within the session.
    window_name:
        Optional contractual window name.

    Returns
    -------
    TmuxPaneRecord
        One resolved tmux pane.

    Raises
    ------
    TmuxCommandError
        Raised when the session has no panes, when the selector matches no panes,
        or when the session is ambiguous and no explicit selector narrows it to a
        single contractual surface.
    """

    panes = list_tmux_panes(session_name=session_name)
    if not panes:
        raise TmuxCommandError(f"No tmux panes are available for `{session_name}`.")

    if pane_id is not None:
        matching = tuple(pane for pane in panes if pane.pane_id == pane_id)
        if not matching:
            raise TmuxCommandError(
                f"No tmux panes matched pane id `{pane_id}` in `{session_name}`."
            )
        return _prefer_live_tmux_pane(matching)

    matching = panes
    selectors: list[tuple[str, str]] = []
    if window_id is not None:
        selectors.append(("window id", window_id))
        matching = tuple(pane for pane in matching if pane.window_id == window_id)
        if not matching:
            selector_detail = " and ".join(
                f"{selector_label} `{selector_value}`"
                for selector_label, selector_value in selectors
            )
            raise TmuxCommandError(f"No tmux panes matched {selector_detail} in `{session_name}`.")
    if window_index is not None:
        selectors.append(("window index", window_index))
        matching = tuple(pane for pane in matching if pane.window_index == window_index)
        if not matching:
            selector_detail = " and ".join(
                f"{selector_label} `{selector_value}`"
                for selector_label, selector_value in selectors
            )
            raise TmuxCommandError(f"No tmux panes matched {selector_detail} in `{session_name}`.")
    if window_name is not None:
        selectors.append(("window", window_name))
        matching = tuple(pane for pane in matching if pane.window_name == window_name)
        if not matching:
            selector_detail = " and ".join(
                f"{selector_label} `{selector_value}`"
                for selector_label, selector_value in selectors
            )
            raise TmuxCommandError(f"No tmux panes matched {selector_detail} in `{session_name}`.")

    if not selectors and len(matching) != 1:
        raise TmuxCommandError(
            f"Ambiguous tmux pane target for `{session_name}`: {len(matching)} panes matched; "
            "provide pane_id, window_id, window_index, or window_name."
        )
    return _prefer_live_tmux_pane(matching)


def find_tmux_pane(*, session_name: str, pane_id: str) -> TmuxPaneRecord | None:
    """Return one optional tmux pane record by pane id."""

    try:
        return resolve_tmux_pane(session_name=session_name, pane_id=pane_id)
    except TmuxCommandError as exc:
        if f"pane id `{pane_id}`" in str(exc):
            return None
        raise


def capture_tmux_pane(*, target: str) -> str:
    """Return capture-pane text for one tmux target."""

    if target.startswith("%"):
        pane = _require_libtmux_pane(pane_id=target)
        try:
            return "\n".join(pane.capture_pane(start="-", end="-", escape_sequences=True))
        except Exception as exc:  # noqa: BLE001
            raise TmuxCommandError(
                f"Failed to capture tmux pane `{target}`: {str(exc).strip() or 'unknown tmux error'}"
            ) from exc

    result = _libtmux_server().cmd("capture-pane", "-p", "-e", "-S", "-", target=target)
    if result.returncode != 0:
        detail = _libtmux_cmd_detail(result)
        raise TmuxCommandError(
            f"Failed to capture tmux pane `{target}`: {detail or 'unknown tmux error'}"
        )
    return "\n".join(str(line) for line in result.stdout)


def load_tmux_buffer(*, buffer_name: str, text: str) -> None:
    """Load literal text into one named tmux buffer."""

    try:
        result = subprocess.run(
            ["tmux", "load-buffer", "-b", buffer_name, "-"],
            check=False,
            capture_output=True,
            text=True,
            input=text,
        )
    except OSError as exc:
        raise TmuxCommandError(
            f"Failed to run tmux command `load-buffer` for `{buffer_name}`: {exc}"
        ) from exc

    if result.returncode == 0:
        return
    detail = tmux_error_detail(result)
    raise TmuxCommandError(
        f"Failed to load tmux buffer `{buffer_name}`: {detail or 'unknown tmux error'}"
    )


def paste_tmux_buffer(*, target: str, buffer_name: str, bracketed_paste: bool = True) -> None:
    """Paste one named tmux buffer into the target pane."""

    args = ["paste-buffer"]
    if bracketed_paste:
        args.append("-p")
    args.extend(["-b", buffer_name, "-t", target])
    result = run_tmux(args)
    if result.returncode == 0:
        return
    detail = tmux_error_detail(result)
    raise TmuxCommandError(
        f"Failed to paste tmux buffer `{buffer_name}` into `{target}`: "
        f"{detail or 'unknown tmux error'}"
    )


def select_tmux_pane(*, target: str) -> None:
    """Select one tmux pane."""

    result = run_tmux(["select-pane", "-t", target])
    if result.returncode != 0:
        detail = tmux_error_detail(result)
        raise TmuxCommandError(
            f"Failed to select tmux pane `{target}`: {detail or 'unknown tmux error'}"
        )


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
        segments.append(TmuxControlInputSegment(kind="literal", value=sequence[cursor:]))

    return tuple(segment for segment in segments if segment.value)


def send_tmux_control_input(*, target: str, segments: tuple[TmuxControlInputSegment, ...]) -> None:
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
            f"Failed to send tmux control input to `{target}`: {detail or 'unknown tmux error'}"
        )


def generate_tmux_session_name(
    *,
    tool: str,
    role_name: str,
    existing_sessions: set[str] | None = None,
) -> str:
    """Generate one default tmux session name for a tool/role identity."""

    occupied = existing_sessions if existing_sessions is not None else list_tmux_sessions()
    canonical_agent_name = normalize_agent_identity_name(
        derive_auto_agent_name_base(tool=tool, role_name=role_name)
    ).canonical_name
    try:
        return derive_tmux_session_name(
            canonical_agent_name=canonical_agent_name,
            launch_epoch_ms=time.time_ns() // 1_000_000,
            occupied_session_names=occupied,
        )
    except SessionManifestError as exc:
        raise TmuxCommandError(str(exc)) from exc


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


def _libtmux_server() -> "libtmux.Server":
    """Return one libtmux server handle."""

    try:
        import libtmux
    except ImportError as exc:
        raise TmuxCommandError("`libtmux` is required for repo-owned tmux integration.") from exc
    try:
        return libtmux.Server()
    except Exception as exc:  # noqa: BLE001
        raise TmuxCommandError(
            f"Failed to initialize libtmux server: {str(exc).strip() or 'unknown tmux error'}"
        ) from exc


def _require_libtmux_session(*, session_name: str) -> Any:
    """Return one live libtmux session by name."""

    for session in _libtmux_server().sessions:
        if getattr(session, "session_name", None) == session_name:
            return session
    raise TmuxCommandError(f"Tmux session `{session_name}` does not exist.")


def _require_libtmux_pane(*, pane_id: str) -> Any:
    """Return one live libtmux pane by pane id."""

    server = _libtmux_server()
    try:
        import libtmux

        return libtmux.Pane.from_pane_id(server=server, pane_id=pane_id)
    except Exception as exc:  # noqa: BLE001
        raise TmuxCommandError(
            f"Tmux pane `{pane_id}` could not be resolved: {str(exc).strip() or 'unknown tmux error'}"
        ) from exc


def _tmux_pane_record_from_libtmux_pane(*, pane: Any, session_name: str) -> TmuxPaneRecord:
    """Convert one libtmux pane object into the repository pane record."""

    pane_dead = _coerce_bool_tmux_flag(
        _optional_libtmux_pane_value(
            pane=pane,
            attr_name="pane_dead",
            format_expression=_TMUX_PANE_DEAD_FORMAT,
        )
    )
    pane_pid_value = _optional_libtmux_pane_value(
        pane=pane,
        attr_name="pane_pid",
        format_expression=_TMUX_PANE_PID_FORMAT,
    )
    return TmuxPaneRecord(
        pane_id=_require_libtmux_text(getattr(pane, "pane_id", None), field_name="pane_id"),
        session_name=_require_libtmux_text(
            getattr(pane, "session_name", None) or session_name,
            field_name="session_name",
        ),
        window_id=_require_libtmux_text(getattr(pane, "window_id", None), field_name="window_id"),
        window_index=_require_libtmux_text(
            getattr(pane, "window_index", None),
            field_name="window_index",
        ),
        window_name=_require_libtmux_text(
            getattr(pane, "window_name", None),
            field_name="window_name",
        ),
        pane_index=_require_libtmux_text(
            getattr(pane, "pane_index", None), field_name="pane_index"
        ),
        pane_active=_coerce_bool_tmux_flag(
            _normalize_libtmux_scalar(getattr(pane, "pane_active", None))
        ),
        pane_dead=pane_dead,
        pane_pid=int(pane_pid_value)
        if pane_pid_value is not None and pane_pid_value.isdigit()
        else None,
    )


def _optional_libtmux_pane_value(
    *,
    pane: Any,
    attr_name: str,
    format_expression: str,
) -> str | None:
    """Return one optional pane value from a direct attribute or object-bound format query."""

    direct_value = _normalize_libtmux_scalar(getattr(pane, attr_name, None))
    if direct_value is not None:
        return direct_value
    try:
        output = pane.display_message(format_expression, get_text=True)
    except Exception as exc:  # noqa: BLE001
        raise TmuxCommandError(
            f"Failed to query tmux pane format `{format_expression}`: "
            f"{str(exc).strip() or 'unknown tmux error'}"
        ) from exc
    if not output:
        return None
    return _normalize_libtmux_scalar(output[0])


def _require_libtmux_text(value: Any, *, field_name: str) -> str:
    """Return one normalized required libtmux scalar string."""

    normalized = _normalize_libtmux_scalar(value)
    if normalized is None:
        raise TmuxCommandError(f"libtmux pane is missing required `{field_name}`.")
    return normalized


def _normalize_libtmux_scalar(value: Any) -> str | None:
    """Normalize one optional libtmux scalar into text."""

    if value is None:
        return None
    if isinstance(value, bool):
        return "1" if value else "0"
    text = str(value).strip()
    return text or None


def _coerce_bool_tmux_flag(value: str | None) -> bool:
    """Return one tmux flag string as a boolean."""

    return value == "1"


def _prefer_live_tmux_pane(panes: tuple[TmuxPaneRecord, ...]) -> TmuxPaneRecord:
    """Prefer the active live pane when multiple tmux panes match."""

    for pane in panes:
        if pane.pane_active and not pane.pane_dead:
            return pane
    for pane in panes:
        if not pane.pane_dead:
            return pane
    return panes[0]


def _libtmux_cmd_detail(result: Any) -> str:
    """Extract concise stderr/stdout detail from one libtmux command result."""

    stderr = getattr(result, "stderr", []) or []
    stdout = getattr(result, "stdout", []) or []
    lines = stderr or stdout
    return "\n".join(str(line).strip() for line in lines if str(line).strip())
