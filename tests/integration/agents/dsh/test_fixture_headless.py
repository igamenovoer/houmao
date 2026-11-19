"""Qualify native one-shot fixture workflows against a controlled local provider."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import pytest


@pytest.mark.parametrize("case", ["cloud-api", "self-hosted"])
@pytest.mark.parametrize("surface", ["raw", "manager"])
def test_native_fixture_exact_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    case: str,
    surface: str,
) -> None:
    """Both explicit protocols preserve one native conversation across DSH workers."""

    repo = Path(__file__).resolve().parents[4]
    monkeypatch.syspath_prepend(str(repo / "scripts/agents/test-fixtures"))
    configuration = importlib.import_module("fixturelib.config")
    prepare = importlib.import_module("fixturelib.prepare")
    launch = importlib.import_module("fixturelib.launch")
    endpoint, requests = controlled_messages_server
    prefix = "HOUMAO_TEST_CLOUD" if case == "cloud-api" else "HOUMAO_TEST_SELF_HOSTED"
    selected = {
        prefix + "_MODEL": "controlled",
        prefix + "_CONTEXT_WINDOW": "8192",
        prefix + "_MAX_OUTPUT_TOKENS": "128",
        prefix + "_DSH_REASONING": "false",
    }
    if case == "cloud-api":
        selected.update(
            {"DEEPSEEK_API_KEY": "synthetic-local-key", "DEEPSEEK_BASE_URL_ANTHROPIC": endpoint}
        )
    else:
        selected[prefix + "_OPENAI_BASE_URL"] = endpoint
        monkeypatch.setenv("OPENAI_API_KEY", "synthetic-unselected-ambient-key")
    config = configuration.resolve_config(
        case=case, client="dsh", mode="headless", surface=surface, process_env=selected
    )
    run = prepare.prepare_run(config, run_root=tmp_path / "runs", executable=str(dsh_executable))
    root = Path(run["run_dir"])
    try:
        first = launch.launch_run(root, prompt="first fixture turn", timeout=45)
        assert first["backend"] == "dsh_headless"
        if surface == "raw":
            native_id = first["identity"]["provider_session_id"]
            home = root / "home"
        else:
            manifest = json.loads(Path(first["identity"]["manifest_path"]).read_text())
            assert manifest["backend"] == "dsh_headless"
            argv = manifest["launch_plan"]["args"]
            assert argv[:2] == ["--profile", "headless"] and "--json" in argv
            assert argv.index("--patch") < argv.index("--json")
            assert "first fixture turn" not in argv and "--session-id" not in argv
            native_id = manifest["headless"]["session_id"]
            home = Path(manifest["launch_plan"]["home_selector"]["home_path"])
        second = launch.prompt_run(root, prompt="second fixture turn", timeout=45)
        if surface == "raw":
            assert native_id == second["identity"]["provider_session_id"]
        else:
            manifest = json.loads(Path(second["identity"]["manifest_path"]).read_text())
            assert native_id == manifest["headless"]["session_id"]
        assert len(second["turns"]) == len(requests) == 2
        assert all(
            row["_fixture_placeholder_authorization"] == (case == "self-hosted") for row in requests
        )
        assert "first fixture turn" in json.dumps(requests[1]["messages"])
        journals = list((home / "sessions").rglob("session.v4.jsonl"))
        assert len(journals) == 1
        assert json.loads(journals[0].read_text().splitlines()[0])["id"] == native_id
        if surface == "raw":
            workers = prepare.load_run(root)["raw_workers"]
            assert len(workers) == 2 and workers[0] != workers[1]
            captures = sorted(root.glob("raw-turn-*.jsonl"))
            logs = sorted(root.glob("raw-turn-*.stderr"))
        else:
            artifact_root = Path(second["identity"]["manifest_path"]).with_suffix(".turn-artifacts")
            captures = sorted(artifact_root.glob("*/stdout.jsonl"))
            logs = sorted(artifact_root.glob("*/stderr.log"))
            handoffs = [
                json.loads(path.read_text())
                for path in artifact_root.glob("*/dsh-native-handoff.json")
            ]
            assert len(handoffs) == 2
            assert {row["native_session_id"] for row in handoffs} == {native_id}
            assert len({(row["process_id"], row["process_birth_token"]) for row in handoffs}) == 2
            assert len(second["usage"]["records"]) == 2
            assert all(
                record["token_usage"]["total_tokens"]["value"] == 16
                for record in second["usage"]["records"]
            )
        assert len(captures) == len(logs) == 2
        for capture in captures:
            rows = [json.loads(line) for line in capture.read_text().splitlines()]
            assert rows[0]["type"] == "session" and rows[0]["sessionId"] == native_id
            assert rows[-1]["type"] == "final" and rows[-1]["reason"]["kind"] == "completed"
        assert all(
            "composed sandbox and approval defaults match no preset" not in path.read_text().lower()
            for path in logs
        )
        assert "synthetic-local-key" not in (root / "report.json").read_text()
    finally:
        launch.stop_run(root)
