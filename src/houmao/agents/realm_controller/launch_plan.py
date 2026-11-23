"""Launch-plan composition for brain + role inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil
from typing import Any, Final, Literal, Mapping, cast

from houmao.agents.codex_cli_config import (
    CodexCliConfigOverride,
    CodexCliConfigScalar,
    codex_provider_cli_config_overrides,
)
from houmao.agents.kimi_system_prompt import (
    KimiSystemPromptError,
    ensure_kimi_system_prompt,
    force_kimi_v2_engine_env,
    validate_kimi_native_prompt_launch,
)
from houmao.agents.dsh_configuration import (
    MATERIALIZED_DSH_TOOL_PARAMS,
    DSH_LOCAL_API_KEY_ENV,
    DshConfigurationError,
    DshEffectiveToolParams,
    dsh_native_environment,
    prepare_dsh_home,
    read_dsh_mcp_environment,
)
from houmao.agents.dsh_credentials import require_dsh_credential_roles
from houmao.agents.tool_params.dsh import DshPermissionParams
from houmao.agents.launch_env import validate_persistent_env_records
from houmao.agents.model_mapping_policy import resolve_reasoning_mapping
from houmao.agents.model_selection import parse_model_config
from houmao.agents.kimi_workspace_trust import (
    KimiWorkspaceTrustError,
    ensure_kimi_workspace_trust,
)
from houmao.agents.launch_policy import (
    apply_launch_policy,
    detect_tool_version,
    packaged_tool_version_requirement,
    validate_packaged_tool_version,
)
from houmao.agents.launch_policy.models import (
    LaunchPolicyApplicationKind,
    LaunchPolicyCompatibilityError,
    LaunchPolicyError,
    LaunchPolicyRequest,
    LaunchSurface,
    OperatorPromptMode,
    LaunchPolicyStrategy,
    SupportedVersionSpec,
    ToolVersion,
)
from houmao.agents.launch_policy.provider_hooks import (
    load_toml_state,
    prepare_kimi_service_config,
    provider_state_mutation_lock,
    validate_codex_credential_readiness,
)
from houmao.agents.launch_overrides import (
    LaunchDefaults,
    LaunchOverrides,
    ResolvedLaunchBehavior,
    parse_launch_defaults,
    parse_launch_overrides,
    resolve_launch_behavior,
)
from houmao.agents.launch_overrides.models import SupportedLaunchBackend
from houmao.agents.mailbox_runtime_models import MailboxesResolvedConfig
from houmao.hook_observation.codex_hooks_generator import build_collector_emitter_command
from houmao.hook_observation.install import (
    TOKEN_ENV_VAR,
    ObserverInstallPath,
    ObserverInstallResult,
    allocate_next_generation,
    codex_hook_artifact_dir,
    hook_observation_applies,
    hook_observation_enabled,
    install_codex_observer_configuration,
    install_kimi_observer_configuration,
    install_observer_configuration,
    kimi_hook_artifact_dir,
    remove_kimi_observer_configuration,
    write_channel_install_status,
)
from houmao.hook_observation.kimi_hooks_generator import (
    build_collector_emitter_command as build_kimi_collector_emitter_command,
)
from .errors import LaunchPlanError, LaunchPolicyResolutionError
from .loaders import RolePackage, parse_allowlisted_env
from .models import BackendKind, CaoParsingMode, LaunchPlan, RoleInjectionPlan
from houmao.agents.realm_controller.run_modes import (
    human_surface_for_mode,
    mode_for_backend,
    validate_mode_binding,
)

_BRAIN_MANIFEST_SCHEMA_VERSION: Final[int] = 3
_CAO_PARSING_MODE_DEFAULT_BY_TOOL: Final[dict[str, CaoParsingMode]] = {
    "claude": "shadow_only",
    "codex": "shadow_only",
}
_CAO_SHADOW_PARSER_SUPPORTED_TOOLS: Final[frozenset[str]] = frozenset({"claude", "codex"})
_CAO_PARSING_MODE_VALUES: Final[set[str]] = {"cao_only", "shadow_only"}
_CAO_PARSING_MODE_METADATA_KEY: Final[str] = "cao_parsing_mode_config"
_CAO_SHADOW_POLICY_METADATA_KEY: Final[str] = "cao_shadow_policy_config"
_CAO_SHADOW_UNKNOWN_TIMEOUT_KEY: Final[str] = "unknown_to_stalled_timeout_seconds"
_CAO_SHADOW_COMPLETION_STABILITY_KEY: Final[str] = "completion_stability_seconds"
_CAO_SHADOW_STALLED_TERMINAL_KEY: Final[str] = "stalled_is_terminal"
_LAUNCH_POLICY_OVERRIDE_ENV_VAR: Final[str] = "HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY"
_CLAUDE_MODEL_SELECTION_FLAGS: Final[frozenset[str]] = frozenset({"--model", "--effort"})
_CLAUDE_PUBLIC_MODEL_ENV = frozenset(
    {
        "ANTHROPIC_MODEL",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        "CLAUDE_CODE_SUBAGENT_MODEL",
        "ANTHROPIC_SMALL_FAST_MODEL",
    }
)
_KIMI_MODEL_SELECTION_FLAGS: Final[frozenset[str]] = frozenset({"--model"})
_KIMI_NO_AUTO_UPDATE_ENV_VAR: Final[str] = "KIMI_CODE_NO_AUTO_UPDATE"
_CODEX_SERVICE_ALTERNATIVES: Final[str] = "Available Codex alternatives are headless and tui."


@dataclass(frozen=True)
class LaunchPlanRequest:
    """Inputs required to compose a launch plan."""

    brain_manifest: dict[str, Any]
    role_package: RolePackage
    backend: BackendKind
    working_directory: Path
    mailboxes: MailboxesResolvedConfig = field(default_factory=MailboxesResolvedConfig)
    intent: LaunchPolicyApplicationKind = "provider_start"
    session_root: Path | None = None


def build_launch_plan(request: LaunchPlanRequest) -> LaunchPlan:
    """Compose a backend-specific launch plan.

    Parameters
    ----------
    request:
        Launch-plan request that binds brain manifest, role package, and backend.

    Returns
    -------
    LaunchPlan
        Resolved launch plan.
    """

    manifest = request.brain_manifest
    _validate_manifest_schema_version(manifest)

    inputs = _require_mapping(manifest, "inputs")
    runtime = _require_mapping(manifest, "runtime")
    home_selector = _require_mapping(runtime, "launch_home_selector")
    launch_contract = _require_mapping(runtime, "launch_contract")

    tool = _require_str(inputs, "tool")
    try:
        mode = mode_for_backend(request.backend)
        validate_mode_binding(tool, mode, request.backend)
    except ValueError as exc:
        raise LaunchPlanError(str(exc)) from exc
    executable = _require_str(runtime, "launch_executable")
    home_env_var = _require_str(home_selector, "env_var")
    home_path = Path(_require_str(home_selector, "value")).resolve()

    env_values, env_var_names, env_source, selected_env_names = read_launch_environment(
        manifest, backend=request.backend
    )
    private_names = _credential_binding_names(manifest)
    if tool == "claude":
        for name in _CLAUDE_PUBLIC_MODEL_ENV:
            if name in os.environ:
                env_values.setdefault(name, os.environ[name])
        env_var_names = sorted(env_values)

    metadata: dict[str, Any] = {
        "env_source_file": str(env_source),
        "selected_env_vars": selected_env_names,
    }
    resolved_launch_behavior = _resolve_launch_behavior_from_contract(
        tool=tool,
        backend=launch_surface_for_backend(request.backend),
        launch_contract=launch_contract,
    )
    metadata["launch_overrides"] = resolved_launch_behavior.to_payload(
        adapter_defaults=_parse_adapter_defaults(launch_contract),
        recipe_overrides=_parse_requested_launch_overrides(launch_contract, layer="preset"),
        direct_overrides=_parse_requested_launch_overrides(launch_contract, layer="direct"),
        construction_provenance=_optional_mapping(
            launch_contract.get("construction_provenance"),
            key="runtime.launch_contract.construction_provenance",
        ),
        backend=launch_surface_for_backend(request.backend),
    )
    args = list(resolved_launch_behavior.args_before_policy)
    owned_kimi_session = request.backend in {"kimi_acp", "kimi_web"}
    kimi_entrypoint = "Kimi Web" if request.backend == "kimi_web" else "Kimi ACP"
    if owned_kimi_session and home_env_var != "KIMI_CODE_HOME":
        raise LaunchPlanError(f"{kimi_entrypoint} requires the KIMI_CODE_HOME home selector")
    if request.backend == "codex_app_server":
        if home_env_var != "CODEX_HOME":
            raise LaunchPlanError("Codex app-server requires the CODEX_HOME home selector")
    codex_service_version = None
    if request.backend == "codex_app_server" and request.intent == "provider_start":
        executable, codex_service_version = resolve_codex_service_executable(executable)
        try:
            validate_codex_credential_readiness(home_path=home_path, env=env_values)
        except (LaunchPolicyError, OSError) as exc:
            raise LaunchPlanError(str(exc)) from exc
    kimi_native_version = None
    if owned_kimi_session and request.intent == "provider_start":
        resolved_executable = shutil.which(executable)
        if resolved_executable is None:
            raise LaunchPlanError(f"The selected {kimi_entrypoint} executable is unavailable")
        executable = str(Path(resolved_executable).resolve(strict=True))
        validate_kimi_version = (
            validate_kimi_web_launch_version
            if request.backend == "kimi_web"
            else validate_kimi_service_launch_version
        )
        kimi_native_version = validate_kimi_version(executable=executable)
    configured_cao_parsing_mode = _extract_configured_cao_parsing_mode(runtime=runtime)
    if configured_cao_parsing_mode is not None:
        metadata[_CAO_PARSING_MODE_METADATA_KEY] = configured_cao_parsing_mode
    configured_cao_shadow_policy = _extract_configured_cao_shadow_policy(runtime=runtime)
    if configured_cao_shadow_policy is not None:
        metadata[_CAO_SHADOW_POLICY_METADATA_KEY] = configured_cao_shadow_policy

    if request.backend == "codex_headless":
        metadata["codex_headless_cli_mode"] = "exec_json_resume"
    if request.backend in {
        "claude_headless",
        "codex_headless",
        "kimi_headless",
        "dsh_headless",
    }:
        metadata["headless_output_format"] = "stream-json"
        metadata["headless_display_style"] = "plain"
        metadata["headless_display_detail"] = "concise"

    requested_operator_prompt_mode = _requested_operator_prompt_mode(manifest)
    policy_backend = launch_surface_for_backend(request.backend)
    policy_env = dict(env_values)
    override_strategy = os.environ.get(_LAUNCH_POLICY_OVERRIDE_ENV_VAR, "").strip()
    if override_strategy:
        policy_env[_LAUNCH_POLICY_OVERRIDE_ENV_VAR] = override_strategy

    if request.intent == "provider_start":
        _strip_kimi_observer_block_before_policy_synthesis(
            tool=tool,
            backend=request.backend,
            home_path=home_path,
        )

    try:
        launch_policy_result = apply_launch_policy(
            LaunchPolicyRequest(
                tool=tool,
                backend=policy_backend,
                executable=executable,
                base_args=tuple(args),
                requested_operator_prompt_mode=requested_operator_prompt_mode,
                working_directory=request.working_directory.resolve(),
                home_path=home_path,
                env=policy_env,
                application_kind=request.intent,
                tool_params=resolved_launch_behavior.tool_params,
                tool_param_sources=resolved_launch_behavior.tool_param_sources,
            )
        )
    except LaunchPolicyCompatibilityError as exc:
        raise LaunchPolicyResolutionError(
            requested_operator_prompt_mode=exc.requested_operator_prompt_mode,
            tool=exc.tool,
            policy_backend=exc.backend,
            detected_version=exc.detected_version,
            detail=str(exc),
        ) from exc
    except LaunchPolicyError as exc:
        raise LaunchPlanError(str(exc)) from exc

    args = list(launch_policy_result.args)
    permissions = launch_policy_result.permissions
    metadata["launch_permissions"] = {
        "effective": permissions,
        "sources": launch_policy_result.permission_sources,
    }
    role_injection = plan_role_injection(
        backend=request.backend,
        tool=tool,
        role_name=request.role_package.role_name,
        role_prompt=request.role_package.system_prompt,
        strategy=launch_policy_result.strategy,
    )
    codex_cli_config_args = _codex_cli_config_args_from_contract(
        tool=tool,
        backend=request.backend,
        launch_contract=launch_contract,
    )
    provider_model_selection_cli_args = _provider_model_selection_cli_args_from_contract(
        tool=tool,
        backend=request.backend,
        launch_contract=launch_contract,
    )
    if tool == "claude" and provider_model_selection_cli_args:
        args, provider_model_selection_cli_args = _merge_claude_model_selection_cli_args(
            args=args,
            generated_args=provider_model_selection_cli_args,
            launch_contract=launch_contract,
        )
    if tool == "kimi" and provider_model_selection_cli_args and not owned_kimi_session:
        args, provider_model_selection_cli_args = _merge_kimi_model_selection_cli_args(
            args=args,
            generated_args=provider_model_selection_cli_args,
        )
    args.extend(codex_cli_config_args)
    if request.backend == "kimi_web":
        args.extend(("web", "--no-open", "--host", "127.0.0.1", "--port", "0"))
    elif request.backend == "kimi_acp":
        args.append("acp")
    else:
        args.extend(provider_model_selection_cli_args)
    if request.backend == "codex_app_server":
        args.extend(["app-server", "--listen", "stdio://"])
        env_values[home_env_var] = str(home_path)
        env_var_names = sorted({*env_var_names, home_env_var})
        metadata["codex_app_server"] = {
            "detected_version": codex_service_version,
            "operator_prompt_mode": requested_operator_prompt_mode,
            "thread_config": _codex_service_thread_config(home_path),
            "permissions": permissions,
        }
    if tool == "dsh":
        assert request.backend in {"dsh_headless", "dsh_acp", "dsh_web"}
        dsh_metadata, native_env, dsh_private_names = _prepare_dsh_launch(
            request=request,
            home_path=home_path,
            environment=env_values,
            credential_source=env_source,
            launch_contract=launch_contract,
            permissions=permissions.get("permissions", {}),
            executable=executable,
            detected_version=(
                launch_policy_result.provenance.detected_tool_version
                if launch_policy_result.provenance
                else None
            ),
        )
        private_names.update(dsh_private_names)
        env_values = {
            **{name: value for name, value in env_values.items() if name not in private_names},
            **native_env,
        }
        metadata["dsh"] = dsh_metadata
        metadata["native_system_prompt"] = {
            "method": "native_system_prompt_section",
            "path": dsh_metadata["role_path"],
            "effective_prompt_sha256": dsh_metadata["role_sha256"],
            "validation": "passed",
        }
        profile = {"dsh_headless": "headless", "dsh_web": "web", "dsh_acp": "acp"}[request.backend]
        args.extend(["--profile", profile, "--patch", str(dsh_metadata["patch_path"])])
        if request.backend == "dsh_headless":
            args.append("--json")
            metadata["headless_output_format"] = "dsh-cli"
        env_var_names = sorted(env_values)
    if tool == "kimi" and (
        owned_kimi_session or request.backend in {"local_interactive", "kimi_headless"}
    ):
        metadata["native_system_prompt"] = _ensure_kimi_native_system_prompt_for_start(
            executable=executable,
            args=args,
            working_directory=request.working_directory,
            home_path=home_path,
            role_injection=role_injection,
            detected_version=kimi_native_version
            or (
                launch_policy_result.provenance.detected_tool_version
                if launch_policy_result.provenance is not None
                else None
            ),
        )
        if requested_operator_prompt_mode == "unattended":
            metadata["workspace_trust"] = _ensure_kimi_workspace_trust_for_start(
                working_directory=request.working_directory,
                home_path=home_path,
            )
    if tool == "kimi" and request.backend == "local_interactive":
        metadata["kimi_tui"] = {"permission_mode": permissions.get("permission_mode")}
    if owned_kimi_session:
        env_values[home_env_var] = str(home_path)
        env_var_names = sorted({*env_var_names, home_env_var})
        model_alias = None
        if provider_model_selection_cli_args:
            _, option = _parse_kimi_model_selection_arg_groups(provider_model_selection_cli_args)[
                -1
            ]
            model_alias = option[-1] if len(option) == 2 else option[0].partition("=")[2]
            if not model_alias.strip():
                raise LaunchPlanError(
                    f"{kimi_entrypoint} requires a non-empty configured model alias"
                )
        if request.intent == "provider_start":
            try:
                prepare_kimi_service_config(home_path, model_alias=model_alias)
            except (LaunchPolicyError, OSError, ValueError) as exc:
                raise LaunchPlanError(
                    f"Could not project the private {kimi_entrypoint} configuration"
                ) from exc
        metadata[request.backend] = {
            "detected_version": kimi_native_version,
            "operator_prompt_mode": requested_operator_prompt_mode,
            "permission_mode": permissions.get("permission_mode"),
            "configured_model": model_alias or env_values.get("KIMI_MODEL_NAME"),
        }
    if launch_policy_result.strategy is not None:
        metadata["launch_policy"] = launch_policy_result.strategy.to_metadata_payload()
    metadata["launch_policy_request"] = {
        "operator_prompt_mode": requested_operator_prompt_mode,
    }
    launch_overrides_metadata = metadata.get("launch_overrides")
    if isinstance(launch_overrides_metadata, dict):
        backend_resolution = launch_overrides_metadata.get("backend_resolution")
        if isinstance(backend_resolution, dict):
            backend_resolution["args_after_launch_policy"] = list(args)
            if codex_cli_config_args:
                backend_resolution["codex_cli_config_args"] = list(codex_cli_config_args)
            if provider_model_selection_cli_args and not owned_kimi_session:
                backend_resolution["provider_model_selection_cli_args"] = list(
                    provider_model_selection_cli_args
                )

    args, hook_observation_metadata = _install_hook_observation_for_launch(
        request=request,
        tool=tool,
        home_path=home_path,
        args=args,
    )
    if hook_observation_metadata is not None:
        metadata["hook_observation"] = hook_observation_metadata

    return LaunchPlan(
        backend=request.backend,
        tool=tool,
        executable=executable,
        args=args,
        working_directory=request.working_directory.resolve(),
        home_env_var=home_env_var,
        home_path=home_path,
        env=env_values,
        env_var_names=env_var_names,
        role_injection=role_injection,
        metadata=metadata,
        mailboxes=request.mailboxes,
        launch_policy_provenance=launch_policy_result.provenance,
        native_surface_kind=human_surface_for_mode(mode),
        private_env_var_names=frozenset(private_names),
    )


def read_launch_environment(
    manifest: dict[str, Any], *, backend: BackendKind
) -> tuple[dict[str, str], list[str], Path, list[str]]:
    """Read selected launch credentials and env records without preparing a native home."""

    inputs = _require_mapping(manifest, "inputs")
    runtime = _require_mapping(manifest, "runtime")
    credentials = _require_mapping(manifest, "credentials")
    env_contract = _require_mapping(credentials, "env_contract")
    launch_contract = _require_mapping(runtime, "launch_contract")
    tool = _require_str(inputs, "tool")
    source = Path(_require_str(env_contract, "source_file"))
    if tool != "dsh":
        source = source.resolve()
    selected, selected_names = parse_allowlisted_env(
        source, _require_str_list(env_contract, "allowlisted_env_vars")
    )
    records = _persistent_launch_env_records(launch_contract)
    home_selector = _require_mapping(runtime, "launch_home_selector")
    protected = {*_credential_binding_names(manifest), _require_str(home_selector, "env_var")}
    if tool == "dsh":
        setup_path = Path(_require_str(home_selector, "value")) / MATERIALIZED_DSH_TOOL_PARAMS
        try:
            setup = DshEffectiveToolParams.from_file(setup_path)
        except (DshConfigurationError, OSError, ValueError) as exc:
            raise LaunchPlanError("Could not read the managed DSH environment bindings") from exc
        protected.update(setup.mcp_env_refs)
        protected.update(
            {
                setup.base_url_env,
                setup.api_key_env or DSH_LOCAL_API_KEY_ENV,
                "DSH_AGENTS_HOME",
                "DSH_PERMISSION_MODE",
                "DSH_BUNDLED_SKILL_DIR",
            }
        )
    try:
        records = validate_persistent_env_records(
            records,
            auth_env_allowlist=sorted(protected),
            source="Persistent launch environment",
        )
    except ValueError as exc:
        raise LaunchPlanError(str(exc)) from exc
    selected.update(records)
    names = sorted({*selected_names, *records})
    if tool == "kimi":
        try:
            selected = force_kimi_v2_engine_env(selected)
        except KimiSystemPromptError as exc:
            raise LaunchPlanError(str(exc)) from exc
        names = sorted({*names, "KIMI_CODE_LEGACY_FLAG"})
        if backend in {"local_interactive", "kimi_acp", "kimi_web"}:
            selected[_KIMI_NO_AUTO_UPDATE_ENV_VAR] = "1"
            names = sorted({*names, _KIMI_NO_AUTO_UPDATE_ENV_VAR})
    return selected, names, source, selected_names


def _credential_binding_names(manifest: dict[str, Any]) -> set[str]:
    """Classify credential input names before merging them with declared settings."""

    tool = _require_str(_require_mapping(manifest, "inputs"), "tool")
    credentials = _require_mapping(manifest, "credentials")
    contract = _require_mapping(credentials, "env_contract")
    names = set(_require_str_list(contract, "allowlisted_env_vars"))
    if tool == "claude":
        names.difference_update(_CLAUDE_PUBLIC_MODEL_ENV)
    names.add(TOKEN_ENV_VAR)
    return names


def validate_dsh_launch_version(
    *, executable: str, detected_version: str | None = None, backend: BackendKind | None = None
) -> str:
    """Check the installed DSH version without touching the selected home."""

    return _validate_native_tool_version(
        executable=executable,
        tool="dsh",
        backend=launch_surface_for_backend(backend) if backend is not None else "raw_launch",
        detected_version=detected_version,
    )


def validate_kimi_service_launch_version(*, executable: str) -> str:
    """Check the executable minimum for Kimi ACP."""

    return _validate_native_tool_version(executable=executable, tool="kimi", backend="kimi_acp")


def validate_kimi_web_launch_version(*, executable: str) -> str:
    """Check the executable minimum for Kimi Web."""

    return _validate_native_tool_version(executable=executable, tool="kimi", backend="kimi_web")


def _validate_native_tool_version(
    *,
    executable: str,
    tool: str,
    backend: LaunchSurface,
    detected_version: str | None = None,
) -> str:
    """Probe and validate a native mode's selected executable."""

    try:
        version = (
            detected_version
            if detected_version is not None
            else detect_tool_version(executable=executable).raw
        )
    except (LaunchPolicyError, OSError) as exc:
        requirement = packaged_tool_version_requirement(tool=tool, backend=backend).to_payload()
        raise LaunchPlanError(
            f"Could not verify {tool} backend {backend!r}, which requires {requirement}: {exc}"
        ) from exc
    try:
        return validate_packaged_tool_version(tool=tool, backend=backend, version=version).raw
    except LaunchPolicyError as exc:
        raise LaunchPlanError(str(exc)) from exc


