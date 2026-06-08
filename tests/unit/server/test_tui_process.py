from __future__ import annotations

import subprocess

import pytest

from houmao.agents.realm_controller.backends import local_interactive as local_interactive_module
from houmao.server.config import HoumaoServerConfig
from houmao.server.tui.process import PaneProcessInspector


def _completed(
    *, stdout: str, returncode: int = 0, stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["ps"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_process_inspector_detects_supported_process_up(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        return _completed(
            stdout=(
                "4321 1000 bash /bin/bash\n"
                "5000 4321 python python helper.py\n"
                "5001 4321 codex codex app-server\n"
            )
        )

    monkeypatch.setattr("subprocess.run", _fake_run)
    inspector = PaneProcessInspector(supported_processes={"codex": ("codex",)})

    result = inspector.inspect(tool="codex", pane_pid=4321)

    assert result.process_state == "tui_up"
    assert result.matched_process_names == ("codex",)
    assert result.matched_processes[0].pid == 5001


@pytest.mark.parametrize("command_name", ["kimi-code", "kimi"])
def test_process_inspector_detects_kimi_tui_process_names(
    monkeypatch: pytest.MonkeyPatch,
    command_name: str,
) -> None:
    def _fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        return _completed(
            stdout=(f"4321 1000 bash /bin/bash\n5001 4321 {command_name} {command_name}\n")
        )

    monkeypatch.setattr("subprocess.run", _fake_run)
    inspector = PaneProcessInspector(supported_processes={"kimi": ("kimi-code", "kimi")})

    result = inspector.inspect(tool="kimi", pane_pid=4321)

    assert result.process_state == "tui_up"
    assert result.matched_process_names == (command_name,)


def test_server_and_local_runtime_defaults_include_kimi_process_names() -> None:
    assert HoumaoServerConfig().supported_tui_processes["kimi"] == ("kimi-code", "kimi")
    assert local_interactive_module._SUPPORTED_TUI_PROCESSES["kimi"] == (  # noqa: SLF001
        "kimi-code",
        "kimi",
    )


def test_process_inspector_detects_tui_down_when_no_supported_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        return _completed(stdout="4321 1000 bash /bin/bash\n5000 4321 python python helper.py\n")

    monkeypatch.setattr("subprocess.run", _fake_run)
    inspector = PaneProcessInspector(supported_processes={"codex": ("codex",)})

    result = inspector.inspect(tool="codex", pane_pid=4321)

    assert result.process_state == "tui_down"
    assert result.matched_process_names == ()


def test_process_inspector_reports_probe_error_for_missing_pane_pid() -> None:
    inspector = PaneProcessInspector(supported_processes={"codex": ("codex",)})

    result = inspector.inspect(tool="codex", pane_pid=None)

    assert result.process_state == "probe_error"
    assert "pane_pid" in (result.error_message or "")


def test_process_inspector_reports_unsupported_tool() -> None:
    inspector = PaneProcessInspector(supported_processes={"codex": ("codex",)})

    result = inspector.inspect(tool="claude", pane_pid=4321)

    assert result.process_state == "unsupported_tool"
