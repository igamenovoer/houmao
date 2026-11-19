"""CLI entrypoints for raw launch-helper policy application."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import cast

from houmao.agents.launch_policy.engine import apply_launch_policy
from houmao.agents.launch_policy.models import (
    LaunchPolicyRequest,
    LaunchSurface,
    OperatorPromptMode,
)


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
    if namespace.dsh_credential_env_file is not None:
        if namespace.tool != "dsh":
            parser.error("The DSH credential source can only be used with DSH.")
        environment = _dsh_launch_environment(home, namespace.dsh_credential_env_file, environment)
    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool=str(namespace.tool),
            backend=backend,
            executable=str(namespace.executable),
            base_args=tuple(str(item) for item in namespace.launch_args),
            requested_operator_prompt_mode=requested_operator_prompt_mode,
            working_directory=Path(str(namespace.working_directory)).resolve(),
            home_path=home,
            env=environment,
        )
    )
    command = [result.executable, *result.args, *passthrough]
    os.execvpe(result.executable, command, environment)
    return 0


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
