"""Recover DSH interruption authority through exact private native and driver bindings."""

from __future__ import annotations

from dataclasses import replace
import fcntl
import json
from pathlib import Path
import signal
from unittest.mock import Mock

import pytest

import houmao.agents.realm_controller.backends.dsh_acp as dsh_module
import houmao.agents.realm_controller.backends.headless_runner as runner_module
from houmao.agents.realm_controller.backends.dsh_acp import DshAcpSession
from houmao.agents.realm_controller.backends.headless_base import HeadlessSessionState
from houmao.agents.realm_controller.backends.headless_runner import HeadlessCliRunner
from tests.unit.agents.realm_controller.test_gateway_support import _sample_headless_plan


def _bound_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[DshAcpSession, Path, Mock]:
    """Create exact on-disk authority while substituting every process and tmux operation."""

    home = tmp_path / "private-home"
    home.mkdir()
    manifest = tmp_path / "runtime/manifest.json"
    manifest.parent.mkdir()
    manifest.write_text(
        json.dumps(
            {
                "tool": "dsh",
                "backend": "dsh_acp",
                "working_directory": str(tmp_path.resolve()),
                "runtime": {"session_id": "runtime-one"},
                "registry_generation_id": "generation-one",
                "backend_state": {"session_id": "native-one", "turn_index": 3},
            }
        )
    )
    turn = manifest.parent / "manifest.turn-artifacts/exact-attempt"
    turn.mkdir(parents=True)
    binding = {
        "version": 1,
        "attempt_id": turn.name,
        "runtime_session_id": "runtime-one",
        "generation": "generation-one",
        "native_session_id": "native-one",
        "working_directory": str(tmp_path.resolve()),
        "evidence_path": str(turn / "dsh-native-evidence.jsonl"),
        "process_id": 10101,
        "process_birth_token": "native-birth",
    }
    (turn / "dsh-native-binding.json").write_text(json.dumps(binding))
    (home / "houmao-native-session.json").write_text(json.dumps(binding))
    (turn / "process.json").write_text(
        json.dumps(
            {
                "runner_pid": 30303,
                "runner_birth_token": "bridge-birth",
                "child_pid": 20202,
                "child_birth_token": "driver-birth",
            }
        )
    )
    session = object.__new__(DshAcpSession)
    session._plan = replace(
        _sample_headless_plan(tmp_path), backend="dsh_acp", tool="dsh", home_path=home
    )
    session._session_manifest_path = manifest
    session._turn_artifacts_root = turn.parent
    session._state = HeadlessSessionState(
        working_directory=str(tmp_path),
        session_id="native-one",
        turn_index=1,
        tmux_session_name="owned-envelope",
    )
    session._runner = HeadlessCliRunner()
    session._force_cleanup_on_terminate = False
    births = {10101: "native-birth", 20202: "driver-birth"}
    monkeypatch.setattr(dsh_module, "_dispatch_origin_birth_token", births.get)
    monkeypatch.setattr(runner_module, "_dispatch_origin_birth_token", births.get)
    monkeypatch.setattr(dsh_module.os, "getpgid", lambda pid: pid)
    signal_pid = Mock(return_value=True)
    monkeypatch.setattr(runner_module, "_signal_pid", signal_pid)
    monkeypatch.setattr(runner_module, "signal_dsh_native_process", Mock(return_value=True))
    monkeypatch.setattr(
        runner_module,
        "run_tmux_shared",
        Mock(side_effect=AssertionError("No terminal fallback is allowed")),
    )
    return session, turn, signal_pid


@pytest.mark.parametrize(
    "operation,expected_signal", [("interrupt", signal.SIGTERM), ("terminate", signal.SIGKILL)]
)
def test_independent_controller_restores_only_its_exact_owned_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str, expected_signal: int
) -> None:
    """A newly reconstructed runner can control the bound live driver without launching work."""

    session, turn, signal_pid = _bound_session(tmp_path, monkeypatch)
    with (session._plan.home_path / "houmao-invocation.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = getattr(session, operation)()
    assert result.status == "ok"
    signal_pid.assert_called_once_with(20202, expected_signal)
    assert session._runner.m_active_turn_dir == turn
    assert session._runner._active_tmux_pane_target is None
    assert session._state.session_id == "native-one"
    assert session._state.turn_index == 3
    assert (turn / "usage-interrupt.json").is_file()


@pytest.mark.parametrize("operation", ["interrupt", "terminate"])
@pytest.mark.parametrize(
    "mismatch",
    [
        "generation",
        "runtime_session_id",
        "native_session_id",
        "working_directory",
        "attempt_id",
        "native_birth",
        "driver_birth",
        "terminal",
        "missing_binding",
    ],
)
def test_resumed_control_refuses_mismatched_or_unavailable_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str, mismatch: str
) -> None:
    """Stale sidecars, replaced processes, and unknown startup cannot authorize a signal."""

    session, turn, signal_pid = _bound_session(tmp_path, monkeypatch)
    home_binding = session._plan.home_path / "houmao-native-session.json"
    binding = json.loads(home_binding.read_text())
    if mismatch in {"generation", "runtime_session_id", "native_session_id", "working_directory"}:
        binding[mismatch] = "mismatched"
        home_binding.write_text(json.dumps(binding))
    elif mismatch == "attempt_id":
        binding["attempt_id"] = "../outside"
        home_binding.write_text(json.dumps(binding))
    elif mismatch == "native_birth":
        monkeypatch.setattr(
            dsh_module, "_dispatch_origin_birth_token", lambda _pid: "reused-native"
        )
    elif mismatch == "driver_birth":
        monkeypatch.setattr(
            runner_module, "_dispatch_origin_birth_token", lambda _pid: "reused-driver"
        )
    elif mismatch == "terminal":
        (turn / "exitcode").write_text("0\n")
    else:
        home_binding.unlink()
    with (session._plan.home_path / "houmao-invocation.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = getattr(session, operation)()
    assert result.status == "error"
    signal_pid.assert_not_called()
    assert not (turn / "usage-interrupt.json").exists()


def test_surviving_native_body_without_a_live_driver_is_not_reported_idle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A released controller lock cannot hide a native worker whose birth still matches."""

    session, _turn, signal_pid = _bound_session(tmp_path, monkeypatch)
    monkeypatch.setattr(runner_module, "_dispatch_origin_birth_token", lambda _pid: None)
    result = session.terminate()
    assert result.status == "error"
    signal_pid.assert_not_called()
