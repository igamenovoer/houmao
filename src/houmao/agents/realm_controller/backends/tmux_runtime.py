"""Shared tmux primitives for runtime backends and identity resolution."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, Mapping, MutableMapping

from houmao.agents.kimi_launch_env import KIMI_CONFIG_ENV_NAMES, KIMI_PRIVATE_ENV_NAMES
from houmao.agents.launch_env import owner_tmux_launch_environment
from houmao.execution.tmux import (
    TmuxCommandError as TmuxCommandError,
    TmuxCommandResult,
    TmuxPaneRecord as TmuxPaneRecord,
    TmuxServer,
    capture_tmux_socket_path,
    tmux_command,
)

from ..agent_identity import (
    SELF_TMUX_SESSION_ENV_VAR,
    SELF_TMUX_SOCKET_ENV_VAR,
    derive_auto_agent_name_base,
    derive_tmux_session_name,
    normalize_agent_identity_name,
)
from ..errors import SessionManifestError
from ..boundary_models import SessionManifestTmuxSectionV1
from ..managed_terminal import select_primary_tmux_surface

if TYPE_CHECKING:
    from ..models import LaunchPlan


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
        "C-u",
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
HEADLESS_AGENT_PANE_INDEX: Final[str] = "0"
HEADLESS_AGENT_WINDOW_NAME: Final[str] = "agent"
TMUX_CONFIG_INJECTION_ENV_VAR: Final[str] = "HOUMAO_ENABLE_TMUX_CONFIG_INJECTION"
TMUX_RICH_COLOR_TERM: Final[str] = "tmux-256color"
TMUX_RICH_COLOR_COLORTERM: Final[str] = "truecolor"
TMUX_COLOR_ENV_UNSET_NAMES: Final[tuple[str, ...]] = ("NO_COLOR",)
_TMUX_PANE_DEAD_FORMAT: Final[str] = "#{pane_dead}"
_TMUX_PANE_PID_FORMAT: Final[str] = "#{pane_pid}"
_TMUX_CONFIG_INJECTION_GUIDANCE: Final[str] = (
    f"Set {TMUX_CONFIG_INJECTION_ENV_VAR}=0 to disable Houmao tmux config injection and retry."
)


def ensure_tmux_available() -> None:
    """Fail fast when tmux is not available on PATH."""

    if shutil.which("tmux") is None:
        raise TmuxCommandError("`tmux` was not found on PATH.")


def tmux_config_injection_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return whether Houmao should inject tmux session defaults."""

    source = env if env is not None else os.environ
    return source.get(TMUX_CONFIG_INJECTION_ENV_VAR, "").strip() != "0"


def overlay_tmux_rich_color_environment(env: MutableMapping[str, str]) -> None:
    """Overlay Houmao-owned rich color environment values when enabled."""

    if not tmux_config_injection_enabled():
        return
    env["TERM"] = TMUX_RICH_COLOR_TERM
    env["COLORTERM"] = TMUX_RICH_COLOR_COLORTERM
    for variable_name in TMUX_COLOR_ENV_UNSET_NAMES:
        env.pop(variable_name, None)


def apply_tmux_config_injection(*, session_name: str) -> None:
    """Apply Houmao-owned tmux defaults to one created session."""

    if not tmux_config_injection_enabled():
        return

    target = f"={session_name}:"
    commands = (
        ["set-option", "-t", target, "mouse", "on"],
        ["set-option", "-t", target, "default-terminal", TMUX_RICH_COLOR_TERM],
        ["set-option", "-at", target, "terminal-overrides", ",*256col*:Tc"],
        ["set-environment", "-t", target, "TERM", TMUX_RICH_COLOR_TERM],
        ["set-environment", "-t", target, "COLORTERM", TMUX_RICH_COLOR_COLORTERM],
        ["set-environment", "-t", target, "-r", "NO_COLOR"],
    )
    for args in commands:
        result = tmux_command(list(args))
        if result.returncode == 0:
            continue
        detail = tmux_error_detail(result)
        raise TmuxCommandError(
            "Failed to apply Houmao tmux config injection to session "
            f"`{session_name}` with command `tmux {' '.join(args)}`: "
            f"{detail or 'unknown tmux error'}. {_TMUX_CONFIG_INJECTION_GUIDANCE}"
        )


def list_tmux_sessions() -> set[str]:
    """Return active tmux session names from a checked observation."""

    return TmuxServer().list_sessions(allow_missing_server=True)


