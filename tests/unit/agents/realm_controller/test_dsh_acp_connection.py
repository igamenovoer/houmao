"""Exercise ACP pipe concurrency and failure semantics with real subprocesses."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys
import threading

import pytest

from houmao.agents.realm_controller.backends.dsh_acp_connection import (
    DshAcpConnection,
    DshAcpProtocolError,
    DshAcpRequestError,
    reject_dsh_acp_permission,
    validate_dsh_acp_initialization,
)


def _worker(tmp_path: Path, body: str, **kwargs: object) -> DshAcpConnection:
    """Start an isolated deterministic peer using the managed interpreter."""

    return DshAcpConnection.from_command(
        [sys.executable, "-u", "-c", body],
        cwd=tmp_path,
        env=os.environ.copy(),
        **kwargs,  # type: ignore[arg-type]
    )


def test_reader_handles_permission_notifications_and_reversed_responses(tmp_path: Path) -> None:
    """A pending permission cannot block updates or unrelated responses."""

    entered = threading.Event()
    release = threading.Event()
    raw: list[str] = []

    def permission(method: str, params: dict[str, object]) -> dict[str, object]:
        """Hold a permission while another native result arrives."""

        assert method == "session/request_permission"
        assert params["sessionId"] == "native-a"
        entered.set()
        assert release.wait(5)
        return {"outcome": {"outcome": "cancelled"}}

    connection = _worker(
        tmp_path,
        """
import json, sys
def send(frame):
    print(json.dumps({'jsonrpc': '2.0', **frame}), flush=True)
first = json.loads(input())
second = json.loads(input())
sys.stderr.write('diagnostic' * 200000 + '\\n')
sys.stderr.flush()
send({'id': 'permission-1', 'method': 'session/request_permission', 'params': {'sessionId': 'native-a'}})
send({'method': 'session/update', 'params': {'sessionId': 'native-a', 'update': {'sessionUpdate': 'agent_message_chunk'}}})
send({'id': second['id'], 'result': {'sessionId': 'native-a'}})
answer = json.loads(input())
assert answer['id'] == 'permission-1'
send({'id': first['id'], 'result': {'stopReason': 'cancelled'}})
sys.stdin.read()
""",
        request_handler=permission,
        frame_sink=raw.append,
    )
    try:
        first = connection.request("session/prompt", {"sessionId": "native-a", "prompt": []})
        second = connection.request("session/list", {})
        assert entered.wait(5)
        assert second.result(timeout=5) == {"sessionId": "native-a"}
        notification = connection.next_notification(timeout=5)
        assert notification is not None
        assert notification["params"]["sessionId"] == "native-a"
        assert not first.done()
        release.set()
        assert first.result(timeout=5) == {"stopReason": "cancelled"}
        assert len(connection.diagnostics) <= 4096 * 128
        assert len(raw) == 4
    finally:
        release.set()
        connection.close()
    assert connection.process.returncode == 0


@pytest.mark.parametrize(
    "invalid", ["not-json", '{"jsonrpc":"1.0"}', '{"jsonrpc":"2.0","id":999,"result":{}}']
)
def test_invalid_stdout_fails_every_pending_request(tmp_path: Path, invalid: str) -> None:
    """Protocol corruption leaves no request waiting and never resends it."""

    connection = _worker(
        tmp_path,
        f"import sys; input(); print({invalid!r}, flush=True); sys.stdin.read()",
    )
    try:
        pending = connection.request("initialize", {})
        with pytest.raises(DshAcpProtocolError):
            pending.result(timeout=5)
        with pytest.raises(DshAcpProtocolError):
            connection.request("initialize", {})
    finally:
        connection.close()


def test_eof_is_failure_and_raw_frames_remain_distinct(tmp_path: Path) -> None:
    """EOF cannot establish completion merely because a native update exists."""

    raw: list[str] = []
    connection = _worker(
        tmp_path,
        """
import json
input()
print(json.dumps({'jsonrpc':'2.0','method':'session/update','params':{'sessionId':'wrong-session','update':{}}}), flush=True)
""",
        frame_sink=raw.append,
    )
    try:
        pending = connection.request("session/prompt", {"sessionId": "expected"})
        with pytest.raises(DshAcpProtocolError):
            pending.result(timeout=5)
        assert connection.next_notification(timeout=5)["params"]["sessionId"] == "wrong-session"
        assert len(raw) == 1
    finally:
        connection.close()


def test_remote_errors_are_not_successful_results(tmp_path: Path) -> None:
    """A peer refusal remains a typed remote error with its original code."""

    connection = _worker(
        tmp_path,
        """
import json, sys
frame=json.loads(input())
print(json.dumps({'jsonrpc':'2.0','id':frame['id'],'error':{'code':-32602,'message':'missing session'}}), flush=True)
sys.stdin.read()
""",
    )
    try:
        with pytest.raises(DshAcpRequestError) as failure:
            connection.request("session/resume", {"sessionId": "missing"}).result(timeout=5)
        assert failure.value.error["code"] == -32602
    finally:
        connection.close()


def test_concurrent_request_writes_are_complete_frames(tmp_path: Path) -> None:
    """Parallel control calls cannot splice their JSON payloads together."""

    connection = _worker(
        tmp_path,
        """
import json, sys
for line in sys.stdin:
    frame = json.loads(line)
    print(json.dumps({'jsonrpc':'2.0','id':frame['id'],'result':frame['params']}), flush=True)
""",
    )
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            calls = [
                pool.submit(connection.request, "probe", {"n": n, "text": "x" * 10000})
                for n in range(16)
            ]
            assert [call.result(timeout=5).result(timeout=5)["n"] for call in calls] == list(
                range(16)
            )
    finally:
        connection.close()


def test_resume_capability_is_required_only_for_continuation() -> None:
    """Missing resume support fails before the caller can submit any prompt."""

    result = {
        "protocolVersion": 1,
        "agentInfo": {"name": "deepseek-harness-acp", "version": "0.0.1"},
        "agentCapabilities": {"sessionCapabilities": {"close": {}}},
    }
    validate_dsh_acp_initialization(result, require_resume=False)
    with pytest.raises(DshAcpProtocolError, match="lifecycle capabilities"):
        validate_dsh_acp_initialization(result, require_resume=True)


def test_permission_handler_denies_unanswered_questions_and_checks_binding() -> None:
    """The headless client never invents approval or accepts another session."""

    params = {
        "sessionId": "native-a",
        "options": [
            {"optionId": "approve", "kind": "allow_once"},
            {"optionId": "deny", "kind": "reject_once"},
        ],
    }
    assert reject_dsh_acp_permission(
        "session/request_permission", params, session_id="native-a"
    ) == {"outcome": {"outcome": "selected", "optionId": "deny"}}
    with pytest.raises(DshAcpProtocolError, match="unbound"):
        reject_dsh_acp_permission("session/request_permission", params, session_id="other")
    with pytest.raises(DshAcpProtocolError, match="Unsupported"):
        reject_dsh_acp_permission("elicitation/create", params, session_id="native-a")
