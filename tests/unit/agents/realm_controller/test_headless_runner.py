from __future__ import annotations

import os
import json
from pathlib import Path
import subprocess

import pytest

import houmao.agents.realm_controller.backends.headless_runner as headless_runner_module
from houmao.agents.realm_controller.backends.headless_runner import (
    HeadlessCliRunner,
)


def _write_idle_shell(tmp_path: Path) -> Path:
    idle_shell = tmp_path / "idle-shell.sh"
    idle_shell.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    idle_shell.chmod(0o755)
    return idle_shell


def _tmux_wait_timeout() -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["tmux", "wait-for"],
        returncode=1,
        stdout="",
        stderr="timed out",
    )


def test_headless_runner_parses_stream_json_and_session_id(tmp_path: Path) -> None:
    script = tmp_path / "emit_stream.sh"
    script.write_text(
        "#!/usr/bin/env bash\n"
        'echo \'{"type":"delta","text":"hello"}\'\n'
        'echo \'{"type":"final","session_id":"sess-123","text":"done"}\'\n',
        encoding="utf-8",
    )
    script.chmod(0o755)

    runner = HeadlessCliRunner()
    result = runner.run(
        command=[str(script)],
        env={},
        cwd=tmp_path,
        turn_index=1,
        output_format="stream-json",
    )

    assert result.returncode == 0
    assert result.session_id == "sess-123"
    assert [event.kind for event in result.events] == ["delta", "final"]


def test_headless_runner_parses_json_payload(tmp_path: Path) -> None:
    script = tmp_path / "emit_json.sh"
    script.write_text(
        '#!/usr/bin/env bash\necho \'{"type":"result","session_id":"sess-999","text":"ok"}\'\n',
        encoding="utf-8",
    )
    script.chmod(0o755)

    runner = HeadlessCliRunner()
    result = runner.run(
        command=[str(script)],
        env={},
        cwd=tmp_path,
        turn_index=1,
        output_format="json",
    )

    assert result.returncode == 0
    assert result.session_id == "sess-999"
    assert len(result.events) == 1
    assert result.events[0].message == "ok"


def test_headless_runner_extracts_codex_thread_id_from_stream_json(
    tmp_path: Path,
) -> None:
    script = tmp_path / "emit_codex_jsonl.sh"
    script.write_text(
        "#!/usr/bin/env bash\n"
        'echo \'{"type":"thread.started","thread_id":"thread-abc"}\'\n'
        'echo \'{"type":"response.completed","text":"done"}\'\n',
        encoding="utf-8",
    )
    script.chmod(0o755)

    runner = HeadlessCliRunner()
    result = runner.run(
        command=[str(script)],
        env={},
        cwd=tmp_path,
        turn_index=1,
        output_format="stream-json",
    )

    assert result.returncode == 0
    assert result.session_id == "thread-abc"


def test_headless_runner_prefers_first_stream_json_session_id_for_gemini_resume_identity(
    tmp_path: Path,
) -> None:
    script = tmp_path / "emit_gemini_jsonl.sh"
    script.write_text(
        "#!/usr/bin/env bash\n"
        'echo \'{"type":"init","session_id":"sess-init"}\'\n'
        'echo \'{"type":"delta","text":"hello"}\'\n'
        'echo \'{"type":"final","session_id":"sess-final","text":"done"}\'\n',
        encoding="utf-8",
    )
    script.chmod(0o755)

    runner = HeadlessCliRunner()
    result = runner.run(
        command=[str(script)],
        env={},
        cwd=tmp_path,
        turn_index=1,
        output_format="stream-json",
    )

    assert result.returncode == 0
    assert result.session_id == "sess-init"


