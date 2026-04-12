"""Launch-plan composition for brain + role inputs."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Final, cast

from houmao.agents.launch_policy import apply_launch_policy
from houmao.agents.launch_policy.models import (
    LaunchPolicyApplicationKind,
    LaunchPolicyCompatibilityError,
    LaunchPolicyError,
    LaunchPolicyRequest,
    OperatorPromptMode,
)
from houmao.agents.launch_overrides import (
    LaunchDefaults,
    LaunchOverrides,
    ResolvedLaunchBehavior,
    ToolLaunchMetadata,
    parse_launch_defaults,
    parse_launch_overrides,
    parse_tool_launch_metadata,
    resolve_launch_behavior,
)
from houmao.agents.launch_overrides.models import SupportedLaunchBackend
from houmao.agents.mailbox_runtime_models import MailboxResolvedConfig
from .errors import LaunchPlanError, LaunchPolicyResolutionError
from .loaders import RolePackage, parse_allowlisted_env
from .models import BackendKind, CaoParsingMode, LaunchPlan, RoleInjectionPlan

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


@dataclass(frozen=True)
class LaunchPlanRequest:
    """Inputs required to compose a launch plan."""

    brain_manifest: dict[str, Any]
    role_package: RolePackage
    backend: BackendKind
    working_directory: Path
    mailbox: MailboxResolvedConfig | None = None
    intent: LaunchPolicyApplicationKind = "provider_start"


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
    credentials = _require_mapping(manifest, "credentials")
    env_contract = _require_mapping(credentials, "env_contract")
    home_selector = _require_mapping(runtime, "launch_home_selector")
    launch_contract = _require_mapping(runtime, "launch_contract")

    tool = _require_str(inputs, "tool")
    executable = _require_str(runtime, "launch_executable")
    home_env_var = _require_str(home_selector, "env_var")
    home_path = Path(_require_str(home_selector, "value")).resolve()

    env_source = Path(_require_str(env_contract, "source_file")).resolve()
    allowlist = _require_str_list(env_contract, "allowlisted_env_vars")
    env_values, selected_env_names = parse_allowlisted_env(env_source, allowlist)
    env_var_names = list(selected_env_names)
    persistent_env_records = _persistent_launch_env_records(launch_contract)
    env_values.update(persistent_env_records)
    env_var_names = sorted({*env_var_names, *persistent_env_records.keys()})

    role_injection = plan_role_injection(
        backend=request.backend,
        tool=tool,
        role_name=request.role_package.role_name,
        role_prompt=request.role_package.system_prompt,
    )

    metadata: dict[str, Any] = {
        "env_source_file": str(env_source),
        "selected_env_vars": selected_env_names,
    }
    resolved_launch_behavior = _resolve_launch_behavior_from_contract(
        tool=tool,
        backend=_launch_surface_for_backend(request.backend),
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
        backend=_launch_surface_for_backend(request.backend),
    )
    args = list(resolved_launch_behavior.args_before_policy)
    configured_cao_parsing_mode = _extract_configured_cao_parsing_mode(runtime=runtime)
    if configured_cao_parsing_mode is not None:
        metadata[_CAO_PARSING_MODE_METADATA_KEY] = configured_cao_parsing_mode
    configured_cao_shadow_policy = _extract_configured_cao_shadow_policy(runtime=runtime)
    if configured_cao_shadow_policy is not None:
        metadata[_CAO_SHADOW_POLICY_METADATA_KEY] = configured_cao_shadow_policy

    if request.backend == "codex_headless":
        metadata["codex_headless_cli_mode"] = "exec_json_resume"
    if request.backend in {"claude_headless", "gemini_headless", "codex_headless"}:
        metadata["headless_output_format"] = "stream-json"
        metadata["headless_display_style"] = "plain"
        metadata["headless_display_detail"] = "concise"

    requested_operator_prompt_mode = _requested_operator_prompt_mode(manifest)
    policy_backend = _launch_surface_for_backend(request.backend)
    policy_env = dict(env_values)
    override_strategy = os.environ.get(_LAUNCH_POLICY_OVERRIDE_ENV_VAR, "").strip()
    if override_strategy:
        policy_env[_LAUNCH_POLICY_OVERRIDE_ENV_VAR] = override_strategy

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
    if provider_model_selection_cli_args:
        args, provider_model_selection_cli_args = _merge_claude_model_selection_cli_args(
            args=args,
            generated_args=provider_model_selection_cli_args,
            launch_contract=launch_contract,
        )
    args.extend(codex_cli_config_args)
    args.extend(provider_model_selection_cli_args)
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
            if provider_model_selection_cli_args:
                backend_resolution["provider_model_selection_cli_args"] = list(
                    provider_model_selection_cli_args
                )

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
        mailbox=request.mailbox,
        launch_policy_provenance=launch_policy_result.provenance,
    )


def plan_role_injection(
    *,
    backend: BackendKind,
    tool: str | None = None,
    role_name: str,
    role_prompt: str,
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
        if tool == "gemini":
            return RoleInjectionPlan(
                method="bootstrap_message",
                role_name=role_name,
                prompt=role_prompt,
                bootstrap_message=_bootstrap_message(role_name, role_prompt),
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

    if backend == "gemini_headless":
        return RoleInjectionPlan(
            method="bootstrap_message",
            role_name=role_name,
            prompt=role_prompt,
            bootstrap_message=_bootstrap_message(role_name, role_prompt),
        )

    if backend in {"cao_rest", "houmao_server_rest"}:
        return RoleInjectionPlan(
            method="cao_profile",
            role_name=role_name,
            prompt=role_prompt,
        )

    raise LaunchPlanError(f"Unsupported backend: {backend}")


def backend_for_tool(
    tool: str,
    prefer_cao: bool = False,
    *,
    prefer_local_interactive: bool = False,
) -> BackendKind:
    """Return the default backend for a tool.

    Parameters
    ----------
    tool:
        Tool name from the brain manifest.
    prefer_cao:
        If true, force CAO backend regardless of tool.

    Returns
    -------
    BackendKind
        Selected backend.
    """

    if prefer_cao:
        return "cao_rest"
    if prefer_local_interactive:
        if tool in {"codex", "claude", "gemini"}:
            return "local_interactive"
        raise LaunchPlanError(f"No local interactive backend for tool {tool!r}")
    if tool == "codex":
        return "codex_headless"
    if tool == "claude":
        return "claude_headless"
    if tool == "gemini":
        return "gemini_headless"
    raise LaunchPlanError(f"No default backend for tool {tool!r}")


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

    if tool != "claude" or backend not in {"local_interactive", "claude_headless"}:
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
    _parse_claude_model_selection_arg_groups(args)
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


def _launch_surface_for_backend(backend: BackendKind) -> SupportedLaunchBackend:
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


def _parse_tool_launch_metadata(launch_contract: dict[str, Any]) -> ToolLaunchMetadata:
    """Parse tool-launch metadata from the manifest."""

    try:
        return parse_tool_launch_metadata(
            launch_contract.get("tool_metadata"),
            source="runtime.launch_contract.tool_metadata",
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
            metadata=_parse_tool_launch_metadata(launch_contract),
        )
    except ValueError as exc:
        raise LaunchPlanError(str(exc)) from exc
