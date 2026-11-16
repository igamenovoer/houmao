"""Audit DSH ownership, timeout, and cleanup without using a tmux server."""

from __future__ import annotations

from dataclasses import replace
import fcntl
import io
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import houmao.agents.realm_controller.backends.dsh_acp_connection as connection_module
import houmao.agents.realm_controller.backends.headless_runner as runner_module
from houmao.agents.realm_controller.backends.dispatch_control import HeadlessDispatchControl
from houmao.agents.realm_controller.backends.dsh_acp import DshAcpSession
from houmao.agents.realm_controller.backends.dsh_acp_connection import (
    DshAcpConnection,
    DshAcpProtocolError,
    signal_dsh_native_process,
)
from houmao.agents.realm_controller.backends.dsh_acp_driver import (
    DshAcpInvocation,
    run_dsh_acp_turn,
)
from houmao.agents.realm_controller.backends.headless_base import (
    HeadlessInteractiveSession,
    HeadlessSessionState,
)
from houmao.agents.realm_controller.backends.headless_bridge import main as run_headless_bridge
from houmao.agents.realm_controller.backends.headless_runner import (
    HeadlessCliRunner,
    HeadlessProcessMetadata,
    HeadlessTurnWaitTimeout,
)
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.models import HeadlessTurnSessionSelection
from tests.unit.agents.realm_controller.test_dsh_usage_adapter import _managed_service
from tests.unit.agents.realm_controller.test_dsh_acp_driver import _invocation
from tests.unit.agents.realm_controller.test_gateway_support import _sample_headless_plan


@pytest.mark.parametrize("escape_group", [False, True])
def test_connection_reaps_captured_descendants_after_native_leader_exit(
    tmp_path: Path, escape_group: bool
) -> None:
    """Retained stdout/stderr pipes cannot make cleanup wait forever after root exit."""

    script = "\n".join(
        [
            "import json, subprocess, sys",
            f"child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session={escape_group!r})",
            "print(json.dumps({'jsonrpc':'2.0', 'method':'owned-child', 'params':{'pid':child.pid}}), flush=True)",
            "sys.stdin.read()",
        ]
    )
    connection = DshAcpConnection.from_command(
        [sys.executable, "-u", "-c", script],
        cwd=tmp_path,
        env={"PATH": os.environ.get("PATH", "")},
    )
    child_pid: int | None = None
    child_birth: str | None = None
    try:
        notification = connection.next_notification(timeout=3)
        assert notification is not None
        child_pid = notification["params"]["pid"]
        child_birth = connection_module._dispatch_origin_birth_token(child_pid)
        assert child_birth is not None
        recorded_birth = connection.process_birth_token
        started = time.monotonic()
        connection.close(timeout=0.2)
        assert time.monotonic() - started < 3
        assert connection.process.returncode == 0
        assert connection.process_birth_token == recorded_birth
        deadline = time.monotonic() + 2
        while connection_module._dispatch_origin_birth_token(child_pid) == child_birth:
            if time.monotonic() >= deadline:
                pytest.fail("An exactly captured native child survived connection cleanup")
            time.sleep(0.01)
    finally:
        # Every signal is fenced against the exact private subprocess created
        # above. No executable-name lookup or tmux server is involved.
        if (
            connection_module._dispatch_origin_birth_token(connection.process.pid)
            == connection.process_birth_token
        ):
            connection._signal_owned_group(signal.SIGKILL)
        if (
            child_pid is not None
            and child_birth is not None
            and connection_module._dispatch_origin_birth_token(child_pid) == child_birth
        ):
            os.kill(child_pid, signal.SIGKILL)
        connection.process.wait(timeout=3)


def test_broken_stdin_close_cannot_skip_native_reaping(tmp_path: Path) -> None:
    """A provider that closed input already still receives bounded transport cleanup."""

    connection = DshAcpConnection()
    process = SimpleNamespace(
        pid=12345,
        stdin=SimpleNamespace(close=Mock(side_effect=BrokenPipeError())),
        stdout=io.StringIO(),
        stderr=io.StringIO(),
        wait=Mock(return_value=0),
    )
    connection.m_process = process
    connection._capture_owned_processes = Mock()
    connection._signal_owned_group = Mock(return_value=False)
    connection.close(timeout=0.1)
    process.wait.assert_called_once_with(timeout=0.1)
    assert process.stdout.closed and process.stderr.closed


