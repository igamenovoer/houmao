"""Lifecycle execution engine for the pending-state capture runner."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

from .models import (
    LifecycleManifest,
    LifecycleStep,
    SendKeyStep,
    SendTextStep,
    WaitForPatternAbsentStep,
    WaitForPatternStep,
    WaitSecondsStep,
)
from .pattern_poller import PatternPoller, check_confirmation_violation


@dataclass
class LifecycleResult:
    """Outcome of one lifecycle execution."""

    success: bool
    transition_times: dict[str, float | None]
    last_visible_text: str
    failure_code: str | None = None
    failure_note: str | None = None
    taint_reasons: tuple[str, ...] = ()


class LifecycleExecutor:
    """Execute one provider lifecycle manifest against a surface poller."""

    def __init__(
        self,
        *,
        manifest: LifecycleManifest,
        poller: PatternPoller,
        start_monotonic: float,
    ) -> None:
        self.m_manifest = manifest
        self.m_poller = poller
        self.m_start_monotonic = start_monotonic
        self.m_patterns = {name: spec.compile() for name, spec in manifest.patterns.items()}
        self.m_transition_times: dict[str, float | None] = {
            "active_onset": None,
            "pending_onset": None,
            "pending_offset": None,
            "done_onset": None,
            "ready_return": None,
        }
        self.m_taint_reasons: list[str] = []

    def run(self) -> LifecycleResult:
        """Run every configured lifecycle step and return the result."""

        for step in self.m_manifest.steps:
            try:
                self._execute_step(step)
            except LifecycleError as exc:
                return LifecycleResult(
                    success=False,
                    transition_times=dict(self.m_transition_times),
                    last_visible_text=exc.visible_text,
                    failure_code=exc.code,
                    failure_note=exc.note,
                )
        return LifecycleResult(
            success=True,
            transition_times=dict(self.m_transition_times),
            last_visible_text=self.m_poller.capture_text(),
            taint_reasons=tuple(self.m_taint_reasons),
        )

    def _execute_step(self, step: LifecycleStep) -> None:
        violation = check_confirmation_violation(self.m_poller.capture_text())
        if violation is not None:
            raise LifecycleError(
                code="unattended_confirmation_violation",
                note=f"Visible confirmation surface: {violation}",
                visible_text=self.m_poller.capture_text(),
            )

        if isinstance(step, WaitSecondsStep):
            self.m_poller.wait_seconds(step.seconds)
            return

        if isinstance(step, WaitForPatternStep):
            pattern = self._resolve_pattern(step.pattern)
            match = self.m_poller.wait_for_pattern(
                pattern=pattern, timeout_seconds=step.timeout_seconds
            )
            self._record_transition(step.pattern, found=match.found)
            if not match.found:
                if step.non_fatal_on_timeout:
                    self.m_taint_reasons.append(f"pattern_timeout_non_fatal:{step.pattern}")
                    return
                if step.required:
                    raise LifecycleError(
                        code=f"pattern_timeout:{step.pattern}",
                        note=f"Pattern `{step.pattern}` did not appear within {step.timeout_seconds}s",
                        visible_text=match.visible_text,
                    )
            return

        if isinstance(step, WaitForPatternAbsentStep):
            pattern = self._resolve_pattern(step.pattern)
            match = self.m_poller.wait_for_pattern_absent(
                pattern=pattern, timeout_seconds=step.timeout_seconds
            )
            self._record_transition(f"{step.pattern}_absent", found=match.found)
            if not match.found and step.required:
                raise LifecycleError(
                    code=f"pattern_persisted:{step.pattern}",
                    note=(f"Pattern `{step.pattern}` persisted beyond {step.timeout_seconds}s"),
                    visible_text=match.visible_text,
                )
            return

        if isinstance(step, SendTextStep):
            self.m_poller.send_text(step.text)
            return

        if isinstance(step, SendKeyStep):
            self.m_poller.send_key(step.key)
            return

        raise LifecycleError(
            code="unsupported_step",
            note=f"Unsupported lifecycle step: {step!r}",
            visible_text=self.m_poller.capture_text(),
        )

    def _resolve_pattern(self, name: str) -> re.Pattern[str]:
        if name not in self.m_patterns:
            raise LifecycleError(
                code="unknown_pattern",
                note=f"Lifecycle step references undefined pattern `{name}`",
                visible_text=self.m_poller.capture_text(),
            )
        return self.m_patterns[name]

    def _record_transition(self, pattern_name: str, *, found: bool) -> None:
        if not found:
            return
        elapsed = max(0.0, time.monotonic() - self.m_start_monotonic)
        if pattern_name == "active" and self.m_transition_times["active_onset"] is None:
            self.m_transition_times["active_onset"] = elapsed
        elif pattern_name == "pending" and self.m_transition_times["pending_onset"] is None:
            self.m_transition_times["pending_onset"] = elapsed
        elif pattern_name == "pending_absent":
            self.m_transition_times["pending_offset"] = elapsed
        elif pattern_name == "active_absent":
            self.m_transition_times["done_onset"] = elapsed
        elif pattern_name == "ready":
            self.m_transition_times["ready_return"] = elapsed


@dataclass
class LifecycleError(Exception):
    """Raised when one lifecycle step cannot complete."""

    code: str
    note: str
    visible_text: str
