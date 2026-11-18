"""Verify DSH selection, isolated brain projection, and API-only credentials."""

from __future__ import annotations

from dataclasses import replace
from importlib.resources import files
import json
from pathlib import Path
import shutil
from typing import Any
from types import SimpleNamespace

from click.testing import CliRunner
import pytest
import yaml

from houmao.agents.brain_builder import BuildError, BuildRequest, build_brain_home
from houmao.agents.dsh_configuration import DshSetup, load_dsh_home
from houmao.agents.launch_overrides import LaunchDefaults, ToolLaunchMetadata
from houmao.agents.launch_overrides.resolver import resolve_launch_behavior
from houmao.agents.launch_policy.models import SupportedVersionSpec, ToolVersion
from houmao.agents.model_mapping_policy import (
    resolve_reasoning_mapping,
    temporary_project_model_config,
)
from houmao.agents.model_selection import ModelConfig, ModelReasoningConfig
from houmao.agents.realm_controller.backends.dsh_acp import DshAcpSession
from houmao.agents.realm_controller.backends.headless_base import HeadlessSessionState
from houmao.agents.realm_controller.errors import LaunchPlanError
from houmao.agents.realm_controller.launch_plan import (
    LaunchPlanRequest,
    backend_for_tool,
    build_launch_plan,
)
from houmao.agents.realm_controller.loaders import RolePackage
from houmao.agents.realm_controller.runtime import RuntimeSessionController
from houmao.srv_ctrl.commands.main import cli
from houmao.project.overlay import require_project_overlay


def _seed(tmp_path: Path) -> BuildRequest:
    """Prepare synthetic explicit credentials and a two-model DSH catalog."""

    definitions = tmp_path / "agents"
    source = (
        Path(__file__).resolve().parents[3] / "src/houmao/project/assets/starter_agents/tools/dsh"
    )
    tool = definitions / "tools/dsh"
    shutil.copytree(source, tool)
    (definitions / "skills").mkdir(parents=True)
    setup: dict[str, Any] = {
        "version": 1,
        "provider": {
            "adapter": "deepseek",
            "protocol": "messages",
            "route": "deepseek-official",
            "base_url_env": "DEEPSEEK_BASE_URL_ANTHROPIC",
            "api_key_env": "DEEPSEEK_API_KEY",
        },
        "models": [
            {"id": "model-a", "context_window": 8192, "max_output_tokens": 512, "reasoning": False},
            {
                "id": "model-b",
                "context_window": 16384,
                "max_output_tokens": 1024,
                "reasoning": {"0": "off", "1": "low", "2": "high"},
            },
        ],
        "selected_model": "model-a",
        "hmr": False,
    }
    (tool / "setups/default/dsh-setup.yaml").write_text(yaml.safe_dump(setup))
    auth = tool / "auth/selected/env/vars.env"
    auth.parent.mkdir(parents=True)
    auth.write_text(
        "DEEPSEEK_API_KEY=synthetic-selected-private\n"
        "DEEPSEEK_BASE_URL_ANTHROPIC=http://127.0.0.1:12345/anthropic\n"
        "OPENAI_API_KEY=synthetic-competing-private\n"
        "OPENAI_BASE_URL=http://127.0.0.1:54321/v1\n"
    )
    return BuildRequest(
        agent_def_dir=definitions,
        runtime_root=tmp_path / "runtime",
        tool="dsh",
        skills=[],
        setup="default",
        auth="selected",
        home_id="agent-a",
        role_prompt_override="Keep {{braces}} and $variables literally.\n",
    )


def test_dsh_brains_preserve_explicit_selection_and_isolate_homes(tmp_path: Path) -> None:
    """Project exact models and numbered efforts without public credential values."""

    request = _seed(tmp_path)
    first = build_brain_home(request)
    second = build_brain_home(
        replace(
            request,
            home_id="agent-b",
            direct_model_config=ModelConfig(
                name="model-b", reasoning=ModelReasoningConfig(level=99)
            ),
        )
    )
    first_projection = first.manifest["runtime"]["launch_contract"]["construction_provenance"][
        "dsh"
    ]
    second_projection = second.manifest["runtime"]["launch_contract"]["construction_provenance"][
        "dsh"
    ]
    assert first_projection["model"] == "model-a"
    assert second_projection["model"] == "model-b"
    assert second_projection["reasoning_effort"] == "high"
    assert first_projection["agents_home"] != second_projection["agents_home"]
    assert first_projection["persistence_root"] != second_projection["persistence_root"]
    assert first.home_path.stat().st_mode & 0o077 == 0
    assert (first.home_path / "houmao-role.txt").read_text() == request.role_prompt_override
    assert "synthetic-selected-private" not in json.dumps(first.manifest)
    assert "synthetic-competing-private" not in json.dumps(first.manifest)


