"""CLI entrypoints for raw launch-helper policy application."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import cast

from houmao.agents.launch_overrides.native import split_permission_args
from houmao.agents.launch_policy.engine import apply_launch_policy
from houmao.agents.launch_policy.models import (
    LaunchPolicyError,
    LaunchPolicyRequest,
    LaunchSurface,
    OperatorPromptMode,
)
from houmao.agents.tool_params import merge_partial_tool_params


def main(argv: list[str] | None = None) -> int:
    """Run the launch-policy helper CLI."""

    parser = argparse.ArgumentParser(description="Apply Houmao launch policy and exec the tool.")
    parser.add_argument("--tool", required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--executable", required=True)
    parser.add_argument("--working-directory", required=True)
    parser.add_argument("--home-path", required=True)
    parser.add_argument("--requested-operator-prompt-mode", default=None)
    parser.add_argument("--dsh-credential-env-file", type=Path)
    parser.add_argument("--kimi-credential-env-file", type=Path)
    parser.add_argument("--kimi-credential-env-name", action="append", default=[])
    parser.add_argument("--hermes-credential-env-file", type=Path)
    parser.add_argument("--hermes-env-name", action="append", default=[])
    parser.add_argument("--permission-params", type=json.loads, default={})
    parser.add_argument(
        "--launch-arg",
        dest="launch_args",
        action="append",
        default=[],
        help="Base launch arg from the manifest/builder (repeatable).",
    )
    parser.add_argument("passthrough", nargs=argparse.REMAINDER)
    namespace = parser.parse_args(argv)

    passthrough = list(namespace.passthrough)
    if passthrough[:1] == ["--"]:
        passthrough = passthrough[1:]

    backend = _parse_backend(str(namespace.backend))
    requested_operator_prompt_mode = _parse_operator_prompt_mode(
        str(namespace.requested_operator_prompt_mode)
        if namespace.requested_operator_prompt_mode is not None
        else None
    )

    home = Path(namespace.home_path).resolve()
    environment = dict(os.environ)
    if namespace.hermes_credential_env_file is not None:
        if namespace.tool != "hermes":
            parser.error("The Hermes credential source can only be used with Hermes.")
        _exec_hermes(
            home=home,
            workspace=Path(namespace.working_directory),
            env_file=namespace.hermes_credential_env_file,
            env_names=namespace.hermes_env_name,
            args=[*namespace.launch_args, *passthrough],
            operator_prompt_mode=requested_operator_prompt_mode or "unattended",
        )
    if namespace.dsh_credential_env_file is not None:
        if namespace.tool != "dsh":
            parser.error("The DSH credential source can only be used with DSH.")
        environment = _dsh_launch_environment(home, namespace.dsh_credential_env_file, environment)
    if namespace.kimi_credential_env_file is not None:
        if namespace.tool != "kimi":
            parser.error("The Kimi credential source can only be used with Kimi.")
        environment = _kimi_launch_environment(
            home,
            namespace.kimi_credential_env_file,
            namespace.kimi_credential_env_name,
            environment,
        )
    tool = str(namespace.tool)
    permission_params = namespace.permission_params
    permission_sources: dict[str, str] = {}
    try:
        if requested_operator_prompt_mode != "as_is":
            remaining, late_permissions = split_permission_args(
                tool,
                tuple(passthrough),
                source="trailing launch args",
                backend=backend,
                unattended=True,
            )
            passthrough = list(remaining)
            if tool == "dsh":
                for argument in passthrough:
                    option = argument.partition("=")[0]
                    if option == "--":
                        break
                    if option in {"--profile", "--patch"}:
                        parser.error(
                            f"Unattended DSH launch owns the native {option} selection. "
                            "Select `as_is` to use a custom native launch profile or overlay."
                        )
            if late_permissions:
                permission_params = merge_partial_tool_params(
                    tool,
                    (
                        ("generated launch helper", permission_params),
                        ("trailing launch args", late_permissions),
                    ),
                )
                for field, value in late_permissions.items():
                    if isinstance(value, dict):
                        permission_sources.update(
                            {f"{field}.{key}": "trailing launch args" for key in value}
                        )
                    else:
                        permission_sources[field] = "trailing launch args"
        result = apply_launch_policy(
            LaunchPolicyRequest(
                tool=tool,
                backend=backend,
                executable=str(namespace.executable),
                base_args=tuple(str(item) for item in namespace.launch_args),
                requested_operator_prompt_mode=requested_operator_prompt_mode,
                working_directory=Path(str(namespace.working_directory)).resolve(),
                home_path=home,
                env=environment,
                tool_params=permission_params,
                tool_param_sources=permission_sources,
            )
        )
    except (LaunchPolicyError, ValueError) as exc:
        parser.error(str(exc))
    if namespace.dsh_credential_env_file is not None:
        from houmao.agents.dsh_configuration import project_dsh_home_permissions
        from houmao.agents.tool_params.dsh import DshPermissionParams

        project_dsh_home_permissions(
            home / "houmao-profile.patch.json",
            DshPermissionParams.model_validate(result.permissions.get("permissions", {})),
        )
    command = [result.executable, *result.args, *passthrough]
    os.execvpe(result.executable, command, environment)
    return 0


def _exec_hermes(
    *,
    home: Path,
    workspace: Path,
    env_file: Path,
    env_names: list[str],
    args: list[str],
    operator_prompt_mode: OperatorPromptMode,
) -> None:
    """Launch the selected native tool using only the explicit credential source."""

    from houmao.agents.hermes_configuration import (
        HERMES_API_KEY_ENV,
        hermes_runtime_environment,
        project_hermes_approval_policy,
        resolve_hermes_executable,
    )
    from houmao.agents.launch_env import owner_launch_baseline
    from houmao.agents.realm_controller.errors import LaunchPlanError
    from houmao.agents.realm_controller.loaders import parse_env_file

    try:
        credentials = parse_env_file(env_file)
        environment = owner_launch_baseline(os.environ)
        environment.update({name: os.environ[name] for name in env_names if name in os.environ})
        environment.pop(HERMES_API_KEY_ENV, None)
        if HERMES_API_KEY_ENV in credentials:
            environment[HERMES_API_KEY_ENV] = credentials[HERMES_API_KEY_ENV]
        native_environment = hermes_runtime_environment(home, environment)
        executable = resolve_hermes_executable(
            environment=native_environment, working_directory=workspace
        )
        project_hermes_approval_policy(home, operator_prompt_mode)
        if operator_prompt_mode == "unattended" and ("--tui" in args or "tui" in args[:1]):
            native_environment["HERMES_NONINTERACTIVE"] = "1"
        os.execve(executable, [executable, *args], native_environment)
    except (OSError, LaunchPlanError, ValueError) as exc:
        raise SystemExit(str(exc)) from None


def _dsh_launch_environment(
    home: Path, env_file: Path, process_environment: dict[str, str]
) -> dict[str, str]:
    """Read the selected provider binding privately when the generated helper runs."""

    from houmao.agents.dsh_configuration import (
        MATERIALIZED_DSH_TOOL_PARAMS,
        DshEffectiveToolParams,
        dsh_native_environment,
    )
    from houmao.agents.dsh_credentials import require_dsh_credential_roles
    from houmao.agents.realm_controller.errors import LaunchPlanError
    from houmao.agents.realm_controller.loaders import parse_allowlisted_env

    try:
        setup = DshEffectiveToolParams.from_file(home / MATERIALIZED_DSH_TOOL_PARAMS)
        require_dsh_credential_roles(
            env_file, base_url_env=setup.base_url_env, api_key_env=setup.api_key_env
        )
        names = [name for name in (setup.base_url_env, setup.api_key_env) if name is not None]
        selected, _ = parse_allowlisted_env(env_file, names)
        environment = {key: value for key, value in process_environment.items() if key not in names}
        return dsh_native_environment(home, setup, {**environment, **selected})
    except (OSError, LaunchPlanError, ValueError) as exc:
        raise SystemExit(str(exc)) from None


def _kimi_launch_environment(
    home: Path, env_file: Path, names: list[str], process_environment: dict[str, str]
) -> dict[str, str]:
    """Load Kimi private inputs at exec and mask inherited native setting names."""

    from houmao.agents.kimi_configuration import (
        KIMI_CONFIG_FILENAME,
        load_kimi_config,
        validate_kimi_config_credentials,
    )
    from houmao.agents.kimi_launch_env import (
        KIMI_API_KEY_ENV,
        KIMI_CONFIG_ENV_NAMES,
        KIMI_PRIVATE_ENV_NAMES,
        reject_kimi_config_env,
    )
    from houmao.agents.realm_controller.errors import LaunchPlanError
    from houmao.agents.realm_controller.loaders import parse_env_file

    try:
        parsed = parse_env_file(env_file)
        reject_kimi_config_env(parsed, source="Kimi credential bundle")
        references = validate_kimi_config_credentials(
            load_kimi_config(home / KIMI_CONFIG_FILENAME), parsed, names
        )
        masked = KIMI_CONFIG_ENV_NAMES | KIMI_PRIVATE_ENV_NAMES | set(names)
        selected = {key: parsed[key] for key in names if key in parsed}
        if KIMI_API_KEY_ENV not in references:
            selected.pop(KIMI_API_KEY_ENV, None)
        return {
            **{key: value for key, value in process_environment.items() if key not in masked},
            **selected,
        }
    except (OSError, LaunchPlanError, ValueError) as exc:
        raise SystemExit(str(exc)) from None


def _parse_backend(raw_value: str) -> LaunchSurface:
    """Parse one required launch backend string."""

    value = raw_value.strip()
    if value not in {
        "raw_launch",
        "codex_headless",
        "codex_app_server",
        "claude_headless",
        "kimi_headless",
        "kimi_acp",
        "dsh_headless",
        "dsh_acp",
        "dsh_web",
        "hermes_tui",
        "hermes_service",
        "hermes_headless",
        "kimi_web",
        "cao_rest",
    }:
        raise SystemExit(f"Unsupported --backend value: {raw_value!r}")
    return cast(LaunchSurface, value)


def _parse_operator_prompt_mode(raw_value: str | None) -> OperatorPromptMode | None:
    """Parse one optional operator prompt mode CLI value."""

    if raw_value is None:
        return None
    value = raw_value.strip()
    if value not in {"as_is", "unattended"}:
        raise SystemExit(
            "--requested-operator-prompt-mode must be `as_is` or `unattended` when set."
        )
    return cast(OperatorPromptMode, value)


if __name__ == "__main__":
    raise SystemExit(main())
