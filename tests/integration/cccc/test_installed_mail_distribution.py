"""Qualify explicit Mail recovery through independently installed v2 wheels."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def test_mail_recovery_requires_a_dedicated_loopback_endpoint(tmp_path: Path) -> None:
    """Reject a missing or unsuitable provider before starting the wheel runner."""

    source = Path(__file__).resolve().parents[3]
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    for name in (
        "houmao-3.0.0rc8-py3-none-any.whl",
        "houmao_cccc-0.3.0-py3-none-any.whl",
        "houmao_gateway_qualification_fixtures-0.1.0-py3-none-any.whl",
    ):
        (wheelhouse / name).touch()
    result = subprocess.run(
        [
            sys.executable,
            str(source / "scripts/qualification/cccc/installed.py"),
            "run-mail",
            "--wheelhouse",
            str(wheelhouse),
            "--work-root",
            str(tmp_path / "run"),
            "--endpoint",
            "https://cccc.example",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "dedicated loopback CCCC endpoint" in json.loads(result.stderr)["error"]
    assert not (tmp_path / "run/venv").exists()


def test_installed_mail_reconnect_preserves_body_and_ordered_consumption(tmp_path: Path) -> None:
    """Exercise Mail with current installed wheels in both gateway modes."""

    wheelhouse = os.environ.get("HOUMAO_CCCC_MAIL_WHEELHOUSE")
    endpoint = os.environ.get("HOUMAO_CCCC_TEST_URL")
    assert wheelhouse, "Mail qualification requires HOUMAO_CCCC_MAIL_WHEELHOUSE"
    assert endpoint, "Mail qualification requires HOUMAO_CCCC_TEST_URL"
    source = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [
            sys.executable,
            str(source / "scripts/qualification/cccc/installed.py"),
            "run-mail",
            "--wheelhouse",
            wheelhouse,
            "--work-root",
            str(tmp_path / "installed"),
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
    assert report["action"] == "run-mail"
    assert report["checkout_imports"] is False
    assert report["offline_install"] is True
    assert report["actual_cccc"] is True
    assert report["receiver_protocol_version"] == 2
    assert report["cleanup"] == "completed"
    assert len(report["artifacts"]) == 3
    version = report["versions"]["houmao-cccc"]
    assert any(
        artifact["filename"].startswith(f"houmao_cccc-{version}-")
        for artifact in report["artifacts"]
    )
    assert {mode["execution_mode"] for mode in report["modes"]} == {
        "detached_process",
        "tmux_auxiliary_window",
    }
    for mode in report["modes"]:
        for evidence in (
            "mail_reconnect_preserved_body",
            "stale_controller_reconnect_preserved",
            "mail_cli",
            "mail_deferred",
            "mail_non_consuming_inspection",
            "mail_ordered_read",
            "mail_receipt_recovery",
            "mail_lost_response",
            "mail_receipt_gateway_restart",
            "mail_empty_reuse",
            "mail_precommit_size",
            "mail_reference_isolation",
            "mail_credential_refresh",
            "maintained_chat",
        ):
            assert mode[evidence] is True
