"""Exercise Hermes ACP multiplexing, reverse permission requests, and settlement."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import time

import pytest

from houmao.agents.realm_controller.backends.hermes_acp_service import HermesAcpServiceProvider
from houmao.agents.realm_controller.backends.hermes_native import (
    HermesDaemon,
    HermesDaemonIdentity,
    HermesSessionSnapshot,
)
from houmao.agents.realm_controller.backends.service_runtime import (
    ServiceOperationContext,
    ServiceOwnerConfig,
)


_PEER = """
import json
import sys

def send(frame):
    print(json.dumps({"jsonrpc": "2.0", **frame}), flush=True)

def update(text):
    send({
        "method": "session/update",
        "params": {
            "sessionId": "local-exact",
            "update": {"sessionUpdate": "agent_message_chunk",
                       "content": {"type": "text", "text": text}},
        },
    })

def tool_update(update, session_id="local-exact"):
    send({"method": "session/update", "params": {"sessionId": session_id, "update": update}})

while line := sys.stdin.readline():
    frame = json.loads(line)
    method = frame.get("method")
    params = frame["params"]
    if method == "initialize":
        result = {"protocolVersion": 1, "agentCapabilities": {"loadSession": True}}
    elif method == "session/load":
        assert params["sessionId"] == "local-exact"
        update("earlier transcript")
        result = {}
    elif method == "session/prompt":
        assert params["sessionId"] == "local-exact"
        prompt = params["prompt"][0]["text"]
        if prompt == "viewer eof":
            break
        if prompt == "cancel me":
            cancel = json.loads(sys.stdin.readline())
            assert cancel["method"] == "session/cancel"
            assert cancel["params"]["sessionId"] == "local-exact"
            result = {"stopReason": "cancelled"}
        elif prompt == "tools":
            start = {"sessionUpdate": "tool_call", "toolCallId": "private-id", "title": "private title", "kind": "read"}
            tool_update(start, "another-session")
            tool_update(start)
            tool_update(start)
            tool_update({"sessionUpdate": "tool_call_update", "toolCallId": "private-id", "status": "completed", "rawOutput": "private output"})
            update(prompt)
            result = {"stopReason": "end_turn"}
        else:
            options = [
                {"kind": "allow_always", "optionId": "approve"},
                {"kind": "reject_once", "optionId": "explicit-refusal"},
            ]
            if prompt == "only approval":
                options.pop()
            if prompt == "malformed options":
                options = {"kind": "allow_always", "optionId": "approve"}
            send({
                "id": "permission",
                "method": "terminal/create" if prompt == "unsupported" else "session/request_permission",
                "params": {"sessionId": "local-exact", "options": options},
            })
            update(prompt)
            reply = json.loads(sys.stdin.readline())
            if prompt == "unsupported":
                assert reply["error"]["code"] == -32601
            elif prompt in {"only approval", "malformed options"}:
                assert reply["result"]["outcome"] == {"outcome": "cancelled"}
            else:
                assert reply["result"]["outcome"] == {
                    "outcome": "selected", "optionId": "explicit-refusal",
                }
            result = {"stopReason": "end_turn"}
    else:
        raise RuntimeError(method)
    send({"id": frame["id"], "result": result})
