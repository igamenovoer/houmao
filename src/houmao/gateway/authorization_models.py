"""Typed authorization data for one observed gateway owner domain."""

from __future__ import annotations

from functools import cached_property
from typing import Annotated, ClassVar, Literal, Self
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
AuthorizationBasis = Literal["public", "scoped", "self", "admin", "open", "default"]
AuthorizationMode = Literal["open", "keyed"]
PermissionGroupName = Literal[
    "agent-requester",
    "agent-maintainer",
    "agent-operator",
    "managed-self",
    "agent-admin",
]
RETIRED_OBSERVER_ROLE = "builtin:agent-observer"
BUILTIN_PEER_ROLES: dict[str, PermissionGroupName] = {
    "builtin:agent-requester": "agent-requester",
    "builtin:agent-maintainer": "agent-maintainer",
    "builtin:agent-operator": "agent-operator",
}


class _AuthorizationModel(BaseModel):
    """Validate strict immutable policy records without echoing input on error."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True, strict=True)


class Permission(_AuthorizationModel):
    """Name one supported effect on a canonical resource."""

    resource: Resource
    action: Action


STATUS_READ_PERMISSION = Permission(resource="agent", action="agent.status.read")


class _ExpectedPolicyTarget(_AuthorizationModel):
    """Pin an administration request to two optional verified coordinates."""

    schema_version: Literal[1] = 1
    expected_target: GatewayTarget | None = None
    expected_listener_id: Identifier | None = None

    def require_expected(self, decision: AuthorizationDecision) -> None:
        """Refuse a mutation on a different listener or generation than selected."""

        from houmao.gateway._access_storage import GatewayAccessError

        if (self.expected_target is not None and self.expected_target != decision.target) or (
            self.expected_listener_id is not None
            and self.expected_listener_id != decision.listener_id
        ):
            raise GatewayAccessError(409, "authorization_target_conflict")


class DefaultPermissionGroupRequest(_ExpectedPolicyTarget):
    """Select one versioned built-in group as the unassigned caller default."""

    group: PermissionGroupName


class DefaultPermissionGroupReceipt(_AuthorizationModel):
    """Report the retained default after a completed policy transaction."""

    schema_version: Literal[1] = 1
    default_permission_group: PermissionGroupName
    default_permission_revision: Annotated[int, Field(ge=0)]
    policy_revision: Annotated[int, Field(ge=0)]


class DefaultFallbackRequest(_ExpectedPolicyTarget):
    """Set whether one verified principal can inherit the current default."""

    enabled: bool


class PrincipalDefaultFallback(_AuthorizationModel):
    """Retain a principal setting and every transition's fence."""

    principal_id: Identifier
    enabled: bool
    revision: Annotated[int, Field(ge=1)]


class DefaultFallbackReceipt(_AuthorizationModel):
    """Report the committed principal setting and enclosing policy revision."""

    schema_version: Literal[1] = 1
    principal_id: Identifier
    enabled: bool
    default_fallback_revision: Annotated[int, Field(ge=1)]
    policy_revision: Annotated[int, Field(ge=0)]


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
    source: Literal["direct", "retired-observer"] = "direct"

    @model_validator(mode="after")
    def _validate_source(self) -> ScopedGrant:
        """Only an exact status grant can originate in an observer migration."""

        if self.source == "retired-observer" and self.permission != STATUS_READ_PERMISSION:
            raise ValueError("migrated observer grant must supply only status access")
        return self


class RoleTemplate(_AuthorizationModel):
    """Retain the catalog revision and exact resource used to create a local role."""

    name: Identifier
    resource: Resource
    version: Literal[1] = 1


