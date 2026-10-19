"""TUI-only equivalence gate for a disabled hook observation channel.

Replays the frozen Claude 2.1.296 qualification recordings through
``LiveSessionTracker`` twice: once with no hook channel and once with a
disabled channel backed by a store that contains hook events. Every pre-existing
projected field must be identical, and the additive channel metadata is the only
allowed difference.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import pytest

from houmao.hook_observation.reader import HookObservationChannel
from houmao.hook_observation.store import HookObservationStore
from houmao.server.models import HoumaoTrackedSessionIdentity
from houmao.server.tui.tracking import LiveSessionTracker

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "shared_tui_tracking"
    / "claude"
    / "qualification"
)
_ADDITIVE_DIAGNOSTIC_FIELDS = {
    "hook_channel_state",
    "hook_counters",
    "hook_conflict_reasons",
}


def _identity() -> HoumaoTrackedSessionIdentity:
    return HoumaoTrackedSessionIdentity(
        tracked_session_id="claude-qualification",
        session_name="claude-qualification",
        tool="claude",
        observed_tool_version="2.1.296",
        tmux_session_name="HOUMAO-claude-qualification",
        terminal_aliases=["abcd1234"],
    )


def _snapshots(fixture_dir: Path) -> list[dict[str, Any]]:
    with gzip.open(fixture_dir / "pane_snapshots.ndjson.gz", "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _tracker(*, hook_channel: HookObservationChannel | None) -> LiveSessionTracker:
    return LiveSessionTracker(
        identity=_identity(),
        recent_transition_limit=24,
        snapshot_history_limit=8,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
        hook_channel=hook_channel,
    )


def _disabled_channel(tmp_path: Path) -> HookObservationChannel:
    store = HookObservationStore(tmp_path, generation=1)
    store.append_event({"hook_event_name": "UserPromptSubmit", "prompt_id": "ignored"})
    store.append_event({"hook_event_name": "Stop", "prompt_id": "ignored", "background_tasks": []})
    status = json.loads(store.channel_path.read_text(encoding="utf-8"))
    status["state"] = "disabled_by_policy"
    store.channel_path.write_text(json.dumps(status), encoding="utf-8")
    channel = HookObservationChannel.from_session_root(tmp_path)
    assert channel is not None
    return channel


def _projection_payload(state_payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(state_payload)
    payload.pop("observation_channels", None)
    diagnostics = dict(payload["diagnostics"])
    for field in _ADDITIVE_DIAGNOSTIC_FIELDS:
        diagnostics.pop(field, None)
    payload["diagnostics"] = diagnostics
    return payload


@pytest.mark.parametrize(
    "session_fixture",
    ["session1_lifecycle", "session2_operator_surfaces_002", "session2_operator_surfaces"],
)
def test_disabled_channel_projection_equals_no_channel(
    session_fixture: str, tmp_path: Path
) -> None:
    fixture_dir = _FIXTURE_ROOT / session_fixture
    snapshots = _snapshots(fixture_dir)
    plain = _tracker(hook_channel=None)
    disabled = _tracker(hook_channel=_disabled_channel(tmp_path))

    for index, snapshot in enumerate(snapshots):
        at = float(snapshot["elapsed_seconds"])
        output_text = str(snapshot["output_text"])
        observed_at_utc = f"2026-10-12T14:{index // 60 % 60:02d}:{index % 60:02d}+00:00"
        plain_state = plain.record_cycle(
            identity=_identity(),
            observed_at_utc=observed_at_utc,
            monotonic_ts=at,
            transport_state="tmux_up",
            process_state="tui_up",
            parse_status="parsed",
            probe_snapshot=None,
            probe_error=None,
            parse_error=None,
            parsed_surface=None,
            output_text=output_text,
        )
        disabled_state = disabled.record_cycle(
            identity=_identity(),
            observed_at_utc=observed_at_utc,
            monotonic_ts=at,
            transport_state="tmux_up",
            process_state="tui_up",
            parse_status="parsed",
            probe_snapshot=None,
            probe_error=None,
            parse_error=None,
            parsed_surface=None,
            output_text=output_text,
        )

        plain_payload = _projection_payload(plain_state.model_dump(mode="json"))
        disabled_payload = _projection_payload(disabled_state.model_dump(mode="json"))
        assert disabled_payload == plain_payload, f"projection diverged at sample {index}"
        assert disabled_state.observation_channels is not None
        assert disabled_state.observation_channels[0].state == "disabled_by_policy"
        assert disabled_state.work == "unknown"
        assert disabled_state.settled is False