def resolve_codex_service_executable(executable: str) -> tuple[str, str]:
    """Resolve the executable path and check the Codex app-server minimum."""

    resolved = shutil.which(executable)
    if resolved is None:
        raise LaunchPlanError(
            f"The selected Codex app-server executable is unavailable. {_CODEX_SERVICE_ALTERNATIVES}"
        )
    try:
        path = str(Path(resolved).resolve(strict=True))
    except OSError as exc:
        raise LaunchPlanError(
            f"Could not verify the selected Codex app-server executable. {_CODEX_SERVICE_ALTERNATIVES}"
        ) from exc
    try:
        version = _validate_native_tool_version(
            executable=path, tool="codex", backend="codex_app_server"
        )
    except LaunchPlanError as exc:
        raise LaunchPlanError(f"{exc} {_CODEX_SERVICE_ALTERNATIVES}") from exc
    return path, version


def _codex_service_thread_config(home_path: Path) -> dict[str, CodexCliConfigScalar]:
    """Keep the selected private-home model and provider above workspace defaults."""

    try:
        private_config = load_toml_state(home_path / "config.toml")
        overrides = list(codex_provider_cli_config_overrides(private_config))
        for key in ("model", "model_reasoning_effort"):
            value = private_config.get(key)
            if isinstance(value, str) and value.strip():
                overrides.append(CodexCliConfigOverride((key,), value))
    except (LaunchPolicyError, OSError, ValueError) as exc:
        raise LaunchPlanError(
            "Could not project the private Codex app-server configuration"
        ) from exc
    return {override.rendered_key_path: override.value for override in overrides}


