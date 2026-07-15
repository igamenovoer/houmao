"""Unit tests for lifecycle manifest parsing and validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tui_pending_state_capture.models import (
    LifecycleManifest,
    SendKeyStep,
    SendTextStep,
    WaitForPatternAbsentStep,
    WaitForPatternStep,
    WaitSecondsStep,
    load_lifecycle_manifest,
)


MINIMAL_MANIFEST = {
    "schema_version": 1,
    "provider": "codex",
    "calibrated_version": "1.2.3",
    "patterns": {
        "ready": {"regex": "ready", "description": "ready cue"},
        "active": {"regex": "active", "description": "active cue"},
        "pending": {"regex": "pending", "description": "pending cue"},
    },
    "prompts": {"first": "hello", "second": "world"},
    "steps": [
        {"kind": "wait_seconds", "seconds": 0.5},
        {"kind": "wait_for_pattern", "pattern": "ready", "timeout_seconds": 10},
        {"kind": "send_text", "text": "{{first}}"},
        {"kind": "send_key", "key": "Enter"},
        {"kind": "send_text", "text": "{{second}}"},
        {"kind": "wait_for_pattern_absent", "pattern": "active", "timeout_seconds": 5},
    ],
}


def test_load_lifecycle_manifest_parses_steps() -> None:
    manifest = load_lifecycle_manifest(MINIMAL_MANIFEST)
    assert isinstance(manifest, LifecycleManifest)
    assert manifest.provider == "codex"
    assert manifest.calibrated_version == "1.2.3"
    assert set(manifest.patterns) == {"ready", "active", "pending"}
    assert manifest.prompts == {"first": "hello", "second": "world"}

    steps = manifest.steps
    assert len(steps) == 6
    assert isinstance(steps[0], WaitSecondsStep) and steps[0].seconds == 0.5
    assert isinstance(steps[1], WaitForPatternStep) and steps[1].pattern == "ready"
    assert isinstance(steps[2], SendTextStep) and steps[2].text == "hello"
    assert isinstance(steps[3], SendKeyStep) and steps[3].key == "Enter"
    assert isinstance(steps[4], SendTextStep) and steps[4].text == "world"
    assert isinstance(steps[5], WaitForPatternAbsentStep)


def test_prompt_placeholders_are_resolved() -> None:
    manifest = load_lifecycle_manifest(MINIMAL_MANIFEST)
    text_step = next(step for step in manifest.steps if isinstance(step, SendTextStep))
    assert "{{" not in text_step.text


def test_unknown_step_kind_raises() -> None:
    payload = {**MINIMAL_MANIFEST, "steps": [{"kind": "warp_drive"}]}
    with pytest.raises(ValueError, match="unknown step kind"):
        load_lifecycle_manifest(payload)


def test_missing_prompt_placeholder_raises() -> None:
    payload = {
        **MINIMAL_MANIFEST,
        "steps": [{"kind": "send_text", "text": "{{missing}}"}],
    }
    with pytest.raises(ValueError, match="not defined in manifest"):
        load_lifecycle_manifest(payload)


def test_invalid_provider_raises() -> None:
    payload = {**MINIMAL_MANIFEST, "provider": "gemini"}
    with pytest.raises(ValueError, match="provider must be one of"):
        load_lifecycle_manifest(payload)


def test_default_lifecycle_files_are_valid_json() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    lifecycle_dir = repo_root / "scripts" / "qualification" / "tui-prompt-admission" / "lifecycles"
    for path in lifecycle_dir.glob("*.json"):
        if "-calibration" in path.name:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        manifest = load_lifecycle_manifest(payload)
        provider_from_stem = path.stem.split("-")[0]
        assert manifest.provider == provider_from_stem
        assert "ready" in manifest.patterns
        assert "active" in manifest.patterns
        assert "pending" in manifest.patterns


def test_long_canary_prompt_is_preserved_in_manifest() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    for provider in ("claude", "codex", "kimi"):
        path = (
            repo_root
            / "scripts"
            / "qualification"
            / "tui-prompt-admission"
            / "lifecycles"
            / f"{provider}-3-pending-long.json"
        )
        manifest = load_lifecycle_manifest(json.loads(path.read_text(encoding="utf-8")))
        long_prompt = manifest.prompts["follow_up_3_long"]
        assert "[CANARY-500-CHARS-PENDING]" in long_prompt
        assert len(long_prompt) >= 450


def test_non_fatal_on_timeout_step_is_parsed() -> None:
    payload = {
        **MINIMAL_MANIFEST,
        "steps": [
            {
                "kind": "wait_for_pattern",
                "pattern": "pending",
                "timeout_seconds": 5,
                "non_fatal_on_timeout": True,
            }
        ],
    }
    manifest = load_lifecycle_manifest(payload)
    step = manifest.steps[0]
    assert isinstance(step, WaitForPatternStep)
    assert step.non_fatal_on_timeout is True
