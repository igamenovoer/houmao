"""Tmux operations for the Houmao-owned CAO-compatible control core."""

from __future__ import annotations

import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from houmao.agents.realm_controller.backends.tmux_runtime import (
    TMUX_COLOR_ENV_UNSET_NAMES,
    TMUX_CONFIG_INJECTION_ENV_VAR,
    TMUX_RICH_COLOR_COLORTERM,
    TMUX_RICH_COLOR_TERM,
    tmux_config_injection_enabled,
)
from houmao.execution.tmux import TmuxCommandError, TmuxServer

CompatibilityTmuxError = TmuxCommandError
_WINDOW_FORMAT = "#{window_id}\t#{window_index}\t#{window_name}"


@dataclass(frozen=True)
class TmuxWindowRecord:
    """Resolved tmux window identity used by the compatibility core."""

    window_id: str
    window_index: str
    window_name: str


class CompatibilityTmuxController:
    """Preserve compatibility terminal behavior through shared tmux operations."""

    def ensure_tmux_available(self) -> None:
        """Fail fast when tmux is not available on PATH."""

        if shutil.which("tmux") is None:
            raise CompatibilityTmuxError("tmux is not available on PATH.")

    def session_exists(self, *, session_name: str) -> bool:
        """Return whether the exact session exists on the selected server."""

        return session_name in TmuxServer().list_sessions(allow_missing_server=True)

    def create_session_with_window(
        self,
        *,
        session_name: str,
        window_name: str,
        working_directory: Path,
    ) -> TmuxWindowRecord:
        """Create a detached tmux session with one named initial window."""

        tmux = TmuxServer()
        result = tmux.start(
            [
                "new-session",
                "-d",
                "-s",
                session_name,
                "-n",
                window_name,
                "-c",
                str(working_directory),
                "-P",
                "-F",
                f"#{{session_id}}\t{_WINDOW_FORMAT}",
            ],
            environment=tmux.native_environment(),
        )
        result.require_success()
        session_id, _, window_row = result.stdout.partition("\t")
        if not session_id.startswith("$") or not session_id[1:].isdigit():
            raise CompatibilityTmuxError(f"Missing tmux session id for {session_name!r}.")
        try:
            record = self._parse_window_record(window_row, context=session_name)
            self._apply_config_injection(tmux, session_id=session_id, session_name=session_name)
        except CompatibilityTmuxError:
            try:
                tmux.checked_command(["kill-session", "-t", session_id])
            except CompatibilityTmuxError:
                pass
            raise
        return record

    def create_window(
        self,
        *,
        session_name: str,
        window_name: str,
        working_directory: Path,
    ) -> TmuxWindowRecord:
        """Create a detached tmux window in the exact named session."""

        tmux = TmuxServer()
        session_id = self._session_id(tmux, session_name)
        result = tmux.checked_command(
            [
                "new-window",
                "-d",
                "-t",
                f"{session_id}:",
                "-n",
                window_name,
                "-c",
                str(working_directory),
                "-P",
                "-F",
                _WINDOW_FORMAT,
            ]
        )
        return self._parse_window_record(result.stdout, context=session_name)

    def kill_session(self, *, session_name: str) -> None:
        """Terminate one exact tmux session if present."""

        tmux = TmuxServer()
        if session_name in tmux.list_sessions(allow_missing_server=True):
            tmux.checked_command(["kill-session", "-t", self._session_id(tmux, session_name)])

    def kill_window(self, *, window_id: str) -> None:
        """Terminate one tmux window if present."""

        tmux = TmuxServer()
        if not tmux.list_sessions(allow_missing_server=True):
            return
        result = tmux.command(["kill-window", "-t", window_id])
        if result.returncode == 1 and result.stderr.strip() == f"can't find window: {window_id}":
            return
        result.require_success()

    def list_windows(self, *, session_name: str) -> list[TmuxWindowRecord]:
        """Return tmux window records for the exact named session."""

        tmux = TmuxServer()
        result = tmux.checked_command(
            ["list-windows", "-t", self._session_id(tmux, session_name), "-F", _WINDOW_FORMAT]
        )
        return [
            self._parse_window_record(line, context=session_name)
            for line in result.stdout.splitlines()
            if line
        ]

    def list_clients(self, *, session_name: str) -> tuple[str, ...]:
        """Return currently attached tmux clients for one session."""

        tmux = TmuxServer()
        result = tmux.checked_command(
            ["list-clients", "-t", self._session_id(tmux, session_name), "-F", "#{client_tty}"]
        )
        return tuple(result.stdout.splitlines())

    def capture_window(self, *, window_id: str) -> str:
        """Capture rendered text with the original whitespace and trailing blank rows."""

        tmux = TmuxServer()
        pane_id = self._require_window_pane(tmux, window_id)
        result = tmux.capture_exact(["capture-pane", "-p", "-e", "-S", "-", "-t", pane_id])
        result.require_success()
        return result.stdout

    def get_window_working_directory(self, *, window_id: str) -> str | None:
        """Return the current working directory of the window's target pane."""

        pane = self._window_pane(TmuxServer(), window_id)
        if pane is None:
            return None
        return pane[1] or None

    def wait_for_shell(
        self,
        *,
        window_id: str,
        timeout_seconds: float,
        polling_interval_seconds: float,
    ) -> None:
        """Wait until one new shell surface looks stable enough for input."""

        started_at = time.monotonic()
        previous_output: str | None = None
        while time.monotonic() - started_at < timeout_seconds:
            output = self.capture_window(window_id=window_id)
            if output.strip() and previous_output is not None and output == previous_output:
                return
            previous_output = output
            time.sleep(polling_interval_seconds)
        raise CompatibilityTmuxError(
            f"Timed out waiting for shell readiness in tmux window {window_id!r}."
        )

    def send_command(self, *, window_id: str, command: str) -> None:
        """Send one literal shell command followed by Enter."""

        tmux = TmuxServer()
        pane_id = self._require_window_pane(tmux, window_id)
        tmux.send_keys(pane_id, command, literal=True)
        tmux.send_keys(pane_id, "Enter")

    def send_text(self, *, window_id: str, text: str, enter_count: int = 2) -> None:
        """Paste one input payload plus the configured number of Enter keys."""

        tmux = TmuxServer()
        pane_id = self._require_window_pane(tmux, window_id)
        buffer_name = f"houmao_cao_{uuid.uuid4().hex}"
        tmux.load_buffer(buffer_name, text)
        try:
            tmux.paste_buffer(buffer_name, pane_id, delete_after=True)
        except CompatibilityTmuxError:
            try:
                tmux.delete_buffer(buffer_name)
            except CompatibilityTmuxError:
                pass
            raise

        time.sleep(0.3)
        for index in range(enter_count):
            if index > 0:
                time.sleep(0.5)
            tmux.send_keys(pane_id, "Enter")

    def send_special_key(self, *, window_id: str, key_name: str) -> None:
        """Send one tmux special key to a window."""

        tmux = TmuxServer()
        tmux.send_keys(self._require_window_pane(tmux, window_id), key_name)

    @staticmethod
    def _session_id(tmux: TmuxServer, session_name: str) -> str:
        """Return the live session handle from the checked exact observation."""

        panes = tmux.observe_session(session_name)
        if not panes or panes[0].session_id is None:
            raise CompatibilityTmuxError(f"Tmux session {session_name!r} does not exist.")
        return panes[0].session_id

    @staticmethod
    def _window_pane(tmux: TmuxServer, window_id: str) -> tuple[str, str] | None:
        """Return the pane and working path for the compatibility window target."""

        result = tmux.command(
            [
                "display-message",
                "-p",
                "-t",
                f"{window_id}.0",
                "#{window_id}\t#{pane_id}\t#{pane_current_path}",
            ]
        )
        if result.returncode and any(
            reason in result.stderr.lower() for reason in ("can't find pane", "can't find window")
        ):
            return None
        result.require_success()
        if not result.stdout.strip():
            return None
        fields = result.stdout.rstrip("\n").split("\t", maxsplit=2)
        if (
            len(fields) != 3
            or fields[0] != window_id
            or not fields[1].startswith("%")
            or not fields[1][1:].isdigit()
        ):
            raise CompatibilityTmuxError(f"Invalid pane observation for tmux window {window_id!r}.")
        return fields[1], fields[2].strip()

    @classmethod
    def _require_window_pane(cls, tmux: TmuxServer, window_id: str) -> str:
        """Require a pane in the compatibility window before using its exact handle."""

        pane = cls._window_pane(tmux, window_id)
        if pane is None:
            raise CompatibilityTmuxError(f"No tmux pane is available in window {window_id!r}.")
        return pane[0]

    @staticmethod
    def _apply_config_injection(tmux: TmuxServer, *, session_id: str, session_name: str) -> None:
        """Apply Houmao-owned tmux defaults to one compatibility session."""

        if not tmux_config_injection_enabled():
            return

        commands = (
            ["set-option", "-t", session_id, "mouse", "on"],
            ["set-option", "-t", session_id, "default-terminal", TMUX_RICH_COLOR_TERM],
            ["set-option", "-at", session_id, "terminal-overrides", ",*256col*:Tc"],
            ["set-environment", "-t", session_id, "TERM", TMUX_RICH_COLOR_TERM],
            ["set-environment", "-t", session_id, "COLORTERM", TMUX_RICH_COLOR_COLORTERM],
            ["set-environment", "-t", session_id, "-u", TMUX_COLOR_ENV_UNSET_NAMES[0]],
        )
        try:
            for args in commands:
                tmux.checked_command(args)
        except CompatibilityTmuxError as exc:
            raise CompatibilityTmuxError(
                "Failed to apply Houmao tmux config injection to session "
                f"{session_name!r}: {exc}. Set {TMUX_CONFIG_INJECTION_ENV_VAR}=0 "
                "to disable Houmao tmux config injection and retry."
            ) from exc

    @staticmethod
    def _parse_window_record(line: str, *, context: str) -> TmuxWindowRecord:
        """Parse one tmux window listing or creation receipt."""

        parts = line.rstrip("\n").split("\t", maxsplit=2)
        if len(parts) != 3 or not parts[0].startswith("@") or not parts[1].isdigit():
            raise CompatibilityTmuxError(f"Invalid tmux window record for {context!r}.")
        return TmuxWindowRecord(window_id=parts[0], window_index=parts[1], window_name=parts[2])
