"""Shared resolution helpers for Houmao-owned filesystem roots.

This module centralizes the precedence rules for Houmao-managed directories:
explicit override first, environment override second, and built-in defaults
last.

Functions
---------
resolve_houmao_home_root
    Return the shared ``~/.houmao`` anchor.
resolve_registry_root
    Resolve the effective shared-registry root.
resolve_runtime_root
    Resolve the effective durable runtime root.
resolve_mailbox_root
    Resolve the effective shared mailbox root.
resolve_local_jobs_root
    Resolve the per-session job-root base directory.
resolve_session_job_dir
    Resolve the concrete per-session job directory.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

import platformdirs

AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR = "AGENTSYS_GLOBAL_REGISTRY_DIR"
AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR = "AGENTSYS_GLOBAL_RUNTIME_DIR"
AGENTSYS_GLOBAL_MAILBOX_DIR_ENV_VAR = "AGENTSYS_GLOBAL_MAILBOX_DIR"
AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR = "AGENTSYS_LOCAL_JOBS_DIR"
AGENTSYS_JOB_DIR_ENV_VAR = "AGENTSYS_JOB_DIR"

_HOU_MAO_DIRNAME = ".houmao"


def resolve_houmao_home_root() -> Path:
    """Return the shared ``~/.houmao`` anchor directory."""

    return (_resolve_home_anchor_from_platformdirs() / _HOU_MAO_DIRNAME).resolve()


def resolve_registry_root(
    *,
    explicit_root: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    base: Path | None = None,
) -> Path:
    """Resolve the effective shared-registry root."""

    return _resolve_root(
        explicit_root=explicit_root,
        env=env,
        env_var_name=AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR,
        default_root=resolve_houmao_home_root() / "registry",
        base=base,
    )


def resolve_runtime_root(
    *,
    explicit_root: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    base: Path | None = None,
) -> Path:
    """Resolve the effective durable runtime root."""

    return _resolve_root(
        explicit_root=explicit_root,
        env=env,
        env_var_name=AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR,
        default_root=resolve_houmao_home_root() / "runtime",
        base=base,
    )


def resolve_mailbox_root(
    *,
    explicit_root: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    base: Path | None = None,
) -> Path:
    """Resolve the effective shared mailbox root."""

    return _resolve_root(
        explicit_root=explicit_root,
        env=env,
        env_var_name=AGENTSYS_GLOBAL_MAILBOX_DIR_ENV_VAR,
        default_root=resolve_houmao_home_root() / "mailbox",
        base=base,
    )


def resolve_local_jobs_root(
    *,
    working_directory: Path,
    explicit_root: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    base: Path | None = None,
) -> Path:
    """Resolve the effective local jobs-root base directory."""

    return _resolve_root(
        explicit_root=explicit_root,
        env=env,
        env_var_name=AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR,
        default_root=working_directory.resolve() / _HOU_MAO_DIRNAME / "jobs",
        base=base,
    )


def resolve_session_job_dir(
    *,
    session_id: str,
    working_directory: Path,
    explicit_jobs_root: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    base: Path | None = None,
) -> Path:
    """Resolve the concrete per-session job directory."""

    return (
        resolve_local_jobs_root(
            working_directory=working_directory,
            explicit_root=explicit_jobs_root,
            env=env,
            base=base,
        )
        / session_id
    ).resolve()


def _resolve_root(
    *,
    explicit_root: str | Path | None,
    env: Mapping[str, str] | None,
    env_var_name: str,
    default_root: Path,
    base: Path | None,
) -> Path:
    """Apply explicit, environment, then default root precedence."""

    resolved_explicit = _resolve_optional_path(explicit_root, base=base)
    if resolved_explicit is not None:
        return resolved_explicit

    env_mapping = dict(os.environ) if env is None else dict(env)
    raw_env_override = env_mapping.get(env_var_name)
    if raw_env_override is not None and raw_env_override.strip():
        env_path = Path(raw_env_override).expanduser()
        if not env_path.is_absolute():
            raise ValueError(f"`{env_var_name}` must be an absolute path.")
        return env_path.resolve()

    return default_root.resolve()


def _resolve_optional_path(value: str | Path | None, *, base: Path | None) -> Path | None:
    """Resolve one optional explicit path override."""

    if value is None:
        return None

    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()

    anchor = (base or Path.cwd()).resolve()
    return (anchor / path).resolve()


def _resolve_home_anchor_from_platformdirs() -> Path:
    """Infer the current user's home anchor from a platformdirs-managed path."""

    user_data_path = Path(platformdirs.user_data_path(appname="houmao", appauthor=False))
    parts = user_data_path.parts

    if "AppData" in parts:
        index = parts.index("AppData")
        return Path(*parts[:index]).resolve()

    if "Library" in parts:
        index = parts.index("Library")
        return Path(*parts[:index]).resolve()

    if ".local" in parts:
        index = parts.index(".local")
        return Path(*parts[:index]).resolve()

    return Path.home().expanduser().resolve()
