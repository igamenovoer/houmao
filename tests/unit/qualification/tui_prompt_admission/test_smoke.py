"""Smoke test using the actual codex lifecycle manifest and a fake poller."""

from __future__ import annotations

import json
from pathlib import Path

from tui_pending_state_capture.lifecycle import LifecycleExecutor
from tui_pending_state_capture.models import load_lifecycle_manifest
from tui_pending_state_capture.pattern_poller import FakePatternPoller


def test_codex_lifecycle_smoke() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    manifest_path = (
        repo_root
        / "scripts"
        / "qualification"
        / "tui-prompt-admission"
        / "lifecycles"
        / "codex.json"
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = load_lifecycle_manifest(payload)

    poller = FakePatternPoller()
    # Repeat each synthetic surface enough times to survive the per-step
    # confirmation check and the polling loops.
    poller.set_frames(
        [""] * 10
        + ["› Find and fix a bug"] * 20
        + ["Working (1/3) ..."] * 20
        + ["Working (2/3) ... Messages to be submitted after next tool call"] * 20
        + ["Working (3/3) ..."] * 20
        + ["› Find and fix a bug"] * 20
    )

    executor = LifecycleExecutor(manifest=manifest, poller=poller, start_monotonic=0.0)
    result = executor.run()

    # The synthetic frames should carry the lifecycle through pending and back.
    assert result.success
    assert result.transition_times["active_onset"] is not None
    assert result.transition_times["pending_onset"] is not None
    assert result.transition_times["pending_offset"] is not None
    assert result.transition_times["ready_return"] is not None

    # The second prompt should have been injected while active.
    send_text_actions = [a for a in poller.m_actions if a["action"] == "send_text"]
    assert len(send_text_actions) == 2
    assert send_text_actions[1]["text"] == manifest.prompts["second"]
