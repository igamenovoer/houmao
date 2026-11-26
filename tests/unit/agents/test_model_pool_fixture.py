"""Verify developer model pool inputs without live providers or credential stores."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import importlib
import json
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
import yaml

_REPO = Path(__file__).resolve().parents[3]
_POOL_TOML = """\
schema_version = 1

[models.local]
client = "dsh"
case = "self-hosted"
model = "example-local"
base_url = "https://local.example.invalid/v1"
context_window = 4096
max_output_tokens = 512
dsh_reasoning = false
supported_modes = ["web"]

[models.cloud]
client = "claude"
case = "cloud-api"
model = "example-cloud"
env_file = "separate.env"
"""
_HERMES_POOL_TOML = """\
schema_version = 1

[models.hermes]
client = "hermes"
case = "self-hosted"
model = "example-hermes"
base_url = "https://local.example.invalid/v1"
env_file = "hermes.env"
"""


@pytest.fixture
def pool_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Import the same model pool code used by the fixture CLI."""

    monkeypatch.syspath_prepend(str(_REPO / "scripts/agents/test-fixtures"))
    return importlib.import_module("fixturelib.pool")


def _write_pool(path: Path, contents: str = _POOL_TOML) -> Path:
    """Create synthetic pool input with the required private permissions."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(mode=0o600)
    path.write_text(contents, encoding="utf-8")
    return path


@pytest.fixture
def hermes_env_file(tmp_path: Path) -> Path:
    """Write an explicit synthetic Hermes credential file."""

    path = tmp_path / "hermes.env"
    path.touch(mode=0o600)
    path.write_text("HOUMAO_TEST_SELF_HOSTED_API_KEY=synthetic-hermes-key\n", encoding="utf-8")
    return path


def _hermes_case_args(env_file: Path) -> list[str]:
    """Return the direct CLI equivalent of the synthetic Hermes pool route."""

    return [
        "--client",
        "hermes",
        "--case",
        "self-hosted",
        "--model",
        "example-hermes",
        "--base-url",
        "https://local.example.invalid/v1",
        "--env-file",
        str(env_file),
    ]


def test_selects_pool_from_cli_env_then_xdg(pool_module: ModuleType, tmp_path: Path) -> None:
    """Resolve all three supported locations and prefer the explicit path."""

    xdg = tmp_path / "xdg"
    xdg_pool = _write_pool(xdg / "houmao/test-fixtures/model-pool.toml")
    configured_pool = _write_pool(
        tmp_path / "configs/model-pool.toml", _POOL_TOML.replace("example-local", "env-model")
    )
    explicit_pool = _write_pool(
        tmp_path / "other/model-pool.toml", _POOL_TOML.replace("example-local", "cli-model")
    )
    env = {"XDG_DATA_HOME": str(xdg), "HOUMAO_TEST_MODEL_POOL": str(configured_pool)}

    assert pool_module.load_model_pool(explicit_pool, process_env=env).models["local"].model == (
        "cli-model"
    )
    assert pool_module.load_model_pool(process_env=env).models["local"].model == "env-model"
    pool = pool_module.load_model_pool(process_env={"XDG_DATA_HOME": str(xdg)})
    assert pool.models["local"].model == "example-local"
    assert pool.models["cloud"].env_file == xdg_pool.parent / "separate.env"


def test_pool_defaults_to_home_share(pool_module: ModuleType, tmp_path: Path) -> None:
    """Use XDG's default data directory when the setting is unset or blank."""

    _write_pool(tmp_path / ".local/share/houmao/test-fixtures/model-pool.toml")
    pool = pool_module.load_model_pool(process_env={"XDG_DATA_HOME": ""}, user_home=tmp_path)
    assert set(pool.models) == {"local", "cloud"}


def test_pool_must_be_outside_checkout(pool_module: ModuleType, tmp_path: Path) -> None:
    """Refuse repository files even beneath its ignored tmp directory."""

    checkout = tmp_path / "checkout"
    path = _write_pool(checkout / "tmp/model-pool.toml")
    with pytest.raises(pool_module.FixtureError, match="outside the checkout"):
        pool_module.load_model_pool(path, repo_root=checkout)


