"""Shared operator wording helpers for project-aware maintained CLI commands."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from houmao.owned_paths import (
    HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR,
    HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR,
    HOUMAO_LOCAL_JOBS_DIR_ENV_VAR,
)


def runtime_root_option_help() -> str:
    """Return shared runtime-root option help text."""

    return (
        "Explicit runtime-root override. When omitted, this command uses the active "
        "project runtime root when project context is active. Set "
        f"`{HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR}` to use an explicit shared runtime-root "
        "override instead."
    )


def mailbox_root_option_help() -> str:
    """Return shared mailbox-root option help text."""

    return (
        "Explicit mailbox-root override. When omitted, this command uses the active "
        "project mailbox root when project context is active. Set "
        f"`{HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR}` to use an explicit shared mailbox-root "
        "override instead."
    )


def describe_runtime_root_selection(
    *,
    explicit_root: str | Path | None,
    env: Mapping[str, str] | None = None,
) -> str:
    """Describe how one command selected its runtime root."""

    if explicit_root is not None:
        return "Selected runtime root from the explicit `--runtime-root` override."
    if _has_env_override(HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR, env=env):
        return f"Selected shared runtime root from `{HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR}`."
    return "Selected the active project runtime root from the current project overlay."


def describe_mailbox_root_selection(
    *,
    explicit_root: str | Path | None,
    env: Mapping[str, str] | None = None,
) -> str:
    """Describe how one command selected its mailbox root."""

    if explicit_root is not None:
        return "Selected mailbox root from the explicit `--mailbox-root` override."
    if _has_env_override(HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR, env=env):
        return f"Selected shared mailbox root from `{HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR}`."
    return "Selected the active project mailbox root from the current project overlay."


def describe_local_jobs_root_selection(*, env: Mapping[str, str] | None = None) -> str:
    """Describe how one command selected its jobs root."""

    if _has_env_override(HOUMAO_LOCAL_JOBS_DIR_ENV_VAR, env=env):
        return f"Selected jobs root from `{HOUMAO_LOCAL_JOBS_DIR_ENV_VAR}`."
    return "Selected the overlay-local jobs root for this invocation."


def describe_overlay_bootstrap(*, created_overlay: bool, overlay_exists: bool = True) -> str:
    """Describe whether the selected overlay was bootstrapped implicitly."""

    if created_overlay:
        return "Applied implicit bootstrap for the selected overlay root during this invocation."
    if overlay_exists:
        return "Reused the selected project overlay without implicit bootstrap."
    return "No project overlay was bootstrapped for this invocation."


def describe_overlay_root_selection_source(*, overlay_root_source: str) -> str:
    """Describe how one invocation selected its overlay root."""

    if overlay_root_source == "env":
        return "Selected overlay root from `HOUMAO_PROJECT_OVERLAY_DIR`."
    if overlay_root_source == "discovered":
        return "Selected overlay root from nearest-ancestor project discovery."
    return "Selected overlay root from the default project-aware `<cwd>/.houmao` candidate."


def _has_env_override(env_var_name: str, *, env: Mapping[str, str] | None) -> bool:
    """Return whether one env-backed override is active."""

    env_mapping = dict(os.environ) if env is None else dict(env)
    raw_value = env_mapping.get(env_var_name)
    return raw_value is not None and bool(raw_value.strip())
