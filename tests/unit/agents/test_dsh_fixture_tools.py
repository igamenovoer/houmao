"""Exercise explicit DSH fixture routing and ACP children without provider accounts."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import ModuleType

import pytest
import yaml

_REPO = Path(__file__).resolve().parents[3]
_HELPER = _REPO / "scripts/agents/test-fixtures"


@pytest.fixture
def fixture_tools(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, ModuleType, ModuleType]:
    """Load development modules without installing them as product code."""

    monkeypatch.syspath_prepend(str(_HELPER))
    return tuple(
        importlib.import_module("fixturelib." + name) for name in ("config", "prepare", "launch")
    )


def _inputs(case: str) -> dict[str, str]:
    """Provide only the selected route's synthetic credential and model references."""

    prefix = "HOUMAO_TEST_CLOUD" if case == "cloud-api" else "HOUMAO_TEST_SELF_HOSTED"
    result = {
        prefix + "_MODEL": "controlled-model",
        prefix + "_CONTEXT_WINDOW": "8192",
        prefix + "_MAX_OUTPUT_TOKENS": "512",
        prefix + "_DSH_REASONING": "false",
    }
    if case == "cloud-api":
        result.update(
            {
                "DEEPSEEK_API_KEY": "synthetic-dsh-key",
                "DEEPSEEK_BASE_URL_ANTHROPIC": "http://127.0.0.1:19091",
            }
        )
    else:
        result.update(
            {
                prefix + "_API_KEY": "synthetic-self-hosted-key",
                prefix + "_OPENAI_BASE_URL": "http://127.0.0.1:19092/v1",
            }
        )
    return result


@pytest.mark.parametrize("case", ["cloud-api", "self-hosted"])
@pytest.mark.parametrize("surface", ["raw", "manager", "passive-server"])
def test_all_dsh_surfaces_prepare_the_same_explicit_route(
    fixture_tools: tuple[ModuleType, ModuleType, ModuleType],
    tmp_path: Path,
    case: str,
    surface: str,
) -> None:
    """Raw and maintained preparations retain exact catalog, protocol, and private auth."""

    config_tools, prepare, _ = fixture_tools
    config = config_tools.resolve_config(
        case=case, client="dsh", surface=surface, process_env=_inputs(case)
    )
    run = prepare.prepare_run(config, run_root=tmp_path / "runs", executable=sys.executable)
    root = Path(run["run_dir"])
    setup = yaml.safe_load((root / "home/dsh-setup.yaml").read_text())
    assert setup["models"] == [
        {
            "id": "controlled-model",
            "context_window": 8192,
            "max_output_tokens": 512,
            "reasoning": False,
        }
    ]
    assert setup["provider"]["protocol"] == (
        "messages" if case == "cloud-api" else "openai-completions"
    )
    assert run["configuration"]["dsh"]["adapter"] == (
        "deepseek" if case == "cloud-api" else "pi-ai"
    )
    private = json.loads((root / "private-env.json").read_text())
    key_name = setup["provider"]["api_key_env"]
    assert private[key_name] == config.api_key.get_secret_value()
    assert (root / "home/skills").is_dir()
    assert config.api_key.get_secret_value() not in (root / "run.json").read_text()
    assert (root / "private-env.json").stat().st_mode & 0o777 == 0o600
    if surface != "raw":
        prepared = (
            Path(run["project_dir"]) / ".houmao/agents/tools/dsh/setups/fixture/dsh-setup.yaml"
        )
        assert yaml.safe_load(prepared.read_text()) == setup
        assert config.api_key.get_secret_value() in Path(run["credential"]["env_file"]).read_text()