def test_unsettled_reader_cleanup_is_explicit_without_blocking_stream_close() -> None:
    """A pipe whose ownership cannot be reconciled produces bounded cleanup failure."""

    connection = DshAcpConnection()
    stdout = SimpleNamespace(
        close=Mock(side_effect=AssertionError("A live reader may hold the stream lock"))
    )
    connection.m_process = SimpleNamespace(
        pid=12345,
        stdin=io.StringIO(),
        stdout=stdout,
        stderr=None,
        wait=Mock(return_value=0),
    )
    reader = SimpleNamespace(join=Mock(), is_alive=lambda: True)
    connection.m_reader = reader
    connection._capture_owned_processes = Mock()
    connection._signal_owned_group = Mock(return_value=False)
    with pytest.raises(DshAcpProtocolError, match="stream cleanup did not settle"):
        connection.close(timeout=0.01)
    reader.join.assert_called_once_with(timeout=0.01)
    stdout.close.assert_not_called()


def test_replaced_leader_birth_never_authorizes_group_signals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even retained private connection state cannot signal a reused process-group leader."""

    connection = DshAcpConnection()
    connection.m_process = SimpleNamespace(pid=12345)
    connection.m_process_birth_token = "proc:original"
    connection.m_owned_processes = {12345: "proc:original"}
    monkeypatch.setattr(
        connection_module,
        "_read_process_lineage",
        lambda _pid: (1, 12345, 12345, "proc:replacement"),
    )
    monkeypatch.setattr(
        connection_module, "_dispatch_origin_birth_token", lambda _pid: "proc:replacement"
    )
    group_signal = Mock()
    process_signal = Mock()
    monkeypatch.setattr(connection_module.os, "killpg", group_signal)
    monkeypatch.setattr(connection_module.os, "kill", process_signal)
    assert connection._signal_owned_group(signal.SIGKILL) is False
    group_signal.assert_not_called()
    process_signal.assert_not_called()


@pytest.mark.parametrize(
    "birth,group,expected", [("other", 12345, False), ("owned", 9, False), ("owned", 12345, True)]
)
def test_external_native_cleanup_requires_both_birth_and_group_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, birth: str, group: int, expected: bool
) -> None:
    """An artifact alone is never permission to signal a replacement or unrelated group."""

    (tmp_path / "dsh-native-binding.json").write_text(
        json.dumps({"process_id": 12345, "process_birth_token": "owned"})
    )
    monkeypatch.setattr(connection_module, "_dispatch_origin_birth_token", lambda _pid: birth)
    monkeypatch.setattr(connection_module.os, "getpgid", lambda _pid: group)
    signal_group = Mock()
    monkeypatch.setattr(connection_module.os, "killpg", signal_group)
    assert signal_dsh_native_process(tmp_path, signal.SIGKILL) is expected
    if expected:
        signal_group.assert_called_once_with(12345, signal.SIGKILL)
    else:
        signal_group.assert_not_called()


def test_occupied_native_interval_never_starts_another_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second independently resumed controller cannot overlap the native owner."""

    invocation = DshAcpInvocation(
        command=(),
        working_directory=tmp_path,
        environment={},
        prompt="synthetic input",
        session_id="exact-native",
        attempt_id="second",
        runtime_session_id="runtime",
        generation="generation",
        turn_dir=tmp_path / "second",
        lock_path=tmp_path / "invocation.lock",
        evidence_path=tmp_path / "second/evidence.jsonl",
    )
    start = Mock(side_effect=AssertionError("An occupied session cannot launch a replacement"))
    monkeypatch.setattr(DshAcpConnection, "from_command", start)
    with invocation.lock_path.open("a") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(DshAcpProtocolError, match="active invocation"):
            run_dsh_acp_turn(
                invocation,
                emit=lambda _event: None,
                interrupted=threading.Event(),
                confirmed=lambda: pytest.fail("No admission"),
            )
    start.assert_not_called()
    assert not invocation.evidence_path.exists()


def test_hung_native_cancellation_preserves_failure_and_reaps_the_worker(tmp_path: Path) -> None:
    """A secondary close timeout cannot hide the original native cancellation failure."""

    invocation = _invocation(tmp_path)
    original = invocation.command[-1]
    script = original.replace(
        "reason = 'cancelled'",
        "__import__('time').sleep(60)\n            reason = 'cancelled'",
    )
    assert script != original
    invocation = replace(
        invocation,
        command=(*invocation.command[:-1], script),
        cancellation_timeout=0.03,
        close_timeout=0.05,
    )
    invocation.environment["FAKE_WAIT_FOR_CANCEL"] = "1"
    interrupted = threading.Event()

    def observe(event: dict[str, object]) -> None:
        """Request cancellation only after this native attempt has emitted output."""

        if event["type"] == "session_update":
            interrupted.set()

    with pytest.raises(DshAcpProtocolError, match="native cancellation did not settle"):
        run_dsh_acp_turn(invocation, emit=observe, interrupted=interrupted, confirmed=lambda: None)
    binding = json.loads((invocation.turn_dir / "dsh-native-binding.json").read_text())
    assert connection_module._dispatch_origin_birth_token(binding["process_id"]) is None


