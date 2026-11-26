"""Verify public CLI handoff before any caller-local project materialization."""

from pathlib import Path

from click.testing import CliRunner

from houmao.srv_ctrl.commands.main import cli
from houmao.srv_ctrl.commands.output import collect_output_payloads, emit


def test_launch_handoff_preserves_target_only_paths(monkeypatch, tmp_path: Path) -> None:
    """A foreign project/workdir must reach delegation without local existence checks."""

    from houmao.execution import router
    from houmao.srv_ctrl.commands import project_easy

    calls = []
    monkeypatch.setattr(
        router,
        "launch_with_executor",
        lambda name, request, *, project_dir: calls.append((name, request, project_dir)),
    )
    monkeypatch.setattr(
        project_easy,
        "_ensure_project_overlay",
        lambda: (_ for _ in ()).throw(AssertionError("caller prepared project")),
    )
    result = CliRunner().invoke(
        cli,
        [
            "project",
            "--project-dir",
            str(tmp_path / "foreign-project"),
            "agents",
            "launch",
            "--profile",
            "reviewer",
            "--executor",
            "alice",
            "--workdir",
            "/foreign/workdir",
            "--tool-params",
            "@/foreign/params.yaml",
            "--tmux-server",
            "socket",
            "--tmux-socket-path",
            "/foreign/tmux.sock",
        ],
    )
    assert result.exit_code == 0, result.output
    assert calls[0][0] == "alice"
    assert calls[0][1].workdir == Path("/foreign/workdir")
    assert calls[0][1].tool_params == "@/foreign/params.yaml"
    assert calls[0][1].tmux_server == "socket"
    assert calls[0][1].tmux_socket_path == "/foreign/tmux.sock"
    assert calls[0][2] == tmp_path / "foreign-project"
    assert not (tmp_path / "foreign-project").exists()


def test_collect_payloads_is_nested_and_does_not_render(capsys) -> None:
    """Application service collection must preserve structured output without stdout."""

    with collect_output_payloads() as outer:
        emit({"first": 1})
        with collect_output_payloads() as inner:
            emit({"second": 2})
        emit({"last": 3})
    assert outer == [{"first": 1}, {"last": 3}]
    assert inner == [{"second": 2}]
    assert capsys.readouterr().out == ""


def test_admin_executor_commands_are_available() -> None:
    """Recovery commands expose locator maintenance separately from first birth."""

    result = CliRunner().invoke(cli, ["admin", "executors", "--help"])
    assert result.exit_code == 0
    assert "reconcile" in result.output
    assert "forget" in result.output
