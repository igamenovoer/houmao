"""Controlled checks for explicit native-login smoke selection and cleanup."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("failed", [False, True])
def test_native_smoke_uses_explicit_external_bundle_and_always_stops(tmp_path, monkeypatch, failed):
    """Source state remains untouched and cleanup uses only the returned private run."""

    spec = importlib.util.spec_from_file_location(
        "claude_native_smoke", REPO / "tests/manual/manual_claude_official_login_smoke.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    bundle = tmp_path / "auth/claude/work/files"
    bundle.mkdir(parents=True)
    original = bundle / ".credentials.json"
    original.write_text('{"claudeAiOauth":{"accessToken":"synthetic-native"}}')
    before = original.read_bytes(), original.stat().st_mtime_ns
    root = tmp_path / "private-run"
    root.mkdir()
    calls = []

    def prepare(config, **kwargs):
        assert config.auth_method == "native-login" and config.case is None
        assert config.native_bundle == bundle.parent
        calls.append("prepare")
        return {"run_dir": str(root)}

    def launch(path, **kwargs):
        assert path == root
        calls.append("launch")
        if failed:
            raise module.FixtureError("controlled failure")
        return {"identity": {"agent_id": "captured-native-id"}}

    monkeypatch.setattr(module, "prepare_run", prepare)
    monkeypatch.setattr(module, "launch_run", launch)
    monkeypatch.setattr(module, "stop_run", lambda path: calls.append(("stop", path)))
    assert module.main(["--auth-bundle", "work", "--auth-root", str(tmp_path / "auth")]) == (
        2 if failed else 0
    )
    assert calls[-1] == ("stop", root)
    assert (original.read_bytes(), original.stat().st_mtime_ns) == before