def test_wrong_workspace_refuses_before_any_tmux_or_native_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preserved native identity cannot be silently reinterpreted in another workspace."""

    plan = replace(_sample_headless_plan(tmp_path), backend="dsh_acp", tool="dsh")
    plan.home_path.mkdir()
    binding = plan.home_path / "houmao-native-session.json"
    binding.write_text(
        json.dumps(
            {
                "native_session_id": "exact-native",
                "working_directory": str(tmp_path / "different-workspace"),
            }
        )
    )
    original = binding.read_bytes()
    initialize = Mock(side_effect=AssertionError("No terminal or native activation is allowed"))
    monkeypatch.setattr(HeadlessInteractiveSession, "__init__", initialize)
    with pytest.raises(BackendExecutionError, match="recorded workspace"):
        DshAcpSession(
            launch_plan=plan, role_name="role", session_manifest_path=tmp_path / "manifest.json"
        )
    assert binding.read_bytes() == original
    initialize.assert_not_called()


def test_latest_session_selection_cannot_fall_back_to_a_new_conversation(tmp_path: Path) -> None:
    """Unsupported selection fails before reading a manifest or creating native input."""

    session = object.__new__(DshAcpSession)
    session.m_turn_dir = tmp_path / "attempt"
    with pytest.raises(BackendExecutionError, match="latest-session selection is unsupported"):
        session._build_command(
            prompt="synthetic",
            session_selection=HeadlessTurnSessionSelection(mode="tool_last_or_new"),
        )
    assert not session.m_turn_dir.exists()


@pytest.mark.parametrize(
    ("process_running", "concurrent_exitcode"),
    [(False, None), (True, None), (False, 0)],
    ids=["unconfirmed-startup", "known-active", "concurrent-success-marker"],
)
def test_controller_timeout_requires_terminal_proof_before_usage_finalization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    process_running: bool,
    concurrent_exitcode: int | None,
) -> None:
    """A wait timeout is not a terminal native result or authority to replay input."""

    service, manifest, home = _managed_service(tmp_path)
    session = object.__new__(DshAcpSession)
    session.backend = "dsh_acp"
    session._plan = replace(
        _sample_headless_plan(tmp_path), backend="dsh_acp", tool="dsh", home_path=home
    )
    session._session_manifest_path = manifest
    session._turn_artifacts_root = manifest.parent / "manifest.turn-artifacts"
    session._state = HeadlessSessionState(working_directory=str(tmp_path))
    session._runner = SimpleNamespace(active_process_running=process_running)

    def stop_wait(*_args: object, **_kwargs: object) -> None:
        """Race the wait expiry with an independently published native completion."""

        if concurrent_exitcode is not None:
            (session._turn_artifacts_root / "pending-attempt/exitcode").write_text(
                f"{concurrent_exitcode}\n", encoding="utf-8"
            )
        raise HeadlessTurnWaitTimeout("controller stopped waiting")

    session._execute_prompt = Mock(side_effect=stop_wait)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.UsageService.from_launch",
        lambda *_args: service,
    )
    with pytest.raises(HeadlessTurnWaitTimeout):
        session.send_prompt("synthetic", turn_artifact_dir_name="pending-attempt")
    pending = service.store.get_pending_turn("pending-attempt")
    assert pending is not None and pending.finalization is None
    assert service.get_usage().records == []
    assert not (session._turn_artifacts_root / "pending-attempt/usage-final.json").exists()
    if concurrent_exitcode is not None:
        service.reconcile()
        records = service.get_usage().records
        assert len(records) == 1
        assert records[0].outcome == "completed"
        assert service.store.get_pending_turn("pending-attempt").finalization.returncode == 0


@pytest.mark.parametrize("guarded", [False, True])
def test_runner_timeout_keeps_original_owned_identity_without_cancelling_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, guarded: bool
) -> None:
    """A live native body survives controller wait expiry with recoverable process metadata."""

    runner = HeadlessCliRunner()
    artifacts = tmp_path / "artifacts"
    turn_dir = artifacts / "attempt"
    metadata = HeadlessProcessMetadata(child_pid=12345, child_birth_token="original-birth")
    if guarded:
        control = HeadlessDispatchControl.from_callbacks(
            allowed=lambda: True, confirmed=lambda: None, deadline=time.monotonic() + 30
        )
        runner.set_dispatch_control(control)

    def launch(_args: list[str]) -> SimpleNamespace:
        """Publish controlled native handoff evidence without invoking tmux or a process."""

        (turn_dir / "dsh-native-handoff.json").write_text(
            json.dumps({"version": 1, "attempt_id": "attempt", "native_session_id": "exact-native"})
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner_module, "run_tmux_shared", launch)
    monkeypatch.setattr(runner_module, "wait_for_tmux_signal_shared", lambda **_kwargs: None)
    monkeypatch.setattr(runner_module, "headless_artifact_process_alive", lambda _path: True)
    monkeypatch.setattr(runner, "_wait_for_process_metadata", lambda **_kwargs: metadata)
    with pytest.raises(HeadlessTurnWaitTimeout):
        runner.run(
            command=["must-not-execute"],
            env={},
            cwd=tmp_path,
            turn_index=1,
            output_format="stream-json",
            provider="dsh",
            tmux_session_name="controlled-only",
            tmux_pane_target="%owned",
            turn_artifacts_root=artifacts,
            turn_artifact_dir_name="attempt",
            completion_timeout_seconds=0,
        )
    assert runner.active_process_running is True
    assert runner._active_process_metadata == metadata
    assert runner._active_tmux_pane_target == "%owned"
    assert not (turn_dir / "exitcode").exists()
    if guarded:
        assert control.m_handoff_confirmed.is_set()
        assert not control.m_cancelled.is_set()


@pytest.mark.parametrize("operation", ["interrupt", "terminate"])
def test_unavailable_dsh_process_identity_never_falls_back_to_terminal_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    """A replacement supervisory pane is not a substitute for the captured native body."""

    runner = HeadlessCliRunner()
    runner.m_active_provider = "dsh"
    runner.m_active_turn_dir = tmp_path
    runner._active_tmux_pane_target = "%replacement"
    runner._active_process_metadata = HeadlessProcessMetadata(
        child_pid=12345, child_birth_token="old-birth"
    )
    keys = Mock(side_effect=AssertionError("Never target a replacement terminal"))
    signal_pid = Mock(side_effect=AssertionError("Never signal a replacement process"))
    monkeypatch.setattr(runner_module, "run_tmux_shared", keys)
    monkeypatch.setattr(runner_module, "_signal_pid", signal_pid)
    monkeypatch.setattr(
        runner_module, "_dispatch_origin_birth_token", lambda _pid: "replacement-birth"
    )
    getattr(runner, operation)()
    keys.assert_not_called()
    signal_pid.assert_not_called()


def test_native_cancelled_bridge_outcome_is_interrupted_without_operator_flag(
    tmp_path: Path,
) -> None:
    """Preserve a native cancelled result as interrupted through real subprocess capture and ledger finalization."""

    service, manifest, _ = _managed_service(tmp_path)
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "native-cancelled"
    service.begin_headless_turn(
        turn_id="native-cancelled", turn_dir=turn_dir, turn_index=1, new_session=True
    )
    environment = tmp_path / "synthetic-driver-env.json"
    environment.write_text("{}")
    script = "import json,sys; print(json.dumps({'type':'native_result','session_id':'cancelled-native','stop_reason':'cancelled'})); sys.exit(130)"
    result = run_headless_bridge(
        [
            "--provider",
            "dsh",
            "--output-format",
            "stream-json",
            "--turn-index",
            "1",
            "--turn-dir",
            str(turn_dir),
            "--cwd",
            str(tmp_path),
            "--launched-at-utc",
            "2026-11-16T00:00:00+00:00",
            "--env-file",
            str(environment),
            "--",
            sys.executable,
            "-c",
            script,
        ]
    )
    assert result == 130
    assert not (turn_dir / "usage-interrupt.json").exists()
    terminal = json.loads((turn_dir / "usage-final.json").read_text())
    assert terminal["outcome"] == "interrupted"
    assert terminal["interrupted"] is True
    assert terminal["returncode"] == 130
    record = service.finalize_headless_turn(turn_dir)
    assert record is not None and record.outcome == "interrupted"
