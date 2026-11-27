"""Persist the owner identity and paths of a managed Hermes named profile."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from houmao.execution.models import validate_absolute_path

HERMES_PROFILE_RECORD = ".houmao-profile.json"
HERMES_STANDALONE_RELAUNCH_REFUSAL = (
    "The recorded Hermes worker uses a standalone home. Stop it and create a fresh project "
    "launch for a named profile. Its saved conversation cannot continue across layouts."
)
HERMES_PROFILE_PARKED = "gateway.parked"


def require_hermes_installation_context(
    root: Path, context_id: str, *, claim: bool = False
) -> None:
    """Keep a prepared installation dedicated to one verified execution context."""

    path = root / ".houmao-owner-context"
    expected = f"{context_id}\n".encode()
    if not os.path.lexists(path):
        if not claim:
            return
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(expected)
        return
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.geteuid()
            or info.st_mode & 0o077
            or stream.read(len(expected) + 1) != expected
        ):
            raise ValueError(
                "The prepared Hermes installation belongs to another execution context."
            )


class HermesProfileBinding(BaseModel):
    """Describe one prepared installation, canonical profile, and project-local home link."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    prepared_root: Path
    profile_home: Path
    profile_name: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    context_id: str = Field(min_length=1, max_length=128)
    gateway_lock_dir: Path
    project_home_link: Path
    installation_build: str = Field(pattern=r"^[a-f0-9]{40}$")
    profile_owner_id: str = Field(min_length=1, max_length=128)
    executable: Path
    broker_socket: Path

    @field_validator(
        "prepared_root",
        "profile_home",
        "gateway_lock_dir",
        "project_home_link",
        "executable",
        "broker_socket",
        mode="before",
    )
    @classmethod
    def _parse_absolute_path(cls, value: object, info: ValidationInfo) -> str | Path:
        """Restore absolute paths without consulting a different execution owner's filesystem."""

        if not isinstance(value, (str, Path)):
            raise ValueError("Hermes profile paths must be absolute strings")
        path = validate_absolute_path(str(value))
        return path if info.mode == "json" else Path(path)

    @model_validator(mode="after")
    def _require_owned_layout(self) -> HermesProfileBinding:
        """Keep the canonical native profile separate from its project-local entry."""

        if (
            self.profile_name == "default"
            or self.profile_home != self.prepared_root / "profiles" / self.profile_name
            or self.gateway_lock_dir != self.prepared_root / "gateway-locks"
            or not self.executable.is_relative_to(self.prepared_root)
            or self.project_home_link.is_relative_to(self.prepared_root)
        ):
            raise ValueError("The Hermes binding differs from the managed named-profile layout")
        return self


def require_hermes_profile_home(
    binding: HermesProfileBinding, *, allow_missing_link: bool = False
) -> None:
    """Verify the canonical private home, ownership record, and exact project entry."""

    require_hermes_profile_owner(binding)
    home = binding.profile_home
    link = binding.project_home_link
    if link.parent.resolve() != link.parent:
        raise ValueError("The project entry differs from the recorded managed Hermes profile.")
    if allow_missing_link and not os.path.lexists(link):
        return
    if not link.is_symlink() or Path(os.readlink(link)) != home:
        raise ValueError("The project entry differs from the recorded managed Hermes profile.")


def require_hermes_profile_owner(binding: HermesProfileBinding) -> None:
    """Pin the canonical private home to its exact builder-owned binding."""

    home = binding.profile_home
    if home.resolve() != home:
        raise ValueError("The canonical managed Hermes profile path has changed.")
    home_info = home.lstat()
    if (
        not stat.S_ISDIR(home_info.st_mode)
        or home_info.st_uid != os.geteuid()
        or home_info.st_mode & 0o077
    ):
        raise ValueError("The managed Hermes profile home is not private to its owner.")
    record = read_hermes_profile_record(home)
    if record != binding:
        raise ValueError("The managed Hermes profile ownership record has changed.")


def read_hermes_profile_record(home: Path) -> HermesProfileBinding:
    """Read the private, bounded ownership record from an exact canonical home."""

    descriptor = os.open(home / HERMES_PROFILE_RECORD, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.geteuid()
            or info.st_mode & 0o077
            or info.st_size > 16_384
        ):
            raise ValueError("The managed Hermes profile ownership record is invalid.")
        return HermesProfileBinding.model_validate_json(stream.read(16_385))


def write_hermes_profile_record(home: Path, binding: HermesProfileBinding) -> None:
    """Place the exact binding into a private unpublished profile directory."""

    descriptor = os.open(
        home / HERMES_PROFILE_RECORD,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW | os.O_NONBLOCK,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(binding.model_dump(mode="json"), stream)
        stream.write("\n")