def test_dsh_model_override_validates_without_mutating_profile(tmp_path: Path) -> None:
    """Validate request controls without rewriting the materialized native profile."""

    built = build_brain_home(_seed(tmp_path))
    patch = built.home_path / "houmao-profile.patch.json"
    before = patch.read_bytes()
    with temporary_project_model_config(
        home_path=built.home_path,
        tool="dsh",
        model_config=ModelConfig(name="model-b", reasoning=ModelReasoningConfig(level=1)),
    ) as projection:
        assert projection.args == []
        assert projection.env == {}
        assert patch.read_bytes() == before
    with pytest.raises(ValueError, match="exact catalog"):
        with temporary_project_model_config(
            home_path=built.home_path, tool="dsh", model_config=ModelConfig(name="not-configured")
        ):
            pytest.fail("Invalid selection must not reach execution")


def test_dsh_reasoning_does_not_invent_capabilities(tmp_path: Path) -> None:
    """Retain explicit off support and saturate only a declared positive ladder."""

    built = build_brain_home(_seed(tmp_path))
    off = resolve_reasoning_mapping(
        tool="dsh", requested_level=0, model_name="model-a", home_path=built.home_path
    )
    assert off["native_value"] == "off"
    with pytest.raises(ValueError, match="no positive reasoning presets"):
        resolve_reasoning_mapping(
            tool="dsh", requested_level=1, model_name="model-a", home_path=built.home_path
        )


@pytest.mark.parametrize(
    ("launch_model", "execution_model", "expected_model", "expected_key", "expected_effort"),
    [
        (
            None,
            ModelConfig(name="model-b", reasoning=ModelReasoningConfig(level=99)),
            "model-b",
            "2",
            "high",
        ),
        (
            ModelConfig(name="model-b"),
            ModelConfig(reasoning=ModelReasoningConfig(level=99)),
            "model-b",
            "2",
            "high",
        ),
        (
            None,
            ModelConfig(name="model-b", reasoning=ModelReasoningConfig(level=0)),
            "model-b",
            "0",
            "off",
        ),
        (None, ModelConfig(reasoning=ModelReasoningConfig(level=0)), "model-a", None, "off"),
    ],
    ids=["saturated-override", "selected-model-fallback", "explicit-off", "nonreasoning-off"],
)
def test_dsh_prompt_invocation_uses_the_effective_reasoning_profile_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    launch_model: ModelConfig | None,
    execution_model: ModelConfig,
    expected_model: str,
    expected_key: str | None,
    expected_effort: str | None,
) -> None:
    """Serialize canonical per-prompt selections that native preparation accepts."""

    built = build_brain_home(replace(_seed(tmp_path), direct_model_config=launch_model))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.launch_plan.detect_tool_version",
        lambda **_: ToolVersion.parse("0.2.2-rc.3"),
    )
    monkeypatch.setattr(
        "houmao.agents.launch_policy.engine.detect_tool_version",
        lambda **_: ToolVersion.parse("0.2.2-rc.3"),
    )
    plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=built.manifest,
            role_package=RolePackage("role", "Literal role", tmp_path),
            backend="dsh_acp",
            working_directory=tmp_path,
        )
    )
    manifest_path = tmp_path / "session.json"
    manifest_path.write_text(
        json.dumps({"registry_generation_id": "generation", "runtime": {"session_id": "runtime"}})
    )
    session = object.__new__(DshAcpSession)
    session._plan = plan
    session._session_manifest_path = manifest_path
    session._state = HeadlessSessionState()
    session.m_turn_dir = tmp_path / "turn-artifacts/attempt"
    session.m_execution_model = execution_model
    patch_path = Path(plan.metadata["dsh"]["patch_path"])
    original_patch = patch_path.read_bytes()

    command, prompt = session._build_command(prompt="Private prompt")

    assert prompt == "Private prompt"
    assert "Private prompt" not in command
    assert patch_path.read_bytes() == original_patch
    private = json.loads(Path(command[-1]).read_text())
    assert private["model"] == execution_model.name
    assert private["reasoning_level"] == expected_key
    prepared = load_dsh_home(
        built.home_path,
        DshSetup.from_file(Path(private["setup_path"])),
        plan.env,
        selected_model=private["model"],
        reasoning_level=private["reasoning_level"],
    )
    assert prepared.model == ("deepseek-official", expected_model)
    assert prepared.reasoning_effort == expected_effort
    assert patch_path.read_bytes() == original_patch


