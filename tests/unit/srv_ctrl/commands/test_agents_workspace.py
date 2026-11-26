from __future__ import annotations

from dataclasses import replace
from functools import partial
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from click.testing import CliRunner
import pytest

from houmao.agents.realm_controller.gateway_models import (
    GatewayMemoryMemoResponseV1,
    GatewayMemoryMemoWriteRequestV1,
)
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
        identity=cast(Any, SimpleNamespace(agent_id="agent-123", backend="local_interactive")),
        controller=cast(Any, controller),
    )


@pytest.mark.parametrize("style", ["plain", "fancy", "json"])
@pytest.mark.parametrize("route", ["self", "single", "pair"])
def test_memo_writes_acknowledge_one_operation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, route: str, style: str
) -> None:
    """The write receipt is safe to inspect without another write or a memo reread."""

    target = _local_memory_target(tmp_path / "[named-project]")
    assert target.controller is not None
    memo_file = target.controller.memo_file
    assert memo_file is not None
    pair_calls: list[str] = []

    def get_memo(agent_ref: str) -> GatewayMemoryMemoResponseV1:
        """Preserve the content-bearing pair read response."""

        assert agent_ref == "agent-123"
        pair_calls.append("show")
        return GatewayMemoryMemoResponseV1(
            memo_file=str(memo_file), content=memo_file.read_text(encoding="utf-8")
        )

    def write_memo(
        agent_ref: str, request: GatewayMemoryMemoWriteRequestV1, *, append: bool
    ) -> GatewayMemoryMemoResponseV1:
        """Simulate the existing full pair response for each accepted write."""

        assert agent_ref == "agent-123"
        pair_calls.append("append" if append else "set")
        with memo_file.open("a" if append else "w", encoding="utf-8") as stream:
            stream.write(request.content)
        return GatewayMemoryMemoResponseV1(
            memo_file=str(memo_file), content=memo_file.read_text(encoding="utf-8")
        )

    scope = ["agents", "single", "--agent-id", "agent-123"]
    if route == "self":
        scope = ["agents", "self"]
    elif route == "pair":
        target = replace(
            target,
            mode="server",
            client=cast(
                Any,
                SimpleNamespace(
                    put_managed_agent_gateway_memory_memo=partial(write_memo, append=False),
                    append_managed_agent_gateway_memory_memo=partial(write_memo, append=True),
                    get_managed_agent_gateway_memory_memo=get_memo,
                ),
            ),
            controller=None,
        )
    monkeypatch.setattr(memory_commands, "resolve_managed_agent_target", lambda **kwargs: target)
    monkeypatch.setenv("COLUMNS", "48")

    def unexpected_read(paths: Any) -> str:
        """Reject memo reads during acknowledgement."""

        pytest.fail(f"Memo write tried to read {paths.memo_file}")

    initial = "Private initial memo content."
    added = "\nOne appended line."
    runner = CliRunner()
    with monkeypatch.context() as write_context:
        write_context.setattr(memory_commands, "read_memo", unexpected_read)
        for operation, action, content in (
            ("set", "write_memo", initial),
            ("append", "append_memo", added),
        ):
            result = runner.invoke(
                cli, [f"--print-{style}", *scope, "memory", "memo", operation, "--content", content]
            )
            assert result.exit_code == 0, result.output
            if style == "json":
                assert _json_payload(result.output) == {
                    "success": True,
                    "action": action,
                    "memo_file": str(memo_file),
                }
            else:
                assert all(field in result.output for field in ("success", "action", "memo_file"))
                assert all(value in result.output for value in ("true", action, str(memo_file)))
            assert initial not in result.output
            assert added.strip() not in result.output

    shown = runner.invoke(cli, ["--print-json", *scope, "memory", "memo", "show"])
    assert shown.exit_code == 0, shown.output
    assert _json_payload(shown.output)["content"] == initial + added
    assert pair_calls == (["set", "append", "show"] if route == "pair" else [])


def test_memory_cli_page_and_resolve_operations(monkeypatch, tmp_path: Path) -> None:
    target = _local_memory_target(tmp_path)
    monkeypatch.setattr(
        memory_commands,
        "resolve_managed_agent_target",
        lambda **kwargs: target,
    )
    runner = CliRunner()

    path_result = runner.invoke(
        cli,
        ["--print-json", "agents", "single", "--agent-id", "agent-123", "memory", "path"],
    )
    assert path_result.exit_code == 0
    path_payload = _json_payload(path_result.output)
    assert path_payload["memory_root"] == str(target.controller.memory_root)
    assert path_payload["pages_dir"] == str(target.controller.pages_dir)

    write_result = runner.invoke(
        cli,
        [
            "--print-json",
            "agents",
            "single",
            "--agent-id",
            "agent-123",
            "memory",
            "write",
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
            "single",
            "--agent-id",
            "agent-123",
            "memory",
            "append",
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
            "single",
            "--agent-id",
            "agent-123",
            "memory",
            "resolve",
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
            "single",
            "--agent-id",
            "agent-123",
            "memory",
            "read",
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
        ["--print-json", "agents", "single", "--agent-id", "agent-123", "memory", "tree"],
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
            "single",
            "--agent-id",
            "agent-123",
            "memory",
            "delete",
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
        ["--print-json", "agents", "single", "--agent-id", "agent-123", "memory", "reindex"],
    )
    assert reindex_result.exit_code != 0