class RoleDefinition(_AuthorizationModel):
    """Define explicit permissions for a domain-scoped role."""

    role_id: Identifier
    permissions: tuple[Permission, ...] = Field(max_length=1024)
    template: RoleTemplate | None = None

    @model_validator(mode="after")
    def _validate_permissions(self) -> RoleDefinition:
        """Keep host roles reserved and reject redundant permission rows."""

        if self.role_id in {"gateway-admin", "anonymous", "self"}:
            raise ValueError("role name is reserved")
        if len(set(self.permissions)) != len(self.permissions):
            raise ValueError("role repeats a permission")
        if self.template is not None and any(
            permission.resource != self.template.resource for permission in self.permissions
        ):
            raise ValueError("template permissions must use its exact resource")
        return self


class RoleAssignment(_AuthorizationModel):
    """Assign an existing policy role to a principal for a bounded interval."""

    principal_id: Identifier
    role_id: Identifier
    expires_at: Expiry | None = None
    builtin_version: Literal[1] | None = None


class _PolicyRows(_AuthorizationModel):
    """Validate owner, identity, and permission rows in retained policy versions."""

    builtin_roles: ClassVar[frozenset[str]] = frozenset(BUILTIN_PEER_ROLES)
    owner: GatewayOwner
    policy_id: Identifier = Field(default_factory=lambda: uuid4().hex)
    revision: Annotated[int, Field(ge=0)] = 0
    roster_revision: Annotated[int, Field(ge=0)] = 0
    open_epoch: Annotated[int, Field(ge=0)] = 0
    default_permission_revision: Annotated[int, Field(ge=0)] = 0
    principals: tuple[Principal, ...] = Field(default=(), max_length=512)
    credentials: tuple[Credential, ...] = Field(default=(), max_length=512)
    roles: tuple[RoleDefinition, ...] = Field(default=(), max_length=128)
    grants: tuple[ScopedGrant, ...] = Field(default=(), max_length=4608)
    role_assignments: tuple[RoleAssignment, ...] = Field(default=(), max_length=4096)

    @model_validator(mode="after")
    def _validate_rows(self) -> Self:
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
        if len({(row.principal_id, row.permission, row.source) for row in self.grants}) != len(
            self.grants
        ):
            raise ValueError("duplicate scoped grant")
        assignments = {
            (row.principal_id, row.role_id, row.builtin_version is not None)
            for row in self.role_assignments
        }
        if len(assignments) != len(self.role_assignments):
            raise ValueError("duplicate role assignment")
        if any(row.principal_id not in principal_ids for row in self.credentials):
            raise ValueError("credential principal is missing")
        if any(row.principal_id not in principal_ids for row in self.grants):
            raise ValueError("grant principal is missing")
        if any(
            row.principal_id not in principal_ids
            or row.role_id not in (self.builtin_roles if row.builtin_version else role_ids)
            for row in self.role_assignments
        ):
            raise ValueError("role assignment principal or role is missing")
        if self.open_epoch > self.roster_revision or self.roster_revision > self.revision:
            raise ValueError("invalid roster revisions")
        if self.default_permission_revision > self.revision:
            raise ValueError("invalid default permission revision")
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


class LegacyPolicySnapshot(_PolicyRows):
    """Read the previous version solely at the retained-policy migration boundary."""

    builtin_roles: ClassVar[frozenset[str]] = _PolicyRows.builtin_roles | {RETIRED_OBSERVER_ROLE}
    schema_version: Literal[1] = 1
    default_permission_group: PermissionGroupName | Literal["agent-observer"] = "agent-requester"
    default_permission_group_version: Literal[1] = 1

    @model_validator(mode="after")
    def _validate_legacy_grants(self) -> LegacyPolicySnapshot:
        """Allow only grant rows that could have been written in the previous version."""

        if len(self.grants) > 4096 or any(row.source != "direct" for row in self.grants):
            raise ValueError("invalid legacy grant rows")
        return self


