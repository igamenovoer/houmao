"""Bounded local auth discovery and private, copy-only credential import."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import tomllib
from typing import Iterator, Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field

from fixturelib.config import Client, FixtureError, HOME_VARIABLE, REPO_ROOT, ResolvedConfig

_AUTH_NAMES = {"claude": ".credentials.json", "codex": "auth.json", "kimi": "kimi-code.json"}
_SKIP_DIRS = {".git", "node_modules", "sessions", "history", "logs", ".cache", "__pycache__"}


class AuthCandidate(BaseModel):
    """Safe discovery metadata with internal allowlisted source file references."""

    model_config = ConfigDict(extra="forbid", strict=True)
    candidate_id: str
    client: Client
    source: Path
    kind: str
    importable: bool
    reason: str | None = None
    files: dict[str, Path] = Field(default_factory=dict, exclude=True)

    def summary(self) -> dict[str, object]:
        """Report candidate metadata without reading or returning secret contents."""

        return {
            **self.model_dump(mode="json", exclude={"files"}),
            "supported_files": sorted(self.files),
        }


def external_root(
    kind: Literal["auth", "run"],
    *,
    override: Path | None = None,
    process_env: Mapping[str, str] | None = None,
    user_home: Path | None = None,
    repo_root: Path = REPO_ROOT,
    create: bool = False,
) -> Path:
    """Resolve an external private root or a purpose-specific checkout tmp run root."""

    env = os.environ if process_env is None else process_env
    home = user_home or Path.home()
    variable = "HOUMAO_TEST_AUTH_ROOT" if kind == "auth" else "HOUMAO_TEST_RUN_ROOT"
    xdg_variable = "XDG_DATA_HOME" if kind == "auth" else "XDG_STATE_HOME"
    suffix = "share" if kind == "auth" else "state"
    base = Path(env[xdg_variable]) if env.get(xdg_variable) else home / ".local" / suffix
    path = override or (Path(env[variable]) if env.get(variable) else None)
    resolved = (
        (path or base / "houmao/test-fixtures" / ("auth" if kind == "auth" else "runs"))
        .expanduser()
        .resolve()
    )
    validate_external_path(resolved, repo_root=repo_root, allow_checkout_tmp=kind == "run")
    if resolved in {Path("/"), Path("/tmp"), home.resolve()}:
        raise FixtureError("Select a purpose-specific external directory")
    if create:
        private_directory(resolved)
    return resolved


def validate_external_path(
    path: Path, *, repo_root: Path = REPO_ROOT, allow_checkout_tmp: bool = False
) -> Path:
    """Reject checkout state except for purpose-specific tmp run subdirectories."""

    resolved = path.expanduser().resolve()
    checkout = repo_root.resolve()
    scratch = checkout / "tmp"
    if resolved.is_relative_to(checkout) and not (
        allow_checkout_tmp and resolved != scratch and resolved.is_relative_to(scratch)
    ):
        raise FixtureError(
            "Credential and private run state must be outside the checkout or in a tmp subdirectory"
        )
    return resolved


def private_directory(path: Path) -> None:
    """Create a user-owned private directory without changing unrelated parents."""

    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink() or path.stat().st_uid != os.getuid():
        raise FixtureError("Private directory must be user-owned and not a symlink")
    path.chmod(0o700)


def private_write(path: Path, data: bytes) -> None:
    """Atomically replace one private file without exposing a partial write."""

    private_directory(path.parent)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path: Path, payload: object) -> None:
    """Write private lifecycle data with stable JSON formatting."""

    private_write(path, (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode())


def allocate_run(
    config: ResolvedConfig, *, run_root: Path | None = None, repo_root: Path = REPO_ROOT
) -> Path:
    """Allocate a fresh external or checkout-tmp run directory for one selected lane."""

    parent = external_root("run", override=run_root, repo_root=repo_root, create=True)
    prefix = f"{config.case or config.auth_method}-{config.client}-{config.mode}-{config.surface}"
    result = parent / f"{prefix}-{uuid.uuid4().hex[:12]}"
    result.mkdir(mode=0o700)
    return result


def _inside_file(path: Path, root: Path) -> Path | None:
    """Return a regular file only when its resolved target remains in scope."""

    try:
        resolved = path.resolve()
        return resolved if resolved.is_relative_to(root.resolve()) and resolved.is_file() else None
    except (OSError, RuntimeError):
        return None


def _has_token(data: object, names: tuple[str, ...]) -> bool:
    """Accept nonempty token strings, excluding malformed scalar/object values."""

    return isinstance(data, dict) and any(
        isinstance(data.get(name), str) and data[name].strip() for name in names
    )


def candidate_from_source(
    client: Client, source: Path, *, user_home: Path | None = None
) -> AuthCandidate:
    """Inspect only supported files under one explicit home or auth-file input."""

    source = source.expanduser().resolve()
    root = source.parent if source.is_file() else source
    primary = (
        source
        if source.is_file()
        else root / ("credentials/kimi-code.json" if client == "kimi" else _AUTH_NAMES[client])
    )
    if source.is_file() and source.name != _AUTH_NAMES[client]:
        raise FixtureError("Selected source is not the supported auth filename for this client")
    primary = _inside_file(primary, root)
    files: dict[str, Path] = {}
    reason = None
    kind = "native-login"
    if primary is None:
        reason = "supported_auth_file_missing_or_non_file_auth"
    else:
        try:
            content = json.loads(primary.read_bytes())
            if not isinstance(content, dict) or not content:
                raise ValueError("empty or non-object")
            if client == "codex":
                tokens = content.get("tokens", {})
                usable = _has_token(content, ("OPENAI_API_KEY", "api_key")) or _has_token(
                    tokens, ("access_token", "refresh_token")
                )
                kind = (
                    "api-key-file"
                    if content.get("OPENAI_API_KEY") or content.get("api_key")
                    else "native-login"
                )
                config_path = _inside_file(root / "config.toml", root)
                if config_path is not None:
                    provider = tomllib.loads(config_path.read_text()).get("model_provider")
                    if provider not in {None, "openai"}:
                        usable = False
                        reason = "custom_provider_config_requires_explicit_api_case"
            elif client == "claude":
                oauth = content.get("claudeAiOauth", {})
                usable = _has_token(oauth, ("accessToken", "refreshToken"))
            else:
                token_data = content.get("tokens", content)
                usable = _has_token(
                    token_data, ("access_token", "accessToken", "refresh_token", "refreshToken")
                )
            if not usable and reason is None:
                reason = "unsupported_or_empty_auth_shape"
        except (OSError, ValueError, UnicodeError):
            reason = "unreadable_or_invalid_auth_json"
        if reason is None:
            relative = "credentials/kimi-code.json" if client == "kimi" else _AUTH_NAMES[client]
            files[relative] = primary
            home = primary.parent.parent if client == "kimi" else primary.parent
            companion = home / ("config.toml" if client == "kimi" else ".claude.json")
            if client in {"claude", "kimi"}:
                found = _inside_file(companion, home)
                if found is not None:
                    files[companion.name] = found
                elif (
                    client == "claude" and home == (user_home or Path.home()).resolve() / ".claude"
                ):
                    found = _inside_file(home.parent / ".claude.json", home.parent)
                    if found is not None:
                        files[".claude.json"] = found
            try:
                for name, path in files.items():
                    if name == "config.toml":
                        tomllib.loads(path.read_text())
                    elif name == ".claude.json" and not isinstance(
                        json.loads(path.read_bytes()), dict
                    ):
                        raise ValueError("Unsupported companion state")
            except (OSError, ValueError, UnicodeError):
                reason = "unreadable_or_invalid_companion_state"
                files = {}
    identifier = hashlib.sha256(f"{client}:{source}".encode()).hexdigest()[:20]
    return AuthCandidate(
        candidate_id=f"auth-{identifier}",
        client=client,
        source=source,
        kind=kind,
        importable=reason is None,
        reason=reason,
        files=files,
    )


def discover_auth(
    client: Client,
    *,
    process_env: Mapping[str, str] | None = None,
    user_home: Path | None = None,
    search_roots: Sequence[Path] = (),
    include_defaults: bool = True,
) -> list[AuthCandidate]:
    """Discover selected-tool files with bounded recursion and safe candidate output."""

    env = os.environ if process_env is None else process_env
    home = (user_home or Path.home()).resolve()
    sources: list[Path] = []
    if include_defaults:
        if env.get(HOME_VARIABLE[client]):
            sources.append(Path(env[HOME_VARIABLE[client]]).expanduser())
        sources.append(
            home / {"claude": ".claude", "codex": ".codex", "kimi": ".kimi-code"}[client]
        )
    for raw_root in search_roots:
        root = raw_root.expanduser().resolve()
        if root.is_file():
            sources.append(root)
            continue
        visited = 0
        for directory, directories, filenames in os.walk(root, followlinks=False):
            current = Path(directory)
            visited += 1
            directories[:] = (
                [
                    name
                    for name in sorted(directories)
                    if name not in _SKIP_DIRS
                    and not (current / name).is_symlink()
                    and len((current / name).relative_to(root).parts) <= 6
                ]
                if visited < 10000
                else []
            )
            if _AUTH_NAMES[client] in filenames:
                found = _inside_file(current / _AUTH_NAMES[client], root)
                if found is not None:
                    sources.append(found)
            if visited >= 10000:
                break
    result: dict[Path, AuthCandidate] = {}
    for source in sources:
        candidate = candidate_from_source(client, source, user_home=home)
        identity = next(iter(candidate.files.values()), candidate.source)
        result.setdefault(identity, candidate)
    return list(result.values())


@contextmanager
def _bundle_lock(root: Path, name: str) -> Iterator[None]:
    """Serialize publication and replacement of one local credential bundle."""

    descriptor = os.open(root / f".{name}.lock", os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(descriptor, "a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def bundle_path(root: Path, client: Client, name: str) -> Path:
    """Validate a human-readable local bundle identifier without path traversal."""

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name):
        raise FixtureError("Credential name must be a single safe directory identifier")
    return root / client / name


def import_auth(
    candidate: AuthCandidate,
    *,
    name: str,
    auth_root: Path | None = None,
    replace: bool = False,
) -> Path:
    """Copy one explicit candidate atomically without modifying its original files."""

    if not candidate.importable:
        raise FixtureError(f"Selected auth cannot be imported: {candidate.reason}")
    root = external_root("auth", override=auth_root, create=True)
    destination = bundle_path(root, candidate.client, name)
    private_directory(destination.parent)
    with _bundle_lock(destination.parent, name):
        if destination.is_symlink():
            raise FixtureError("Imported credential destination must not be a symlink")
        if destination.exists() and not replace:
            raise FixtureError("Credential already exists; select --replace explicitly")
        stage = Path(tempfile.mkdtemp(prefix=f".{name}-", dir=destination.parent))
        backup: Path | None = None
        try:
            for relative, source in candidate.files.items():
                private_write(stage / "files" / relative, source.read_bytes())
            if candidate.client == "claude" and ".claude.json" not in candidate.files:
                private_write(stage / "files/.claude.json", b"{}\n")
            private_write(stage / "env/vars.env", b"")
            write_json(
                stage / "import.json",
                {"client": candidate.client, "kind": candidate.kind, "schema_version": 1},
            )
            if destination.exists():
                backup = destination.with_name(f".{name}.previous-{uuid.uuid4().hex}")
                destination.rename(backup)
            try:
                stage.rename(destination)
            except BaseException:
                if backup is not None:
                    backup.rename(destination)
                    backup = None
                raise
        finally:
            if stage.exists():
                shutil.rmtree(stage)
            if backup is not None:
                shutil.rmtree(backup)
    return destination
