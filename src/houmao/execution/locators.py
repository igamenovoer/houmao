"""Secret-free operator locators for agents controlled through an execution owner."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import stat
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from houmao.agents.realm_controller.agent_identity import (
    normalize_managed_agent_id,
    normalize_managed_agent_name,
)
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.execution.models import ExecutionBindingV1, validate_selector
from houmao.owned_mutation import remove_tree_or_path
from houmao.owned_paths import resolve_registry_root

MAX_LOCATOR_BYTES = 65_536


class ExecutorLocatorError(ValueError):
    """Report invalid, ambiguous, conflicting, or unsafe operator routing state."""


class ExecutorAgentLocatorV1(BaseModel):
    """Point to owner authority without copying manifests, endpoints, or mutable runtime state."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    schema_version: Literal[1] = 1
    kind: Literal["executor_managed"] = "executor_managed"
    agent_id: str
    agent_name: str
    profile_name: str
    binding: ExecutionBindingV1

    _profile = field_validator("profile_name")(validate_selector)

    @field_validator("agent_id")
    @classmethod
    def _agent_id(cls, value: str) -> str:
        """Reuse authoritative identity normalization without silently changing a stored ID."""

        try:
            normalized = normalize_managed_agent_id(value)
        except SessionManifestError:
            raise ValueError("invalid authoritative agent ID") from None
        if normalized != value:
            raise ValueError("agent ID must be normalized")
        return value

    @field_validator("agent_name")
    @classmethod
    def _agent_name(cls, value: str) -> str:
        """Validate a friendly name without deriving logical identity from it."""

        try:
            normalized = normalize_managed_agent_name(value)
        except SessionManifestError:
            raise ValueError("invalid friendly agent name") from None
        if normalized != value:
            raise ValueError("agent name must be normalized")
        return value

    @model_validator(mode="after")
    def _profile_matches_binding(self) -> ExecutorAgentLocatorV1:
        """Prevent a locator from selecting a different profile than its captured binding."""

        if self.profile_name != self.binding.profile_name:
            raise ValueError("locator profile differs from its execution binding")
        return self


def executor_locators_root(
    *, root: Path | None = None, env: Mapping[str, str] | None = None
) -> Path:
    """Return the operator collection beneath its effective registry root without creating it."""

    return resolve_registry_root(explicit_root=root, env=env) / "executor_agents"


def load_executor_locator(
    agent_id: str, *, root: Path | None = None, env: Mapping[str, str] | None = None
) -> ExecutorAgentLocatorV1 | None:
    """Load an exact routing identity without opening any owner-local path.

    Missing entries return None. Present but malformed or unsafe entries fail explicitly
    so a known exact identity cannot fall through to unrelated caller-local authority.
    """

    agent_id = _identity(agent_id)
    collection = executor_locators_root(root=root, env=env)
    _require_directory(collection, missing_ok=True)
    directory = collection / agent_id
    if not directory.exists() and not directory.is_symlink():
        return None
    _require_directory(directory)
    path = directory / "record.json"
    try:
        payload = _read_bounded(path)
    except FileNotFoundError:
        raise ExecutorLocatorError("Known execution locator has no readable record") from None
    try:
        record = ExecutorAgentLocatorV1.model_validate_json(payload)
    except (ValidationError, ValueError):
        raise ExecutorLocatorError("Known execution locator is malformed or incompatible") from None
    if record.agent_id != agent_id:
        raise ExecutorLocatorError("Execution locator ID differs from its registry path")
    return record


def list_executor_locators(
    *, root: Path | None = None, env: Mapping[str, str] | None = None
) -> tuple[ExecutorAgentLocatorV1, ...]:
    """List valid routing locators without leases, liveness probes, or filesystem repairs."""

    collection = executor_locators_root(root=root, env=env)
    _require_directory(collection, missing_ok=True)
    if not collection.exists():
        return ()
    records: list[ExecutorAgentLocatorV1] = []
    for directory in sorted(collection.iterdir()):
        try:
            record = load_executor_locator(directory.name, root=root, env=env)
        except (ExecutorLocatorError, OSError):
            continue
        if record is not None:
            records.append(record)
    return tuple(records)