def test_headless_runner_tmux_persists_process_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    script = tmp_path / "emit_tmux_stream.sh"
    script.write_text(
        '#!/usr/bin/env bash\necho \'{"type":"final","session_id":"sess-tmux","text":"done"}\'\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    idle_shell = _write_idle_shell(tmp_path)
    prepared_sessions: list[str] = []
    tmux_calls: list[list[str]] = []

    def _fake_run_tmux(args: list[str]) -> subprocess.CompletedProcess[str]:
        tmux_calls.append(list(args))
        if args[:1] == ["respawn-pane"]:
            subprocess.Popen(
                ["sh", "-lc", str(args[-1])],
                cwd=tmp_path,
                env={**os.environ, "SHELL": str(idle_shell)},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        raise AssertionError(args)

    monkeypatch.setattr(headless_runner_module, "run_tmux_shared", _fake_run_tmux)
    monkeypatch.setattr(
        headless_runner_module,
        "prepare_headless_agent_window_shared",
        lambda *, session_name: prepared_sessions.append(session_name),
    )
    monkeypatch.setattr(
        headless_runner_module,
        "wait_for_tmux_signal_shared",
        lambda **_kwargs: _tmux_wait_timeout(),
    )

    runner = HeadlessCliRunner()
    result = runner.run(
        command=[str(script)],
        env={},
        cwd=tmp_path,
        turn_index=1,
        output_format="stream-json",
        tmux_session_name="HOUMAO-headless-test",
        turn_artifacts_root=tmp_path / "turn-artifacts",
    )

    assert result.returncode == 0
    assert result.session_id == "sess-tmux"
    assert result.process_path is not None
    assert result.process_path.exists()
    assert result.process_metadata is not None
    assert result.process_metadata.runner_pid is not None
    assert result.process_metadata.child_pid is not None
    persisted = json.loads(result.process_path.read_text(encoding="utf-8"))
    assert persisted["runner_pid"] == result.process_metadata.runner_pid
    assert persisted["child_pid"] == result.process_metadata.child_pid
    assert persisted["launched_at_utc"]
    assert prepared_sessions == ["HOUMAO-headless-test"]
    assert any(
        call[:4] == ["respawn-pane", "-k", "-t", "HOUMAO-headless-test:0.0"] for call in tmux_calls
    )
    assert not any(call[:1] == ["new-window"] for call in tmux_calls)


def test_headless_runner_tmux_mirrors_output_to_console_and_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    script = tmp_path / "emit_tmux_visible_output.sh"
    script.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                'echo \'{"type":"delta","text":"visible-stdout"}\'',
                'echo "visible-stderr" >&2',
                'echo \'{"type":"final","session_id":"sess-visible","text":"done"}\'',
                "",
            ]
        ),
        encoding="utf-8",
    )
    script.chmod(0o755)

    captured: dict[str, str] = {}
    idle_shell = _write_idle_shell(tmp_path)
    prepared_sessions: list[str] = []
    tmux_calls: list[list[str]] = []

    def _fake_run_tmux(args: list[str]) -> subprocess.CompletedProcess[str]:
        tmux_calls.append(list(args))
        if args[:1] == ["respawn-pane"]:
            result = subprocess.run(
                ["sh", "-lc", str(args[-1])],
                cwd=tmp_path,
                env={**os.environ, "SHELL": str(idle_shell)},
                text=True,
                capture_output=True,
                check=False,
            )
            captured["stdout"] = result.stdout
            captured["stderr"] = result.stderr
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        raise AssertionError(args)

    monkeypatch.setattr(headless_runner_module, "run_tmux_shared", _fake_run_tmux)
    monkeypatch.setattr(
        headless_runner_module,
        "prepare_headless_agent_window_shared",
        lambda *, session_name: prepared_sessions.append(session_name),
    )
    monkeypatch.setattr(
        headless_runner_module,
        "wait_for_tmux_signal_shared",
        lambda **_kwargs: _tmux_wait_timeout(),
    )

    runner = HeadlessCliRunner()
    result = runner.run(
        command=[str(script)],
        env={},
        cwd=tmp_path,
        turn_index=1,
        output_format="stream-json",
        tmux_session_name="HOUMAO-headless-visible-output",
        turn_artifacts_root=tmp_path / "turn-artifacts",
    )

    assert result.returncode == 0
    assert result.session_id == "sess-visible"
    assert result.stdout_path is not None
    assert result.stderr_path is not None
    assert "visible-stdout" in result.stdout_path.read_text(encoding="utf-8")
    assert "visible-stderr" in result.stderr_path.read_text(encoding="utf-8")
    assert "visible-stdout" in captured["stdout"]
    assert "visible-stderr" in captured["stderr"]
    assert prepared_sessions == ["HOUMAO-headless-visible-output"]
    assert any(
        call[:4] == ["respawn-pane", "-k", "-t", "HOUMAO-headless-visible-output:0.0"]
        for call in tmux_calls
    )
    assert not any(call[:1] == ["new-window"] for call in tmux_calls)


