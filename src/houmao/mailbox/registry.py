"""Durable offline membership, scoped mail, and managed attachment authority.

Membership lives in the filesystem registration index, independently of runtime
leases and terminal presence. Public models never contain credential verifiers.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
import secrets
import re
import sqlite3
from typing import Literal, cast
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from houmao.agents.mailbox_runtime_models import FilesystemMailboxResolvedConfig
from houmao.mailbox.authority_lock import offline_authority_lock
from houmao.mailbox.filesystem import bootstrap_filesystem_mailbox, load_active_mailbox_registration
from houmao.mailbox.managed import (
    DeregisterMailboxRequest,
    ManagedMailboxOperationError,
    RegisterMailboxRequest,
    deregister_mailbox,
    register_mailbox,
)
from houmao.mailbox.models import (
    GatewayMailArchiveRequestV1,
    GatewayMailAttachmentUploadV1,
    GatewayMailboxMessageV1,
    GatewayMailListRequestV1,
    GatewayMailListResponseV1,
    GatewayMailMarkRequestV1,
    GatewayMailMessageRequestV1,
    GatewayMailMoveRequestV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
)
from houmao.mailbox.policy import (
    MailPolicyError,
    MailPolicyReceipt,
    SignedMailPolicyUpdate,
    apply_mail_policy,
    initialize_mail_policy,
    mail_policy_is_protected,
    read_mail_policy_receipt,
    set_mail_policy_owner,
    verify_mail_policy_update,
)
from houmao.mailbox.registry_config import (
    OfflineRegistryConfig,
    associate_registry_store,
    protected_registry_isolated,
    read_private_credential,
)
from houmao.mailbox.protocol import validate_mailbox_address
from houmao.mailbox.scope import MailScope, MailboxScopeError
from houmao.mailbox.services import FilesystemGatewayMailboxAdapter, ScopedMailboxAdapter

_MEMBER_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS offline_members ("
    "agent_id TEXT PRIMARY KEY, address TEXT NOT NULL, registration_id TEXT NOT NULL, "
    "credential_digest TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('active','released')))",
    "CREATE UNIQUE INDEX IF NOT EXISTS offline_member_active_address "
    "ON offline_members(address) WHERE status = 'active'",
    "CREATE UNIQUE INDEX IF NOT EXISTS offline_member_active_credential "
    "ON offline_members(credential_digest) WHERE status = 'active'",
    "CREATE TABLE IF NOT EXISTS offline_policy_backend ("
    "singleton INTEGER PRIMARY KEY CHECK(singleton = 1), backend_id TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS offline_uploads ("
    "upload_id TEXT PRIMARY KEY, registration_id TEXT NOT NULL, "
    "path TEXT NOT NULL UNIQUE, sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL, "
    "media_type TEXT NOT NULL, label TEXT)",
)
_ATTACHMENT_PREFIX = "registry-attachment:"


class OfflineRegistryError(RuntimeError):
    """A safe public registry error with a stable code and HTTP classification."""

    def __init__(self, code: str, message: str, status: int = 409) -> None:
        """Record only sanitized failure information."""

        super().__init__(message)
        self.m_code = code
        self.m_status = status

    @property
    def code(self) -> str:
        """Return the machine-readable failure code."""

        return self.m_code

    @property
    def status(self) -> int:
        """Return the corresponding HTTP status."""

        return self.m_status


class RegistryMember(BaseModel):
    """Safe durable membership, independent of a running body or gateway."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    agent_id: str
    address: str
    registration_id: str
    status: Literal["active", "released"]
    presence: Literal["unknown"] = "unknown"
    policy_backend_id: str | None = None
    placement_writable: bool = True


class RegistryPolicyOwnerResult(RegistryMember):
    """Owner enrollment evidence visible only to trusted registry administration."""

    policy_revision: int | None = None


class RegistryEnrollment(BaseModel):
    """Administrative enrollment with a caller-prepared private member token."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    agent_id: str = Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9_.-]+$")
    address: str
    member_credential: SecretStr
    display_name: str | None = None

    @field_validator("address")
    @classmethod
    def _validate_address(cls, value: str) -> str:
        """Normalize the full address before comparing durable membership."""

        return validate_mailbox_address(value)

    @field_validator("member_credential")
    @classmethod
    def _validate_credential(cls, value: SecretStr) -> SecretStr:
        """Require a high-entropy-sized token without echoing it on failure."""

        token = value.get_secret_value()
        if len(token) < 32 or any(character.isspace() for character in token):
            raise ValueError("member credential must have at least 32 non-space characters")
        return value


class RegistryAttachment(BaseModel):
    """Managed transport locator that never exposes a server filesystem path."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    attachment_id: str
    locator: str
    sha256: str
    size_bytes: int
    media_type: str
    label: str | None = None


