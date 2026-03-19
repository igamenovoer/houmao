from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

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
    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:9890",
        healthy: bool = True,
        health_status: str | None = "ok",
        service_name: str | None = "cli-agent-orchestrator",
        error: str | None = None,
        ownership_file: Path | None = None,
    ) -> None:
        self.m_base_url = base_url
        self.m_healthy = healthy
        self.m_health_status = health_status
        self.m_service_name = service_name
        self.m_error = error
        self.m_ownership_file = ownership_file or Path("/tmp/houmao-server-tests-no-ownership")
        self.start_calls = 0
        self.stop_calls = 0

    def start(self) -> None:
        self.start_calls += 1

    def stop(self) -> None:
        self.stop_calls += 1

    def inspect(self) -> object:
        config = type("Config", (), {"base_url": self.m_base_url})()
        status = type(
            "Status",
            (),
            {
                "healthy": self.m_healthy,
                "health_status": self.m_health_status,
                "service": self.m_service_name,
                "error": self.m_error,
            },
        )()
        return type("Inspection", (), {"config": config, "status": status})()

    def ownership_file_path(self) -> Path:
        return self.m_ownership_file


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


def test_startup_persists_current_instance_and_child_metadata(tmp_path: Path) -> None:
    ownership_file = tmp_path / "child-cao" / "ownership.json"
    ownership_file.parent.mkdir(parents=True, exist_ok=True)
    ownership_file.write_text("{}\n", encoding="utf-8")
    child_manager = _FakeChildManager(ownership_file=ownership_file)
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=_FakeTransport({("GET", "/sessions", ()): _json_response([])}),
        child_manager=child_manager,
    )

    service.startup()

    current_instance_path = (
        tmp_path / "houmao_servers" / "127.0.0.1-9889" / "run" / "current-instance.json"
    )
    current_instance = json.loads(current_instance_path.read_text(encoding="utf-8"))
    health = service.health_response()

    assert child_manager.start_calls == 1
    assert current_instance["status"] == "ok"
    assert current_instance["api_base_url"] == "http://127.0.0.1:9889"
    assert current_instance["child_cao"]["api_base_url"] == "http://127.0.0.1:9890"
    assert current_instance["child_cao"]["derived_port"] == 9890
    assert current_instance["child_cao"]["ownership_file"] == str(ownership_file)
    assert health.status == "ok"
    assert health.service == "cli-agent-orchestrator"
    assert health.houmao_service == "houmao-server"
    assert health.child_cao is not None
    assert health.child_cao.healthy is True
    assert health.child_cao.derived_port == 9890


def test_startup_seeds_existing_child_sessions_and_starts_watch_workers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    started: list[str] = []
    monkeypatch.setattr(TerminalWatchWorker, "start", lambda self: started.append(self.m_terminal_id))
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=_FakeTransport(
            {
                ("GET", "/sessions", ()): _json_response([{"id": "cao-gpu"}]),
                (
                    "GET",
                    "/sessions/cao-gpu/terminals",
                    (),
                ): _json_response(
                    [
                        {
                            "id": "abcd1234",
                            "name": "gpu-a",
                            "provider": "codex",
                            "session_name": "cao-gpu",
                            "agent_profile": "runtime-profile",
                            "status": "idle",
                        },
                        {
                            "id": "deadbeef",
                            "name": "gpu-b",
                            "provider": "codex",
                            "session_name": "cao-gpu",
                            "agent_profile": "runtime-profile",
                            "status": "processing",
                        },
                    ]
                ),
            }
        ),
        child_manager=_FakeChildManager(),
    )

    service.startup()

    assert sorted(started) == ["abcd1234", "deadbeef"]
    assert service.terminal_state("abcd1234").terminal.session_name == "cao-gpu"
    assert service.terminal_state("deadbeef").terminal.status == CaoTerminalStatus.PROCESSING


def test_terminal_history_sorts_entries_and_applies_limit(tmp_path: Path) -> None:
    config = HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path)
    history_dir = config.terminal_history_root / "abcd1234"
    history_dir.mkdir(parents=True, exist_ok=True)
    (history_dir / "samples.ndjson").write_text(
        "\n".join(
            (
                json.dumps(
                    {
                        "recorded_at_utc": "2026-03-19T10:00:02+00:00",
                        "kind": "sample",
                        "payload": {"ordinal": 2},
                    }
                ),
                json.dumps(
                    {
                        "recorded_at_utc": "2026-03-19T10:00:01+00:00",
                        "kind": "sample",
                        "payload": {"ordinal": 1},
                    }
                ),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    (history_dir / "transitions.ndjson").write_text(
        json.dumps(
            {
                "recorded_at_utc": "2026-03-19T10:00:03+00:00",
                "kind": "transition",
                "payload": {"ordinal": 3},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    service = HoumaoServerService(
        config=config,
        transport=_FakeTransport({}),
        child_manager=_FakeChildManager(),
    )

    history = service.terminal_history("abcd1234", limit=2)

    assert [entry.payload["ordinal"] for entry in history.entries] == [2, 3]
    assert [entry.kind for entry in history.entries] == ["sample", "transition"]


def test_handle_deleted_session_stops_workers_and_clears_registry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    stopped: list[str] = []
    monkeypatch.setattr(TerminalWatchWorker, "start", lambda self: None)
    monkeypatch.setattr(
        TerminalWatchWorker,
        "stop",
        lambda self, *, join=True: stopped.append(self.m_terminal_id),
    )
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=_FakeTransport({}),
        child_manager=_FakeChildManager(),
    )
    service.sync_created_terminal(
        {
            "id": "abcd1234",
            "name": "gpu-a",
            "provider": "codex",
            "session_name": "cao-gpu",
            "agent_profile": "runtime-profile",
            "status": "idle",
        }
    )
    service.sync_created_terminal(
        {
            "id": "deadbeef",
            "name": "gpu-b",
            "provider": "codex",
            "session_name": "cao-gpu",
            "agent_profile": "runtime-profile",
            "status": "idle",
        }
    )

    service.handle_deleted_session("cao-gpu")

    assert sorted(stopped) == ["abcd1234", "deadbeef"]
    assert "cao-gpu" not in service.m_sessions
    assert service.m_terminals == {}
    with pytest.raises(HTTPException, match="Unknown terminal `abcd1234`"):
        service.terminal_state("abcd1234")


def test_shutdown_stops_workers_and_child_manager(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    stopped: list[str] = []
    child_manager = _FakeChildManager()
    monkeypatch.setattr(TerminalWatchWorker, "start", lambda self: None)
    monkeypatch.setattr(
        TerminalWatchWorker,
        "stop",
        lambda self, *, join=True: stopped.append(self.m_terminal_id),
    )
    service = HoumaoServerService(
        config=HoumaoServerConfig(api_base_url="http://127.0.0.1:9889", runtime_root=tmp_path),
        transport=_FakeTransport({}),
        child_manager=child_manager,
    )
    service.sync_created_terminal(
        {
            "id": "abcd1234",
            "name": "gpu",
            "provider": "codex",
            "session_name": "cao-gpu",
            "agent_profile": "runtime-profile",
            "status": "idle",
        }
    )

    service.shutdown()

    assert stopped == ["abcd1234"]
    assert child_manager.stop_calls == 1
