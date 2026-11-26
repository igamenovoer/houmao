"""Guard maintained fixture consumers against machine-specific launch inputs."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
import runpy
import subprocess

import pytest


REPO = Path(__file__).resolve().parents[3]


def test_retired_local_credentials_remain_ignored() -> None:
    """Protect old operator state without reading or changing any credential file."""

    path = "tests/fixtures/auth-bundles/claude/operator-synthetic/files/.credentials.json"
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", path],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0 and result.stdout.strip() == path


def test_maintained_launch_inputs_have_no_account_specific_paths() -> None:
    """Seed configs and current guides cannot reintroduce personal fixture defaults."""

    roots = [
        "AGENTS.md",
        "docs",
        "scripts/agents",
        "scripts/demo",
        "scripts/explore",
        "src/houmao/project/assets/starter_agents",
    ]
    result = subprocess.run(
        ["git", "ls-files", "--", *roots], cwd=REPO, text=True, capture_output=True, check=True
    )
    for relative in result.stdout.splitlines():
        path = REPO / relative
        if (
            "/legacy/" in relative
            or not path.is_file()
            or path.suffix not in {".md", ".py", ".sh", ".json", ".toml", ".yaml"}
        ):
            continue
        text = path.read_text()
        assert "tests/fixtures/auth-bundles/" not in text, relative
        assert "yunwu-openai" not in text, relative
        assert "personal-a-default" not in text, relative


def test_instructional_launches_use_portable_model_inputs() -> None:
    """Keep model routing in the pool while allowing local services under test."""

    loopback = r"https?://(?:localhost|127(?:\.\d{1,3}){3}|\[::1\])(?::\d+)?"
    model_endpoint = re.compile(rf"{loopback}/(?:v1|models)\b", re.IGNORECASE)
    explicit_route = re.compile(r"\b(?:MODEL_URL|(?:MODEL_)?BASE_URL)\s*=|--base-url\b")
    local_dsh = re.compile(r"\btmp/dsh\b|node_modules/@deepseek-ai/dsh\b")
    for path in sorted((REPO / "tests/instructional").glob("*/README.md")):
        _, separator, after_launch = path.read_text().partition("\n## Launch\n")
        assert separator, path
        launch = after_launch.split("\n## ", maxsplit=1)[0]
        assert model_endpoint.search(launch) is None, path
        assert explicit_route.search(launch) is None, path
        assert local_dsh.search(launch) is None, path


@pytest.mark.parametrize("client", ["dsh", "kimi"])
def test_cccc_queue_proof_reads_successful_native_tool_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: str
) -> None:
    """Both Web journals must prove the queue steps ran in one native turn."""

    helpers = REPO / "tests/instructional/agent-cccc/helpers"
    monkeypatch.syspath_prepend(str(helpers))
    verifier = runpy.run_path(str(helpers / "verify_queue_access.py"))
    fence = "<<< BEGIN CCCC REQUEST >>> example"
    content = [{"type": "text", "text": fence}]
    commands = {
        "command": "\n".join(f"chat {op}" for op in ("peek", "pop", "ack", "pop-result", "reply"))
    }
    source = {"kind": "user"}
    if client == "dsh":
        turn = 7
        message = {
            "type": "user/message",
            "data": {"id": "message", "source": source, "content": content},
        }
        call = {
            "type": "tool/call",
            "data": {
                "callId": "call",
                "turn": turn,
                "name": "bash",
                "arguments": json.dumps(commands),
            },
        }
        result = {
            "type": "tool/result",
            "data": {"message": {"toolCallId": "call", "isError": False}},
        }
    else:
        turn = "7"
        message = {"type": "turn.prompt", "promptId": "prompt", "origin": source, "input": content}
        call = {
            "type": "context.append_loop_event",
            "event": {
                "type": "tool.call",
                "toolCallId": "call",
                "turnId": turn,
                "name": "Bash",
                "args": commands,
            },
        }
        result = {
            "type": "context.append_loop_event",
            "event": {"type": "tool.result", "toolCallId": "call", "result": {"output": "ok"}},
        }
    transcript = tmp_path / "b-transcript-0.jsonl"
    transcript.write_text("".join(f"{json.dumps(row)}\n" for row in (message, call, result)))
    assert verifier["_recipient_trace"](tmp_path) == (turn, [fence])

    transcript.write_text("".join(f"{json.dumps(row)}\n" for row in (message, call)))
    with pytest.raises(verifier["LabError"], match="Successful queue operations"):
        verifier["_recipient_trace"](tmp_path)


def test_transcript_capture_retains_selected_kimi_main_journal(tmp_path: Path) -> None:
    """Keep the launched Kimi session's evidence even if its child writes later."""

    helper_path = REPO / "tests/instructional/agent-mail-stalwart/helpers/mail_lab.py"
    helper = runpy.run_path(str(helper_path))
    run_dir = tmp_path / "fixture"
    agents = run_dir / "runtime/homes/session/agents"
    journal = agents / "main/wire.jsonl"
    journal.parent.mkdir(parents=True)
    journal.write_text('{"type":"turn.prompt"}\n')
    child_journal = agents / "child/wire.jsonl"
    child_journal.parent.mkdir()
    child_journal.write_text('{"type":"metadata"}\n')
    manifest = run_dir / "manifest.json"
    manifest.write_text(json.dumps({"backend_state": {"evidence_path": str(journal)}}))
    run = {
        "status": "launched",
        "configuration": {"client": "kimi"},
        "identity": {"agent_id": "agent", "manifest_path": str(manifest)},
    }
    (run_dir / "run.json").write_text(json.dumps(run))
    run_meta = tmp_path / "run-meta.json"
    run_meta.write_text(
        json.dumps(
            {"run_a": str(run_dir), "run_b": "peer", "mail": {"provider": "stalwart"}, "tag": "run"}
        )
    )
    output = tmp_path / "evidence"
    arguments = argparse.Namespace(run_meta=run_meta, role="a", output=output, max_files=1)

    assert helper["command_transcript"](arguments) == 0
    assert (output / "a-transcript-0.jsonl").read_bytes() == journal.read_bytes()

    cccc = runpy.run_path(str(REPO / "tests/instructional/agent-cccc/helpers/cccc_lab.py"))
    cuda = runpy.run_path(
        str(REPO / "tests/instructional/agent-cccc-cuda-coop/helpers/cuda_coop_lab.py")
    )
    assert cccc["session_files"](run_dir) == [child_journal, journal]
    assert cccc["session_files"](run_dir, main_only=True) == [journal]
    assert cuda["session_files"](run_dir, client="kimi") == [child_journal, journal]


def test_packaged_demo_does_not_import_fixture_utility_or_test_code() -> None:
    """Prepared inputs cross a data boundary rather than a production import dependency."""

    root = REPO / "src/houmao/demo/shared_tui_tracking_demo_pack"
    for path in root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                names = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not any(
                name.split(".")[0] in {"tests", "scripts", "fixturelib", "fixture"}
                for name in names
            ), path


def test_exploration_launchers_use_the_shared_prepared_run_interface() -> None:
    """Retained shell entrypoints expose current launch/prompt commands safely."""

    folder = REPO / "scripts/explore/interactive-pipeline-test"
    for name in ("interactive_pipeline_cao_claude.sh", "send_prompt.sh"):
        result = subprocess.run(
            ["bash", str(folder / name), "--help"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "--run-dir" in result.stdout