def test_dsh_uses_only_the_selected_env_file(
    fixture_tools: tuple[ModuleType, ModuleType, ModuleType],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Conflicting ambient auth and routing cannot replace selected file inputs."""

    config_tools, _, _ = fixture_tools
    selected = tmp_path / "selected.env"
    selected.write_text("".join(f"{key}={value}\n" for key, value in _inputs("cloud-api").items()))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "unselected-ambient-key")
    monkeypatch.setenv("HOUMAO_TEST_CLOUD_MODEL", "unselected-ambient-model")
    config = config_tools.resolve_config(case="cloud-api", client="dsh", env_file=selected)
    assert config.api_key.get_secret_value() == "synthetic-dsh-key"
    assert config.model == "controlled-model"
    with pytest.raises(config_tools.FixtureError, match="explicitly selected"):
        config_tools.resolve_config(case="cloud-api", client="dsh")


@pytest.mark.parametrize("missing", ["_CONTEXT_WINDOW", "_MAX_OUTPUT_TOKENS", "_DSH_REASONING"])
def test_dsh_refuses_missing_capacities_before_allocating_state(
    fixture_tools: tuple[ModuleType, ModuleType, ModuleType], missing: str
) -> None:
    """No generic million-token or reasoning fallback can enter a fixture."""

    config_tools, _, _ = fixture_tools
    env = _inputs("self-hosted")
    del env["HOUMAO_TEST_SELF_HOSTED" + missing]
    with pytest.raises(config_tools.FixtureError, match="DSH requires explicit"):
        config_tools.resolve_config(case="self-hosted", client="dsh", process_env=env)


def test_dsh_cli_resolves_without_saved_native_login(tmp_path: Path) -> None:
    """The real CLI accepts DSH API inputs while rejecting native-login selection."""

    selected = tmp_path / "selected.env"
    selected.write_text("".join(f"{key}={value}\n" for key, value in _inputs("cloud-api").items()))
    base = [sys.executable, str(_HELPER / "fixture.py"), "check", "--client", "dsh"]
    result = subprocess.run(
        [*base, "--case", "cloud-api", "--env-file", str(selected)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["configuration"]["dsh"]["adapter"] == "deepseek"
    assert "synthetic-dsh-key" not in result.stdout + result.stderr
    rejected = subprocess.run(
        [*base, "--auth-method", "native-login", "--auth-bundle", "unused"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert rejected.returncode == 2 and "API credentials only" in rejected.stderr


def test_dsh_messages_preserves_an_explicit_version_path(
    fixture_tools: tuple[ModuleType, ModuleType, ModuleType],
) -> None:
    """The native Messages adapter recognizes /v1 rather than appending it twice."""

    config_tools, _, _ = fixture_tools
    env = _inputs("cloud-api")
    env["DEEPSEEK_BASE_URL_ANTHROPIC"] = "http://127.0.0.1:19091/custom/v1"
    config = config_tools.resolve_config(case="cloud-api", client="dsh", process_env=env)
    assert config.base_url == "http://127.0.0.1:19091/custom/v1"


def test_unsupported_dsh_native_login_does_not_allocate_private_state(
    fixture_tools: tuple[ModuleType, ModuleType, ModuleType],
    tmp_path: Path,
) -> None:
    """Native login fails before preparing credential-bearing roots in either posture."""

    config_tools, prepare, _ = fixture_tools
    selected = config_tools.ResolvedConfig(
        client="dsh", mode="headless", surface="raw", auth_method="native-login"
    )
    with pytest.raises(config_tools.FixtureError, match="selected API credentials"):
        prepare.prepare_run(
            selected, run_root=tmp_path / "never-allocated", executable=sys.executable
        )
    assert not (tmp_path / "never-allocated").exists()


@pytest.mark.parametrize("case", ["cloud-api", "self-hosted"])
@pytest.mark.parametrize("surface", ["raw", "manager"])
@pytest.mark.parametrize("prompt_mode", ["unattended", "as_is"])
def test_web_preparation_reuses_explicit_cases_and_operator_posture(
    fixture_tools: tuple[ModuleType, ModuleType, ModuleType],
    tmp_path: Path,
    case: str,
    surface: str,
    prompt_mode: str,
) -> None:
    """A fresh browser host has exact route metadata and never requires native auth JSON."""

    config_tools, prepare, launch = fixture_tools
    config = config_tools.resolve_config(
        case=case,
        client="dsh",
        mode="tui",
        surface=surface,
        operator_prompt_mode=prompt_mode,
        process_env=_inputs(case),
    )
    run = prepare.prepare_run(config, run_root=tmp_path / "runs", executable=sys.executable)
    root = Path(run["run_dir"])
    preset = yaml.safe_load((root / "assets/presets/server-api-smoke-dsh-fixture.yaml").read_text())
    assert preset["launch"]["prompt_mode"] == prompt_mode
    assert run["configuration"]["operator_prompt_mode"] == prompt_mode
    assert run["configuration"]["mode"] == "tui"
    assert not (root / "home/auth.json").exists()
    assert not (root / "home/models").exists()
    assert "HOUMAO_HOOK_OBSERVATION_DSH" not in launch.run_environment(run)
    assert launch.run_environment(run)["PATH"].startswith(str(root / "bin"))
    if surface == "manager":
        project_preset = yaml.safe_load(
            (
                Path(run["project_dir"]) / ".houmao/agents/presets/fixture-agent-dsh-fixture.yaml"
            ).read_text()
        )
        assert project_preset["launch"]["prompt_mode"] == prompt_mode


def test_live_runner_needs_explicit_external_credentials(tmp_path: Path) -> None:
    """Not-run and offline reports cannot accidentally contact ambient paid accounts."""

    command = [sys.executable, str(_REPO / "scripts/qualification/dsh/qualify.py")]
    missing = subprocess.run(command, capture_output=True, text=True, check=False)
    assert missing.returncode == 2
    missing_report = json.loads(missing.stdout)
    assert missing_report["status"] == "not_run"
    assert missing_report["native_surface"] == "headless-acp"
    assert "Interactive Web is not qualified" in missing_report["limits"][0]
    selected = tmp_path / "selected.env"
    selected.write_text("".join(f"{key}={value}\n" for key, value in _inputs("cloud-api").items()))
    offline = subprocess.run(
        [*command, "--env-file", str(selected), "--check-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert offline.returncode == 0, offline.stderr
    report = json.loads(offline.stdout)
    assert report["status"] == "not_run" and report["model"] == "controlled-model"
    assert report["native_surface"] == "headless-acp"
    assert "synthetic-dsh-key" not in offline.stdout + offline.stderr


def _native_peer(path: Path) -> str:
    """Serve an actual local ACP subprocess with bound metadata-only native receipts."""

    path.write_text(
        f"#!{sys.executable}\n"
        + """
import json, os, sys
from pathlib import Path
if '--version' in sys.argv:
    print('0.2.2-rc.3')
    sys.exit(0)
patch = json.loads(Path(sys.argv[-1]).read_text())
profile = json.loads(Path(sys.argv[sys.argv.index('--patch') + 1]).read_text())
route = next(item['config'] for item in profile if item.get('id') == 'acp')
selected_model = json.dumps([route['provider'], route['model']])
control = json.loads(Path(patch[0]['insert'][0]['config']['controlFile']).read_text())
native = control['expected_native_session_id'] or 'synthetic-native-fixture'
sequence = 0
def record(event, **fields):
    global sequence
    row = {**control, 'event':event, 'sequence':sequence, 'native_session_id':native,
           'process_id':os.getpid(), 'host_incarnation':'fixture-host',
           'agent_incarnation':None if event == 'loaded' else 'fixture-agent', **fields}
    with Path(control['evidence_path']).open('a') as target:
        target.write(json.dumps(row)+'\\n')
    sequence += 1
def send(frame):
    print(json.dumps({'jsonrpc':'2.0', **frame}), flush=True)
record('loaded', native_session_id=None)
for line in sys.stdin:
    frame = json.loads(line)
    method, params = frame['method'], frame.get('params', {})
    if method == 'initialize':
        send({'id':frame['id'], 'result':{'protocolVersion':1,
            'agentInfo':{'name':'deepseek-harness-acp','version':'0.0.1'},
            'agentCapabilities':{'sessionCapabilities':{'resume':{}, 'close':{}}}}})
    elif method in ('session/new','session/resume'):
        if method == 'session/resume':
            assert params['sessionId'] == native
        record('created')
        send({'id':frame['id'], 'result':{'sessionId':native, 'configOptions':[
            {'id':'model', 'type':'select', 'currentValue':selected_model,
             'options':[{'value':selected_model}]},
            {'id':'reasoning_effort', 'type':'select', 'currentValue':'off',
             'options':[{'value':'off'}]}]}})
    elif method == 'session/prompt':
        record('admitted', message_id='synthetic-input')
        record('claimed', message_id='synthetic-input', turn=1)
        Path('received-key.txt').write_text(os.getenv('DEEPSEEK_API_KEY', 'missing'))
        reason = 'end_turn'
        if params['prompt'][0]['text'] == 'WAIT_FOR_INTERRUPT':
            Path('native-waiting').write_text('claimed')
            cancellation = json.loads(sys.stdin.readline())
            assert cancellation['method'] == 'session/cancel'
            reason = 'cancelled'
        send({'id':frame['id'], 'result':{'stopReason':reason}})
    elif method == 'session/close':
        send({'id':frame['id'], 'result':{}})
"""
    )
    path.chmod(0o700)
    return str(path)


def test_raw_dsh_uses_acp_and_exact_private_continuation(
    fixture_tools: tuple[ModuleType, ModuleType, ModuleType], tmp_path: Path
) -> None:
    """Two independent fixture workers keep one native session and distinct raw artifacts."""

    config_tools, prepare, launch = fixture_tools
    config = config_tools.resolve_config(
        case="cloud-api", client="dsh", surface="raw", process_env=_inputs("cloud-api")
    )
    run = prepare.prepare_run(
        config, run_root=tmp_path / "runs", executable=_native_peer(tmp_path / "dsh")
    )
    root = Path(run["run_dir"])
    first = launch.launch_run(root, prompt="first explicit work", timeout=10)
    second = launch.prompt_run(root, prompt="second explicit work", timeout=10)
    assert first["identity"]["provider_session_id"] == second["identity"]["provider_session_id"]
    assert len(second["turns"]) == 2
    assert (root / "workdir/received-key.txt").read_text() == "synthetic-dsh-key"
    for index in (1, 2):
        frames = (root / "raw-turns" / f"turn-{index}" / "provider-stdout.jsonl").read_text()
        assert '"jsonrpc": "2.0"' in frames
        assert not (root / "raw-turns" / f"turn-{index}" / "input.json").exists()
    assert "synthetic-dsh-key" not in (root / "report.json").read_text()
    launch.stop_run(root)


def test_fixture_tmux_commands_have_explicit_server_and_clear_inherited_authority(
    fixture_tools: tuple[ModuleType, ModuleType, ModuleType], tmp_path: Path
) -> None:
    """Both direct commands and in-process runtime PATH lookup stay off the shared server."""

    _, prepare, launch = fixture_tools
    metadata = prepare._prepare_tmux_isolation(tmp_path)
    if not metadata:
        pytest.skip("tmux unavailable")
    run = {"run_dir": str(tmp_path), **metadata}
    command = launch._tmux_command(run, "has-session", "-t", "owned")
    assert command[1:3] == ["-L", "houmao-fixture-" + tmp_path.name]
    env = prepare.isolated_environment(
        {}, run_dir=tmp_path, process_env={"PATH": os.defpath, "TMUX": "shared", "TMUX_PANE": "%1"}
    )
    assert "TMUX" not in env and "TMUX_PANE" not in env
    assert env["PATH"].split(os.pathsep)[0] == str(tmp_path / "bin")
    shim = (tmp_path / "bin/tmux").read_text()
    assert "unset TMUX TMUX_PANE" in shim and " -L " in shim


def test_raw_fixture_interrupt_targets_its_captured_driver_and_native_attempt(
    fixture_tools: tuple[ModuleType, ModuleType, ModuleType],
    tmp_path: Path,
) -> None:
    """An independent interruption reaches native cancellation without another prompt."""

    from concurrent.futures import ThreadPoolExecutor

    config_tools, prepare, launch = fixture_tools
    config = config_tools.resolve_config(
        case="cloud-api", client="dsh", surface="raw", process_env=_inputs("cloud-api")
    )
    run = prepare.prepare_run(
        config, run_root=tmp_path / "runs", executable=_native_peer(tmp_path / "dsh")
    )
    root = Path(run["run_dir"])
    launch.launch_run(root, prompt="first work", timeout=5)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            active = pool.submit(launch.prompt_run, root, prompt="WAIT_FOR_INTERRUPT", timeout=5)
            deadline = time.monotonic() + 5
            while not (root / "workdir/native-waiting").is_file():
                assert time.monotonic() < deadline
                time.sleep(0.01)
            assert launch.interrupt_run(root)["status"] == "interrupt_requested"
            with pytest.raises(config_tools.FixtureError, match="Raw client turn failed"):
                active.result(timeout=5)
        terminal = prepare.load_run(root)
        assert len(terminal["turns"]) == 2
        assert terminal["turns"][-1]["returncode"] == 130
        assert "active_process" not in terminal
    finally:
        launch.stop_run(root)


def test_dsh_passive_birth_uses_the_prepared_brain_and_selected_route(
    fixture_tools: tuple[ModuleType, ModuleType, ModuleType],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The maintained passive launch receives DSH inputs with no credential payload."""

    config_tools, prepare, launch = fixture_tools
    config = config_tools.resolve_config(
        case="cloud-api", client="dsh", surface="passive-server", process_env=_inputs("cloud-api")
    )
    run = prepare.prepare_run(config, run_root=tmp_path / "runs", executable=sys.executable)
    requests = []

    def request(base, path, body=None):
        """Inspect the actual built brain behind a controlled authority response."""
        assert body["tool"] == "dsh"
        brain = yaml.safe_load(Path(body["brain_manifest_path"]).read_text())
        assert brain["inputs"]["tool"] == "dsh"
        requests.append((base, path, body))
        return {"tracked_agent_id": "controlled-dsh-authority"}

    monkeypatch.setattr(launch, "_http", request)
    result = launch._passive_launch(run, "http://127.0.0.1:19093")
    assert result["tracked_agent_id"] == "controlled-dsh-authority"
    assert requests[0][1] == "/houmao/agents/headless/launches"
    assert "synthetic-dsh-key" not in json.dumps(requests)


def test_managed_fixture_observes_execution_release_after_usage_without_resending(
    fixture_tools: tuple[ModuleType, ModuleType, ModuleType],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A completed ledger row cannot make sequential explicit prompts overlap."""

    config_tools, prepare, launch = fixture_tools
    config = config_tools.resolve_config(
        case="cloud-api", client="dsh", surface="manager", process_env=_inputs("cloud-api")
    )
    run = prepare.prepare_run(config, run_root=tmp_path / "runs", executable=sys.executable)
    run.update(
        {"status": "launched", "identity": {"gateway_host": "127.0.0.1", "gateway_port": 19094}}
    )
    root = Path(run["run_dir"])
    prepare.write_json(root / "run.json", run)
    calls, states = [], iter(["running", "idle"])

    def request(base, path, body=None):
        """Finalize accounting before releasing the same execution's ownership."""
        calls.append((path, body))
        if path == "/v1/control/prompt":
            return {"status": "accepted"}
        if path == "/v1/status":
            return {"active_execution": next(states)}
        assert path == "/v1/usage"
        return {
            "records": []
            if len(calls) == 1
            else [{"record_id": "completed-once", "outcome": "completed"}]
        }

    monkeypatch.setattr(launch, "_http", request)
    monkeypatch.setattr(launch.time, "sleep", lambda _: None)
    result = launch.prompt_run(root, prompt="one explicit request")
    assert result["turns"][-1]["status"] == "completed"
    assert sum(path == "/v1/control/prompt" for path, _ in calls) == 1
    assert sum(path == "/v1/status" for path, _ in calls) == 2
