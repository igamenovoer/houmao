"""Tracker-blind tmux interaction primitives for the capture runner."""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, cast

from houmao.agents.realm_controller.backends.tmux_runtime import (  # type: ignore[import-untyped]
    capture_tmux_pane,
    parse_tmux_control_input,
    send_tmux_control_input,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.preflight import (  # type: ignore[import-untyped]
    find_confirmation_violation,
)
from houmao.demo.shared_tui_tracking_demo_pack.tooling import (  # type: ignore[import-untyped]
    capture_visible_pane_text,
)
from houmao.terminal_record.runtime_bridge import (  # type: ignore[import-untyped]
    append_managed_control_input_for_tmux_session,
)


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


@dataclass(frozen=True)
class PatternMatch:
    """Result of one visible-text pattern poll."""

    found: bool
    visible_text: str
    plain_text: str


class PatternPoller(ABC):
    """Abstract surface poller used by the lifecycle executor."""

    @abstractmethod
    def capture_text(self) -> str:
        """Return the latest visible pane text."""

    @abstractmethod
    def wait_seconds(self, seconds: float) -> None:
        """Sleep for a fixed duration."""

    @abstractmethod
    def wait_for_pattern(self, pattern: re.Pattern[str], timeout_seconds: float) -> PatternMatch:
        """Poll until the regex matches or time runs out."""

    @abstractmethod
    def wait_for_pattern_absent(
        self, pattern: re.Pattern[str], timeout_seconds: float
    ) -> PatternMatch:
        """Poll until the regex no longer matches or time runs out."""

    @abstractmethod
    def send_text(self, text: str) -> None:
        """Send literal text."""

    @abstractmethod
    def send_key(self, key: str) -> None:
        """Send one tmux special key."""


@dataclass
class TmuxPatternPoller(PatternPoller):
    """Real tmux-backed poller for live provider capture."""

    m_session_name: str
    m_pane_id: str
    m_poll_interval_seconds: float = 0.25

    def capture_text(self) -> str:
        """Capture the currently visible pane surface."""

        return cast(str, capture_visible_pane_text(pane_id=self.m_pane_id))

    def wait_seconds(self, seconds: float) -> None:
        time.sleep(seconds)

    def wait_for_pattern(self, pattern: re.Pattern[str], timeout_seconds: float) -> PatternMatch:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            visible_text = self.capture_text()
            plain_text = strip_ansi(visible_text)
            if pattern.search(plain_text):
                return PatternMatch(found=True, visible_text=visible_text, plain_text=plain_text)
            time.sleep(self.m_poll_interval_seconds)
        visible_text = self.capture_text()
        return PatternMatch(
            found=False, visible_text=visible_text, plain_text=strip_ansi(visible_text)
        )

    def wait_for_pattern_absent(
        self, pattern: re.Pattern[str], timeout_seconds: float
    ) -> PatternMatch:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            visible_text = self.capture_text()
            plain_text = strip_ansi(visible_text)
            if not pattern.search(plain_text):
                return PatternMatch(found=True, visible_text=visible_text, plain_text=plain_text)
            time.sleep(self.m_poll_interval_seconds)
        visible_text = self.capture_text()
        return PatternMatch(
            found=False, visible_text=visible_text, plain_text=strip_ansi(visible_text)
        )

    def send_text(self, text: str) -> None:
        segments = parse_tmux_control_input(sequence=text, escape_special_keys=True)
        send_tmux_control_input(target=self.m_pane_id, segments=segments)
        append_managed_control_input_for_tmux_session(
            session_name=self.m_session_name,
            sequence=text,
            escape_special_keys=True,
            tmux_target=self.m_pane_id,
        )

    def send_key(self, key: str) -> None:
        token = _key_to_token(key)
        segments = parse_tmux_control_input(sequence=token)
        send_tmux_control_input(target=self.m_pane_id, segments=segments)
        append_managed_control_input_for_tmux_session(
            session_name=self.m_session_name,
            sequence=token,
            escape_special_keys=False,
            tmux_target=self.m_pane_id,
        )


@dataclass
class FakePatternPoller(PatternPoller):
    """In-memory poller for deterministic unit/smoke tests."""

    m_frames: list[str] = field(default_factory=list)
    m_frame_index: int = 0
    m_actions: list[dict[str, Any]] = field(default_factory=list)
    m_time: float = 0.0

    def set_frames(self, frames: list[str]) -> None:
        """Replace the queued visible-text frames."""

        self.m_frames = frames
        self.m_frame_index = 0

    def capture_text(self) -> str:
        if not self.m_frames:
            return ""
        frame = self.m_frames[min(self.m_frame_index, len(self.m_frames) - 1)]
        self.m_frame_index += 1
        return frame

    def wait_seconds(self, seconds: float) -> None:
        self.m_time += seconds
        self.m_actions.append({"action": "wait_seconds", "seconds": seconds})

    def wait_for_pattern(self, pattern: re.Pattern[str], timeout_seconds: float) -> PatternMatch:
        deadline = self.m_time + timeout_seconds
        while self.m_time < deadline:
            visible_text = self.capture_text()
            plain_text = strip_ansi(visible_text)
            self.m_actions.append({"action": "poll", "pattern": pattern.pattern})
            if pattern.search(plain_text):
                return PatternMatch(found=True, visible_text=visible_text, plain_text=plain_text)
            self.m_time += 0.25
        visible_text = self.capture_text()
        return PatternMatch(
            found=False, visible_text=visible_text, plain_text=strip_ansi(visible_text)
        )

    def wait_for_pattern_absent(
        self, pattern: re.Pattern[str], timeout_seconds: float
    ) -> PatternMatch:
        deadline = self.m_time + timeout_seconds
        while self.m_time < deadline:
            visible_text = self.capture_text()
            plain_text = strip_ansi(visible_text)
            self.m_actions.append({"action": "poll", "pattern": pattern.pattern})
            if not pattern.search(plain_text):
                return PatternMatch(found=True, visible_text=visible_text, plain_text=plain_text)
            self.m_time += 0.25
        visible_text = self.capture_text()
        return PatternMatch(
            found=False, visible_text=visible_text, plain_text=strip_ansi(visible_text)
        )

    def send_text(self, text: str) -> None:
        self.m_actions.append({"action": "send_text", "text": text})

    def send_key(self, key: str) -> None:
        self.m_actions.append({"action": "send_key", "key": key})


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from terminal text."""

    return ANSI_ESCAPE_RE.sub("", text)


def _key_to_token(key: str) -> str:
    """Map a human key name to the tmux control-input token syntax."""

    mapping = {
        "Enter": "<[Enter]>",
        "Return": "<[Enter]>",
        "Escape": "<[Escape]>",
        "Esc": "<[Escape]>",
        "Ctrl+C": "<[C-c]>",
        "C-c": "<[C-c]>",
        "Ctrl+D": "<[C-d]>",
        "C-d": "<[C-d]>",
        "Ctrl+U": "<[C-u]>",
        "C-u": "<[C-u]>",
        "Backspace": "<[BSpace]>",
        "Tab": "<[Tab]>",
        "Up": "<[Up]>",
        "Down": "<[Down]>",
        "Left": "<[Left]>",
        "Right": "<[Right]>",
    }
    if key in mapping:
        return mapping[key]
    if key.startswith("<[") and key.endswith("]>"):
        return key
    raise ValueError(f"unsupported tmux key name: {key!r}")


def check_confirmation_violation(visible_text: str) -> str | None:
    """Return the first unallowlisted confirmation surface, if any."""

    return cast(str | None, find_confirmation_violation(visible_text=visible_text))


def capture_full_pane_text(pane_id: str) -> str:
    """Return the full pane capture (including scrollback) for one pane id."""

    return cast(str, capture_tmux_pane(target=pane_id))
