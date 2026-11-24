"""Evaluate exact gateway operations and fence authorization at handoff."""

from __future__ import annotations

from collections.abc import Callable, Iterable
import json
import time
from typing import Protocol, cast

import casbin  # type: ignore[import-untyped]

from houmao.gateway._access_storage import GatewayAccessError
from houmao.gateway.access_models import GatewaySelfKey, GatewayTarget
from houmao.gateway.authorization_models import (
    AuthorizationActor,
    AuthorizationBasis,
    AuthorizationDecision,
    Credential,
    Permission,
    PolicySnapshot,
)
from houmao.gateway.authorization_store import AuthorizationStore

_MODEL = """[request_definition]
r = sub, dom, obj, act
[policy_definition]
p = sub, dom, obj, act
[role_definition]
g = _, _, _
[policy_effect]
e = some(where (p.eft == allow))
[matchers]
m = r.dom == p.dom && r.obj == p.obj && r.act == p.act && (r.sub == p.sub || g(r.sub, p.sub, r.dom))
"""
_ADMIN = "builtin:gateway-admin"
_PUBLIC = "builtin:public"
_SELF = "builtin:self"


class _Enforcer(Protocol):
    """Describe the in-memory PyCasbin interface used by the fixed model."""

    def add_policies(self, rules: list[list[str]]) -> bool:
        """Add explicit permission rows."""

    def add_grouping_policies(self, rules: list[list[str]]) -> bool:
        """Add scoped role assignments."""

    def enforce(self, subject: str, domain: str, resource: str, action: str) -> bool:
        """Evaluate a single exact permission."""