def create_tmux_session(
    *, session_name: str, working_directory: Path, launch_plan: LaunchPlan | None = None
) -> None:
    """Create a detached tmux session with a fixed working directory."""

    masked_names = (
        launch_plan.private_env_var_names | launch_plan.previous_public_env_var_names
        if launch_plan is not None and launch_plan.public_env is not None
        else frozenset()
    )
    if launch_plan is not None and launch_plan.tool == "kimi":
        masked_names = masked_names | KIMI_CONFIG_ENV_NAMES | KIMI_PRIVATE_ENV_NAMES
    initial_env = [argument for name in sorted(masked_names) for argument in ("-e", f"{name}=")]
    server = TmuxServer()
    environment = owner_tmux_launch_environment(
        server.native_environment(), excluded_names=masked_names
    )
    result = server.start(
        [
            "new-session",
            "-d",
            "-E",
            "-s",
            session_name,
            "-c",
            str(working_directory),
            *initial_env,
        ],
        environment=environment,
    )
    if result.returncode == 0:
        try:
            apply_tmux_config_injection(session_name=session_name)
        except TmuxCommandError:
            cleanup_tmux_session(session_name=session_name)
            raise
        return
    detail = tmux_error_detail(result)
    raise TmuxCommandError(
        f"Failed to create tmux session `{session_name}`: {detail or 'unknown tmux error'}"
    )


def headless_agent_window_target(*, session_name: str) -> str:
    """Return the stable tmux window target for one headless agent surface."""

    return f"={session_name}:{HEADLESS_AGENT_WINDOW_INDEX}"


def prepare_headless_agent_window(
    *,
    session_name: str,
    fresh_session: bool = False,
) -> TmuxPaneRecord:
    """Normalize, rename, select, and return the primary tmux surface handles."""

    panes = list_tmux_panes(session_name=session_name)
    if not panes:
        raise TmuxCommandError(f"No tmux panes are available for `{session_name}`.")

    window_id = _select_primary_window_id_for_preparation(
        session_name=session_name,
        panes=panes,
        fresh_session=fresh_session,
    )
    surface = _select_single_live_pane(
        panes=tuple(pane for pane in panes if pane.window_id == window_id),
        selector_detail=f"window id `{window_id}`",
        session_name=session_name,
    )
    if surface.window_index != HEADLESS_AGENT_WINDOW_INDEX:
        _run_tmux_step(
            [
                "move-window",
                "-s",
                surface.window_id,
                "-t",
                headless_agent_window_target(session_name=session_name),
            ],
            description="move",
            target=surface.window_id,
        )

    for args, description in (
        (
            [
                "set-window-option",
                "-t",
                window_id,
                "pane-base-index",
                HEADLESS_AGENT_PANE_INDEX,
            ],
            "normalize pane-base-index for",
        ),
        (
            ["rename-window", "-t", window_id, HEADLESS_AGENT_WINDOW_NAME],
            "rename",
        ),
        (
            ["select-window", "-t", window_id],
            "select",
        ),
    ):
        _run_tmux_step(args, description=description, target=window_id)

    return resolve_primary_tmux_surface(
        session_name=session_name,
        pane_id=surface.pane_id,
        window_id=window_id,
        window_name=HEADLESS_AGENT_WINDOW_NAME,
    )


def _run_tmux_step(args: list[str], *, description: str, target: str) -> None:
    """Run one tmux surface-preparation command with contextual errors."""

    result = tmux_command(args)
    if result.returncode == 0:
        return
    detail = tmux_error_detail(result)
    raise TmuxCommandError(
        f"Failed to {description} tmux headless agent window `{target}`: "
        f"{detail or 'unknown tmux error'}"
    )


def _select_primary_window_id_for_preparation(
    *,
    session_name: str,
    panes: tuple[TmuxPaneRecord, ...],
    fresh_session: bool,
) -> str:
    """Return the only safe window id to normalize as the primary surface."""

    window_ids = tuple(dict.fromkeys(pane.window_id for pane in panes))
    if fresh_session and len(window_ids) != 1:
        raise TmuxCommandError(
            f"Fresh tmux session `{session_name}` has unexpected extra windows; "
            "refusing to choose a primary managed-agent surface."
        )

    primary_window_ids = tuple(
        dict.fromkeys(
            pane.window_id for pane in panes if pane.window_index == HEADLESS_AGENT_WINDOW_INDEX
        )
    )
    if len(primary_window_ids) == 1:
        return primary_window_ids[0]
    if len(primary_window_ids) > 1:
        raise TmuxCommandError(
            f"Tmux session `{session_name}` has multiple windows at index "
            f"`{HEADLESS_AGENT_WINDOW_INDEX}`; refusing to choose one."
        )
    if fresh_session and len(window_ids) == 1:
        return window_ids[0]
    raise TmuxCommandError(
        f"Tmux session `{session_name}` is missing primary window "
        f"`{HEADLESS_AGENT_WINDOW_INDEX}` and has {len(window_ids)} windows; "
        "refusing to guess which window is the managed-agent surface."
    )


