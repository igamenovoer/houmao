"""Qualify actual native browser/API coexistence without paid model requests."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest

from houmao.agents.realm_controller.backends.dsh_web_client import DshWebClient, DshWebError
from tests.integration.agents.dsh.web.browser import NativeBrowser
from tests.integration.agents.dsh.web.conftest import NativeWebGates, NativeWebHost
from tests.integration.agents.dsh.web.controlled_model import controlled_browser_model


def _wait_ready(host: NativeWebHost, *, minimum_turn: int) -> dict[str, Any]:
    """Require settled native activity and idle authority after the expected turn."""

    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        state = host.client.state(host.identity)
        last = state.get("last_turn") or {}
        if last.get("turn", 0) >= minimum_turn and state["admission"]["ready_only"]:
            return state
        time.sleep(0.02)
    raise AssertionError("Expected shared native turn did not settle")


def _api_prompt(host: NativeWebHost, text: str, operation_id: str) -> None:
    """Insert once through the independent API and inspect only its original receipt."""

    receipt = host.client.prompt(
        host.identity,
        text,
        operation_id=operation_id,
        deadline_epoch_ms=int(time.time() * 1000) + 10_000,
    )
    assert receipt["message_id"]
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        receipt = host.client.receipt(host.identity, operation_id)
        if receipt is not None and receipt["status"] == "terminal":
            assert receipt["result"] == "completed"
            return
        time.sleep(0.02)
    raise AssertionError("Original API operation did not settle")


def test_browser_api_alternation_navigation_and_independent_auth(
    native_web_host: NativeWebHost,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Share history while browser drafts, navigation, and API revocation stay distinct."""

    host = native_web_host
    assert host.client.m_http is not None
    workspace = host.client.m_http.post(
        "/api/workspace/create",
        json={
            "type": "client-request",
            "rpcId": "workspace-setup",
            "method": "workspace/create",
            "payload": {"args": {"request": {"path": str(host.root)}}},
        },
    )
    assert workspace.status_code == 200
    assert workspace.json()["result"]["ok"] is True
    requests = controlled_messages_server[1]
    _api_prompt(host, "API first shared marker", "api-first")
    _wait_ready(host, minimum_turn=1)
    browser = NativeBrowser.from_connection_file(host.browser_connection_file())
    try:
        browser.call("contains", text="API first shared marker")
        before = host.client.state(host.identity)
        browser.call("draft", text="local draft must not become pending")
        draft = host.client.state(host.identity)
        assert draft["pending_inbox"] == []
        assert draft["active_turn"] is None
        assert draft["sequence"] == before["sequence"]
        assert draft["admission"]["ready_only"] is True
        browser.call("submit", text="Browser shared marker")
        _wait_ready(host, minimum_turn=2)
        assert len(requests) == 2
        assert "API first shared marker" in json.dumps(requests[1]["messages"])
        assert "Browser shared marker" in json.dumps(requests[1]["messages"])
        assert "local draft must not become pending" not in json.dumps(requests)
        _api_prompt(host, "API second shared marker", "api-second")
        _wait_ready(host, minimum_turn=3)
        browser.call("contains", text="API second shared marker")
        history = host.client.history(host.identity)
        claims = [entry for entry in history["entries"] if entry["event"] == "inbox/claimed"]
        assert {entry["turn"] for entry in claims} == {1, 2, 3}
        assert any(entry.get("operation_id") is None and entry["turn"] == 2 for entry in claims)
        target = dict(host.identity)
        other = browser.call("new")["session_id"]
        assert other != target["native_session_id"]
        browser.call("submit", text="Browser unrelated session marker")
        deadline = time.monotonic() + 20
        while len(requests) < 4 and time.monotonic() < deadline:
            time.sleep(0.02)
        assert len(requests) == 4
        assert "Browser shared marker" not in json.dumps(requests[3]["messages"])
        assert host.client.state(target)["identity"] == target
        _api_prompt(host, "API binding remains original marker", "api-bound")
        _wait_ready(host, minimum_turn=4)
        assert "Browser shared marker" in json.dumps(requests[4]["messages"])
        assert "Browser unrelated session marker" not in json.dumps(requests[4]["messages"])
        browser.call("select", session_id=target["native_session_id"])
        browser.call("contains", text="API binding remains original marker")
        replacement = DshWebClient.from_connection(host.origin, launch_token=host.launch_token)
        host.client.close()
        host.client = replacement
        browser.call("reload")
        browser.call("submit", text="Browser survives API revocation marker")
        _wait_ready(host, minimum_turn=5)
        assert len(requests) == 6
        assert host.client.state(target)["identity"] == target
    finally:
        browser.close()


