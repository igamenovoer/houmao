"""Qualify explicit Mail through independently upgraded installed distributions."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def test_mail_upgrade_requires_a_selected_previous_wheel(tmp_path: Path) -> None:
    """Mail qualification cannot silently become a fresh chat-only installation."""

    source = Path(__file__).resolve().parents[3]
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    for name in (
        "houmao-2.4.0-py3-none-any.whl",
        "houmao_cccc-0.2.0-py3-none-any.whl",
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
            "http://127.0.0.1:8849",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "requires the frozen previous plugin wheel" in json.loads(result.stderr)["error"]
    assert not (tmp_path / "run/venv").exists()


def test_mail_wheel_upgrade_preserves_body_and_ordered_consumption(tmp_path: Path) -> None:
    """Upgrade both gateway modes and exercise the real provider's Mail boundary."""

    wheelhouse = os.environ.get("HOUMAO_CCCC_MAIL_WHEELHOUSE")
    previous = os.environ.get("HOUMAO_CCCC_PREVIOUS_PLUGIN_WHEEL")
    endpoint = os.environ.get("HOUMAO_CCCC_TEST_URL")
    assert wheelhouse, "Mail qualification requires HOUMAO_CCCC_MAIL_WHEELHOUSE"
    assert previous, "Mail qualification requires HOUMAO_CCCC_PREVIOUS_PLUGIN_WHEEL"
    assert endpoint, "Mail qualification requires HOUMAO_CCCC_TEST_URL"
    source = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [
            sys.executable,
            str(source / "scripts/qualification/cccc/installed.py"),
            "run-mail",
            "--wheelhouse",
            wheelhouse,
            "--previous-plugin-wheel",
            previous,
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
    assert report["versions"]["houmao-cccc"] == "0.2.0"
    assert report["checkout_imports"] is False
    assert report["offline_install"] is True
    assert report["actual_cccc"] is True
    assert report["cleanup"] == "completed"
    assert report["previous_plugin_artifact"]["filename"].startswith("houmao_cccc-0.1.0-")
    assert {mode["execution_mode"] for mode in report["modes"]} == {
        "detached_process",
        "tmux_auxiliary_window",
    }
    for mode in report["modes"]:
        for evidence in (
            "mail_upgrade_preserved_body",
            "stale_controller_upgrade_preserved",
            "mail_cli",
            "mail_deferred",
            "mail_non_consuming_inspection",
            "mail_ordered_read",
            "mail_receipt_recovery",
            "mail_lost_response",
            "mail_empty_reuse",
            "mail_precommit_size",
            "mail_reference_isolation",
            "mail_credential_refresh",
            "maintained_chat",
        ):
            assert mode[evidence] is True