def resolve_primary_tmux_surface(
    *,
    session_name: str,
    pane_id: str | None = None,
    window_id: str | None = None,
    window_name: str | None = None,
    require_pane_index_zero: bool = False,
) -> TmuxPaneRecord:
    """Resolve a primary selector without repairing or relaxing explicit handles."""

    matching = tuple(
        pane
        for pane in list_tmux_panes(session_name=session_name)
        if (pane_id is None or pane.pane_id == pane_id)
        and (window_id is None or pane.window_id == window_id)
        and (window_name is None or pane.window_name == window_name)
    )
    observation = select_primary_tmux_surface(
        SessionManifestTmuxSectionV1(
            session_name=session_name,
            primary_window_name=window_name,
            primary_window_id=window_id,
            primary_pane_id=pane_id,
        ),
        matching,
        joined=require_pane_index_zero,
    )
    surface = observation.pane or observation.replacement
    if surface is not None:
        return surface
    if observation.state == "ambiguous_pane":
        raise TmuxCommandError(f"Ambiguous tmux primary surface for `{session_name}`.")
    raise TmuxCommandError(
        f"No tmux panes matched primary selector in `{session_name}` ({observation.state})."
    )


def _select_single_live_pane(
    *,
    panes: tuple[TmuxPaneRecord, ...],
    selector_detail: str,
    session_name: str,
) -> TmuxPaneRecord:
    """Return the only actionable pane from a primary-surface candidate set."""

    live = tuple(pane for pane in panes if not pane.pane_dead)
    if len(live) == 1:
        return live[0]
    if len(live) == 0 and len(panes) == 1:
        return panes[0]
    raise TmuxCommandError(
        f"Ambiguous tmux primary surface for `{session_name}`: {len(live)} live panes "
        f"matched {selector_detail}."
    )


def cleanup_tmux_session(*, session_name: str) -> None:
    """Best-effort tmux session cleanup."""

    try:
        kill_tmux_session(session_name=session_name)
    except TmuxCommandError:
        return


def kill_tmux_session(*, session_name: str) -> None:
    """Terminate a tmux session and fail if tmux reports an error."""

    result = tmux_command(["kill-session", "-t", f"={session_name}"])
    if result.returncode == 0:
        return
    detail = tmux_error_detail(result)
    raise TmuxCommandError(
        f"Failed to kill tmux session `{session_name}`: {detail or 'unknown tmux error'}"
    )


def has_tmux_session(*, session_name: str) -> TmuxCommandResult:
    """Return raw tmux `has-session` command output."""

    return tmux_command(["has-session", "-t", f"={session_name}"])


def tmux_session_exists(*, session_name: str, allow_missing_server: bool = False) -> bool:
    """Check presence on the selected socket, propagating observation failures."""

    return session_name in TmuxServer().list_sessions(allow_missing_server=allow_missing_server)


_TmuxHealthState = Literal[
    "healthy",
    "degraded_missing_primary",
    "degraded_ambiguous_primary",
    "degraded_dead_primary",
    "degraded_stale_primary_handles",
    "stale_missing_session",
]


@dataclass(frozen=True)
class TmuxBackedAuthorityHealth:
    """Derived local tmux-authority health for one tmux-backed managed session.

    Attributes
    ----------
    state:
        Three-class derived health classification.
    session_exists:
        Whether the named tmux session currently exists.
    primary_window_exists:
        Whether the contractual primary window index `0` is present.
    primary_pane_exists:
        Whether a contractual primary pane is present in window `0`.
    primary_window_handle_valid:
        Whether a supplied primary window id still resolves to window index `0`.
    primary_pane_handle_valid:
        Whether a supplied primary pane id still resolves under window index `0`.
    """

    state: _TmuxHealthState
    session_exists: bool
    primary_window_exists: bool
    primary_pane_exists: bool
    primary_window_handle_valid: bool | None = None
    primary_pane_handle_valid: bool | None = None