@pytest.mark.parametrize("interruptor", ["api", "browser"])
def test_browser_queue_progress_and_exact_human_turn_interruption(
    native_web_factory: Callable[..., NativeWebHost],
    interruptor: str,
) -> None:
    """Observe streamed human work, refuse ordinary delivery, and retain native queue facts."""

    with controlled_browser_model() as model:
        host = native_web_factory(endpoint=model.endpoint)
        _api_prompt(host, "Seed browser queue session", "seed-queue")
        _wait_ready(host, minimum_turn=1)
        browser = NativeBrowser.from_connection_file(host.browser_connection_file())
        try:
            browser.call("submit", text="BROWSER_BLOCK human active turn")
            assert model.active.wait(10)
            browser.call("contains", text="Controlled active browser progress")
            active = host.client.state(host.identity)
            assert active["active_turn"] is not None
            assert active["admission"]["ready_only"] is False
            with pytest.raises(DshWebError):
                host.client.prompt(
                    host.identity,
                    "REFUSED_ORDINARY_NEVER_EXECUTES",
                    operation_id="refused-while-human-active",
                    deadline_epoch_ms=int(time.time() * 1000) + 5000,
                )
            browser.call("submit", text="Human queued next turn marker")
            deadline = time.monotonic() + 5
            pending: list[dict[str, Any]] = []
            while time.monotonic() < deadline:
                pending = host.client.state(host.identity)["pending_inbox"]
                if pending:
                    break
                time.sleep(0.02)
            assert pending
            assert all(row["operation_id"] is None for row in pending)
            with pytest.raises(DshWebError):
                host.client.prompt(
                    host.identity,
                    "REFUSED_QUEUE_NEVER_EXECUTES",
                    operation_id="refused-existing-queue",
                    deadline_epoch_ms=int(time.time() * 1000) + 5000,
                    admission_policy="if_no_pending",
                    operator=True,
                )
            start_sequence = active["active_turn"]["start_sequence"]
            if interruptor == "api":
                host.client.interrupt(host.identity, turn_start_seq=start_sequence)
            else:
                browser.call("stop")
            model.release.set()
            deadline = time.monotonic() + 10
            settled = host.client.state(host.identity)
            while (
                settled["last_turn"]["turn"] < 2 or settled["active_turn"] is not None
            ) and time.monotonic() < deadline:
                time.sleep(0.02)
                settled = host.client.state(host.identity)
            assert settled["last_turn"]["turn"] == 2
            assert settled["last_turn"]["result"] == "aborted"
            assert settled["active_turn"] is None
            assert {row["message_id"] for row in pending} <= {
                row["message_id"] for row in settled["pending_inbox"]
            }
            assert len(model.requests) == 2
            browser.call("contains", text="Human queued next turn marker")
            assert "REFUSED_ORDINARY_NEVER_EXECUTES" not in json.dumps(model.requests)
            assert "REFUSED_QUEUE_NEVER_EXECUTES" not in json.dumps(model.requests)
            history = host.client.history(host.identity)
            ended = [entry for entry in history["entries"] if entry["event"] == "turn/end"]
            assert any(entry["turn"] == 2 and entry["result"] == "aborted" for entry in ended)
        finally:
            model.release.set()
            browser.close()


def test_as_is_browser_answers_question_while_api_only_observes(
    native_web_factory: Callable[..., NativeWebHost],
) -> None:
    """Let the browser answer a native question without an API interaction responder."""

    with controlled_browser_model() as model:
        host = native_web_factory(endpoint=model.endpoint, operator_prompt_mode="as_is")
        _api_prompt(host, "Seed human question session", "seed-question")
        _wait_ready(host, minimum_turn=1)
        browser = NativeBrowser.from_connection_file(host.browser_connection_file())
        try:
            browser.call("submit", text="BROWSER_QUESTION ask the human")
            deadline = time.monotonic() + 10
            state = host.client.state(host.identity)
            while "question" not in state["interaction_waits"] and time.monotonic() < deadline:
                time.sleep(0.02)
                state = host.client.state(host.identity)
            assert "question" in state["interaction_waits"]
            browser.call("contains", text="Controlled browser question")
            assert state["admission"]["ready_only"] is False
            with pytest.raises(DshWebError):
                host.client.prompt(
                    host.identity,
                    "REFUSED_QUESTION_NEVER_EXECUTES",
                    operation_id="question-blocked",
                    deadline_epoch_ms=int(time.time() * 1000) + 5000,
                )
            browser.call("answer", name="Proceed")
            settled = _wait_ready(host, minimum_turn=2)
            assert settled["interaction_waits"] == []
            assert "Proceed" in json.dumps(model.requests[-1]["messages"])
            assert "REFUSED_QUESTION_NEVER_EXECUTES" not in json.dumps(model.requests)
        finally:
            browser.close()


