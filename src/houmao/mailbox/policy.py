"""Signed recipient rules and durable receipts for trusted mail backends."""

from __future__ import annotations

import base64
import binascii
from hashlib import sha256
import json
import sqlite3
from typing import Literal, cast

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, load_ssh_public_key
from pydantic import BaseModel, ConfigDict, Field, field_validator

from houmao.mailbox.errors import MailboxProtocolError
from houmao.mailbox.protocol import validate_mailbox_address

_SIGNATURE_DOMAIN = b"houmao-mail-policy-v1\x00"
_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS mailbox_policy ("
    "binding_id TEXT PRIMARY KEY, owner_public_key TEXT, revision INTEGER NOT NULL)",
    "CREATE TABLE IF NOT EXISTS mailbox_policy_block ("
    "binding_id TEXT NOT NULL, sender_address TEXT NOT NULL, "
    "PRIMARY KEY (binding_id, sender_address))",
    "CREATE TABLE IF NOT EXISTS mailbox_policy_receipt ("
    "binding_id TEXT NOT NULL, operation_id TEXT NOT NULL, digest TEXT NOT NULL, "
    "revision INTEGER NOT NULL, PRIMARY KEY (binding_id, operation_id))",
)


class MailPolicyError(RuntimeError):
    """A policy failure safe to report without showing rule or key material."""

    def __init__(self, code: str, status: int, message: str) -> None:
        """Classify the failure for transport-specific adapters."""

        super().__init__(message)
        self.m_code = code
        self.m_status = status

    @property
    def code(self) -> str:
        """Return the stable failure classification."""

        return self.m_code

    @property
    def status(self) -> int:
        """Return the corresponding HTTP status."""

        return self.m_status


class MailPolicyUpdate(BaseModel):
    """A complete replacement of the prospective blocklist for one mailbox."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    operation: Literal["apply"] = "apply"
    backend_id: str = Field(min_length=1, max_length=512)
    binding_id: str = Field(min_length=1, max_length=512)
    expected_revision: int = Field(strict=True, ge=0, lt=2**63 - 1)
    operation_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    blocked_senders: tuple[str, ...] = Field(max_length=4096, repr=False)

    @field_validator("blocked_senders")
    @classmethod
    def _validate_senders(cls, senders: tuple[str, ...]) -> tuple[str, ...]:
        """Accept exact normalized addresses without changing local-part case."""

        try:
            return tuple(sorted({validate_mailbox_address(sender) for sender in senders}))
        except MailboxProtocolError as exc:
            raise ValueError("blocked senders must be full mailbox addresses") from exc

    def signing_bytes(self) -> bytes:
        """Return stable, purpose-separated bytes for the normalized update."""

        payload = json.dumps(
            self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
        return _SIGNATURE_DOMAIN + payload.encode("utf-8")


class SignedMailPolicyUpdate(BaseModel):
    """An owner-signed rule update that the gateway can forward unchanged."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    update: MailPolicyUpdate
    signature: str = Field(min_length=88, max_length=88, repr=False)


class GatewayMailPolicyRequest(BaseModel):
    """Pin the selected gateway binding separately from the backend request."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    expected_binding_id: str = Field(min_length=1, max_length=512)
    signed_update: SignedMailPolicyUpdate = Field(repr=False)


class MailPolicyReceipt(BaseModel):
    """The outcome of one policy request, without blocklist contents."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    status: Literal["applied", "refused", "unsupported", "uncertain"]
    operation_id: str
    revision: int | None = None
    detail: str | None = None


def sign_mail_policy_update(
    update: MailPolicyUpdate, signer: Ed25519PrivateKey
) -> SignedMailPolicyUpdate:
    """Sign a rule change in the independently controlled owner process."""

    signature = signer.sign(update.signing_bytes())
    return SignedMailPolicyUpdate(
        update=update, signature=base64.b64encode(signature).decode("ascii")
    )


def initialize_mail_policy(connection: sqlite3.Connection) -> None:
    """Create policy state inside the trusted backend's private store."""

    for statement in _SCHEMA:
        connection.execute(statement)


def set_mail_policy_owner(
    connection: sqlite3.Connection, binding_id: str, public_key: str | None
) -> int | None:
    """Fence earlier proofs on rotation or revocation and retain existing rules."""

    if public_key is None:
        connection.execute(
            "UPDATE mailbox_policy SET owner_public_key = NULL, revision = revision + 1 "
            "WHERE binding_id = ? AND owner_public_key IS NOT NULL",
            (binding_id,),
        )
    else:
        owner = _load_owner_key(public_key)
        normalized = owner.public_bytes(Encoding.OpenSSH, PublicFormat.OpenSSH).decode("ascii")
        connection.execute(
            "INSERT INTO mailbox_policy(binding_id, owner_public_key, revision) VALUES (?, ?, 0) "
            "ON CONFLICT(binding_id) DO UPDATE SET owner_public_key = excluded.owner_public_key, "
            "revision = revision + 1 WHERE owner_public_key IS NOT excluded.owner_public_key",
            (binding_id, normalized),
        )
    row = connection.execute(
        "SELECT revision FROM mailbox_policy WHERE binding_id = ?", (binding_id,)
    ).fetchone()
    return int(row[0]) if row is not None else None


