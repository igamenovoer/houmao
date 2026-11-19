"""Keep DSH passive-server authority and native evidence across reconstruction."""

from __future__ import annotations

import json
from pathlib import Path
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tests.unit.passive_server.contract_client import arrange_passive_launch_access
from houmao.agents.realm_controller.backends.headless_output import CanonicalHeadlessEvent
from houmao.passive_server.models import PassiveHeadlessTurnAcceptedResponse
from houmao.server.managed_agents import ManagedHeadlessActiveTurnRecord, ManagedHeadlessTurnRecord
from tests.unit.passive_server.test_headless_service import (
    _FakeHeadlessBackendSession,
    _FakeRuntimeController,
    _launch_request,
    _make_service,
    _seed_managed_handle,
)


def test_dsh_passive_headless_birth_selects_the_native_one_shot_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pass the qualified one-shot binding through the public passive launch."""

    arrange_passive_launch_access(monkeypatch, tmp_path)
    service = _make_service(tmp_path)
    request = _launch_request(tmp_path, tool="dsh")
    manifest = tmp_path / "runtime/manifest.json"
    manifest.parent.mkdir()
    controller = _FakeRuntimeController(manifest_path=manifest, output_format="dsh-cli")
    start = Mock(return_value=controller)
    monkeypatch.setattr(
        "houmao.passive_server.headless.load_brain_manifest",
        lambda _path: {"inputs": {"tool": "dsh"}},
    )
    monkeypatch.setattr("houmao.passive_server.headless.load_role_package", lambda *_args: None)
    monkeypatch.setattr("houmao.passive_server.headless.start_runtime_session", start)
    monkeypatch.setattr("houmao.passive_server.headless.publish_live_agent_record", Mock())
    monkeypatch.setattr(service.m_headless, "_start_usage_service", Mock())

    response = service.m_headless.launch(request)

    assert not isinstance(response, tuple)
    assert response.status == "ok"
    assert start.call_args.kwargs["backend"] == "dsh_headless"
    assert start.call_args.kwargs["mode"] == "headless"
    authority = service.m_headless.m_store.read_authority(
        tracked_agent_id=response.tracked_agent_id
    )
    assert authority is not None and authority.backend == "dsh_headless"


def test_kimi_launch_preserves_authority_and_accepts_managed_follow_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The expanded DSH selector retains the maintained Kimi launch and turn path."""

    arrange_passive_launch_access(monkeypatch, tmp_path)
    service = _make_service(tmp_path)
    request = _launch_request(tmp_path, tool="kimi")
    manifest = tmp_path / "runtime/manifest.json"
    manifest.parent.mkdir()
    prompts: list[str] = []

    def send(prompt: str, *, turn_artifact_dir_name: str) -> list:
        """Publish one controlled terminal result without starting a native process."""

        prompts.append(prompt)
        directory = manifest.parent / "manifest.turn-artifacts" / turn_artifact_dir_name
        (directory / "stdout.jsonl").write_text("", encoding="utf-8")
        (directory / "exitcode").write_text("0\n", encoding="utf-8")
        return []

    controller = _FakeRuntimeController(
        manifest_path=manifest,
        backend_session=_FakeHeadlessBackendSession(send_prompt_callback=send),
    )
    start = Mock(return_value=controller)
    monkeypatch.setattr(
        "houmao.passive_server.headless.load_brain_manifest",
        lambda _path: {"inputs": {"tool": "kimi"}},
    )
    monkeypatch.setattr("houmao.passive_server.headless.load_role_package", lambda *_args: None)
    monkeypatch.setattr("houmao.passive_server.headless.start_runtime_session", start)
    monkeypatch.setattr("houmao.passive_server.headless.publish_live_agent_record", Mock())
    monkeypatch.setattr(service.m_headless, "_start_usage_service", Mock())
    monkeypatch.setattr(service.m_headless, "_reconcile_usage", Mock())

    response = service.m_headless.launch(request)

    assert not isinstance(response, tuple)
    assert response.status == "ok"
    assert start.call_args.kwargs["backend"] == "kimi_headless"
    authority = service.m_headless.m_store.read_authority(
        tracked_agent_id=response.tracked_agent_id
    )
    assert authority is not None
    assert authority.backend == "kimi_headless" and authority.tool == "kimi"
    accepted = service.m_headless.submit_turn(response.tracked_agent_id, "Kimi follow-up")
    assert isinstance(accepted, PassiveHeadlessTurnAcceptedResponse)
    handle = service.m_headless._require_handle(response.tracked_agent_id)
    assert handle is not None and handle.turn_worker is not None
    handle.turn_worker.join(2)
    assert not handle.turn_worker.is_alive()
    assert prompts == ["Kimi follow-up"]
    assert (
        service.m_headless.turn_status(response.tracked_agent_id, accepted.turn_id).status
        == "completed"
    )


