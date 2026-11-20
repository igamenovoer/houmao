"""Qualify raw and managed generic Web fixture lanes against controlled native hosts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib
import json
from pathlib import Path
import subprocess
import threading
import time
from typing import Any

import httpx
import pytest

from houmao.agents.realm_controller.backends.dsh_web_client import DshWebClient
from tests.fixtures.gateway_access import FixtureProofAuth, fixture_admin_key
from tests.integration.agents.dsh.conftest import ControlledModelGate
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
        selected[prefix + "_OPENAI_BASE_URL"] = endpoint
        monkeypatch.setenv("OPENAI_API_KEY", "synthetic-unselected-ambient-key")
    config = config_tools.resolve_config(
        case=case, client="dsh", mode="web", surface=surface, process_env=selected
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
        observed = subprocess.run(
            launch._tmux_command(
                run,
                "display-message",
                "-p",
                "-t",
                run["identity"]["tmux_session_name"],
                "#{socket_path}",
            ),
            env=launch.run_environment(run),
            capture_output=True,
            text=True,
            check=True,
        )
        assert run["tmux_socket_path"] != str(isolated_tmux)
        assert observed.stdout.strip() == run["tmux_socket_path"]
        if surface == "raw":
            state = run["raw_web_state"]
        else:
            manifest = json.loads(Path(run["identity"]["manifest_path"]).read_text())
            assert manifest["tmux"]["socket_path"] == run["tmux_socket_path"]
            state = manifest["backend_state"]
        identity = state["web_identity"]
        connection_file = web.browser_connection_file(run)
        private = json.loads(connection_file.read_text())
        assert private["native_session_id"] == identity["native_session_id"]
        observer = DshWebClient.from_connection(
            private["origin"], launch_token=private["launch_token"]
        )
        browser_file = connection_file
        if surface == "manager" and case == "self-hosted":
            gateway = f"http://127.0.0.1:{run['identity']['gateway_port']}"
            with httpx.Client(base_url=gateway, trust_env=False, timeout=10) as http:
                assert http.get("/v1/endpoint").json()["admin_access"] == "open"
                assert http.get("/v1/web/enter", follow_redirects=False).status_code == 302
            browser_file = root / "gateway-browser-connection.json"
            browser_file.write_text(
                json.dumps(
                    {
                        "origin": state["origin"],
                        "native_session_id": identity["native_session_id"],
                        "gateway_entry_url": f"{gateway}/v1/web/enter",
                    }
                )
            )
            browser_file.chmod(0o600)
        browser = NativeBrowser.from_connection_file(browser_file)
        assert browser.metadata["session_id"] == identity["native_session_id"]
        assert browser.metadata["origin"] == state["origin"]
        assert browser.metadata["clean_url"] is True
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
        assert all(
            row["_fixture_placeholder_authorization"] == (case == "self-hosted") for row in requests
        )
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


def test_web_manager_and_authenticated_gateway_share_one_native_turn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    controlled_model_gate: ControlledModelGate,
    isolated_tmux: Path,
) -> None:
    """Race subprocess manager admission against a keyed gateway without a CLI admin signer."""

    repo = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(repo / "scripts/agents/test-fixtures"))
    config_tools = importlib.import_module("fixturelib.config")
    prepare = importlib.import_module("fixturelib.prepare")
    launch = importlib.import_module("fixturelib.launch")
    endpoint, requests = controlled_messages_server
    config = config_tools.resolve_config(
        case="self-hosted",
        client="dsh",
        mode="web",
        surface="manager",
        process_env={
            "HOUMAO_TEST_SELF_HOSTED_MODEL": "controlled",
            "HOUMAO_TEST_SELF_HOSTED_OPENAI_BASE_URL": endpoint,
            "HOUMAO_TEST_SELF_HOSTED_CONTEXT_WINDOW": "8192",
            "HOUMAO_TEST_SELF_HOSTED_MAX_OUTPUT_TOKENS": "128",
            "HOUMAO_TEST_SELF_HOSTED_DSH_REASONING": "false",
        },
    )
    prepared = prepare.prepare_run(
        config, run_root=tmp_path / "runs", executable=str(dsh_executable)
    )
    root = Path(prepared["run_dir"])
    try:
        launch.launch_run(root)
        run = prepare.load_run(root)
        assert run["tmux_socket_path"] != str(isolated_tmux)
        identity = run["identity"]
        gateway = f"http://127.0.0.1:{identity['gateway_port']}"
        key, signer = fixture_admin_key(tmp_path, "competing-admin")
        with httpx.Client(base_url=gateway, timeout=10) as http:
            enrollment = http.post(
                "/v1/admin/keys",
                json=key.model_dump(mode="json"),
                auth=FixtureProofAuth(signer, purpose="register", proposed_key=key),
            )
            assert enrollment.status_code == 201, enrollment.text

        start = threading.Barrier(2)
        controlled_model_gate.armed = True

        def manager_prompt() -> subprocess.CompletedProcess[str]:
            """Enter the owner CLI independently of the authenticated gateway."""

            start.wait(timeout=5)
            return subprocess.run(
                [
                    "houmao-mgr",
                    "--print-json",
                    "agents",
                    "single",
                    "--agent-id",
                    identity["agent_id"],
                    "prompt",
                    "--prompt",
                    "owner race marker",
                ],
                env=launch.run_environment(run),
                cwd=run["workdir"],
                text=True,
                capture_output=True,
                timeout=25,
                check=False,
            )

        def api_prompt() -> httpx.Response:
            """Send an independently signed ready-only request to the same owned session."""

            start.wait(timeout=5)
            with httpx.Client(base_url=gateway, timeout=10) as http:
                return http.post(
                    "/v1/control/prompt",
                    json={"prompt": "gateway race marker", "admission_policy": "ready_only"},
                    auth=FixtureProofAuth(signer, purpose="admin"),
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            manager = executor.submit(manager_prompt)
            gateway_prompt = executor.submit(api_prompt)
            try:
                assert controlled_model_gate.entered.wait(timeout=10)
                api = gateway_prompt.result(timeout=10)
                assert api.status_code in {200, 409}, api.text
                if api.status_code == 200:
                    local = manager.result(timeout=10)
                    assert local.returncode != 0, local.stdout
                assert len(requests) == 1
            finally:
                controlled_model_gate.release.set()
            local = manager.result(timeout=15)
        assert (local.returncode == 0) != (api.status_code == 200), (local.stdout, api.text)
        assert len(requests) == 1
        assert (
            "owner race marker" if local.returncode == 0 else "gateway race marker"
        ) in json.dumps(requests[0])
    finally:
        controlled_model_gate.release.set()
        launch.stop_run(root)
