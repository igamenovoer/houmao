"""Qualify packaged companion hooks against the explicitly selected native DSH build."""

import json
import os
from pathlib import Path
from typing import Any

import pytest

from houmao.agents.dsh_configuration import DshEffectiveToolParams, prepare_dsh_home
from houmao.agents.realm_controller.backends.dsh_acp_connection import DshAcpConnection


def _launch_native(
    executable: Path,
    root: Path,
    endpoint: str,
    *,
    session_id: str | None = None,
    attempt_name: str | None = None,
    abandoned_message_ids: list[str] | None = None,
    extra_plugins: list[dict[str, Any]] | None = None,
    adapter: str = "deepseek",
) -> tuple[DshAcpConnection, Path]:
    """Launch a real native ACP runtime with isolated roots and the shipped module."""

    attempt = root / (attempt_name or ("resume" if session_id else "create"))
    attempt.mkdir()
    role = "Houmao literal {{example}} $HOME `code`\nkeep native guidance"
    role_file = attempt / "role.txt"
    role_file.write_text(role)
    evidence = attempt / "evidence.jsonl"
    control = {
        "version": 1,
        "attempt_id": attempt.name,
        "runtime_session_id": "qualification",
        "generation": "qualified-generation",
        "expected_native_session_id": session_id,
        "evidence_path": str(evidence),
        "abandoned_message_ids": abandoned_message_ids or [],
    }
    control_file = attempt / "control.json"
    control_file.write_text(json.dumps(control))
    asset = (
        Path(__file__).resolve().parents[4] / "src/houmao/agents/assets/dsh/managed-companion.mjs"
    )
    setup = DshEffectiveToolParams.from_mapping(
        {
            "provider": {
                "adapter": adapter,
                "protocol": "messages" if adapter == "deepseek" else "openai-completions",
                "route": "deepseek-official" if adapter == "deepseek" else "houmao-controlled",
                "base_url_env": "DSH_SYNTHETIC_ENDPOINT",
                "api_key_env": "DSH_SYNTHETIC_KEY",
            },
            "models": [
                {
                    "id": "controlled",
                    "context_window": 8192,
                    "max_output_tokens": 128,
                    "reasoning_efforts": False,
                }
            ],
        }
    )
    prepared = prepare_dsh_home(
        root / "dsh-home",
        setup,
        {
            "PATH": os.environ["PATH"],
            "HOME": str(root / "user-home"),
            "DSH_SYNTHETIC_KEY": "synthetic-local-only",
            "DSH_SYNTHETIC_ENDPOINT": endpoint,
        },
        role,
    )
    patch = json.loads(prepared.patch_path.read_text())
    patch.extend(
        [
            {
                "insert": [
                    {
                        "id": "houmao-managed",
                        "name": str(asset),
                        "config": {
                            "roleFile": str(role_file),
                            "controlFile": str(control_file),
                        },
                    }
                ]
            },
        ]
    )
    if extra_plugins:
        patch.append({"insert": extra_plugins})
    patch_file = attempt / "patch.json"
    patch_file.write_text(json.dumps(patch))
    connection = DshAcpConnection.from_command(
        [str(executable), "--profile", "acp", "--patch", str(patch_file)],
        cwd=root,
        env=prepared.environment,
    )
    return connection, evidence


@pytest.mark.parametrize("adapter", ["deepseek", "pi-ai"])
def test_native_module_literal_prompt_and_exact_resume(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    adapter: str,
) -> None:
    """Prove module loading, prompt semantics, admission evidence, and raw journal format."""

    endpoint, requests = controlled_messages_server
    native_id = None
    all_rows = []
    for _ in range(2):
        connection, evidence = _launch_native(
            dsh_executable, tmp_path, endpoint, session_id=native_id, adapter=adapter
        )
        try:
            initialized = connection.request(
                "initialize",
                {
                    "protocolVersion": 1,
                    "clientCapabilities": {},
                    "clientInfo": {"name": "houmao-native-qualification", "version": "1"},
                },
            ).result(timeout=45)
            assert initialized["agentCapabilities"]["sessionCapabilities"]["resume"] is not None
            selected = connection.request(
                "session/resume" if native_id else "session/new",
                {
                    "cwd": str(tmp_path),
                    "mcpServers": [],
                    **({"sessionId": native_id} if native_id else {}),
                },
            ).result(timeout=20)
            native_id = selected.get("sessionId", native_id)
            assert native_id
            result = connection.request(
                "session/prompt",
                {
                    "sessionId": native_id,
                    "prompt": [{"type": "text", "text": "controlled work"}],
                },
            ).result(timeout=30)
            assert result["stopReason"] == "end_turn"
            connection.request("session/close", {"sessionId": native_id}).result(timeout=20)
        except Exception as error:
            raise AssertionError(f"Native conformance failed: {connection.diagnostics}") from error
        finally:
            connection.close(timeout=5)
        rows = [json.loads(line) for line in evidence.read_text().splitlines()]
        all_rows.extend(rows)
        assert {"loaded", "created", "admitted", "claimed", "turn/start", "turn/end"} <= {
            row["event"] for row in rows
        }
        assert all(row["native_session_id"] in (None, native_id) for row in rows)
    assert len(requests) == 2
    for request in requests:
        system = json.dumps(
            request.get(
                "system",
                [message for message in request["messages"] if message["role"] == "system"],
            ),
            ensure_ascii=False,
        )
        assert "Houmao literal {{example}} $HOME `code`" in system
        assert "DeepSeek Harness" in system
        assert request["tools"], "Native tool guidance/schema must remain present"
    journals = list((tmp_path / "dsh-home/sessions").rglob("session.v4.jsonl"))
    assert len(journals) == 1
    lines = [json.loads(line) for line in journals[0].read_text().splitlines()]
    assert lines[0]["type"] == "session"
    assert lines[0]["version"] == 4
    assert lines[0]["id"] == native_id
    assert {"turn/start", "assistant/message", "turn/end"} <= {line["type"] for line in lines[1:]}


