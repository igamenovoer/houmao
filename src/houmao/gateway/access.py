"""Apply retained caller authorization to one live gateway or passive ingress."""

from __future__ import annotations

from collections.abc import Callable, Iterable
import hashlib
from typing import TypeAlias
from uuid import uuid4

from houmao.gateway._access_sshsig import (
    MAX_SIGNATURE_HEADER as MAX_SIGNATURE_HEADER,
    SSHSIG_NAMESPACE as SSHSIG_NAMESPACE,
    WEB_LOGIN_NAMESPACE,
    public_key_text as public_key_text,
    sign_sshsig as sign_sshsig,
    sshsig_header as sshsig_header,
    sshsig_key_id,
    verify_sshsig,
)
from houmao.gateway._access_storage import (
    GatewayAccessError as GatewayAccessError,
    GatewayAccessStore as GatewayAccessStore,
    load_gateway_signer as load_gateway_signer,
    read_private_access_file as read_private_access_file,
)
from houmao.gateway.access_models import (
    CHALLENGE_HEADER as CHALLENGE_HEADER,
    MAX_ACCESS_DOCUMENT as MAX_ACCESS_DOCUMENT,
    MAX_ADMIN_KEYS as MAX_ADMIN_KEYS,
    SIGNATURE_HEADER as SIGNATURE_HEADER,
    GatewayAdminKey as GatewayAdminKey,
    GatewayChallenge as GatewayChallenge,
    GatewayChallengeRequest as GatewayChallengeRequest,
    GatewayClientBinding as GatewayClientBinding,
    GatewayLaunchSeed as GatewayLaunchSeed,
    GatewayOwner as GatewayOwner,
    GatewayRequestBinding as GatewayRequestBinding,
    GatewaySelfKey as GatewaySelfKey,
    GatewayTarget as GatewayTarget,
    ProofPurpose as ProofPurpose,
    parse_access_document as parse_access_document,
    validate_gateway_base_url as validate_gateway_base_url,
)
from houmao.gateway.authorization import GatewayAuthorizer
from houmao.gateway.authorization_models import (
    AuthorizationActor,
    AuthorizationDecision,
    Permission,
    PolicySnapshot,
)
from houmao.gateway.authorization_store import AuthorizationStore
from houmao.gateway.caller_proof import (
    CHALLENGE_LIFETIME_SECONDS as CHALLENGE_LIFETIME_SECONDS,
    CallerProofs,
    FirstEnrollment as FirstEnrollment,
)
from houmao.gateway.operations import (
    ADMIN_ADD,
    ADMIN_REMOVE,
    CORE_PERMISSIONS,
    PUBLIC_INPUT_PERMISSIONS,
    SELF_PERMISSIONS,
    WEB_ENTRY,
    supports_mail_permission,
    supports_self_mail_permission,
)
from houmao.gateway.roster import add_admin_key, remove_admin_key

GatewayGrant: TypeAlias = AuthorizationDecision


