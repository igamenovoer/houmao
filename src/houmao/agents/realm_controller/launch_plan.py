"""Launch-plan composition for brain + role inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, cast

from houmao.agents.mailbox_runtime_models import MailboxResolvedConfig
from .errors import LaunchPlanError
from houmao.agents.mailbox_runtime_support import mailbox_env_bindings, mailbox_env_var_names
from .loaders import RolePackage, parse_allowlisted_env
from .models import BackendKind, CaoParsingMode, LaunchPlan, RoleInjectionPlan

_CLAUDE_HEADLESS_RESERVED_ARGS: Final[tuple[str, ...]] = (
    "--resume",
    "--output-format",
    "--append-system-prompt",
)
_CODEX_HEADLESS_RESERVED_ARGS: Final[tuple[str, ...]] = (
    "app-server",
    "exec",
    "resume",
    "--json",
)
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


@dataclass(frozen=True)
class LaunchPlanRequest:
    """Inputs required to compose a launch plan."""

    brain_manifest: dict[str, Any]
    role_package: RolePackage
    backend: BackendKind
    working_directory: Path
    mailbox: MailboxResolvedConfig | None = None


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

    inputs = _require_mapping(manifest, "inputs")
    runtime = _require_mapping(manifest, "runtime")
    credentials = _require_mapping(manifest, "credentials")
    env_contract = _require_mapping(credentials, "env_contract")
    home_selector = _require_mapping(runtime, "launch_home_selector")

    tool = _require_str(inputs, "tool")
    executable = _require_str(runtime, "launch_executable")
    launch_args = _require_str_list(runtime, "launch_args")
    home_env_var = _require_str(home_selector, "env_var")
    home_path = Path(_require_str(home_selector, "value")).resolve()

    env_source = Path(_require_str(env_contract, "source_file")).resolve()
    allowlist = _require_str_list(env_contract, "allowlisted_env_vars")
    env_values, selected_env_names = parse_allowlisted_env(env_source, allowlist)
    env_var_names = list(selected_env_names)

    if request.mailbox is not None:
        mailbox_env = mailbox_env_bindings(request.mailbox)
        env_values.update(mailbox_env)
        env_var_names = sorted({*env_var_names, *mailbox_env_var_names(request.mailbox)})

    role_injection = plan_role_injection(
        backend=request.backend,
        role_name=request.role_package.role_name,
        role_prompt=request.role_package.system_prompt,
    )

    args = list(launch_args)
    metadata: dict[str, Any] = {
        "env_source_file": str(env_source),
        "selected_env_vars": selected_env_names,
    }
    configured_cao_parsing_mode = _extract_configured_cao_parsing_mode(runtime=runtime)
    if configured_cao_parsing_mode is not None:
        metadata[_CAO_PARSING_MODE_METADATA_KEY] = configured_cao_parsing_mode
    configured_cao_shadow_policy = _extract_configured_cao_shadow_policy(runtime=runtime)
    if configured_cao_shadow_policy is not None:
        metadata[_CAO_SHADOW_POLICY_METADATA_KEY] = configured_cao_shadow_policy

    if request.backend == "claude_headless":
        conflicts = _find_reserved_arg_conflicts(
            args=args,
            reserved_args=_CLAUDE_HEADLESS_RESERVED_ARGS,
        )
        if conflicts:
            joined = ", ".join(conflicts)
            raise LaunchPlanError(
                "Claude launch.args contains backend-reserved argument(s): "
                f"{joined}. Remove these from tool-adapter `launch.args`; "
                "the backend injects them automatically."
            )
        metadata["headless_reserved_args"] = list(_CLAUDE_HEADLESS_RESERVED_ARGS)
    elif request.backend == "codex_headless":
        conflicts = _find_reserved_arg_conflicts(
            args=args,
            reserved_args=_CODEX_HEADLESS_RESERVED_ARGS,
        )
        if conflicts:
            joined = ", ".join(conflicts)
            raise LaunchPlanError(
                "Codex launch.args contains backend-reserved argument(s): "
                f"{joined}. Remove these from tool-adapter `launch.args`; "
                "the backend injects them automatically."
            )
        metadata["headless_reserved_args"] = list(_CODEX_HEADLESS_RESERVED_ARGS)
        metadata["headless_output_format"] = "stream-json"

    if request.backend == "codex_app_server":
        args = [*args, "app-server"]
    elif request.backend == "codex_headless":
        metadata["codex_headless_cli_mode"] = "exec_json_resume"
    elif request.backend == "gemini_headless":
        args = [*args, "-p"]
        metadata["headless_reserved_args"] = ["--resume", "--output-format"]
        metadata["headless_output_format"] = "stream-json"
    elif request.backend == "claude_headless":
        metadata["headless_output_format"] = "stream-json"

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
    )


def plan_role_injection(
    *,
    backend: BackendKind,
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


def backend_for_tool(tool: str, prefer_cao: bool = False) -> BackendKind:
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
    if tool == "codex":
        return "codex_headless"
    if tool == "claude":
        return "claude_headless"
    if tool == "gemini":
        return "gemini_headless"
    raise LaunchPlanError(f"No default backend for tool {tool!r}")


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


def _find_reserved_arg_conflicts(*, args: list[str], reserved_args: tuple[str, ...]) -> list[str]:
    conflicts: set[str] = set()
    for arg in args:
        for reserved in reserved_args:
            if arg == reserved or arg.startswith(f"{reserved}="):
                conflicts.add(reserved)
    return sorted(conflicts)


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
