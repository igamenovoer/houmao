"""Verify display selection at the supported project launch commands."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from houmao.srv_ctrl.commands import project_easy
from houmao.srv_ctrl.commands.main import cli


@pytest.fixture
def project_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    """Create a project with a synthetic credential and a specialist supporting all modes."""

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "init"])
    assert result.exit_code == 0, result.output
    result = runner.invoke(
        cli,
        [
            "project",
            "specialist",
            "create",
            "--name",
            "worker",
            "--tool",
            "kimi",
            "--api-key",
            "test",
        ],
    )
    assert result.exit_code == 0, result.output
    return runner


def _create_profile(runner: CliRunner, *options: str) -> None:
    """Save project defaults for the fixture specialist."""

    result = runner.invoke(
        cli,
        [
            "project",
            "profile",
            "create",
            "--name",
            "saved",
            "--specialist",
            "worker",
            "--agent-name",
            "worker-1",
            *options,
        ],
    )
    assert result.exit_code == 0, result.output


def _capture_launch(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Observe the effective launch arguments before starting an agent."""

    launch = Mock()
    monkeypatch.setattr(project_easy, "launch_managed_agent_locally", launch)
    monkeypatch.setattr(project_easy, "build_local_launch_completion", Mock())
    monkeypatch.setattr(project_easy, "render_local_launch_completion", Mock())
    return launch


def test_headless_launch_resolves_each_field_and_preserves_profile(
    project_cli: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    _create_profile(
        project_cli,
        "--mode",
        "headless",
        "--headless-display-style",
        "fancy",
        "--headless-display-detail",
        "detail",
    )
    launch = _capture_launch(monkeypatch)
    for overrides, expected in (
        ([], ("fancy", "detail")),
        (["--headless-display-style", "json"], ("json", "detail")),
        (["--headless-display-detail", "concise"], ("fancy", "concise")),
    ):
        result = project_cli.invoke(
            cli, ["project", "agents", "launch", "--profile", "saved", *overrides]
        )
        assert result.exit_code == 0, result.output
        values = launch.call_args.kwargs
        assert (values["headless_display_style"], values["headless_display_detail"]) == expected

    result = project_cli.invoke(
        cli, ["--print-json", "project", "profile", "get", "--name", "saved"]
    )
    assert result.exit_code == 0, result.output
    posture = json.loads(result.output)["defaults"]["posture"]
    assert posture["headless_display_style"] == "fancy"
    assert posture["headless_display_detail"] == "detail"


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ([], ("plain", "concise")),
        (["--headless-display-style", "json"], ("json", "concise")),
        (["--headless-display-detail", "detail"], ("plain", "detail")),
    ],
)
def test_direct_specialist_launch_uses_explicit_display_and_defaults(
    project_cli: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    overrides: list[str],
    expected: tuple[str, str],
) -> None:
    launch = _capture_launch(monkeypatch)
    result = project_cli.invoke(
        cli,
        [
            "project",
            "agents",
            "launch",
            "--specialist",
            "worker",
            "--name",
            "worker-1",
            "--mode",
            "headless",
            *overrides,
        ],
    )
    assert result.exit_code == 0, result.output
    values = launch.call_args.kwargs
    assert (values["headless_display_style"], values["headless_display_detail"]) == expected


@pytest.mark.parametrize("mode", ["tui", "service", "web"])
@pytest.mark.parametrize("use_profile", [False, True])
def test_non_headless_display_rejection_precedes_launch_preparation(
    project_cli: CliRunner, monkeypatch: pytest.MonkeyPatch, mode: str, use_profile: bool
) -> None:
    display_options = ["--headless-display-style", "plain", "--headless-display-detail", "concise"]
    if use_profile:
        _create_profile(project_cli, "--mode", "headless", *display_options)
        arguments = ["--profile", "saved"]
    else:
        arguments = ["--specialist", "worker", "--name", "worker-1", *display_options]
    projection = Mock()
    monkeypatch.setattr(project_easy, "materialize_project_agent_catalog_projection", projection)
    launch = _capture_launch(monkeypatch)

    result = project_cli.invoke(
        cli, ["project", "agents", "launch", *arguments, "--mode", mode, "--force", "clean"]
    )
    assert result.exit_code == 1, result.output
    assert "require headless mode" in result.output
    assert repr(mode) in result.output
    assert "--headless-display-style" in result.output
    assert "--headless-display-detail" in result.output
    projection.assert_not_called()
    launch.assert_not_called()


def test_direct_headless_mode_enables_saved_display_settings(
    project_cli: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    _create_profile(project_cli, "--mode", "web", "--headless-display-detail", "detail")
    launch = _capture_launch(monkeypatch)
    result = project_cli.invoke(
        cli, ["project", "agents", "launch", "--profile", "saved", "--mode", "headless"]
    )
    assert result.exit_code == 0, result.output
    assert launch.call_args.kwargs["mode"] == "headless"
    assert launch.call_args.kwargs["headless_display_style"] == "plain"
    assert launch.call_args.kwargs["headless_display_detail"] == "detail"


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [("headless_display_style", "silent"), ("headless_display_detail", None)],
)
def test_invalid_stored_display_value_fails_before_projection(
    project_cli: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    field: str,
    bad_value: object,
) -> None:
    _create_profile(project_cli, "--mode", "headless")
    with closing(sqlite3.connect(tmp_path / ".houmao" / "catalog.sqlite")) as catalog, catalog:
        catalog.execute(
            "UPDATE launch_profiles SET posture_payload = ? WHERE name = ?",
            (json.dumps({"mode": "headless", field: bad_value}), "saved"),
        )
    projection = Mock()
    monkeypatch.setattr(project_easy, "materialize_project_agent_catalog_projection", projection)
    launch = _capture_launch(monkeypatch)

    result = project_cli.invoke(cli, ["project", "agents", "launch", "--profile", "saved"])
    assert result.exit_code == 1, result.output
    assert f"defaults.posture.{field} must be one of" in result.output
    projection.assert_not_called()
    launch.assert_not_called()