def resolve_executor_locator(
    *,
    agent_id: str | None = None,
    agent_name: str | None = None,
    root: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> ExecutorAgentLocatorV1 | None:
    """Resolve one exact ID or unique friendly name, reporting ambiguous owner contexts."""

    if (agent_id is None) == (agent_name is None):
        raise ExecutorLocatorError("Provide exactly one agent ID or friendly name")
    if agent_id is not None:
        return load_executor_locator(agent_id, root=root, env=env)
    assert agent_name is not None
    try:
        normalized = normalize_managed_agent_name(agent_name)
    except SessionManifestError:
        raise ExecutorLocatorError("Invalid friendly agent name") from None
    records = tuple(
        record
        for record in list_executor_locators(root=root, env=env)
        if record.agent_name == normalized
    )
    if len(records) > 1:
        candidates = ", ".join(
            f"{record.agent_id}@{record.binding.context_id}" for record in records
        )
        raise ExecutorLocatorError(
            f"Ambiguous execution-owned agent name; select an agent ID: {candidates}"
        )
    return records[0] if records else None


def publish_executor_locator(
    record: ExecutorAgentLocatorV1,
    *,
    root: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> ExecutorAgentLocatorV1:
    """Atomically publish an admitted owner's locator without replacing another owner.

    Publication shares the stable per-ID ownership lock used by local lifecycle records.
    A caller must report partial owner-launch success if this operation fails afterward.
    """

    # Revalidate copy-updated models as well as deserialized caller input.
    record = ExecutorAgentLocatorV1.model_validate_json(record.model_dump_json())
    registry = resolve_registry_root(explicit_root=root, env=env)
    collection = executor_locators_root(root=root, env=env)
    _require_directory(collection, missing_ok=True)
    with _identity_lock(registry, record.agent_id):
        existing = load_executor_locator(record.agent_id, root=root, env=env)
        if existing is not None and existing.binding != record.binding:
            raise ExecutorLocatorError(
                "Authoritative agent ID already has a different execution binding"
            )
        _check_local_owner_conflict(registry, record)
        collection.mkdir(mode=0o700, parents=True, exist_ok=True)
        _require_directory(collection)
        directory = collection / record.agent_id
        directory.mkdir(mode=0o700, exist_ok=True)
        _require_directory(directory)
        payload = (record.model_dump_json(indent=2) + "\n").encode()
        if len(payload) > MAX_LOCATOR_BYTES:
            raise ExecutorLocatorError("Execution locator exceeds its size limit")
        temporary = directory / f".record.{uuid4().hex}.tmp"
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as target:
                target.write(payload)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary, directory / "record.json")
        finally:
            temporary.unlink(missing_ok=True)
    return record


def forget_executor_locator(
    agent_id: str, *, root: Path | None = None, env: Mapping[str, str] | None = None
) -> bool:
    """Remove only an operator locator's lexical entry, with no owner lifecycle action."""

    agent_id = _identity(agent_id)
    registry = resolve_registry_root(explicit_root=root, env=env)
    collection = executor_locators_root(root=root, env=env)
    _require_directory(collection, missing_ok=True)
    path = collection / agent_id
    if not path.exists() and not path.is_symlink():
        return False
    with _identity_lock(registry, agent_id):
        _require_directory(collection)
        existed = path.exists() or path.is_symlink()
        remove_tree_or_path(path, allowed_roots=(collection,))
        return existed


def _identity(value: str) -> str:
    """Validate storage selectors through the existing logical identity contract."""

    try:
        return normalize_managed_agent_id(value)
    except SessionManifestError:
        raise ExecutorLocatorError("Invalid authoritative agent ID") from None


def _require_directory(path: Path, *, missing_ok: bool = False) -> None:
    """Reject symlinked/non-directory routing storage before reading or mutating it."""

    try:
        metadata = path.lstat()
    except FileNotFoundError:
        if missing_ok:
            return
        raise ExecutorLocatorError("Execution locator directory is missing") from None
    if not stat.S_ISDIR(metadata.st_mode):
        raise ExecutorLocatorError("Execution locator directory is unsafe")


def _read_bounded(path: Path) -> bytes:
    """Read only a regular lexical record with finite size and no symlink following."""

    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ExecutorLocatorError("Execution locator record is unsafe")
            payload = source.read(MAX_LOCATOR_BYTES + 1)
    except FileNotFoundError:
        raise
    except OSError:
        raise ExecutorLocatorError("Execution locator record cannot be read safely") from None
    if len(payload) > MAX_LOCATOR_BYTES:
        raise ExecutorLocatorError("Execution locator exceeds its size limit")
    return payload


def _check_local_owner_conflict(registry: Path, desired: ExecutorAgentLocatorV1) -> None:
    """Refuse to publish an executor locator over a different owner-local logical identity."""

    collection = registry / "live_agents"
    _require_directory(collection, missing_ok=True)
    directory = collection / desired.agent_id
    if not directory.exists() and not directory.is_symlink():
        return
    _require_directory(directory)
    try:
        payload: object = json.loads(_read_bounded(directory / "record.json"))
        if not isinstance(payload, dict) or payload.get("agent_id") != desired.agent_id:
            raise ValueError("invalid local identity")
        binding = ExecutionBindingV1.model_validate_json(
            json.dumps(payload.get("execution_binding"))
        )
    except (OSError, ValueError, ValidationError):
        raise ExecutorLocatorError(
            "Local agent ID exists without matching execution authority"
        ) from None
    if binding != desired.binding:
        raise ExecutorLocatorError("Local agent ID belongs to a different execution binding")


@contextmanager
def _identity_lock(registry: Path, agent_id: str) -> Iterator[None]:
    """Serialize locator/local-runtime publications using their common per-ID lock path."""

    directory = registry / ".managed-agent-locks"
    _require_directory(directory, missing_ok=True)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    _require_directory(directory)
    descriptor = os.open(
        directory / f"{agent_id}.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
    )
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