def probe_tmux_backed_authority(
    *,
    session_name: str,
    primary_window_id: str | None = None,
    primary_pane_id: str | None = None,
    primary_window_name: str | None = None,
    joined: bool = False,
) -> TmuxBackedAuthorityHealth:
    """Classify local tmux authority for one persisted managed session name.

    Inspects tmux for the named session and the contractual primary surface
    (window index `0`), plus optional persisted tmux handles,
    and returns a derived health classification. The result is host-local
    runtime state and is never persisted into shared registry state.
    """

    name = session_name.strip()
    if not name:
        return TmuxBackedAuthorityHealth(
            state="stale_missing_session",
            session_exists=False,
            primary_window_exists=False,
            primary_pane_exists=False,
            primary_window_handle_valid=False if primary_window_id else None,
            primary_pane_handle_valid=False if primary_pane_id else None,
        )

    server = TmuxServer()
    observation = select_primary_tmux_surface(
        SessionManifestTmuxSectionV1(
            session_name=name,
            socket_path=server.socket_path,
            primary_window_name=primary_window_name,
            primary_window_id=primary_window_id,
            primary_pane_id=primary_pane_id,
        ),
        server.observe_session(name),
        joined=joined,
    )
    state: _TmuxHealthState
    if observation.state == "missing_session":
        state = "stale_missing_session"
    elif observation.state == "valid" or (
        observation.replacement is not None
        and primary_window_id is None
        and primary_pane_id is None
    ):
        state = "healthy"
    elif observation.state == "stale_handles":
        state = "degraded_stale_primary_handles"
    elif observation.state == "ambiguous_pane":
        state = "degraded_ambiguous_primary"
    elif observation.state == "dead_pane":
        state = "degraded_dead_primary"
    else:
        state = "degraded_missing_primary"
    return TmuxBackedAuthorityHealth(
        state=state,
        session_exists=observation.session_exists,
        primary_window_exists=observation.primary_window_exists,
        primary_pane_exists=observation.primary_pane_exists,
        primary_window_handle_valid=observation.primary_window_handle_valid,
        primary_pane_handle_valid=observation.primary_pane_handle_valid,
    )


def detached_tool_environment(
    environment: Mapping[str, str], *, session_name: str
) -> dict[str, str]:
    """Give detached native tool processes their exact owning tmux locator."""

    detached = {
        key: value for key, value in environment.items() if key not in {"TMUX", "TMUX_PANE"}
    }
    detached[SELF_TMUX_SOCKET_ENV_VAR] = capture_tmux_socket_path()
    detached[SELF_TMUX_SESSION_ENV_VAR] = session_name
    return detached


def publish_tmux_launch_environment(*, session_name: str, launch_plan: LaunchPlan) -> None:
    """Reconcile the launch environment in the verified owning session."""

    if launch_plan.public_env is None:
        return

    private_names = launch_plan.private_env_var_names
    if launch_plan.tool == "kimi":
        private_names = private_names | KIMI_CONFIG_ENV_NAMES | KIMI_PRIVATE_ENV_NAMES
    public = {
        key: value for key, value in launch_plan.public_env.items() if key not in private_names
    }
    removed = (launch_plan.previous_public_env_var_names | private_names).difference(public)
    target = f"={session_name}"
    for name in sorted(removed):
        _publish_tmux_launch_variable(target=target, name=name, value=None)
    for name, value in public.items():
        _publish_tmux_launch_variable(target=target, name=name, value=value)


def _publish_tmux_launch_variable(*, target: str, name: str, value: str | None) -> None:
    """Set a value or mask its inherited name without echoing the arguments on failure."""

    args = ["set-environment", "-t", target]
    if value is None:
        args.extend(["-r", "--", name])
    else:
        # tmux's argv parser treats a terminal semicolon as a command separator.
        literal_value = value[:-1] + r"\;" if value.endswith(";") else value
        args.extend(["--", name, literal_value])
    try:
        result = tmux_command(args, sensitive=True)
    except (TmuxCommandError, ValueError):
        raise TmuxCommandError(
            f"Failed to publish tmux launch variable `{name}` in `{target}`"
        ) from None
    if result.returncode != 0:
        raise TmuxCommandError(f"Failed to publish tmux launch variable `{name}` in `{target}`")


def set_tmux_session_environment(*, session_name: str, env_vars: Mapping[str, str]) -> None:
    """Set environment variables in the exactly named session."""

    for name, value in env_vars.items():
        _publish_tmux_launch_variable(target=f"={session_name}", name=name, value=value)


def unset_tmux_session_environment(*, session_name: str, variable_names: list[str]) -> None:
    """Unset multiple tmux session environment variables."""

    for variable_name in variable_names:
        result = tmux_command(["set-environment", "-t", f"={session_name}", "-u", variable_name])
        if result.returncode == 0:
            continue
        detail = tmux_error_detail(result)
        raise TmuxCommandError(
            f"Failed to unset tmux environment variable `{variable_name}` in session "
            f"`{session_name}`: {detail or 'unknown tmux error'}"
        )