def test_unsupported_headless_backend_returns_422_before_runtime_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An incompatible resolved backend fails validation before provider launch."""

    service = _make_service(tmp_path)
    request = _launch_request(tmp_path)
    start = Mock(
        side_effect=AssertionError("Unsupported headless backends cannot start a provider")
    )
    monkeypatch.setattr(
        "houmao.passive_server.headless.load_brain_manifest",
        lambda _path: {"inputs": {"tool": "claude"}},
    )
    monkeypatch.setattr("houmao.passive_server.headless.load_role_package", lambda *_args: None)
    monkeypatch.setattr(
        "houmao.passive_server.headless.resolve_run_mode",
        lambda _tool, **_kwargs: SimpleNamespace(backend="local_interactive"),
    )
    monkeypatch.setattr("houmao.passive_server.headless.start_runtime_session", start)

    response = service.m_headless.launch(request)

    assert isinstance(response, tuple)
    assert response[0] == 422
    assert "supported headless backend" in response[1]["detail"]
    start.assert_not_called()
    assert service.m_headless.m_store.list_authority_records() == []


@pytest.mark.parametrize("live_host", [True, False])
def test_dsh_restart_reconciles_original_attempt_without_prompt_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, live_host: bool
) -> None:
    """A surviving worker stays active; later terminal artifacts clear its old admission."""

    service = _make_service(tmp_path)
    send = Mock(side_effect=AssertionError("Recovery must never resubmit the original input"))
    controller = _FakeRuntimeController(
        manifest_path=tmp_path / "runtime/tracked-dsh/manifest.json",
        backend_session=_FakeHeadlessBackendSession(send_prompt_callback=send),
        output_format="dsh-acp",
    )
    controller.manifest_path.parent.mkdir(parents=True)
    controller.manifest_path.write_text("{}\n", encoding="utf-8")
    (tmp_path / "agent-defs").mkdir()
    authority = _seed_managed_handle(service, tracked_agent_id="tracked-dsh", controller=controller)
    authority = authority.model_copy(update={"backend": "dsh_acp", "tool": "dsh"})
    store = service.m_headless.m_store
    store.write_authority(authority)
    service.m_headless.m_handles.clear()
    turn_dir = Path(authority.session_root) / "manifest.turn-artifacts/original"
    turn_dir.mkdir(parents=True)
    common = {
        "tracked_agent_id": authority.tracked_agent_id,
        "turn_id": "original",
        "turn_index": 1,
        "turn_artifact_dir": str(turn_dir),
        "started_at_utc": "2026-11-16T00:00:00+00:00",
        "tmux_session_name": authority.tmux_session_name,
    }
    store.write_active_turn(ManagedHeadlessActiveTurnRecord(**common))
    store.write_turn_record(ManagedHeadlessTurnRecord(**common))
    monkeypatch.setattr(
        "houmao.passive_server.headless.tmux_session_exists", lambda **_kwargs: live_host
    )
    monkeypatch.setattr(
        "houmao.passive_server.headless.headless_artifact_process_alive", lambda _path: live_host
    )
    monkeypatch.setattr(
        "houmao.passive_server.headless.resume_runtime_session", lambda **_kwargs: controller
    )
    monkeypatch.setattr("houmao.passive_server.headless.publish_live_agent_record", Mock())
    monkeypatch.setattr(service.m_headless, "_start_usage_service", Mock())
    monkeypatch.setattr(service.m_headless, "_reconcile_usage", Mock())

    service.m_headless.start()

    assert store.read_authority(tracked_agent_id=authority.tracked_agent_id) is not None
    state = service.m_headless.get_managed_control_state(authority.tracked_agent_id)
    assert state is not None
    assert state.can_accept_prompt_now is False
    if live_host:
        assert state.active_turn is not None
        raw = {"jsonrpc": "2.0", "id": 4, "result": {"stopReason": "end_turn"}}
        (turn_dir / "provider-stdout.jsonl").write_text(json.dumps(raw) + "\n", encoding="utf-8")
        canonical = CanonicalHeadlessEvent(
            kind="assistant",
            message="native DSH reply",
            turn_index=1,
            provider="dsh",
            provider_event_type="agent_message_chunk",
            session_id="exact-native-session",
            data={"text": "native DSH reply"},
        )
        (turn_dir / "canonical-events.jsonl").write_text(
            json.dumps(canonical.to_artifact_record()) + "\n", encoding="utf-8"
        )
        (turn_dir / "exitcode").write_text("0\n", encoding="utf-8")
        status = service.m_headless.turn_status(authority.tracked_agent_id, "original")
        assert status.status == "completed"
        assert (
            json.loads(
                service.m_headless.turn_artifact_text(
                    authority.tracked_agent_id, "original", "stdout"
                )
            )
            == raw
        )
        events = service.m_headless.turn_events(authority.tracked_agent_id, "original")
        assert [event.message for event in events.entries] == ["native DSH reply"]
        state = service.m_headless.get_managed_control_state(authority.tracked_agent_id)
        assert state.can_accept_prompt_now is True
    else:
        status = service.m_headless.turn_status(authority.tracked_agent_id, "original")
        assert status.status == "failed"
        assert state.runtime_resumable is False
    assert store.read_active_turn(tracked_agent_id=authority.tracked_agent_id) is None
    completed = store.read_turn_record(
        tracked_agent_id=authority.tracked_agent_id, turn_id="original"
    )
    service.m_headless.turn_status(authority.tracked_agent_id, "original")
    assert (
        store.read_turn_record(tracked_agent_id=authority.tracked_agent_id, turn_id="original")
        == completed
    )
    send.assert_not_called()


def test_dsh_concurrent_turn_requests_reserve_only_one_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Serialize the active-marker check and write before starting native work."""

    service = _make_service(tmp_path)
    started = threading.Event()
    finish = threading.Event()
    calls: list[str] = []

    def send(prompt: str, *, turn_artifact_dir_name: str) -> list:
        """Hold one native execution while two public requests compete for admission."""

        calls.append(prompt)
        started.set()
        assert finish.wait(3)
        return []

    authority = _seed_managed_handle(
        service,
        controller=_FakeRuntimeController(
            manifest_path=tmp_path / "runtime/manifest.json",
            backend_session=_FakeHeadlessBackendSession(send_prompt_callback=send),
        ),
    )
    authority = authority.model_copy(update={"backend": "dsh_acp", "tool": "dsh"})
    service.m_headless.m_store.write_authority(authority)
    service.m_headless.m_handles[authority.tracked_agent_id].authority = authority
    monkeypatch.setattr(service.m_headless, "_reconcile_usage", Mock())
    barrier = threading.Barrier(3)
    results: list[object] = []

    def submit() -> None:
        """Submit simultaneous requests through the same public service method."""

        barrier.wait()
        results.append(service.m_headless.submit_turn(authority.tracked_agent_id, "one input"))

    senders = [threading.Thread(target=submit) for _ in range(2)]
    try:
        for sender in senders:
            sender.start()
        barrier.wait()
        for sender in senders:
            sender.join(2)
            assert not sender.is_alive()
        assert started.wait(1)
        assert sum(isinstance(item, PassiveHeadlessTurnAcceptedResponse) for item in results) == 1
        assert sum(isinstance(item, tuple) and item[0] == 409 for item in results) == 1
        assert calls == ["one input"]
    finally:
        finish.set()
        handle = service.m_headless._require_handle(authority.tracked_agent_id)
        assert handle.turn_worker is not None
        handle.turn_worker.join(3)


