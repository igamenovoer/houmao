"""Verify DSH selection, isolated brain projection, and API-only credentials."""

from __future__ import annotations

from dataclasses import replace
from importlib.resources import files
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any
from types import SimpleNamespace

from click.testing import CliRunner
import pytest
import yaml

from houmao.agents.brain_builder import (
    BuildError,
    BuildRequest,
    build_brain_home,
    validate_brain_inputs,
)
from houmao.agents.definition_parser import parse_agent_preset
from houmao.agents.dsh_configuration import (
    DSH_LOCAL_API_KEY_ENV,
    DshConfigurationError,
    DshEffectiveToolParams,
    load_dsh_home,
    read_dsh_mcp_environment,
)
from houmao.agents.dsh_credentials import (
    DSH_CREDENTIAL_ROLES_FILENAME,
    DshCredentialRoles,
    write_dsh_credential_roles,
)
from houmao.agents.launch_overrides import LaunchDefaults
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
    build_launch_plan,
    validate_dsh_launch_version,
)
from houmao.agents.realm_controller.loaders import RolePackage
from houmao.agents.realm_controller.run_modes import resolve_run_mode
from houmao.agents.realm_controller.runtime import RuntimeSessionController
from houmao.agents.tool_params import validate_tool_params
from houmao.project.catalog import ProjectCatalog
from houmao.srv_ctrl.commands.main import cli
from houmao.project.overlay import require_project_overlay
from houmao.agents.tool_params.dsh import DshMcpServer, DshToolParamsAdapter


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
        "provider": {
            "adapter": "deepseek",
            "protocol": "messages",
            "route": "deepseek-official",
            "base_url_env": "DEEPSEEK_BASE_URL_ANTHROPIC",
            "api_key_env": "DEEPSEEK_API_KEY",
        },
        "models": [
            {
                "id": "model-a",
                "context_window": 8192,
                "max_output_tokens": 512,
                "reasoning_efforts": False,
            },
            {
                "id": "model-b",
                "context_window": 16384,
                "max_output_tokens": 1024,
                "reasoning_efforts": {"off": "off", "low": "low", "high": "high"},
            },
        ],
    }
    (tool / "setups/default/tool-params.yaml").write_text(yaml.safe_dump(setup))
    auth = tool / "auth/selected/env/vars.env"
    auth.parent.mkdir(parents=True)
    auth.write_text(
        "DEEPSEEK_API_KEY=synthetic-selected-private\n"
        "DEEPSEEK_BASE_URL_ANTHROPIC=http://127.0.0.1:12345/anthropic\n"
        "OPENAI_API_KEY=synthetic-competing-private\n"
        "OPENAI_BASE_URL=http://127.0.0.1:54321/v1\n"
    )
    auth.chmod(0o600)
    write_dsh_credential_roles(
        auth, DshCredentialRoles("DEEPSEEK_BASE_URL_ANTHROPIC", "DEEPSEEK_API_KEY")
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
        preset_model_config=ModelConfig(name="model-a"),
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
            "high",
            "high",
        ),
        (
            ModelConfig(name="model-b"),
            ModelConfig(reasoning=ModelReasoningConfig(level=99)),
            "model-b",
            "high",
            "high",
        ),
        (
            None,
            ModelConfig(name="model-b", reasoning=ModelReasoningConfig(level=0)),
            "model-b",
            "off",
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
        DshEffectiveToolParams.from_file(Path(private["setup_path"])),
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


@pytest.mark.parametrize("backend", ["dsh_acp", "dsh_web"])
@pytest.mark.parametrize("authenticated", [False, True])
def test_dsh_bound_roles_project_into_native_launch_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend: str, authenticated: bool
) -> None:
    """Use custom role names or the native-only public placeholder for both surfaces."""

    request = _seed(tmp_path)
    auth = request.agent_def_dir / "tools/dsh/auth/selected/env/vars.env"
    key_name = "SGLANG_AUTH" if authenticated else None
    endpoint_name = "SGLANG_ENDPOINT"
    endpoint = "http://127.0.0.1:12345/v1"
    key = "synthetic-custom-binding"
    auth.write_text(f"{endpoint_name}={endpoint}\n" + (f"{key_name}={key}\n" if key_name else ""))
    write_dsh_credential_roles(auth, DshCredentialRoles(endpoint_name, key_name))
    request = replace(
        request,
        direct_tool_params={
            "provider": {
                "adapter": "pi-ai",
                "protocol": "openai-completions",
                "route": "local-chat",
                "base_url_env": endpoint_name,
                "api_key_env": key_name,
            },
            "models": [{"id": "model-b", "reasoning_efforts": False}],
        },
    )
    built = build_brain_home(request)
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-ambient")
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
            backend=backend,
            working_directory=tmp_path,
        )
    )
    native_key = key_name or DSH_LOCAL_API_KEY_ENV
    assert plan.env[native_key] == (key if authenticated else "houmao-local-no-auth")
    assert plan.env[endpoint_name] == endpoint
    assert "OPENAI_API_KEY" not in plan.env
    patch_path = Path(plan.metadata["dsh"]["patch_path"])
    patch = json.loads(patch_path.read_text())
    adapter = next(row for row in patch if row["id"] == "llm-pi-ai")
    assert adapter["config"]["providers"]["local-chat"]["apiKeyEnv"] == native_key
    assert (
        yaml.safe_load((built.home_path / "houmao-tool-params.yaml").read_text())["provider"][
            "api_key_env"
        ]
        == key_name
    )
    for path in (built.manifest_path, patch_path, auth, built.launch_helper_path):
        assert "houmao-local-no-auth" not in path.read_text()
    assert key not in json.dumps(plan.metadata)