def test_rejects_symlink_pool_and_checkout_alias(pool_module: ModuleType, tmp_path: Path) -> None:
    """Reject symlink files and real files reached via an alias to the checkout."""

    checkout = tmp_path / "checkout"
    _write_pool(checkout / "model-pool.toml")
    path = _write_pool(tmp_path / "real-pool.toml")
    link = tmp_path / "symlink-pool.toml"
    link.symlink_to(path)
    checkout_alias = tmp_path / "checkout-alias"
    checkout_alias.symlink_to(checkout, target_is_directory=True)

    with pytest.raises(pool_module.FixtureError, match="symlink"):
        pool_module.load_model_pool(link, repo_root=checkout)
    with pytest.raises(pool_module.FixtureError, match="outside the checkout"):
        pool_module.load_model_pool(checkout_alias / "model-pool.toml", repo_root=checkout)


def test_rejects_checkout_env_file(pool_module: ModuleType, tmp_path: Path) -> None:
    """Apply the external path rule to credential references before resolving a case."""

    checkout = tmp_path / "checkout"
    checkout.mkdir()
    path = _write_pool(
        tmp_path / "model-pool.toml",
        _POOL_TOML.replace("separate.env", "checkout/credentials.env"),
    )
    with pytest.raises(pool_module.FixtureError, match="outside the checkout"):
        pool_module.load_model_pool(path, repo_root=checkout)


@pytest.mark.parametrize("mode", [0o640, 0o602, 0o601])
def test_requires_owner_only_permissions(
    pool_module: ModuleType, tmp_path: Path, mode: int
) -> None:
    """Require private files and name the repair command."""

    path = _write_pool(tmp_path / "model-pool.toml")
    path.chmod(mode)
    with pytest.raises(pool_module.FixtureError, match="chmod 600"):
        pool_module.load_model_pool(path)


def test_requires_a_regular_file(pool_module: ModuleType, tmp_path: Path) -> None:
    """Reject a named pipe without waiting for a writer."""

    path = tmp_path / "model-pool.toml"
    os.mkfifo(path, 0o600)
    with pytest.raises(pool_module.FixtureError, match="regular file"):
        pool_module.load_model_pool(path)


@pytest.mark.parametrize(
    "entry_line",
    [
        'api_key = "synthetic-secret"',
        'auth_token = "synthetic-secret"',
        'base_url = "https://user:synthetic-secret@example.invalid/v1"',
        'base_url = "https://example.invalid/v1?api_key=synthetic-secret"',
        'dsh_compat = { chat_template_args = { apiKey = "synthetic-secret" } }',
    ],
)
def test_schema_rejects_inline_credentials(
    pool_module: ModuleType, tmp_path: Path, entry_line: str
) -> None:
    """Keep secret values out of both configured entries and validation errors."""

    path = _write_pool(tmp_path / "model-pool.toml", _POOL_TOML + entry_line + "\n")
    with pytest.raises(pool_module.FixtureError, match="Invalid model pool schema") as error:
        pool_module.load_model_pool(path)
    assert "synthetic-secret" not in str(error.value)
    assert error.value.__suppress_context__


def test_slot_selection_checks_override_then_shared_key(
    pool_module: ModuleType, tmp_path: Path
) -> None:
    """Normalize a slot name for environment lookup and keep explicit keys independent."""

    pool = pool_module.load_model_pool(_write_pool(tmp_path / "model-pool.toml"))
    env = {"HOUMAO_TEST_MODEL": "local", "HOUMAO_TEST_MODEL_CUDA_ALGO": "cloud"}
    assert pool_module.select_pool_key(pool, slot="cuda-algo", process_env=env) == "cloud"
    assert pool_module.select_pool_key(pool, slot="lead", process_env=env) == "local"
    assert pool_module.select_pool_key(pool, key="local", process_env={}) == "local"


def test_slot_selection_errors_name_available_keys(pool_module: ModuleType, tmp_path: Path) -> None:
    """Fail on missing selection and on an invalid override of a valid shared key."""

    pool = pool_module.load_model_pool(_write_pool(tmp_path / "model-pool.toml"))
    with pytest.raises(
        pool_module.FixtureError, match="HOUMAO_TEST_MODEL_LEAD or HOUMAO_TEST_MODEL"
    ):
        pool_module.select_pool_key(pool, slot="lead", process_env={})
    with pytest.raises(pool_module.FixtureError, match="Available model keys: cloud, local"):
        pool_module.select_pool_key(
            pool,
            slot="lead",
            process_env={"HOUMAO_TEST_MODEL_LEAD": "invalid", "HOUMAO_TEST_MODEL": "cloud"},
        )


