"""Prepare managed Hermes homes and their private launch environment."""

from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path
import subprocess
import tempfile

import yaml

from houmao.agents.tool_params.hermes import HermesReasoningEffort

HERMES_HOME_ENV = "HERMES_HOME"
HERMES_LOCK_DIR_ENV = "HERMES_GATEWAY_LOCK_DIR"
HERMES_API_KEY_ENV = "HERMES_MANAGED_API_KEY"
HERMES_CONFIG_FILENAME = "config.yaml"
_NATIVE_ENV_PREFIXES = ("HERMES_", "OPENAI_", "OPENROUTER_", "ANTHROPIC_", "DEEPSEEK_")


def resolve_hermes_executable(
    *,
    environment: Mapping[str, str] | None = None,
    working_directory: Path | None = None,
) -> str:
    """Resolve the command from PATH in this execution context."""

    cwd = working_directory or Path.cwd()
    try:
        result = subprocess.run(
            ["/bin/sh", "-c", "command -v hermes"],
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise ValueError(f"Could not look up Hermes in execution context {cwd}: {exc}") from exc
    command = result.stdout.rstrip("\n")
    if result.returncode != 0 or not command:
        raise ValueError(
            f"Hermes was not found on PATH in execution context {cwd}. "
            "Make `command -v hermes` succeed in that execution context."
        )
    return str((cwd / command).absolute())


def selected_hermes_key(environment: Mapping[str, str]) -> str:
    """Read the required API key from the explicitly selected binding."""

    key = environment.get(HERMES_API_KEY_ENV, "")
    if not key.strip() or any(control in key for control in ("\0", "\r", "\n")):
        raise ValueError(f"The selected Hermes credential bundle must set {HERMES_API_KEY_ENV}.")
    return key


def hermes_owned_environment_name(name: str) -> bool:
    """Recognize native provider and runtime environment controls owned by Houmao."""

    return name.startswith(_NATIVE_ENV_PREFIXES)


def hermes_runtime_environment(
    home: Path, selected_environment: Mapping[str, str]
) -> dict[str, str]:
    """Set a private launch home, rendezvous directory, and selected credential."""

    credential = selected_hermes_key(selected_environment)
    home = home.absolute()
    return {
        **{
            name: value
            for name, value in selected_environment.items()
            if not hermes_owned_environment_name(name)
        },
        HERMES_HOME_ENV: str(home),
        HERMES_LOCK_DIR_ENV: str(home / ".houmao-gateway-locks"),
        HERMES_API_KEY_ENV: credential,
    }


def prepare_hermes_home(
    home_path: Path,
    *,
    base_url: str,
    model_name: str,
    role_prompt: str,
    reasoning_effort: HermesReasoningEffort | None = None,
) -> None:
    """Project the custom Chat Completions route, effort, and native role file."""

    agent: dict[str, object] = {"disabled_toolsets": ["browser", "computer_use"]}
    if reasoning_effort is not None:
        agent["reasoning_effort"] = reasoning_effort
    config = {
        "model": {
            "default": model_name,
            "provider": "custom",
            "base_url": base_url,
            "api_mode": "chat_completions",
            "key_env": HERMES_API_KEY_ENV,
        },
        "fallback_providers": [],
        "agent": agent,
        "security": {"allow_lazy_installs": False},
        "approvals": {
            "mode": "manual",
            "single_query_mode": "deny",
            "unattended_mode": "deny",
        },
    }
    _write_private_text(home_path / HERMES_CONFIG_FILENAME, yaml.safe_dump(config, sort_keys=False))
    write_hermes_role(home_path, role_prompt)


def write_hermes_role(home_path: Path, role_prompt: str) -> None:
    """Replace Hermes's native `SOUL.md` with the composed literal role."""

    _write_private_text(home_path / "SOUL.md", role_prompt)


def _write_private_text(path: Path, content: str) -> None:
    """Replace a native input atomically without exposing it to other users."""

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}-", delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
