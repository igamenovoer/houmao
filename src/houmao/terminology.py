"""Shared Houmao terminology and root-selection constants."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping, Literal

NATIVE_AGENT_ROOT_ENV_VAR = "HOUMAO_NATIVE_AGENT_ROOT"
LEGACY_AGENT_DEF_DIR_ENV_VAR = "HOUMAO_AGENT_DEF_DIR"

PROJECT_SPECIALIST_TERM = "specialist"
PROJECT_PROFILE_TERM = "profile"
PROJECT_MANAGED_AGENT_TERM = "managed agent"
NATIVE_AGENT_TERM = "native agent"
NATIVE_AGENT_ROOT_TERM = "native-agent root"
LAUNCH_DOSSIER_TERM = "launch dossier"

NativeAgentRootSource = Literal["cli", "env", "legacy_env"]


@dataclass(frozen=True)
class NativeAgentRootResolution:
    """Resolved native-agent root plus operator-facing diagnostics."""

    root: Path
    source: NativeAgentRootSource
    diagnostics: tuple[str, ...] = ()


def resolve_native_agent_root(
    *,
    cli_value: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    base: Path | None = None,
) -> NativeAgentRootResolution:
    """Resolve the native-agent root for direct internal native-agent commands."""

    anchor = (base or Path.cwd()).resolve()
    if cli_value is not None:
        return NativeAgentRootResolution(
            root=_resolve_cli_path(cli_value, base=anchor),
            source="cli",
        )

    env_mapping = dict(os.environ) if env is None else dict(env)
    native_value = env_mapping.get(NATIVE_AGENT_ROOT_ENV_VAR)
    if native_value is not None and native_value.strip():
        return NativeAgentRootResolution(
            root=_resolve_absolute_env_path(
                native_value.strip(),
                env_var_name=NATIVE_AGENT_ROOT_ENV_VAR,
            ),
            source="env",
        )

    legacy_value = env_mapping.get(LEGACY_AGENT_DEF_DIR_ENV_VAR)
    if legacy_value is not None and legacy_value.strip():
        return NativeAgentRootResolution(
            root=_resolve_absolute_env_path(
                legacy_value.strip(),
                env_var_name=LEGACY_AGENT_DEF_DIR_ENV_VAR,
            ),
            source="legacy_env",
            diagnostics=(
                f"`{LEGACY_AGENT_DEF_DIR_ENV_VAR}` is deprecated for native-agent internals; "
                f"set `{NATIVE_AGENT_ROOT_ENV_VAR}` instead.",
            ),
        )

    raise ValueError(
        "Native-agent internals require a selected native-agent root. "
        f"Pass `--native-agent-root` or set `{NATIVE_AGENT_ROOT_ENV_VAR}`."
    )


def _resolve_cli_path(value: str | Path, *, base: Path) -> Path:
    """Resolve one CLI path relative to the invocation base."""

    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (base / path).resolve()


def _resolve_absolute_env_path(value: str, *, env_var_name: str) -> Path:
    """Resolve one absolute env-var path."""

    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError(f"`{env_var_name}` must be an absolute path.")
    return path.resolve()
