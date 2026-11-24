"""Native launch fencing for unsuccessful immediate plugin event attempts."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from houmao.agents.realm_controller.backends.dispatch_control import (
    HeadlessDispatchControl,
    headless_dispatch_permission_allowed,
)
from houmao.agents.realm_controller.backends import headless_bridge
from houmao.agents.realm_controller.backends import dispatch_control
from houmao.agents.realm_controller.backends import headless_runner
from houmao.agents.realm_controller.backends.headless_runner import (
    HeadlessCliRunner,
    HeadlessProcessMetadata,
)
from houmao.agents.realm_controller.errors import BackendExecutionError


@pytest.mark.parametrize(
    "reason",
    ["cancellation", "expiry", "replacement", "missing_manifest", "dead_origin", "reused_origin"],
)
def test_bridge_never_launches_under_revoked_or_superseded_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reason: str
) -> None:
    """Recheck authorization in the actual bridge, after a delayed tmux handoff."""

    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"registry_generation_id": "one"}), encoding="utf-8")
    control = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: True,
        confirmed=lambda: None,
        deadline=time.monotonic() + 10,
        manifest_path=manifest,
        generation_id="one",
    )
    turn = tmp_path / "turn"
    turn.mkdir()
    guard = control.prepare_bridge_permission(turn)
    assert headless_dispatch_permission_allowed(guard)
    assert guard.stat().st_mode & 0o777 == 0o600
    payload = json.loads(guard.read_text(encoding="utf-8"))
    assert set(payload) == {
        "active",
        "attempt_id",
        "expires_at",
        "manifest_path",
        "registry_generation_id",
        "origin_pid",
        "origin_birth_token",
    }
    assert payload["attempt_id"] == turn.name
    if reason == "cancellation":
        control.cancel()
    elif reason == "expiry":
        payload["expires_at"] = time.time() - 1
        guard.write_text(json.dumps(payload), encoding="utf-8")
    elif reason == "replacement":
        manifest.write_text(json.dumps({"registry_generation_id": "two"}), encoding="utf-8")
    elif reason == "missing_manifest":
        manifest.unlink()
    else:
        monkeypatch.setattr(
            dispatch_control,
            "_dispatch_origin_birth_token",
            lambda _: None if reason == "dead_origin" else "different-process-birth",
        )
    assert not headless_dispatch_permission_allowed(guard)
    environment = tmp_path / "environment.json"
    environment.write_text("{}", encoding="utf-8")

    def forbidden_spawn(*_args: object, **_kwargs: object) -> None:
        """Fail if an unsuccessful request ever reaches the native client."""

        raise AssertionError("A revoked request attempted to spawn its client")

    monkeypatch.setattr(headless_bridge.subprocess, "Popen", forbidden_spawn)
    result = headless_bridge.main(
        [
            "--provider",
            "codex",
            "--output-format",
            "stream-json",
            "--turn-index",
            "1",
            "--turn-dir",
            str(turn),
            "--cwd",
            str(tmp_path),
            "--launched-at-utc",
            "2026-11-13T00:00:00Z",
            "--env-file",
            str(environment),
            "--dispatch-guard-file",
            str(guard),
            "--",
            "never-invoked-client",
        ]
    )
    assert result == 125
    assert not environment.exists()
    assert (turn / "exitcode").read_text(encoding="utf-8") == "125\n"
    assert not (turn / "process.json").exists()


def test_dispatch_grant_rejects_a_real_dead_origin(tmp_path: Path) -> None:
    """A grant ceases to authorize native launch when its source process exits."""

    origin = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        token = dispatch_control._dispatch_origin_birth_token(origin.pid)
        assert token is not None
        control = HeadlessDispatchControl.from_callbacks(
            allowed=lambda: True, confirmed=lambda: None, deadline=time.monotonic() + 10
        )
        control.m_origin_pid = origin.pid
        control.m_origin_birth_token = token
        grant = control.prepare_bridge_permission(tmp_path)
        assert headless_dispatch_permission_allowed(grant)
        origin.terminate()
        origin.wait(timeout=5)
        assert not headless_dispatch_permission_allowed(grant)
    finally:
        if origin.poll() is None:
            origin.kill()
            origin.wait(timeout=5)


def test_dispatch_origin_fallback_is_stable_and_rejects_missing_process() -> None:
    """The explicit ps fallback supplies a stable token or fails closed."""

    token = dispatch_control._dispatch_origin_ps_birth_token(os.getpid())
    assert token is not None and token.startswith("ps:")
    assert dispatch_control._dispatch_origin_ps_birth_token(os.getpid()) == token
    assert dispatch_control._dispatch_origin_ps_birth_token(2147483647) is None


def _bridge_launch_arguments(tmp_path: Path, guard: Path | None = None) -> list[str]:
    """Prepare one isolated bridge launch with no provider environment values."""

    environment = tmp_path / "environment.json"
    environment.write_text("{}", encoding="utf-8")
    return [
        "--provider",
        "codex",
        "--output-format",
        "stream-json",
        "--turn-index",
        "1",
        "--turn-dir",
        str(tmp_path / "turn"),
        "--cwd",
        str(tmp_path),
        "--launched-at-utc",
        "2026-11-13T00:00:00Z",
        "--env-file",
        str(environment),
        *(["--dispatch-guard-file", str(guard)] if guard else []),
        "--",
        "unused-client",
    ]


def test_bridge_native_spawn_failure_publishes_terminal_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed Popen cannot leave a worker waiting for an absent completion marker."""

    def fail(*_: object, **__: object) -> None:
        """Raise an unsafe native exception whose content must remain private."""

        raise OSError("private-spawn-sentinel")

    monkeypatch.setattr(headless_bridge.subprocess, "Popen", fail)
    assert headless_bridge.main(_bridge_launch_arguments(tmp_path)) == 127
    turn = tmp_path / "turn"
    assert (turn / "exitcode").read_text() == "127\n"
    assert "private-spawn-sentinel" not in (turn / "stderr.log").read_text()
    assert not (turn / "process.json").exists()
    assert not (tmp_path / "environment.json").exists()