class GatewayAccessPolicy:
    """Coordinate exact proof, semantic policy decisions, and current handoffs."""

    def __init__(
        self,
        *,
        store: AuthorizationStore,
        target: Callable[[], GatewayTarget],
        current_self: Callable[[], GatewaySelfKey | None],
        listener_id: str,
        catalog: Callable[[], Iterable[Permission]] | None = None,
        supports: Callable[[Permission], bool] | None = None,
    ) -> None:
        """Bind one transient listener to retained owner authorization."""

        self.m_store: AuthorizationStore = store
        self.m_listener_id: str = listener_id
        self.m_self: Callable[[], GatewaySelfKey | None] = current_self
        self.m_proofs: CallerProofs = CallerProofs(
            store=store, target=target, current_self=current_self, listener_id=listener_id
        )
        self.m_authorizer: GatewayAuthorizer = GatewayAuthorizer(
            store,
            catalog=(
                (lambda: CORE_PERMISSIONS.union(catalog()))
                if catalog is not None
                else CORE_PERMISSIONS
            ),
            public_permissions=PUBLIC_INPUT_PERMISSIONS,
            self_permissions=SELF_PERMISSIONS,
            supports=(
                (lambda permission: supports_mail_permission(permission) or supports(permission))
                if supports is not None
                else supports_mail_permission
            ),
            supports_self=supports_self_mail_permission,
        )

    @property
    def store(self) -> AuthorizationStore:
        """Return retained policy selected by this ingress."""

        return self.m_store

    @property
    def listener_id(self) -> str:
        """Return the issuer identity bound into each proof and decision."""

        return self.m_listener_id

    def issue(self, issuer: str, request: GatewayChallengeRequest) -> GatewayChallenge:
        """Issue one bounded proof challenge for enrolled or managed self credentials."""

        return self.m_proofs.issue(issuer, request)

    def admit(
        self,
        permissions: Iterable[Permission] | Callable[[], Iterable[Permission]],
        *,
        issuer: str,
        request: GatewayRequestBinding,
        challenge_id: str | None = None,
        signature: str | None = None,
        registration: bool = False,
    ) -> GatewayGrant | FirstEnrollment:
        """Verify any supplied proof before selecting its exact allowed effects."""

        actor = (
            self.m_proofs.verify(
                issuer, request, challenge_id, signature, registration=registration
            )
            if challenge_id is not None or signature is not None
            else AuthorizationActor(kind="anonymous")
        )
        if isinstance(actor, FirstEnrollment):
            return actor
        if (
            callable(permissions)
            and actor.kind == "anonymous"
            and self.m_store.snapshot().admin_mode == "keyed"
        ):
            raise GatewayAccessError(401, "proof_required")
        operation = permissions() if callable(permissions) else permissions
        return self.authorize(actor, operation)

    def verify_public_request(
        self,
        *,
        issuer: str,
        request: GatewayRequestBinding,
        challenge_id: str | None,
        signature: str | None,
    ) -> None:
        """Reject invalid explicit proof even on an otherwise public transport route."""

        self.m_proofs.verify(issuer, request, challenge_id, signature)

    def authenticate(
        self,
        *,
        issuer: str,
        request: GatewayRequestBinding,
        challenge_id: str | None,
        signature: str | None,
    ) -> AuthorizationActor:
        """Authenticate a caller before a handler selects its resolved resource."""

        if challenge_id is None and signature is None:
            if self.m_store.snapshot().admin_mode == "keyed":
                raise GatewayAccessError(401, "proof_required")
            return AuthorizationActor(kind="anonymous")
        actor = self.m_proofs.verify(issuer, request, challenge_id, signature)
        if not isinstance(actor, AuthorizationActor):
            raise GatewayAccessError(401, "invalid_proof")
        return actor

    def authorize(
        self, actor: AuthorizationActor, permissions: Iterable[Permission]
    ) -> GatewayGrant:
        """Evaluate a verified actor on the current retained policy."""

        return self.m_authorizer.authorize(
            actor,
            permissions,
            target=self.m_proofs.target(),
            listener_id=self.m_listener_id,
            current_self=self._self_for(actor),
        )

    def revalidate(self, grant: GatewayGrant) -> bool:
        """Check exact currently bound authority before protected disclosure."""

        return self.m_authorizer.revalidate(
            grant,
            target=self.m_proofs.target(),
            listener_id=self.m_listener_id,
            current_self=self._self_for(grant.actor),
        )

    def handoff(self, grant: GatewayGrant, *, operation_id: str | None = None) -> GatewayGrant:
        """Claim this exact effect in order with retained policy mutation."""

        return self.m_authorizer.handoff(
            grant,
            operation_id=(
                uuid4().hex
                if operation_id is None
                else "request:" + hashlib.sha256(operation_id.encode()).hexdigest()
            ),
            target=self.m_proofs.target(),
            listener_id=self.m_listener_id,
            current_self=self._self_for(grant.actor),
        )

    def verify_web_login(self, challenge: bytes, proofs: tuple[str, ...]) -> GatewayGrant:
        """Select a current enrolled signer that has Web entry permission."""

        state = self.m_store.snapshot()
        verified = False
        for proof in proofs:
            try:
                key_id = sshsig_key_id(proof)
            except ValueError:
                continue
            key = state.find_credential(key_id)
            if key is None or not verify_sshsig(
                key.public_key, challenge, proof, namespace=WEB_LOGIN_NAMESPACE
            ):
                continue
            verified = True
            try:
                return self.authorize(AuthorizationActor.from_credential(key), (WEB_ENTRY,))
            except GatewayAccessError as error:
                if error.status_code not in {401, 403}:
                    raise
        if verified:
            raise GatewayAccessError(403, "insufficient_authority")
        raise GatewayAccessError(401, "invalid_proof")

    def add_key(
        self, grant: GatewayGrant | FirstEnrollment, key: GatewayAdminKey
    ) -> GatewayAdminKey:
        """Commit first enrollment or a qualified administrator's roster update."""

        with self.m_store.transaction() as transaction:
            current = transaction.snapshot
            if isinstance(grant, FirstEnrollment):
                if grant.key != key:
                    raise GatewayAccessError(401, "invalid_proof")
                if (
                    grant.target != self.m_proofs.target()
                    or grant.listener_id != self.m_listener_id
                    or grant.policy_id != current.policy_id
                    or grant.roster_revision != current.roster_revision
                    or current.admin_mode != "open"
                ):
                    raise GatewayAccessError(409, "enrollment_conflict")
                actor = "bootstrap"
            else:
                actor = self._require_admin(current, grant, ADMIN_ADD)
            transaction.replace(add_admin_key(current, key), actor=actor, action=ADMIN_ADD.action)
        return key

    def remove_key(self, grant: GatewayGrant, key_id: str) -> None:
        """Revoke one live key's administrator qualification."""

        with self.m_store.transaction() as transaction:
            current = transaction.snapshot
            actor = self._require_admin(current, grant, ADMIN_REMOVE)
            transaction.replace(
                remove_admin_key(current, key_id), actor=actor, action=ADMIN_REMOVE.action
            )

    def _require_admin(
        self, state: PolicySnapshot, grant: GatewayGrant, permission: Permission
    ) -> str:
        """Require current per-key administration for live roster mutation."""

        if grant.basis == "open" and permission == ADMIN_ADD:
            raise GatewayAccessError(401, "first_enrollment_proof_required")
        if grant.basis != "admin" or permission not in grant.permissions:
            raise GatewayAccessError(403, "insufficient_authority")
        self.m_authorizer.require_current(
            state, grant, target=self.m_proofs.target(), listener_id=self.m_listener_id
        )
        assert grant.actor.principal_id is not None
        return grant.actor.principal_id

    def _self_for(self, actor: AuthorizationActor) -> GatewaySelfKey | None:
        """Look up generation authority only for proof between the same agent and target."""

        return self.m_self() if actor.kind == "self" else None
