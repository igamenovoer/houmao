"""Qualify native descendant continuation and disjoint accounting under controlled model traffic."""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from typing import Any

import pytest

from houmao.agents.realm_controller.backends.dsh_acp import DshAcpSession
from houmao.agents.realm_controller.models import HeadlessTurnSessionSelection
from houmao.agents.realm_controller.usage_adapters.dsh import (
    inspect_dsh_journal,
    select_dsh_journal,
)
from houmao.agents.realm_controller.usage_support import UsageService
from tests.integration.agents.dsh.test_managed_acp import _launch_plan


@dataclass
class _ControlledDelegation:
    """Keep synthetic endpoint synchronization separate from native identity evidence."""

    endpoint: str = ""
    requests: list[dict[str, Any]] = field(default_factory=list)
    root_requests: int = 0
    child_requests: int = 0
    delegation_tool: str = "subagent"
    delegation_sent: bool = False
    child_started: threading.Event = field(default_factory=threading.Event)
    release_child: threading.Event = field(default_factory=threading.Event)


@pytest.fixture
def controlled_delegation_server() -> Iterator[_ControlledDelegation]:
    """Return one genuine native delegation followed by a delayed controlled child result."""

    state = _ControlledDelegation()
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        """Serve deterministic Messages results and a real subagent tool request."""

        def do_POST(self) -> None:
            """Hold the child until the test observes the first native root turn's end."""

            assert self.path.endswith("/messages")
            body = json.loads(self.rfile.read(int(self.headers["content-length"])))
            last_user = next(
                message for message in reversed(body["messages"]) if message["role"] == "user"
            )
            user_content = json.dumps(last_user["content"])
            is_child = "CONTROLLED_CHILD_REQUEST" in user_content
            with lock:
                state.requests.append(body)
                if is_child:
                    state.child_requests += 1
                    call = state.child_requests
                else:
                    state.root_requests += 1
                    call = state.root_requests
                tool = (
                    not is_child
                    and not state.delegation_sent
                    and "Controlled root request" in user_content
                )
                if tool:
                    state.delegation_sent = True
            if is_child:
                state.child_started.set()
                assert state.release_child.wait(35), "The native child was never released"
            block = (
                {
                    "type": "tool_use",
                    "id": "controlled-delegation",
                    "name": state.delegation_tool,
                    "input": {},
                }
                if tool
                else {"type": "text", "text": ""}
            )
            delta = (
                {
                    "type": "input_json_delta",
                    "partial_json": json.dumps(
                        {
                            "description": "Controlled native child",
                            "name": "controlled-child",
                            "prompt": "CONTROLLED_CHILD_REQUEST",
                        }
                    ),
                }
                if tool
                else {
                    "type": "text_delta",
                    "text": "Controlled child completion"
                    if is_child
                    else "Controlled root completion",
                }
            )
            frames = [
                {
                    "type": "message_start",
                    "message": {
                        "id": f"controlled-{'child' if is_child else 'root'}-{call}",
                        "type": "message",
                        "role": "assistant",
                        "model": "controlled",
                        "content": [],
                        "usage": {
                            "input_tokens": 11,
                            "output_tokens": 0,
                            "cache_read_input_tokens": 0,
                            "cache_creation_input_tokens": 0,
                        },
                    },
                },
                {"type": "content_block_start", "index": 0, "content_block": block},
                {"type": "content_block_delta", "index": 0, "delta": delta},
                {"type": "content_block_stop", "index": 0},
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": "tool_use" if tool else "end_turn"},
                    "usage": {"output_tokens": 5},
                },
                {"type": "message_stop"},
            ]
            payload = "".join(
                f"event: {frame['type']}\ndata: {json.dumps(frame)}\n\n" for frame in frames
            ).encode()
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: Any) -> None:
            """Keep synthetic HTTP transport details outside acceptance output."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state.endpoint = f"http://127.0.0.1:{server.server_port}/v1"
    try:
        yield state
    finally:
        state.release_child.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _evidence(path: Path) -> list[dict[str, Any]]:
    """Read only complete native companion metadata records."""

    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text().splitlines(keepends=True)
        if line.endswith("\n")
    ]


@pytest.mark.parametrize("delegation_tool", ["subagent", "subagent_fork"])
def test_native_child_result_starts_a_second_root_turn_and_is_accounted_once(
    tmp_path: Path,
    dsh_executable: Path,
    isolated_tmux: Path,
    controlled_delegation_server: _ControlledDelegation,
    delegation_tool: str,
) -> None:
    """Preserve one managed interval across native roots and report the proven child separately."""

    state = controlled_delegation_server
    state.delegation_tool = delegation_tool
    plan, manifest = _launch_plan(tmp_path, dsh_executable, state.endpoint)
    session = DshAcpSession(
        launch_plan=plan, role_name="controlled", session_manifest_path=manifest
    )
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "delegation"
    baseline = int(delegation_tool == "subagent_fork")
    try:
        if baseline:
            session.send_prompt(
                "Earlier completed parent history", turn_artifact_dir_name="baseline"
            )
            payload = json.loads(manifest.read_text())
            payload["backend_state"] = {"session_id": session.state.session_id}
            manifest.write_text(json.dumps(payload))
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(
                session.send_prompt, "Controlled root request", turn_artifact_dir_name="delegation"
            )
            try:
                assert state.child_started.wait(20), (
                    "The native subagent tool did not create a child request"
                )
                deadline = time.monotonic() + 20
                while not any(
                    row.get("event") == "turn/end" and row.get("turn") == baseline + 1
                    for row in _evidence(turn_dir / "dsh-native-evidence.jsonl")
                ):
                    if pending.done():
                        pending.result()
                        pytest.fail("The managed prompt settled before its native child")
                    assert time.monotonic() < deadline, "First native root turn did not settle"
                    time.sleep(0.02)
                assert not pending.done()
            finally:
                state.release_child.set()
            events = pending.result(timeout=35)
        assert any(event.kind == "done" for event in events)
        rows = _evidence(turn_dir / "dsh-native-evidence.jsonl")
        roots = [row["turn"] for row in rows if row["event"] == "turn/start"]
        assert roots == [baseline + 1, baseline + 2]
        child_starts = [row for row in rows if row["event"] == "descendant/turn/start"]
        assert len(child_starts) == 1
        assert state.root_requests == baseline + 3
        assert state.child_requests == 1
        native_id = session.state.session_id
        assert native_id is not None
        payload = json.loads(manifest.read_text())
        payload["backend_state"] = {"session_id": native_id}
        manifest.write_text(json.dumps(payload))
        service = UsageService.from_manifest(manifest)
        page = service.get_usage()
        assert len(page.records) == baseline + 1
        record = next(record for record in page.records if record.turn_id == "delegation")
        assert record.token_usage.total_tokens.value == 48
        assert record.provider_turn_id is None
        assert record.subagent_accounting == "separate"
        assert len(record.subagent_usage) == 1
        child = record.subagent_usage[0]
        assert child.child_id == child_starts[0]["child_session_id"]
        assert child.included_in_parent is False
        assert child.token_usage.total_tokens.value == 16
        assert child.parent_turn_id == "delegation"
        if baseline:
            child_journal = select_dsh_journal(plan.home_path / "sessions", child.child_id)
            assert child_journal is not None
            info = inspect_dsh_journal(child_journal, child.child_id)
            assert info.seeded and info.inherited_cut_seq >= 0
            journal_rows = [json.loads(line) for line in child_journal.read_text().splitlines()]
            assert any(
                row.get("type") == "assistant/message"
                and row.get("seq", info.inherited_cut_seq + 1) <= info.inherited_cut_seq
                for row in journal_rows
            ), "Fork qualification requires a real inherited provider sample"
        first_record = record.model_dump_json()
        assert all(
            private not in first_record
            for private in (
                "CONTROLLED_CHILD_REQUEST",
                "Controlled child completion",
                str(plan.home_path),
            )
        )
        session.send_prompt(
            "Explicit later root request",
            turn_artifact_dir_name="later",
            session_selection=HeadlessTurnSessionSelection(mode="exact", session_id=native_id),
        )
        service.reconcile()
        later = service.get_usage(after=page.next_cursor)
        assert len(later.records) == 1
        assert later.records[0].token_usage.total_tokens.value == 16
        assert later.records[0].subagent_usage == []
        assert (
            next(
                record for record in service.get_usage().records if record.turn_id == "delegation"
            ).model_dump_json()
            == first_record
        )
        assert state.root_requests == baseline + 4 and state.child_requests == 1
    finally:
        state.release_child.set()
        session.configure_stop_force_cleanup(force_cleanup=True)
        session.terminate()