@pytest.mark.parametrize("bridge", [False, True])
def test_cancellation_during_popen_reaps_the_unconfirmed_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bridge: bool
) -> None:
    """A cancel arriving during spawn cannot leave an unconfirmed native child alive."""

    control = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: True, confirmed=lambda: None, deadline=time.monotonic() + 10
    )
    turn = tmp_path / "turn"
    turn.mkdir()
    grant = control.prepare_bridge_permission(turn)
    original_spawn = subprocess.Popen
    children: list[subprocess.Popen[str]] = []

    def spawn(*args: object, **kwargs: object) -> subprocess.Popen[str]:
        """Simulate a delayed Popen finishing immediately after caller cancellation."""

        process = original_spawn(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        children.append(process)
        control.cancel()
        return process

    monkeypatch.setattr(headless_runner.subprocess, "Popen", spawn)
    try:
        if bridge:
            assert headless_bridge.main(_bridge_launch_arguments(tmp_path, grant)) == 125
            assert (turn / "exitcode").read_text() == "125\n"
        else:
            runner = HeadlessCliRunner()
            runner.set_dispatch_control(control)
            # Preparing the bridge grant did not revoke the original source.
            with pytest.raises(BackendExecutionError, match="no longer active"):
                runner.run(
                    command=["unused-client"],
                    env={},
                    cwd=tmp_path,
                    turn_index=1,
                    output_format="stream-json",
                )
            assert runner._active_process is None
        assert len(children) == 1
        assert children[0].poll() is not None
        assert children[0].stdout.closed
        assert children[0].stderr.closed
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)