class GatewayAuthorizer:
    """Build and evaluate a current authorization snapshot for one target domain."""

    def __init__(
        self,
        store: AuthorizationStore,
        *,
        catalog: Iterable[Permission] | Callable[[], Iterable[Permission]],
        public_permissions: Iterable[Permission] = (),
        self_permissions: Iterable[Permission] = (),
        supports: Callable[[Permission], bool] | None = None,
        supports_self: Callable[[Permission], bool] | None = None,
    ) -> None:
        """Select supported client operations and host-controlled public and self access."""

        self.m_store: AuthorizationStore = store
        self.m_catalog: Iterable[Permission] | Callable[[], Iterable[Permission]] = (
            catalog if callable(catalog) else frozenset(catalog)
        )
        self.m_public_permissions: frozenset[Permission] = frozenset(public_permissions)
        self.m_self_permissions: frozenset[Permission] = frozenset(self_permissions)
        self.m_supports: Callable[[Permission], bool] | None = supports
        self.m_supports_self: Callable[[Permission], bool] | None = supports_self
        self.m_domain: str = json.dumps([store.owner.agent_id, store.owner.context_id])

    def authorize(
        self,
        actor: AuthorizationActor,
        permissions: Iterable[Permission],
        *,
        target: GatewayTarget,
        listener_id: str,
        current_self: GatewaySelfKey | None = None,
    ) -> AuthorizationDecision:
        """Authorize all effects of one operation under the latest committed policy."""

        return self.authorize_snapshot(
            self.m_store.snapshot(),
            actor,
            permissions,
            target=target,
            listener_id=listener_id,
            current_self=current_self,
        )

    def authorize_snapshot(
        self,
        snapshot: PolicySnapshot,
        actor: AuthorizationActor,
        permissions: Iterable[Permission],
        *,
        target: GatewayTarget,
        listener_id: str,
        current_self: GatewaySelfKey | None = None,
    ) -> AuthorizationDecision:
        """Apply an already-read owner snapshot for atomic ingress decisions."""

        self._require_owner(snapshot, target)
        credential = _require_actor(snapshot, actor, target, current_self)
        required = self._require_supported(permissions)
        basis = self._admit_basis(snapshot, actor, credential, required)
        return AuthorizationDecision(
            actor=actor,
            target=target,
            listener_id=listener_id,
            permissions=required,
            basis=basis,
            policy_id=snapshot.policy_id,
            policy_revision=snapshot.revision,
            open_epoch=snapshot.open_epoch if basis == "open" else None,
            admin_revision=credential.admin_revision if basis == "admin" and credential else None,
        )

    def revalidate(
        self,
        decision: AuthorizationDecision,
        *,
        target: GatewayTarget,
        listener_id: str,
        current_self: GatewaySelfKey | None = None,
    ) -> bool:
        """Recheck the admitted basis for a read or continuing disclosure."""

        try:
            self.require_current(
                self.m_store.snapshot(),
                decision,
                target=target,
                listener_id=listener_id,
                current_self=current_self,
            )
        except GatewayAccessError as error:
            if error.status_code == 503:
                raise
            return False
        return True

    def require_current(
        self,
        snapshot: PolicySnapshot,
        decision: AuthorizationDecision,
        *,
        target: GatewayTarget,
        listener_id: str,
        current_self: GatewaySelfKey | None = None,
    ) -> AuthorizationDecision:
        """Recheck the exact admitted basis inside an owner transaction or read."""

        self._require_owner(snapshot, target)
        if (
            decision.target != target
            or decision.listener_id != listener_id
            or decision.policy_id != snapshot.policy_id
            or decision.policy_revision > snapshot.revision
        ):
            raise GatewayAccessError(409, "authorization_target_conflict")
        actor = decision.actor
        credential = _require_actor(snapshot, actor, target, current_self)
        required = self._require_supported(decision.permissions)
        subject = _admitted_subject(snapshot, decision, credential)
        if not self._permits(snapshot, subject, required):
            raise GatewayAccessError(403, "insufficient_authority")
        return decision.model_copy(update={"policy_revision": snapshot.revision})

    def handoff(
        self,
        decision: AuthorizationDecision,
        *,
        operation_id: str,
        target: GatewayTarget,
        listener_id: str,
        current_self: GatewaySelfKey | None = None,
    ) -> AuthorizationDecision:
        """Order one exact mutation admission against concurrent policy updates."""

        with self.m_store.transaction() as transaction:
            current = self.require_current(
                transaction.snapshot,
                decision,
                target=target,
                listener_id=listener_id,
                current_self=current_self,
            )
            transaction.record_handoff(operation_id, current)
            return current

    def _require_owner(self, snapshot: PolicySnapshot, target: GatewayTarget) -> None:
        """Prevent a different target, context, or snapshot from crossing this domain."""

        if snapshot.owner != self.m_store.owner or target.owner != snapshot.owner:
            raise GatewayAccessError(403, "insufficient_authority")

    def _require_supported(self, permissions: Iterable[Permission]) -> tuple[Permission, ...]:
        """Allow only declared exact operations or host-validated concrete resources."""

        required = tuple(dict.fromkeys(permissions))
        if not 1 <= len(required) <= 64:
            raise GatewayAccessError(403, "insufficient_authority")
        try:
            catalog = set(self.m_catalog() if callable(self.m_catalog) else self.m_catalog)
            unsupported = any(
                permission not in catalog
                and (self.m_supports is None or not self.m_supports(permission))
                for permission in required
            )
        except GatewayAccessError:
            raise
        except Exception:
            raise GatewayAccessError(503, "policy_unavailable") from None
        if unsupported:
            raise GatewayAccessError(403, "insufficient_authority")
        return required

    def _admit_basis(
        self,
        snapshot: PolicySnapshot,
        actor: AuthorizationActor,
        credential: Credential | None,
        permissions: tuple[Permission, ...],
    ) -> AuthorizationBasis:
        """Choose an attributable basis and preserve it across subsequent checks."""

        if all(permission in self.m_public_permissions for permission in permissions):
            basis: AuthorizationBasis = "public"
            subject = _PUBLIC
        elif snapshot.admin_mode == "open":
            basis, subject = "open", _ADMIN
        elif credential is not None and credential.admin_revision is not None:
            basis, subject = "admin", _ADMIN
        elif credential is not None:
            basis, subject = "scoped", _principal_subject(credential.principal_id)
        elif actor.kind == "self":
            basis, subject = "self", _SELF
        else:
            raise GatewayAccessError(401, "proof_required")
        if not self._permits(snapshot, subject, permissions):
            raise GatewayAccessError(403, "insufficient_authority")
        return basis

    def _permits(
        self, snapshot: PolicySnapshot, subject: str, permissions: tuple[Permission, ...]
    ) -> bool:
        """Evaluate the compound request with fresh, unexpired exact policy rows."""

        try:
            model = casbin.model.Model()
            model.load_model_from_text(_MODEL)
            enforcer = cast(_Enforcer, casbin.Enforcer(model))
            required = set(permissions)
            now = time.time()
            domain = self.m_domain
            policies = [
                [_ADMIN, domain, permission.resource, permission.action]
                for permission in permissions
            ]
            policies.extend(
                [_PUBLIC, domain, permission.resource, permission.action]
                for permission in permissions
                if permission in self.m_public_permissions
            )
            policies.extend(
                [_SELF, domain, permission.resource, permission.action]
                for permission in permissions
                if permission in self.m_self_permissions
                or (self.m_supports_self is not None and self.m_supports_self(permission))
            )
            policies.extend(
                [
                    _principal_subject(grant.principal_id),
                    domain,
                    permission.resource,
                    permission.action,
                ]
                for grant in snapshot.grants
                if (grant.expires_at is None or grant.expires_at > now)
                and (permission := grant.permission) in required
            )
            policies.extend(
                [_role_subject(role.role_id), domain, permission.resource, permission.action]
                for role in snapshot.roles
                for permission in role.permissions
                if permission in required
            )
            grouping = [[_SELF, _PUBLIC, domain]]
            grouping.extend(
                [_principal_subject(principal.principal_id), _PUBLIC, domain]
                for principal in snapshot.principals
            )
            grouping.extend(
                [
                    _principal_subject(assignment.principal_id),
                    _role_subject(assignment.role_id),
                    domain,
                ]
                for assignment in snapshot.role_assignments
                if assignment.expires_at is None or assignment.expires_at > now
            )
            if not enforcer.add_policies(policies) or not enforcer.add_grouping_policies(grouping):
                raise ValueError("invalid authorization policy rows")
            return all(
                enforcer.enforce(subject, domain, permission.resource, permission.action)
                for permission in permissions
            )
        except GatewayAccessError:
            raise
        except Exception:
            raise GatewayAccessError(503, "policy_unavailable") from None


