"""Read private developer model selections for agent launch fixtures."""

from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path
import re
import shlex
import stat
import tomllib
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from houmao.agents.realm_controller.run_modes import RunMode
from houmao.agents.tool_params.dsh import DshCompat

from fixturelib.auth import bundle_path, validate_external_path
from fixturelib.config import Client, DshProtocol, FixtureError, ModelOptions, REPO_ROOT

_POOL_VARIABLE = "HOUMAO_TEST_MODEL_POOL"
_MODEL_VARIABLE = "HOUMAO_TEST_MODEL"
_POOL_KEY_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_CREDENTIAL_FIELDS = {
    "accesstoken",
    "apikey",
    "apitoken",
    "authorization",
    "authtoken",
    "password",
    "refreshtoken",
}


class ModelPoolEntry(ModelOptions):
    """Bind a client model to explicit routing and external credential references."""

    client: Client
    case: Literal["self-hosted", "cloud-api"] | None = None
    auth_method: Literal["native-login"] | None = None
    auth_bundle: str | None = None
    model: str = Field(min_length=1)
    base_url: str | None = None
    env_file: Path | None = None
    descriptor: Path | None = None
    executable: str | None = None
    dsh_protocol: DshProtocol | None = None
    reasoning_level: int | None = Field(default=None, ge=0)
    supported_modes: list[RunMode] | None = Field(default=None, min_length=1)

    @field_validator("env_file", "descriptor", mode="before")
    @classmethod
    def _parse_path(cls, value: object) -> object:
        """Accept TOML file references as nonempty path strings."""

        if isinstance(value, str):
            if not value.strip() or "\x00" in value:
                raise ValueError("file reference must be a nonempty path")
            return Path(value)
        return value

    @field_validator("model", "executable")
    @classmethod
    def _single_line(cls, value: str | None) -> str | None:
        """Require a single-line identifier or executable path."""

        if value is not None and (not value.strip() or any(c in value for c in "\r\n\x00")):
            raise ValueError("must be a nonempty single-line value")
        return value

    @field_validator("base_url")
    @classmethod
    def _public_base_url(cls, value: str | None) -> str | None:
        """Accept routing URLs without user info, query parameters, or fragments."""

        if value is None:
            return None
        parts = urlsplit(value)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or "?" in value
            or "#" in value
            or any(ord(character) <= 32 or ord(character) == 127 for character in value)
        ):
            raise ValueError("expected an HTTP(S) base URL without credentials or query")
        return value

    @field_validator("dsh_compat")
    @classmethod
    def _public_compat(cls, value: dict[str, object] | None) -> dict[str, object] | None:
        """Validate native compatibility options and reject credential template fields."""

        if value is None:
            return None
        compat = DshCompat.model_validate(value)
        for arguments in (compat.chat_template_args, compat.chat_template_kwargs):
            if arguments and any(
                re.sub(r"[^a-z0-9]", "", name.lower()) in _CREDENTIAL_FIELDS for name in arguments
            ):
                raise ValueError("credential fields belong in the selected external env file")
        return value

    @model_validator(mode="after")
    def _validate_route(self) -> Self:
        """Require exactly one API case or an imported native login bundle."""

        if self.auth_method == "native-login":
            if self.client in {"dsh", "hermes"} or not self.auth_bundle:
                raise ValueError("native login requires a supported client and an auth bundle")
            bundle_path(Path(), self.client, self.auth_bundle)
            if any(
                value is not None
                for value in (self.case, self.base_url, self.env_file, self.descriptor)
            ):
                raise ValueError("native login cannot use API case or endpoint settings")
        else:
            if self.case is None or self.auth_bundle is not None:
                raise ValueError("API entries require a case and cannot use native auth bundles")
            if self.case == "cloud-api" and self.env_file is None:
                raise ValueError("cloud API entries require an external env file")
            if self.base_url is None and self.env_file is None:
                raise ValueError("API entries require a base URL or an external env file")
        if self.supported_modes is not None and len(set(self.supported_modes)) != len(
            self.supported_modes
        ):
            raise ValueError("supported modes must be unique")
        return self


class ModelPool(BaseModel):
    """Versioned model keys a developer can assign to test-agent slots."""

    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: int = Field(ge=1, le=1)
    models: dict[str, ModelPoolEntry] = Field(min_length=1)

    @field_validator("models")
    @classmethod
    def _validate_keys(cls, models: dict[str, ModelPoolEntry]) -> dict[str, ModelPoolEntry]:
        """Restrict public keys to portable identifiers."""

        if any(not _POOL_KEY_PATTERN.fullmatch(key) for key in models):
            raise ValueError("model keys must be portable identifiers")
        return models