def test_missing_guarded_handoff_does_not_wait_for_turn_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unconfirmed request revokes its fence and releases runner state promptly."""

    runner = HeadlessCliRunner()
    control = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: True, confirmed=lambda: None, deadline=time.monotonic() + 10
    )
    runner.set_dispatch_control(control)
    monkeypatch.setattr(
        headless_runner,
        "run_tmux_shared",
        lambda args: subprocess.CompletedProcess(args, 0, "", ""),
    )
    monkeypatch.setattr(runner, "_wait_for_process_metadata", lambda **_: None)
    monkeypatch.setattr(
        headless_runner,
        "wait_for_tmux_signal_shared",
        lambda **_: pytest.fail("unconfirmed attempt waited for completed turn"),
    )
    with pytest.raises(BackendExecutionError, match="handoff was not confirmed"):
        runner.run(
            command=["unused-client"],
            env={"TEST_ENV": "dummy"},
            cwd=tmp_path,
            turn_index=1,
            output_format="stream-json",
            provider="codex",
            tmux_session_name="owned",
            tmux_pane_target="%1",
            turn_artifacts_root=tmp_path,
            turn_artifact_dir_name="attempt",
        )
    assert runner._active_process_metadata is None
    assert runner._active_tmux_pane_target is None
    assert list((tmp_path / "attempt").glob(".provider-env-*.json")) == []
    assert not headless_dispatch_permission_allowed(
        tmp_path / "attempt" / ".dispatch-permission.json"
    )


@pytest.mark.skipif(not Path("/proc/self/stat").exists(), reason="Zombie observation uses procfs")
def test_tmux_handoff_liveness_rejects_zombie_native_child(tmp_path: Path) -> None:
    """A dead child awaiting bridge reaping cannot confirm a live handoff."""

    child = subprocess.Popen([sys.executable, "-c", "pass"])
    try:
        deadline = time.monotonic() + 5
        state = ""
        while time.monotonic() < deadline:
            state = Path(f"/proc/{child.pid}/stat").read_text().rpartition(")")[2].split()[0]
            if state == "Z":
                break
            time.sleep(0.01)
        assert state == "Z"
        process_path = tmp_path / "process.json"
        process_path.write_text(
            json.dumps({"runner_pid": os.getpid(), "child_pid": child.pid}), encoding="utf-8"
        )
        runner = HeadlessCliRunner()
        runner.m_active_turn_dir = tmp_path
        runner._active_process_path = process_path
        runner._active_process_metadata = HeadlessProcessMetadata(child_pid=child.pid)
        os.kill(child.pid, 0)
        assert runner.active_process_running is False
    finally:
        child.wait(timeout=5)


def test_metadata_only_headless_liveness_remains_available() -> None:
    """In-memory metadata still serves callers without a managed artifact path."""

    runner = HeadlessCliRunner()
    runner._active_process_metadata = HeadlessProcessMetadata(child_pid=os.getpid())
    assert runner.active_process_running is True


def test_direct_runner_rejects_expired_attempt_before_native_spawn(tmp_path: Path) -> None:
    """A caller deadline is enforced even without a separate tmux bridge."""

    runner = HeadlessCliRunner()
    runner.set_dispatch_control(
        HeadlessDispatchControl.from_callbacks(
            allowed=lambda: True,
            confirmed=lambda: None,
            deadline=time.monotonic() - 1,
        )
    )
    with pytest.raises(BackendExecutionError, match="no longer active"):
        runner.run(
            command=["never-invoked-client"],
            env={},
            cwd=tmp_path,
            turn_index=1,
            output_format="stream-json",
        )


def test_handoff_confirmation_remains_valid_after_sender_response() -> None:
    """Finishing a long successful turn does not require a fresh sender lease."""

    active = True
    confirmations: list[bool] = []
    control = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: active,
        confirmed=lambda: confirmations.append(True),
        deadline=time.monotonic() + 10,
    )
    control.confirm_handoff()
    active = False
    control.confirm_handoff()
    assert confirmations == [True]
    with pytest.raises(BackendExecutionError):
        control.require_allowed()


def test_handoff_confirmation_requires_durable_callback() -> None:
    """A failed evidence write cannot set the confirmed handoff flag."""

    def persist() -> None:
        """Simulate unavailable owner admission storage."""

        raise BackendExecutionError("evidence store unavailable")

    control = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: True, confirmed=persist, deadline=time.monotonic() + 10
    )
    with pytest.raises(BackendExecutionError, match="evidence store unavailable"):
        control.confirm_handoff()
    assert not control.m_handoff_confirmed.is_set()


def test_tui_confirms_after_managed_prompt_enter(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bootstrap submission cannot confirm the requested TUI prompt's handoff."""

    from houmao.agents.realm_controller.backends import local_interactive

    backend = object.__new__(local_interactive.LocalInteractiveSession)
    backend._plan = SimpleNamespace(
        role_injection=SimpleNamespace(method="bootstrap_message", bootstrap_message="bootstrap")
    )
    backend._state = SimpleNamespace(role_bootstrap_applied=False, turn_index=0)
    operations: list[str] = []
    backend.m_dispatch_control = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: True,
        confirmed=lambda: operations.append("handoff"),
        deadline=time.monotonic() + 10,
    )
    monkeypatch.setattr(backend, "_require_tmux_session_name", lambda: "owned-session")
    monkeypatch.setattr(backend, "_primary_tmux_pane_target", lambda: "%1")
    monkeypatch.setattr(
        local_interactive, "load_tmux_buffer_shared", lambda *, text, **_: operations.append(text)
    )
    monkeypatch.setattr(local_interactive, "paste_tmux_buffer_shared", lambda **_: None)
    monkeypatch.setattr(local_interactive.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        local_interactive, "send_tmux_control_input_shared", lambda **_: operations.append("enter")
    )
    monkeypatch.setattr(local_interactive, "delete_tmux_buffer_shared", lambda **_: None)

    assert backend.send_prompt("managed prompt")[0].kind == "submitted"
    assert operations == ["bootstrap", "enter", "managed prompt", "enter", "handoff"]
    assert backend.m_dispatch_control.m_handoff_confirmed.is_set()


def test_tui_replacement_after_paste_prevents_enter_and_clears_buffer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A request loses submission authority if its body changes between paste and Enter."""

    from houmao.agents.realm_controller.backends import local_interactive

    backend = object.__new__(local_interactive.LocalInteractiveSession)
    active = True
    backend.m_dispatch_control = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: active, confirmed=lambda: None, deadline=time.monotonic() + 10
    )
    monkeypatch.setattr(backend, "_require_tmux_session_name", lambda: "owned-session")
    monkeypatch.setattr(backend, "_primary_tmux_pane_target", lambda: "%1")
    monkeypatch.setattr(local_interactive, "load_tmux_buffer_shared", lambda **_kwargs: None)
    operations: list[object] = []

    def paste(**_kwargs: object) -> None:
        """Replace the current body immediately after the literal paste."""

        nonlocal active
        operations.append("paste")
        active = False

    monkeypatch.setattr(local_interactive, "paste_tmux_buffer_shared", paste)
    monkeypatch.setattr(local_interactive.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        local_interactive,
        "send_tmux_control_input_shared",
        lambda **_kwargs: operations.append("enter"),
    )
    monkeypatch.setattr(
        local_interactive, "delete_tmux_buffer_shared", lambda **_: operations.append("delete-buffer")
    )
    with pytest.raises(BackendExecutionError, match="no longer active"):
        backend._submit_semantic_prompt("discarded request")
    assert operations == ["paste", "delete-buffer"]
