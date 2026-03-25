"""Tmux helpers for the Houmao-owned CAO-compatible control core."""

from __future__ import annotations

import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TmuxWindowRecord:
    """Resolved tmux window identity used by the compatibility core."""

    window_id: str
    window_index: str
    window_name: str


class CompatibilityTmuxError(RuntimeError):
    """Raised when tmux operations fail for the compatibility core."""


class CompatibilityTmuxController:
    """Small tmux wrapper used by the native compatibility core."""

    def ensure_tmux_available(self) -> None:
        """Fail fast when `tmux` is not available on `PATH`."""

        if shutil.which("tmux") is None:
            raise CompatibilityTmuxError("`tmux` is not available on PATH.")

    def session_exists(self, *, session_name: str) -> bool:
        """Return whether one tmux session currently exists."""

        result = self._run_tmux(["has-session", "-t", session_name])
        return result.returncode == 0

    def create_session_with_window(
        self,
        *,
        session_name: str,
        window_name: str,
        working_directory: Path,
    ) -> TmuxWindowRecord:
        """Create a detached tmux session with one named initial window."""

        result = self._run_tmux(
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
                "#{window_id}\t#{window_index}\t#{window_name}",
            ]
        )
        if result.returncode != 0:
            raise CompatibilityTmuxError(
                f"Failed to create tmux session `{session_name}`: {self._tmux_detail(result)}"
            )
        return self._parse_window_record(result.stdout.strip(), context=session_name)

    def create_window(
        self,
        *,
        session_name: str,
        window_name: str,
        working_directory: Path,
    ) -> TmuxWindowRecord:
        """Create a detached tmux window in an existing session."""

        result = self._run_tmux(
            [
                "new-window",
                "-d",
                "-t",
                session_name,
                "-n",
                window_name,
                "-c",
                str(working_directory),
                "-P",
                "-F",
                "#{window_id}\t#{window_index}\t#{window_name}",
            ]
        )
        if result.returncode != 0:
            raise CompatibilityTmuxError(
                f"Failed to create tmux window in `{session_name}`: {self._tmux_detail(result)}"
            )
        return self._parse_window_record(result.stdout.strip(), context=session_name)

    def kill_session(self, *, session_name: str) -> None:
        """Terminate one tmux session."""

        result = self._run_tmux(["kill-session", "-t", session_name])
        if result.returncode != 0:
            detail = self._tmux_detail(result).lower()
            if "can't find session" in detail or "no server running" in detail:
                return
            raise CompatibilityTmuxError(
                f"Failed to kill tmux session `{session_name}`: {self._tmux_detail(result)}"
            )

    def kill_window(self, *, window_id: str) -> None:
        """Terminate one tmux window."""

        result = self._run_tmux(["kill-window", "-t", window_id])
        if result.returncode != 0:
            detail = self._tmux_detail(result).lower()
            if "can't find window" in detail or "no server running" in detail:
                return
            raise CompatibilityTmuxError(
                f"Failed to kill tmux window `{window_id}`: {self._tmux_detail(result)}"
            )

    def list_windows(self, *, session_name: str) -> list[TmuxWindowRecord]:
        """Return tmux window records for one session."""

        result = self._run_tmux(
            [
                "list-windows",
                "-t",
                session_name,
                "-F",
                "#{window_id}\t#{window_index}\t#{window_name}",
            ]
        )
        if result.returncode != 0:
            raise CompatibilityTmuxError(
                f"Failed to list tmux windows for `{session_name}`: {self._tmux_detail(result)}"
            )
        return [
            self._parse_window_record(line.strip(), context=session_name)
            for line in result.stdout.splitlines()
            if line.strip()
        ]

    def list_clients(self, *, session_name: str) -> tuple[str, ...]:
        """Return currently attached tmux clients for one session."""

        result = self._run_tmux(["list-clients", "-t", session_name, "-F", "#{client_tty}"])
        if result.returncode != 0:
            detail = self._tmux_detail(result).lower()
            if "no current client" in detail or "no server running" in detail:
                return ()
            raise CompatibilityTmuxError(
                f"Failed to list tmux clients for `{session_name}`: {self._tmux_detail(result)}"
            )
        return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())

    def capture_window(self, *, window_id: str) -> str:
        """Capture the full rendered pane output for one tmux window."""

        result = self._run_tmux(["capture-pane", "-p", "-e", "-S", "-", "-t", f"{window_id}.0"])
        if result.returncode != 0:
            raise CompatibilityTmuxError(
                f"Failed to capture tmux window `{window_id}`: {self._tmux_detail(result)}"
            )
        return result.stdout

    def get_window_working_directory(self, *, window_id: str) -> str | None:
        """Return the current pane working directory for one window."""

        result = self._run_tmux(
            ["display-message", "-p", "-t", f"{window_id}.0", "#{pane_current_path}"]
        )
        if result.returncode != 0:
            detail = self._tmux_detail(result).lower()
            if "can't find pane" in detail or "can't find window" in detail:
                return None
            raise CompatibilityTmuxError(
                f"Failed to read tmux working directory for `{window_id}`: {self._tmux_detail(result)}"
            )
        working_directory = result.stdout.strip()
        return working_directory or None

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
            f"Timed out waiting for shell readiness in tmux window `{window_id}`."
        )

    def send_command(self, *, window_id: str, command: str) -> None:
        """Send one shell command followed by Enter."""

        result = self._run_tmux(["send-keys", "-t", f"{window_id}.0", "-l", command])
        if result.returncode != 0:
            raise CompatibilityTmuxError(
                f"Failed to send tmux command to `{window_id}`: {self._tmux_detail(result)}"
            )
        enter_result = self._run_tmux(["send-keys", "-t", f"{window_id}.0", "Enter"])
        if enter_result.returncode != 0:
            raise CompatibilityTmuxError(
                f"Failed to submit tmux command in `{window_id}`: {self._tmux_detail(enter_result)}"
            )

    def send_text(self, *, window_id: str, text: str, enter_count: int = 2) -> None:
        """Paste one input payload plus the configured number of Enter keys."""

        buffer_name = f"houmao_cao_{uuid.uuid4().hex[:8]}"
        try:
            load_result = subprocess.run(
                ["tmux", "load-buffer", "-b", buffer_name, "-"],
                check=False,
                input=text.encode("utf-8"),
                capture_output=True,
            )
            if load_result.returncode != 0:
                raise CompatibilityTmuxError(
                    f"Failed to load tmux paste buffer `{buffer_name}`: {self._tmux_detail(load_result)}"
                )

            paste_result = self._run_tmux(
                ["paste-buffer", "-p", "-b", buffer_name, "-t", f"{window_id}.0"]
            )
            if paste_result.returncode != 0:
                raise CompatibilityTmuxError(
                    f"Failed to paste tmux buffer into `{window_id}`: {self._tmux_detail(paste_result)}"
                )

            time.sleep(0.3)
            for index in range(enter_count):
                if index > 0:
                    time.sleep(0.5)
                enter_result = self._run_tmux(["send-keys", "-t", f"{window_id}.0", "Enter"])
                if enter_result.returncode != 0:
                    raise CompatibilityTmuxError(
                        f"Failed to send Enter to `{window_id}`: {self._tmux_detail(enter_result)}"
                    )
        finally:
            self._run_tmux(["delete-buffer", "-b", buffer_name])

    def send_special_key(self, *, window_id: str, key_name: str) -> None:
        """Send one tmux special key to a window."""

        result = self._run_tmux(["send-keys", "-t", f"{window_id}.0", key_name])
        if result.returncode != 0:
            raise CompatibilityTmuxError(
                f"Failed to send special key `{key_name}` to `{window_id}`: {self._tmux_detail(result)}"
            )

    def _run_tmux(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """Run one tmux command with normalized error handling."""

        try:
            return subprocess.run(
                ["tmux", *args],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            raise CompatibilityTmuxError(f"Failed to run tmux command `{args}`: {exc}") from exc

    @staticmethod
    def _tmux_detail(result: subprocess.CompletedProcess[object]) -> str:
        """Return concise tmux stderr or stdout detail."""

        stderr = (
            result.stderr.decode("utf-8", errors="replace")
            if isinstance(result.stderr, bytes)
            else result.stderr
        )
        stdout = (
            result.stdout.decode("utf-8", errors="replace")
            if isinstance(result.stdout, bytes)
            else result.stdout
        )
        return str(stderr or stdout or "unknown tmux error").strip()

    @staticmethod
    def _parse_window_record(line: str, *, context: str) -> TmuxWindowRecord:
        """Parse one tmux window listing row."""

        parts = line.split("\t", maxsplit=2)
        if len(parts) != 3:
            raise CompatibilityTmuxError(
                f"Failed to parse tmux window record for `{context}`: unexpected row `{line}`."
            )
        return TmuxWindowRecord(
            window_id=parts[0],
            window_index=parts[1],
            window_name=parts[2],
        )