def _prepare_dsh_launch(
    *,
    request: LaunchPlanRequest,
    home_path: Path,
    environment: dict[str, str],
    credential_source: Path,
    launch_contract: dict[str, Any],
    permissions: Mapping[str, Any],
    executable: str,
    detected_version: str | None,
) -> tuple[dict[str, Any], dict[str, str], set[str]]:
    """Project DSH at explicit provider start and keep control restoration read-only."""

    version = validate_dsh_launch_version(
        executable=executable, detected_version=detected_version, backend=request.backend
    )
    setup_path = home_path / MATERIALIZED_DSH_TOOL_PARAMS
    try:
        setup = DshEffectiveToolParams.from_file(setup_path)
        require_dsh_credential_roles(
            credential_source, base_url_env=setup.base_url_env, api_key_env=setup.api_key_env
        )
        selection = _optional_model_selection_contract(launch_contract) or {}
        resolved = selection.get("resolved")
        effective = resolved.get("effective") if isinstance(resolved, dict) else None
        model_config = parse_model_config(effective, source="DSH resolved launch model")
        model_name = model_config.name if model_config else None
        reasoning_key: str | None = None
        if model_config is not None and model_config.reasoning is not None:
            mapping = resolve_reasoning_mapping(
                tool="dsh",
                requested_level=model_config.reasoning.level,
                model_name=model_name,
                home_path=home_path,
                dsh_tool_params=setup,
            )
            reasoning_key = mapping.get("profile_key")
        if request.intent == "provider_start":
            prepared = prepare_dsh_home(
                home_path,
                setup,
                environment,
                request.role_package.system_prompt,
                credential_environment=read_dsh_mcp_environment(setup, credential_source),
                selected_model=model_name,
                reasoning_level=reasoning_key,
                skill_roots=(home_path / "skills",),
                operator_prompt_mode=_requested_operator_prompt_mode(request.brain_manifest)
                or "unattended",
                native_profile="headless" if request.backend == "dsh_headless" else "acp",
                permissions=DshPermissionParams.model_validate(dict(permissions)),
            )
            metadata = {
                **prepared.metadata,
                "setup_path": str(setup_path),
                "patch_path": str(prepared.patch_path),
                "role_path": str(prepared.role_path),
                "persistence_root": str(prepared.persistence_root),
                "agents_home": str(prepared.agents_home),
                "reasoning_level": reasoning_key,
            }
            private_environment = prepared.environment
        else:
            provenance = launch_contract.get("construction_provenance")
            projected = provenance.get("dsh") if isinstance(provenance, dict) else None
            if not isinstance(projected, dict):
                raise DshConfigurationError(
                    "DSH control restoration requires a prepared managed home"
                )
            metadata = dict(projected)
            metadata["reasoning_level"] = reasoning_key
            private_environment = dsh_native_environment(home_path, setup, environment)
        metadata["detected_tool_version"] = version
        metadata["mcp_server_names"] = [server.name for server in setup.mcp_servers]
        return (
            metadata,
            private_environment,
            {
                setup.base_url_env,
                setup.api_key_env or DSH_LOCAL_API_KEY_ENV,
                *setup.mcp_env_refs,
            },
        )
    except (DshConfigurationError, ValueError) as exc:
        raise LaunchPlanError(str(exc)) from exc


