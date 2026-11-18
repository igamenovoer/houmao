"""Qualify installed product and independent plugin wheels without source imports."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def test_missing_wheelhouse_is_an_explicit_setup_failure(tmp_path: Path) -> None:
    """Refuse missing local artifacts before creating an environment or skipping."""

    source_root = Path(__file__).resolve().parents[4]
    driver = source_root / "scripts/qualification/gateway-plugins/qualify.py"
    work_root = tmp_path / "run"
    result = subprocess.run(
        [
            sys.executable,
            str(driver),
            "run",
            "--wheelhouse",
            str(tmp_path / "empty-wheels"),
            "--work-root",
            str(work_root),
        ],
        cwd=source_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    error = json.loads(result.stderr)
    assert error["result"] == "failed"
    assert "Setup requires exactly one wheel" in error["error"]
    assert not (work_root / "venv").exists()


def test_external_plugin_wheels_in_normal_gateway_process_modes(tmp_path: Path) -> None:
    """Require an explicit wheelhouse and run actual detached/tmux gateways."""

    selected = os.environ.get("HOUMAO_GATEWAY_PLUGIN_WHEELHOUSE")
    assert selected, (
        "Installed-wheel qualification setup requires HOUMAO_GATEWAY_PLUGIN_WHEELHOUSE; "
        "prepare it with scripts/qualification/gateway-plugins/qualify.py prepare"
    )
    wheelhouse = Path(selected).resolve()
    assert wheelhouse.is_dir(), "The explicitly selected wheelhouse is missing"
    source_root = Path(__file__).resolve().parents[4]
    driver = source_root / "scripts/qualification/gateway-plugins/qualify.py"
    work_root = tmp_path / "installed-run"
    result = subprocess.run(
        [
            sys.executable,
            str(driver),
            "run",
            "--wheelhouse",
            str(wheelhouse),
            "--work-root",
            str(work_root),
        ],
        cwd=source_root,
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )
    if result.returncode:
        log = work_root / "operations.log"
        diagnostic = log.read_text(encoding="utf-8")[-16000:] if log.exists() else ""
        raise AssertionError(result.stderr + "\n" + diagnostic)
    report = json.loads(result.stdout)
    assert report["result"] == "passed"
    assert report["checkout_imports"] is False
    assert {mode["execution_mode"] for mode in report["modes"]} == {
        "detached_process",
        "tmux_auxiliary_window",
    }
    assert report["owner_isolation"] is True
    assert report["selected_only_imports"] is True
    assert report["cleanup"] == "completed"
    for mode in report["modes"]:
        assert mode["open_and_key_required_controls"] is True
        assert mode["verified_private_callers"] is True