def test_native_pending_input_is_reconciled_before_activation(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Preserve a failed initialization's native inbox and remove only proven input."""

    endpoint, requests = controlled_messages_server
    session_file = tmp_path / "seeded-session.txt"
    seed_plugin = tmp_path / "seed-pending.mjs"
    seed_plugin.write_text(
        """
import { writeFileSync } from 'node:fs';
export const inject = ['agents', 'sessions', 'sessionPersistence'];
export function apply(ctx, config) {
  ctx.on('agent/created', async ({agent}) => {
    agent.inbox.append('next-turn', {
      id: 'abandoned-native-input', role: 'user', source: {kind: 'user'},
      content: [{type: 'text', text: 'ABANDONED INPUT MUST NEVER EXECUTE'}],
    });
    await ctx.sessions.flush(agent.session);
    writeFileSync(config.sessionFile, agent.session.id);
    throw new Error('controlled initialization failure before native activation');
  });
}
"""
    )
    connection, _ = _launch_native(
        dsh_executable,
        tmp_path,
        endpoint,
        attempt_name="seed",
        extra_plugins=[
            {
                "id": "controlled-pending-seed",
                "name": str(seed_plugin),
                "config": {"sessionFile": str(session_file)},
            }
        ],
    )
    try:
        connection.request("initialize", {"protocolVersion": 1, "clientCapabilities": {}}).result(
            30
        )
        with pytest.raises(Exception) as failure:
            connection.request("session/new", {"cwd": str(tmp_path), "mcpServers": []}).result(20)
        assert session_file.exists(), getattr(failure.value, "error", str(failure.value))
        native_id = session_file.read_text()
    finally:
        connection.close(timeout=5)
    assert requests == []

    connection, evidence = _launch_native(
        dsh_executable, tmp_path, endpoint, session_id=native_id, attempt_name="unknown-refused"
    )
    try:
        connection.request("initialize", {"protocolVersion": 1, "clientCapabilities": {}}).result(
            30
        )
        with pytest.raises(Exception):
            connection.request(
                "session/resume",
                {
                    "cwd": str(tmp_path),
                    "mcpServers": [],
                    "sessionId": native_id,
                },
            ).result(20)
    finally:
        connection.close(timeout=5)
    rows = [json.loads(line) for line in evidence.read_text().splitlines()]
    assert "unreconciled" in {row["event"] for row in rows}
    assert requests == []

    connection, evidence = _launch_native(
        dsh_executable,
        tmp_path,
        endpoint,
        session_id=native_id,
        attempt_name="known-reconciled",
        abandoned_message_ids=["abandoned-native-input"],
    )
    try:
        connection.request("initialize", {"protocolVersion": 1, "clientCapabilities": {}}).result(
            30
        )
        connection.request(
            "session/resume",
            {
                "cwd": str(tmp_path),
                "mcpServers": [],
                "sessionId": native_id,
            },
        ).result(20)
        assert requests == []
        connection.request(
            "session/prompt",
            {
                "sessionId": native_id,
                "prompt": [{"type": "text", "text": "fresh explicit work"}],
            },
        ).result(30)
        connection.request("session/close", {"sessionId": native_id}).result(20)
    finally:
        connection.close(timeout=5)
    rows = [json.loads(line) for line in evidence.read_text().splitlines()]
    events = [row["event"] for row in rows]
    assert events.index("reconciled") < events.index("created") < events.index("admitted")
    assert len(requests) == 1
    assert "ABANDONED INPUT MUST NEVER EXECUTE" not in json.dumps(
        [request["messages"] for request in requests]
    )
    assert not any(
        row["event"] == "claimed" and row["message_id"] == "abandoned-native-input" for row in rows
    )