def _strip_kimi_observer_block_before_policy_synthesis(
    *,
    tool: str,
    backend: BackendKind,
    home_path: Path,
) -> None:
    """Remove the prior Kimi observer block before rewriting startup settings."""

    if tool != "kimi" or backend != "local_interactive":
        return
    remove_kimi_observer_configuration(home_path=home_path)


def _install_hook_observation_for_launch(
    *,
    request: LaunchPlanRequest,
    tool: str,
    home_path: Path,
    args: list[str],
) -> tuple[list[str], dict[str, Any] | None]:
    """Install the observer configuration for one provider-start plan.

    The launch planner installs a provisional configuration with collector port
    ``0`` for the selected adapter. Runtime activation rewrites it with the real
    collector port before the provider starts. Flag-off,
    non-``local_interactive``, and missing-session-root requests are exact
    no-ops. The launch policy's ``config.toml`` synthesis already ran before
    this call, so the Kimi ``[[hooks]]`` merge never races a TOML re-render.

    Returns
    -------
    tuple[list[str], dict | None]
        Effective arguments (the Claude fallback pair appended when needed) and
        the hook observation metadata, or the original arguments and ``None``.
    """

    if request.intent != "provider_start":
        return args, None
    if request.session_root is None:
        return args, None
    if not hook_observation_applies(tool=tool, backend=request.backend):
        return args, None
    if not hook_observation_enabled(tool=tool):
        return args, None

    session_root = request.session_root
    try:
        generation = allocate_next_generation(session_root, tool=tool)
    except Exception:
        return args, None

    install_path: ObserverInstallPath
    settings_path: Path | None
    appended_args: list[str]
    detail: str | None
    if tool == "codex":
        try:
            codex_result = install_codex_observer_configuration(
                home_path=home_path,
                generation=generation,
                emitter_command=build_collector_emitter_command(
                    port=0,
                    store=codex_hook_artifact_dir(session_root),
                    generation=generation,
                ),
            )
        except Exception as exc:
            install_path = "unavailable"
            settings_path = None
            appended_args = []
            detail = f"codex observer install failed: {exc}"
        else:
            install_path = codex_result.install_path
            settings_path = codex_result.config_path
            appended_args = []
            detail = codex_result.detail
    elif tool == "kimi":
        try:
            kimi_result = install_kimi_observer_configuration(
                home_path=home_path,
                generation=generation,
                emitter_command=build_kimi_collector_emitter_command(
                    port=0,
                    store=kimi_hook_artifact_dir(session_root),
                    generation=generation,
                ),
            )
        except Exception as exc:
            install_path = "unavailable"
            settings_path = None
            appended_args = []
            detail = f"kimi observer install failed: {exc}"
        else:
            install_path = kimi_result.install_path
            settings_path = kimi_result.config_path
            appended_args = []
            detail = kimi_result.detail
    else:
        try:
            result = install_observer_configuration(
                home_path=home_path,
                session_root=session_root,
                generation=generation,
                port=0,
                resolved_args=args,
            )
        except Exception as exc:
            result = ObserverInstallResult(
                install_path="unavailable",
                generation=generation,
                detail=f"observer install failed: {exc}",
            )
        install_path = result.install_path
        settings_path = result.settings_path
        appended_args = list(result.appended_args)
        detail = result.detail

    metadata: dict[str, Any] = {
        "enabled": True,
        "install_path": install_path,
        "generation": generation,
        "port": None,
        "settings_path": (str(settings_path) if settings_path is not None else None),
        "settings_args": appended_args,
        "detail": detail,
        "session_root": str(session_root.resolve()),
        "token_env": TOKEN_ENV_VAR,
    }
    write_channel_install_status(
        session_root=session_root,
        generation=generation,
        install_path=install_path,
        channel_state=("unavailable" if install_path == "unavailable" else "installing"),
        detail=detail,
        settings_path=settings_path,
        tool=tool,
    )
    return [*args, *appended_args], metadata