def show_tmux_environment(*, session_name: str, variable_name: str) -> TmuxCommandResult:
    """Return raw tmux `show-environment` output for one variable."""

    return tmux_command(
        ["show-environment", "-t", f"={session_name}", variable_name], sensitive=True
    )


def read_tmux_session_environment_value(*, session_name: str, variable_name: str) -> str | None:
    """Return one optional tmux session environment value."""

    result = show_tmux_environment(session_name=session_name, variable_name=variable_name)
    if result.returncode != 0:
        detail = tmux_error_detail(result).lower()
        if "unknown variable" in detail or "unknown-environment" in detail:
            return None
        raise TmuxCommandError(
            f"Failed to read tmux environment variable `{variable_name}` from "
            f"`{session_name}` (exit {result.returncode})"
        )

    line = (result.stdout or "").strip()
    if not line or line.startswith("-"):
        return None
    expected_prefix = f"{variable_name}="
    if not line.startswith(expected_prefix):
        raise TmuxCommandError(
            f"Unexpected tmux environment output for `{variable_name}` in `{session_name}`"
        )
    value = line[len(expected_prefix) :].strip()
    return value or None


def list_tmux_clients(*, session_name: str) -> tuple[str, ...]:
    """Return attached tmux client identifiers for the exact session."""

    result = TmuxServer().checked_command(
        ["list-clients", "-t", f"={session_name}", "-F", "#{client_tty}"],
    )
    return tuple(line for line in result.stdout.splitlines() if line)


def attach_tmux_session(*, session_name: str) -> None:
    """Attach the caller terminal through the selected libtmux server."""

    TmuxServer().checked_command(["attach-session", "-t", f"={session_name}"])


def list_tmux_panes(*, session_name: str) -> tuple[TmuxPaneRecord, ...]:
    """Return checked pane records across all windows in the exact session."""

    panes = TmuxServer().observe_session(session_name)
    if panes is None:
        raise TmuxCommandError(f"Tmux session `{session_name}` does not exist.")
    return panes


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

    panes = TmuxServer().observe_session(session_name)
    return next((pane for pane in panes or () if pane.pane_id == pane_id), None)


def capture_tmux_pane(*, target: str) -> str:
    """Return the pane's normalized capture and scrollback."""

    return TmuxServer().capture_pane(target, history=True, escape_sequences=True)


def load_tmux_buffer(*, buffer_name: str, text: str) -> None:
    """Load literal text into one named tmux buffer."""

    TmuxServer().load_buffer(buffer_name, text)


def paste_tmux_buffer(*, target: str, buffer_name: str, bracketed_paste: bool = True) -> None:
    """Paste one named tmux buffer into the target pane."""

    TmuxServer().paste_buffer(buffer_name, target, bracketed=bracketed_paste)


def delete_tmux_buffer(*, buffer_name: str) -> None:
    """Delete a buffer on the bound tmux server."""

    TmuxServer().delete_buffer(buffer_name)


def select_tmux_pane(*, target: str) -> None:
    """Select one tmux pane."""

    result = tmux_command(["select-pane", "-t", target])
    if result.returncode != 0:
        detail = tmux_error_detail(result)
        raise TmuxCommandError(
            f"Failed to select tmux pane `{target}`: {detail or 'unknown tmux error'}"
        )


def wait_for_tmux_signal(
    *, signal_name: str, timeout_seconds: float | None = None
) -> TmuxCommandResult:
    """Wait for a tmux wait-for signal."""

    return TmuxServer().wait_for(signal_name, timeout_seconds=timeout_seconds)


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

    server = TmuxServer()
    for segment in segments:
        server.send_keys(target, segment.value, literal=segment.kind == "literal")


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


def tmux_error_detail(result: TmuxCommandResult | subprocess.CompletedProcess[str]) -> str:
    """Extract concise stderr/stdout detail from a tmux command result."""

    detail = (result.stderr or result.stdout or "").strip()
    if not detail and result.returncode != 0:
        return f"tmux exited with status {result.returncode}"
    return detail


def _prefer_live_tmux_pane(panes: tuple[TmuxPaneRecord, ...]) -> TmuxPaneRecord:
    """Prefer the active live pane when multiple tmux panes match."""

    for pane in panes:
        if pane.pane_active and not pane.pane_dead:
            return pane
    for pane in panes:
        if not pane.pane_dead:
            return pane
    return panes[0]
