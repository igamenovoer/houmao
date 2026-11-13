"""Verify Kimi hook smoke uses explicitly imported external fixture inputs."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


def test_kimi_smoke_requires_selected_bundle_and_uses_shared_preparation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing state cannot trigger a personal-home copy into the checkout."""

    repo = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(
        "kimi_hook_fixture_smoke", repo / "tests/manual/manual_kimi_hook_observation_smoke.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    selected = tmp_path / "external-auth/kimi/work"
    output = tmp_path / "private-output"
    output.mkdir(mode=0o700)
    with pytest.raises(module.ScenarioFailure, match="Import a Kimi native bundle explicitly"):
        module._ensure_bundle(output, selected)
    assert not selected.exists()
    credentials = selected / "files/credentials/kimi-code.json"
    credentials.parent.mkdir(parents=True)
    credentials.write_text('{"access_token":"synthetic-native-token"}')
    (selected / "import.json").write_text('{"schema_version":1,"client":"kimi"}')
    before = credentials.read_bytes(), credentials.stat().st_mtime_ns
    provenance = module._ensure_bundle(output, selected)
    assert provenance.storage_check == {"outside_checkout": True}
    calls = []
    run_dir = output / "owned-run"
    run_dir.mkdir()
    workdir = run_dir / "workdir"
    workdir.mkdir()
    (run_dir / "private-env.json").write_text("{}")

    def prepare(config, **kwargs):
        calls.append((config, kwargs))
        assert config.native_bundle == selected
        assert config.auth_method == "native-login" and config.case is None
        return {
            "run_dir": str(run_dir),
            "workdir": str(workdir),
            "home_path": str(run_dir / "home"),
            "configuration": {"client": "kimi", "mode": "tui", "surface": "manager"},
        }

    monkeypatch.setattr(module, "prepare_run", prepare)
    ctx = module._prepare_run(
        scenario=module.SCENARIOS["multi-turn"],
        run_root=output,
        kimi_bin=Path(sys.executable),
        kimi_version="fixture 2.6.0",
        bundle=provenance,
        stamp="controlled",
    )
    assert calls[0][1]["role"] == "gpu-kernel-coder"
    assert ctx.run_dir == run_dir and (run_dir / "evidence").is_dir()
    stopped = []
    monkeypatch.setattr(module, "stop_run", lambda path: stopped.append(path))
    module._teardown(ctx, None)
    assert stopped == [run_dir]
    assert (credentials.read_bytes(), credentials.stat().st_mtime_ns) == before
    assert "synthetic-native-token" not in json.dumps(
        json.loads((output / "bundle-provenance.json").read_text())
    )
