"""Shared Codex home bootstrap helpers for non-interactive launches."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from houmao.agents.launch_policy.models import LaunchPolicyError
from houmao.agents.launch_policy.provider_hooks import (
    ensure_codex_unattended_runtime_state,
    validate_codex_credential_readiness,
)

from ..errors import BackendExecutionError


def ensure_codex_home_bootstrap(
    *,
    home_path: Path,
    env: Mapping[str, str],
    working_directory: Path,
) -> None:
    """Ensure Codex runtime-home bootstrap invariants before launch.

    Parameters
    ----------
    home_path:
        Runtime Codex home path (`CODEX_HOME`).
    env:
        Effective launch environment values used to validate auth readiness.
    working_directory:
        Launch working directory used to resolve the trust target.
    """

    home_path.mkdir(parents=True, exist_ok=True)
    try:
        validate_codex_credential_readiness(
            home_path=home_path,
            env=env,
            error_factory=BackendExecutionError,
        )
        ensure_codex_unattended_runtime_state(
            home_path=home_path,
            working_directory=working_directory,
        )
    except LaunchPolicyError as exc:
        raise BackendExecutionError(str(exc)) from exc