def test_dsh_missing_route_and_undeclared_model_fail_before_launch(tmp_path: Path) -> None:
    """Reject incomplete configuration without borrowing ambient provider state."""

    request = _seed(tmp_path)
    env = request.agent_def_dir / "tools/dsh/auth/selected/env/vars.env"
    env.write_text("DEEPSEEK_API_KEY=synthetic\n")
    with pytest.raises(BuildError, match="endpoint reference"):
        build_brain_home(request)


def test_dsh_controller_keeps_request_fields_separate_from_frozen_launch_defaults(
    tmp_path: Path,
) -> None:
    """Reasoning-only ACP requests preserve current-native model fallback downstream."""

    controller = object.__new__(RuntimeSessionController)
    controller.backend_session = object.__new__(DshAcpSession)
    controller.brain_manifest_path = tmp_path / "unread-frozen-brain.json"
    controller.brain_manifest_path.write_text("invalid saved launch projection")
    request = ModelConfig(reasoning=ModelReasoningConfig(level=1))
    assert controller._resolve_headless_execution_model(request) == request
    assert controller._resolve_headless_execution_model(None) is None


@pytest.mark.parametrize("backend,profile", [("dsh_acp", "acp"), ("dsh_web", "web")])
def test_dsh_launch_plan_is_native_and_restore_is_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    backend: str,
    profile: str,
) -> None:
    """Use the selected executable/profile while preserving a newer native projection."""

    request = _seed(tmp_path)
    built = build_brain_home(request)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.launch_plan.detect_tool_version",
        lambda **_: ToolVersion.parse("0.2.2-rc.3"),
    )
    monkeypatch.setattr(
        "houmao.agents.launch_policy.engine.detect_tool_version",
        lambda **_: ToolVersion.parse("0.2.2-rc.3"),
    )
    role = RolePackage("role", "Native {{literal}}\n", tmp_path)
    plan_request = LaunchPlanRequest(
        brain_manifest=built.manifest,
        role_package=role,
        backend=backend,
        working_directory=tmp_path,
    )
    plan = build_launch_plan(plan_request)
    assert plan.executable == "dsh"
    assert plan.args == ["--profile", profile, "--patch", plan.metadata["dsh"]["patch_path"]]
    assert plan.native_surface_kind == ("web" if backend == "dsh_web" else None)
    assert plan.role_injection.method == "native_system_prompt_section"
    assert plan.role_injection.bootstrap_message is None
    assert set(plan.env).isdisjoint({"OPENAI_API_KEY", "OPENAI_BASE_URL"})
    assert "synthetic-selected-private" not in json.dumps(plan.metadata)
    assert plan.metadata["dsh"]["setup_path"] == str(built.home_path / "dsh-setup.yaml")
    role_path = Path(plan.metadata["dsh"]["role_path"])
    patch_path = Path(plan.metadata["dsh"]["patch_path"])
    role_path.write_text("newer-role")
    patch_path.write_text("newer-profile")
    restored = build_launch_plan(replace(plan_request, intent="resume_control"))
    assert restored.metadata["dsh"]["patch_path"] == str(patch_path)
    assert patch_path.read_text() == "newer-profile"
    assert role_path.read_text() == "newer-role"


