from __future__ import annotations

import json
from pathlib import Path

import pytest

from houmao.cao.models import CaoTerminalStatus
from houmao.server.config import HoumaoServerConfig
from houmao.server.models import HoumaoRegisterLaunchRequest
from houmao.server.service import HoumaoServerService, ProxyResponse, TerminalWatchWorker


def _json_response(payload: object, *, status_code: int = 200) -> ProxyResponse:
    return ProxyResponse(
        status_code=status_code,
        body=json.dumps(payload).encode("utf-8"),
        content_type="application/json",
        json_payload=payload,
    )


class _FakeTransport:
    def __init__(self, responses: dict[tuple[str, str, tuple[tuple[str, str], ...]], ProxyResponse]) -> None:
        self.m_responses = responses

    def request(
        self,
        *,
        base_url: str,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
    ) -> ProxyResponse:
        del base_url
        key = (method.upper(), path, tuple(sorted((params or {}).items())))
        return self.m_responses[key]


class _FakeChildManager:
    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None


def test_register_launch_discovers_terminal_and_persists_registration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(TerminalWatchWorker, "start", lambda self: None)
    transport = _FakeTransport(
        {
            (
                "GET",
                "/sessions/cao-gpu/terminals",
                (),
            ): _json_response(
                [
                    {
                        "id": "abcd1234",
                        "name": "gpu",
                        "provider": "codex",
                        "session_name": "cao-gpu",
                        "agent_profile": "runtime-profile",
                        "status": "idle",
                    }
                ]
            ),
            (
                "GET",
                "/terminals/abcd1234",
                (),
            ): _json_response(
                {
                    "id": "abcd1234",
                    "name": "gpu",
                    "provider": "codex",
                    "session_name": "cao-gpu",
                    "agent_profile": "runtime-profile",
                    "status": "idle",
                }
            ),
        }
    )
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=transport,
        child_manager=_FakeChildManager(),
    )

    response = service.register_launch(
        HoumaoRegisterLaunchRequest(
            session_name="cao-gpu",
            tool="codex",
            manifest_path="/tmp/manifest.json",
            session_root="/tmp/session-root",
            agent_name="AGENTSYS-gpu",
            agent_id="AGENTSYS-gpu",
            tmux_session_name="AGENTSYS-gpu",
        )
    )

    assert response.success is True
    assert response.terminal_id == "abcd1234"
    state = service.terminal_state("abcd1234")
    assert state.terminal.session_name == "cao-gpu"
    registration_path = tmp_path / "houmao_servers" / "127.0.0.1-9889" / "sessions" / "cao-gpu" / "registration.json"
    payload = json.loads(registration_path.read_text(encoding="utf-8"))
    assert payload["session_name"] == "cao-gpu"
    assert payload["terminal_id"] is None
    assert payload["manifest_path"] == "/tmp/manifest.json"


def test_refresh_terminal_state_reduces_terminal_status_and_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(TerminalWatchWorker, "start", lambda self: None)
    responses: dict[tuple[str, str, tuple[tuple[str, str], ...]], ProxyResponse] = {
        (
            "GET",
            "/terminals/abcd1234",
            (),
        ): _json_response(
            {
                "id": "abcd1234",
                "name": "gpu",
                "provider": "codex",
                "session_name": "cao-gpu",
                "agent_profile": "runtime-profile",
                "status": CaoTerminalStatus.PROCESSING.value,
            }
        ),
        (
            "GET",
            "/terminals/abcd1234/output",
            (("mode", "full"),),
        ): _json_response({"output": "partial output"}),
    }
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=_FakeTransport(responses),
        child_manager=_FakeChildManager(),
    )
    service.sync_created_terminal(
        {
            "id": "abcd1234",
            "name": "gpu",
            "provider": "codex",
            "session_name": "cao-gpu",
            "agent_profile": "runtime-profile",
            "status": CaoTerminalStatus.IDLE.value,
        }
    )
    service.note_prompt_submission(terminal_id="abcd1234", message="Explain the failure.")

    first_state = service.refresh_terminal_state("abcd1234")

    assert first_state.operator_state.status == "processing"
    assert first_state.raw_observation is not None
    assert first_state.raw_observation.output_excerpt == "partial output"
    assert first_state.owned_work.state == "submitted"

    responses[("GET", "/terminals/abcd1234", ())] = _json_response(
        {
            "id": "abcd1234",
            "name": "gpu",
            "provider": "codex",
            "session_name": "cao-gpu",
            "agent_profile": "runtime-profile",
            "status": CaoTerminalStatus.COMPLETED.value,
        }
    )
    responses[("GET", "/terminals/abcd1234/output", (("mode", "full"),))] = _json_response(
        {"output": "final output"}
    )

    second_state = service.refresh_terminal_state("abcd1234")

    assert second_state.operator_state.status == "completed"
    assert second_state.owned_work.state == "completed"
    assert second_state.external_activity.last_changed_at_utc is None
    state_path = (
        tmp_path
        / "houmao_servers"
        / "127.0.0.1-9889"
        / "state"
        / "terminals"
        / "abcd1234"
        / "current.json"
    )
    assert state_path.is_file()
