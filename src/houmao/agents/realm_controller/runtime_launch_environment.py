"""Keep one prepared runtime's launch environment in private local storage."""

from __future__ import annotations

import os
import re
import stat
from collections.abc import Mapping
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from houmao.agents.realm_controller.errors import SessionManifestError


class RuntimeLaunchEnvironment(BaseModel):
    """Private environment for reopening a live runtime generation."""

    model_config = ConfigDict(extra="forbid", strict=True)

    environment: dict[str, str] = Field(repr=False)
    transient_names: list[str]
    mcp_environment: dict[str, str] = Field(default_factory=dict, repr=False)


def is_runtime_launch_environment_file(name: str) -> bool:
    """Identify generated runtime environment filenames without allowing path components."""

    return re.fullmatch(r"launch-environment-[a-f0-9]{32}\.json", name) is not None


def write_runtime_launch_environment(
    session_root: Path,
    *,
    environment: dict[str, str],
    transient_names: frozenset[str],
    mcp_environment: Mapping[str, str],
) -> str:
    """Store selected values in an owner-private file before publishing its name."""

    name = f"launch-environment-{uuid4().hex}.json"
    path = session_root / name
    payload = RuntimeLaunchEnvironment(
        environment=environment,
        transient_names=sorted(transient_names),
        mcp_environment=dict(mcp_environment),
    )
    session_root.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(payload.model_dump_json())
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        path.unlink(missing_ok=True)
        raise
    return name


def read_runtime_launch_environment(path: Path) -> RuntimeLaunchEnvironment:
    """Read one owner-private environment without following a file symlink."""

    if not is_runtime_launch_environment_file(path.name):
        raise SessionManifestError("Invalid runtime launch environment locator")
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_mode & 0o077
                or info.st_nlink != 1
            ):
                raise SessionManifestError("Runtime launch environment must be owner-private")
            return RuntimeLaunchEnvironment.model_validate_json(stream.read())
    except (OSError, ValidationError):
        raise SessionManifestError("Runtime launch environment is missing or malformed") from None
