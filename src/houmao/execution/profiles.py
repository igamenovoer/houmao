"""Load trusted operator execution configuration without consulting agent projects."""

from __future__ import annotations

import os
from pathlib import Path
import stat

from pydantic import ValidationError
import yaml

from houmao.execution.models import ExecutionProfileV1, validate_selector
from houmao.owned_paths import resolve_houmao_home_root

MAX_PROFILE_BYTES = 65_536


class ExecutionProfileError(ValueError):
    """Represent invalid, missing, or untrusted execution configuration safely."""


def execution_profiles_root() -> Path:
    """Return the operator-owned execution-profile collection without creating it."""

    return resolve_houmao_home_root() / "executors"


def load_execution_profile(name: str, *, root: Path | None = None) -> ExecutionProfileV1:
    """Read one trusted named profile from the explicit operator configuration root.

    Parameters
    ----------
    name : str
        Filesystem-safe profile name, never a path or project selector.
    root : Path or None
        Explicit configuration collection for controlled embedding and tests.

    Returns
    -------
    ExecutionProfileV1
        Validated profile, with authentication references kept only in memory.
    """

    validate_selector(name)
    directory = root if root is not None else execution_profiles_root()
    path = directory / f"{name}.yaml"
    try:
        _check_trust(directory, directory=True)
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as source:
            metadata = os.fstat(source.fileno())
            _check_metadata(metadata, directory=False)
            payload = source.read(MAX_PROFILE_BYTES + 1)
        if len(payload) > MAX_PROFILE_BYTES:
            raise ExecutionProfileError("Execution profile exceeds its size limit")
        data: object = yaml.safe_load(payload)
        if not isinstance(data, dict):
            raise ExecutionProfileError("Execution profile must be a YAML object")
        profile = ExecutionProfileV1.model_validate(data)
        if profile.name != name:
            raise ExecutionProfileError("Execution profile name does not match its selector")
        return profile
    except ExecutionProfileError:
        raise
    except (OSError, ValueError, yaml.YAMLError, ValidationError):
        raise ExecutionProfileError(
            f"Execution profile {name!r} is unavailable or invalid"
        ) from None


def _check_trust(path: Path, *, directory: bool) -> None:
    """Reject symlinked or writable-by-others profile collections."""

    _check_metadata(path.lstat(), directory=directory)


def _check_metadata(metadata: os.stat_result, *, directory: bool) -> None:
    """Require regular operator/root-owned configuration with restrictive write access."""

    expected_kind = stat.S_ISDIR if directory else stat.S_ISREG
    if (
        not expected_kind(metadata.st_mode)
        or metadata.st_uid not in {0, os.geteuid()}
        or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        raise ExecutionProfileError(
            "Execution configuration must be trusted and not writable by others"
        )
