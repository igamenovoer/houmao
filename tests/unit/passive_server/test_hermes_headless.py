"""Recover Hermes headless status from exact durable evidence after server restart."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from houmao.agents.realm_controller.backends.hermes_headless import HermesHeadlessSession
from houmao.agents.realm_controller.backends.hermes_headless_protocol import HERMES_HEADLESS_REQUEST
from houmao.server.managed_agents import ManagedHeadlessActiveTurnRecord, ManagedHeadlessTurnRecord
from tests.unit.passive_server.test_headless_service import (
    _FakeHeadlessBackendSession,
    _FakeRuntimeController,
    _make_service,
    _seed_managed_handle,
)


@pytest.mark.parametrize("matching_result", [True, False])
def test_passive_rebuilds_hermes_turn_from_native_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, matching_result: bool
) -> None:
    """A separate viewer exit leaves unresolved native work in the active slot."""

    service = _make_service(tmp_path)
    headless = service.m_headless
    send = Mock(side_effect=AssertionError("Passive recovery attempted to replay a prompt"))
    controller = _FakeRuntimeController(
        manifest_path=tmp_path / "runtime/tracked-hermes/manifest.json",
        backend_session=_FakeHeadlessBackendSession(send_prompt_callback=send),
    )
    monkeypatch.setattr(controller, "registry_generation_id", "generation", raising=False)
    controller.manifest_path.parent.mkdir(parents=True)
    controller.manifest_path.write_text("{}\n", encoding="utf-8")
    tracked_id = "tracked-hermes"
    authority = _seed_managed_handle(service, tracked_agent_id=tracked_id, controller=controller)
    headless.m_store.write_authority(
        authority.model_copy(update={"backend": "hermes_headless", "tool": "hermes"})
    )
    headless.m_handles.clear()
    turn = Path(authority.session_root) / "manifest.turn-artifacts" / "exact-turn"
    turn.mkdir(parents=True)
    common = {
        "tracked_agent_id": authority.tracked_agent_id,
        "turn_id": turn.name,
        "turn_index": 1,
        "turn_artifact_dir": str(turn),
        "started_at_utc": "2026-11-16T00:00:00+00:00",
        "tmux_session_name": authority.tmux_session_name,
    }
    headless.m_store.write_active_turn(ManagedHeadlessActiveTurnRecord(**common))
    headless.m_store.write_turn_record(ManagedHeadlessTurnRecord(**common))
    (turn / HERMES_HEADLESS_REQUEST).write_text(
        json.dumps(
            {
                "turn_id": turn.name,
                "turn_index": 1,
                "session_id": "verified",
                "generation_id": "generation",
            }
        ),
        encoding="utf-8",
    )
    (turn / "stdout.jsonl").write_text(
        json.dumps({"type": "system", "subtype": "init", "session_id": ""})
        + "\n"
        + json.dumps(
            {
                "type": "result",
                "session_id": "verified" if matching_result else "another-conversation",
                "exit_code": 0,
                "text": "answer",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (turn / "stderr.log").write_text("native stderr\n", encoding="utf-8")
    (turn / "exitcode").write_text("0\n", encoding="utf-8")
    monkeypatch.setattr(
        "houmao.passive_server.headless.tmux_session_exists", lambda **_kwargs: True
    )
    monkeypatch.setattr(
        "houmao.passive_server.headless.resume_runtime_session", lambda **_kwargs: controller
    )
    monkeypatch.setattr("houmao.passive_server.headless.publish_live_agent_record", Mock())
    monkeypatch.setattr(headless, "_start_usage_service", Mock())
    monkeypatch.setattr(headless, "_reconcile_usage", Mock())

    headless.start()

    status = headless.turn_status(tracked_id, turn.name)
    assert not isinstance(status, tuple)
    assert status.status == ("completed" if matching_result else "unknown")
    assert (status.completed_at_utc is not None) == matching_result
    assert status.completion_source == ("native_jsonl" if matching_result else None)
    assert status.returncode == 0
    assert status.stdout_path == str(turn / "stdout.jsonl")
    assert headless.turn_artifact_text(tracked_id, turn.name, "stderr") == "native stderr\n"
    state = headless.get_managed_control_state(tracked_id)
    assert state is not None and state.can_accept_prompt_now == matching_result
    assert (state.active_turn is None) == matching_result
    if not matching_result:
        monkeypatch.setattr(
            controller.backend_session,
            "interrupt",
            lambda: HermesHeadlessSession.interrupt(controller.backend_session),
        )
        result = headless.interrupt_managed(tracked_id)
        assert isinstance(result, tuple) and result[0] == 409
        assert "attributable native admission" in result[1]["detail"]
        assert headless.m_store.read_active_turn(tracked_agent_id=tracked_id) == state.active_turn
        refused = headless.submit_turn(tracked_id, "new input")
        assert isinstance(refused, tuple) and refused[0] == 409
    send.assert_not_called()
