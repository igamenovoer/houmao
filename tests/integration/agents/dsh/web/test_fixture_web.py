"""Qualify raw and managed generic Web fixture lanes against controlled native hosts."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import time
from typing import Any

import pytest

from houmao.agents.realm_controller.backends.dsh_web_client import DshWebClient
from tests.integration.agents.dsh.web.browser import NativeBrowser


@pytest.mark.parametrize("case", ["cloud-api", "self-hosted"])
@pytest.mark.parametrize("surface", ["raw", "manager"])
def test_native_web_fixture_keeps_one_browser_api_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
    case: str,
    surface: str,
) -> None:
    """Reuse exact explicit routes and keep browser work visible before another API prompt."""

    repo = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(repo / "scripts/agents/test-fixtures"))
    config_tools = importlib.import_module("fixturelib.config")
    prepare = importlib.import_module("fixturelib.prepare")
    launch = importlib.import_module("fixturelib.launch")
    web = importlib.import_module("fixturelib.web")
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
    config = config_tools.resolve_config(
        case=case, client="dsh", mode="tui", surface=surface, process_env=selected
    )
    prepared = prepare.prepare_run(
        config, run_root=tmp_path / "runs", executable=str(dsh_executable)
    )
    root = Path(prepared["run_dir"])
    browser: NativeBrowser | None = None
    observer: DshWebClient | None = None
    try:
        launch.launch_run(root, prompt="Fixture first Web marker", timeout=45)
        launch.prompt_run(root, prompt="Fixture second Web marker", timeout=45)
        run = prepare.load_run(root)
        if surface == "raw":
            state = run["raw_web_state"]
        else:
            state = json.loads(Path(run["identity"]["manifest_path"]).read_text())["backend_state"]
        identity = state["web_identity"]
        connection_file = web.browser_connection_file(run)
        private = json.loads(connection_file.read_text())
        assert private["native_session_id"] == identity["native_session_id"]
        observer = DshWebClient.from_connection(
            private["origin"], launch_token=private["launch_token"]
        )
        browser = NativeBrowser.from_connection_file(connection_file)
        assert browser.metadata["session_id"] == identity["native_session_id"]
        browser.call("contains", text="Fixture first Web marker")
        browser.call("contains", text="Fixture second Web marker")
        browser.call("submit", text="Fixture human Web marker")
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            snapshot = observer.state(identity)
            if (snapshot["last_turn"] or {}).get("turn", 0) >= 3 and snapshot["admission"][
                "ready_only"
            ]:
                break
            time.sleep(0.02)
        else:
            raise AssertionError("Browser fixture turn did not settle")
        final = launch.prompt_run(root, prompt="Fixture final API marker", timeout=45)
        assert observer.state(identity)["identity"] == identity
        assert len(requests) == 4
        assert "Fixture human Web marker" in json.dumps(requests[3]["messages"])
        assert "Fixture first Web marker" in json.dumps(requests[3]["messages"])
        report = (root / "report.json").read_text()
        assert "synthetic-local-key" not in report
        assert private["launch_token"] not in report
        assert "bootstrap_path" not in report
        assert "cookie_path" not in report
        assert len(final["turns"]) == 3
        if surface == "manager":
            records = launch.check_run(root, live=True)["usage"]["records"]
            assert len(records) == 4
            assert (
                len([record for record in records if record["turn_origin"] == "native_observed"])
                == 1
            )
            immutable = {record["record_id"]: record for record in records}
            browser.close()
            observer.close()
            browser = observer = None
            prepare.manager_root_call(
                [
                    "agents",
                    "single",
                    "--agent-id",
                    run["identity"]["agent_id"],
                    "relaunch",
                    "--chat-session-mode",
                    "exact",
                    "--chat-session-id",
                    identity["native_session_id"],
                ],
                env=launch.run_environment(run),
            )
            restored_manifest = json.loads(Path(run["identity"]["manifest_path"]).read_text())
            restored = restored_manifest["backend_state"]["web_identity"]
            assert restored["native_session_id"] == identity["native_session_id"]
            assert restored["runtime_session_id"] == identity["runtime_session_id"]
            assert restored["generation"] != identity["generation"]
            assert restored["host_incarnation"] != identity["host_incarnation"]
            assert restored["agent_incarnation"] != identity["agent_incarnation"]
            assert len(requests) == 4
            launch.prompt_run(root, prompt="Fixture post-relaunch API marker", timeout=45)
            assert len(requests) == 5
            assert "Fixture first Web marker" in json.dumps(requests[4]["messages"])
            assert "Fixture human Web marker" in json.dumps(requests[4]["messages"])
            refreshed = launch.check_run(root, live=True)["usage"]["records"]
            assert len(refreshed) == 5
            assert all(
                record == immutable[record["record_id"]]
                for record in refreshed
                if record["record_id"] in immutable
            )
    finally:
        if browser is not None:
            browser.close()
        if observer is not None:
            observer.close()
        launch.stop_run(root)
