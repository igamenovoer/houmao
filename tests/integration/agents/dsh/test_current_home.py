"""Qualify current native inputs across exact DSH one-shot continuations."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import re
import sys
import time
from types import ModuleType
from typing import Any

import pytest
import yaml

from houmao.agents.realm_controller.native_refresh_models import NativeRefreshRequestV1


def _catalog(body: dict[str, Any]) -> str:
    """Read the latest native catalog while preserving older catalogs as history."""

    text = json.dumps(body["messages"])
    catalogs = re.findall(r"<available_skills>.*?</available_skills>", text)
    assert catalogs, "The controlled native request contains no skill catalog"
    return catalogs[-1]


def _skill(home: Path, name: str, description: str) -> None:
    """Write one synthetic external skill in the selected native home."""

    root = home / "skills" / name
    root.mkdir(parents=True, exist_ok=True)
    (root / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\nCurrent body {description}.\n"
    )


def _prepare_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    *,
    endpoint: str,
    surface: str,
    mode: str = "headless",
    reasoning: bool | dict[str, str] = False,
) -> tuple[dict[str, Any], ModuleType, ModuleType]:
    """Prepare one native CLI agent with an explicitly selected synthetic cloud route."""

    repo = Path(__file__).resolve().parents[4]
    monkeypatch.syspath_prepend(str(repo / "scripts/agents/test-fixtures"))
    configuration = importlib.import_module("fixturelib.config")
    prepare = importlib.import_module("fixturelib.prepare")
    launch = importlib.import_module("fixturelib.launch")
    config = configuration.resolve_config(
        case="cloud-api",
        client="dsh",
        mode=mode,
        surface=surface,
        process_env={
            "HOUMAO_TEST_CLOUD_MODEL": "controlled",
            "HOUMAO_TEST_CLOUD_CONTEXT_WINDOW": "8192",
            "HOUMAO_TEST_CLOUD_MAX_OUTPUT_TOKENS": "128",
            "HOUMAO_TEST_CLOUD_DSH_REASONING": json.dumps(reasoning),
            "DEEPSEEK_API_KEY": "synthetic-local-only",
            "DEEPSEEK_BASE_URL_ANTHROPIC": endpoint,
        },
    )
    run = prepare.prepare_run(config, run_root=tmp_path / "runs", executable=str(dsh_executable))
    return run, prepare, launch


def test_service_refresh_requires_native_relaunch_for_skills_and_mcp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """A persistent ACP session reads changed resources at its native boundaries."""

    endpoint, requests = controlled_messages_server
    run, prepare, launch = _prepare_fixture(
        tmp_path, monkeypatch, dsh_executable, endpoint=endpoint, surface="manager", mode="service"
    )
    root = Path(run["run_dir"])
    try:
        result = launch.launch_run(root, timeout=45)
        identity = result["identity"]
        manifest_path = Path(identity["manifest_path"])
        manifest = json.loads(manifest_path.read_text())
        initial = manifest["backend_state"]
        home = Path(manifest["launch_plan"]["home_selector"]["home_path"])
        env = launch.run_environment(launch.load_run(root))
        scope = ["agents", "single", "--agent-id", identity["agent_id"]]

        def managed(*args: str) -> dict[str, Any]:
            """Use the fixture's verified manager path for the current service."""

            return prepare.manager_root_call([*scope, *args], env=env)

        managed("prompt", "--prompt", "before resource edits")
        assert len(requests) == 1
        _skill(home, "service-current-skill", "skill added after service startup")
        marker = root / "service-mcp-started"
        script = root / "service_mcp.py"
        script.write_text(
            "import json, sys\n"
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).touch()\n"
            "for line in sys.stdin:\n"
            "    request = json.loads(line)\n"
            "    if 'id' not in request:\n"
            "        continue\n"
            "    method = request.get('method')\n"
            "    if method == 'initialize':\n"
            "        result = {'protocolVersion': request['params']['protocolVersion'], "
            "'capabilities': {'tools': {}}, "
            "'serverInfo': {'name': 'service-mcp-probe', 'version': '1'}}\n"
            "    else:\n"
            "        result = {'tools': [{'name': 'service_probe', 'description': 'Read a marker', "
            "'inputSchema': {'type': 'object'}}]}\n"
            "    print(json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'result': result}), "
            "flush=True)\n",
            encoding="utf-8",
        )
        setup_path = home / "houmao-tool-params.yaml"
        setup = yaml.safe_load(setup_path.read_text())
        setup["mcp_servers"] = [
            {"name": "service-mcp-probe", "command": sys.executable, "args": [str(script)]}
        ]
        setup_path.write_text(yaml.safe_dump(setup))
        gateway = launch.manager_gateway(launch.load_run(root))
        observation = gateway.get_common_plugin_state()
        resources = {resource.kind: resource for resource in observation.resources}
        assert resources["skills"].component == "provider_start"
        assert resources["mcp"].component == "session_binding"
        refreshed = gateway.refresh_native(NativeRefreshRequestV1())
        assert refreshed.outcome == "restart_required"
        assert not marker.exists()
        assert len(requests) == 1
        managed("prompt", "--prompt", "between edit and relaunch")
        assert len(requests) == 2
        assert "skill added after service startup" not in json.dumps(requests[-1]["messages"])
        assert not marker.exists()
        assert json.loads(manifest_path.read_text())["backend_state"] == initial

        managed("gateway", "detach")
        managed("stop")
        managed(
            "relaunch",
            "--chat-session-mode",
            "exact",
            "--chat-session-id",
            initial["native_session_id"],
        )
        next_state = json.loads(manifest_path.read_text())["backend_state"]
        assert next_state["native_session_id"] == initial["native_session_id"]
        assert next_state["service_incarnation"] != initial["service_incarnation"]
        managed("prompt", "--prompt", "after the verified resource boundary")
        assert len(requests) == 3
        assert "skill added after service startup" in _catalog(requests[-1])
        assert marker.exists()
        assert "service_probe" in json.dumps(requests[-1].get("tools", []))
    finally:
        launch.stop_run(root)


