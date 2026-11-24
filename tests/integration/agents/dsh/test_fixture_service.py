"""Exercise the maintained DSH service fixture with its real isolated ACP child."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import time
from typing import Any

import pytest
import yaml

from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token
from houmao.agents.realm_controller.registry_storage import load_managed_agent_record_by_agent_id
from tests.integration.agents.dsh.conftest import ControlledModelGate


def test_service_fixture_reuses_one_bound_acp_process_and_usage_journal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    controlled_model_gate: ControlledModelGate,
) -> None:
    """Manager and authenticated gateway calls share one child and restore its default model."""

    repo = Path(__file__).resolve().parents[4]
    monkeypatch.syspath_prepend(str(repo / "scripts/agents/test-fixtures"))
    configuration = importlib.import_module("fixturelib.config")
    prepare = importlib.import_module("fixturelib.prepare")
    launch = importlib.import_module("fixturelib.launch")
    endpoint, requests = controlled_messages_server
    config = configuration.resolve_config(
        case="cloud-api",
        client="dsh",
        mode="service",
        surface="manager",
        process_env={
            "HOUMAO_TEST_CLOUD_MODEL": "controlled",
            "HOUMAO_TEST_CLOUD_CONTEXT_WINDOW": "262144",
            "HOUMAO_TEST_CLOUD_MAX_OUTPUT_TOKENS": "128",
            "HOUMAO_TEST_CLOUD_DSH_REASONING": "false",
            "DEEPSEEK_API_KEY": "synthetic-local-service-key",
            "DEEPSEEK_BASE_URL_ANTHROPIC": endpoint,
        },
    )
    prepared = prepare.prepare_run(
        config, run_root=tmp_path / "runs", executable=str(dsh_executable), tmux_server="new"
    )
    root = Path(prepared["run_dir"])
    project = Path(prepared["project_dir"])
    setup = project / ".houmao/agents/tools/dsh/setups/fixture/tool-params.yaml"
    parameters = yaml.safe_load(setup.read_text())
    parameters["models"].append({**parameters["models"][0], "id": "controlled-alternate"})
    setup.write_text(yaml.safe_dump(parameters))
    pid: int | None = None
    birth: str | None = None
    try:
        first = launch.launch_run(root, timeout=55)
        manifest_path = Path(first["identity"]["manifest_path"])
        initial = json.loads(manifest_path.read_text())
        assert (initial["mode"], initial["backend"]) == ("service", "dsh_acp")
        assert initial.get("headless") is None and initial.get("native_surface") is None
        identity = initial["backend_state"]
        native_session = identity["native_session_id"]
        incarnation = identity["service_incarnation"]

        run = launch.load_run(root)
        environment = launch.run_environment(run)
        selector = ["agents", "single", "--agent-id", first["identity"]["agent_id"]]
        for prompt, model in (
            ("first persistent ACP prompt", []),
            ("second persistent ACP prompt", ["--model", "controlled-alternate"]),
        ):
            result = prepare.manager_root_call(
                [*selector, "prompt", "--prompt", prompt, *model], env=environment
            )
            assert result["delivery_state"] == "completed", result
        launch.prompt_run(root, prompt="third persistent ACP prompt", timeout=30)
        current = json.loads(manifest_path.read_text())
        assert current["backend_state"]["service_incarnation"] == incarnation
        assert current["backend_state"]["native_session_id"] == native_session
        terminal = current["tmux"]
        server = launch._fixture_tmux(run)
        assert terminal["socket_path"] == server.socket_path
        assert terminal["primary_window_role"] == "supervisor_logs"
        panes = server.observe_session(terminal["session_name"])
        assert panes is not None
        assert any(
            (pane.window_id, pane.pane_id)
            == (terminal["primary_window_id"], terminal["primary_pane_id"])
            and pane.window_index == terminal["primary_window_index"] == "0"
            for pane in panes
        )
        record = load_managed_agent_record_by_agent_id(current["agent_id"], env=environment)
        assert record is not None and record.generation_id == current["registry_generation_id"]
        assert (record.terminal.socket_path, record.terminal.current_session_name) == (
            terminal["socket_path"],
            terminal["session_name"],
        )
        assert [row["model"] for row in requests] == [
            "controlled",
            "controlled-alternate",
            "controlled",
        ]
        assert "first persistent ACP prompt" in json.dumps(requests[1]["messages"])
        artifact_root = manifest_path.parent / f"{manifest_path.stem}.turn-artifacts"
        receipts = [
            json.loads(path.read_text()) for path in artifact_root.glob("*/dsh-native-handoff.json")
        ]
        assert len(receipts) == 3
        assert {row["service_incarnation"] for row in receipts} == {incarnation}
        assert {row["native_session_id"] for row in receipts} == {native_session}
        assert len({row["attempt_id"] for row in receipts}) == 3
        assert len({row["process_id"] for row in receipts}) == 1
        assert len({row["process_birth_token"] for row in receipts}) == 1
        pid, birth = receipts[0]["process_id"], receipts[0]["process_birth_token"]
        assert _dispatch_origin_birth_token(pid) == birth
        totals = launch._gateway_request(run, "/v1/usage")["records"]
        assert len(totals) == 3
        assert {row["turn_id"] for row in totals} == {row["attempt_id"] for row in receipts}
        assert all(row["token_usage"]["total_tokens"]["value"] == 16 for row in totals)
        assert len({row["provider_turn_id"] for row in totals}) == 3
        controlled_model_gate.armed = True
        accepted = launch._gateway_request(
            run, "/v1/control/prompt", {"prompt": "hold this service turn"}
        )
        assert controlled_model_gate.entered.wait(5)
        launch.interrupt_run(root)
        operation_id = accepted["operation_id"]
        deadline = time.monotonic() + 15
        while True:
            observation = launch._gateway_request(run, "/v1/status")["observation"]
            if observation.get("last_request_id") == operation_id:
                break
            if time.monotonic() >= deadline:
                pytest.fail("The bound native service cancellation did not settle")
            time.sleep(0.1)
        assert observation["last_outcome"] == "interrupted", observation
        interrupted = json.loads(
            (artifact_root / operation_id / "dsh-native-handoff.json").read_text()
        )
        assert (
            interrupted["process_id"] == pid and interrupted["native_session_id"] == native_session
        )
        assert _dispatch_origin_birth_token(pid) == birth
        assert len(requests) == 4
    finally:
        controlled_model_gate.release.set()
        launch.stop_run(root)
    assert pid is not None and birth is not None and _dispatch_origin_birth_token(pid) != birth
