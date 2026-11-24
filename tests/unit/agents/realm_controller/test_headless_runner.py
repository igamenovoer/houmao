from __future__ import annotations

import os
import json
from pathlib import Path
from types import SimpleNamespace
import signal
import subprocess

import pytest

import houmao.agents.realm_controller.backends.headless_runner as headless_runner_module
from houmao.agents.realm_controller.backends.headless_runner import (
    HeadlessCliRunner,
    interrupt_owned_headless_attempt,
)


def _write_idle_shell(tmp_path: Path) -> Path:
    idle_shell = tmp_path / "idle-shell.sh"
    idle_shell.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    idle_shell.chmod(0o755)
    return idle_shell


@pytest.mark.parametrize("actual_birth", ["expected-birth", "reused-pid-birth"])
def test_owned_interrupt_verifies_birth_after_opening_pidfd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, actual_birth: str
) -> None:
    """A recorded PID is insufficient unless the opened process has the saved start identity."""

    (tmp_path / "process.json").write_text(json.dumps({
        "child_pid": 1234, "child_birth_token": "expected-birth",
    }))
    signals = []
    monkeypatch.setattr(os, "pidfd_open", lambda _pid: os.open(os.devnull, os.O_RDONLY), raising=False)
    monkeypatch.setattr(
        headless_runner_module, "_dispatch_origin_birth_token", lambda _pid: actual_birth
    )
    monkeypatch.setattr(signal, "pidfd_send_signal", lambda _fd, sig: signals.append(sig), raising=False)
    result = interrupt_owned_headless_attempt(tmp_path)
    if actual_birth == "expected-birth":
        assert result.status == "ok"
        assert signals == [signal.SIGTERM]
        assert (tmp_path / "usage-interrupt.json").is_file()
    else:
        assert result.status == "error"
        assert not signals
        assert not (tmp_path / "usage-interrupt.json").exists()


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


@pytest.mark.parametrize(
    ("provider", "raw_line", "expected_kind", "expected_provider_event"),
    (
        (
            "codex",
            (
                '{"type":"item.completed","item":{"id":"collab-1",'
                '"type":"collab_tool_call","tool":"wait","sender_thread_id":"parent",'
                '"receiver_thread_ids":["child"],"prompt":null,"agents_states":'
                '{"child":{"status":"completed","message":null}},"status":"completed"}}'
            ),
            "action_result",
            "item.completed.collab_tool_call",
        ),
        (
            "kimi",
            (
                '{"role":"meta","type":"turn.step.retrying","failed_attempt":1,'
                '"next_attempt":2,"max_attempts":3,"delay_ms":100,'
                '"error_name":"RetryError","error_message":"retry","status_code":429}'
            ),
            "progress",
            "turn.step.retrying",
        ),
    ),
)
def test_headless_runner_preserves_current_provider_raw_records_while_canonicalizing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    provider: str,
    raw_line: str,
    expected_kind: str,
    expected_provider_event: str,
) -> None:
    script = tmp_path / f"emit_{provider}_current_event.sh"
    script.write_text(f"#!/usr/bin/env bash\nprintf '%s\\n' '{raw_line}'\n", encoding="utf-8")
    script.chmod(0o755)
    idle_shell = _write_idle_shell(tmp_path)

    def _fake_run_tmux(args: list[str]) -> subprocess.CompletedProcess[str]:
        if args[:1] == ["respawn-pane"]:
            subprocess.run(
                ["bash", "-lc", str(args[-1])],
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
        "resolve_primary_tmux_surface_shared",
        lambda **_kwargs: SimpleNamespace(pane_id="%7"),
    )
    monkeypatch.setattr(
        headless_runner_module,
        "wait_for_tmux_signal_shared",
        lambda **_kwargs: _tmux_wait_timeout(),
    )

    result = HeadlessCliRunner().run(
        command=[str(script)],
        env={},
        cwd=tmp_path,
        turn_index=1,
        output_format="stream-json",
        provider=provider,  # type: ignore[arg-type]
        tmux_session_name=f"HOUMAO-{provider}-raw-current",
        turn_artifacts_root=tmp_path / "turn-artifacts",
    )

    assert result.returncode == 0
    assert result.stdout_path is not None
    assert result.stdout_path.read_text(encoding="utf-8") == raw_line + "\n"
    assert result.canonical_path is not None
    records = [
        json.loads(line)
        for line in result.canonical_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [record["kind"] for record in records] == [expected_kind]
    assert records[0]["provider_event_type"] == expected_provider_event
    assert records[0]["raw_payload"] == json.loads(raw_line)


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
                ["bash", "-lc", str(args[-1])],
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
        "resolve_primary_tmux_surface_shared",
        lambda *, session_name: (
            (prepared_sessions.append(session_name)) or SimpleNamespace(pane_id="%7")
        ),
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
    assert any(call[:4] == ["respawn-pane", "-k", "-t", "%7"] for call in tmux_calls)
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
                ["bash", "-lc", str(args[-1])],
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
        "resolve_primary_tmux_surface_shared",
        lambda *, session_name: (
            (prepared_sessions.append(session_name)) or SimpleNamespace(pane_id="%7")
        ),
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
    assert any(call[:4] == ["respawn-pane", "-k", "-t", "%7"] for call in tmux_calls)
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
                ["bash", "-lc", str(args[-1])],
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
        "resolve_primary_tmux_surface_shared",
        lambda *, session_name: (
            (prepared_sessions.append(session_name)) or SimpleNamespace(pane_id="%7")
        ),
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
        "%7",
        "%7",
    ]
    assert prepared_sessions == [
        "HOUMAO-headless-reuse",
        "HOUMAO-headless-reuse",
    ]


