"""Qualify externally edited native homes across ordinary exact ACP continuations."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import re
import sys
import time
from typing import Any

import pytest
import yaml

from houmao.agents.realm_controller.native_refresh_models import NativeRefreshRequestV1


_MCP_SERVER = """import json, sys
for line in sys.stdin:
    row = json.loads(line)
    if 'id' not in row:
        continue
    method = row['method']
    if method == 'initialize':
        result = {'protocolVersion': row['params']['protocolVersion'],
                  'capabilities': {'tools': {}},
                  'serverInfo': {'name': 'current-home-probe', 'version': sys.argv[1]}}
    elif method == 'tools/list':
        result = {'tools': [{'name': 'probe_' + sys.argv[1], 'description': 'Synthetic probe',
                            'inputSchema': {'type': 'object', 'properties': {}}}]}
    elif method == 'ping':
        result = {}
    else:
        print(json.dumps({'jsonrpc': '2.0', 'id': row['id'],
                          'error': {'code': -32601, 'message': 'unsupported'}}), flush=True)
        continue
    print(json.dumps({'jsonrpc': '2.0', 'id': row['id'], 'result': result}), flush=True)
"""


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


@pytest.mark.parametrize("surface", ["raw", "manager"])
def test_exact_continuation_consumes_external_skill_and_mcp_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    surface: str,
) -> None:
    """Each worker consumes current home inputs rather than restoring launch snapshots."""

    repo = Path(__file__).resolve().parents[4]
    monkeypatch.syspath_prepend(str(repo / "scripts/agents/test-fixtures"))
    configuration = importlib.import_module("fixturelib.config")
    prepare = importlib.import_module("fixturelib.prepare")
    launch = importlib.import_module("fixturelib.launch")
    endpoint, requests = controlled_messages_server
    config = configuration.resolve_config(
        case="cloud-api",
        client="dsh",
        surface=surface,
        process_env={
            "HOUMAO_TEST_CLOUD_MODEL": "controlled",
            "HOUMAO_TEST_CLOUD_CONTEXT_WINDOW": "8192",
            "HOUMAO_TEST_CLOUD_MAX_OUTPUT_TOKENS": "128",
            "HOUMAO_TEST_CLOUD_DSH_REASONING": "false",
            "DEEPSEEK_API_KEY": "synthetic-local-only",
            "DEEPSEEK_BASE_URL_ANTHROPIC": endpoint,
        },
    )
    run = prepare.prepare_run(config, run_root=tmp_path / "runs", executable=str(dsh_executable))
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
        _skill(home, "current-alpha", "alpha first revision")
        setup_path = home / "houmao-tool-params.yaml"
        setup = yaml.safe_load(setup_path.read_text())
        server = root / "mcp_server.py"
        server.write_text(_MCP_SERVER)
        setup["mcp_servers"] = [
            {"name": "current", "command": sys.executable, "args": [str(server), "v1"]}
        ]
        setup_path.write_text(yaml.safe_dump(setup))
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
            """Exercise maintained scoped reads and automatic refresh through the fixture."""

            environment = launch.run_environment(launch.load_run(root))
            scope = ["agents", "single", "--agent-id", first["identity"]["agent_id"]]
            selected_home = prepare.manager_root_call([*scope, "home"], env=environment)
            assert selected_home["home_dir"] == str(home)
            with pytest.raises(prepare.ManagedCommandError) as checked:
                prepare.manager_root_call([*scope, "refresh", "--check"], env=environment)
            assert checked.value.payload["freshness"] == "unknown"
            cli_refresh = prepare.manager_root_call([*scope, "refresh"], env=environment)
            assert cli_refresh["outcome"] == "automatic"

        def prompt(text: str) -> dict[str, Any]:
            """Run ordinary follow-up work and verify every materialized byte stays intact."""

            before = {str(path): path.read_bytes() for path in protected}
            if surface == "manager":
                identity = first["identity"]
                client = launch.manager_gateway(launch.load_run(root))
                binding = home / "houmao-native-session.json"
                journal = next((home / "sessions").rglob("session.v4.jsonl"))
                native_before = {path: path.read_bytes() for path in (binding, journal)}
                artifacts = Path(identity["manifest_path"]).parent / "manifest.turn-artifacts"
                attempts = set(artifacts.iterdir())
                count = len(requests)
                observed = client.get_common_plugin_state()
                assert observed.freshness == "unknown"
                refreshed = client.refresh_native(NativeRefreshRequestV1())
                assert refreshed.outcome == "automatic", refreshed.model_dump(mode="json")
                assert all(item.boundary == "next_turn" for item in refreshed.observation.resources)
                check_cli()
                assert len(requests) == count
                assert set(artifacts.iterdir()) == attempts
                assert {path: path.read_bytes() for path in native_before} == native_before
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
        assert any(tool["name"] == "mcp__current__probe_v1" for tool in requests[-1]["tools"])
        assert "EXTERNALLY_EDITED_ROLE_MUST_SURVIVE" in json.dumps(requests[-1]["system"])
        _skill(home, "current-alpha", "alpha second revision")
        _skill(home, "current-beta", "beta newly discovered")
        setup["mcp_servers"][0]["args"][-1] = "v2"
        setup_path.write_text(yaml.safe_dump(setup))
        prompt("third current-home work")
        assert "alpha second revision" in _catalog(requests[-1])
        assert "beta newly discovered" in _catalog(requests[-1])
        assert any(tool["name"] == "mcp__current__probe_v2" for tool in requests[-1]["tools"])
        (home / "skills/current-alpha/SKILL.md").unlink()
        (home / "skills/current-beta/SKILL.md").unlink()
        setup["mcp_servers"] = []
        setup_path.write_text(yaml.safe_dump(setup))
        result = prompt("fourth current-home work")
        assert "current-alpha" not in _catalog(requests[-1])
        assert "current-beta" not in _catalog(requests[-1])
        assert all(not tool["name"].startswith("mcp__current__") for tool in requests[-1]["tools"])
        assert len(requests) == len(result["turns"]) == 4
        assert "initial current-home work" in json.dumps(requests[-1]["messages"])
        assert len(list((home / "sessions").rglob("session.v4.jsonl"))) == 1
        if surface == "manager":
            before = {path: path.read_bytes() for path in protected}
            binding = home / "houmao-native-session.json"
            binding_before = binding.read_bytes()
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
            assert binding.read_bytes() == binding_before
            assert len(requests) == 4
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

    repo = Path(__file__).resolve().parents[4]
    monkeypatch.syspath_prepend(str(repo / "scripts/agents/test-fixtures"))
    configuration = importlib.import_module("fixturelib.config")
    prepare = importlib.import_module("fixturelib.prepare")
    launch = importlib.import_module("fixturelib.launch")
    endpoint, requests = controlled_messages_server
    config = configuration.resolve_config(
        case="cloud-api",
        client="dsh",
        surface="manager",
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

            previous = {
                row["record_id"]
                for row in launch._gateway_request(managed_run, "/v1/usage")["records"]
            }
            launch._gateway_request(
                managed_run, "/v1/control/prompt", {"prompt": text, "execution": {"model": model}}
            )
            deadline = time.monotonic() + 45
            while True:
                records = launch._gateway_request(managed_run, "/v1/usage")["records"]
                selected = [row for row in records if row["record_id"] not in previous]
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
        next(row for row in rows if row.get("id") == "acp")["config"]["model"] = "alternate"
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
