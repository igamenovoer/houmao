"""Exercise one-shot bridge closure and exact captured-process interruption."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from textwrap import dedent
from time import monotonic, sleep

import pytest

from houmao.agents.realm_controller.backends import headless_runner
from houmao.agents.realm_controller.backends.dispatch_control import (
    HeadlessDispatchControl,
    _dispatch_origin_birth_token,
)
from houmao.agents.realm_controller.backends.headless_runner import (
    HeadlessCliRunner,
    HeadlessTurnWaitTimeout,
    interrupt_owned_headless_attempt,
)


def _bridge(tmp_path: Path, worker: str) -> tuple[subprocess.Popen[str], Path]:
    """Launch a real private bridge using a fixture process in place of DSH."""

    env = tmp_path / "env.json"
    env.write_text("{}\n", encoding="utf-8")
    turn = tmp_path / "turn"
    command = [
        sys.executable,
        "-m",
        "houmao.agents.realm_controller.backends.headless_bridge",
        "--provider",
        "dsh",
        "--output-format",
        "dsh-cli",
        "--turn-index",
        "1",
        "--turn-dir",
        str(turn),
        "--cwd",
        str(tmp_path),
        "--launched-at-utc",
        "2026-11-19T00:00:00Z",
        "--env-file",
        str(env),
        "--",
        sys.executable,
        "-c",
        worker,
    ]
    return subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    ), turn


@pytest.mark.skipif(sys.platform != "linux", reason="Exact process pins use Linux pidfd")
def test_dsh_worker_interruption_escalates_and_reaps_the_owned_process_group(
    tmp_path: Path,
) -> None:
    """A stale attempt cannot signal a replacement and closure reaps the captured tree."""

    worker = dedent("""\
        import json, pathlib, signal, subprocess, sys, time
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        child = subprocess.Popen(
            [sys.executable, '-c', 'import time; time.sleep(120)'], start_new_session=True,
        )
        pathlib.Path('worker.json').write_text(json.dumps({'child': child.pid}))
        print('{"type":"session","sessionId":"session-fixture"}', flush=True)
        time.sleep(120)
    """)
    bridge, turn = _bridge(tmp_path, worker)
    try:
        marker = tmp_path / "worker.json"
        deadline = monotonic() + 5
        while not marker.is_file() or not (turn / "process.json").is_file():
            if monotonic() >= deadline:
                raise AssertionError("The isolated worker did not start")
            sleep(0.02)
        child_pid = json.loads(marker.read_text())["child"]
        metadata = json.loads((turn / "process.json").read_text())
        assert metadata["child_isolated_group"] is True
        stale = tmp_path / "stale-turn"
        stale.mkdir()
        (stale / "process.json").write_text(json.dumps({**metadata, "child_birth_token": "proc:0"}))
        assert interrupt_owned_headless_attempt(stale).status == "error"
        assert _dispatch_origin_birth_token(metadata["child_pid"]) == metadata["child_birth_token"]
        assert _dispatch_origin_birth_token(child_pid) is not None
        assert os.getsid(child_pid) == child_pid
        assert interrupt_owned_headless_attempt(turn).status == "ok"
        bridge.communicate(timeout=5)
        assert bridge.returncode == 130
        assert (turn / "exitcode").read_text().strip() == "130"
        assert '"type":"session"' in (turn / "stdout.jsonl").read_text()
        closure = json.loads((turn / "dsh-native-closure.json").read_text())
        assert closure["source"] == "owner_process"
        deadline = monotonic() + 2
        while _dispatch_origin_birth_token(child_pid) is not None and monotonic() < deadline:
            sleep(0.02)
        assert _dispatch_origin_birth_token(child_pid) is None
    finally:
        if bridge.poll() is None:
            interrupt_owned_headless_attempt(turn)
            bridge.terminate()
            bridge.communicate(timeout=5)


def test_dsh_partial_stream_cannot_publish_success(tmp_path: Path) -> None:
    """Retain an unterminated native row and refuse settlement even after nominal exit zero."""

    output = '{"type":"session","sessionId":"session-fixture"}\n{"type":"final"'
    bridge, turn = _bridge(tmp_path, f"print({output!r}, end='')")
    bridge.communicate(timeout=5)
    assert bridge.returncode == 1
    assert (turn / "stdout.jsonl").read_text() == output
    assert (turn / "stdout.jsonl").stat().st_mode & 0o077 == 0
    assert (turn / "exitcode").read_text().strip() == "1"
    assert not (turn / "dsh-native-closure.json").exists()


def test_dsh_wait_timeout_preserves_the_confirmed_owned_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A controller wait timeout leaves the confirmed worker and its slot pending."""

    turn = tmp_path / "attempt"
    pid = os.getpid()
    birth = _dispatch_origin_birth_token(pid)
    assert birth is not None
    handoffs: list[bool] = []
    runner = HeadlessCliRunner()
    dispatch = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: True,
        confirmed=lambda: handoffs.append(True),
        deadline=monotonic() + 5,
    )
    runner.set_dispatch_control(dispatch)

    def spawn(args: list[str]) -> subprocess.CompletedProcess[str]:
        """Leave the runner a verified, admitted test attempt without an exit marker."""

        assert args[:1] == ["respawn-pane"]
        (turn / "process.json").write_text(
            json.dumps(
                {
                    "child_pid": pid,
                    "child_birth_token": birth,
                    "child_isolated_group": True,
                }
            )
        )
        (turn / "dsh-native-handoff.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "attempt_id": turn.name,
                    "native_session_id": "session-fixture",
                    "process_id": pid,
                    "process_birth_token": birth,
                }
            )
        )
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(headless_runner, "run_tmux_shared", spawn)
    monkeypatch.setattr(headless_runner, "wait_for_tmux_signal_shared", lambda **_: None)
    with pytest.raises(HeadlessTurnWaitTimeout):
        runner.run(
            command=["unused-test-worker"],
            env={},
            cwd=tmp_path,
            turn_index=1,
            output_format="dsh-cli",
            provider="dsh",
            tmux_session_name="fixture-only",
            tmux_pane_target="%fixture",
            turn_artifacts_root=tmp_path,
            turn_artifact_dir_name=turn.name,
            completion_timeout_seconds=0,
        )
    assert handoffs == [True]
    assert runner.active_process_running
    assert not (turn / "exitcode").exists()
    assert not (turn / "usage-final.json").exists()
    assert json.loads((turn / ".dispatch-permission.json").read_text())["active"] is True
