"""Controlled minimal-demo checks with explicit shared fixture selection."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
SCRIPT = REPO / "scripts/demo/minimal-agent-launch/scripts/run_demo.py"


@pytest.mark.parametrize("provider", ["claude_code", "codex"])
@pytest.mark.parametrize("headless", [False, True])
def test_minimal_demo_preserves_role_transport_and_scoped_cleanup(
    tmp_path, monkeypatch, provider, headless
):
    """Both providers use the same role and current prepared-run lifecycle."""

    spec = importlib.util.spec_from_file_location("minimal_fixture_demo", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL_OPENAI", "https://cloud.example/v1")
    monkeypatch.setenv("DEEPSEEK_BASE_URL_ANTHROPIC", "https://cloud.example/anthropic")
    calls = []
    root = tmp_path / "private-run"

    def prepare(config, **kwargs):
        root.mkdir()
        calls.append(("prepare", config, kwargs))
        assert kwargs["role"] == "minimal-launch"
        assert kwargs["prompt_file"].is_file()
        return {"run_dir": str(root), "status": "prepared"}

    monkeypatch.setattr(module, "prepare_run", prepare)
    monkeypatch.setattr(
        module,
        "launch_run",
        lambda path, **kw: (
            calls.append(("launch", path, kw)) or {"identity": {"agent_id": "captured-id"}}
        ),
    )
    monkeypatch.setattr(
        module,
        "check_run",
        lambda path, **kw: calls.append(("check", path, kw)) or {"status": "launched"},
    )
    monkeypatch.setattr(
        module, "stop_run", lambda path: calls.append(("stop", path)) or {"status": "stopped"}
    )
    argv = [
        "--provider",
        provider,
        "--case",
        "cloud-api",
        "--model",
        "explicit-model",
        "--output-dir",
        str(tmp_path),
    ]
    if headless:
        argv.append("--headless")
    assert module.main(argv) == 0
    config = calls[0][1]
    assert config.client == ("claude" if provider == "claude_code" else "codex")
    assert config.surface == "manager" and config.mode == ("headless" if headless else "tui")
    assert bool(calls[1][2]["prompt"]) == headless
    assert any(call[0] == "stop" for call in calls) == headless
    summary = json.loads((root / "summary.json").read_text())
    assert summary["identity"]["agent_id"] == "captured-id"
    assert "synthetic-key" not in (root / "summary.json").read_text()


def test_minimal_tutorial_uses_external_preparation():
    """The tutorial explains required selection and external state."""

    tutorial = (SCRIPT.parents[1] / "tut-agent-launch-minimal.md").read_text()
    assert "--case cloud-api" in tutorial and "--model MODEL" in tutorial
    assert "fixture.py stop --run-dir" in tutorial
    assert "tests/fixtures/auth-bundles" not in tutorial