def _require_actor(
    snapshot: PolicySnapshot,
    actor: AuthorizationActor,
    target: GatewayTarget,
    current_self: GatewaySelfKey | None,
) -> Credential | None:
    """Reject revoked enrollment or a retired or foreign same-agent proof."""

    if actor.kind == "credential":
        assert actor.key_id is not None
        credential = snapshot.find_credential(actor.key_id)
        if credential is None or AuthorizationActor.from_credential(credential) != actor:
            raise GatewayAccessError(401, "invalid_proof")
        return credential
    if actor.kind == "self" and (
        current_self is None
        or current_self.owner != target.owner
        or current_self.generation_id != target.incarnation
        or AuthorizationActor.from_self(current_self) != actor
    ):
        raise GatewayAccessError(401, "invalid_proof")
    return None


def _admitted_subject(
    snapshot: PolicySnapshot, decision: AuthorizationDecision, credential: Credential | None
) -> str:
    """Do not promote an admitted operation to a different authorization basis."""

    match decision.basis:
        case "open":
            if snapshot.admin_mode != "open" or snapshot.open_epoch != decision.open_epoch:
                raise GatewayAccessError(403, "insufficient_authority")
            return _ADMIN
        case "admin":
            if credential is None or credential.admin_revision != decision.admin_revision:
                raise GatewayAccessError(403, "insufficient_authority")
            return _ADMIN
        case "scoped":
            assert credential is not None
            return _principal_subject(credential.principal_id)
        case "self":
            return _SELF
        case "public":
            return _PUBLIC


def _principal_subject(principal_id: str) -> str:
    """Separate stable principal identifiers from role and host identifiers."""

    return f"principal:{principal_id}"


def _role_subject(role_id: str) -> str:
    """Keep ordinary role assignments distinct from host-controlled subjects."""

    return f"role:{role_id}"