@pytest.mark.parametrize("backend", ["dsh_acp", "dsh_web"])
def test_dsh_launch_plan_preserves_as_is_native_permissions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    backend: str,
) -> None:
    """Carry explicit native permission posture through initial build and provider start."""

    request = replace(_seed(tmp_path), operator_prompt_mode="as_is")
    built = build_brain_home(request)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.launch_plan.detect_tool_version",
        lambda **_: ToolVersion.parse("0.2.2-rc.3"),
    )
    plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=built.manifest,
            role_package=RolePackage("role", "Literal role", tmp_path),
            backend=backend,
            working_directory=tmp_path,
        )
    )
    assert plan.metadata["dsh"]["operator_prompt_mode"] == "as_is"
    patch = json.loads(Path(plan.metadata["dsh"]["patch_path"]).read_text())
    assert {entry["id"] for entry in patch}.isdisjoint({"approval", "sandbox-policy"})


def test_dsh_operation_selection_and_owned_arguments_are_explicit() -> None:
    """Select native ACP or Web explicitly and reserve protocol-owned controls."""

    assert backend_for_tool("dsh") == "dsh_acp"
    assert backend_for_tool("dsh", prefer_local_interactive=True) == "dsh_web"
    with pytest.raises(LaunchPlanError, match="CAO"):
        backend_for_tool("dsh", prefer_cao=True)
    with pytest.raises(ValueError, match="reserved"):
        resolve_launch_behavior(
            tool="dsh",
            backend="dsh_acp",
            adapter_defaults=LaunchDefaults(args=("--profile", "web")),
            recipe_overrides=None,
            direct_overrides=None,
            metadata=ToolLaunchMetadata(),
        )


@pytest.mark.parametrize("backend", ["local_interactive", "codex_headless", "cao_rest"])
def test_dsh_launch_plan_rejects_an_incompatible_backend(tmp_path: Path, backend: str) -> None:
    """Refuse mismatched backends before executable probing or native startup."""

    built = build_brain_home(_seed(tmp_path))
    with pytest.raises(LaunchPlanError, match="dsh_acp.*dsh_web"):
        build_launch_plan(
            LaunchPlanRequest(
                brain_manifest=built.manifest,
                role_package=RolePackage("role", "Literal role", tmp_path),
                backend=backend,  # type: ignore[arg-type]
                working_directory=tmp_path,
            )
        )


def test_dsh_version_floor_is_lower_bounded_for_release_and_rc_only() -> None:
    """Accept lower-bounded release and rc builds without an upper cap; reject alpha/beta/dev."""

    from houmao.agents.launch_policy import DSH_SUPPORTED_VERSIONS, is_supported_dsh_version

    spec = SupportedVersionSpec.parse(DSH_SUPPORTED_VERSIONS)
    for supported in ("0.2.2-rc.1", "0.2.2-rc.3", "0.2.2", "0.2.3-rc.1", "0.2.3", "1.0.0"):
        assert spec.contains(ToolVersion.parse(supported)), supported
        assert is_supported_dsh_version(supported), supported
    for unsupported in (
        "0.2.1",
        "0.2.1-rc.5",
        "0.2.2-alpha.3",
        "0.2.2-beta.1",
        "0.2.2.dev1",
        "0.2.3-alpha.1",
    ):
        assert not spec.contains(ToolVersion.parse(unsupported)), unsupported
        assert not is_supported_dsh_version(unsupported), unsupported


@pytest.mark.parametrize(
    "adapter,key_name,endpoint_name",
    [
        ("deepseek", "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL_ANTHROPIC"),
        ("pi-ai", "OPENAI_API_KEY", "OPENAI_BASE_URL"),
    ],
)
def test_dsh_credential_commands_are_api_only(
    tmp_path: Path, adapter: str, key_name: str, endpoint_name: str
) -> None:
    """Store explicitly selected API material without printing its value or importing auth JSON."""

    definitions = _seed(tmp_path).agent_def_dir
    runner = CliRunner()
    prefix = ["internals", "native-agent", "credentials", "dsh"]
    result = runner.invoke(
        cli,
        [
            *prefix,
            "add",
            "--native-agent-root",
            str(definitions),
            "--name",
            "test-api",
            "--adapter",
            adapter,
            "--api-key",
            "synthetic-credential-private",
            "--base-url",
            "https://model.example.test",
        ],
    )
    assert result.exit_code == 0, result.output
    env = (definitions / "tools/dsh/auth/test-api/env/vars.env").read_text()
    assert f"{key_name}=synthetic-credential-private" in env
    assert f"{endpoint_name}=https://model.example.test" in env
    assert "synthetic-credential-private" not in result.output
    login = runner.invoke(cli, [*prefix, "login"])
    assert login.exit_code != 0
    assert "No such command" in login.output


