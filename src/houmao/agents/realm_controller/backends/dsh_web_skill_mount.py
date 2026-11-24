"""Bind one versioned skill mount to the verified DSH Web process and Agent."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
import re
import time
from uuid import UUID, uuid4

import yaml

from houmao.agents.realm_controller.backends.dsh_web_client import DshWebClient, DshWebError
from houmao.gateway._access_storage import (
    GatewayAccessError,
    _file_lock,
    _private_directory,
    _read_file,
    _write_file,
)
from houmao.gateway.file_edits.projection import FileProjection
from houmao.gateway.file_edits.storage import MountStorage

QUALIFIED_BUILD = "0.2.2-rc.3"
QUALIFIED_PRESET = "standard"
_LINEAGE = re.compile(r"[a-f0-9]{32}")
_SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_DELIMITER = re.compile(r"^---\r?$", re.MULTILINE)
_UNCONFIRMED_ADMISSION = {"outcome_uncertain", "protocol_mismatch", "transport_failure"}


def skill_home_lineage(root: Path, *, create: bool = False) -> str:
    """Recover a private home lineage, creating it only for owner opt-in."""

    with _private_directory(root, create=create) as directory:
        with _file_lock(directory, ".lineage.lock", exclusive=create, create=create):
            try:
                data = _read_file(directory, "lineage", 33)
            except FileNotFoundError:
                if not create:
                    raise
                data = (uuid4().hex + "\n").encode("ascii")
                _write_file(directory, "lineage", data)
    lineage = data.decode("ascii")
    if not lineage.endswith("\n") or not _LINEAGE.fullmatch(lineage[:-1]):
        raise ValueError("Invalid private skill mount lineage")
    return lineage[:-1]


def validate_skill_tree(files: Mapping[str, bytes]) -> None:
    """Require native skill directory names and parse each required entrypoint."""

    roots: set[str] = set()
    for path in files:
        root, slash, _ = path.partition("/")
        if not slash or not _SKILL_NAME.fullmatch(root):
            raise GatewayAccessError(422, "invalid_skill_tree")
        roots.add(root)
    for root in roots:
        entrypoint = files.get(f"{root}/SKILL.md")
        if entrypoint is None:
            raise GatewayAccessError(422, "invalid_skill_tree")
        try:
            text = entrypoint.decode("utf-8")
            opening = _DELIMITER.match(text)
            closing = _DELIMITER.search(text, pos=opening.end() + 1) if opening else None
            if opening is None or closing is None:
                raise ValueError
            metadata = yaml.safe_load(text[opening.end() : closing.start()])
        except (UnicodeError, RecursionError, ValueError, yaml.YAMLError):
            raise GatewayAccessError(422, "invalid_skill_tree") from None
        if (
            not isinstance(metadata, dict)
            or metadata.get("name") != root
            or not isinstance(metadata.get("description"), str)
            or not metadata["description"].strip()
        ):
            raise GatewayAccessError(422, "invalid_skill_tree")
        for key in ("disableModelInvocation", "modelInvocable", "userInvocable"):
            if key in metadata:
                raise GatewayAccessError(422, "invalid_skill_tree")
        for key in ("disable-model-invocation", "user-invocable"):
            if key in metadata and str(metadata[key]).lower() not in {
                "true",
                "false",
                "yes",
                "no",
                "on",
                "off",
                "1",
                "0",
            }:
                raise GatewayAccessError(422, "invalid_skill_tree")


def _native_access_error(error: DshWebError) -> GatewayAccessError:
    """Translate exact native refusals without exporting native error messages."""

    if error.code == "busy":
        return GatewayAccessError(409, "file_native_busy")
    if error.code in {"conflict", "stale_identity", "stale_operation"}:
        return GatewayAccessError(409, "file_native_conflict")
    if error.code == "invalid_request":
        return GatewayAccessError(422, "invalid_skill_tree")
    return GatewayAccessError(503, "file_native_unavailable")


class DshSkillTransaction:
    """Hold the owner-authenticated channel for one native maintenance claim."""

    def __init__(
        self,
        client: DshWebClient,
        identity: dict[str, object],
        operation_id: str,
        token: str,
    ) -> None:
        """Bind future requests to the already-selected operation and Peer."""

        self.m_client: DshWebClient = client
        self.m_operation_id: str = operation_id
        self.m_request: dict[str, object] = {
            "identity": identity,
            "operation_id": operation_id,
            "maintenance_token": token,
        }
        self.m_settlement: Mapping[str, object] | None = None

    @property
    def settlement(self) -> Mapping[str, object] | None:
        """Read the verified outcome recorded when native maintenance was released."""

        return self.m_settlement

    def publish(self) -> Mapping[str, object]:
        """Dispatch the exact operation once while native maintenance is held."""

        try:
            return _native_receipt(
                self.m_client.call("skill_mount_publish", self.m_request), self.m_operation_id
            )
        except DshWebError as error:
            raise _native_access_error(error) from None

    def close(self) -> None:
        """Release native maintenance and capture any attributable final evidence."""

        try:
            self.m_settlement = _native_receipt(
                self.m_client.call("skill_mount_close", self.m_request), self.m_operation_id
            )
        except (DshWebError, GatewayAccessError):
            # The Peer closure independently ends the native hold.
            pass


class DshWebSkillMount:
    """Expose only the native mount qualified for the exact owned DSH Web Agent."""

    def __init__(
        self,
        storage: MountStorage,
        projection: FileProjection,
        identity: dict[str, object],
        open_peer: Callable[[float], AbstractContextManager[DshWebClient]],
    ) -> None:
        """Capture the verified native identity and private mount layout."""

        self.m_storage: MountStorage = storage
        self.m_projection: FileProjection = projection
        self.m_identity: dict[str, object] = identity.copy()
        self.m_open_peer: Callable[[float], AbstractContextManager[DshWebClient]] = open_peer

    @property
    def storage(self) -> MountStorage:
        """Return the retained owner-private Git and draft store."""

        return self.m_storage

    @property
    def projection(self) -> FileProjection:
        """Return the owner-provisioned immutable revision projection."""

        return self.m_projection

    def validate(self, files: dict[str, bytes]) -> None:
        """Validate the mount's layout before creating or activating a commit."""

        validate_skill_tree(files)

    def require_native_mount(self, client: DshWebClient) -> None:
        """Verify the effective native build, preset, and retained mount binding."""

        try:
            native = client.call("skill_mount", {"identity": self.m_identity})
        except DshWebError as error:
            raise _native_access_error(error) from None
        if native != {
            "mount_id": self.m_storage.mount_id,
            "preset": QUALIFIED_PRESET,
            "build": QUALIFIED_BUILD,
        }:
            raise GatewayAccessError(503, "file_native_unavailable")

    @contextmanager
    def native_transaction(
        self, operation_id: str, candidate: str, expected: str, *, deadline_monotonic: float
    ) -> Iterator[DshSkillTransaction]:
        """Acquire one immediate native hold before the gateway hands off publication."""

        remaining = deadline_monotonic - time.monotonic()
        if remaining <= 0:
            raise GatewayAccessError(503, "file_native_unavailable")
        try:
            with self.m_open_peer(remaining) as client:
                remaining = deadline_monotonic - time.monotonic()
                if remaining <= 0:
                    raise GatewayAccessError(503, "file_native_unavailable")
                try:
                    token_result = client.call(
                        "skill_mount_open",
                        {
                            "identity": self.m_identity,
                            "operation_id": operation_id,
                            "candidate": candidate,
                            "expected": expected,
                            "deadline_epoch_ms": int((time.time() + remaining) * 1000),
                        },
                    )
                except DshWebError as error:
                    if error.code in _UNCONFIRMED_ADMISSION:
                        raise GatewayAccessError(503, "file_native_admission_unconfirmed") from None
                    raise
                token = (
                    token_result.get("maintenance_token")
                    if isinstance(token_result, dict)
                    and token_result.keys() == {"maintenance_token"}
                    else None
                )
                try:
                    if not isinstance(token, str) or str(UUID(token, version=4)) != token:
                        raise ValueError
                except ValueError:
                    raise GatewayAccessError(503, "file_native_admission_unconfirmed") from None
                transaction = DshSkillTransaction(client, self.m_identity, operation_id, token)
                try:
                    yield transaction
                finally:
                    transaction.close()
        except DshWebError as error:
            raise _native_access_error(error) from None

    def native_status(self, operation_id: str) -> Mapping[str, object]:
        """Read evidence for the selected attempt from the current owned execution."""

        try:
            with self.m_open_peer(3.0) as client:
                result = client.call(
                    "skill_mount_status",
                    {"identity": self.m_identity, "operation_id": operation_id},
                )
        except DshWebError as error:
            raise _native_access_error(error) from None
        return {} if result is None else _native_receipt(result, operation_id)


def _native_receipt(value: object, operation_id: str) -> Mapping[str, object]:
    """Read publication evidence only when it belongs to the exact operation."""

    if (
        not isinstance(value, dict)
        or value.get("operation_id") != operation_id
        or value.get("outcome") not in ("pending", "activated", "unchanged", "unknown")
        or type(value.get("native_settled")) is not bool
        or type(value.get("native_ready")) is not bool
    ):
        raise GatewayAccessError(503, "file_native_unavailable")
    return value
