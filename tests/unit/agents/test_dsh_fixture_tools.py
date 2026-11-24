"""Exercise explicit DSH fixture routing without provider accounts."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from uuid import uuid4

import pytest
import yaml

from houmao.execution.tmux import TmuxObservationUnavailable, TmuxServer, capture_tmux_socket_path

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
@pytest.mark.parametrize("surface", ["raw", "manager"])
def test_all_dsh_surfaces_prepare_the_same_explicit_route(
    fixture_tools: tuple[ModuleType, ModuleType, ModuleType],
    tmp_path: Path,
    case: str,
    surface: str,
) -> None:
    """Raw and maintained preparations retain exact catalog, protocol, and private auth."""

    config_tools, prepare, launch = fixture_tools
    model = "controlled-cloud-model" if case == "cloud-api" else "Qwen/Qwen3.8-27B-FP8"
    config = config_tools.resolve_config(
        case=case,
        client="dsh",
        mode="headless",
        surface=surface,
        model=model,
        process_env=_inputs(case),
    )
    run = prepare.prepare_run(config, run_root=tmp_path / "runs", executable=sys.executable)
    root = Path(run["run_dir"])
    setup = yaml.safe_load((root / "home/houmao-tool-params.yaml").read_text())
    assert [
        {
            key: model[key]
            for key in ("id", "context_window", "max_output_tokens", "reasoning_efforts")
        }
        for model in setup["models"]
    ] == [
        {
            "id": model,
            "context_window": 8192,
            "max_output_tokens": 512,
            "reasoning_efforts": False,
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
    assert run["backend"] == "dsh_headless"
    assert config.api_key.get_secret_value() not in (root / "run.json").read_text()
    assert (root / "private-env.json").stat().st_mode & 0o777 == 0o600
    patch_path = root / "home/houmao-profile.patch.json"
    patch = json.loads(patch_path.read_text())
    selector = next(row["config"] for row in patch if row.get("id") == "agent-default-model")
    assert selector == {"provider": setup["provider"]["route"], "model": model}
    assert (patch_path.stat().st_mode & 0o777) == 0o600
    assert config.api_key.get_secret_value() not in patch_path.read_text()
    if surface != "raw":
        prepared = (
            Path(run["project_dir"]) / ".houmao/agents/tools/dsh/setups/fixture/tool-params.yaml"
        )
        assert yaml.safe_load(prepared.read_text())["provider"] == setup["provider"]
        assert config.api_key.get_secret_value() in Path(run["credential"]["env_file"]).read_text()
    else:
        argv = launch.raw_command(run, prompt="a private task")
        role_patch = root / "home/fixture-headless-role.patch.json"
        assert argv == [
            run["executable"],
            "--profile",
            "headless",
            "--patch",
            str(patch_path),
            "--patch",
            str(role_patch),
            "--json",
        ]
        assert {"prompt", "acp", config.api_key.get_secret_value()}.isdisjoint(argv)
        assert (role_patch.stat().st_mode & 0o777) == 0o600
        run["identity"] = {"provider_session_id": "session-verified"}
        assert launch.raw_command(run, prompt="another private task") == [
            *argv,
            "--session-id",
            "session-verified",
        ]


@pytest.mark.parametrize("surface", ["raw", "manager"])
def test_self_hosted_dsh_prepares_endpoint_only_without_auth(
    fixture_tools: tuple[ModuleType, ModuleType, ModuleType],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
) -> None:
    """Retain an explicit null provider role and never persist the native placeholder."""

    config_tools, prepare, _ = fixture_tools
    monkeypatch.setenv("HOUMAO_TEST_SELF_HOSTED_API_KEY", "unselected-ambient")
    config = config_tools.resolve_config(
        case="self-hosted",
        client="dsh",
        mode="web",
        surface=surface,
        model="controlled-model",
        base_url="http://127.0.0.1:19092/v1",
        context_window=8192,
        max_output_tokens=512,
        dsh_protocol="openai-completions",
        dsh_reasoning='{"off":null,"low":"low"}',
        dsh_compat='{"supports_developer_role":false}',
    )
    run = prepare.prepare_run(config, run_root=tmp_path / "runs", executable=sys.executable)
    root = Path(run["run_dir"])
    config_path = root / "home/houmao-tool-params.yaml"
    projected = yaml.safe_load(config_path.read_text())
    assert projected["provider"]["api_key_env"] is None
    assert projected["models"][0]["reasoning_efforts"] == {"off": None, "low": "low"}
    assert projected["models"][0]["compat"] == {"supports_developer_role": False}
    env_file = root / "assets/tools/dsh/auth/default/env/vars.env"
    assert env_file.read_text() == "OPENAI_BASE_URL=http://127.0.0.1:19092/v1\n"
    for path in (env_file, config_path, root / "private-env.json", root / "run.json"):
        assert "houmao-local-no-auth" not in path.read_text()
        assert "unselected-ambient" not in path.read_text()


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
        mode="web",
        surface=surface,
        operator_prompt_mode=prompt_mode,
        process_env=_inputs(case),
    )
    run = prepare.prepare_run(config, run_root=tmp_path / "runs", executable=sys.executable)
    root = Path(run["run_dir"])
    preset = yaml.safe_load((root / "assets/presets/server-api-smoke-dsh-fixture.yaml").read_text())
    assert preset["launch"]["prompt_mode"] == prompt_mode
    assert run["configuration"]["operator_prompt_mode"] == prompt_mode
    assert run["configuration"]["mode"] == "web"
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


def test_headless_qualification_reports_missing_selected_environment() -> None:
    """Offline qualification declares the native lane and demands selected credentials."""

    command = [sys.executable, str(_REPO / "scripts/qualification/dsh/qualify.py"), "--check-only"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["status"] == "not_run"
    assert report["mode"] == "headless"
    assert report["backend"] == "dsh_headless"
    assert report["native_surface"] is None
    assert "explicit external --env-file" in report["reason"]


def test_fixture_tmux_commands_have_explicit_server_and_clear_inherited_authority(
    fixture_tools: tuple[ModuleType, ModuleType, ModuleType], tmp_path: Path
) -> None:
    """Both fixture and runtime adapters honor the prepared restrictive PATH shim."""

    _, prepare, launch = fixture_tools
    run_dir = tmp_path / uuid4().hex[:12]
    metadata = prepare._prepare_tmux_isolation(run_dir)
    if not metadata:
        pytest.skip("tmux unavailable")
    run = {"run_dir": str(run_dir), **metadata}
    fixture_server = launch._fixture_tmux(run)
    socket = metadata["tmux_socket_path"]
    assert fixture_server.socket_path == socket
    env = prepare.isolated_environment(
        {},
        run_dir=run_dir,
        tmux_socket_path=socket,
        process_env={
            "PATH": os.defpath,
            "TMUX": "shared",
            "TMUX_PANE": "%1",
            "TMUX_TMPDIR": str(tmp_path / "unselected"),
        },
    )
    assert {"TMUX", "TMUX_PANE", "TMUX_TMPDIR"}.isdisjoint(env)
    assert env["PATH"].split(os.pathsep)[0] == str(run_dir / "bin")
    shim = (run_dir / "bin/tmux").read_text()
    assert "unset TMUX TMUX_PANE" in shim and f" -S {socket} " in shim
    try:
        with prepare.command_environment(env):
            assert capture_tmux_socket_path() == socket
            runtime_server = TmuxServer()
            runtime_server.start(
                ["-f", "/dev/null", "new-session", "-d", "-s", "owned"], environment=env
            ).require_success()
            observed = runtime_server.checked_command(
                ["display-message", "-p", "-t", "=owned:", "#{socket_path}"],
            )
            assert observed.stdout.strip() == socket
            foreign = TmuxServer(tmp_path / "foreign.sock")
            refused = foreign.command(["list-sessions"])
            assert (refused.returncode, refused.stdout, refused.stderr) == (2, "", "")
            with pytest.raises(TmuxObservationUnavailable, match="status 2") as failure:
                foreign.observe_session("owned")
            assert failure.value.returncode == 2
        assert fixture_server.observe_session("owned")
    finally:
        fixture_server.command(["kill-session", "-t", "=owned"])


@pytest.mark.parametrize(
    ("mode", "surface", "message"),
    [
        ("tui", "raw", "does not support mode 'tui'"),
        ("service", "raw", "Persistent service fixtures require the manager surface"),
        ("web", "passive-server", "Passive-server birth supports headless"),
    ],
)
def test_dsh_fixture_rejects_unqualified_modes_before_preparation(
    fixture_tools: tuple[ModuleType, ModuleType, ModuleType],
    mode: str,
    surface: str,
    message: str,
) -> None:
    """Unsupported modes cannot create a fixture that reports another lane as qualified."""

    config_tools, _, _ = fixture_tools
    with pytest.raises(config_tools.FixtureError, match=message):
        config_tools.resolve_config(
            case="cloud-api",
            client="dsh",
            mode=mode,
            surface=surface,
            process_env=_inputs("cloud-api"),
        )


@pytest.mark.parametrize("mode", ["headless", "web"])
def test_managed_fixture_observes_execution_release_after_usage_without_resending(
    fixture_tools: tuple[ModuleType, ModuleType, ModuleType],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    """A completed ledger row cannot make sequential explicit prompts overlap."""

    config_tools, prepare, launch = fixture_tools
    config = config_tools.resolve_config(
        case="cloud-api",
        client="dsh",
        mode=mode,
        surface="manager",
        process_env=_inputs("cloud-api"),
    )
    run = prepare.prepare_run(config, run_root=tmp_path / "runs", executable=sys.executable)
    run.update(
        {"status": "launched", "identity": {"gateway_host": "127.0.0.1", "gateway_port": 19094}}
    )
    root = Path(run["run_dir"])
    prepare.write_json(root / "run.json", run)
    calls, states = [], iter(["running", "idle"])

    def request(run, path, body=None):
        """Finalize accounting before releasing the same execution's ownership."""
        calls.append((path, body))
        if path == "/v1/control/prompt":
            return {"status": "accepted", "operation_id": "admitted-operation"}
        if path == "/v1/status":
            return {"active_execution": next(states)}
        assert path == "/v1/usage"
        return {
            "records": []
            if len(calls) == 1
            else [
                {
                    "record_id": "different-activity",
                    "outcome": "failed",
                    "turn_id": "other-operation",
                },
                {
                    "record_id": "completed-once",
                    "outcome": "completed",
                    "turn_id": "admitted-operation",
                },
            ]
        }

    monkeypatch.setattr(launch, "_gateway_request", request)
    monkeypatch.setattr(launch.time, "sleep", lambda _: None)
    result = launch.prompt_run(root, prompt="one explicit request")
    assert result["turns"][-1]["status"] == "completed"
    assert sum(path == "/v1/control/prompt" for path, _ in calls) == 1
    assert sum(path == "/v1/status" for path, _ in calls) == 2
