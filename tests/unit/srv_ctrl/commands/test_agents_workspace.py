from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from click.testing import CliRunner

from houmao.srv_ctrl.commands.agents import workspace as workspace_commands
from houmao.srv_ctrl.commands.main import cli
from houmao.srv_ctrl.commands.managed_agents import ManagedAgentTarget


def _json_payload(output: str) -> dict[str, Any]:
    """Decode one CLI JSON payload."""

    return cast(dict[str, Any], json.loads(output))


def _local_workspace_target(tmp_path: Path, *, persist_enabled: bool = True) -> ManagedAgentTarget:
    """Build one local managed-agent target with manifest-backed workspace fields."""

    workspace_root = (tmp_path / ".houmao" / "memory" / "agents" / "agent-123").resolve()
    persist_dir = (workspace_root / "persist").resolve() if persist_enabled else None
    controller = SimpleNamespace(
        workspace_root=workspace_root,
        memo_file=(workspace_root / "houmao-memo.md").resolve(),
        scratch_dir=(workspace_root / "scratch").resolve(),
        persist_binding="auto" if persist_enabled else "disabled",
        persist_dir=persist_dir,
    )
    controller.scratch_dir.mkdir(parents=True, exist_ok=True)
    controller.memo_file.parent.mkdir(parents=True, exist_ok=True)
    controller.memo_file.touch()
    if persist_dir is not None:
        persist_dir.mkdir(parents=True, exist_ok=True)
    return ManagedAgentTarget(
        mode="local",
        agent_ref="agent-123",
        identity=cast(Any, SimpleNamespace(agent_id="agent-123")),
        controller=cast(Any, controller),
    )


def test_workspace_cli_memo_and_file_operations(
    monkeypatch,
    tmp_path: Path,
) -> None:
    target = _local_workspace_target(tmp_path)
    monkeypatch.setattr(
        workspace_commands,
        "resolve_managed_agent_target",
        lambda **kwargs: target,
    )
    runner = CliRunner()

    path_result = runner.invoke(
        cli,
        ["--print-json", "agents", "workspace", "path", "--agent-id", "agent-123"],
    )
    assert path_result.exit_code == 0
    path_payload = _json_payload(path_result.output)
    assert path_payload["workspace_root"] == str(target.controller.workspace_root)
    assert path_payload["persist_binding"] == "auto"

    set_result = runner.invoke(
        cli,
        [
            "--print-json",
            "agents",
            "workspace",
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
            "workspace",
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
            "workspace",
            "write",
            "--agent-id",
            "agent-123",
            "--lane",
            "scratch",
            "--path",
            "notes/todo.txt",
            "--content",
            "one",
        ],
    )
    assert write_result.exit_code == 0
    assert _json_payload(write_result.output)["action"] == "write_file"

    append_file_result = runner.invoke(
        cli,
        [
            "--print-json",
            "agents",
            "workspace",
            "append",
            "--agent-id",
            "agent-123",
            "--lane",
            "scratch",
            "--path",
            "notes/todo.txt",
            "--content",
            "\ntwo",
        ],
    )
    assert append_file_result.exit_code == 0

    read_result = runner.invoke(
        cli,
        [
            "--print-json",
            "agents",
            "workspace",
            "read",
            "--agent-id",
            "agent-123",
            "--lane",
            "scratch",
            "--path",
            "notes/todo.txt",
        ],
    )
    assert read_result.exit_code == 0
    assert _json_payload(read_result.output)["content"] == "one\ntwo"

    tree_result = runner.invoke(
        cli,
        [
            "--print-json",
            "agents",
            "workspace",
            "tree",
            "--agent-id",
            "agent-123",
            "--lane",
            "scratch",
        ],
    )
    assert tree_result.exit_code == 0
    assert [entry["path"] for entry in _json_payload(tree_result.output)["entries"]] == [
        "notes",
        "notes/todo.txt",
    ]

    delete_result = runner.invoke(
        cli,
        [
            "--print-json",
            "agents",
            "workspace",
            "delete",
            "--agent-id",
            "agent-123",
            "--lane",
            "scratch",
            "--path",
            "notes/todo.txt",
        ],
    )
    assert delete_result.exit_code == 0
    assert _json_payload(delete_result.output)["action"] == "delete_path"

    clear_result = runner.invoke(
        cli,
        [
            "--print-json",
            "agents",
            "workspace",
            "clear",
            "--agent-id",
            "agent-123",
            "--lane",
            "scratch",
            "--dry-run",
        ],
    )
    assert clear_result.exit_code == 0
    assert "would clear workspace lane" in _json_payload(clear_result.output)["detail"]


def test_workspace_cli_reports_disabled_persist_lane(
    monkeypatch,
    tmp_path: Path,
) -> None:
    target = _local_workspace_target(tmp_path, persist_enabled=False)
    monkeypatch.setattr(
        workspace_commands,
        "resolve_managed_agent_target",
        lambda **kwargs: target,
    )

    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "agents",
            "workspace",
            "tree",
            "--agent-id",
            "agent-123",
            "--lane",
            "persist",
        ],
    )

    assert result.exit_code == 1
    assert "persist lane is disabled" in result.output