def test_browser_wins_after_api_readiness_before_native_handoff(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
) -> None:
    """Refuse delayed API preparation after an actual browser starts native work."""

    with controlled_browser_model() as model:
        host = native_web_factory(endpoint=model.endpoint, extra_plugins=[native_web_gates.plugin])
        _api_prompt(host, "Seed human-first race", "seed-human-first")
        _wait_ready(host, minimum_turn=1)
        browser = NativeBrowser.from_connection_file(host.browser_connection_file())
        native_web_gates.hold("prepare", "ORDINARY_RACE_REFUSED")
        try:
            assert host.client.state(host.identity)["admission"]["ready_only"] is True
            with ThreadPoolExecutor(max_workers=1) as executor:
                pending = executor.submit(
                    host.client.prompt,
                    host.identity,
                    "ORDINARY_RACE_REFUSED",
                    operation_id="human-first-refused",
                    deadline_epoch_ms=int(time.time() * 1000) + 20_000,
                )
                try:
                    native_web_gates.wait("prepare")
                    browser.call("submit", text="BROWSER_BLOCK human wins native admission")
                    assert model.active.wait(10)
                finally:
                    native_web_gates.release("prepare")
                with pytest.raises(DshWebError):
                    pending.result(timeout=10)
            model.release.set()
            _wait_ready(host, minimum_turn=2)
            assert len(model.requests) == 2
            assert "ORDINARY_RACE_REFUSED" not in json.dumps(model.requests)
            assert host.client.receipt(host.identity, "human-first-refused") is None
        finally:
            model.release.set()
            native_web_gates.release("prepare")
            browser.close()


def test_program_wins_while_browser_input_is_still_preparing(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
) -> None:
    """Accept one idle API insertion before a browser's delayed native preparation."""

    with controlled_browser_model() as model:
        host = native_web_factory(endpoint=model.endpoint, extra_plugins=[native_web_gates.plugin])
        _api_prompt(host, "Seed program-first race", "seed-program-first")
        _wait_ready(host, minimum_turn=1)
        browser = NativeBrowser.from_connection_file(host.browser_connection_file())
        native_web_gates.hold("prepare", "Browser preparation resumes after program")
        try:
            browser.call("submit", text="Browser preparation resumes after program")
            native_web_gates.wait("prepare")
            receipt = host.client.prompt(
                host.identity,
                "BROWSER_BLOCK program wins native admission",
                operation_id="program-first-accepted",
                deadline_epoch_ms=int(time.time() * 1000) + 10_000,
            )
            assert receipt["message_id"]
            assert model.active.wait(10)
            native_web_gates.release("prepare")
            deadline = time.monotonic() + 5
            state = host.client.state(host.identity)
            while not state["pending_inbox"] and time.monotonic() < deadline:
                time.sleep(0.02)
                state = host.client.state(host.identity)
            assert state["pending_inbox"]
            assert all(row["operation_id"] is None for row in state["pending_inbox"])
            model.release.set()
            _wait_ready(host, minimum_turn=3)
            settled = host.client.receipt(host.identity, "program-first-accepted")
            assert settled is not None and settled["turns"] == [2]
            assert len(model.requests) == 3
            assert "Browser preparation resumes after program" in json.dumps(model.requests[2])
        finally:
            model.release.set()
            native_web_gates.release("prepare")
            browser.close()


def test_browser_model_selection_controls_the_actual_human_request(
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Select the native browser model and retain its actual request attribution."""

    host = native_web_factory(
        models=[
            {"id": name, "context_window": 131072, "max_output_tokens": 128, "reasoning": False}
            for name in ["controlled", "controlled-browser"]
        ]
    )
    _api_prompt(host, "Seed model selection session", "seed-model")
    _wait_ready(host, minimum_turn=1)
    browser = NativeBrowser.from_connection_file(host.browser_connection_file())
    try:
        browser.call("model", name="controlled-browser")
        assert host.client.state(host.identity)["model"]["model"] == "controlled-browser"
        browser.call("submit", text="Human selected model marker")
        deadline = time.monotonic() + 15
        while len(controlled_messages_server[1]) < 2 and time.monotonic() < deadline:
            time.sleep(0.02)
        assert len(controlled_messages_server[1]) >= 2
        _wait_ready(host, minimum_turn=2)
        assert controlled_messages_server[1][1]["model"] == "controlled-browser"
        conversation = host.client.conversation(host.identity)
        assert any(
            entry["type"] == "model/selection" and entry["model"] == "controlled-browser"
            for entry in conversation["entries"]
        )
    finally:
        browser.close()