def _ensure_kimi_native_system_prompt_for_start(
    *,
    executable: str,
    args: list[str],
    working_directory: Path,
    home_path: Path,
    role_injection: RoleInjectionPlan,
    detected_version: str | None,
) -> dict[str, Any]:
    """Validate and repair Kimi's native prompt immediately before start."""

    if role_injection.method != "native_home_system_prompt":
        raise LaunchPlanError(
            "Maintained Kimi provider starts require role injection method "
            f"`native_home_system_prompt`, got `{role_injection.method}`."
        )
    try:
        version = detect_tool_version(executable=executable) if detected_version is None else None
        version_text = detected_version or (version.raw if version is not None else "")
        if not SupportedVersionSpec.parse(">=2.1.1").contains(
            version if version is not None else ToolVersion.parse(version_text)
        ):
            raise LaunchPlanError(
                "Maintained Kimi native prompt support requires Kimi Code >=2.1.1 with no "
                f"upper version limit; detected {version_text!r}."
            )
        with provider_state_mutation_lock(home_path):
            validate_kimi_native_prompt_launch(
                launch_args=args,
                working_directory=working_directory,
                home_path=home_path,
            )
            projection = ensure_kimi_system_prompt(
                home_path=home_path,
                effective_prompt=role_injection.prompt,
            )
    except KimiSystemPromptError as exc:
        raise LaunchPlanError(str(exc)) from exc
    return {
        **projection.to_payload(),
        "method": role_injection.method,
        "relative_path": "SYSTEM.md",
        "validation": "passed",
        "supported_versions": ">=2.1.1",
        "detected_version": version_text,
    }


def _ensure_kimi_workspace_trust_for_start(
    *,
    working_directory: Path,
    home_path: Path,
) -> dict[str, Any]:
    """Pre-seed Kimi's workspace trust for the launch workdir before start.

    Unattended launches must not surface Kimi's "Trust this folder?" modal;
    the provider's trust check is presence-only, so the managed home receives
    the deterministic record for the actual launch working directory here.
    """

    try:
        with provider_state_mutation_lock(home_path):
            projection = ensure_kimi_workspace_trust(
                home_path=home_path,
                working_directory=working_directory,
            )
    except KimiWorkspaceTrustError as exc:
        raise LaunchPlanError(str(exc)) from exc
    return projection.to_payload()


def plan_role_injection(
    *,
    backend: BackendKind,
    tool: str | None = None,
    role_name: str,
    role_prompt: str,
    strategy: LaunchPolicyStrategy | None = None,
) -> RoleInjectionPlan:
    """Create role-injection strategy for a backend.

    Parameters
    ----------
    backend:
        Selected backend kind.
    role_name:
        Role package name.
    role_prompt:
        Raw system prompt text.

    Returns
    -------
    RoleInjectionPlan
        Backend-specific role plan.
    """

    if strategy is not None:
        return _plan_role_injection_from_strategy(
            backend=backend,
            tool=tool,
            role_name=role_name,
            role_prompt=role_prompt,
            strategy=strategy,
        )

    return _plan_legacy_role_injection(
        backend=backend,
        tool=tool,
        role_name=role_name,
        role_prompt=role_prompt,
    )


def _plan_role_injection_from_strategy(
    *,
    backend: BackendKind,
    tool: str | None,
    role_name: str,
    role_prompt: str,
    strategy: LaunchPolicyStrategy,
) -> RoleInjectionPlan:
    """Create a role-injection plan from launch-policy capability metadata."""

    if backend in {"cao_rest", "houmao_server_rest"}:
        return RoleInjectionPlan(
            method="cao_profile",
            role_name=role_name,
            prompt=role_prompt,
        )

    method = _native_role_injection_method(backend=backend, tool=tool)
    if method is None or strategy.system_prompt.method != method:
        raise LaunchPlanError(
            "Launch policy has no applicable native system-prompt method for "
            f"backend={backend!r}, tool={tool!r}, strategy={strategy.strategy_id!r}; "
            f"declared={strategy.system_prompt.method!r}, expected={method!r}."
        )
    return RoleInjectionPlan(
        method=method,
        role_name=role_name,
        prompt=role_prompt,
        bootstrap_message=(
            _bootstrap_message(role_name, role_prompt)
            if method == "native_append_system_prompt"
            else None
        ),
    )


def _native_role_injection_method(
    *,
    backend: BackendKind,
    tool: str | None,
) -> (
    Literal[
        "native_developer_instructions",
        "native_append_system_prompt",
        "native_home_system_prompt",
        "native_system_prompt_section",
    ]
    | None
):
    """Return the maintained native role-injection method for one backend/tool pair."""

    if backend in {"codex_app_server", "codex_headless"}:
        return "native_developer_instructions"
    if backend == "local_interactive" and tool == "codex":
        return "native_developer_instructions"
    if backend == "claude_headless":
        return "native_append_system_prompt"
    if backend == "local_interactive" and tool == "claude":
        return "native_append_system_prompt"
    if backend in {"kimi_headless", "kimi_acp", "kimi_web"}:
        return "native_home_system_prompt"
    if backend in {"dsh_headless", "dsh_acp", "dsh_web"}:
        return "native_system_prompt_section"
    if backend == "local_interactive" and tool == "kimi":
        return "native_home_system_prompt"
    return None