@pytest.mark.parametrize("surface", ["raw", "manager"])
def test_exact_continuation_consumes_external_skill_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    surface: str,
) -> None:
    """Each worker consumes current home inputs rather than restoring launch snapshots."""

    endpoint, requests = controlled_messages_server
    run, prepare, launch = _prepare_fixture(
        tmp_path, monkeypatch, dsh_executable, endpoint=endpoint, surface=surface
    )
    root = Path(run["run_dir"])
    try:
        first = launch.launch_run(root, prompt="initial current-home work", timeout=45)
        if surface == "raw":
            native_id = first["identity"]["provider_session_id"]
            home = Path(run["home_path"])
        else:
            manifest = json.loads(Path(first["identity"]["manifest_path"]).read_text())
            native_id = manifest["headless"]["session_id"]
            home = Path(manifest["launch_plan"]["home_selector"]["home_path"])
        _skill(home, "current-anchor", "persistent qualification anchor")
        _skill(home, "current-alpha", "alpha first revision")
        setup_path = home / "houmao-tool-params.yaml"
        role = home / "houmao-role.txt"
        role.write_text("EXTERNALLY_EDITED_ROLE_MUST_SURVIVE")
        credentials = home / "houmao-empty-credentials.yaml"
        credentials.write_text("# externally preserved native file\n{}\n")
        patch = home / "houmao-profile.patch.json"
        rows = json.loads(patch.read_text())
        next(row for row in rows if row.get("id") == "skill-filesystem")["config"]["watch"] = True
        patch.write_text(json.dumps(rows))
        protected = [role, credentials, patch, setup_path]

        def check_cli() -> None:
            """Exercise maintained scoped reads for both qualified and unsupported resources."""

            environment = launch.run_environment(launch.load_run(root))
            scope = ["agents", "single", "--agent-id", first["identity"]["agent_id"]]
            selected_home = prepare.manager_root_call([*scope, "home"], env=environment)
            assert selected_home["home_dir"] == str(home)
            with pytest.raises(prepare.ManagedCommandError) as checked:
                prepare.manager_root_call([*scope, "refresh", "--check"], env=environment)
            assert checked.value.payload["freshness"] == "unknown"
            with pytest.raises(prepare.ManagedCommandError) as refreshed:
                prepare.manager_root_call([*scope, "refresh"], env=environment)
            assert refreshed.value.payload["outcome"] == "unsupported"
            resources = {
                item["kind"]: item for item in refreshed.value.payload["observation"]["resources"]
            }
            assert (
                resources["skills"]["supported"] and resources["skills"]["boundary"] == "next_turn"
            )
            assert resources["mcp"]["reason"] == "dsh_cli_mcp_unqualified"

        def prompt(text: str) -> dict[str, Any]:
            """Run ordinary follow-up work and verify every materialized byte stays intact."""

            before = {str(path): path.read_bytes() for path in protected}
            if surface == "manager":
                identity = first["identity"]
                client = launch.manager_gateway(launch.load_run(root))
                journal = next((home / "sessions").rglob("session.v4.jsonl"))
                journal_before = journal.read_bytes()
                artifacts = Path(identity["manifest_path"]).with_suffix(".turn-artifacts")
                attempts = set(artifacts.iterdir())
                count = len(requests)
                observed = client.get_common_plugin_state()
                assert observed.freshness == "unknown"
                refreshed = client.refresh_native(NativeRefreshRequestV1())
                assert refreshed.outcome == "unsupported"
                resources = {item.kind: item for item in refreshed.observation.resources}
                assert resources["skills"].supported and resources["skills"].boundary == "next_turn"
                assert not resources["mcp"].supported
                assert resources["mcp"].reason == "dsh_cli_mcp_unqualified"
                check_cli()
                assert len(requests) == count
                assert set(artifacts.iterdir()) == attempts
                assert journal.read_bytes() == journal_before
            result = launch.prompt_run(root, prompt=text, timeout=45)
            assert {str(path): path.read_bytes() for path in protected} == before
            if surface == "raw":
                assert result["identity"]["provider_session_id"] == native_id
            else:
                current = json.loads(Path(result["identity"]["manifest_path"]).read_text())
                assert current["headless"]["session_id"] == native_id
            return result

        prompt("second current-home work")
        assert "alpha first revision" in _catalog(requests[-1])
        assert "EXTERNALLY_EDITED_ROLE_MUST_SURVIVE" in json.dumps(requests[-1]["system"])
        _skill(home, "current-alpha", "alpha second revision")
        _skill(home, "current-beta", "beta newly discovered")
        prompt("third current-home work")
        assert "alpha second revision" in _catalog(requests[-1])
        assert "beta newly discovered" in _catalog(requests[-1])
        (home / "skills/current-alpha/SKILL.md").unlink()
        (home / "skills/current-beta/SKILL.md").unlink()
        result = prompt("fourth current-home work")
        assert "current-alpha" not in _catalog(requests[-1])
        assert "current-beta" not in _catalog(requests[-1])
        assert "current-anchor" in _catalog(requests[-1])
        assert len(requests) == len(result["turns"]) == 4
        assert "initial current-home work" in json.dumps(requests[-1]["messages"])
        assert len(list((home / "sessions").rglob("session.v4.jsonl"))) == 1
        if surface == "manager":
            before = {path: path.read_bytes() for path in protected}
            journal = next((home / "sessions").rglob("session.v4.jsonl"))
            journal_before = journal.read_bytes()
            assert len(result["usage"]["records"]) == 4
            assert {row["provider_session_id"] for row in result["usage"]["records"]} == {native_id}
            prepare.manager_root_call(
                [
                    "agents",
                    "single",
                    "--agent-id",
                    first["identity"]["agent_id"],
                    "gateway",
                    "detach",
                ],
                env=launch.run_environment(launch.load_run(root)),
            )
            check_cli()
            assert {path: path.read_bytes() for path in protected} == before
            assert journal.read_bytes() == journal_before
            assert len(requests) == 4
    finally:
        launch.stop_run(root)