def test_headless_runner_tmux_bridge_preserves_raw_stdout_and_writes_canonical_events(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    script = tmp_path / "emit_tmux_bridge_stream.sh"
    script.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                'printf "%s" "$FIXTURE_SECRET" > observed-secret.txt',
                (
                    "echo "
                    "'{"
                    '"type":"assistant",'
                    '"session_id":"sess-bridge",'
                    '"message":{"model":"claude","content":[{"type":"text","text":"hello from bridge"}]}'
                    "}'"
                ),
                (
                    "echo "
                    "'{"
                    '"type":"result",'
                    '"session_id":"sess-bridge",'
                    '"subtype":"success",'
                    '"usage":{"input_tokens":3,"output_tokens":5,"total_tokens":8}'
                    "}'"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    script.chmod(0o755)

    captured: dict[str, str] = {}
    idle_shell = _write_idle_shell(tmp_path)

    def _fake_run_tmux(args: list[str]) -> subprocess.CompletedProcess[str]:
        if args[:1] == ["respawn-pane"]:
            assert "synthetic-bridge-secret" not in str(args)
            assert "--env-json" not in str(args)
            files = list((tmp_path / "turn-artifacts").rglob(".provider-env-*.json"))
            assert len(files) == 1 and files[0].stat().st_mode & 0o777 == 0o600
            assert json.loads(files[0].read_text())["FIXTURE_SECRET"] == "synthetic-bridge-secret"
            result = subprocess.run(
                ["bash", "-lc", str(args[-1])],
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
        "resolve_primary_tmux_surface_shared",
        lambda **_kwargs: SimpleNamespace(pane_id="%7"),
    )
    monkeypatch.setattr(
        headless_runner_module,
        "wait_for_tmux_signal_shared",
        lambda **_kwargs: _tmux_wait_timeout(),
    )

    runner = HeadlessCliRunner()
    result = runner.run(
        command=[str(script)],
        env={"FIXTURE_SECRET": "synthetic-bridge-secret"},
        cwd=tmp_path,
        turn_index=1,
        output_format="stream-json",
        provider="claude",
        display_style="plain",
        display_detail="concise",
        tmux_session_name="HOUMAO-headless-bridge",
        turn_artifacts_root=tmp_path / "turn-artifacts",
    )

    assert result.returncode == 0
    assert (tmp_path / "observed-secret.txt").read_text() == "synthetic-bridge-secret"
    assert not list((tmp_path / "turn-artifacts").rglob(".provider-env-*.json"))
    assert result.session_id == "sess-bridge"
    assert result.stdout_path is not None
    assert result.canonical_path is not None
    assert (
        result.stdout_path.read_text(encoding="utf-8")
        .splitlines()[0]
        .startswith('{"type":"assistant"')
    )
    assert '{"type":"assistant"' not in captured["stdout"]
    assert "hello from bridge" in captured["stdout"]
    assert (
        "[complete] success | input_tokens=3, output_tokens=5, total_tokens=8" in captured["stdout"]
    )
    canonical_records = [
        json.loads(line)
        for line in result.canonical_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [record["kind"] for record in canonical_records] == ["assistant", "completion"]


def test_headless_runner_interrupt_fallback_uses_stable_agent_pane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmux_calls: list[list[str]] = []

    def _fake_run_tmux(args: list[str]) -> subprocess.CompletedProcess[str]:
        tmux_calls.append(list(args))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(headless_runner_module, "run_tmux_shared", _fake_run_tmux)

    runner = HeadlessCliRunner()
    runner._active_tmux_pane_target = "%7"  # type: ignore[attr-defined]

    result = runner.interrupt()

    assert result.status == "ok"
    assert tmux_calls == [["send-keys", "-t", "%7", "C-c"]]


def test_headless_runner_terminate_fallback_uses_stable_agent_pane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmux_calls: list[list[str]] = []

    def _fake_run_tmux(args: list[str]) -> subprocess.CompletedProcess[str]:
        tmux_calls.append(list(args))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(headless_runner_module, "run_tmux_shared", _fake_run_tmux)

    runner = HeadlessCliRunner()
    runner._active_tmux_pane_target = "%7"  # type: ignore[attr-defined]

    result = runner.terminate()

    assert result.status == "ok"
    assert tmux_calls == [["send-keys", "-t", "%7", "C-c"]]
