"""Qualify real ACP fixture workflows against a controlled local provider."""

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
    """Both explicit protocols preserve one native conversation across driver processes."""

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
        selected.update(
            {prefix + "_API_KEY": "synthetic-local-key", prefix + "_OPENAI_BASE_URL": endpoint}
        )
    config = configuration.resolve_config(
        case=case, client="dsh", surface=surface, process_env=selected
    )
    run = prepare.prepare_run(config, run_root=tmp_path / "runs", executable=str(dsh_executable))
    root = Path(run["run_dir"])
    try:
        first = launch.launch_run(root, prompt="first fixture turn", timeout=45)
        if surface == "raw":
            native_id = first["identity"]["provider_session_id"]
            home = root / "home"
        else:
            manifest = json.loads(Path(first["identity"]["manifest_path"]).read_text())
            native_id = manifest["headless"]["session_id"]
            home = Path(manifest["launch_plan"]["home_selector"]["home_path"])
        second = launch.prompt_run(root, prompt="second fixture turn", timeout=45)
        if surface == "raw":
            assert native_id == second["identity"]["provider_session_id"]
        else:
            manifest = json.loads(Path(second["identity"]["manifest_path"]).read_text())
            assert native_id == manifest["headless"]["session_id"]
        assert len(second["turns"]) == len(requests) == 2
        assert "first fixture turn" in json.dumps(requests[1]["messages"])
        journals = list((home / "sessions").rglob("session.v4.jsonl"))
        assert len(journals) == 1
        assert json.loads(journals[0].read_text().splitlines()[0])["id"] == native_id
        if surface == "raw":
            for index in (1, 2):
                assert (root / "raw-turns" / f"turn-{index}" / "provider-stdout.jsonl").is_file()
        else:
            assert len(second["usage"]["records"]) == 2
            assert all(
                record["token_usage"]["total_tokens"]["value"] == 16
                for record in second["usage"]["records"]
            )
        assert "synthetic-local-key" not in (root / "report.json").read_text()
    finally:
        launch.stop_run(root)
