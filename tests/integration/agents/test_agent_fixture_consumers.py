"""Check real demo preparation against selected external fixture data."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
import tomllib

import pytest


def _prepare_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: str):
    """Render synthetic selected inputs without personal auth or a live endpoint."""

    repo = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(repo / "scripts/agents/test-fixtures"))
    config = importlib.import_module("fixturelib.config")
    prepare = importlib.import_module("fixturelib.prepare")
    selected = config.resolve_config(
        case="cloud-api",
        client=client,
        surface="raw",
        model="explicit-consumer-model",
        context_window=65536,
        process_env={
            "DEEPSEEK_API_KEY": "synthetic-consumer-secret",
            "DEEPSEEK_BASE_URL_OPENAI": "https://cloud.example/v1",
            "DEEPSEEK_BASE_URL_ANTHROPIC": "https://cloud.example/anthropic",
        },
    )
    return prepare.prepare_run(
        selected, run_root=tmp_path / "fixture-runs", executable=sys.executable
    )


@pytest.mark.parametrize(
    "package", ["single_agent_mail_wakeup", "single_agent_gateway_wakeup_headless"]
)
@pytest.mark.parametrize("client", ["claude", "codex"])
def test_mail_demo_keeps_selected_setup_model_and_secret_out_of_os_args(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    package: str,
    client: str,
) -> None:
    """Actual project commands work from external directories and keep credential ownership."""

    run = _prepare_source(tmp_path, monkeypatch, client)
    runtime = importlib.import_module(f"houmao.demo.{package}.runtime")
    models = importlib.import_module(f"houmao.demo.{package}.models")
    paths = models.build_demo_layout(demo_output_dir=tmp_path / "demo")
    paths.project_dir.mkdir(parents=True)
    env = runtime.build_demo_environment(paths=paths)
    original = runtime.run_command
    commands = []

    def observed(command, **kwargs):
        assert "synthetic-consumer-secret" not in str(command)
        commands.append(list(command))
        return original(command, **kwargs)

    monkeypatch.setattr(runtime, "run_command", observed)
    runtime.initialize_project_overlay(paths=paths, env=env, timeout_seconds=30)
    parameters = models.ToolParameters(
        provider="claude_code" if client == "claude" else "codex",
        setup="api-compatible" if client == "codex" else "default",
        auth_name="fixture",
        auth_fixture_dir=Path(run["assets_root"]) / "tools" / client / "auth/default",
        specialist_name_prefix="fixture",
        instance_name_prefix="fixture",
        session_name_prefix="fixture",
    )
    imported = runtime.import_project_auth_from_fixture(
        paths=paths,
        env=env,
        tool=client,
        tool_parameters=parameters,
        repo_root=Path(__file__).resolve().parents[3],
        timeout_seconds=30,
    )
    assert imported["prepared_run"] == run["run_dir"]
    env_file = Path(imported["env_file"])
    assert "synthetic-consumer-secret" in env_file.read_text()
    assert env_file.is_relative_to(paths.output_root)
    created = runtime.create_specialist(
        paths=paths,
        env=env,
        specialist_name="fixture-agent",
        tool=client,
        tool_parameters=parameters,
        system_prompt_file=Path(run["assets_root"]) / "roles/server-api-smoke/system-prompt.md",
        timeout_seconds=30,
    )
    assert created["specialist"] == "fixture-agent"
    if client == "codex":
        setup = paths.overlay_dir / "agents/tools/codex/setups/api-compatible/config.toml"
        payload = tomllib.loads(setup.read_text())
        assert payload["model"] == "explicit-consumer-model"
        assert (
            payload["model_providers"]["api-compatible"]["base_url"] == "https://cloud.example/v1"
        )
    assert commands
    assert not any("credentials" in command for command in commands)
    for path in paths.logs_dir.rglob("*"):
        if path.is_file():
            assert "synthetic-consumer-secret" not in path.read_text(), path


def test_writer_team_preserves_kimi_context_and_capabilities_in_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The selected bundle's metadata reaches the existing adapter-owned env channel."""

    run = _prepare_source(tmp_path, monkeypatch, "kimi")
    from houmao.demo.kimi_writer_team_manual import models, runtime

    paths = models.build_demo_layout(demo_output_dir=tmp_path / "writer-demo")
    paths.project_dir.mkdir(parents=True)
    env = runtime.build_demo_environment(paths=paths)
    runtime.initialize_project_overlay(paths=paths, env=env, timeout_seconds=30)
    bundle = Path(run["assets_root"]) / "tools/kimi/auth/default"
    arguments, _ = runtime.build_kimi_credential_args_from_bundle(bundle_dir=bundle)
    original = runtime.run_command

    def observed(command, **kwargs):
        assert "synthetic-consumer-secret" not in str(command)
        return original(command, **kwargs)

    monkeypatch.setattr(runtime, "run_command", observed)
    result = runtime.upsert_kimi_credential(
        paths=paths,
        env=env,
        credential_name="fixture",
        credential_args=arguments,
        timeout_seconds=30,
        fixture_bundle=bundle,
    )
    material = Path(result["env_file"]).read_text()
    assert "KIMI_MODEL_MAX_CONTEXT_SIZE=65536" in material
    assert "KIMI_MODEL_CAPABILITIES=tool_use" in material
    for path in paths.logs_dir.rglob("*"):
        if path.is_file():
            assert "synthetic-consumer-secret" not in path.read_text()