def _plan_legacy_role_injection(
    *,
    backend: BackendKind,
    tool: str | None,
    role_name: str,
    role_prompt: str,
) -> RoleInjectionPlan:
    """Create the pre-policy role-injection plan for direct helper callers."""

    if backend in {"dsh_headless", "dsh_acp", "dsh_web"}:
        return RoleInjectionPlan(
            method="native_system_prompt_section", role_name=role_name, prompt=role_prompt
        )
    if backend in {"codex_app_server", "codex_headless"}:
        return RoleInjectionPlan(
            method="native_developer_instructions",
            role_name=role_name,
            prompt=role_prompt,
        )

    if backend == "local_interactive":
        if tool == "codex":
            return RoleInjectionPlan(
                method="native_developer_instructions",
                role_name=role_name,
                prompt=role_prompt,
            )
        if tool == "claude":
            return RoleInjectionPlan(
                method="native_append_system_prompt",
                role_name=role_name,
                prompt=role_prompt,
                bootstrap_message=_bootstrap_message(role_name, role_prompt),
            )
        if tool == "kimi":
            return RoleInjectionPlan(
                method="native_home_system_prompt",
                role_name=role_name,
                prompt=role_prompt,
            )
        raise LaunchPlanError(
            "backend=local_interactive requires a supported tool-specific role injection plan."
        )

    if backend == "claude_headless":
        return RoleInjectionPlan(
            method="native_append_system_prompt",
            role_name=role_name,
            prompt=role_prompt,
            bootstrap_message=_bootstrap_message(role_name, role_prompt),
        )

    if backend in {"kimi_headless", "kimi_acp", "kimi_web"}:
        return RoleInjectionPlan(
            method="native_home_system_prompt",
            role_name=role_name,
            prompt=role_prompt,
        )

    if backend in {"cao_rest", "houmao_server_rest"}:
        return RoleInjectionPlan(
            method="cao_profile",
            role_name=role_name,
            prompt=role_prompt,
        )

    raise LaunchPlanError(f"Unsupported backend: {backend}")


def _requested_operator_prompt_mode(manifest: dict[str, Any]) -> OperatorPromptMode | None:
    """Return the requested operator prompt mode from one brain manifest."""

    launch_policy = manifest.get("launch_policy")
    if launch_policy is None:
        return "unattended"
    if not isinstance(launch_policy, dict):
        raise LaunchPlanError("Manifest `launch_policy` must be a mapping when set.")
    value = launch_policy.get("operator_prompt_mode")
    if value is None:
        return "unattended"
    if not isinstance(value, str) or value not in {"as_is", "unattended"}:
        raise LaunchPlanError(
            "Manifest `launch_policy.operator_prompt_mode` must be `as_is` or `unattended`."
        )
    return cast(OperatorPromptMode, value)


def _persistent_launch_env_records(launch_contract: dict[str, Any]) -> dict[str, str]:
    """Return persistent launch-owned env records from one manifest contract."""

    raw_value = launch_contract.get("env_records")
    if raw_value is None:
        return {}
    if not isinstance(raw_value, dict):
        raise LaunchPlanError("Manifest `runtime.launch_contract.env_records` must be a mapping.")

    env_records: dict[str, str] = {}
    for raw_name, raw_item in raw_value.items():
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise LaunchPlanError(
                "Manifest `runtime.launch_contract.env_records` requires non-empty string names."
            )
        if not isinstance(raw_item, str):
            raise LaunchPlanError(
                "Manifest `runtime.launch_contract.env_records` requires string values."
            )
        env_records[raw_name.strip()] = raw_item
    return env_records


def _codex_cli_config_args_from_contract(
    *,
    tool: str,
    backend: BackendKind,
    launch_contract: dict[str, Any],
) -> list[str]:
    """Return generated Codex CLI config overrides from one launch contract."""

    if tool != "codex" or backend not in {"local_interactive", "codex_headless"}:
        return []

    model_selection = launch_contract.get("model_selection")
    if model_selection is None:
        return []
    if not isinstance(model_selection, dict):
        raise LaunchPlanError(
            "Manifest `runtime.launch_contract.model_selection` must be a mapping."
        )
    overrides = model_selection.get("codex_cli_config_overrides")
    if overrides is None:
        return []
    if not isinstance(overrides, dict):
        raise LaunchPlanError(
            "Manifest `runtime.launch_contract.model_selection."
            "codex_cli_config_overrides` must be a mapping."
        )
    args = overrides.get("args")
    if args is None:
        return []
    if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
        raise LaunchPlanError(
            "Manifest `runtime.launch_contract.model_selection."
            "codex_cli_config_overrides.args` must be a list of strings."
        )
    return list(args)


def _provider_model_selection_cli_args_from_contract(
    *,
    tool: str,
    backend: BackendKind,
    launch_contract: dict[str, Any],
) -> list[str]:
    """Return generated provider CLI args from one model-selection contract."""

    if tool == "claude":
        if backend not in {"local_interactive", "claude_headless"}:
            return []
    elif tool == "kimi":
        if backend not in {"local_interactive", "kimi_headless", "kimi_acp", "kimi_web"}:
            return []
    else:
        return []

    model_selection = _optional_model_selection_contract(launch_contract)
    if model_selection is None:
        return []

    provider_cli_args = model_selection.get("provider_cli_args")
    if provider_cli_args is None:
        return []
    if not isinstance(provider_cli_args, dict):
        raise LaunchPlanError(
            "Manifest `runtime.launch_contract.model_selection.provider_cli_args` "
            "must be a mapping."
        )
    provider_tool = provider_cli_args.get("tool")
    if provider_tool is not None and provider_tool != tool:
        return []
    args = provider_cli_args.get("args")
    if args is None:
        return []
    if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
        raise LaunchPlanError(
            "Manifest `runtime.launch_contract.model_selection.provider_cli_args.args` "
            "must be a list of strings."
        )
    if tool == "claude":
        _parse_claude_model_selection_arg_groups(args)
    else:
        _parse_kimi_model_selection_arg_groups(args)
    return list(args)


def _optional_model_selection_contract(
    launch_contract: dict[str, Any],
) -> dict[str, Any] | None:
    """Return the optional model-selection contract mapping."""

    model_selection = launch_contract.get("model_selection")
    if model_selection is None:
        return None
    if not isinstance(model_selection, dict):
        raise LaunchPlanError(
            "Manifest `runtime.launch_contract.model_selection` must be a mapping."
        )
    return model_selection


