"""Drive the pinned native Web UI through the existing Bun Playwright toolchain."""

from __future__ import annotations

import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
from typing import Any, TextIO


class NativeBrowser:
    """Own one isolated browser context without retaining browser credentials."""

    def __init__(self) -> None:
        self.m_process: subprocess.Popen[str] | None = None
        self.m_metadata: dict[str, Any] = {}

    @property
    def metadata(self) -> dict[str, Any]:
        """Return token-free browser version and selected native target evidence."""

        return dict(self.m_metadata)

    @classmethod
    def from_connection_file(cls, path: Path, *, observe_selection: bool = False) -> NativeBrowser:
        """Start a browser and optionally observe selection without clicking the sidebar."""

        bun = shutil.which("bun")
        if bun is None:
            raise RuntimeError("Bun Playwright prerequisite is missing")
        if path.resolve().is_relative_to(Path(__file__).resolve().parents[5]):
            raise RuntimeError("Browser credentials must remain outside the checkout")
        if path.stat().st_mode & 0o077:
            raise RuntimeError("Browser connection descriptor must be user-private")
        browser = cls()
        browser.m_process = subprocess.Popen(
            [bun, str(Path(__file__).with_name("browser_driver.ts"))],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env={
                key: value for key, value in os.environ.items() if key not in {"TMUX", "TMUX_PANE"}
            },
            start_new_session=True,
        )
        try:
            browser.m_metadata = browser.call(
                "connect", connection_file=str(path), observe_selection=observe_selection
            )
        except BaseException:
            browser.close()
            raise
        return browser

    def call(self, action: str, **parameters: str | bool) -> dict[str, Any]:
        """Execute one action and accept only sanitized metadata from the bridge."""

        process = self.m_process
        if process is None or process.stdin is None or process.stdout is None:
            raise RuntimeError("Browser driver is closed")
        process.stdin.write(json.dumps({"action": action, **parameters}) + "\n")
        process.stdin.flush()
        response = self._read_response(process.stdout)
        if response.get("ok") is not True:
            raise RuntimeError(f"Native browser action failed: {action} ({response.get('stage')})")
        return response

    def close(self) -> None:
        """Close only this driver's browser and owned process group."""

        process = self.m_process
        if process is None:
            return
        try:
            if process.poll() is None:
                self.call("close")
                if process.stdin is not None:
                    process.stdin.close()
                process.wait(timeout=10)
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=10)
        finally:
            self.m_process = None

    @staticmethod
    def _read_response(stdout: TextIO) -> dict[str, Any]:
        """Bound bridge reads and reject malformed or unapproved public output."""

        if not select.select([stdout], [], [], 45)[0]:
            raise RuntimeError("Native browser action timed out")
        try:
            response = json.loads(stdout.readline())
        except ValueError as exc:
            raise RuntimeError("Native browser returned malformed metadata") from exc
        permitted = {
            "ok",
            "origin",
            "session_id",
            "clean_url",
            "browser_version",
            "startup_mutations",
            "action",
            "stage",
            "error",
        }
        if not isinstance(response, dict) or set(response) - permitted:
            raise RuntimeError("Native browser returned unexpected metadata fields")
        return response