def test_headless_runner_tmux_reuses_stable_agent_pane_across_turns(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    script = tmp_path / "emit_tmux_stream.sh"
    script.write_text(
        '#!/usr/bin/env bash\necho \'{"type":"final","session_id":"sess-tmux","text":"done"}\'\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    idle_shell = _write_idle_shell(tmp_path)
    prepared_sessions: list[str] = []
    respawn_targets: list[str] = []

    def _fake_run_tmux(args: list[str]) -> subprocess.CompletedProcess[str]:
        if args[:1] == ["respawn-pane"]:
            respawn_targets.append(args[3])
            subprocess.run(
                ["sh", "-lc", str(args[-1])],
                cwd=tmp_path,
                env={**os.environ, "SHELL": str(idle_shell)},
                text=True,
                capture_output=True,
                check=False,
            )
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        raise AssertionError(args)

    monkeypatch.setattr(headless_runner_module, "run_tmux_shared", _fake_run_tmux)
    monkeypatch.setattr(
        headless_runner_module,
        "prepare_headless_agent_window_shared",
        lambda *, session_name: prepared_sessions.append(session_name),
    )
    monkeypatch.setattr(
        headless_runner_module,
        "wait_for_tmux_signal_shared",
        lambda **_kwargs: _tmux_wait_timeout(),
    )

    runner = HeadlessCliRunner()
    for turn_index in (1, 2):
        result = runner.run(
            command=[str(script)],
            env={},
            cwd=tmp_path,
            turn_index=turn_index,
            output_format="stream-json",
            tmux_session_name="HOUMAO-headless-reuse",
            turn_artifacts_root=tmp_path / "turn-artifacts",
        )
        assert result.returncode == 0

    assert respawn_targets == [
        "HOUMAO-headless-reuse:0.0",
        "HOUMAO-headless-reuse:0.0",
    ]
    assert prepared_sessions == [
        "HOUMAO-headless-reuse",
        "HOUMAO-headless-reuse",
    ]


def test_headless_runner_interrupt_fallback_uses_stable_agent_pane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmux_calls: list[list[str]] = []

    def _fake_run_tmux(args: list[str]) -> subprocess.CompletedProcess[str]:
        tmux_calls.append(list(args))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(headless_runner_module, "run_tmux_shared", _fake_run_tmux)

    runner = HeadlessCliRunner()
    runner._active_tmux_pane_target = "HOUMAO-headless-test:0.0"  # type: ignore[attr-defined]

    result = runner.interrupt()

    assert result.status == "ok"
    assert tmux_calls == [["send-keys", "-t", "HOUMAO-headless-test:0.0", "C-c"]]


def test_headless_runner_terminate_fallback_uses_stable_agent_pane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmux_calls: list[list[str]] = []

    def _fake_run_tmux(args: list[str]) -> subprocess.CompletedProcess[str]:
        tmux_calls.append(list(args))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(headless_runner_module, "run_tmux_shared", _fake_run_tmux)

    runner = HeadlessCliRunner()
    runner._active_tmux_pane_target = "HOUMAO-headless-test:0.0"  # type: ignore[attr-defined]

    result = runner.terminate()

    assert result.status == "ok"
    assert tmux_calls == [["send-keys", "-t", "HOUMAO-headless-test:0.0", "C-c"]]
