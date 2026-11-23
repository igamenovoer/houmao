"""Qualify raw and managed generic Web fixture lanes against controlled native hosts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import importlib
import json
from pathlib import Path
import sqlite3
import subprocess
import threading
import time
from typing import Any

import httpx
import pytest

from houmao.agents.mailbox_runtime_models import FilesystemMailboxResolvedConfig
from houmao.agents.realm_controller.backends.dsh_web_client import DshWebClient
from houmao.agents.realm_controller.manifest import mutate_session_mailbox_binding
from tests.fixtures.gateway_access import FixtureProofAuth, fixture_admin_key
from tests.integration.agents.dsh.conftest import ControlledModelGate
from tests.integration.agents.dsh.web.browser import NativeBrowser
from tests.integration.agents.dsh.web.conftest import (
    call_native_request,
    read_native_history,
    read_native_session_ids,
    read_native_workspaces,
)
from tests.unit.agents.realm_controller.test_gateway_support import _deliver_unread_mailbox_message


def _gateway_browser_file(run: dict[str, Any], state: dict[str, Any]) -> Path:
    """Give the browser the gateway URL and expected identity without native credentials."""

    path = Path(run["run_dir"]) / "gateway-browser-connection.json"
    path.write_text(
        json.dumps(
            {
                "origin": state["origin"],
                "native_session_id": state["web_identity"]["native_session_id"],
                "gateway_entry_url": f"http://127.0.0.1:{run['identity']['gateway_port']}/v1/web/enter",
            }
        )
    )
    path.chmod(0o600)
    return path


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
            browser_file = _gateway_browser_file(run, state)
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


def _bind_fixture_notifier_mailbox(manifest_path: Path, root: Path) -> None:
    """Attach one fixture-owned offline mailbox containing unread work."""

    manifest = json.loads(manifest_path.read_text())
    agent_id = manifest["agent_id"]
    address = "workspace-browser@agents.localhost"
    _deliver_unread_mailbox_message(
        root, recipient_principal_id=agent_id, recipient_address=address
    )
    mailbox_root = root / "mailbox"
    with closing(sqlite3.connect(mailbox_root / "index.sqlite")) as connection:
        registration = connection.execute(
            "SELECT registration_id FROM mailbox_registrations WHERE address=? AND status='active'",
            (address,),
        ).fetchone()
    assert registration is not None
    mutate_session_mailbox_binding(
        manifest_path,
        channel="offline",
        expected_revision=manifest["launch_plan"]["mailboxes"]["offline"]["revision"],
        binding=FilesystemMailboxResolvedConfig(
            transport="filesystem",
            principal_id=agent_id,
            address=address,
            filesystem_root=mailbox_root,
            bindings_version="workspace-browser-mail-revision",
            agent_id=agent_id,
            binding_id=registration[0],
        ),
        agent_id=agent_id,
        session_id=manifest["runtime"]["session_id"],
    )


def test_managed_browser_entry_selects_bound_workspace_before_and_after_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
) -> None:
    """Observe exact entry and reload before any prompt, across relaunch, and after a notifier."""

    repo = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(repo / "scripts/agents/test-fixtures"))
    config_tools = importlib.import_module("fixturelib.config")
    prepare = importlib.import_module("fixturelib.prepare")
    launch = importlib.import_module("fixturelib.launch")
    web = importlib.import_module("fixturelib.web")
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
        manifest_path = Path(run["identity"]["manifest_path"])
        state = json.loads(manifest_path.read_text())["backend_state"]
        workdir = str(Path(run["workdir"]).resolve())
        original_identity = state["web_identity"]
        original = original_identity["native_session_id"]
        history_marker = "Original managed browser Workspace history"
        other_marker = "Unrelated browser Workspace history"
        notification_marker = "Controlled Workspace browser notifier"
        other_workdir = tmp_path / "unrelated-workdir"
        other_workdir.mkdir()

        def observe_native() -> DshWebClient:
            """Open a separate API peer to the currently published native host."""

            private = json.loads(web.browser_connection_file(run).read_text())
            return DshWebClient.from_connection(
                private["origin"], launch_token=private["launch_token"]
            )

        def open_managed_browser(current: dict[str, Any]) -> NativeBrowser:
            """Open managed gateway entry with clean browser storage and no sidebar click."""

            return NativeBrowser.from_connection_file(
                _gateway_browser_file(run, current), observe_selection=True
            )

        with closing(observe_native()) as observer:
            initial = read_native_workspaces(observer)
            assert set(initial) == {workdir}
            workspace_id = initial[workdir]["workspaceId"]
            assert initial[workdir]["sessionIds"] == [original]
            assert read_native_session_ids(observer) == {original}
            assert not requests
            with closing(open_managed_browser(state)) as browser:
                assert browser.metadata["session_id"] == original
                assert browser.metadata["clean_url"] is True
                assert browser.metadata["startup_mutations"] == 0
                assert read_native_workspaces(observer) == initial
                assert read_native_session_ids(observer) == {original}
                assert browser.call("reload")["session_id"] == original
                assert read_native_workspaces(observer) == initial
                assert read_native_session_ids(observer) == {original}
                assert not requests
                launch.prompt_run(root, prompt=history_marker, timeout=45)
                browser.call("contains", text=history_marker)

                other_workspace = call_native_request(
                    observer, "workspace/create", {"request": {"path": str(other_workdir)}}
                )["workspace"]
                other = browser.call("new", workspace_id=other_workspace["workspaceId"])[
                    "session_id"
                ]
                assert other != original
                browser.call("submit", text=other_marker)
                browser.call("contains", text="Controlled native result")
                assert browser.call("reload")["session_id"] == other
                memberships = read_native_workspaces(observer)
                assert memberships[str(other_workdir)]["sessionIds"] == [other]
                before_other = read_native_history(observer, other)
                assert other_marker in before_other
                assert read_native_session_ids(observer) == {original, other}

                _bind_fixture_notifier_mailbox(manifest_path, root)
                gateway = f"http://127.0.0.1:{run['identity']['gateway_port']}"
                with httpx.Client(base_url=gateway, trust_env=False, timeout=10) as http:
                    notifier = "/v1/mail-notifier/offline"
                    http.put(
                        notifier, json={"interval_seconds": 1, "appendix_text": notification_marker}
                    ).raise_for_status()
                    try:
                        deadline = time.monotonic() + 25
                        while True:
                            last_turn = observer.state(original_identity)["last_turn"] or {}
                            if (
                                last_turn.get("turn", 0) >= 2
                                and last_turn.get("result") == "completed"
                                and notification_marker in read_native_history(observer, original)
                            ):
                                break
                            assert time.monotonic() < deadline, (
                                "Notifier turn did not reach managed session"
                            )
                            time.sleep(0.05)
                    finally:
                        http.delete(notifier).raise_for_status()
                entered = browser.call("reenter")
                assert entered["session_id"] == original
                assert entered["clean_url"] is True and entered["startup_mutations"] == 0
                browser.call("contains", text=notification_marker)
                assert json.loads(manifest_path.read_text())["backend_state"]["web_identity"] == (
                    original_identity
                )
                assert read_native_history(observer, other) == before_other
                assert read_native_workspaces(observer) == memberships
                assert read_native_session_ids(observer) == {original, other}

        for mode in ("exact", "new"):
            chat_session = ["--chat-session-mode", mode]
            if mode == "exact":
                chat_session.extend(["--chat-session-id", original])
            prepare.manager_root_call(
                [
                    "agents",
                    "single",
                    "--agent-id",
                    run["identity"]["agent_id"],
                    "relaunch",
                    *chat_session,
                ],
                env=launch.run_environment(run),
            )
            state = json.loads(manifest_path.read_text())["backend_state"]
            target = state["web_identity"]["native_session_id"]
            with closing(observe_native()) as observer:
                before_entry = read_native_workspaces(observer)
                assert set(before_entry) == set(memberships)
                assert before_entry[str(other_workdir)] == memberships[str(other_workdir)]
                assert before_entry[workdir]["workspaceId"] == workspace_id
                if mode == "exact":
                    assert target == original and before_entry == memberships
                    expected_sessions = {original, other}
                else:
                    assert target not in {original, other}
                    assert before_entry[workdir]["sessionIds"] == [target, original]
                    expected_sessions = {original, other, target}
                assert read_native_session_ids(observer) == expected_sessions
                with closing(open_managed_browser(state)) as browser:
                    assert browser.metadata["session_id"] == target
                    assert browser.metadata["clean_url"] is True
                    assert browser.metadata["startup_mutations"] == 0
                    if mode == "exact":
                        browser.call("contains", text=history_marker)
                    assert read_native_workspaces(observer) == before_entry
                    assert read_native_session_ids(observer) == expected_sessions
                assert history_marker in read_native_history(observer, original)
                assert read_native_history(observer, other) == before_other
    finally:
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