@pytest.mark.parametrize("surface", ["raw", "manager"])
@pytest.mark.parametrize("transport", ["stdio", "http"])
def test_headless_refuses_acp_mcp_before_native_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    surface: str,
    transport: str,
) -> None:
    """A valid ACP input fails without starting native work or changing the conversation."""

    endpoint, requests = controlled_messages_server
    run, prepare, launch = _prepare_fixture(
        tmp_path, monkeypatch, dsh_executable, endpoint=endpoint, surface=surface
    )
    root = Path(run["run_dir"])
    try:
        first = launch.launch_run(root, prompt="prior accepted turn", timeout=45)
        manifest_path = None
        if surface == "raw":
            native_id = first["identity"]["provider_session_id"]
            home = Path(run["home_path"])
        else:
            manifest_path = Path(first["identity"]["manifest_path"])
            manifest = json.loads(manifest_path.read_text())
            native_id = manifest["headless"]["session_id"]
            home = Path(manifest["launch_plan"]["home_selector"]["home_path"])
        setup_path = home / "houmao-tool-params.yaml"
        original = setup_path.read_text()
        setup = yaml.safe_load(original)
        marker = root / "unexpected-mcp-start"
        if transport == "stdio":
            server = {
                "name": "stdio-probe",
                "command": sys.executable,
                "args": ["-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"],
            }
        else:
            server = {
                "name": "http-probe",
                "type": "http",
                "url": endpoint.rstrip("/") + "/mcp",
                "headers": [{"name": "Authorization", "env_ref": "DEEPSEEK_API_KEY"}],
            }
        setup["mcp_servers"] = [server]
        setup_path.write_text(yaml.safe_dump(setup))
        edited = setup_path.read_bytes()
        journal = next((home / "sessions").rglob("session.v4.jsonl"))
        native_before = journal.read_bytes()
        native_evidence = set(root.rglob("dsh-native-evidence.jsonl"))
        assert len(requests) == 1

        if manifest_path is None:
            with pytest.raises(launch.FixtureError, match="headless home cannot be loaded"):
                launch.prompt_run(root, prompt="refuse ACP-only native input", timeout=45)
            assert len(prepare.load_run(root)["raw_workers"]) == 1
        else:
            scope = ["agents", "single", "--agent-id", first["identity"]["agent_id"]]
            env = launch.run_environment(launch.load_run(root))
            with pytest.raises(prepare.ManagedCommandError):
                prepare.manager_root_call(
                    [*scope, "prompt", "--prompt", "refuse ACP-only native input"], env=env
                )
            errors = sorted(root.glob("manager-error*.txt"))
            assert errors
            diagnostic = errors[-1].read_text()
            assert "cannot project ACP MCP declarations" in diagnostic
            assert transport in diagnostic
            assert "synthetic-local-only" not in diagnostic

        assert len(requests) == 1
        assert journal.read_bytes() == native_before
        assert set(root.rglob("dsh-native-evidence.jsonl")) == native_evidence
        assert setup_path.read_bytes() == edited
        assert not marker.exists()

        setup_path.write_text(original)
        resumed = launch.prompt_run(root, prompt="continue after exact rejection", timeout=45)
        assert len(requests) == 2
        assert "prior accepted turn" in json.dumps(requests[-1]["messages"])
        if manifest_path is None:
            assert resumed["identity"]["provider_session_id"] == native_id
        else:
            assert json.loads(manifest_path.read_text())["headless"]["session_id"] == native_id
            usage = resumed["usage"]["records"]
            assert len([row for row in usage if row["outcome"] == "completed"]) == 2
            assert {
                row["provider_session_id"] for row in usage if row["outcome"] == "completed"
            } == {native_id}
    finally:
        launch.stop_run(root)