def mail_policy_is_protected(connection: sqlite3.Connection, binding_id: str) -> bool:
    """Return whether this binding reserves placement for the trusted authority."""

    if not _has_policy_store(connection):
        return False
    return (
        connection.execute(
            "SELECT 1 FROM mailbox_policy WHERE binding_id = ?", (binding_id,)
        ).fetchone()
        is not None
    )


def mail_policy_blocks(
    connection: sqlite3.Connection, *, binding_id: str, sender_address: str
) -> bool:
    """Test a transport-verified sender before publishing a recipient placement."""

    if not _has_policy_store(connection):
        return False
    return (
        connection.execute(
            "SELECT 1 FROM mailbox_policy_block WHERE binding_id = ? AND sender_address = ?",
            (binding_id, sender_address),
        ).fetchone()
        is not None
    )


def read_mail_policy_receipt(
    connection: sqlite3.Connection, *, binding_id: str, operation_id: str
) -> MailPolicyReceipt | None:
    """Read a prior outcome from an independently authorized backend path."""

    row = connection.execute(
        "SELECT revision FROM mailbox_policy_receipt WHERE binding_id = ? AND operation_id = ?",
        (binding_id, operation_id),
    ).fetchone()
    if row is None:
        return None
    return MailPolicyReceipt(status="applied", operation_id=operation_id, revision=row[0])


def verify_mail_policy_update(
    connection: sqlite3.Connection,
    *,
    backend_id: str,
    binding_id: str,
    request: SignedMailPolicyUpdate,
) -> MailPolicyReceipt | None:
    """Verify current owner authority and scope, then return any exact replay receipt."""

    update = request.update
    if update.backend_id != backend_id or update.binding_id != binding_id:
        raise MailPolicyError("binding_conflict", 409, "Mail policy target does not match.")
    owner = connection.execute(
        "SELECT owner_public_key, revision FROM mailbox_policy WHERE binding_id = ?", (binding_id,)
    ).fetchone()
    if owner is None or owner[0] is None:
        raise MailPolicyError("owner_authority_required", 403, "Mailbox owner proof required.")
    payload = update.signing_bytes()
    try:
        signature = base64.b64decode(request.signature, validate=True)
        _load_owner_key(cast(str, owner[0])).verify(signature, payload)
    except (binascii.Error, InvalidSignature, MailPolicyError, ValueError) as exc:
        raise MailPolicyError(
            "owner_authority_required", 403, "Mailbox owner proof refused."
        ) from exc
    prior = connection.execute(
        "SELECT digest, revision FROM mailbox_policy_receipt "
        "WHERE binding_id = ? AND operation_id = ?",
        (binding_id, update.operation_id),
    ).fetchone()
    if prior is not None:
        if prior[0] != sha256(payload).hexdigest():
            raise MailPolicyError("operation_conflict", 409, "Mail policy operation ID was reused.")
        return MailPolicyReceipt(
            status="applied", operation_id=update.operation_id, revision=prior[1]
        )
    if owner[1] != update.expected_revision:
        raise MailPolicyError("revision_conflict", 409, "Mail policy revision changed.")
    return None


def apply_mail_policy(
    connection: sqlite3.Connection,
    *,
    backend_id: str,
    binding_id: str,
    request: SignedMailPolicyUpdate,
) -> MailPolicyReceipt:
    """Apply a signed rule and receipt in the backend's serialized transaction."""

    if not connection.in_transaction:
        connection.execute("BEGIN IMMEDIATE")
    prior = verify_mail_policy_update(
        connection, backend_id=backend_id, binding_id=binding_id, request=request
    )
    if prior is not None:
        return prior
    update = request.update
    revision = update.expected_revision + 1
    connection.execute(
        "UPDATE mailbox_policy SET revision = ? WHERE binding_id = ?",
        (revision, binding_id),
    )
    connection.execute("DELETE FROM mailbox_policy_block WHERE binding_id = ?", (binding_id,))
    connection.executemany(
        "INSERT INTO mailbox_policy_block(binding_id, sender_address) VALUES (?, ?)",
        ((binding_id, sender) for sender in update.blocked_senders),
    )
    connection.execute(
        "INSERT INTO mailbox_policy_receipt(binding_id, operation_id, digest, revision) "
        "VALUES (?, ?, ?, ?)",
        (binding_id, update.operation_id, sha256(update.signing_bytes()).hexdigest(), revision),
    )
    return MailPolicyReceipt(status="applied", operation_id=update.operation_id, revision=revision)


def _load_owner_key(value: str) -> Ed25519PublicKey:
    """Parse a single OpenSSH Ed25519 public key without using gateway credentials."""

    try:
        key = load_ssh_public_key(value.strip().encode("ascii"))
    except (ValueError, UnsupportedAlgorithm) as exc:
        raise MailPolicyError(
            "invalid_owner_key", 422, "An Ed25519 owner public key is required."
        ) from exc
    if not isinstance(key, Ed25519PublicKey):
        raise MailPolicyError("invalid_owner_key", 422, "An Ed25519 owner public key is required.")
    return key


def _has_policy_store(connection: sqlite3.Connection) -> bool:
    """Keep existing ordinary shared mailbox databases readable."""

    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'mailbox_policy'"
        ).fetchone()
        is not None
    )
