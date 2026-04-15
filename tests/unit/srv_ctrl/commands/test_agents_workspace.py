from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from click.testing import CliRunner

from houmao.srv_ctrl.commands.agents import workspace as memory_commands
from houmao.srv_ctrl.commands.main import cli
from houmao.srv_ctrl.commands.managed_agents import ManagedAgentTarget


def _json_payload(output: str) -> dict[str, Any]:
    """Decode one CLI JSON payload."""

    return cast(dict[str, Any], json.loads(output))


def _local_memory_target(tmp_path: Path) -> ManagedAgentTarget:
    """Build one local managed-agent target with manifest-backed memory fields."""

    memory_root = (tmp_path / ".houmao" / "memory" / "agents" / "agent-123").resolve()
    controller = SimpleNamespace(
        memory_root=memory_root,
        memo_file=(memory_root / "houmao-memo.md").resolve(),
        pages_dir=(memory_root / "pages").resolve(),
    )
    controller.pages_dir.mkdir(parents=True, exist_ok=True)
    controller.memo_file.parent.mkdir(parents=True, exist_ok=True)
    controller.memo_file.touch()
    return ManagedAgentTarget(
        mode="local",
        agent_ref="agent-123",
        identity=cast(Any, SimpleNamespace(agent_id="agent-123")),
        controller=cast(Any, controller),
    )


def test_memory_cli_memo_page_and_resolve_operations(monkeypatch, tmp_path: Path) -> None:
    target = _local_memory_target(tmp_path)
    monkeypatch.setattr(
        memory_commands,
        "resolve_managed_agent_target",
        lambda **kwargs: target,
    )
    runner = CliRunner()

    path_result = runner.invoke(
        cli,
        ["--print-json", "agents", "memory", "path", "--agent-id", "agent-123"],
    )
    assert path_result.exit_code == 0
    path_payload = _json_payload(path_result.output)
    assert path_payload["memory_root"] == str(target.controller.memory_root)
    assert path_payload["pages_dir"] == str(target.controller.pages_dir)

    set_result = runner.invoke(
        cli,
        [
            "--print-json",
            "agents",
            "memory",
            "memo",
            "set",
            "--agent-id",
            "agent-123",
            "--content",
            "memo",
        ],
    )
    assert set_result.exit_code == 0
    assert _json_payload(set_result.output)["content"] == "memo"

    append_result = runner.invoke(
        cli,
        [
            "--print-json",
            "agents",
            "memory",
            "memo",
            "append",
            "--agent-id",
            "agent-123",
            "--content",
            "\nmore",
        ],
    )
    assert append_result.exit_code == 0
    assert _json_payload(append_result.output)["content"] == "memo\nmore"

    write_result = runner.invoke(
        cli,
        [
            "--print-json",
            "agents",
            "memory",
            "write",
            "--agent-id",
            "agent-123",
            "--path",
            "notes/todo.txt",
            "--content",
            "one",
        ],
    )
    assert write_result.exit_code == 0
    write_payload = _json_payload(write_result.output)
    assert write_payload["action"] == "write_page"
    assert write_payload["relative_link"] == "pages/notes/todo.txt"
    assert write_payload["absolute_path"] == str(target.controller.pages_dir / "notes" / "todo.txt")

    append_file_result = runner.invoke(
        cli,
        [
            "--print-json",
            "agents",
            "memory",
            "append",
            "--agent-id",
            "agent-123",
            "--path",
            "notes/todo.txt",
            "--content",
            "\ntwo",
        ],
    )
    assert append_file_result.exit_code == 0

    resolve_result = runner.invoke(
        cli,
        [
            "--print-json",
            "agents",
            "memory",
            "resolve",
            "--agent-id",
            "agent-123",
            "--path",
            "notes/todo.txt",
        ],
    )
    assert resolve_result.exit_code == 0
    resolve_payload = _json_payload(resolve_result.output)
    assert resolve_payload["path"] == "notes/todo.txt"
    assert resolve_payload["relative_link"] == "pages/notes/todo.txt"
    assert resolve_payload["exists"] is True
    assert resolve_payload["kind"] == "file"

    read_result = runner.invoke(
        cli,
        [
            "--print-json",
            "agents",
            "memory",
            "read",
            "--agent-id",
            "agent-123",
            "--path",
            "notes/todo.txt",
        ],
    )
    assert read_result.exit_code == 0
    read_payload = _json_payload(read_result.output)
    assert read_payload["content"] == "one\ntwo"
    assert read_payload["relative_link"] == "pages/notes/todo.txt"

    tree_result = runner.invoke(
        cli,
        ["--print-json", "agents", "memory", "tree", "--agent-id", "agent-123"],
    )
    assert tree_result.exit_code == 0
    assert [entry["path"] for entry in _json_payload(tree_result.output)["entries"]] == [
        "notes",
        "notes/todo.txt",
    ]
    assert _json_payload(tree_result.output)["entries"][1]["relative_link"] == (
        "pages/notes/todo.txt"
    )

    delete_result = runner.invoke(
        cli,
        [
            "--print-json",
            "agents",
            "memory",
            "delete",
            "--agent-id",
            "agent-123",
            "--path",
            "notes/todo.txt",
        ],
    )
    assert delete_result.exit_code == 0
    delete_payload = _json_payload(delete_result.output)
    assert delete_payload["action"] == "delete_page"
    assert delete_payload["relative_link"] == "pages/notes/todo.txt"

    reindex_result = runner.invoke(
        cli,
        ["--print-json", "agents", "memory", "reindex", "--agent-id", "agent-123"],
    )
    assert reindex_result.exit_code != 0