"""


class _Daemon:
    """Model a verified, separately owned daemon over the real ACP child."""

    def __init__(self, home: Path) -> None:
        """Retain the stable private daemon evidence."""

        self.m_identity = HermesDaemonIdentity(
            home, 1, "birth", "instance", 1, str(home), "ws://127.0.0.1:12345"
        )
        self.m_stopped = False

    def ensure(self) -> HermesDaemonIdentity:
        """Return the already managed native authority."""

        return self.m_identity

    def discover(self) -> HermesDaemonIdentity:
        """Return the same live native authority."""

        return self.m_identity

    def resolve_session(self, session_id: str) -> HermesSessionSnapshot:
        """Supply exact native workspace and empty admission evidence."""

        assert session_id == "local-exact"
        return HermesSessionSnapshot(
            session_id,
            {"pending": [], "prompts": [], "open_requests": [], "running": False},
            self.m_identity.instance_id,
        )

    def stop(self) -> None:
        """Record lifecycle cleanup independently from viewer EOF."""

        self.m_stopped = True


@pytest.fixture
def provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Start a real private protocol child behind a stable fake daemon."""

    executable = tmp_path / "hermes"
    executable.write_text(f"#!{sys.executable}\n{_PEER}", encoding="utf-8")
    executable.chmod(0o700)
    daemon = _Daemon(tmp_path)
    monkeypatch.setattr(HermesDaemon, "from_inputs", lambda **_kwargs: daemon)
    instance = HermesAcpServiceProvider(
        ServiceOwnerConfig(
            backend="hermes_service",
            executable=str(executable),
            arguments=["acp"],
            working_directory=tmp_path,
            home_path=tmp_path,
            environment={},
            metadata={},
            root=tmp_path,
            manifest_path=tmp_path / "manifest.json",
            agent_id="managed",
            runtime_session_id="runtime",
            generation_id="generation",
            service_incarnation="incarnation",
            session_id="local-exact",
        )
    )
    try:
        instance.start()
        yield instance, daemon
    finally:
        instance.close()
        assert daemon.m_stopped


def _operation(tmp_path: Path, name: str, events: list[str]) -> ServiceOperationContext:
    """Track the existing service owner handoff hooks."""

    return ServiceOperationContext(
        name,
        tmp_path,
        lambda: events.append("authorized"),
        lambda _native: events.append("handed_off"),
        lambda _event: None,
    )


def test_acp_two_prompts_ignore_replayed_transcript_and_refuse_permissions(provider, tmp_path):
    """Read reverse requests and progress concurrently on one owned session."""

    backend, _daemon = provider
    assert backend.native_session_id == "local-exact"
    pid = backend.process_id
    for name in ("new first", "new second", "only approval", "malformed options", "unsupported"):
        events = []
        result = backend.prompt(
            name, execution_model=None, operation=_operation(tmp_path, name, events)
        )
        assert result.outcome == "completed"
        assert [event.message for event in result.events] == [name]
        assert events == ["authorized", "handed_off"]
        assert backend.process_id == pid


def test_acp_cancellation_is_scoped_and_eof_does_not_settle(provider, tmp_path):
    """Require the current operation ID and keep daemon work uncertain on EOF."""

    backend, daemon = provider
    events = []
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            backend.prompt,
            "cancel me",
            execution_model=None,
            operation=_operation(tmp_path, "target", events),
        )
        deadline = time.monotonic() + 3
        assert not backend.cancel("other")
        while not backend.cancel("target"):
            assert time.monotonic() < deadline
            time.sleep(0.01)
        assert future.result(timeout=3).outcome == "interrupted"

    events = []
    result = backend.prompt(
        "viewer eof", execution_model=None, operation=_operation(tmp_path, "eof", events)
    )
    assert events == ["authorized"]
    assert result.outcome == "uncertain"
    assert not backend.connection_ready
    assert not daemon.m_stopped


def test_acp_tool_updates_keep_only_attributable_progress(provider, tmp_path):
    """Suppress duplicates and private tool data in the selected operation."""

    backend, _daemon = provider
    result = backend.prompt(
        "tools", execution_model=None, operation=_operation(tmp_path, "tools", [])
    )

    assert result.outcome == "completed"
    assert [event.kind for event in result.events] == ["tool_call", "tool_result", "assistant"]
    first, last, _ = result.events
    assert first.payload == {"tool_call_id": "1", "tool_kind": "read", "status": "pending"}
    assert last.payload == {"tool_call_id": "1", "tool_kind": "read", "status": "completed"}
    assert all("private" not in event.message for event in result.events)
