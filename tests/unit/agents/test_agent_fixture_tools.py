"""Hermetic behavior checks for the development test-agent fixture tools."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib
from types import ModuleType

import pytest
import yaml

_REPO = Path(__file__).resolve().parents[3]
_TOOL_ROOT = _REPO / "scripts/agents/test-fixtures"


@pytest.fixture
def fixture_config(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load utility code without making it a production package dependency."""

    monkeypatch.syspath_prepend(str(_TOOL_ROOT))
    return importlib.import_module("fixturelib.config")


@pytest.fixture
def fixture_auth(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load auth utilities with no discovery or personal I/O during import."""

    monkeypatch.syspath_prepend(str(_TOOL_ROOT))
    return importlib.import_module("fixturelib.auth")


@pytest.fixture
def fixture_prepare(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load private preparation utilities without starting any provider process."""

    monkeypatch.syspath_prepend(str(_TOOL_ROOT))
    return importlib.import_module("fixturelib.prepare")


@pytest.fixture
def fixture_launch(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load explicit launch operations without starting a live provider."""

    monkeypatch.syspath_prepend(str(_TOOL_ROOT))
    return importlib.import_module("fixturelib.launch")


def _env(case: str) -> dict[str, str]:
    """Return synthetic values for either case, without reading developer state."""

    if case == "cloud-api":
        return {
            "DEEPSEEK_API_KEY": "synthetic-fixture-secret",
            "DEEPSEEK_BASE_URL_ANTHROPIC": "https://cloud.example/anthropic",
            "DEEPSEEK_BASE_URL_OPENAI": "https://cloud.example",
            "HOUMAO_TEST_CLOUD_MODEL": "arbitrary-model",
            "HOUMAO_TEST_CLOUD_CONTEXT_WINDOW": "16384",
        }
    return {
        "HOUMAO_TEST_SELF_HOSTED_MODEL": "another-model",
        "HOUMAO_TEST_SELF_HOSTED_ANTHROPIC_BASE_URL": "http://localhost:19001",
        "HOUMAO_TEST_SELF_HOSTED_OPENAI_BASE_URL": "http://localhost:19001/custom/v1",
        "HOUMAO_TEST_SELF_HOSTED_CONTEXT_WINDOW": "8192",
    }


@pytest.mark.parametrize("client", ["claude", "codex", "kimi"])
@pytest.mark.parametrize("case", ["self-hosted", "cloud-api"])
@pytest.mark.parametrize("mode", ["headless", "tui"])
def test_case_resolution_has_no_model_or_account_defaults(
    fixture_config: ModuleType, client: str, case: str, mode: str
) -> None:
    """All client/case/mode combinations resolve explicit independent inputs."""

    config = fixture_config.resolve_config(
        case=case, client=client, mode=mode, process_env=_env(case)
    )
    assert (
        config.model
        == _env(case)[
            "HOUMAO_TEST_CLOUD_MODEL" if case == "cloud-api" else "HOUMAO_TEST_SELF_HOSTED_MODEL"
        ]
    )
    assert config.protocol == fixture_config.CLIENT_PROTOCOL[client]
    assert config.mode == mode and config.model_options.reasoning_effort is None
    assert config.model_options.capabilities == ["tool_use"]
    public = json.dumps(config.summary())
    assert "synthetic-fixture-secret" not in public
    assert "synthetic-fixture-secret" not in repr(config)
    if case == "self-hosted":
        assert config.api_key.get_secret_value() == "EMPTY"


def test_env_precedence_and_literal_quoting(fixture_config: ModuleType, tmp_path: Path) -> None:
    """Explicit input wins over process refs, which win over the selected file."""

    env_file = tmp_path / "private.env"
    env_file.write_text(
        'export DEEPSEEK_API_KEY="file-secret"\n'
        'DEEPSEEK_BASE_URL_OPENAI="https://file.example/v1"\n'
        "HOUMAO_TEST_CLOUD_MODEL='file-model' # model comment\n"
    )
    config = fixture_config.resolve_config(
        case="cloud-api",
        client="codex",
        model="explicit-model",
        env_file=env_file,
        process_env={"DEEPSEEK_API_KEY": "process-secret"},
    )
    assert config.model == "explicit-model"
    assert config.api_key.get_secret_value() == "process-secret"
    assert config.base_url == "https://file.example/v1"


@pytest.mark.parametrize(
    "syntax", ["$(touch target)", "`touch target`", "${OTHER}", "x; touch target"]
)
def test_env_file_does_not_execute_or_echo_input(
    fixture_config: ModuleType, tmp_path: Path, syntax: str
) -> None:
    """Executable/unsupported syntax fails safely without executing anything."""

    path = tmp_path / "private.env"
    path.write_text("DEEPSEEK_API_KEY=" + syntax + "\n")
    with pytest.raises(fixture_config.FixtureError) as caught:
        fixture_config.read_env_file(path)
    assert syntax not in str(caught.value)
    assert not (tmp_path / "target").exists()


def test_cloud_key_cannot_fall_back_to_anonymous_or_native_auth(fixture_config: ModuleType) -> None:
    """A missing cloud key cannot silently use another account or a dummy key."""

    env = _env("cloud-api")
    env.pop("DEEPSEEK_API_KEY")
    env["OPENAI_API_KEY"] = "unrelated-account"
    with pytest.raises(fixture_config.FixtureError, match="DEEPSEEK_API_KEY"):
        fixture_config.resolve_config(case="cloud-api", client="codex", process_env=env)


def test_missing_model_and_kimi_context_are_explicit(fixture_config: ModuleType) -> None:
    """No previous model's name/context can fill missing selected metadata."""

    env = _env("cloud-api")
    env.pop("HOUMAO_TEST_CLOUD_MODEL")
    with pytest.raises(fixture_config.FixtureError, match="--model"):
        fixture_config.resolve_config(case="cloud-api", client="codex", process_env=env)
    env["HOUMAO_TEST_CLOUD_MODEL"] = "chosen-model"
    env.pop("HOUMAO_TEST_CLOUD_CONTEXT_WINDOW")
    with pytest.raises(fixture_config.FixtureError, match="--context-window"):
        fixture_config.resolve_config(case="cloud-api", client="kimi", process_env=env)


def test_chat_only_descriptor_cannot_satisfy_codex(
    fixture_config: ModuleType, tmp_path: Path
) -> None:
    """Endpoint protocol declarations cannot be inferred from a shared URL."""

    original = _REPO / "tests/fixtures/agent-launch/self-hosted.yaml"
    payload = yaml.safe_load(original.read_text())
    payload["endpoints"] = {"openai_chat": payload["endpoints"]["openai_chat"]}
    descriptor = tmp_path / "case.yaml"
    descriptor.write_text(yaml.safe_dump(payload))
    with pytest.raises(fixture_config.FixtureError, match="openai_responses"):
        fixture_config.resolve_config(
            case="self-hosted",
            client="codex",
            process_env=_env("self-hosted"),
            descriptor_path=descriptor,
        )


@pytest.mark.parametrize(
    "extra", [{"model": "fixed-model"}, {"api_key": "private"}, {"schema_version": 2}]
)
def test_descriptor_rejects_unknown_fields_and_versions(
    fixture_config: ModuleType, tmp_path: Path, extra: dict[str, object]
) -> None:
    """Descriptors carry references, never inline account or model defaults."""

    payload = yaml.safe_load((_REPO / "tests/fixtures/agent-launch/cloud-api.yaml").read_text())
    descriptor = tmp_path / "case.yaml"
    descriptor.write_text(yaml.safe_dump({**payload, **extra}))
    with pytest.raises(fixture_config.FixtureError, match="Invalid case descriptor"):
        fixture_config.load_descriptor(descriptor)


def test_protocol_paths_are_preserved_or_rejected_explicitly(fixture_config: ModuleType) -> None:
    """Client root conventions do not silently rewrite operator routing."""

    config = fixture_config.resolve_config(
        case="self-hosted", client="codex", process_env=_env("self-hosted")
    )
    assert config.base_url == "http://localhost:19001/custom/v1"
    with pytest.raises(fixture_config.FixtureError, match="before its appended"):
        fixture_config.resolve_config(
            case="self-hosted",
            client="claude",
            process_env=_env("self-hosted"),
            base_url="http://localhost:19001/v1",
        )
    with pytest.raises(fixture_config.FixtureError, match="without credentials"):
        fixture_config.resolve_config(
            case="cloud-api",
            client="codex",
            process_env=_env("cloud-api"),
            base_url="https://private-secret@host.example/v1",
        )


def test_documented_example_resolves_only_after_explicit_values(
    fixture_config: ModuleType,
) -> None:
    """The tracked env example contains no usable saved key or model selection."""

    example = _REPO / "tests/fixtures/agent-launch/.env.example"
    values = fixture_config.read_env_file(example)
    assert not values["DEEPSEEK_API_KEY"] and not values["HOUMAO_TEST_CLOUD_MODEL"]
    values.update(_env("cloud-api"))
    config = fixture_config.resolve_config(case="cloud-api", client="kimi", process_env=values)
    assert config.model_options.context_window == 16384
    with pytest.raises(fixture_config.FixtureError, match="supports headless"):
        fixture_config.resolve_config(
            case="cloud-api",
            client="kimi",
            mode="tui",
            surface="passive-server",
            process_env=values,
        )


@pytest.mark.parametrize("kind", ["auth", "run"])
def test_private_roots_respect_xdg_and_reject_checkout_symlinks(
    fixture_auth: ModuleType, tmp_path: Path, kind: str
) -> None:
    """Private root selection cannot resolve back into tracked source space."""

    repo = tmp_path / "repo"
    repo.mkdir()
    root = fixture_auth.external_root(
        kind,
        process_env={
            "XDG_DATA_HOME": str(tmp_path / "data"),
            "XDG_STATE_HOME": str(tmp_path / "state"),
        },
        user_home=tmp_path / "user",
        repo_root=repo,
        create=True,
    )
    assert root.is_relative_to(tmp_path / ("data" if kind == "auth" else "state"))
    assert root.stat().st_mode & 0o777 == 0o700
    link = tmp_path / "outside-link"
    link.symlink_to(repo, target_is_directory=True)
    with pytest.raises(ValueError, match="outside the checkout"):
        fixture_auth.external_root(kind, override=link / "auth", repo_root=repo, create=True)
    assert not (repo / "auth").exists()


def _native_home(tmp_path: Path, client: str) -> tuple[Path, Path]:
    """Write one entirely synthetic native auth source and unrelated history."""

    home = tmp_path / client
    filename = {
        "claude": ".credentials.json",
        "codex": "auth.json",
        "kimi": "credentials/kimi-code.json",
    }[client]
    payload = {
        "claude": {"claudeAiOauth": {"accessToken": "synthetic-native-secret"}},
        "codex": {"tokens": {"access_token": "synthetic-native-secret"}},
        "kimi": {"access_token": "synthetic-native-secret"},
    }[client]
    source = home / filename
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps(payload, indent=4) + "\n")
    (home / "sessions").mkdir()
    (home / "sessions/old.txt").write_text("unrelated private history")
    if client == "claude":
        (home / ".claude.json").write_text("{}\n")
    if client == "kimi":
        (home / "config.toml").write_text('default_model = "native-model"\n')
    return home, source


@pytest.mark.parametrize("client", ["claude", "codex", "kimi"])
def test_discovery_and_import_preserve_opaque_source_without_history(
    fixture_auth: ModuleType, tmp_path: Path, client: str
) -> None:
    """Selected files survive exact copying while personal state is left behind."""

    home, source = _native_home(tmp_path, client)
    before = source.read_bytes(), source.stat().st_mtime_ns, source.stat().st_mode
    candidates = fixture_auth.discover_auth(
        client,
        process_env={fixture_auth.HOME_VARIABLE[client]: str(home)},
        user_home=tmp_path / "empty-user",
        search_roots=[home],
    )
    usable = [item for item in candidates if item.importable]
    assert len(usable) == 1
    assert "synthetic-native-secret" not in json.dumps(usable[0].summary())
    bundle = fixture_auth.import_auth(usable[0], name="chosen", auth_root=tmp_path / "store")
    filename = "credentials/kimi-code.json" if client == "kimi" else source.name
    copied = bundle / "files" / filename
    assert copied.read_bytes() == before[0]
    assert copied.stat().st_mode & 0o777 == 0o600
    assert not list(bundle.rglob("old.txt"))
    assert (source.read_bytes(), source.stat().st_mtime_ns, source.stat().st_mode) == before
    with pytest.raises(ValueError, match="already exists"):
        fixture_auth.import_auth(usable[0], name="chosen", auth_root=tmp_path / "store")
    fixture_auth.import_auth(usable[0], name="chosen", auth_root=tmp_path / "store", replace=True)
    assert copied.read_bytes() == before[0]


def test_search_scope_excludes_escaping_links_and_history(
    fixture_auth: ModuleType, tmp_path: Path
) -> None:
    """An explicit search root never broadens into unrelated native credential state."""

    _, secret_source = _native_home(tmp_path / "outside", "codex")
    root = tmp_path / "search"
    root.mkdir()
    (root / "auth.json").symlink_to(secret_source)
    (root / "sessions").mkdir()
    (root / "sessions/auth.json").write_bytes(secret_source.read_bytes())
    assert (
        fixture_auth.discover_auth(
            "codex",
            process_env={},
            user_home=tmp_path / "empty-user",
            search_roots=[root],
            include_defaults=False,
        )
        == []
    )


@pytest.mark.parametrize(
    "content", ["{}", "not-json", '"not-object"', '{"unrecognized":"synthetic-secret"}']
)
def test_unusable_auth_is_reported_without_secret_content(
    fixture_auth: ModuleType, tmp_path: Path, content: str
) -> None:
    """Shape validation cannot turn an existing filename into a valid login claim."""

    source = tmp_path / "auth.json"
    source.write_text(content)
    candidate = fixture_auth.candidate_from_source("codex", source)
    assert not candidate.importable and candidate.reason
    assert "synthetic-secret" not in json.dumps(candidate.summary())
    with pytest.raises(ValueError, match="cannot be imported"):
        fixture_auth.import_auth(candidate, name="bad", auth_root=tmp_path / "store")
    assert not (tmp_path / "store").exists()


def test_distinct_attempts_never_share_private_run_identity(
    fixture_auth: ModuleType, fixture_config: ModuleType, tmp_path: Path
) -> None:
    """Concurrent prepares for the same lane allocate separate owned directories."""

    from concurrent.futures import ThreadPoolExecutor

    config = fixture_config.resolve_config(
        case="cloud-api", client="codex", process_env=_env("cloud-api")
    )
    with ThreadPoolExecutor(max_workers=4) as pool:
        runs = list(
            pool.map(
                lambda _: fixture_auth.allocate_run(config, run_root=tmp_path / "runs"), range(8)
            )
        )
    assert len(set(runs)) == 8
    assert all(path.stat().st_mode & 0o777 == 0o700 for path in runs)


def test_cli_discovery_requires_deliberate_import_selection(tmp_path: Path) -> None:
    """The documented subprocess flow lists ambiguity without writing credentials."""

    _, source = _native_home(tmp_path / "sources", "codex")
    command = [sys.executable, str(_TOOL_ROOT / "fixture.py")]
    env = {"PATH": os.defpath, "HOME": str(tmp_path / "empty-user")}
    result = subprocess.run(
        [
            *command,
            "import-auth",
            "--client",
            "codex",
            "--name",
            "work",
            "--no-defaults",
            "--search-root",
            str(source.parent),
            "--auth-root",
            str(tmp_path / "store"),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    error = json.loads(result.stderr)
    assert error["candidates"][0]["importable"]
    assert "synthetic-native-secret" not in result.stderr
    assert not (tmp_path / "store").exists()
    result = subprocess.run(
        [
            *command,
            "import-auth",
            "--client",
            "codex",
            "--name",
            "work",
            "--source",
            str(source),
            "--auth-root",
            str(tmp_path / "store"),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    bundle = Path(json.loads(result.stdout)["bundle_path"])
    assert (bundle / "files/auth.json").read_bytes() == source.read_bytes()
    assert "synthetic-native-secret" not in result.stdout


def test_cli_offline_check_does_not_print_key(tmp_path: Path) -> None:
    """A real helper process resolves the documented case with synthetic env only."""

    result = subprocess.run(
        [
            sys.executable,
            str(_TOOL_ROOT / "fixture.py"),
            "check",
            "--case",
            "cloud-api",
            "--client",
            "codex",
            "--model",
            "selected",
        ],
        env={"PATH": os.defpath, **_env("cloud-api")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["configuration"]["model"] == "selected"
    assert "synthetic-fixture-secret" not in result.stdout + result.stderr


def test_native_codex_config_is_not_silently_retargeted(
    fixture_auth: ModuleType, tmp_path: Path
) -> None:
    """A custom provider needs explicit API preparation instead of guessed routing."""

    home, source = _native_home(tmp_path, "codex")
    (home / "config.toml").write_text('model_provider = "another-gateway"\n')
    candidate = fixture_auth.candidate_from_source("codex", source)
    assert not candidate.importable
    assert candidate.reason == "custom_provider_config_requires_explicit_api_case"


@pytest.mark.parametrize("client", ["claude", "codex", "kimi"])
@pytest.mark.parametrize("case", ["self-hosted", "cloud-api"])
def test_raw_preparation_has_selected_settings_without_shared_credentials(
    fixture_config: ModuleType,
    fixture_prepare: ModuleType,
    tmp_path: Path,
    client: str,
    case: str,
) -> None:
    """Generated configs and private env agree with selected inputs, without history."""

    config = fixture_config.resolve_config(
        case=case,
        client=client,
        surface="raw",
        process_env=_env(case),
    )
    run = fixture_prepare.prepare_run(config, run_root=tmp_path / "runs", executable=sys.executable)
    root = Path(run["run_dir"])
    env = json.loads((root / "private-env.json").read_text())
    assert env[fixture_config.HOME_VARIABLE[client]] == run["home_path"]
    assert not (root / "home/sessions").exists()
    assert "synthetic-fixture-secret" not in (root / "run.json").read_text()
    assert (root / "private-env.json").stat().st_mode & 0o777 == 0o600
    if client == "codex":
        native = tomllib.loads((root / "home/config.toml").read_text())
        provider = native["model_providers"][native["model_provider"]]
        assert provider["base_url"] == config.base_url and provider["wire_api"] == "responses"
        assert provider["env_key"] == "OPENAI_API_KEY" and not provider["requires_openai_auth"]
        assert "synthetic-fixture-secret" not in (root / "home/config.toml").read_text()
    elif client == "kimi":
        assert env["KIMI_MODEL_MAX_CONTEXT_SIZE"] == str(config.model_options.context_window)
        assert env["KIMI_MODEL_CAPABILITIES"] == "tool_use"
    else:
        assert env["ANTHROPIC_MODEL"] == config.model
        assert env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == config.model


@pytest.mark.parametrize("client", ["claude", "codex", "kimi"])
def test_native_preparation_copies_auth_without_api_routing(
    fixture_config: ModuleType,
    fixture_auth: ModuleType,
    fixture_prepare: ModuleType,
    tmp_path: Path,
    client: str,
) -> None:
    """A prepared native home cannot write through to source or imported login files."""

    _, source = _native_home(tmp_path / "sources", client)
    bundle = fixture_auth.import_auth(
        fixture_auth.candidate_from_source(client, source),
        name="native",
        auth_root=tmp_path / "store",
    )
    config = fixture_config.ResolvedConfig(
        client=client,
        mode="headless",
        surface="raw",
        auth_method="native-login",
        native_bundle=bundle,
    )
    run = fixture_prepare.prepare_run(config, run_root=tmp_path / "runs", executable=sys.executable)
    env = json.loads((Path(run["run_dir"]) / "private-env.json").read_text())
    assert "ANTHROPIC_BASE_URL" not in env and "KIMI_MODEL_BASE_URL" not in env
    filename = "credentials/kimi-code.json" if client == "kimi" else source.name
    home_auth = Path(run["home_path"]) / filename
    assert home_auth.read_bytes() == source.read_bytes()
    home_auth.write_text("client refresh changed only its private copy")
    assert (bundle / "files" / filename).read_bytes() == source.read_bytes()


@pytest.mark.parametrize("client", ["claude", "codex", "kimi"])
def test_managed_preparation_uses_real_project_credential_projection(
    fixture_config: ModuleType,
    fixture_prepare: ModuleType,
    tmp_path: Path,
    client: str,
) -> None:
    """Real project catalogs receive the same selected inputs without launching clients."""

    config = fixture_config.resolve_config(
        case="cloud-api", client=client, process_env=_env("cloud-api")
    )
    run = fixture_prepare.prepare_run(config, run_root=tmp_path / "runs", executable=sys.executable)
    root = Path(run["run_dir"])
    project = Path(run["project_dir"])
    assert (project / ".houmao/houmao-config.toml").exists()
    assert run["specialist"]["specialist"] == "fixture-agent"
    assert "synthetic-fixture-secret" not in (root / "run.json").read_text()
    credential_env = Path(run["credential"]["env_file"])
    assert credential_env.is_relative_to(root)
    assert "synthetic-fixture-secret" in credential_env.read_text()
    if client == "kimi":
        assert "KIMI_MODEL_MAX_CONTEXT_SIZE=16384" in credential_env.read_text()


def test_sanitized_launch_env_overrides_ambient_accounts_and_tmux_bindings(
    fixture_prepare: ModuleType,
    tmp_path: Path,
) -> None:
    """Only selected credentials/routing survive inherited environment construction."""

    env = fixture_prepare.isolated_environment(
        {"ANTHROPIC_AUTH_TOKEN": "selected"},
        run_dir=tmp_path,
        process_env={
            "PATH": "/bin",
            "OPENAI_API_KEY": "other-account",
            "ANTHROPIC_MODEL": "other-model",
            "HOUMAO_PROJECT_OVERLAY_DIR": "/other/project",
        },
    )
    assert env["OPENAI_API_KEY"] == "" and env["ANTHROPIC_MODEL"] == ""
    assert env["ANTHROPIC_AUTH_TOKEN"] == "selected"
    assert env["HOUMAO_PROJECT_OVERLAY_DIR"] == str(tmp_path / "workdir/.houmao")


def test_generic_codex_build_resolves_endpoint_and_rejects_conflicting_accounts(
    tmp_path: Path,
) -> None:
    """The shipped template cannot accidentally fall back to a first-party endpoint."""

    from houmao.agents.brain_builder import BuildError, _resolve_codex_api_routing

    path = tmp_path / "config.toml"
    path.write_bytes(
        (
            _REPO / "tests/fixtures/plain-agent-def/tools/codex/setups/api-compatible/config.toml"
        ).read_bytes()
    )
    with pytest.raises(BuildError, match="explicit OPENAI_BASE_URL"):
        _resolve_codex_api_routing(tool="codex", home_path=tmp_path, env_values={})
    _resolve_codex_api_routing(
        tool="codex",
        home_path=tmp_path,
        env_values={"OPENAI_BASE_URL": "https://selected.example/gateway/v1"},
    )
    assert (
        tomllib.loads(path.read_text())["model_providers"]["api-compatible"]["base_url"]
        == "https://selected.example/gateway/v1"
    )
    with pytest.raises(BuildError, match="different endpoints"):
        _resolve_codex_api_routing(
            tool="codex",
            home_path=tmp_path,
            env_values={"OPENAI_BASE_URL": "https://another.example"},
        )


def test_fixture_presets_and_starter_adapters_have_current_explicit_contract() -> None:
    """Tracked seeds expose generic variants and all required managed env channels."""

    fixture = _REPO / "tests/fixtures/plain-agent-def"
    assert (fixture / "presets/gpu-kernel-coder-codex-api-compatible.yaml").is_file()
    for path in (fixture / "presets").glob("*.yaml"):
        payload = yaml.safe_load(path.read_text())
        assert "auth" not in payload
        assert payload["setup"] != "yunwu-openai"
    for client in ("claude", "codex", "kimi"):
        expected = yaml.safe_load((fixture / "tools" / client / "adapter.yaml").read_text())
        actual = yaml.safe_load(
            (
                _REPO / "src/houmao/project/assets/starter_agents/tools" / client / "adapter.yaml"
            ).read_text()
        )
        assert actual == expected
        names = actual["auth_projection"]["env"]["allowlist"]
        if client == "kimi":
            assert {
                "KIMI_MODEL_MAX_CONTEXT_SIZE",
                "KIMI_MODEL_CAPABILITIES",
                "KIMI_MODEL_REASONING_KEY",
            } <= set(names)


def _client_stub(path: Path, client: str) -> str:
    """Create a harmless client that records selected bindings and emits identity."""

    path.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, sys, time\n"
        f"client = {client!r}\n"
        "if '--version' in sys.argv:\n"
        " print(client + ' fixture 1.0'); sys.exit(0)\n"
        "keys=('ANTHROPIC_AUTH_TOKEN','ANTHROPIC_API_KEY','ANTHROPIC_BASE_URL',"
        "'OPENAI_API_KEY','OPENAI_BASE_URL','KIMI_MODEL_API_KEY','KIMI_MODEL_BASE_URL')\n"
        "pathlib.Path('effective-env.json').write_text(json.dumps({k:os.getenv(k) for k in keys}))\n"
        "if '--json' in sys.argv or '--output-format' in sys.argv:\n"
        " print(json.dumps({'type':'thread.started','thread_id':'synthetic-session'}) if client=='codex' "
        "else json.dumps({'session_id':'synthetic-session','type':'system'}))\n"
        "else: time.sleep(60)\n"
    )
    path.chmod(0o700)
    return str(path)


@pytest.mark.parametrize("client", ["claude", "codex", "kimi"])
@pytest.mark.parametrize("case", ["self-hosted", "cloud-api"])
def test_raw_launch_and_exact_resume_use_selected_private_environment(
    fixture_config: ModuleType,
    fixture_prepare: ModuleType,
    fixture_launch: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    client: str,
    case: str,
) -> None:
    """Actual harmless child processes receive routing and explicit resume selection."""

    config = fixture_config.resolve_config(
        case=case, client=client, surface="raw", process_env=_env(case)
    )
    run = fixture_prepare.prepare_run(
        config, run_root=tmp_path / "runs", executable=_client_stub(tmp_path / "client", client)
    )
    root = Path(run["run_dir"])
    monkeypatch.setenv("OPENAI_API_KEY", "competing-ambient-secret")
    first = fixture_launch.launch_run(root, prompt="first", timeout=5)
    second = fixture_launch.prompt_run(root, prompt="second", timeout=5)
    assert first["identity"]["provider_session_id"] == "synthetic-session"
    assert len(second["turns"]) == 2
    command = fixture_launch.raw_command(fixture_prepare.load_run(root), prompt="third")
    assert "synthetic-session" in command
    if client == "kimi":
        assert "--auto" not in command and "--print" not in command
    child = json.loads((root / "workdir/effective-env.json").read_text())
    name = {
        "claude": "ANTHROPIC_AUTH_TOKEN",
        "codex": "OPENAI_API_KEY",
        "kimi": "KIMI_MODEL_API_KEY",
    }[client]
    assert child[name] == config.api_key.get_secret_value()
    assert "competing-ambient-secret" not in child.values()
    assert config.api_key.get_secret_value() not in (root / "report.json").read_text()
    assert fixture_launch.check_run(root)["prerequisites"]["live_requested"] is False
    assert fixture_launch.stop_run(root)["status"] == "stopped"


def test_partial_manager_launch_retains_identity_and_cleans_only_its_agent(
    fixture_config: ModuleType,
    fixture_prepare: ModuleType,
    fixture_launch: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed gateway attachment does not lose the already created managed identity."""

    config = fixture_config.resolve_config(
        case="cloud-api", client="claude", process_env=_env("cloud-api")
    )
    run = fixture_prepare.prepare_run(config, run_root=tmp_path / "runs", executable=sys.executable)
    root = Path(run["run_dir"])

    def failed(*_args, **_kwargs):
        raise fixture_prepare.ManagedCommandError(
            "sanitized failure", {"agent_id": "only-owned-agent"}
        )

    calls = []
    monkeypatch.setattr(fixture_launch, "manager_call", failed)
    monkeypatch.setattr(
        fixture_launch, "manager_root_call", lambda args, **_kw: calls.append(args) or {}
    )
    with pytest.raises(fixture_config.FixtureError, match="inspect"):
        fixture_launch.launch_run(root)
    metadata = fixture_prepare.load_run(root)
    assert metadata["status"] == "launch_failed"
    assert metadata["identity"]["agent_id"] == "only-owned-agent"
    assert calls == [["agents", "single", "--agent-id", "only-owned-agent", "stop"]]
    assert metadata["cleanup"] == "stopped_owned_identity"


def test_passive_headless_creation_and_turn_use_maintained_http_contract(
    fixture_config: ModuleType,
    fixture_prepare: ModuleType,
    fixture_launch: ModuleType,
    tmp_path: Path,
) -> None:
    """A real local HTTP authority receives brain creation and scoped headless turns."""

    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading

    requests = []

    class Handler(BaseHTTPRequestHandler):
        """Return controlled public responses without logging private requests."""

        def log_message(self, *_args):
            """Suppress default HTTP request logging."""

        def do_POST(self):
            """Accept current launch, turn, and stop request bodies."""
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append((self.path, body))
            if self.path.endswith("launches"):
                assert Path(body["brain_manifest_path"]).is_file()
                response = {
                    "tracked_agent_id": "captured-passive-id",
                    "manifest_path": "/controlled/manifest",
                }
            elif self.path.endswith("/turns"):
                response = {"turn_id": "turn-1"}
            else:
                response = {"status": "ok"}
            self._reply(response)

        def do_GET(self):
            """Finish the controlled headless turn."""
            requests.append((self.path, None))
            self._reply({"status": "completed", "returncode": 0})

        def _reply(self, body):
            """Send a structured local response."""
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config = fixture_config.resolve_config(
            case="cloud-api",
            client="codex",
            surface="passive-server",
            process_env=_env("cloud-api"),
        )
        run = fixture_prepare.prepare_run(
            config, run_root=tmp_path / "runs", executable=sys.executable
        )
        root = Path(run["run_dir"])
        with pytest.raises(fixture_config.FixtureError, match="--passive-url"):
            fixture_launch.launch_run(root)
        result = fixture_launch.launch_run(
            root, passive_url=f"http://127.0.0.1:{server.server_port}", prompt="controlled"
        )
        assert result["identity"]["tracked_agent_id"] == "captured-passive-id"
        assert result["turns"][0]["status"] == "completed"
        fixture_launch.stop_run(root)
        assert requests[0][0] == "/houmao/agents/headless/launches"
        assert requests[1] == ("/houmao/agents/captured-passive-id/turns", {"prompt": "controlled"})
        assert requests[-1][0] == "/houmao/agents/captured-passive-id/stop"
        assert "synthetic-fixture-secret" not in json.dumps(requests)
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.mark.parametrize("client", ["claude", "codex", "kimi"])
def test_auth_discovery_rejects_non_string_token_values(
    fixture_auth: ModuleType,
    tmp_path: Path,
    client: str,
) -> None:
    """Malformed credential objects cannot qualify merely because a value is truthy."""

    home, source = _native_home(tmp_path / "native", client)
    source.write_text(
        json.dumps(
            {
                "claude": {"claudeAiOauth": {"accessToken": {"not": "a token"}}},
                "codex": {"tokens": {"access_token": True}},
                "kimi": {"access_token": 123},
            }[client]
        )
    )
    candidate = fixture_auth.candidate_from_source(client, home)
    assert candidate.importable is False


def test_offline_check_reports_missing_private_prerequisites_without_network(
    fixture_config: ModuleType,
    fixture_prepare: ModuleType,
    fixture_launch: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An offline check cannot turn a missing executable into a readiness pass."""

    config = fixture_config.resolve_config(
        case="cloud-api", client="codex", surface="raw", process_env=_env("cloud-api")
    )
    executable = Path(_client_stub(tmp_path / "client", "codex"))
    run = fixture_prepare.prepare_run(
        config, run_root=tmp_path / "runs", executable=str(executable)
    )
    executable.unlink()

    def no_network(*_args, **_kwargs):
        raise AssertionError("offline checks must not contact an authority")

    monkeypatch.setattr(fixture_launch, "_http", no_network)
    result = fixture_launch.check_run(Path(run["run_dir"]))
    assert result["prerequisites"]["missing"] == ["client_executable"]


def test_gateway_detach_failure_still_attempts_owned_runtime_stop(
    fixture_config: ModuleType,
    fixture_prepare: ModuleType,
    fixture_launch: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A dead gateway cannot prevent cleanup of the captured runtime identity."""

    config = fixture_config.resolve_config(
        case="cloud-api", client="claude", process_env=_env("cloud-api")
    )
    run = fixture_prepare.prepare_run(config, run_root=tmp_path / "runs", executable=sys.executable)
    run["identity"] = {"agent_id": "owned-id", "gateway_port": 12345}
    calls = []

    def command(args, **_kwargs):
        calls.append(args)
        if args[-1] == "detach":
            raise fixture_config.FixtureError("controlled dead gateway")
        return {"status": "ok"}

    monkeypatch.setattr(fixture_launch, "manager_root_call", command)
    fixture_launch._cleanup(run)
    assert calls[-1] == ["agents", "single", "--agent-id", "owned-id", "stop"]


def test_failed_managed_turn_cannot_be_reported_as_successful_qualification(
    fixture_config: ModuleType,
    fixture_prepare: ModuleType,
    fixture_launch: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A finalized failed row must fail the prompt operation while retaining its evidence."""

    config = fixture_config.resolve_config(
        case="cloud-api", client="codex", process_env=_env("cloud-api")
    )
    run = fixture_prepare.prepare_run(config, run_root=tmp_path / "runs", executable=sys.executable)
    root = Path(run["run_dir"])
    run.update(
        status="launched",
        identity={"agent_id": "owned-id", "gateway_host": "127.0.0.1", "gateway_port": 12345},
    )
    fixture_prepare.write_json(root / "run.json", run)
    pages = iter([{"records": []}, {"records": [{"record_id": "failed-row", "outcome": "failed"}]}])
    monkeypatch.setattr(
        fixture_launch,
        "_http",
        lambda _base, _path, body=None: {"status": "ok"} if body is not None else next(pages),
    )
    with pytest.raises(fixture_config.FixtureError, match="did not complete"):
        fixture_launch.prompt_run(root, prompt="controlled")
    saved = fixture_prepare.load_run(root)
    assert saved["turns"] == [{"record_id": "failed-row", "status": "failed"}]