def test_dsh_native_tools_and_recipe_selection_are_maintained(tmp_path: Path) -> None:
    """Prepare a DSH setup through the same maintained internals used by other tools."""

    definitions = _seed(tmp_path).agent_def_dir
    result = CliRunner().invoke(
        cli,
        [
            "internals",
            "native-agent",
            "tools",
            "dsh",
            "setups",
            "add",
            "--name",
            "controlled",
            "--native-agent-root",
            str(definitions),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (definitions / "tools/dsh/setups/controlled").is_dir()
    help_result = CliRunner().invoke(cli, ["internals", "native-agent", "recipes", "add", "--help"])
    assert "dsh" in help_result.output


def test_dsh_join_refuses_before_accessing_any_tmux_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """Require a managed launch rather than adopting an unverified native process."""

    def unexpected_tmux() -> str:
        """Fail if unsupported adoption reaches terminal inspection."""

        pytest.fail("Unsupported DSH join must not inspect tmux")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core._require_current_tmux_session_name", unexpected_tmux
    )
    result = CliRunner().invoke(
        cli,
        ["agents", "self", "join", "--agent-name", "controlled", "--provider", "dsh", "--headless"],
    )
    assert result.exit_code != 0
    assert "DSH adoption is unsupported" in result.output


@pytest.mark.parametrize("prompt_mode", ["unattended", "as_is"])
@pytest.mark.parametrize("adapter", ["deepseek", "pi-ai"])
@pytest.mark.parametrize("headless", [True, False])
def test_dsh_project_profile_prepares_the_selected_managed_native_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    prompt_mode: str,
    adapter: str,
    headless: bool,
) -> None:
    """Resolve actual project credentials/profile/model through the manager without starting a worker."""

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOUMAO_GLOBAL_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
    monkeypatch.setenv("HOUMAO_CLI_PRINT_STYLE", "json")
    runner = CliRunner()
    initialized = runner.invoke(cli, ["project", "init"])
    assert initialized.exit_code == 0, initialized.output
    overlay = require_project_overlay(project)
    tool = overlay.agents_root / "tools" / "dsh"
    setup_source = (
        _seed(tmp_path / "seed").agent_def_dir / "tools/dsh/setups/default/dsh-setup.yaml"
    )
    credential = runner.invoke(
        cli,
        [
            "project",
            "credentials",
            "dsh",
            "add",
            "--name",
            "controlled",
            "--adapter",
            adapter,
            "--api-key",
            "synthetic-project-private",
            "--base-url",
            "http://127.0.0.1:12345/anthropic",
        ],
    )
    assert credential.exit_code == 0, credential.output
    assert "synthetic-project-private" not in credential.output
    setup = yaml.safe_load(setup_source.read_text())
    if adapter == "pi-ai":
        setup["provider"].update(
            adapter="pi-ai",
            protocol="openai-completions",
            route="controlled-generic",
            base_url_env="OPENAI_BASE_URL",
            api_key_env="OPENAI_API_KEY",
        )
    (tool / "setups/default/dsh-setup.yaml").write_text(yaml.safe_dump(setup))
    specialist_args = [
        "project",
        "specialist",
        "create",
        "--name",
        "controlled",
        "--tool",
        "dsh",
        "--credential",
        "controlled",
        "--model",
        "model-b",
        "--reasoning-level",
        "2",
        "--system-prompt",
        "Keep {{literal}} and $variables.",
        "--no-system-skills",
    ]
    if prompt_mode == "as_is":
        specialist_args.append("--no-unattended")
    specialist = runner.invoke(cli, specialist_args)
    assert specialist.exit_code == 0, specialist.output
    profile = runner.invoke(
        cli,
        [
            "project",
            "profile",
            "create",
            "--name",
            "controlled",
            "--specialist",
            "controlled",
            "--agent-name",
            "controlled",
            *(["--headless"] if headless else []),
        ],
    )
    assert profile.exit_code == 0, profile.output
    captured: dict[str, Any] = {}

    def provider_boundary(**kwargs: Any) -> SimpleNamespace:
        """Record fully prepared launch inputs while preventing any subprocess or tmux access."""

        captured.update(kwargs)
        manifest = yaml.safe_load(Path(kwargs["brain_manifest_path"]).read_text())
        captured["manifest"] = manifest
        return SimpleNamespace()

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session", provider_boundary
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.emit_local_launch_completion", lambda **_: None
    )
    launched = runner.invoke(
        cli, ["project", "agents", "launch", "--profile", "controlled", "--no-gateway"]
    )
    assert launched.exit_code == 0, launched.output
    assert captured["backend"] == ("dsh_acp" if headless else "dsh_web")
    provenance = captured["manifest"]["runtime"]["launch_contract"]["construction_provenance"][
        "dsh"
    ]
    assert provenance["operator_prompt_mode"] == prompt_mode
    assert provenance["adapter"] == adapter
    assert provenance["model"] == "model-b"
    assert provenance["reasoning_effort"] == "high"
    assert "synthetic-project-private" not in json.dumps(captured["manifest"])
    home = Path(provenance["role_path"]).parent
    assert (home / "skills").is_dir()
    assert "{{literal}}" in (home / "houmao-role.txt").read_text()
    if not headless:
        captured.clear()
        rejected = runner.invoke(
            cli,
            [
                "project",
                "agents",
                "launch",
                "--profile",
                "controlled",
                "--gateway-tui-watch-poll-interval-seconds",
                "0.1",
            ],
        )
        assert rejected.exit_code != 0
        assert "unsupported" in rejected.output and "Web" in rejected.output
        assert captured == {}