def test_template_loads_all_lanes_without_credentials(
    pool_module: ModuleType, tmp_path: Path
) -> None:
    """Check the public template using the same loader as an external copy."""

    example = _REPO / "tests/fixtures/agent-launch/model-pool.example.toml"
    path = _write_pool(tmp_path / "model-pool.toml", example.read_text(encoding="utf-8"))
    pool = pool_module.load_model_pool(path)

    assert pool.models["local_dsh"].case == "self-hosted"
    assert pool.models["cloud_dsh"].case == "cloud-api"
    assert pool.models["native_codex"].auth_method == "native-login"


@pytest.fixture
def pool_cli(pool_module: ModuleType) -> ModuleType:
    """Load the CLI with the fixture package available on the import path."""

    return importlib.import_module("fixture")


def test_list_models_returns_only_public_fields(
    pool_cli: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """List supported modes without displaying credential or executable references."""

    example = _REPO / "tests/fixtures/agent-launch/model-pool.example.toml"
    path = _write_pool(tmp_path / "model-pool.toml", example.read_text(encoding="utf-8"))

    assert pool_cli.main(["list-models", "--model-pool", str(path)]) == 0
    output = capsys.readouterr().out
    models = {model["key"]: model for model in json.loads(output)["models"]}
    assert models["local_dsh"] == {
        "key": "local_dsh",
        "client": "dsh",
        "case": "self-hosted",
        "auth_method": "api-key",
        "model": "example-local-model",
        "supported_modes": ["web", "headless"],
    }
    assert models["native_codex"]["auth_method"] == "native-login"
    for private in (
        "/path/to/bin/dsh",
        "/path/to/private/deepseek.env",
        "example-imported-bundle",
        str(path),
    ):
        assert private not in output


@pytest.mark.parametrize("command", ["check", "prepare"])
@pytest.mark.parametrize(
    ("key", "mode", "surface", "message"),
    [
        ("local", "headless", "manager", "does not support mode 'headless'"),
        ("local", "web", "passive-server", "Passive-server birth supports headless mode"),
        ("cloud", "web", "manager", "does not support mode 'web'"),
    ],
)
def test_incompatible_selection_fails_before_creating_run_state(
    pool_cli: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    command: str,
    key: str,
    mode: str,
    surface: str,
    message: str,
) -> None:
    """Validate both the client fixture lane and the narrower entry modes."""

    path = _write_pool(tmp_path / "model-pool.toml")
    run_root = tmp_path / "runs"
    run_options = ["--run-root", str(run_root)] if command == "prepare" else []

    assert (
        pool_cli.main(
            [
                command,
                "--model-pool",
                str(path),
                "--pool-key",
                key,
                "--mode",
                mode,
                "--surface",
                surface,
                *run_options,
            ]
        )
        == 2
    )
    assert message in json.loads(capsys.readouterr().err)["error"]
    assert not run_root.exists()


@pytest.mark.parametrize("command", ["check", "prepare"])
@pytest.mark.parametrize("pooled", [False, True])
@pytest.mark.parametrize(
    ("surface", "flags", "pool_options", "message"),
    [
        (
            "manager",
            ["--reasoning-effort", "ultra", "--reasoning-level", "5"],
            'reasoning_effort = "ultra"\nreasoning_level = 5\n',
            "Hermes reasoning_effort must be one of none, minimal, low, medium, high, xhigh, max",
        ),
        (
            "manager",
            ["--reasoning-level", "7"],
            "reasoning_level = 7\n",
            "Hermes fixture preset range 0 through 6",
        ),
        (
            "raw",
            ["--reasoning-level", "5"],
            "reasoning_level = 5\n",
            "Raw Hermes fixtures use --reasoning-effort",
        ),
        (
            "raw",
            ["--dsh-reasoning", "false"],
            "dsh_reasoning = false\n",
            "--dsh-reasoning requires --client dsh",
        ),
        (
            "raw",
            ["--reasoning-key", "analysis"],
            'reasoning_key = "analysis"\n',
            "--reasoning-key requires --client kimi",
        ),
        (
            "raw",
            ["--support-effort", "high"],
            'support_efforts = ["high"]\n',
            "--support-effort requires --client kimi",
        ),
    ],
)
def test_hermes_fixture_rejects_invalid_reasoning_before_allocating_state(
    pool_cli: ModuleType,
    hermes_env_file: Path,
    capsys: pytest.CaptureFixture[str],
    command: str,
    pooled: bool,
    surface: str,
    flags: list[str],
    pool_options: str,
    message: str,
) -> None:
    """Both fixture preflight entry points validate Hermes effort before allocating state."""

    run_root = hermes_env_file.parent / "runs"
    args = [command, "--surface", surface, "--mode", "headless"]
    if command == "prepare":
        args.extend(["--run-root", str(run_root)])
    if pooled:
        pool = _write_pool(
            hermes_env_file.parent / "model-pool.toml", _HERMES_POOL_TOML + pool_options
        )
        args.extend(["--model-pool", str(pool), "--pool-key", "hermes"])
    else:
        args.extend([*_hermes_case_args(hermes_env_file), *flags])
    assert pool_cli.main(args) == 2
    assert message in json.loads(capsys.readouterr().err)["error"]
    assert not run_root.exists()


@pytest.mark.parametrize(
    ("flag", "value"),
    [("--case", "self-hosted"), ("--auth-method", "api-key"), ("--env-file", "secret.env")],
)
def test_pool_selection_rejects_conflicting_raw_flags(
    pool_cli: ModuleType, capsys: pytest.CaptureFixture[str], flag: str, value: str
) -> None:
    """Detect competing routes before opening the pool file."""

    assert pool_cli.main(["check", "--pool-slot", "lead", flag, value]) == 2
    error = json.loads(capsys.readouterr().err)["error"]
    assert "conflict" in error and flag in error


def test_pool_slot_and_key_are_mutually_exclusive(
    pool_cli: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    """An invocation names one slot or one explicit model key."""

    with pytest.raises(SystemExit) as status:
        pool_cli.main(["check", "--pool-slot", "lead", "--pool-key", "local"])
    assert status.value.code == 2
    error = capsys.readouterr().err
    assert "--pool-key" in error and "--pool-slot" in error


def test_live_api_check_uses_only_explicit_credential_file(
    pool_cli: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Probe the configured API route with the selected key and a redacted result."""

    path = _write_pool(tmp_path / "model-pool.toml")
    credential_file = tmp_path / "separate.env"
    credential_file.touch(mode=0o600)
    endpoint = "DEEPSEEK_BASE_URL_ANTHROPIC=https://cloud.example.invalid\n"
    credential_file.write_text(endpoint)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-ambient-secret")
    monkeypatch.setenv("HOUMAO_TEST_MODEL_LEAD", "cloud")
    args = ["check", "--pool-slot", "lead", "--model-pool", str(path)]

    assert pool_cli.main(args) == 2
    error = capsys.readouterr().err
    assert "Supply nonempty DEEPSEEK_API_KEY" in error
    assert "synthetic-ambient-secret" not in error

    credential_file.write_text(endpoint + "DEEPSEEK_API_KEY=synthetic-selected-secret\n")
    launch = importlib.import_module("fixturelib.launch")
    requests: list[tuple[str, str, dict[str, Any]]] = []

    @contextmanager
    def stream(method: str, url: str, **options: Any) -> Iterator[SimpleNamespace]:
        """Capture the endpoint and response without contacting a provider."""

        requests.append((method, url, options))
        yield SimpleNamespace(status_code=405)

    monkeypatch.setattr(launch.httpx, "stream", stream)
    assert pool_cli.main(args) == 0
    assert "live" not in json.loads(capsys.readouterr().out)
    assert not requests
    assert pool_cli.main([*args, "--live"]) == 0
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["pool_key"] == "cloud" and result["pool_slot"] == "lead"
    assert result["live"] == {"http_status": 405, "status": "endpoint_reachable"}
    assert str(credential_file) not in output and "synthetic-selected-secret" not in output
    [(method, url, options)] = requests
    assert (method, url) == ("GET", "https://cloud.example.invalid/v1/models")
    assert options["headers"]["Authorization"] == "Bearer synthetic-selected-secret"
    assert options["follow_redirects"] is False


def test_live_native_check_verifies_import_without_network(
    pool_cli: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Check imported native state without assuming that it exposes a models route."""

    example = _REPO / "tests/fixtures/agent-launch/model-pool.example.toml"
    path = _write_pool(tmp_path / "model-pool.toml", example.read_text(encoding="utf-8"))
    auth_root = tmp_path / "synthetic-imports"
    launch = importlib.import_module("fixturelib.launch")
    monkeypatch.setattr(launch.httpx, "stream", lambda *a, **kw: pytest.fail("Unexpected request"))
    args = [
        "check",
        "--pool-key",
        "native_codex",
        "--model-pool",
        str(path),
        "--auth-root",
        str(auth_root),
        "--live",
    ]
    assert pool_cli.main(args) == 2
    assert "Select an imported native bundle" in capsys.readouterr().err

    bundle = auth_root / "codex/example-imported-bundle"
    (bundle / "files").mkdir(parents=True)
    (bundle / "import.json").write_text('{"client": "codex", "schema_version": 1}')
    (bundle / "files/auth.json").write_text('{"access_token": "synthetic-native-secret"}')

    assert pool_cli.main(args) == 0
    output = capsys.readouterr().out
    assert json.loads(output)["live"] == {"status": "import_validated"}
    assert str(auth_root) not in output and "synthetic-native-secret" not in output


def test_pool_and_direct_prepares_project_equivalent_dsh_inputs(
    pool_cli: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Use the same manager profile, specialist, and tool settings for both inputs."""

    local_credential_file = tmp_path / "local.env"
    local_credential_file.touch(mode=0o600)
    local_credential_file.write_text("HOUMAO_TEST_SELF_HOSTED_API_KEY=synthetic-local-secret\n")
    contents = _POOL_TOML.replace(
        "dsh_reasoning = false",
        'dsh_reasoning = { off = "none", low = "low", xhigh = "xhigh" }\n'
        'executable = "./client-bin"\n'
        'env_file = "local.env"\n'
        "reasoning_level = 2",
    )
    path = _write_pool(tmp_path / "model-pool.toml", contents)
    client_executable = tmp_path / "client-bin"
    client_executable.write_text("#!/bin/sh\nexit 99\n")
    client_executable.chmod(0o700)
    monkeypatch.setenv("HOUMAO_TEST_MODEL", "local")
    monkeypatch.delenv("HOUMAO_TEST_MODEL_LEAD", raising=False)
    base = [
        "prepare",
        "--mode",
        "web",
        "--tmux-server",
        "new",
        "--run-root",
        str(tmp_path / "runs"),
    ]
    assert pool_cli.main([*base, "--pool-slot", "lead", "--model-pool", str(path)]) == 0
    pool_report = capsys.readouterr().out
    pooled = json.loads(pool_report)

    assert (
        pool_cli.main(
            [
                *base,
                "--case",
                "self-hosted",
                "--client",
                "dsh",
                "--base-url",
                "https://local.example.invalid/v1",
                "--model",
                "example-local",
                "--context-window",
                "4096",
                "--max-output-tokens",
                "512",
                "--dsh-reasoning",
                '{"off":"none","low":"low","xhigh":"xhigh"}',
                "--reasoning-level",
                "2",
                "--env-file",
                str(local_credential_file),
                "--executable",
                str(client_executable),
            ]
        )
        == 0
    )
    direct = json.loads(capsys.readouterr().out)
    assert pooled["configuration"] == direct["configuration"]
    assert pooled["pool_key"] == "local" and pooled["pool_slot"] == "lead"
    assert "pool_key" not in direct and "pool_slot" not in direct
    pool_root = Path(pooled["run_dir"])
    direct_root = Path(direct["run_dir"])
    assert pool_root != direct_root

    prepare = importlib.import_module("fixturelib.prepare")
    run_metadata = (pool_root / "run.json").read_text()
    saved = json.loads(run_metadata)
    assert saved["pool_key"] == "local" and saved["pool_slot"] == "lead"
    assert saved["executable"] == str(client_executable)
    for payload in (run_metadata, pool_report):
        assert str(local_credential_file) not in payload
        assert str(path) not in payload and "synthetic-local-secret" not in payload

    setup = Path("assets/tools/dsh/setups/fixture/tool-params.yaml")
    assert (pool_root / setup).read_text() == (direct_root / setup).read_text()
    records = []
    for root in (pool_root, direct_root):
        env = prepare.isolated_environment({}, run_dir=root)
        project = root / "workdir"
        profile = prepare.manager_call(
            project, ["profile", "get", "--name", "fixture-agent"], env=env
        )
        specialist = prepare.manager_call(
            project, ["specialist", "get", "--name", "fixture-agent"], env=env
        )
        records.append((profile["defaults"], specialist))
    assert records[0][0] == records[1][0]
    assert records[0][0]["model"] == {"name": "example-local", "reasoning": {"level": 2}}
    for field in ("tool", "setup", "credential", "launch", "tool_params"):
        assert records[0][1][field] == records[1][1][field]


@pytest.mark.parametrize(
    ("surface", "pool_level", "override_level"),
    [("raw", None, None), ("manager", None, None), ("manager", 5, None), ("manager", 2, 5)],
)
def test_hermes_pool_and_direct_prepares_project_equivalent_reasoning(
    pool_cli: ModuleType,
    hermes_env_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    surface: str,
    pool_level: int | None,
    override_level: int | None,
) -> None:
    """Direct and pool inputs render the same reasoning settings on each launch surface."""

    tmp_path = hermes_env_file.parent
    executable = tmp_path / "hermes"
    executable.write_text("#!/bin/sh\nexit 99\n")
    executable.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ.get("PATH", os.defpath))
    pool_options = 'reasoning_effort = "xhigh"\n'
    if pool_level is not None:
        pool_options += f"reasoning_level = {pool_level}\n"
    pool = _write_pool(tmp_path / "model-pool.toml", _HERMES_POOL_TOML + pool_options)
    common = [
        "prepare",
        "--surface",
        surface,
        "--mode",
        "headless",
        "--run-root",
        str(tmp_path / "runs"),
    ]

    effective_level = override_level if override_level is not None else pool_level
    direct = [*_hermes_case_args(hermes_env_file), "--reasoning-effort", "xhigh"]
    if effective_level is not None:
        direct.extend(["--reasoning-level", str(effective_level)])
    pooled = ["--model-pool", str(pool), "--pool-key", "hermes"]
    if override_level is not None:
        pooled.extend(["--reasoning-level", str(override_level)])

    reports = []
    prepare = importlib.import_module("fixturelib.prepare")
    for args in (direct, pooled):
        assert pool_cli.main([*common, *args]) == 0
        report = json.loads(capsys.readouterr().out)
        reports.append(report)
        run_root = Path(report["run_dir"])
        if surface == "raw":
            native_config = yaml.safe_load((run_root / "home/config.yaml").read_text())
            assert native_config["agent"]["reasoning_effort"] == "xhigh"
        else:
            project = run_root / "workdir"
            setup = project / ".houmao/agents/tools/hermes/setups/fixture/tool-params.yaml"
            assert yaml.safe_load(setup.read_text()) == {
                "base_url": "https://local.example.invalid/v1",
                "reasoning_effort": "xhigh",
            }
            profile = prepare.manager_call(
                project,
                ["profile", "get", "--name", "fixture-agent"],
                env=prepare.isolated_environment({}, run_dir=run_root),
            )
            expected_model: dict[str, object] = {"name": "example-hermes"}
            if effective_level is not None:
                expected_model["reasoning"] = {"level": effective_level}
            assert profile["defaults"]["model"] == expected_model

    direct_report, pool_report = reports
    assert pool_report["configuration"] == direct_report["configuration"]
    assert pool_report["pool_key"] == "hermes"
    assert pool_report["run_dir"] != direct_report["run_dir"]


def test_pool_prepare_honors_explicit_executable_override(
    pool_cli: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An explicit executable overrides the entry on raw preparation too."""

    path = _write_pool(
        tmp_path / "model-pool.toml",
        _POOL_TOML.replace(
            "dsh_reasoning = false", 'dsh_reasoning = false\nexecutable = "./missing"'
        ),
    )
    assert (
        pool_cli.main(
            [
                "prepare",
                "--pool-key",
                "local",
                "--model-pool",
                str(path),
                "--surface",
                "raw",
                "--mode",
                "web",
                "--tmux-server",
                "new",
                "--run-root",
                str(tmp_path / "runs"),
                "--executable",
                sys.executable,
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    metadata = json.loads((Path(report["run_dir"]) / "run.json").read_text())
    assert metadata["executable"] == str(Path(sys.executable).resolve())
    assert metadata["pool_key"] == "local" and "pool_slot" not in metadata