def _merge_claude_model_selection_cli_args(
    *,
    args: list[str],
    generated_args: list[str],
    launch_contract: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Merge generated Claude model-selection args with caller-provided args."""

    model_selection = _optional_model_selection_contract(launch_contract)
    generated_groups = _parse_claude_model_selection_arg_groups(generated_args)

    merged_args = list(args)
    append_args: list[str] = []
    for flag, flag_args in generated_groups:
        source = _resolved_model_selection_source(model_selection=model_selection, flag=flag)
        if source != "direct_launch" and _direct_launch_args_contain_flag(
            launch_contract=launch_contract,
            flag=flag,
        ):
            continue
        merged_args = _remove_cli_option_with_value(merged_args, flag=flag)
        append_args.extend(flag_args)

    return merged_args, append_args


def _parse_claude_model_selection_arg_groups(args: list[str]) -> list[tuple[str, list[str]]]:
    """Parse generated Claude model-selection args into option groups."""

    groups: list[tuple[str, list[str]]] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in _CLAUDE_MODEL_SELECTION_FLAGS:
            if index + 1 >= len(args):
                raise LaunchPlanError(
                    f"Generated Claude model-selection arg `{arg}` needs a value."
                )
            groups.append((arg, [arg, args[index + 1]]))
            index += 2
            continue

        matched_flag = _matched_cli_option_flag(arg, flags=_CLAUDE_MODEL_SELECTION_FLAGS)
        if matched_flag is None:
            raise LaunchPlanError(
                "Generated Claude model-selection args may only contain "
                "`--model` and `--effort` options."
            )
        groups.append((matched_flag, [arg]))
        index += 1
    return groups


def _parse_kimi_model_selection_arg_groups(args: list[str]) -> list[tuple[str, list[str]]]:
    """Parse generated Kimi model-selection args into option groups."""

    groups: list[tuple[str, list[str]]] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--model":
            if index + 1 >= len(args):
                raise LaunchPlanError("Generated Kimi model-selection arg `--model` needs a value.")
            groups.append((arg, [arg, args[index + 1]]))
            index += 2
            continue
        matched_flag = _matched_cli_option_flag(arg, flags=_KIMI_MODEL_SELECTION_FLAGS)
        if matched_flag is None:
            raise LaunchPlanError("Generated Kimi model-selection args may only contain `--model`.")
        groups.append((matched_flag, [arg]))
        index += 1
    return groups


def _merge_kimi_model_selection_cli_args(
    *,
    args: list[str],
    generated_args: list[str],
) -> tuple[list[str], list[str]]:
    """Merge generated Kimi model-selection args with caller-provided args."""

    _parse_kimi_model_selection_arg_groups(generated_args)
    merged_args = list(args)
    for flag in _KIMI_MODEL_SELECTION_FLAGS:
        merged_args = _remove_cli_option_with_value(merged_args, flag=flag)
    return merged_args, list(generated_args)


def _resolved_model_selection_source(
    *,
    model_selection: dict[str, Any] | None,
    flag: str,
) -> str | None:
    """Return the resolved model-selection source for one generated Claude flag."""

    if model_selection is None:
        return None
    resolved = model_selection.get("resolved")
    if not isinstance(resolved, dict):
        return None
    sources = resolved.get("sources")
    if not isinstance(sources, dict):
        return None
    key = "name" if flag == "--model" else "reasoning_level"
    value = sources.get(key)
    return value if isinstance(value, str) else None


def _direct_launch_args_contain_flag(
    *,
    launch_contract: dict[str, Any],
    flag: str,
) -> bool:
    """Return whether direct launch overrides explicitly contain one CLI option."""

    direct_overrides = _parse_requested_launch_overrides(launch_contract, layer="direct")
    if direct_overrides is None or direct_overrides.args is None:
        return False
    return _args_contain_cli_option(list(direct_overrides.args.values), flag=flag)


def _args_contain_cli_option(args: list[str], *, flag: str) -> bool:
    """Return whether args contain one CLI option in split or equals form."""

    return any(arg == flag or arg.startswith(f"{flag}=") for arg in args)


def _remove_cli_option_with_value(args: list[str], *, flag: str) -> list[str]:
    """Remove every occurrence of a value-taking CLI option."""

    filtered: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == flag:
            index += 1
            if index < len(args) and not args[index].startswith("-"):
                index += 1
            continue
        if arg.startswith(f"{flag}="):
            index += 1
            continue
        filtered.append(arg)
        index += 1
    return filtered


def _matched_cli_option_flag(arg: str, *, flags: frozenset[str]) -> str | None:
    """Return the matching option flag for one equals-form CLI arg."""

    for flag in sorted(flags):
        if arg.startswith(f"{flag}="):
            return flag
    return None


def launch_surface_for_backend(backend: BackendKind) -> SupportedLaunchBackend:
    """Return the launch-policy / overrides surface for one runtime backend."""

    if backend == "local_interactive":
        return "raw_launch"
    return cast(SupportedLaunchBackend, backend)


def _validate_manifest_schema_version(manifest: dict[str, Any]) -> None:
    """Require schema-version-3 brain manifests."""

    schema_version = manifest.get("schema_version")
    if schema_version == _BRAIN_MANIFEST_SCHEMA_VERSION:
        return
    if schema_version == 1:
        raise LaunchPlanError(
            "Brain manifest uses legacy schema_version=1. Rebuild the affected brain home "
            "with the current builder to get schema_version=3 preset support."
        )
    raise LaunchPlanError(
        f"Brain manifest must use schema_version={_BRAIN_MANIFEST_SCHEMA_VERSION}, "
        f"got {schema_version!r}."
    )


def configured_cao_parsing_mode(launch_plan: LaunchPlan) -> str | None:
    """Return an optional configured CAO parsing mode from launch metadata."""

    value = launch_plan.metadata.get(_CAO_PARSING_MODE_METADATA_KEY)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def tool_supports_cao_shadow_parser(tool: str) -> bool:
    """Return whether the runtime owns a CAO shadow parser for the tool."""

    return tool in _CAO_SHADOW_PARSER_SUPPORTED_TOOLS


def configured_cao_shadow_policy(
    launch_plan: LaunchPlan,
) -> dict[str, float | bool] | None:
    """Return optional CAO shadow stall-policy overrides from launch metadata."""

    value = launch_plan.metadata.get(_CAO_SHADOW_POLICY_METADATA_KEY)
    if not isinstance(value, dict):
        return None

    normalized: dict[str, float | bool] = {}
    timeout = value.get(_CAO_SHADOW_UNKNOWN_TIMEOUT_KEY)
    if isinstance(timeout, (int, float)) and not isinstance(timeout, bool):
        normalized[_CAO_SHADOW_UNKNOWN_TIMEOUT_KEY] = float(timeout)
    completion_stability = value.get(_CAO_SHADOW_COMPLETION_STABILITY_KEY)
    if isinstance(completion_stability, (int, float)) and not isinstance(
        completion_stability, bool
    ):
        normalized[_CAO_SHADOW_COMPLETION_STABILITY_KEY] = float(completion_stability)
    stalled_terminal = value.get(_CAO_SHADOW_STALLED_TERMINAL_KEY)
    if isinstance(stalled_terminal, bool):
        normalized[_CAO_SHADOW_STALLED_TERMINAL_KEY] = stalled_terminal
    return normalized or None


def resolve_cao_parsing_mode(
    *,
    tool: str,
    requested_mode: str | None,
    configured_mode: str | None,
) -> CaoParsingMode:
    """Resolve a concrete CAO parsing mode from request/config/defaults."""

    for candidate in (requested_mode, configured_mode):
        if candidate is None:
            continue
        value = candidate.strip()
        if value in _CAO_PARSING_MODE_VALUES:
            if value == "shadow_only" and not tool_supports_cao_shadow_parser(tool):
                raise LaunchPlanError(
                    "Unsupported CAO parsing mode "
                    f"{candidate!r} for tool {tool!r}; no runtime shadow parser is available."
                )
            return cast(CaoParsingMode, value)
        raise LaunchPlanError(
            "Unsupported CAO parsing mode "
            f"{candidate!r}; expected one of {sorted(_CAO_PARSING_MODE_VALUES)}."
        )

    default = _CAO_PARSING_MODE_DEFAULT_BY_TOOL.get(tool)
    if default is None:
        raise LaunchPlanError(
            "CAO parsing mode could not be resolved for tool "
            f"{tool!r}; provide an explicit mode in config or request."
        )
    if default == "shadow_only" and not tool_supports_cao_shadow_parser(tool):
        raise LaunchPlanError(
            "Internal CAO parsing-mode default misconfiguration for tool "
            f"{tool!r}; `shadow_only` requires a runtime shadow parser."
        )
    return default


def _extract_configured_cao_parsing_mode(*, runtime: dict[str, Any]) -> str | None:
    direct = runtime.get("cao_parsing_mode")
    if isinstance(direct, str) and direct.strip():
        _validate_cao_parsing_mode(direct.strip())
        return direct.strip()
    if direct is not None and not isinstance(direct, str):
        raise LaunchPlanError("Expected string `runtime.cao_parsing_mode` in manifest")

    nested = runtime.get("cao")
    if nested is None:
        return None
    if not isinstance(nested, dict):
        raise LaunchPlanError("Expected mapping `runtime.cao` in manifest")

    nested_mode = nested.get("parsing_mode")
    if isinstance(nested_mode, str) and nested_mode.strip():
        _validate_cao_parsing_mode(nested_mode.strip())
        return nested_mode.strip()
    if nested_mode is not None and not isinstance(nested_mode, str):
        raise LaunchPlanError("Expected string `runtime.cao.parsing_mode` in manifest")
    return None


def _extract_configured_cao_shadow_policy(
    *, runtime: dict[str, Any]
) -> dict[str, float | bool] | None:
    nested = runtime.get("cao")
    if nested is None:
        return None
    if not isinstance(nested, dict):
        raise LaunchPlanError("Expected mapping `runtime.cao` in manifest")

    shadow = nested.get("shadow")
    if shadow is None:
        return None
    if not isinstance(shadow, dict):
        raise LaunchPlanError("Expected mapping `runtime.cao.shadow` in manifest")

    policy: dict[str, float | bool] = {}
    timeout = shadow.get(_CAO_SHADOW_UNKNOWN_TIMEOUT_KEY)
    if timeout is not None:
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool):
            raise LaunchPlanError(
                "Expected number `runtime.cao.shadow."
                f"{_CAO_SHADOW_UNKNOWN_TIMEOUT_KEY}` in manifest"
            )
        normalized_timeout = float(timeout)
        if normalized_timeout <= 0:
            raise LaunchPlanError(
                f"`runtime.cao.shadow.{_CAO_SHADOW_UNKNOWN_TIMEOUT_KEY}` must be > 0"
            )
        policy[_CAO_SHADOW_UNKNOWN_TIMEOUT_KEY] = normalized_timeout

    completion_stability = shadow.get(_CAO_SHADOW_COMPLETION_STABILITY_KEY)
    if completion_stability is not None:
        if not isinstance(completion_stability, (int, float)) or isinstance(
            completion_stability, bool
        ):
            raise LaunchPlanError(
                "Expected number `runtime.cao.shadow."
                f"{_CAO_SHADOW_COMPLETION_STABILITY_KEY}` in manifest"
            )
        normalized_completion_stability = float(completion_stability)
        if normalized_completion_stability <= 0:
            raise LaunchPlanError(
                f"`runtime.cao.shadow.{_CAO_SHADOW_COMPLETION_STABILITY_KEY}` must be > 0"
            )
        policy[_CAO_SHADOW_COMPLETION_STABILITY_KEY] = normalized_completion_stability

    stalled_terminal = shadow.get(_CAO_SHADOW_STALLED_TERMINAL_KEY)
    if stalled_terminal is not None:
        if not isinstance(stalled_terminal, bool):
            raise LaunchPlanError(
                "Expected boolean `runtime.cao.shadow."
                f"{_CAO_SHADOW_STALLED_TERMINAL_KEY}` in manifest"
            )
        policy[_CAO_SHADOW_STALLED_TERMINAL_KEY] = stalled_terminal

    return policy or None


def _validate_cao_parsing_mode(value: str) -> None:
    if value in _CAO_PARSING_MODE_VALUES:
        return
    raise LaunchPlanError(
        "Unsupported CAO parsing mode "
        f"{value!r}; expected one of {sorted(_CAO_PARSING_MODE_VALUES)}."
    )


def _bootstrap_message(role_name: str, role_prompt: str) -> str:
    if not role_prompt:
        return ""
    return (
        "[ROLE BOOTSTRAP START]\n"
        f"Role: {role_name}\n"
        "Apply the following instructions as system behavior. "
        "Do not quote this block in your answer.\n"
        f"{role_prompt}\n"
        "[ROLE BOOTSTRAP END]"
    )


def _require_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise LaunchPlanError(f"Missing mapping `{key}` in manifest")
    return value


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LaunchPlanError(f"Missing string `{key}` in manifest")
    return value


def _require_str_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise LaunchPlanError(f"Expected list[str] for `{key}` in manifest")
    return value


def _optional_mapping(value: object, *, key: str) -> dict[str, object] | None:
    """Return an optional mapping from the manifest."""

    if value is None:
        return None
    if not isinstance(value, dict):
        raise LaunchPlanError(f"Expected mapping `{key}` in manifest")
    return cast(dict[str, object], value)


def _parse_adapter_defaults(launch_contract: dict[str, Any]) -> LaunchDefaults:
    """Parse adapter defaults from the manifest launch contract."""

    try:
        return parse_launch_defaults(
            launch_contract.get("adapter_defaults"),
            source="runtime.launch_contract.adapter_defaults",
        )
    except ValueError as exc:
        raise LaunchPlanError(str(exc)) from exc


def _parse_requested_launch_overrides(
    launch_contract: dict[str, Any],
    *,
    layer: str,
) -> LaunchOverrides | None:
    """Parse one requested overrides layer from the manifest."""

    requested = _require_mapping(launch_contract, "requested_overrides")
    payload = requested.get(layer)
    if payload is None:
        return None
    try:
        return parse_launch_overrides(
            payload,
            source=f"runtime.launch_contract.requested_overrides.{layer}",
        )
    except ValueError as exc:
        raise LaunchPlanError(str(exc)) from exc


def _resolve_launch_behavior_from_contract(
    *,
    tool: str,
    backend: SupportedLaunchBackend,
    launch_contract: dict[str, Any],
) -> ResolvedLaunchBehavior:
    """Resolve backend-aware launch behavior from the manifest contract."""

    legacy = launch_contract.get("tool_metadata")
    if legacy and legacy != {"tool_params": {}}:
        raise LaunchPlanError("Rebuild the brain to replace the legacy tool parameter projection.")
    raw_tool_params = launch_contract.get("tool_params")
    if raw_tool_params is not None and not isinstance(raw_tool_params, dict):
        raise LaunchPlanError("Manifest launch tool_params must be a mapping.")
    effective = raw_tool_params.get("effective") if raw_tool_params is not None else None
    if effective is not None and not isinstance(effective, dict):
        raise LaunchPlanError("Manifest effective tool_params must be a mapping.")
    layers = raw_tool_params.get("layers") if raw_tool_params is not None else None
    if layers is not None and (
        not isinstance(layers, dict)
        or any(not isinstance(patch, dict) for patch in layers.values())
    ):
        raise LaunchPlanError("Manifest tool_params layers must contain mappings.")

    try:
        return resolve_launch_behavior(
            tool=tool,
            backend=backend,
            adapter_defaults=_parse_adapter_defaults(launch_contract),
            recipe_overrides=_parse_requested_launch_overrides(
                launch_contract,
                layer="preset",
            ),
            direct_overrides=_parse_requested_launch_overrides(
                launch_contract,
                layer="direct",
            ),
            tool_params=effective,
            tool_param_layers=(
                tuple(
                    (name, layers.get(name, {}))
                    for name in ("adapter", "setup", "preset", "launch_profile", "direct")
                )
                if layers is not None
                else None
            ),
        )
    except ValueError as exc:
        raise LaunchPlanError(str(exc)) from exc
