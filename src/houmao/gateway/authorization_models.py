"""Typed authorization data for one observed gateway owner domain."""

from __future__ import annotations

from functools import cached_property
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from houmao.gateway._access_sshsig import key_fingerprint, load_public_key, public_key_text
from houmao.gateway.access_models import (
    GatewayLaunchSeed,
    GatewayOwner,
    GatewaySelfKey,
    GatewayTarget,
)

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_][A-Za-z0-9_.:-]{0,127}$")]
Resource = Annotated[str, Field(pattern=r"^[A-Za-z0-9_][A-Za-z0-9_.:/-]{0,255}$")]
Action = Annotated[str, Field(pattern=r"^[A-Za-z0-9_][A-Za-z0-9_.:-]{0,127}$")]
KeyId = Annotated[str, Field(pattern=r"^SHA256:[A-Za-z0-9_-]{43}$")]
Expiry = Annotated[int, Field(ge=0)]
AuthorizationBasis = Literal["public", "scoped", "self", "admin", "open"]
AuthorizationMode = Literal["open", "keyed"]


class _AuthorizationModel(BaseModel):
    """Validate strict immutable policy records without echoing input on error."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True, strict=True)


class Permission(_AuthorizationModel):
    """Name one supported effect on a canonical resource."""

    resource: Resource
    action: Action


class Principal(_AuthorizationModel):
    """Keep the stable authorization identity distinct from labels and keys."""

    principal_id: Identifier
    kind: Literal["operator", "service", "agent"]
    label: Annotated[str, Field(min_length=1, max_length=128)]
    logical_agent_id: Identifier | None = None

    @model_validator(mode="after")
    def _validate_agent_identity(self) -> Principal:
        """Require the logical identity only for enrolled agent principals."""

        if (self.kind == "agent") != (self.logical_agent_id is not None):
            raise ValueError("only agent principals select a logical agent ID")
        return self


class Credential(_AuthorizationModel):
    """Bind a public key to a principal and one independently revocable enrollment."""

    principal_id: Identifier
    public_key: Annotated[str, Field(min_length=1, max_length=4096, repr=False)]
    enrollment_id: Identifier = Field(default_factory=lambda: uuid4().hex)
    admin_revision: Annotated[int, Field(ge=0)] | None = None

    @field_validator("public_key")
    @classmethod
    def _canonicalize_key(cls, value: str) -> str:
        """Accept supported SSH keys and discard their presentation comments."""

        return public_key_text(load_public_key(value))

    @cached_property
    def key_id(self) -> str:
        """Return the fingerprint of the canonical public key."""

        return key_fingerprint(self.public_key)


class ScopedGrant(_AuthorizationModel):
    """Grant a stable principal one exact operation with optional expiry."""

    principal_id: Identifier
    permission: Permission
    expires_at: Expiry | None = None


class RoleDefinition(_AuthorizationModel):
    """Define explicit permissions for a domain-scoped role."""

    role_id: Identifier
    permissions: tuple[Permission, ...] = Field(max_length=1024)

    @model_validator(mode="after")
    def _validate_permissions(self) -> RoleDefinition:
        """Keep host roles reserved and reject redundant permission rows."""

        if self.role_id in {"gateway-admin", "anonymous", "self"}:
            raise ValueError("role name is reserved")
        if len(set(self.permissions)) != len(self.permissions):
            raise ValueError("role repeats a permission")
        return self


class RoleAssignment(_AuthorizationModel):
    """Assign an existing policy role to a principal for a bounded interval."""

    principal_id: Identifier
    role_id: Identifier
    expires_at: Expiry | None = None


class PolicySnapshot(_AuthorizationModel):
    """Contain all retained authorization rows read at one revision."""

    schema_version: Literal[1] = 1
    owner: GatewayOwner
    policy_id: Identifier = Field(default_factory=lambda: uuid4().hex)
    revision: Annotated[int, Field(ge=0)] = 0
    roster_revision: Annotated[int, Field(ge=0)] = 0
    open_epoch: Annotated[int, Field(ge=0)] = 0
    principals: tuple[Principal, ...] = Field(default=(), max_length=512)
    credentials: tuple[Credential, ...] = Field(default=(), max_length=512)
    roles: tuple[RoleDefinition, ...] = Field(default=(), max_length=128)
    grants: tuple[ScopedGrant, ...] = Field(default=(), max_length=4096)
    role_assignments: tuple[RoleAssignment, ...] = Field(default=(), max_length=4096)

    @model_validator(mode="after")
    def _validate_rows(self) -> PolicySnapshot:
        """Reject ambiguous identities, dangling relations, and impossible revisions."""

        principal_ids = {principal.principal_id for principal in self.principals}
        if len(principal_ids) != len(self.principals):
            raise ValueError("duplicate principal ID")
        role_ids = {role.role_id for role in self.roles}
        if len(role_ids) != len(self.roles):
            raise ValueError("duplicate role ID")
        if len({key.key_id for key in self.credentials}) != len(self.credentials):
            raise ValueError("duplicate credential key")
        if len({key.enrollment_id for key in self.credentials}) != len(self.credentials):
            raise ValueError("duplicate credential enrollment")
        if len({(row.principal_id, row.permission) for row in self.grants}) != len(self.grants):
            raise ValueError("duplicate scoped grant")
        if len({(row.principal_id, row.role_id) for row in self.role_assignments}) != len(
            self.role_assignments
        ):
            raise ValueError("duplicate role assignment")
        if any(row.principal_id not in principal_ids for row in self.credentials):
            raise ValueError("credential principal is missing")
        if any(row.principal_id not in principal_ids for row in self.grants):
            raise ValueError("grant principal is missing")
        if any(
            row.principal_id not in principal_ids or row.role_id not in role_ids
            for row in self.role_assignments
        ):
            raise ValueError("role assignment principal or role is missing")
        if self.open_epoch > self.roster_revision or self.roster_revision > self.revision:
            raise ValueError("invalid roster revisions")
        if any(
            key.admin_revision is not None and key.admin_revision > self.revision
            for key in self.credentials
        ):
            raise ValueError("invalid admin qualification revision")
        return self

    @property
    def admin_mode(self) -> AuthorizationMode:
        """Return the mode determined by current per-key admin qualifications."""

        return (
            "keyed" if any(key.admin_revision is not None for key in self.credentials) else "open"
        )

    def find_credential(self, key_id: str) -> Credential | None:
        """Read the current enrollment for this key on the selected target."""

        return next((key for key in self.credentials if key.key_id == key_id), None)


class AuthorizationActor(_AuthorizationModel):
    """Carry proof identity established by a trusted ingress."""

    kind: Literal["anonymous", "credential", "self"]
    principal_id: Identifier | None = None
    key_id: KeyId | None = None
    enrollment_id: Identifier | None = None
    generation_id: Identifier | None = None

    @model_validator(mode="after")
    def _validate_provenance(self) -> AuthorizationActor:
        """Reject credential attributes that are inconsistent with proof type."""

        if self.kind == "anonymous":
            if any((self.principal_id, self.key_id, self.enrollment_id, self.generation_id)):
                raise ValueError("anonymous actor cannot have credential evidence")
        elif (
            self.principal_id is None
            or self.key_id is None
            or (self.enrollment_id is not None) != (self.kind == "credential")
            or (self.generation_id is not None) != (self.kind == "self")
        ):
            raise ValueError("actor has incomplete or inconsistent credential evidence")
        return self

    @classmethod
    def from_credential(cls, credential: Credential) -> AuthorizationActor:
        """Preserve the exact verified enrollment for policy evaluation."""

        return cls(
            kind="credential",
            principal_id=credential.principal_id,
            key_id=credential.key_id,
            enrollment_id=credential.enrollment_id,
        )

    @classmethod
    def from_self(cls, binding: GatewaySelfKey) -> AuthorizationActor:
        """Preserve the proof identity of a verified same-target generation."""

        return cls(
            kind="self",
            principal_id=binding.owner.agent_id,
            key_id=binding.key_id,
            generation_id=binding.generation_id,
        )


class AuthorizationDecision(_AuthorizationModel):
    """Pin the admitted target, credential, permission set, and authorization basis."""

    actor: AuthorizationActor
    target: GatewayTarget
    listener_id: Identifier
    permissions: tuple[Permission, ...] = Field(min_length=1, max_length=64)
    basis: AuthorizationBasis
    policy_id: Identifier
    policy_revision: Annotated[int, Field(ge=0)]
    open_epoch: Annotated[int, Field(ge=0)] | None = None
    admin_revision: Annotated[int, Field(ge=0)] | None = None

    @model_validator(mode="after")
    def _validate_basis(self) -> AuthorizationDecision:
        """Require the evidence that can fence the exact admitted basis."""

        if (self.open_epoch is not None) != (self.basis == "open"):
            raise ValueError("invalid open authority evidence")
        if (self.admin_revision is not None) != (self.basis == "admin"):
            raise ValueError("invalid admin authority evidence")
        if self.basis in {"scoped", "admin"} and self.actor.kind != "credential":
            raise ValueError("an enrolled actor is required")
        if self.basis == "self" and self.actor.kind != "self":
            raise ValueError("same-agent self evidence is required")
        return self


class AuthorizationAuditEntry(_AuthorizationModel):
    """Expose a safe policy mutation or handoff record to the verified owner."""

    event_id: Annotated[int, Field(gt=0)]
    recorded_at: Expiry
    actor: Identifier
    action: Action
    operation_id: Identifier | None = None
    policy_revision: Annotated[int, Field(ge=0)]


def seed_snapshot(owner: GatewayOwner, seed: GatewayLaunchSeed) -> PolicySnapshot:
    """Build first-birth policy from the execution owner's explicit principal IDs."""

    principals = {key.principal: None for key in seed.admin_keys}
    return PolicySnapshot(
        owner=owner,
        principals=tuple(
            Principal(principal_id=value, kind="operator", label=value) for value in principals
        ),
        credentials=tuple(
            Credential(principal_id=key.principal, public_key=key.public_key, admin_revision=0)
            for key in seed.admin_keys
        ),
    )