class PolicySnapshot(_PolicyRows):
    """Contain all current retained authorization rows read at one revision."""

    schema_version: Literal[2] = 2
    default_permission_group: PermissionGroupName | None = "agent-requester"
    default_permission_group_version: Literal[1] | None = 1
    default_permission_effects: tuple[Permission, ...] = ()
    principal_default_fallback: tuple[PrincipalDefaultFallback, ...] = Field(
        default=(), max_length=512
    )

    @model_validator(mode="after")
    def _validate_defaults(self) -> PolicySnapshot:
        """Validate exact migrated defaults and the per-principal fallback fences."""

        exact = self.default_permission_group is None
        if (self.default_permission_group_version is None) != exact or (
            self.default_permission_effects != ((STATUS_READ_PERMISSION,) if exact else ())
        ):
            raise ValueError("invalid retained default definition")
        principals = {row.principal_id for row in self.principals}
        fallback_ids = {row.principal_id for row in self.principal_default_fallback}
        if (
            len(fallback_ids) != len(self.principal_default_fallback)
            or not fallback_ids <= principals
        ):
            raise ValueError("invalid principal fallback rows")
        if any(row.revision > self.revision for row in self.principal_default_fallback):
            raise ValueError("invalid principal fallback revision")
        return self

    def find_default_fallback(self, principal_id: str | None) -> PrincipalDefaultFallback | None:
        """Read the retained override, leaving callers without a row enabled by default."""

        return next(
            (row for row in self.principal_default_fallback if row.principal_id == principal_id),
            None,
        )


class AuthorizationActor(_AuthorizationModel):
    """Carry proof identity established by a trusted ingress."""

    kind: Literal["anonymous", "credential", "self", "mail"]
    principal_id: Identifier | None = None
    key_id: KeyId | None = None
    enrollment_id: Identifier | None = None
    generation_id: Identifier | None = None
    self_registration_revision: Annotated[int, Field(ge=1)] | None = None
    self_native_authority: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    transport_issuer: Identifier | None = None
    transport_member: Identifier | None = None
    transport_binding: Identifier | None = None

    @model_validator(mode="after")
    def _validate_provenance(self) -> AuthorizationActor:
        """Reject credential attributes that are inconsistent with proof type."""

        transport = (self.transport_issuer, self.transport_member, self.transport_binding)
        if self.kind == "mail":
            if not all(transport) or any(
                (
                    self.key_id,
                    self.enrollment_id,
                    self.generation_id,
                    self.self_registration_revision,
                    self.self_native_authority,
                )
            ):
                raise ValueError("mail actor requires independent transport evidence")
            return self
        if any(transport):
            raise ValueError("transport evidence belongs to the mail ingress")
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
        if (
            self.self_registration_revision is not None or self.self_native_authority is not None
        ) and self.kind != "self":
            raise ValueError("native and registration authority requires managed-self evidence")
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
            self_registration_revision=binding.registration_revision,
            self_native_authority=binding.native_authority,
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
    default_permission_revision: Annotated[int, Field(ge=0)] | None = None
    default_permissions: tuple[Permission, ...] = Field(default=(), max_length=64)
    default_fallback_revision: Annotated[int, Field(ge=1)] | None = None

    @model_validator(mode="after")
    def _validate_basis(self) -> AuthorizationDecision:
        """Require the evidence that can fence the exact admitted basis."""

        if (self.open_epoch is not None) != (self.basis == "open"):
            raise ValueError("invalid open authority evidence")
        if (self.admin_revision is not None) != (self.basis == "admin"):
            raise ValueError("invalid admin authority evidence")
        if (self.default_permission_revision is not None) != (self.basis == "default") or (
            bool(self.default_permissions) != (self.basis == "default")
            or not set(self.default_permissions).issubset(self.permissions)
        ):
            raise ValueError("invalid default authority evidence")
        if self.default_fallback_revision is not None and (
            self.basis != "default" or self.actor.kind != "credential"
        ):
            raise ValueError("invalid principal fallback evidence")
        if self.basis == "admin" and self.actor.kind != "credential":
            raise ValueError("an enrolled admin key is required")
        if self.basis == "scoped" and self.actor.kind not in {"credential", "mail"}:
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