def test_dsh_role_mismatch_and_environment_collisions_fail_before_allocation(
    tmp_path: Path,
) -> None:
    """Reject role mismatches and both override sources without exposing their values."""

    request = _seed(tmp_path)
    auth = request.agent_def_dir / "tools/dsh/auth/selected/env/vars.env"
    with pytest.raises(BuildError, match="provider.api_key_env.*match"):
        validate_brain_inputs(
            replace(request, direct_tool_params={"provider": {"api_key_env": "SGLANG_AUTH"}}),
            backend="dsh_acp",
        )
    with pytest.raises(BuildError, match="DEEPSEEK_BASE_URL_ANTHROPIC.*credential"):
        validate_brain_inputs(
            replace(
                request,
                persistent_env_records={"DEEPSEEK_BASE_URL_ANTHROPIC": "sensitive-override"},
            ),
            backend="dsh_web",
        )
    with pytest.raises(BuildError, match="One-shot.*DEEPSEEK_API_KEY") as captured:
        validate_brain_inputs(
            request,
            backend="dsh_acp",
            launch_env_overrides={"DEEPSEEK_API_KEY": "sensitive-override"},
        )
    assert "sensitive-override" not in str(captured.value)
    auth.with_name(DSH_CREDENTIAL_ROLES_FILENAME).unlink()
    with pytest.raises(BuildError, match="role metadata is missing"):
        build_brain_home(request)
    assert not list(request.runtime_root.glob("homes/*"))


