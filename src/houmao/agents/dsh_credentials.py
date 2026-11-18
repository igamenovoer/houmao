"""Shared declarations for the environment roles in a DSH credential bundle."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml

from houmao.owned_mutation import replace_path_with_text

DSH_CREDENTIAL_ROLES_FILENAME = "credential-roles.yaml"

_RESERVED_ENV_NAMES = frozenset(
    {
        "BASH_ENV",
        "DSH_AGENTS_HOME",
        "DSH_BUNDLED_SKILL_DIR",
        "DSH_HOME",
        "DSH_PERMISSION_MODE",
        "ENV",
        "HOME",
        "NODE_OPTIONS",
        "PATH",
        "PYTHONHOME",
        "PYTHONPATH",
        "SHELL",
        "TMUX",
        "TMUX_PANE",
        "TMUX_TMPDIR",
    }
)
_RESERVED_PREFIXES = ("DYLD_", "HOUMAO_", "LD_", "XDG_")


def validate_dsh_env_name(name: str) -> str:
    """Require a POSIX environment name outside reserved process settings."""

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError("must be a POSIX environment variable name")
    if name in _RESERVED_ENV_NAMES or name.startswith(_RESERVED_PREFIXES):
        raise ValueError("cannot replace native isolation or process settings")
    return name


@dataclass(frozen=True)
class DshCredentialRoles:
    """Name the environment variables bound to the endpoint and API-key roles."""

    base_url_env: str | None = None
    api_key_env: str | None = None

    def __post_init__(self) -> None:
        """Validate the role names and their distinctness."""

        for name in (self.base_url_env, self.api_key_env):
            if name is not None:
                validate_dsh_env_name(name)
        if self.base_url_env is not None and self.base_url_env == self.api_key_env:
            raise ValueError("DSH endpoint and API key require distinct environment names")

    def to_payload(self) -> dict[str, str]:
        """Return the public names of declared roles."""

        return {
            role: name
            for role, name in {
                "base_url_env": self.base_url_env,
                "api_key_env": self.api_key_env,
            }.items()
            if name is not None
        }


def load_dsh_credential_roles(env_file: Path) -> DshCredentialRoles | None:
    """Read role names alongside the selected bundle's lexical environment file."""

    path = env_file.with_name(DSH_CREDENTIAL_ROLES_FILENAME)
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, yaml.YAMLError, RecursionError):
        raise ValueError(f"Cannot read DSH credential roles from {path}") from None
    if (
        not isinstance(payload, dict)
        or set(payload) - {"base_url_env", "api_key_env"}
        or any(not isinstance(name, str) for name in payload.values())
    ):
        raise ValueError(f"Invalid DSH credential roles in {path}")
    try:
        return DshCredentialRoles(
            base_url_env=payload.get("base_url_env"), api_key_env=payload.get("api_key_env")
        )
    except ValueError as exc:
        raise ValueError(f"Invalid DSH credential roles in {path}: {exc}") from None


def require_dsh_credential_roles(
    env_file: Path, *, base_url_env: str, api_key_env: str | None
) -> None:
    """Match the effective provider references to the selected bundle roles."""

    roles = load_dsh_credential_roles(env_file)
    if roles is None:
        raise ValueError(
            "DSH credential role metadata is missing. Set the bundle roles with credentials dsh set."
        )
    if roles.base_url_env != base_url_env:
        raise ValueError("DSH provider.base_url_env must match the selected bundle's endpoint role")
    if roles.api_key_env != api_key_env:
        raise ValueError("DSH provider.api_key_env must match the selected bundle's API-key role")


def write_dsh_credential_roles(env_file: Path, roles: DshCredentialRoles) -> None:
    """Write the role names beside the bundle environment without storing values."""

    path = env_file.with_name(DSH_CREDENTIAL_ROLES_FILENAME)
    replace_path_with_text(
        destination=path,
        text=yaml.safe_dump(roles.to_payload(), sort_keys=False),
        allowed_roots=(path.parent,),
    )
    path.chmod(0o600)