def _external_file(path: Path, *, repo_root: Path) -> Path:
    """Check the supplied path and resolved target against the checkout."""

    if Path(os.path.abspath(path)).is_relative_to(repo_root.resolve()):
        raise FixtureError("Model pool and credential env files must be outside the checkout")
    return validate_external_path(path, repo_root=repo_root, allow_checkout_tmp=False)


def _read_pool(path: Path, *, repo_root: Path, user_home: Path) -> dict[str, object]:
    """Parse TOML only after verifying the opened file is regular and owner-private."""

    try:
        if path.is_symlink():
            raise FixtureError("Model pool must be a regular file, not a symlink")
        resolved = _external_file(path, repo_root=repo_root)
        if resolved in {Path("/"), Path("/tmp"), user_home.resolve()}:
            raise FixtureError("Select a model pool file outside shared directory roots")
        descriptor = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise FixtureError("Model pool must be a regular file")
            if info.st_uid != os.getuid():
                raise FixtureError("Model pool must be owned by the current user")
            if info.st_mode & 0o077:
                raise FixtureError(
                    f"Model pool must be owner-private. Run chmod 600 {shlex.quote(str(path))}"
                )
            return tomllib.load(stream)
    except (OSError, RuntimeError):
        raise FixtureError(f"Cannot read model pool file {path}") from None
    except (tomllib.TOMLDecodeError, UnicodeDecodeError):
        raise FixtureError("Invalid model pool TOML; check its syntax") from None


def load_model_pool(
    path: Path | None = None,
    *,
    process_env: Mapping[str, str] | None = None,
    user_home: Path | None = None,
    repo_root: Path = REPO_ROOT,
) -> ModelPool:
    """Load the selected external pool without reading any referenced credentials."""

    env = os.environ if process_env is None else process_env
    home = user_home or Path.home()
    xdg_data = Path(env["XDG_DATA_HOME"]) if env.get("XDG_DATA_HOME") else home / ".local/share"
    configured_path = path or (Path(env[_POOL_VARIABLE]) if env.get(_POOL_VARIABLE) else None)
    selected_path = (
        configured_path or xdg_data / "houmao/test-fixtures/model-pool.toml"
    ).expanduser()
    contents = _read_pool(selected_path, repo_root=repo_root, user_home=home)
    try:
        pool = ModelPool.model_validate(contents)
    except ValidationError:
        raise FixtureError(
            "Invalid model pool schema; check version, model fields, and external credential references"
        ) from None

    parent = selected_path.resolve().parent
    for entry in pool.models.values():
        if entry.env_file is not None:
            entry.env_file = _external_file(
                parent / entry.env_file.expanduser(), repo_root=repo_root
            )
        if entry.descriptor is not None:
            entry.descriptor = parent / entry.descriptor.expanduser()
        if entry.executable is not None and (
            "/" in entry.executable or entry.executable.startswith("~")
        ):
            entry.executable = str(parent / Path(entry.executable).expanduser())
    return pool


def select_pool_key(
    pool: ModelPool,
    *,
    key: str | None = None,
    slot: str | None = None,
    process_env: Mapping[str, str] | None = None,
) -> str:
    """Look up an explicit key or resolve a slot before checking the shared variable."""

    if (key is None) == (slot is None):
        raise FixtureError("Select exactly one of --pool-key and --pool-slot")
    available = ", ".join(sorted(pool.models))
    if slot is not None:
        normalized = re.sub(r"[^A-Za-z0-9]+", "_", slot).strip("_").upper()
        if not normalized:
            raise FixtureError("Pool slot must contain a letter or digit")
        env = os.environ if process_env is None else process_env
        variable = f"{_MODEL_VARIABLE}_{normalized}"
        if variable not in env and _MODEL_VARIABLE not in env:
            raise FixtureError(
                f"Set {variable} or {_MODEL_VARIABLE}. Available model keys: {available}"
            )
        source = variable if variable in env else _MODEL_VARIABLE
        key = env[source]
    else:
        source = "--pool-key"
    if key is None or key not in pool.models:
        raise FixtureError(
            f"Unknown model key selected by {source}. Available model keys: {available}"
        )
    return key