@pytest.mark.parametrize(
    ("reasoning", "alternate_reasoning"),
    [
        (False, False),
        ({"off": "off", "high": "high"}, {"off": "off", "high": "high"}),
        (False, {"off": "off", "high": "high"}),
    ],
)
def test_request_model_controls_return_to_current_native_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    reasoning: bool | dict[str, str],
    alternate_reasoning: bool | dict[str, str],
) -> None:
    """Native defaults follow current material while request overrides stay transient."""

    endpoint, requests = controlled_messages_server
    run, _, launch = _prepare_fixture(
        tmp_path,
        monkeypatch,
        dsh_executable,
        endpoint=endpoint,
        surface="manager",
        reasoning=reasoning,
    )
    root = Path(run["run_dir"])
    try:
        started = launch.launch_run(root, timeout=45)
        manifest_path = Path(started["identity"]["manifest_path"])
        manifest = json.loads(manifest_path.read_text())
        home = Path(manifest["launch_plan"]["home_selector"]["home_path"])
        setup_path = home / "houmao-tool-params.yaml"
        setup = yaml.safe_load(setup_path.read_text())
        setup["models"][0]["context_window"] = 131072
        setup["models"].append(
            {**setup["models"][0], "id": "alternate", "reasoning_efforts": alternate_reasoning}
        )
        setup_path.write_text(yaml.safe_dump(setup))
        patch = home / "houmao-profile.patch.json"
        rows = json.loads(patch.read_text())
        adapter = next(row for row in rows if row.get("id") == "llm-deepseek")["config"]
        adapter["models"][0]["contextWindow"] = 131072
        adapter["defaultContextWindow"] = 131072
        adapter["models"].append({**adapter["models"][0], "id": "alternate"})
        patch.write_text(json.dumps(rows))
        before = {path: path.read_bytes() for path in (patch, setup_path)}
        launch.prompt_run(root, prompt="current default first", timeout=45)
        native_id = json.loads(manifest_path.read_text())["headless"]["session_id"]
        assert requests[-1]["model"] == "controlled"
        managed_run = launch.load_run(root)

        def override(text: str, model: dict[str, Any]) -> None:
            """Wait only for this admitted controlled request's usage and ownership."""

            receipt = launch._gateway_request(
                managed_run, "/v1/control/prompt", {"prompt": text, "execution": {"model": model}}
            )
            operation_id = receipt["operation_id"]
            assert operation_id
            deadline = time.monotonic() + 45
            while True:
                records = launch._gateway_request(managed_run, "/v1/usage")["records"]
                selected = [row for row in records if row["turn_id"] == operation_id]
                if (
                    selected
                    and launch._gateway_request(managed_run, "/v1/status")["active_execution"]
                    != "running"
                ):
                    assert selected[0]["outcome"] == "completed"
                    break
                assert time.monotonic() < deadline, "Explicit native model override did not settle"
                time.sleep(0.05)

        if reasoning:
            assert requests[-1]["thinking"]["type"] == "disabled"
            assert "output_config" not in requests[-1]
            override("raise the current model effort for one turn", {"reasoning": {"level": 1}})
            assert requests[-1]["model"] == "controlled"
            assert requests[-1]["thinking"]["type"] == "enabled"
            assert requests[-1]["output_config"]["effort"] == "high"

        model: dict[str, Any] = {"name": "alternate"}
        if alternate_reasoning:
            model["reasoning"] = {"level": 99}
        override("temporary alternate model", model)
        assert requests[-1]["model"] == "alternate"
        if alternate_reasoning:
            assert requests[-1]["thinking"]["type"] == "enabled"
        launch.prompt_run(root, prompt="restore current native default", timeout=45)
        assert requests[-1]["model"] == "controlled"
        assert requests[-1]["thinking"]["type"] == "disabled"
        assert {path: path.read_bytes() for path in before} == before
        next(row for row in rows if row.get("id") == "agent-default-model")["config"]["model"] = (
            "alternate"
        )
        patch.write_text(json.dumps(rows))
        externally_edited = patch.read_bytes()
        launch.prompt_run(root, prompt="edited native default applies", timeout=45)
        assert requests[-1]["model"] == "alternate"
        assert patch.read_bytes() == externally_edited
        if alternate_reasoning:
            override("reasoning for edited default", {"reasoning": {"level": 99}})
            assert requests[-1]["model"] == "alternate"
            assert requests[-1]["thinking"]["type"] == "enabled"
            assert patch.read_bytes() == externally_edited
        assert json.loads(manifest_path.read_text())["headless"]["session_id"] == native_id
        assert len(requests) == 4 + bool(alternate_reasoning) + bool(reasoning)
        assert "current default first" in json.dumps(requests[-1]["messages"])
    finally:
        launch.stop_run(root)
