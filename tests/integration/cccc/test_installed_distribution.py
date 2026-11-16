"""Require offline installed-wheel CCCC qualification against an actual selected service."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def test_installed_setup_failure_is_explicit(tmp_path: Path) -> None:
    """Missing wheels fail setup before creating an environment or skipping tests."""

    source = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [
            sys.executable,
            str(source / "scripts/qualification/cccc/installed.py"),
            "run",
            "--wheelhouse",
            str(tmp_path / "empty"),
            "--work-root",
            str(tmp_path / "run"),
            "--endpoint",
            "http://127.0.0.1:8849",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Setup requires exactly one wheel" in json.loads(result.stderr)["error"]
    assert not (tmp_path / "run/venv").exists()


def test_independent_wheels_in_both_gateway_process_modes(tmp_path: Path) -> None:
    """Install only selected wheels and inspect actual service handoff receipts."""

    wheelhouse = os.environ.get("HOUMAO_CCCC_WHEELHOUSE")
    endpoint = os.environ.get("HOUMAO_CCCC_TEST_URL")
    assert wheelhouse, "Installed qualification requires HOUMAO_CCCC_WHEELHOUSE"
    assert endpoint, "Installed qualification requires HOUMAO_CCCC_TEST_URL"
    source = Path(__file__).resolve().parents[3]
    work = tmp_path / "installed"
    result = subprocess.run(
        [
            sys.executable,
            str(source / "scripts/qualification/cccc/installed.py"),
            "run",
            "--wheelhouse",
            wheelhouse,
            "--work-root",
            str(work),
            "--endpoint",
            endpoint,
        ],
        cwd=source,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["checkout_imports"] is False
    assert report["offline_install"] is True
    assert report["actual_cccc"] is True
    assert report["cleanup"] == "completed"
    assert {mode["execution_mode"] for mode in report["modes"]} == {
        "detached_process",
        "tmux_auxiliary_window",
    }
    for mode in report["modes"]:
        for evidence in (
            "owner_isolation",
            "chat_handoff",
            "reply_ancestry",
            "reference_continuity",
            "restart_no_replay",
            "attach_preserved_body",
            "broad_listener_disabled",
            "busy_refusal",
            "explicit_retry",
            "gateway_absence_no_replay",
            "body_replacement_fenced",
            "body_death_fenced",
        ):
            assert mode[evidence] is True