def test_generated_dsh_helper_reads_roles_at_execution_time(tmp_path: Path) -> None:
    """Launch the helper without embedding the selected endpoint or native placeholder."""

    request = _seed(tmp_path)
    tool = request.agent_def_dir / "tools/dsh"
    fake_dsh = tmp_path / "fake-dsh"
    fake_dsh.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = --version ]; then echo "dsh 0.2.2-rc.3"; exit; fi\n'
        '[ "$1" = --profile ] && [ "$2" = acp ] || exit 2\n'
        'printf "%s %s\\n" "$HOUMAO_DSH_LOCAL_API_KEY" "$OPENAI_BASE_URL"\n'
    )
    fake_dsh.chmod(0o700)
    adapter = yaml.safe_load((tool / "adapter.yaml").read_text())
    adapter["launch"]["executable"] = str(fake_dsh)
    (tool / "adapter.yaml").write_text(yaml.safe_dump(adapter))
    auth = tool / "auth/selected/env/vars.env"
    write_dsh_credential_roles(auth, DshCredentialRoles(base_url_env="OPENAI_BASE_URL"))
    auth.write_text("OPENAI_BASE_URL=http://127.0.0.1:12345/v1\n")
    result = build_brain_home(
        replace(
            request,
            operator_prompt_mode="as_is",
            direct_tool_params={
                "provider": {
                    "adapter": "pi-ai",
                    "protocol": "openai-completions",
                    "route": "local-chat",
                    "base_url_env": "OPENAI_BASE_URL",
                    "api_key_env": None,
                },
                "models": [{"id": "model-b", "reasoning_efforts": False}],
            },
        )
    )
    launch = subprocess.run(
        [str(result.launch_helper_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    assert launch.stdout.strip() == "houmao-local-no-auth http://127.0.0.1:12345/v1"
    assert "houmao-local-no-auth" not in result.launch_helper_path.read_text()


@pytest.mark.parametrize("backend", ["dsh_acp", "dsh_headless"])
def test_dsh_controller_keeps_request_fields_separate_from_frozen_launch_defaults(
    tmp_path: Path,
    backend: str,
) -> None:
    """Reasoning-only DSH requests preserve the current native model downstream."""

    controller = object.__new__(RuntimeSessionController)
    controller.launch_plan = SimpleNamespace(backend=backend)
    controller.brain_manifest_path = tmp_path / "unread-frozen-brain.json"
    controller.brain_manifest_path.write_text("invalid saved launch projection")
    request = ModelConfig(reasoning=ModelReasoningConfig(level=1))
    assert controller._resolve_headless_execution_model(request) == request
    assert controller._resolve_headless_execution_model(None) is None


@pytest.mark.parametrize(
    "backend,profile", [("dsh_acp", "acp"), ("dsh_headless", "headless"), ("dsh_web", "web")]
)
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
    assert plan.args == [
        "--profile",
        profile,
        "--patch",
        plan.metadata["dsh"]["patch_path"],
        *(["--json"] if profile == "headless" else []),
    ]
    assert plan.native_surface_kind == ("web" if backend == "dsh_web" else None)
    assert plan.role_injection.method == "native_system_prompt_section"
    assert plan.role_injection.bootstrap_message is None
    assert set(plan.env).isdisjoint({"OPENAI_API_KEY", "OPENAI_BASE_URL"})
    assert "synthetic-selected-private" not in json.dumps(plan.metadata)
    assert plan.metadata["dsh"]["setup_path"] == str(built.home_path / "houmao-tool-params.yaml")
    role_path = Path(plan.metadata["dsh"]["role_path"])
    patch_path = Path(plan.metadata["dsh"]["patch_path"])
    role_path.write_text("newer-role")
    patch_path.write_text("newer-profile")
    restored = build_launch_plan(replace(plan_request, intent="resume_control"))
    assert restored.metadata["dsh"]["patch_path"] == str(patch_path)
    assert patch_path.read_text() == "newer-profile"
    assert role_path.read_text() == "newer-role"


@pytest.mark.parametrize("backend", ["dsh_acp", "dsh_headless", "dsh_web"])
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


@pytest.mark.parametrize("name", ["default", "openai-compatible"])
def test_starter_dsh_setups_load_without_reserved_hmr(name: str) -> None:
    """Validate both packaged setup layers independently of their model catalog."""

    path = files("houmao.project").joinpath(
        "assets", "starter_agents", "tools", "dsh", "setups", name, "tool-params.yaml"
    )
    payload = yaml.safe_load(path.read_text())
    assert "hmr" not in payload
    assert validate_tool_params("dsh", payload, source=str(path)) == payload


@pytest.mark.parametrize("backend", ["dsh_acp", "dsh_headless", "dsh_web"])
def test_dsh_provider_start_pins_resolved_permission_over_materialized_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend: str
) -> None:
    """Reconstruct the authored workspace restriction at each provider start."""

    request = replace(
        _seed(tmp_path),
        preset_tool_params={"permissions": {"sandbox": "workspace-write", "approval": "ask"}},
        direct_tool_params={"permissions": {"approval": "never"}},
    )
    built = build_brain_home(request)
    for detector in ("launch_policy.engine", "realm_controller.launch_plan"):
        monkeypatch.setattr(
            f"houmao.agents.{detector}.detect_tool_version",
            lambda **_: ToolVersion.parse("0.2.2-rc.3"),
        )
    plan_request = LaunchPlanRequest(
        brain_manifest=built.manifest,
        role_package=RolePackage("role", "Literal role", tmp_path),
        backend=backend,
        working_directory=tmp_path,
    )
    for _ in range(2):
        plan = build_launch_plan(plan_request)
        metadata = plan.metadata["dsh"]
        assert metadata["permissions"] == {"sandbox": "workspace-write", "approval": "never"}
        profile_path = Path(metadata["patch_path"])
        patch = {row["id"]: row.get("config") for row in json.loads(profile_path.read_text())}
        assert patch["approval"]["policy"] == "never"
        assert patch["sandbox-policy"]["mode"] == "workspace-write"
        assert (
            patch["permission"]["presets"][metadata["permission_preset"]] == metadata["permissions"]
        )
        assert patch["permission"]["defaultPreset"] == metadata["permission_preset"]
        profile_path.write_text("[]")


def test_dsh_headless_reads_edited_native_model_and_keeps_overrides_private(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read current CLI defaults and return a detached override without altering the home."""

    built = build_brain_home(_seed(tmp_path))
    for detector in ("launch_policy.engine", "realm_controller.launch_plan"):
        monkeypatch.setattr(
            f"houmao.agents.{detector}.detect_tool_version",
            lambda **_: ToolVersion.parse("0.2.2-rc.3"),
        )
    plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=built.manifest,
            role_package=RolePackage("role", "Literal role", tmp_path),
            backend="dsh_headless",
            working_directory=tmp_path,
        )
    )
    projection = plan.metadata["dsh"]
    profile = Path(projection["patch_path"])
    rows = json.loads(profile.read_text())
    defaults = next(row["config"] for row in rows if row["id"] == "agent-default-model")
    defaults.update(model="model-b", reasoningEffort="low")
    profile.write_text(json.dumps(rows))
    role_file = Path(projection["role_path"])
    role_file.write_text("Role edited directly")
    setup = DshEffectiveToolParams.from_file(Path(projection["setup_path"]))

    current = load_dsh_home(built.home_path, setup, plan.env, native_profile="headless")
    assert current.model == ("deepseek-official", "model-b")
    assert current.reasoning_effort == "low"
    assert current.invocation_patch == ()
    override = load_dsh_home(
        built.home_path, setup, plan.env, native_profile="headless", reasoning_level="high"
    )
    assert override.model == current.model
    assert override.reasoning_effort == "high"
    assert (
        next(
            row["config"]["reasoningEffort"]
            for row in override.invocation_patch
            if row["id"] == "agent-default-model"
        )
        == "high"
    )
    assert json.loads(profile.read_text()) == rows
    assert role_file.read_text() == "Role edited directly"


@pytest.mark.parametrize(
    ("declaration", "kind"),
    [
        ({"name": "test-server", "command": "/bin/false"}, "stdio"),
        ({"name": "test-server", "type": "http", "url": "https://example.invalid/mcp"}, "http"),
    ],
)
def test_dsh_headless_refuses_acp_mcp_before_preparing_native_work(
    tmp_path: Path, declaration: dict[str, str], kind: str
) -> None:
    """Reject both typed transport forms at birth and on a native-home read."""

    built = build_brain_home(_seed(tmp_path))
    setup = DshEffectiveToolParams.from_file(built.home_path / "houmao-tool-params.yaml")
    configured = setup.model_copy(
        update={"mcp_servers": [DshMcpServer.model_validate(declaration)]}
    )
    reason = rf"ACP MCP declarations 'test-server' \({kind}\)"
    with pytest.raises(DshConfigurationError, match=reason):
        DshToolParamsAdapter().prepare_launch(configured, backend="dsh_headless")
    with pytest.raises(DshConfigurationError, match=reason):
        load_dsh_home(built.home_path, configured, {}, native_profile="headless")


def test_dsh_headless_detects_older_build_before_starting_native_work() -> None:
    """Apply the headless floor independently of unattended launch policy."""

    assert (
        validate_dsh_launch_version(
            executable="dsh", detected_version="0.2.2-rc.2", backend="dsh_web"
        )
        == "0.2.2-rc.2"
    )
    with pytest.raises(LaunchPlanError, match=r"dsh_headless.*requires version >=0\.2\.2rc3"):
        validate_dsh_launch_version(
            executable="dsh", detected_version="0.2.2-rc.2", backend="dsh_headless"
        )


def test_dsh_operation_selection_and_owned_arguments_are_explicit() -> None:
    """Select each DSH profile while keeping its native flags owner-controlled."""

    assert resolve_run_mode("dsh").backend == "dsh_web"
    assert resolve_run_mode("dsh", mode="headless", entrypoint="project").backend == "dsh_headless"
    assert resolve_run_mode("dsh", mode="service").backend == "dsh_acp"
    with pytest.raises(LaunchPlanError, match="backend 'cao_rest' do not agree"):
        resolve_run_mode("dsh", backend="cao_rest")
    with pytest.raises(ValueError, match="reserved"):
        resolve_launch_behavior(
            tool="dsh",
            backend="dsh_acp",
            adapter_defaults=LaunchDefaults(args=("--profile", "web")),
            recipe_overrides=None,
            direct_overrides=None,
        )


@pytest.mark.parametrize("backend", ["local_interactive", "codex_headless", "cao_rest"])
def test_dsh_launch_plan_rejects_an_incompatible_backend(tmp_path: Path, backend: str) -> None:
    """Refuse mismatched backends before executable probing or native startup."""

    built = build_brain_home(_seed(tmp_path))
    with pytest.raises(LaunchPlanError, match=f"Tool 'dsh'.*backend '{backend}' do not agree"):
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


@pytest.mark.parametrize("prompt_mode", ["unattended", "as_is"])
@pytest.mark.parametrize("adapter", ["deepseek", "pi-ai"])
@pytest.mark.parametrize("selected_mode", [None, "web", "headless"])
def test_dsh_project_profile_prepares_the_selected_managed_native_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    prompt_mode: str,
    adapter: str,
    selected_mode: str | None,
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
        _seed(tmp_path / "seed").agent_def_dir / "tools/dsh/setups/default/tool-params.yaml"
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
    (tool / "setups/default/tool-params.yaml").write_text(yaml.safe_dump(setup))
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
            *(["--mode", selected_mode] if selected_mode else []),
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
        "houmao.agents.realm_controller.launch_plan.detect_tool_version",
        lambda **_: ToolVersion.parse("0.2.2-rc.3"),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.build_local_launch_completion", lambda **_: None
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.render_local_launch_completion", lambda **_: None
    )
    launched = runner.invoke(
        cli, ["project", "agents", "launch", "--profile", "controlled", "--no-gateway"]
    )
    assert launched.exit_code == 0, launched.output
    expected_mode = selected_mode or "web"
    assert captured["mode"] == expected_mode
    assert captured["backend"] == f"dsh_{expected_mode}"
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
    if selected_mode is None:
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
        assert "require a terminal native surface" in rejected.output
        assert captured == {}


def test_dsh_companion_and_setup_are_product_resources() -> None:
    """Keep native launch assets inside the installed product resource namespace."""

    companion = files("houmao.agents").joinpath("assets/dsh/managed-companion.mjs")
    setup = files("houmao.project").joinpath(
        "assets/starter_agents/tools/dsh/setups/default/tool-params.yaml"
    )
    assert companion.is_file()
    assert setup.is_file()


def test_dsh_mcp_references_survive_project_authoring_and_home_construction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preserve private values on credential update and expose only references in launch state."""

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOUMAO_GLOBAL_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
    monkeypatch.setenv("HOUMAO_CLI_PRINT_STYLE", "json")
    runner = CliRunner()

    def invoke(*args: str) -> str:
        """Return output from a successful project command."""

        result = runner.invoke(cli, ["project", *args])
        assert result.exit_code == 0, result.output
        return result.output

    invoke("init")
    invoke(
        "credentials",
        "dsh",
        "add",
        "--name",
        "bound",
        "--adapter",
        "deepseek",
        "--api-key",
        "synthetic-provider-key",
        "--base-url",
        "http://127.0.0.1:12345/v1",
    )
    overlay = require_project_overlay(project)
    catalog = ProjectCatalog.from_overlay(overlay)
    setup_source = (
        _seed(tmp_path / "seed").agent_def_dir / "tools/dsh/setups/default/tool-params.yaml"
    )
    shutil.copyfile(setup_source, overlay.agents_root / "tools/dsh/setups/default/tool-params.yaml")

    def bundle_file() -> Path:
        """Find the current authoritative private credential file after catalog mutations."""

        auth = catalog.load_auth_profile(tool="dsh", name="bound")
        return auth.content_ref.resolve(overlay) / "env/vars.env"

    private_line = "MCP_AUTH_EXAMPLE=synthetic-private-mcp-value\n"
    env_file = bundle_file()
    assert env_file.stat().st_mode & 0o777 == 0o600
    env_file.write_text(env_file.read_text() + private_line)
    invoke(
        "credentials",
        "dsh",
        "set",
        "--name",
        "bound",
        "--adapter",
        "deepseek",
        "--base-url",
        "http://127.0.0.1:12346/v1",
    )
    assert private_line in bundle_file().read_text()
    inspection = invoke("credentials", "dsh", "get", "--name", "bound")
    assert "synthetic-private-mcp-value" not in inspection

    declaration = {
        "name": "remote",
        "type": "http",
        "url": "https://mcp.example.test/rpc",
        "headers": [{"name": "Authorization", "env_ref": "MCP_AUTH_EXAMPLE"}],
    }
    tool_params = {"mcp_servers": [declaration]}
    invoke(
        "specialist",
        "create",
        "--name",
        "bound",
        "--tool",
        "dsh",
        "--credential",
        "bound",
        "--model",
        "model-a",
        "--tool-params",
        json.dumps(tool_params),
        "--no-system-skills",
        "--system-prompt",
        "Test the selected private credential reference.",
    )
    specialist = catalog.load_specialist("bound")
    assert specialist.tool_params == tool_params
    preset_path = specialist.resolved_preset_path(overlay)
    preset = parse_agent_preset(preset_path)
    assert preset.tool_params == tool_params
    invoke(
        "profile",
        "create",
        "--name",
        "bound",
        "--specialist",
        "bound",
        "--agent-name",
        "bound",
        "--mode",
        "web",
    )
    rejected = runner.invoke(cli, ["project", "agents", "launch", "--profile", "bound"])
    assert rejected.exit_code != 0
    assert "MCP declarations are unsupported by backend 'dsh_web'" in rejected.output
    assert "synthetic-private-mcp-value" not in rejected.output

    request = BuildRequest(
        agent_def_dir=overlay.agents_root,
        runtime_root=tmp_path / "runtime",
        tool=preset.tool,
        skills=preset.skills,
        setup=preset.setup,
        auth=preset.auth,
        preset_path=preset.path,
        preset_model_config=preset.launch_model_config,
    )
    prepared = validate_brain_inputs(request, backend="dsh_acp")
    manifest = build_brain_home(replace(request, validated_inputs=prepared)).manifest
    contract = manifest["runtime"]["launch_contract"]
    effective = DshEffectiveToolParams.from_mapping(contract["tool_params"]["effective"])
    assert effective.mcp_servers[0].model_dump(exclude_none=True) == declaration
    home_file = Path(contract["construction_provenance"]["dsh"]["setup_path"])
    assert yaml.safe_load(home_file.read_text())["mcp_servers"] == [declaration]
    assert all(
        "synthetic-private-mcp-value" not in value
        for value in (
            preset_path.read_text(),
            json.dumps(manifest),
            home_file.read_text(),
        )
    )
    binding = read_dsh_mcp_environment(effective, bundle_file())
    loaded = load_dsh_home(
        home_file.parent,
        effective,
        {
            "DEEPSEEK_API_KEY": "synthetic-provider-key",
            "DEEPSEEK_BASE_URL_ANTHROPIC": "http://127.0.0.1:12346/v1",
        },
        credential_environment=binding,
    )
    assert loaded.mcp_servers[0]["headers"] == [
        {"name": "Authorization", "value": "synthetic-private-mcp-value"},
    ]
    env_file = bundle_file()
    env_file.chmod(0o644)
    with pytest.raises(ValueError, match="owner-private"):
        read_dsh_mcp_environment(effective, env_file)


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
    with pytest.raises(LaunchPlanError, match="No qualified managed run modes"):
        resolve_run_mode(identifier)