def test_dsh_recovery_requires_exact_native_closure(tmp_path: Path) -> None:
    """Retain the original slot until the saved worker has matching closure evidence."""

    passive = _make_service(tmp_path)
    service = passive.m_headless
    authority = _seed_managed_handle(passive, tracked_agent_id="tracked-dsh")
    authority = authority.model_copy(update={"backend": "dsh_headless", "tool": "dsh"})
    service.m_store.write_authority(authority)
    service.m_handles[authority.tracked_agent_id].authority = authority
    turn_dir = Path(authority.session_root) / "manifest.turn-artifacts/original"
    turn_dir.mkdir(parents=True)
    common = {
        "tracked_agent_id": authority.tracked_agent_id,
        "turn_id": "original",
        "turn_index": 1,
        "turn_artifact_dir": str(turn_dir),
        "started_at_utc": "2026-11-16T00:00:00+00:00",
        "tmux_session_name": authority.tmux_session_name,
    }
    service.m_store.write_active_turn(ManagedHeadlessActiveTurnRecord(**common))
    service.m_store.write_turn_record(ManagedHeadlessTurnRecord(**common))
    (turn_dir / "exitcode").write_text("0\n")
    (turn_dir / "process.json").write_text(
        json.dumps({"child_pid": 1234, "child_birth_token": "actual-worker"})
    )
    closure = {
        "version": 1,
        "attempt_id": "original",
        "native_session_id": "native-session",
        "process_id": 1234,
        "process_birth_token": "superseded-worker",
        "source": "native_journal",
        "returncode": 0,
    }
    closure_file = turn_dir / "dsh-native-closure.json"
    closure_file.write_text(json.dumps(closure))

    status = service.turn_status(authority.tracked_agent_id, "original")
    assert not isinstance(status, tuple) and status.status == "unknown"
    assert service.m_store.read_active_turn(tracked_agent_id=authority.tracked_agent_id) is not None
    blocked = service.submit_turn(authority.tracked_agent_id, "duplicate")
    assert isinstance(blocked, tuple) and blocked[0] == 409

    closure_file.write_text(json.dumps({**closure, "process_birth_token": "actual-worker"}))
    status = service.turn_status(authority.tracked_agent_id, "original")
    assert not isinstance(status, tuple) and status.status == "completed"
    assert status.completion_source == "native_journal"
    assert service.m_store.read_active_turn(tracked_agent_id=authority.tracked_agent_id) is None
