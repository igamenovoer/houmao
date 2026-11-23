"""Registry loading, version detection, and launch-policy application."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import replace
import re
import subprocess
from pathlib import Path
from typing import Any, Literal, Mapping, cast

import yaml

from houmao.agents.launch_overrides.native import split_permission_args
from houmao.agents.launch_policy.models import (
    LaunchPolicyAction,
    LaunchPolicyCompatibilityError,
    LaunchPolicyError,
    LaunchPolicyProvenance,
    LaunchPolicyRegistryDocument,
    LaunchPolicyRequest,
    LaunchPolicyResult,
    LaunchPolicySelectionSource,
    LaunchPolicyStrategy,
    LaunchSurface,
    MinimalInputContract,
    NativeSystemPromptContract,
    NativeSystemPromptMethod,
    OperatorPromptMode,
    OwnedPathSpec,
    SupportedVersionSpec,
    StrategyEvidence,
    ToolVersion,
)
from houmao.agents.launch_policy.permission_state import permission_projection
from houmao.agents.launch_policy.provider_hooks import (
    provider_state_mutation_lock,
    run_provider_hook,
    set_json_key,
    set_toml_key,
)
from houmao.agents.tool_params import get_tool_params_adapter, validate_tool_params

_VERSION_PATTERN = re.compile(r"(?<![\w.])[vV]?([0-9]+(?:\.[0-9]+){2,}[A-Za-z0-9._+-]*)")
_OVERRIDE_ENV_VAR = "HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY"
_EvidenceKind = Literal["official_docs", "source_reference", "live_probe"]
_ActionKind = Literal[
    "cli_arg.ensure_present",
    "cli_arg.ensure_absent",
    "json.set",
    "toml.set",
    "validate.reject_conflicting_launch_args",
    "provider_hook.call",
]
_OPERATOR_PROMPT_MODES: tuple[OperatorPromptMode, ...] = ("as_is", "unattended")
_SUPPORTED_BACKENDS: tuple[LaunchSurface, ...] = (
    "raw_launch",
    "codex_headless",
    "codex_app_server",
    "claude_headless",
    "kimi_headless",
    "kimi_acp",
    "dsh_headless",
    "dsh_acp",
    "dsh_web",
    "kimi_web",
    "cao_rest",
)
_EVIDENCE_KINDS: tuple[_EvidenceKind, ...] = (
    "official_docs",
    "source_reference",
    "live_probe",
)
_ACTION_KINDS: tuple[_ActionKind, ...] = (
    "cli_arg.ensure_present",
    "cli_arg.ensure_absent",
    "json.set",
    "toml.set",
    "validate.reject_conflicting_launch_args",
    "provider_hook.call",
)
_RESUME_CONTROL_ALLOWED_PROVIDER_HOOKS: frozenset[str] = frozenset(
    {
        "codex.canonicalize_unattended_launch_inputs",
        "codex.append_unattended_cli_overrides",
        "kimi.canonicalize_unattended_launch_inputs",
        "kimi.project_tui_permission",
        "claude.apply_permission_mode",
    }
)
_PERMISSION_KEYS = {
    "claude": ("permission_mode",),
    "codex": ("approval_policy", "sandbox_mode"),
    "kimi": ("permission_mode",),
    "dsh": ("permissions",),
}


def apply_launch_policy(request: LaunchPolicyRequest) -> LaunchPolicyResult:
    """Resolve and apply launch policy for one launch request."""

    strategy = None
    provenance = None
    mode = request.requested_operator_prompt_mode
    if mode == "unattended":
        detected_version = detect_tool_version(executable=request.executable)
        strategy, selection_source = resolve_strategy(
            request=request, detected_version=detected_version
        )
        provenance = LaunchPolicyProvenance(
            requested_operator_prompt_mode=mode,
            detected_tool_version=detected_version.raw,
            selected_strategy_id=strategy.strategy_id,
            selection_source=selection_source,
            override_env_var_name=_OVERRIDE_ENV_VAR if selection_source == "env_override" else None,
        )
    elif mode not in {None, "as_is"}:
        raise LaunchPolicyError(f"Unsupported operator_prompt_mode `{mode}`.")
    permission_keys = _PERMISSION_KEYS.get(request.tool, ())
    try:
        native_args, aliases = split_permission_args(
            request.tool, request.base_args, source="launch args"
        )
        if aliases:
            aliases = validate_tool_params(request.tool, aliases, source="launch args")
    except ValueError as exc:
        raise LaunchPolicyError(str(exc)) from exc
    authored = {
        key: value
        for key, value in {**aliases, **request.tool_params}.items()
        if key in permission_keys and value is not None
    }
    defaults = strategy.permission_defaults if strategy is not None else {}
    permissions = {**defaults, **authored}
    if request.tool == "dsh":
        permissions["permissions"] = {
            **defaults.get("permissions", {}),
            **authored.get("permissions", {}),
        }
    if request.tool == "kimi" and permissions:
        adapter = get_tool_params_adapter(request.tool)
        try:
            adapter.prepare_launch(
                adapter.parse_effective(permissions, source="effective tool_params"),
                backend=request.backend,
            )
        except ValueError as exc:
            raise LaunchPolicyError(str(exc)) from exc
    authored_fields = _permission_fields(authored)
    sources = {
        field: request.tool_param_sources.get(
            field, "launch args" if field in aliases else "tool_params"
        )
        if field in authored_fields
        else f"strategy:{strategy.strategy_id}"
        if strategy is not None
        else "native baseline"
        for field in _permission_fields(permissions)
    }
    request = replace(request, tool_params={**request.tool_params, **permissions})
    args = list(native_args)
    actions = strategy.actions if strategy is not None else _as_is_actions(request, permissions)
    project_home_permissions = (
        request.application_kind == "provider_start"
        and request.tool in {"claude", "codex", "kimi"}
        and not (request.tool == "kimi" and request.backend == "kimi_headless")
        and (permissions or (request.home_path / ".houmao-launch-permissions.json").is_file())
    )

    mutation_context = (
        provider_state_mutation_lock(request.home_path)
        if request.application_kind == "provider_start" and (actions or project_home_permissions)
        else nullcontext()
    )
    with (
        mutation_context,
        (
            permission_projection(tool=request.tool, home=request.home_path, effective=permissions)
            if project_home_permissions
            else nullcontext()
        ),
    ):
        for action in actions:
            _apply_action(action=action, request=request, args=args)
    return LaunchPolicyResult(
        executable=request.executable,
        args=tuple(args),
        provenance=provenance,
        strategy=strategy,
        permissions=permissions,
        permission_sources=sources,
    )


def _permission_fields(permissions: Mapping[str, Any]) -> set[str]:
    """Describe permission values by their user-facing paths."""

    return {
        field
        for key, value in permissions.items()
        for field in ((f"{key}.{child}" for child in value) if isinstance(value, dict) else (key,))
    }


def _as_is_actions(
    request: LaunchPolicyRequest, permissions: Mapping[str, Any]
) -> tuple[LaunchPolicyAction, ...]:
    """Project authored settings without adding unattended bootstrap actions."""

    hooks: tuple[str, ...] = ()
    if permissions:
        if request.tool == "claude":
            hooks = ("claude.apply_permission_mode",)
        elif request.tool == "codex":
            hooks = ("codex.apply_runtime_permissions",)
            if request.backend != "codex_app_server":
                hooks += ("codex.append_unattended_cli_overrides",)
        elif request.tool == "kimi" and request.backend == "raw_launch":
            hooks = ("kimi.project_tui_permission",)
        elif request.tool == "kimi" and request.backend in {"kimi_acp", "kimi_web"}:
            hooks = ("kimi.project_service_permission",)
    return tuple(LaunchPolicyAction("provider_hook.call", {"hook_id": hook}) for hook in hooks)


def detect_tool_version(*, executable: str) -> ToolVersion:
    """Probe one CLI executable with `--version` and parse the result."""

    try:
        completed = subprocess.run(
            [executable, "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise LaunchPolicyError(
            f"Could not probe `{executable} --version`: the executable was not found."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise LaunchPolicyError(
            f"Could not probe `{executable} --version`: "
            f"{exc.stderr.strip() or exc.stdout.strip() or exc}"
        ) from exc

    output = completed.stdout.strip() or completed.stderr.strip()
    match = _VERSION_PATTERN.search(output)
    if match is None:
        raise LaunchPolicyError(
            f"Could not parse a semantic version from `{executable} --version`: `{output}`."
        )
    return ToolVersion.parse(match.group(1))


def resolve_strategy(
    *, request: LaunchPolicyRequest, detected_version: ToolVersion
) -> tuple[LaunchPolicyStrategy, LaunchPolicySelectionSource]:
    """Resolve one registry strategy for the request."""

    requested_operator_prompt_mode = request.requested_operator_prompt_mode
    if requested_operator_prompt_mode is None:
        raise LaunchPolicyError("Launch policy strategy resolution requires a prompt mode.")

    documents = load_registry_documents(tool=request.tool)
    override_strategy_id = request.env.get(_OVERRIDE_ENV_VAR, "").strip()
    if override_strategy_id:
        for document in documents:
            for strategy in document.strategies:
                if strategy.strategy_id != override_strategy_id:
                    continue
                if strategy.operator_prompt_mode != requested_operator_prompt_mode:
                    break
                if request.backend not in strategy.backends:
                    break
                return strategy, "env_override"
        raise LaunchPolicyError(
            f"{_OVERRIDE_ENV_VAR}={override_strategy_id!r} does not match a known "
            f"{request.tool} unattended strategy for backend={request.backend!r}."
        )

    candidates = [
        strategy
        for document in documents
        for strategy in document.strategies
        if strategy.operator_prompt_mode == requested_operator_prompt_mode
        and request.backend in strategy.backends
    ]
    matches = [
        strategy
        for strategy in candidates
        if strategy.supported_versions.contains(detected_version)
    ]

    if not matches:
        reason = "No compatible unattended launch strategy exists"
        if candidates:
            requirements = ", ".join(item.supported_versions.to_payload() for item in candidates)
            reason = f"{reason} (requires a release or RC matching {requirements})"
        raise LaunchPolicyCompatibilityError(
            tool=request.tool,
            backend=request.backend,
            detected_version=detected_version.raw,
            requested_operator_prompt_mode=requested_operator_prompt_mode,
            reason=reason,
        )
    if len(matches) != 1:
        strategy_ids = ", ".join(item.strategy_id for item in matches)
        raise LaunchPolicyCompatibilityError(
            tool=request.tool,
            backend=request.backend,
            detected_version=detected_version.raw,
            requested_operator_prompt_mode=requested_operator_prompt_mode,
            reason=f"Launch policy resolution is ambiguous: {strategy_ids}",
        )
    return matches[0], "registry"


def packaged_tool_version_requirement(*, tool: str, backend: LaunchSurface) -> SupportedVersionSpec:
    """Read the executable requirement for a backend from its packaged unattended strategy."""

    requirements = [
        strategy.supported_versions
        for document in load_registry_documents(tool=tool)
        for strategy in document.strategies
        if backend in strategy.backends and strategy.operator_prompt_mode == "unattended"
    ]
    if len(requirements) != 1:
        raise LaunchPolicyError(
            f"Expected one packaged executable requirement for tool={tool!r}, backend={backend!r}."
        )
    return requirements[0]


def validate_packaged_tool_version(
    *, tool: str, backend: LaunchSurface, version: str | None
) -> ToolVersion:
    """Check the native executable independently of prompt policy and strategy overrides."""

    requirement = packaged_tool_version_requirement(tool=tool, backend=backend)
    message = (
        f"{tool} backend {backend!r} requires version {requirement.to_payload()} "
        f"(release or RC). Detected {version!r}."
    )
    try:
        parsed = ToolVersion.parse(version) if version else None
    except LaunchPolicyError as exc:
        raise LaunchPolicyError(message) from exc
    if parsed is None or not requirement.contains(parsed):
        raise LaunchPolicyError(message)
    return parsed


def load_registry_documents(*, tool: str) -> tuple[LaunchPolicyRegistryDocument, ...]:
    """Load registry YAML documents for one tool."""

    registry_dir = Path(__file__).resolve().parent / "registry"
    path = registry_dir / f"{tool}.yaml"
    if not path.is_file():
        return ()

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise LaunchPolicyError(f"Registry file `{path}` must contain a top-level mapping.")
    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise LaunchPolicyError(f"Registry file `{path}` only supports schema_version=1.")
    payload_tool = payload.get("tool")
    if not isinstance(payload_tool, str) or payload_tool != tool:
        raise LaunchPolicyError(f"Registry file `{path}` has mismatched tool `{payload_tool}`.")

    strategies_payload = payload.get("strategies")
    if not isinstance(strategies_payload, list) or not strategies_payload:
        raise LaunchPolicyError(f"Registry file `{path}` must define at least one strategy.")

    return (
        LaunchPolicyRegistryDocument(
            schema_version=1,
            tool=tool,
            strategies=tuple(
                _parse_strategy(
                    payload=item,
                    source=f"{path}:strategies[{index}]",
                )
                for index, item in enumerate(strategies_payload)
            ),
        ),
    )


def _parse_strategy(*, payload: object, source: str) -> LaunchPolicyStrategy:
    """Parse one registry strategy entry."""

    if not isinstance(payload, dict):
        raise LaunchPolicyError(f"{source} must be a mapping.")

    strategy_id = _require_non_blank_str(payload, "strategy_id", source=source)
    operator_prompt_mode_raw = _require_non_blank_str(
        payload, "operator_prompt_mode", source=source
    )
    if operator_prompt_mode_raw not in _OPERATOR_PROMPT_MODES:
        raise LaunchPolicyError(f"{source}.operator_prompt_mode must be `as_is` or `unattended`.")
    operator_prompt_mode = operator_prompt_mode_raw

    backends_payload = payload.get("backends")
    if not isinstance(backends_payload, list) or not backends_payload:
        raise LaunchPolicyError(f"{source}.backends must be a non-empty list.")
    parsed_backends: list[LaunchSurface] = []
    for item in backends_payload:
        backend_raw = _require_non_blank_item(item, source=f"{source}.backends")
        if backend_raw not in _SUPPORTED_BACKENDS:
            raise LaunchPolicyError(
                f"{source}.backends contains unsupported backend `{backend_raw}`."
            )
        parsed_backends.append(backend_raw)
    backends = tuple(parsed_backends)

    supported_versions_raw = payload.get("supported_versions")
    if not isinstance(supported_versions_raw, str) or not supported_versions_raw.strip():
        raise LaunchPolicyError(
            f"{source}.supported_versions must be a non-empty dependency-style specifier string."
        )
    supported_versions = SupportedVersionSpec.parse(supported_versions_raw)

    minimal_inputs_payload = payload.get("minimal_inputs")
    if not isinstance(minimal_inputs_payload, dict):
        raise LaunchPolicyError(f"{source}.minimal_inputs must be a mapping.")
    credential_forms_payload = minimal_inputs_payload.get("credential_forms")
    if not isinstance(credential_forms_payload, list) or not credential_forms_payload:
        raise LaunchPolicyError(
            f"{source}.minimal_inputs.credential_forms must be a non-empty list."
        )
    requires_user_prepared_state = minimal_inputs_payload.get("requires_user_prepared_state")
    if not isinstance(requires_user_prepared_state, bool):
        raise LaunchPolicyError(
            f"{source}.minimal_inputs.requires_user_prepared_state must be a boolean."
        )
    notes_payload = minimal_inputs_payload.get("notes", [])
    if not isinstance(notes_payload, list) or not all(
        isinstance(item, str) for item in notes_payload
    ):
        raise LaunchPolicyError(f"{source}.minimal_inputs.notes must be a list of strings.")
    minimal_inputs = MinimalInputContract(
        credential_forms=tuple(str(item) for item in credential_forms_payload),
        requires_user_prepared_state=requires_user_prepared_state,
        notes=tuple(notes_payload),
    )

    system_prompt_payload = payload.get("system_prompt")
    if not isinstance(system_prompt_payload, dict):
        raise LaunchPolicyError(f"{source}.system_prompt must be a mapping.")
    system_prompt = _parse_native_system_prompt_contract(
        payload=system_prompt_payload,
        source=f"{source}.system_prompt",
    )

    evidence_payload = payload.get("evidence")
    if not isinstance(evidence_payload, list) or not evidence_payload:
        raise LaunchPolicyError(f"{source}.evidence must be a non-empty list.")
    evidence = tuple(
        _parse_evidence(item=item, source=f"{source}.evidence") for item in evidence_payload
    )

    owned_paths_payload = payload.get("owned_paths")
    if not isinstance(owned_paths_payload, list):
        raise LaunchPolicyError(f"{source}.owned_paths must be a list.")
    owned_paths = tuple(
        _parse_owned_path(item=item, source=f"{source}.owned_paths") for item in owned_paths_payload
    )

    actions_payload = payload.get("actions")
    if not isinstance(actions_payload, list):
        raise LaunchPolicyError(f"{source}.actions must be a list.")
    actions = tuple(
        _parse_action(item=item, source=f"{source}.actions[{index}]")
        for index, item in enumerate(actions_payload)
    )
    permission_defaults = payload.get("permission_defaults", {})
    if not isinstance(permission_defaults, dict):
        raise LaunchPolicyError(f"{source}.permission_defaults must be a mapping.")

    return LaunchPolicyStrategy(
        strategy_id=strategy_id,
        operator_prompt_mode=operator_prompt_mode,
        backends=backends,
        supported_versions=supported_versions,
        minimal_inputs=minimal_inputs,
        system_prompt=system_prompt,
        evidence=evidence,
        owned_paths=owned_paths,
        actions=actions,
        permission_defaults=permission_defaults,
    )


def _parse_native_system_prompt_contract(
    *,
    payload: Mapping[str, Any],
    source: str,
) -> NativeSystemPromptContract:
    """Parse one qualified native system-prompt contract."""

    method_raw = _require_non_blank_str(payload, "method", source=source)
    supported_methods = {
        "native_developer_instructions",
        "native_append_system_prompt",
        "native_home_system_prompt",
        "native_system_prompt_section",
    }
    if method_raw not in supported_methods:
        raise LaunchPolicyError(f"{source}.method is unsupported: `{method_raw}`.")
    owned_surface = _require_non_blank_str(payload, "owned_surface", source=source)

    conflicts_payload = payload.get("precedence_conflicts", [])
    if not isinstance(conflicts_payload, list) or not all(
        isinstance(item, str) and item.strip() for item in conflicts_payload
    ):
        raise LaunchPolicyError(f"{source}.precedence_conflicts must be a list of strings.")

    engine_env_payload = payload.get("required_engine_env", {})
    if not isinstance(engine_env_payload, dict) or not all(
        isinstance(key, str) and key.strip() and isinstance(value, str)
        for key, value in engine_env_payload.items()
    ):
        raise LaunchPolicyError(f"{source}.required_engine_env must map strings to strings.")

    evidence_payload = payload.get("evidence", [])
    if not isinstance(evidence_payload, list):
        raise LaunchPolicyError(f"{source}.evidence must be a list when present.")
    evidence = tuple(
        _parse_evidence(item=item, source=f"{source}.evidence") for item in evidence_payload
    )
    if not evidence:
        raise LaunchPolicyError(f"{source}.evidence must describe the native prompt surface.")

    return NativeSystemPromptContract(
        method=cast(NativeSystemPromptMethod, method_raw),
        owned_surface=owned_surface,
        precedence_conflicts=tuple(item.strip() for item in conflicts_payload),
        required_engine_env={str(key): str(value) for key, value in engine_env_payload.items()},
        evidence=evidence,
    )


def _parse_evidence(*, item: object, source: str) -> StrategyEvidence:
    """Parse one evidence item."""

    if not isinstance(item, dict):
        raise LaunchPolicyError(f"{source} must be a mapping.")
    kind_raw = _require_non_blank_str(item, "kind", source=source)
    if kind_raw not in _EVIDENCE_KINDS:
        raise LaunchPolicyError(f"{source}.kind is unsupported: `{kind_raw}`.")
    return StrategyEvidence(
        kind=kind_raw,
        ref=_require_non_blank_str(item, "ref", source=source),
        note=_require_non_blank_str(item, "note", source=source),
    )


def _parse_owned_path(*, item: object, source: str) -> OwnedPathSpec:
    """Parse one owned-path declaration."""

    if not isinstance(item, dict):
        raise LaunchPolicyError(f"{source} must be a mapping.")
    keys_payload = item.get("keys")
    if not isinstance(keys_payload, list) or not keys_payload:
        raise LaunchPolicyError(f"{source}.keys must be a non-empty list.")
    return OwnedPathSpec(
        path=_require_non_blank_str(item, "path", source=source),
        keys=tuple(
            _require_non_blank_item(value, source=f"{source}.keys") for value in keys_payload
        ),
    )


def _parse_action(*, item: object, source: str) -> LaunchPolicyAction:
    """Parse one launch-policy action."""

    if not isinstance(item, dict):
        raise LaunchPolicyError(f"{source} must be a mapping.")
    kind_raw = _require_non_blank_str(item, "kind", source=source)
    if kind_raw not in _ACTION_KINDS:
        raise LaunchPolicyError(f"{source}.kind is unsupported: `{kind_raw}`.")
    params = item.get("params", {})
    if not isinstance(params, dict):
        raise LaunchPolicyError(f"{source}.params must be a mapping.")
    return LaunchPolicyAction(
        kind=kind_raw,
        params=params,
    )


def _apply_action(
    *,
    action: LaunchPolicyAction,
    request: LaunchPolicyRequest,
    args: list[str],
) -> None:
    """Apply one ordered launch-policy action."""

    if action.kind == "validate.reject_conflicting_launch_args":
        if request.application_kind != "provider_start":
            return
        _validate_owned_args(params=action.params, args=args)
        return
    if action.kind == "cli_arg.ensure_present":
        arg = _require_non_blank_str(action.params, "arg", source=action.kind)
        if arg not in args:
            args.append(arg)
        return
    if action.kind == "cli_arg.ensure_absent":
        arg = _require_non_blank_str(action.params, "arg", source=action.kind)
        while arg in args:
            args.remove(arg)
        return
    if action.kind == "json.set":
        if request.application_kind != "provider_start":
            return
        path = request.home_path / _require_non_blank_str(action.params, "path", source=action.kind)
        key_path = _parse_key_path(action.params, source=action.kind)
        set_json_key(
            path=path,
            key_path=key_path,
            value=action.params.get("value"),
            repair_invalid=True,
        )
        return
    if action.kind == "toml.set":
        if request.application_kind != "provider_start":
            return
        path = request.home_path / _require_non_blank_str(action.params, "path", source=action.kind)
        key_path = _parse_key_path(action.params, source=action.kind)
        value = action.params.get("value")
        if not isinstance(value, (str, bool, int)):
            raise LaunchPolicyError(
                f"{action.kind}.params.value must be a string, boolean, or integer."
            )
        set_toml_key(
            path=path,
            key_path=key_path,
            value=value,
            repair_invalid=True,
        )
        return
    if action.kind == "provider_hook.call":
        hook_id = _require_non_blank_str(action.params, "hook_id", source=action.kind)
        if (
            request.application_kind != "provider_start"
            and hook_id not in _RESUME_CONTROL_ALLOWED_PROVIDER_HOOKS
        ):
            return
        run_provider_hook(hook_id=hook_id, request=request, args=args)
        return
    raise LaunchPolicyError(f"Unsupported launch-policy action kind `{action.kind}`.")


def _validate_owned_args(*, params: Mapping[str, Any], args: list[str]) -> None:
    """Reject conflicting caller args for one strategy-owned arg set."""

    owned_args_payload = params.get("owned_args", [])
    disallowed_args_payload = params.get("disallowed_args", [])
    if not isinstance(owned_args_payload, list) or not all(
        isinstance(item, str) for item in owned_args_payload
    ):
        raise LaunchPolicyError(
            "validate.reject_conflicting_launch_args.owned_args must be a list."
        )
    if not isinstance(disallowed_args_payload, list) or not all(
        isinstance(item, str) for item in disallowed_args_payload
    ):
        raise LaunchPolicyError(
            "validate.reject_conflicting_launch_args.disallowed_args must be a list."
        )

    disallowed = {item.strip() for item in disallowed_args_payload if item.strip()}
    conflicts = sorted(arg for arg in args if arg in disallowed)
    if conflicts:
        joined = ", ".join(conflicts)
        raise LaunchPolicyError(
            f"Caller launch args conflict with unattended strategy-owned args: {joined}."
        )

    seen: set[str] = set()
    deduped: list[str] = []
    owned_args = {item.strip() for item in owned_args_payload if item.strip()}
    for arg in args:
        if arg in owned_args:
            if arg in seen:
                continue
            seen.add(arg)
        deduped.append(arg)
    args[:] = deduped


def _parse_key_path(payload: Mapping[str, Any], *, source: str) -> tuple[str, ...]:
    """Parse one nested key path list."""

    key_path_payload = payload.get("key_path")
    if not isinstance(key_path_payload, list) or not key_path_payload:
        raise LaunchPolicyError(f"{source}.params.key_path must be a non-empty list.")
    return tuple(
        _require_non_blank_item(value, source=f"{source}.params.key_path")
        for value in key_path_payload
    )


def _require_non_blank_str(payload: Mapping[str, Any], key: str, *, source: str) -> str:
    """Return one required non-blank string."""

    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LaunchPolicyError(f"{source}.{key} must be a non-empty string.")
    return value.strip()


def _require_non_blank_item(value: object, *, source: str) -> str:
    """Return one required non-blank string item."""

    if not isinstance(value, str) or not value.strip():
        raise LaunchPolicyError(f"{source} items must be non-empty strings.")
    return value.strip()
