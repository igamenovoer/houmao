"""Qualify explicit unsupported ACP operations against the pinned native executable."""

import json
from pathlib import Path
import time
from typing import Any

import pytest

from houmao.agents.realm_controller.backends.dsh_acp_connection import DshAcpRequestError
from tests.integration.agents.dsh.test_native_companion import _launch_native


def test_native_acp_fork_request_is_unsupported_without_another_conversation(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """An unsupported native fork fails explicitly and cannot substitute a new session or prompt."""

    endpoint, requests = controlled_messages_server
    connection, _ = _launch_native(dsh_executable, tmp_path, endpoint)
    try:
        connection.request("initialize", {"protocolVersion": 1, "clientCapabilities": {}}).result(
            30
        )
        selected = connection.request(
            "session/new", {"cwd": str(tmp_path), "mcpServers": []}
        ).result(20)
        native_id = selected["sessionId"]
        before = connection.request("session/list", {"cwd": str(tmp_path)}).result(20)
        with pytest.raises(DshAcpRequestError) as failure:
            connection.request("session/fork", {"sessionId": native_id}).result(20)
        assert failure.value.error["code"] == -32601
        after = connection.request("session/list", {"cwd": str(tmp_path)}).result(20)
        assert after == before
        assert requests == []
        connection.request("session/close", {"sessionId": native_id}).result(20)
    finally:
        connection.close(timeout=5)


def test_native_profile_edits_during_a_turn_remain_startup_only(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """An active native process keeps its loaded role/config when startup files change."""

    endpoint, requests = controlled_messages_server
    entered = tmp_path / "entered"
    release = tmp_path / "release"
    plugin = tmp_path / "controlled-step-gate.mjs"
    plugin.write_text("""
import { existsSync, writeFileSync } from 'node:fs';
import { setTimeout } from 'node:timers/promises';
export function apply(ctx, config) {
  ctx.on('agent/pre-step', async (_event, next) => {
    writeFileSync(config.entered, 'entered');
    while (!existsSync(config.release)) await setTimeout(5);
    return next();
  });
}
""")
    connection, _ = _launch_native(
        dsh_executable,
        tmp_path,
        endpoint,
        extra_plugins=[
            {
                "id": "controlled-step-gate",
                "name": str(plugin),
                "config": {"entered": str(entered), "release": str(release)},
            }
        ],
    )
    original_pid = connection.process.pid
    try:
        connection.request("initialize", {"protocolVersion": 1, "clientCapabilities": {}}).result(
            30
        )
        selected = connection.request(
            "session/new", {"cwd": str(tmp_path), "mcpServers": []}
        ).result(20)
        native_id = selected["sessionId"]
        pending = connection.request(
            "session/prompt",
            {
                "sessionId": native_id,
                "prompt": [{"type": "text", "text": "controlled startup-only work"}],
            },
        )
        deadline = time.monotonic() + 15
        while not entered.is_file():
            assert time.monotonic() < deadline, (
                "Native prompt did not reach its controlled active step"
            )
            if pending.done():
                pending.result()
                pytest.fail("Native prompt settled before the active-step gate")
            time.sleep(0.02)
        assert requests == []
        (tmp_path / "create/role.txt").write_text("CHANGED_ROLE_REQUIRES_EXPLICIT_RESTART")
        (tmp_path / "create/patch.json").write_text("[]")
        assert not pending.done()
        release.write_text("release")
        assert pending.result(30)["stopReason"] == "end_turn"
        assert connection.process.pid == original_pid and connection.process.poll() is None
        assert len(requests) == 1
        system = json.dumps(requests[0]["system"])
        assert "Houmao literal {{example}}" in system
        assert "CHANGED_ROLE_REQUIRES_EXPLICIT_RESTART" not in system
        connection.request("session/close", {"sessionId": native_id}).result(20)
    finally:
        release.write_text("release")
        connection.close(timeout=5)
