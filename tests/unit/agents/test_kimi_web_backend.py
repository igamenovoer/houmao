"""Pin stock Kimi Web's check-and-send and exact native result semantics."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
import time
from typing import Any
from urllib.parse import unquote, urlsplit

import pytest

from houmao.agents.realm_controller.backends.dispatch_control import HeadlessDispatchControl
from houmao.agents.realm_controller.backends.dsh_web_client import DshWebError
from houmao.agents.realm_controller.backends.kimi_web import (
    KimiWebSession,
    KimiWebSessionState,
    recover_kimi_web_prompt_result,
)
from houmao.agents.realm_controller.backends.kimi_web_client import KimiWebClient
from houmao.hook_observation.kimi_journal import kimi_native_workspace_path


class _Native:
    """Model the bounded stock HTTP contract and an append-only native journal."""

    def __init__(self, journal: Path, workspace: Path) -> None:
        """Start with a known exact conversation and no active browser work."""

        self.m_journal: Path = journal
        self.m_workspace: Path = workspace
        self.m_busy: bool = False
        self.m_lose_response: bool = False
        self.m_refuse_preflight: bool = False
        self.m_calls: list[tuple[str, str]] = []

    def append(self, *rows: dict[str, Any]) -> None:
        """Write native rows without coupling them to a gateway execution lifecycle."""

        with self.m_journal.open("a") as stream:
            for row in rows:
                stream.write(json.dumps({"agentId": "main", **row}) + "\n")

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        before_send: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        """Return one exact receipt, optionally after the browser wins the race."""

        if before_send:
            before_send()
        self.m_calls.append((method, path))
        if method == "GET" and path == "/sessions/session_selected":
            return {
                "id": "session_selected",
                "metadata": {"cwd": str(self.m_workspace)},
                "archived": False,
                "busy": self.m_busy,
                "main_turn_active": self.m_busy,
                "pending_interaction": "none",
            }
        if method == "GET" and path.endswith("/prompts"):
            return {
                "active": None,
                "queued": ["browser pending"] if self.m_refuse_preflight else [],
            }
        if method == "POST" and path.endswith("/prompts"):
            assert body is not None
            self.write_turn("browser_prompt", 0, "unrelated browser text")
            prompt_id = body["prompt_id"]
            self.write_turn(prompt_id, 1, "exact managed text")
            if self.m_lose_response:
                raise DshWebError("outcome_uncertain", "Native HTTP response lost")
            return {"prompt_id": prompt_id, "status": "queued"}
        if method == "POST" and path.endswith(":abort"):
            assert body == {}
            return {"aborted": True}
        pytest.fail(f"Unexpected native request {method} {path}")

    def write_turn(self, prompt_id: str, turn: int, text: str) -> None:
        """Record one native start, assistant output, and two matching terminal facts."""

        self.append(
            {"type": "turn.prompt", "promptId": prompt_id, "turnId": turn},
            {
                "type": "context.append_loop_event",
                "event": {
                    "type": "content.part",
                    "turnId": str(turn),
                    "part": {"type": "text", "text": text},
                },
            },
            {"type": "turn.ended", "turnId": turn, "reason": "completed"},
            {"type": "prompt.completed", "promptId": prompt_id, "reason": "completed"},
        )


@pytest.fixture
def web(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[KimiWebSession, _Native]:
    """Construct a verified fixture owner with no tmux or network dependency."""

    home = tmp_path / "home"
    workspace = tmp_path / "project"
    workspace.mkdir()
    session = kimi_native_workspace_path(home, workspace) / "session_selected"
    journal = session / "agents/main/wire.jsonl"
    journal.parent.mkdir(parents=True)
    journal.touch(mode=0o600)
    state_path = session / "state.json"
    state_path.touch(mode=0o600)
    state_path.write_text(json.dumps({"id": session.name, "cwd": str(workspace)}))
    identity = {
        "protocol_version": 1,
        "agent_id": "agent",
        "runtime_session_id": "runtime",
        "native_session_id": session.name,
        "generation": "generation",
        "host_incarnation": "host",
        "agent_incarnation": "instance",
    }
    state = KimiWebSessionState(
        origin="http://127.0.0.1:8080",
        web_identity=identity,
        bootstrap_path=str(home / "bootstrap.json"),
        cookie_path=str(home / "server.token"),
        control_path=str(home / "control.json"),
        supervisor_pid=39,
        supervisor_birth_token="proc:5",
        tmux_session_name="test",
        evidence_path=str(journal),
        working_directory=str(workspace),
        native_pid=40,
        native_birth_token="proc:6",
    )
    adapter = KimiWebSession()
    adapter.m_state = state
    adapter.m_manifest_path = tmp_path / "manifest.json"
    adapter.manifest_path.write_text(
        json.dumps(
            {
                "backend": "kimi_web",
                "registry_generation_id": "generation",
                "agent_id": "agent",
                "runtime_session_id": "runtime",
                "working_directory": str(workspace),
                "backend_state": state.to_payload(),
                "launch_plan": {"home_selector": {"home_path": str(home)}},
            }
        )
    )
    native = _Native(journal, workspace)
    monkeypatch.setattr(adapter, "_client", lambda: native)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.kimi_web.UsageService.begin_headless_turn",
        lambda *_args, **_kwargs: None,
    )
    return adapter, native


def test_reports_native_queue_receipt_before_settlement(
    web: tuple[KimiWebSession, _Native],
) -> None:
    """Preserve a late browser win and attribute only the managed native answer."""

    adapter, native = web
    receipt = adapter.manifest_path.parent / "manifest.turn-artifacts/request/web-receipt.json"
    handed_off: list[str] = []
    control = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: True,
        confirmed=lambda: handed_off.append(json.loads(receipt.read_text())["status"]),
        deadline=time.monotonic() + 2,
    )
    adapter.configure_request_dispatch(control)
    events = adapter.send_web_prompt("input", turn_artifact_dir_name="request")
    assert handed_off == ["queued"]
    assert control.m_input_started.is_set()
    assert events[0].payload and events[0].payload["native_status"] == "queued"
    assert [event.message for event in events if event.kind == "assistant"] == [
        "exact managed text"
    ]
    terminal = json.loads(receipt.with_name("web-result.json").read_text())
    assert terminal["receipt"]["turns"] == [1]
    assert terminal["outcome"] == "completed"


def test_passive_read_and_rejected_preflight_send_no_prompt(
    web: tuple[KimiWebSession, _Native],
) -> None:
    """Use non-mutating session state passively, then respect a checked pending queue."""

    adapter, native = web
    assert adapter.observe_web_state()["admission"]["ready_only"]
    assert native.m_calls == [("GET", "/sessions/session_selected")]
    native.m_refuse_preflight = True
    with pytest.raises(DshWebError, match="not_ready"):
        adapter.send_web_prompt("input", turn_artifact_dir_name="refused")
    assert all(method == "GET" for method, _ in native.m_calls)


def test_final_native_readiness_follows_dispatch_authorization(
    web: tuple[KimiWebSession, _Native],
) -> None:
    """Refuse native work that starts while the managed permission is being checked."""

    adapter, native = web
    checks = 0

    def allow() -> bool:
        """Start browser work during the final gateway permission callback."""

        nonlocal checks
        checks += 1
        if checks == 2:
            native.m_busy = True
        return True

    control = HeadlessDispatchControl.from_callbacks(
        allowed=allow, confirmed=lambda: None, deadline=time.monotonic() + 2
    )
    adapter.configure_request_dispatch(control)
    with pytest.raises(DshWebError, match="not_ready"):
        adapter.send_web_prompt("input", turn_artifact_dir_name="late-browser")
    assert native.m_calls == [("GET", "/sessions/session_selected")]
    assert not control.m_input_started.is_set()


def test_lost_http_response_recovers_exact_journal_without_repeat(
    web: tuple[KimiWebSession, _Native],
) -> None:
    """Recover native completion from the saved exact attempt instead of replaying input."""

    adapter, native = web
    native.m_lose_response = True
    with pytest.raises(DshWebError, match="outcome_uncertain"):
        adapter.send_web_prompt("input", turn_artifact_dir_name="lost")
    recover_kimi_web_prompt_result(adapter.manifest_path, "generation", "lost")
    result_path = adapter.manifest_path.parent / "manifest.turn-artifacts/lost/web-result.json"
    result = json.loads(result_path.read_text())
    assert result["assistant_text"] == "exact managed text"
    assert result["receipt"]["native_status"] == "unknown"
    assert [item for item in native.m_calls if item[0] == "POST"] == [
        ("POST", "/sessions/session_selected/prompts")
    ]


def test_interrupt_uses_captured_native_prompt(web: tuple[KimiWebSession, _Native]) -> None:
    """Refuse stale capture and abort the exact active native prompt on valid capture."""

    adapter, native = web
    native.m_busy = True
    native.append({"type": "turn.prompt", "promptId": "active_prompt", "turnId": 2})
    captured = adapter.observe_web_state()["active_turn"]
    assert captured and captured["turn"] == 2
    assert (
        adapter.interrupt_web_turn(adapter.state.web_identity, turn_start_seq=0).status == "error"
    )
    assert (
        adapter.interrupt_web_turn(
            adapter.state.web_identity,
            turn_start_seq=captured["start_sequence"],
        ).status
        == "ok"
    )
    assert [item for item in native.m_calls if item[0] == "POST"] == [
        ("POST", "/sessions/session_selected/prompts/active_prompt:abort")
    ]


def test_wrong_listener_never_reads_private_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject changed kernel listener ownership before reading or sending a bearer."""

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.kimi_web_client.owned_listener",
        lambda *_args: False,
    )
    client = KimiWebClient("http://127.0.0.1:8080", 1234, "proc:99", tmp_path / "token")
    with pytest.raises(DshWebError, match="stale_identity"):
        client.request("GET", "/meta")


def test_explicit_browser_open_keeps_credential_out_of_process_arguments(
    web: tuple[KimiWebSession, _Native],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use a 0600 local browser bootstrap whose public result contains no bearer."""

    adapter, _ = web
    sentinel = "synthetic-native-browser-token"
    seen: list[str] = []
    monkeypatch.setattr(adapter, "browser_credentials", lambda: (adapter.state.origin, sentinel))
    monkeypatch.setattr("webbrowser.open", lambda path: not seen.append(path))
    result = adapter.open_browser()
    assert result.status == "ok"
    browser_source = Path(unquote(urlsplit(seen[0]).path))
    assert browser_source.stat().st_mode & 0o777 == 0o600
    assert f"{adapter.state.origin}/#token={sentinel}" in browser_source.read_text()
    assert sentinel not in seen[0] and sentinel not in result.detail
