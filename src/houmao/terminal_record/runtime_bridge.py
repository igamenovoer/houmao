"""Runtime-facing bridge for active terminal-recorder integration."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from houmao.execution.tmux import TmuxCommandError, TmuxServer
from houmao.terminal_record.models import (
    InputCaptureLevel,
    TerminalRecordInputEvent,
    append_ndjson,
    load_live_state,
    load_manifest,
    now_utc_iso,
)


TERMINAL_RECORD_LIVE_STATE_ENV_VAR: Final[str] = "HOUMAO_TERMINAL_RECORD_LIVE_STATE"


def publish_active_terminal_record_session(
    *, tmux: TmuxServer, session_name: str, live_state_path: Path
) -> None:
    """Publish the active recorder live-state pointer into tmux session env."""

    tmux.checked_command(
        [
            "set-environment",
            "-t",
            f"={session_name}",
            TERMINAL_RECORD_LIVE_STATE_ENV_VAR,
            str(live_state_path.resolve()),
        ]
    )


def clear_active_terminal_record_session(
    *, tmux: TmuxServer, session_name: str, live_state_path: Path
) -> None:
    """Clear the session's recorder pointer when it still references this run."""

    if _read_terminal_record_live_state_path(tmux, session_name) == live_state_path:
        tmux.checked_command(
            ["set-environment", "-u", "-t", f"={session_name}", TERMINAL_RECORD_LIVE_STATE_ENV_VAR]
        )


def append_managed_control_input_for_tmux_session(
    *,
    session_name: str,
    sequence: str,
    escape_special_keys: bool,
    tmux_target: str,
) -> None:
    """Append one managed control-input event when an active recorder is present."""

    try:
        live_state_path = _read_terminal_record_live_state_path(TmuxServer(), session_name)
    except TmuxCommandError:
        return
    if live_state_path is None or not live_state_path.is_file():
        return

    live_state = load_live_state(live_state_path)
    if live_state.status != "running" or live_state.mode != "active":
        return

    manifest = load_manifest(Path(live_state.manifest_path))
    if _managed_capture_level(manifest.input_capture_level) is False:
        return

    input_events_path = Path(manifest.run_root) / "input_events.ndjson"
    existing_count = 0
    if input_events_path.is_file():
        existing_count = sum(1 for _ in input_events_path.open("r", encoding="utf-8"))
    event = TerminalRecordInputEvent(
        event_id=f"i{existing_count + 1:06d}",
        elapsed_seconds=_elapsed_seconds(manifest.started_at_utc),
        ts_utc=now_utc_iso(),
        source="managed_send_keys",
        sequence=sequence,
        escape_special_keys=escape_special_keys,
        tmux_target=tmux_target,
    )
    append_ndjson(input_events_path, event.to_payload())


def _read_terminal_record_live_state_path(tmux: TmuxServer, session_name: str) -> Path | None:
    """Return one optional active recorder live-state path from tmux env."""

    result = tmux.command(
        ["show-environment", "-t", f"={session_name}", TERMINAL_RECORD_LIVE_STATE_ENV_VAR]
    )
    if result.returncode and result.stderr.strip() == "unknown variable":
        return None
    result.require_success()
    name, _, value = result.stdout.rstrip("\n").partition("=")
    return Path(value) if name == TERMINAL_RECORD_LIVE_STATE_ENV_VAR and value else None


def _managed_capture_level(level: InputCaptureLevel) -> bool:
    """Return whether managed input events should be persisted for this level."""

    return level in {"authoritative_managed", "managed_only"}


def _elapsed_seconds(started_at_utc: str) -> float:
    """Return elapsed seconds since the recorder started."""

    from datetime import datetime

    started_at = datetime.fromisoformat(started_at_utc)
    return max((datetime.now(started_at.tzinfo) - started_at).total_seconds(), 0.0)