def prepare_member_credential(path: Path) -> Path:
    """Create a private token once before enrollment so lost-response retries reuse it."""

    path = path.expanduser().absolute()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        read_private_credential(path)
        return path
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(secrets.token_urlsafe(48) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return path


class OfflineRegistryService:
    """Registry-host filesystem authority shared by local and HTTP callers."""

    def __init__(self) -> None:
        """Initialize an unconfigured service; use ``from_config``."""

        self.m_config: OfflineRegistryConfig
        self.m_index: Path
        self.m_admin_digest: str
        self.m_policy_backend_id: str
        self.m_policy_enabled: bool

    @classmethod
    def from_config(cls, config: OfflineRegistryConfig) -> OfflineRegistryService:
        """Validate explicit authority and initialize durable membership tables."""

        instance = cls()
        instance.m_config = config
        instance.m_admin_digest = _digest(read_private_credential(config.admin_credential_file))
        associate_registry_store(config.registry_root, config.mailbox_root)
        if config.protected_filtering:
            config.mailbox_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        paths = bootstrap_filesystem_mailbox(config.mailbox_root)
        instance.m_index = paths.sqlite_path
        with offline_authority_lock(config.mailbox_root):
            with sqlite3.connect(instance.m_index) as connection:
                for statement in _MEMBER_SCHEMA:
                    connection.execute(statement)
                initialize_mail_policy(connection)
                connection.execute(
                    "INSERT OR IGNORE INTO offline_policy_backend VALUES (1, ?)",
                    ("offline:" + uuid4().hex,),
                )
                instance.m_policy_backend_id = str(
                    connection.execute("SELECT backend_id FROM offline_policy_backend").fetchone()[
                        0
                    ]
                )
                known_member_credential = connection.execute(
                    "SELECT 1 FROM offline_members WHERE credential_digest=? LIMIT 1",
                    (instance.m_admin_digest,),
                ).fetchone()
                connection.commit()
            instance.m_index.chmod(0o600)
            instance.m_policy_enabled = (
                known_member_credential is None and protected_registry_isolated(config)
            )
            if not instance.m_policy_enabled:
                with sqlite3.connect(instance.m_index) as connection:
                    active_policy = connection.execute(
                        "SELECT 1 FROM mailbox_policy LIMIT 1"
                    ).fetchone()
                if active_policy is not None:
                    raise OfflineRegistryError(
                        "unsafe_policy_store",
                        "Existing protected policy state requires an isolated registry store",
                        503,
                    )
        return instance

    @property
    def max_attachment_bytes(self) -> int:
        """Return the configured content transfer limit."""

        return self.m_config.max_attachment_bytes

    def require_admin(self, credential: str) -> None:
        """Authenticate an administrative token independently of agent identity."""

        if not hmac.compare_digest(_digest(credential), self.m_admin_digest):
            raise OfflineRegistryError("unauthorized", "administrative credential required", 401)

    def enroll(self, request: RegistryEnrollment) -> RegistryMember:
        """Enroll idempotently; ordinary retries never rotate existing credentials."""

        digest = _digest(request.member_credential.get_secret_value())
        self._require_separate_member_digest(digest)
        with offline_authority_lock(self.m_config.mailbox_root):
            with sqlite3.connect(self.m_index) as connection:
                credential_owner = connection.execute(
                    "SELECT agent_id FROM offline_members WHERE credential_digest=? AND status='active'",
                    (digest,),
                ).fetchone()
            if credential_owner is not None and str(credential_owner[0]) != request.agent_id:
                raise OfflineRegistryError(
                    "credential_conflict", "member credential already belongs to another agent"
                )
            existing = self._member_for_agent(request.agent_id)
            if existing is not None and existing.status == "active":
                if existing.address != request.address:
                    raise OfflineRegistryError(
                        "membership_conflict", "agent already has an offline address"
                    )
                with sqlite3.connect(self.m_index) as connection:
                    old_digest = str(
                        connection.execute(
                            "SELECT credential_digest FROM offline_members WHERE agent_id = ?",
                            (request.agent_id,),
                        ).fetchone()[0]
                    )
                if not hmac.compare_digest(old_digest, digest):
                    raise OfflineRegistryError(
                        "credential_conflict",
                        "existing membership requires explicit credential replacement",
                    )
            try:
                result = register_mailbox(
                    self.m_config.mailbox_root,
                    RegisterMailboxRequest(
                        mode="safe",
                        address=request.address,
                        owner_principal_id=request.agent_id,
                        mailbox_kind="in_root",
                        mailbox_path=self.m_config.mailbox_root / "mailboxes" / request.address,
                        display_name=request.display_name,
                    ),
                )
            except ManagedMailboxOperationError as exc:
                raise OfflineRegistryError(
                    "address_conflict", "offline address is unavailable"
                ) from exc
            registration_id = str(result["active_registration_id"])
            with sqlite3.connect(self.m_index) as connection:
                connection.execute(
                    "INSERT INTO offline_members "
                    "(agent_id,address,registration_id,credential_digest,status) VALUES(?,?,?,?, 'active') "
                    "ON CONFLICT(agent_id) DO UPDATE SET address=excluded.address, "
                    "registration_id=excluded.registration_id, credential_digest=excluded.credential_digest, "
                    "status='active'",
                    (request.agent_id, request.address, registration_id, digest),
                )
                connection.commit()
            return self._with_policy_status(
                RegistryMember(
                    agent_id=request.agent_id,
                    address=request.address,
                    registration_id=registration_id,
                    status="active",
                )
            )

    def replace_credential(self, agent_id: str, credential: str) -> RegistryMember:
        """Replace a member token only through an explicit administrative operation."""

        if len(credential) < 32 or any(character.isspace() for character in credential):
            raise OfflineRegistryError("invalid_credential", "member credential is invalid", 422)
        digest = _digest(credential)
        self._require_separate_member_digest(digest)
        with offline_authority_lock(self.m_config.mailbox_root):
            member = self._member_for_agent(agent_id)
            if member is None or member.status != "active":
                raise OfflineRegistryError("not_registered", "active membership required", 404)
            with sqlite3.connect(self.m_index) as connection:
                other = connection.execute(
                    "SELECT agent_id FROM offline_members WHERE credential_digest=? "
                    "AND status='active' AND agent_id!=?",
                    (digest, agent_id),
                ).fetchone()
                if other is not None:
                    raise OfflineRegistryError(
                        "credential_conflict", "credential belongs to another member"
                    )
                connection.execute(
                    "UPDATE offline_members SET credential_digest = ? WHERE agent_id = ?",
                    (digest, agent_id),
                )
                connection.commit()
            return self._with_policy_status(member)

    def _require_separate_member_digest(self, digest: str) -> None:
        """Keep the independent registry administrator token out of runtime credentials."""

        if hmac.compare_digest(digest, self.m_admin_digest):
            raise OfflineRegistryError(
                "credential_conflict", "registry administrative credential is reserved"
            )

    def release(
        self,
        agent_id: str,
        *,
        purge: bool = False,
        expected_registration_id: str | None = None,
    ) -> RegistryMember:
        """Release membership without deleting canonical mail or external private targets."""

        with offline_authority_lock(self.m_config.mailbox_root):
            member = self._member_for_agent(agent_id)
            if member is None:
                raise OfflineRegistryError("not_registered", "membership was not found", 404)
            if (
                expected_registration_id is not None
                and member.registration_id != expected_registration_id
            ):
                raise MailboxScopeError("offline registration changed before release")
            if member.status == "released":
                return member
            try:
                registration = load_active_mailbox_registration(
                    self.m_config.mailbox_root,
                    address=member.address,
                )
            except Exception as exc:
                raise OfflineRegistryError(
                    "binding_conflict", "registration requires reconciliation"
                ) from exc
            if registration.registration_id != member.registration_id:
                raise OfflineRegistryError("binding_conflict", "registration changed")
            deregister_mailbox(
                self.m_config.mailbox_root,
                DeregisterMailboxRequest(
                    mode="purge" if purge else "deactivate",
                    address=member.address,
                ),
            )
            with sqlite3.connect(self.m_index) as connection:
                connection.execute(
                    "UPDATE offline_members SET status='released' WHERE agent_id=?", (agent_id,)
                )
                connection.commit()
            return member.model_copy(update={"status": "released"})

    def member_status(self, agent_id: str) -> RegistryMember:
        """Resolve durable ownership by agent ID independently of runtime presence."""

        with offline_authority_lock(self.m_config.mailbox_root):
            member = self._member_for_agent(agent_id)
            if member is not None:
                return self._with_policy_status(member)
            with sqlite3.connect(self.m_index) as connection:
                rows = connection.execute(
                    "SELECT address,registration_id FROM mailbox_registrations "
                    "WHERE owner_principal_id=? AND status='active'",
                    (agent_id,),
                ).fetchall()
            if len(rows) != 1:
                raise OfflineRegistryError(
                    "not_registered", "one active agent membership was not found", 404
                )
            return RegistryMember(
                agent_id=agent_id,
                address=str(rows[0][0]),
                registration_id=str(rows[0][1]),
                status="active",
            )

    def self_status(self, credential: str) -> RegistryMember:
        """Resolve a private member without relying on runtime presence."""

        with offline_authority_lock(self.m_config.mailbox_root):
            return self._with_policy_status(self._authenticate(credential, require_active=False))

    def release_self(self, credential: str, *, expected_registration_id: str) -> RegistryMember:
        """Authenticate and release one exact owner without a reassignment race."""

        with offline_authority_lock(self.m_config.mailbox_root):
            member = self._authenticate(credential, require_active=False)
            if member.status == "active":
                self._require_member_placement(member)
            return self.release(member.agent_id, expected_registration_id=expected_registration_id)

    def set_policy_owner(
        self, agent_id: str, *, expected_registration_id: str, public_key: str | None
    ) -> RegistryPolicyOwnerResult:
        """Enroll or revoke independent rule authority through trusted administration."""

        with offline_authority_lock(self.m_config.mailbox_root):
            if not self.m_policy_enabled or not protected_registry_isolated(self.m_config):
                raise OfflineRegistryError(
                    "unsupported_operation",
                    "protected filtering requires an isolated registry",
                    422,
                )
            member = self._policy_member(agent_id, expected_registration_id)
            try:
                with sqlite3.connect(self.m_index) as connection:
                    revision = set_mail_policy_owner(connection, member.registration_id, public_key)
            except MailPolicyError as exc:
                raise OfflineRegistryError(exc.code, str(exc), exc.status) from exc
            return RegistryPolicyOwnerResult(
                **self._with_policy_status(member).model_dump(),
                policy_revision=revision,
            )

    def apply_policy(
        self, request: SignedMailPolicyUpdate, *, credential: str | None = None
    ) -> MailPolicyReceipt:
        """Apply a scope-pinned owner proof through member relay or direct submission."""

        update = request.update
        with offline_authority_lock(self.m_config.mailbox_root):
            member = self._authenticate(credential) if credential is not None else None
            if member is not None and member.registration_id != update.binding_id:
                return MailPolicyReceipt(
                    status="refused", operation_id=update.operation_id, detail="binding_conflict"
                )
            if not self.m_policy_enabled:
                return MailPolicyReceipt(
                    status="unsupported",
                    operation_id=update.operation_id,
                    detail="registry_not_isolated",
                )
            try:
                with sqlite3.connect(self.m_index) as connection:
                    row = connection.execute(
                        "SELECT m.agent_id FROM offline_members m JOIN mailbox_registrations r "
                        "ON r.registration_id=m.registration_id AND r.address=m.address "
                        "AND r.owner_principal_id=m.agent_id "
                        "WHERE m.registration_id=? AND m.status='active' AND r.status='active'",
                        (update.binding_id,),
                    ).fetchone()
                    if row is None:
                        return MailPolicyReceipt(
                            status="refused",
                            operation_id=update.operation_id,
                            detail="owner_authority_required",
                        )
                    prior = verify_mail_policy_update(
                        connection,
                        backend_id=self.m_policy_backend_id,
                        binding_id=update.binding_id,
                        request=request,
                    )
                    if prior is not None:
                        return prior
                    if not protected_registry_isolated(self.m_config):
                        return MailPolicyReceipt(
                            status="unsupported",
                            operation_id=update.operation_id,
                            detail="registry_not_isolated",
                        )
                    return apply_mail_policy(
                        connection,
                        backend_id=self.m_policy_backend_id,
                        binding_id=update.binding_id,
                        request=request,
                    )
            except MailPolicyError as exc:
                return MailPolicyReceipt(
                    status="refused", operation_id=update.operation_id, detail=exc.code
                )
            except sqlite3.Error:
                return MailPolicyReceipt(
                    status="uncertain",
                    operation_id=update.operation_id,
                    detail="registry_unavailable",
                )

    def policy_receipt(
        self, agent_id: str, *, expected_registration_id: str, operation_id: str
    ) -> MailPolicyReceipt:
        """Return durable rule-application evidence through trusted administration."""

        with offline_authority_lock(self.m_config.mailbox_root):
            member = self._policy_member(agent_id, expected_registration_id)
            with sqlite3.connect(self.m_index) as connection:
                receipt = read_mail_policy_receipt(
                    connection, binding_id=member.registration_id, operation_id=operation_id
                )
            if receipt is None:
                raise OfflineRegistryError(
                    "receipt_not_found", "policy receipt is unavailable", 404
                )
            return receipt

    def _policy_member(self, agent_id: str, expected_registration_id: str) -> RegistryMember:
        """Resolve an active registry member with an exact durable mailbox registration."""

        member = self._member_for_agent(agent_id)
        if (
            member is None
            or member.status != "active"
            or member.registration_id != expected_registration_id
        ):
            raise MailboxScopeError("offline registration changed")
        try:
            registration = load_active_mailbox_registration(
                self.m_config.mailbox_root, address=member.address
            )
        except (OSError, ValueError, RuntimeError) as exc:
            raise MailboxScopeError("offline registration changed") from exc
        if (
            registration.registration_id != member.registration_id
            or registration.owner_principal_id != member.agent_id
        ):
            raise MailboxScopeError("offline registration changed")
        return member

    def _with_policy_status(self, member: RegistryMember) -> RegistryMember:
        """Expose only the selected binding's policy target and placement capability."""

        if not self.m_policy_enabled or member.status != "active":
            return member
        return member.model_copy(
            update={
                "policy_backend_id": self.m_policy_backend_id,
                "placement_writable": not self._placement_protected(member),
            }
        )

    def _placement_protected(self, member: RegistryMember) -> bool:
        """Read current protection while caller holds the offline authority lock."""

        with sqlite3.connect(self.m_index) as connection:
            return mail_policy_is_protected(connection, member.registration_id)

    def _require_member_placement(self, member: RegistryMember) -> None:
        """Reserve protected filing and registration release for trusted administration."""

        if self._placement_protected(member):
            raise OfflineRegistryError(
                "unsupported_operation", "protected placement requires backend authority", 422
            )

    def _member_for_agent(self, agent_id: str) -> RegistryMember | None:
        """Load safe membership without exposing a credential digest."""

        with sqlite3.connect(self.m_index) as connection:
            row = connection.execute(
                "SELECT agent_id,address,registration_id,status FROM offline_members WHERE agent_id=?",
                (agent_id,),
            ).fetchone()
        if row is None:
            return None
        return RegistryMember(
            agent_id=str(row[0]),
            address=str(row[1]),
            registration_id=str(row[2]),
            status=cast(Literal["active", "released"], str(row[3])),
        )

    def _authenticate(self, credential: str, *, require_active: bool = True) -> RegistryMember:
        """Authenticate active owner and confirm its exact registration still exists."""

        digest = _digest(credential)
        with sqlite3.connect(self.m_index) as connection:
            row = connection.execute(
                "SELECT agent_id,credential_digest FROM offline_members "
                "WHERE credential_digest=? "
                + ("AND status='active' " if require_active else "")
                + "ORDER BY (status='active') DESC LIMIT 1",
                (digest,),
            ).fetchone()
        if row is None or not hmac.compare_digest(str(row[1]), digest):
            raise OfflineRegistryError("unauthorized", "active member credential required", 401)
        member = self._member_for_agent(str(row[0]))
        assert member is not None
        if member.status == "released":
            return member
        try:
            registration = load_active_mailbox_registration(
                self.m_config.mailbox_root, address=member.address
            )
        except Exception as exc:
            raise OfflineRegistryError(
                "binding_conflict", "registration requires reconciliation"
            ) from exc
        if (
            registration.registration_id != member.registration_id
            or registration.owner_principal_id != member.agent_id
        ):
            raise OfflineRegistryError("binding_conflict", "offline registration changed")
        return member

    def _adapter(self, member: RegistryMember) -> ScopedMailboxAdapter:
        """Build the same filesystem backend used by local mail operations."""

        config = FilesystemMailboxResolvedConfig(
            transport="filesystem",
            principal_id=member.agent_id,
            agent_id=member.agent_id,
            binding_id=member.registration_id,
            address=member.address,
            filesystem_root=self.m_config.mailbox_root,
            bindings_version=member.registration_id,
            registry_root=self.m_config.registry_root,
        )
        return ScopedMailboxAdapter.from_backend(
            FilesystemGatewayMailboxAdapter(config),
            MailScope(member.agent_id, "offline", member.registration_id),
        )

    def list_page(
        self, credential: str, request: GatewayMailListRequestV1
    ) -> GatewayMailListResponseV1:
        """Authorize and page the authoritative offline metadata index."""

        with offline_authority_lock(self.m_config.mailbox_root):
            member = self._authenticate(credential)
            if request.box == "archive":
                self._require_member_placement(member)
            return self._list_page(member, request)

    def _list_page(
        self,
        member: RegistryMember,
        request: GatewayMailListRequestV1,
    ) -> GatewayMailListResponseV1:
        """Page a bound mailbox after the caller's scope has been selected."""

        from houmao.mailbox.pagination import build_mail_page_response

        adapter = self._adapter(member)
        adapter.scope.require_binding(request.expected_binding_id)
        page = adapter.list_page(
            box=request.box,
            read_state=request.read_state,
            answered_state=request.answered_state,
            archived=request.archived,
            limit=request.limit,
            since=request.since,
            cursor=request.cursor,
        )
        page.messages[:] = [self._transport_message(message) for message in page.messages]
        return build_mail_page_response(identity=adapter.status(), box=request.box, page=page)

    def owner_list_page(
        self, agent_id: str, request: GatewayMailListRequestV1
    ) -> GatewayMailListResponseV1:
        """Review a protected recipient's folders through trusted administration."""

        with offline_authority_lock(self.m_config.mailbox_root):
            member = self._protected_member(agent_id, request.expected_binding_id)
            if request.box != "archive":
                raise OfflineRegistryError(
                    "unsupported_operation", "protected administration reviews Archive", 422
                )
            return self._list_page(member, request)

    def owner_peek(
        self, agent_id: str, request: GatewayMailMessageRequestV1
    ) -> GatewayMailboxMessageV1:
        """Review one message in the selected recipient mailbox as the placement authority."""

        with offline_authority_lock(self.m_config.mailbox_root):
            member = self._protected_member(agent_id, request.expected_binding_id)
            return self._transport_message(
                self._adapter(member).peek(message_ref=request.message_ref, box="archive")
            )

    def owner_archive(
        self, agent_id: str, request: GatewayMailArchiveRequestV1
    ) -> list[GatewayMailboxMessageV1]:
        """File selected processed mail through trusted administration."""

        with offline_authority_lock(self.m_config.mailbox_root):
            member = self._protected_member(agent_id, request.expected_binding_id)
            messages = self._adapter(member).archive(message_refs=request.message_refs)
            return [self._transport_message(message) for message in messages]

    def _protected_member(self, agent_id: str, expected_registration_id: str) -> RegistryMember:
        """Scope trusted placement access to an active protected registration."""

        member = self._policy_member(agent_id, expected_registration_id)
        if not self._placement_protected(member):
            raise OfflineRegistryError(
                "unsupported_operation", "membership does not use protected placement", 422
            )
        return member

    def mail(
        self,
        credential: str,
        operation: str,
        request: GatewayMailMessageRequestV1
        | GatewayMailSendRequestV1
        | GatewayMailReplyRequestV1
        | GatewayMailMarkRequestV1
        | GatewayMailMoveRequestV1
        | GatewayMailArchiveRequestV1,
    ) -> list[GatewayMailboxMessageV1]:
        """Authorize owner and binding before a shared mail lifecycle operation."""

        with offline_authority_lock(self.m_config.mailbox_root):
            member = self._authenticate(credential)
            adapter = self._adapter(member)
            adapter.scope.require_binding(request.expected_binding_id)
            if isinstance(request, GatewayMailMessageRequestV1) and operation in ("peek", "read"):
                self._require_member_messages(member, [request.message_ref])
                method = adapter.peek if operation == "peek" else adapter.read
                messages = [method(message_ref=request.message_ref, box=request.box)]
            elif isinstance(request, GatewayMailSendRequestV1) and operation == "send":
                messages = [
                    adapter.send(
                        to_addresses=request.to,
                        cc_addresses=request.cc,
                        subject=request.subject,
                        body_content=request.body_content,
                        attachments=self._attachment_inputs(member, request.attachments),
                        notify_block=request.notify_block,
                        notify_auth=request.notify_auth,
                    )
                ]
            elif isinstance(request, GatewayMailReplyRequestV1) and operation == "reply":
                self._require_member_messages(member, [request.message_ref])
                messages = [
                    adapter.reply(
                        message_ref=request.message_ref,
                        body_content=request.body_content,
                        attachments=self._attachment_inputs(member, request.attachments),
                        notify_block=request.notify_block,
                        notify_auth=request.notify_auth,
                    )
                ]
            elif isinstance(request, GatewayMailMarkRequestV1) and operation == "mark":
                if request.archived is not None:
                    self._require_member_placement(member)
                self._require_member_messages(member, request.message_refs)
                messages = adapter.mark(
                    message_refs=request.message_refs,
                    read=request.read,
                    answered=request.answered,
                    archived=request.archived,
                )
            elif isinstance(request, GatewayMailMoveRequestV1) and operation == "move":
                self._require_member_placement(member)
                messages = adapter.move(
                    message_refs=request.message_refs, destination_box=request.destination_box
                )
            elif isinstance(request, GatewayMailArchiveRequestV1) and operation == "archive":
                self._require_member_placement(member)
                messages = adapter.archive(message_refs=request.message_refs)
            else:
                raise OfflineRegistryError(
                    "unsupported_operation", "operation is not supported", 422
                )
            return [self._transport_message(message) for message in messages]

    def _require_member_messages(self, member: RegistryMember, references: list[str]) -> None:
        """Prevent protected Archive-only content reads through ordinary runtime references."""

        if not self._placement_protected(member):
            return
        scope = MailScope(member.agent_id, "offline", member.registration_id)
        with sqlite3.connect(self.m_index) as connection:
            for reference in references:
                raw_ref = scope.decode(reference)
                prefix, _separator, message_id = raw_ref.partition(":")
                if (
                    prefix != "filesystem"
                    or connection.execute(
                        "SELECT 1 FROM mailbox_projections "
                        "WHERE registration_id=? AND message_id=? AND folder_name<>'archive' LIMIT 1",
                        (member.registration_id, message_id),
                    ).fetchone()
                    is None
                ):
                    raise OfflineRegistryError("message_not_found", "message is unavailable", 404)

    def upload(
        self,
        credential: str,
        content: bytes,
        *,
        sha256: str,
        media_type: str = "application/octet-stream",
        label: str | None = None,
    ) -> RegistryAttachment:
        """Store bounded content owned by one immutable registration."""

        if len(content) > self.max_attachment_bytes:
            raise OfflineRegistryError(
                "attachment_too_large", "attachment exceeds transfer limit", 413
            )
        digest = hashlib.sha256(content).hexdigest()
        if re.fullmatch(r"[0-9a-f]{64}", sha256) is None or not hmac.compare_digest(digest, sha256):
            raise OfflineRegistryError("digest_mismatch", "attachment digest does not match", 422)
        with offline_authority_lock(self.m_config.mailbox_root):
            member = self._authenticate(credential)
            upload_id = uuid4().hex
            directory = self.m_config.mailbox_root / "attachments" / "managed" / "uploads"
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            target = directory / upload_id
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
            try:
                with sqlite3.connect(self.m_index) as connection:
                    connection.execute(
                        "INSERT INTO offline_uploads VALUES(?,?,?,?,?,?,?)",
                        (
                            upload_id,
                            member.registration_id,
                            str(target),
                            digest,
                            len(content),
                            media_type,
                            label,
                        ),
                    )
                    connection.commit()
            except Exception:
                target.unlink(missing_ok=True)
                raise
            return RegistryAttachment(
                attachment_id=upload_id,
                locator=_ATTACHMENT_PREFIX + upload_id,
                sha256=digest,
                size_bytes=len(content),
                media_type=media_type,
                label=label,
            )

    def download(self, credential: str, upload_id: str) -> tuple[RegistryAttachment, bytes]:
        """Download only an owned upload or content attached to the member's mail."""

        with offline_authority_lock(self.m_config.mailbox_root):
            member = self._authenticate(credential)
            protected = self._placement_protected(member)
            with sqlite3.connect(self.m_index) as connection:
                row = connection.execute(
                    "SELECT registration_id,path,sha256,size_bytes,media_type,label "
                    "FROM offline_uploads WHERE upload_id=?",
                    (upload_id,),
                ).fetchone()
                if row is None:
                    raise OfflineRegistryError(
                        "attachment_not_found", "attachment is unavailable", 404
                    )
                allowed = (
                    str(row[0]) == member.registration_id
                    or connection.execute(
                        "SELECT 1 FROM attachments a JOIN message_attachments ma USING(attachment_id) "
                        "JOIN mailbox_projections p USING(message_id) "
                        "WHERE a.locator=? AND p.registration_id=? "
                        "AND (? = 0 OR p.folder_name <> 'archive') LIMIT 1",
                        (str(row[1]), member.registration_id, protected),
                    ).fetchone()
                    is not None
                )
                if not allowed:
                    raise OfflineRegistryError(
                        "attachment_not_found", "attachment is unavailable", 404
                    )
            if int(row[3]) > self.max_attachment_bytes:
                raise OfflineRegistryError(
                    "attachment_too_large", "attachment exceeds transfer limit", 413
                )
            with Path(str(row[1])).open("rb") as handle:
                content = handle.read(self.max_attachment_bytes + 1)
            if len(content) != int(row[3]) or not hmac.compare_digest(
                hashlib.sha256(content).hexdigest(), str(row[2])
            ):
                raise OfflineRegistryError(
                    "attachment_corrupt", "attachment verification failed", 409
                )
            attachment = RegistryAttachment(
                attachment_id=upload_id,
                locator=_ATTACHMENT_PREFIX + upload_id,
                sha256=str(row[2]),
                size_bytes=int(row[3]),
                media_type=str(row[4]),
                label=None if row[5] is None else str(row[5]),
            )
            return attachment, content

    def _attachment_inputs(
        self,
        member: RegistryMember,
        inputs: list[GatewayMailAttachmentUploadV1],
    ) -> list[GatewayMailAttachmentUploadV1]:
        """Resolve managed upload locators; never open a caller-selected host path."""

        translated: list[GatewayMailAttachmentUploadV1] = []
        with sqlite3.connect(self.m_index) as connection:
            for item in inputs:
                if not item.path.startswith(_ATTACHMENT_PREFIX):
                    raise OfflineRegistryError(
                        "attachment_locator_required", "upload attachment content first", 422
                    )
                row = connection.execute(
                    "SELECT path FROM offline_uploads WHERE upload_id=? AND registration_id=?",
                    (item.path.removeprefix(_ATTACHMENT_PREFIX), member.registration_id),
                ).fetchone()
                if row is None:
                    raise OfflineRegistryError(
                        "attachment_not_found", "owned upload is required", 404
                    )
                translated.append(GatewayMailAttachmentUploadV1(path=str(row[0]), label=item.label))
        return translated

    def _transport_message(self, message: GatewayMailboxMessageV1) -> GatewayMailboxMessageV1:
        """Replace internal attachment paths with authorized download locators."""

        attachments = []
        with sqlite3.connect(self.m_index) as connection:
            for attachment in message.attachments:
                row = connection.execute(
                    "SELECT upload_id FROM offline_uploads WHERE path=?", (attachment.locator,)
                ).fetchone()
                attachments.append(
                    attachment.model_copy(
                        update={
                            "locator": _ATTACHMENT_PREFIX + str(row[0])
                            if row is not None
                            else None,
                            "attachment_id": str(row[0])
                            if row is not None
                            else attachment.attachment_id,
                        }
                    )
                )
        return message.model_copy(update={"attachments": attachments})


def _digest(credential: str) -> str:
    """Hash high-entropy bearer material for private verification storage."""

    return hashlib.sha256(credential.encode("utf-8")).hexdigest()