def test_dsh_companion_and_setup_are_product_resources() -> None:
    """Keep native launch assets inside the installed product resource namespace."""

    companion = files("houmao.agents").joinpath("assets/dsh/managed-companion.mjs")
    setup = files("houmao.project").joinpath(
        "assets/starter_agents/tools/dsh/setups/default/dsh-setup.yaml"
    )
    assert companion.is_file()
    assert setup.is_file()


@pytest.mark.parametrize("flag", ["--claude-oauth-token", "--codex-auth-json", "--kimi-code-home"])
def test_dsh_specialist_rejects_native_login_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flag: str
) -> None:
    """Reject other providers' native authentication material instead of silently ignoring it."""

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    runner = CliRunner()
    assert runner.invoke(cli, ["project", "init"]).exit_code == 0
    if flag == "--claude-oauth-token":
        value = "synthetic-private-login-token"
    elif flag == "--codex-auth-json":
        auth_path = tmp_path / "synthetic-auth.json"
        auth_path.write_text('{"synthetic": true}')
        value = str(auth_path)
    else:
        native_home = tmp_path / "synthetic-native-home"
        native_home.mkdir()
        value = str(native_home)
    result = runner.invoke(
        cli,
        [
            "project",
            "specialist",
            "create",
            "--name",
            "rejected",
            "--tool",
            "dsh",
            "--api-key",
            "synthetic-private-key",
            flag,
            value,
        ],
    )
    assert result.exit_code != 0
    assert "native login import is unsupported" in result.output
    assert "synthetic-private" not in result.output


@pytest.mark.parametrize("identifier", ["gemini", "gemini_cli", "gemini_headless"])
def test_removed_provider_identifiers_stay_rejected_on_maintained_surfaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, identifier: str
) -> None:
    """Adding DSH does not restore removed provider, tool, or backend aliases."""

    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        cli,
        ["project", "specialist", "create", "--name", "unsupported", "--tool", identifier],
    )
    assert result.exit_code == 2
    assert "Invalid value for '--tool'" in result.output
    assert not (tmp_path / ".houmao").exists()
    with pytest.raises(LaunchPlanError, match="No default backend"):
        backend_for_tool(identifier)
    with pytest.raises(ValueError, match="is unsupported"):
        ToolLaunchMetadata.from_payload(
            {"tool_params": {"unsupported": {"type": "boolean", "backends": {identifier: {}}}}},
            source="removed-provider-regression",
        )
