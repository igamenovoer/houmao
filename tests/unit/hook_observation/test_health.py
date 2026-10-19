"""Unit tests for the hook channel health state machine."""

from __future__ import annotations

from houmao.hook_observation.health import (
    STARTUP_GRACE_SECONDS,
    STALENESS_THRESHOLD_SECONDS,
    HookChannelHealthMonitor,
)


def _observe(
    monitor: HookChannelHealthMonitor,
    *,
    at: float,
    events: int = 0,
    tui_changed: bool = False,
    collector_status: str | None = None,
    read_error: str | None = None,
) -> str:
    return monitor.observe(
        now_monotonic=at,
        now_utc=f"2026-10-19T13:00:{int(at) % 60:02d}+00:00",
        events_this_cycle=events,
        tui_changed=tui_changed,
        collector_status=collector_status,
        read_error=read_error,
    ).state


def test_default_thresholds_are_the_documented_values() -> None:
    assert STARTUP_GRACE_SECONDS == 15.0
    assert STALENESS_THRESHOLD_SECONDS == 30.0


def test_startup_grace_then_unavailable_detail() -> None:
    monitor = HookChannelHealthMonitor()

    assert _observe(monitor, at=0.0) == "unavailable"
    assert _observe(monitor, at=14.0) == "unavailable"
    assert monitor.snapshot().detail == "No hook event has arrived yet."

    assert _observe(monitor, at=16.0) == "unavailable"
    assert monitor.snapshot().detail == "No hook event arrived within the startup grace period."


def test_event_within_grace_activates_channel() -> None:
    monitor = HookChannelHealthMonitor()

    assert _observe(monitor, at=14.9) == "unavailable"
    assert _observe(monitor, at=15.0, events=1) == "active"
    assert monitor.snapshot().last_event_at_utc is not None


def test_active_becomes_stale_only_while_tui_changes() -> None:
    monitor = HookChannelHealthMonitor()

    assert _observe(monitor, at=0.0, events=1) == "active"
    assert _observe(monitor, at=31.0, tui_changed=False) == "active"
    assert _observe(monitor, at=61.0, tui_changed=True) == "stale"
    assert monitor.snapshot().detail is not None


def test_stale_recovers_on_next_event() -> None:
    monitor = HookChannelHealthMonitor()

    _observe(monitor, at=0.0, events=1)
    assert _observe(monitor, at=31.0, tui_changed=True) == "stale"
    assert _observe(monitor, at=32.0, events=1) == "active"


def test_read_error_is_reported_and_recovers() -> None:
    monitor = HookChannelHealthMonitor()

    assert _observe(monitor, at=0.0, events=1) == "active"
    assert _observe(monitor, at=1.0, read_error="store unreadable") == "error"
    assert _observe(monitor, at=2.0, events=1) == "active"


def test_stopped_collector_is_terminal() -> None:
    monitor = HookChannelHealthMonitor()

    _observe(monitor, at=0.0, events=1)
    assert _observe(monitor, at=1.0, collector_status="stopped") == "stopped"
    assert _observe(monitor, at=2.0, events=1) == "stopped"


def test_forced_policy_states_never_follow_events() -> None:
    for forced_state in ("disabled_by_policy", "untrusted_workspace", "error", "stopped"):
        monitor = HookChannelHealthMonitor(forced_state=forced_state)  # type: ignore[arg-type]
        assert _observe(monitor, at=0.0, events=5) == forced_state


def test_bounded_detail_rejects_multiline_and_long_text() -> None:
    monitor = HookChannelHealthMonitor()

    _observe(monitor, at=0.0, events=1)
    assert _observe(monitor, at=1.0, read_error="line one\nline two " + "x" * 400) == "error"
    detail = monitor.snapshot().detail
    assert detail is not None
    assert "\n" not in detail
    assert len(detail) <= 160
