"""Verify generation-bound caller authority and manage live gateway enrollment."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import secrets
import threading
import time

from houmao.gateway._access_sshsig import (
    MAX_SIGNATURE_HEADER as MAX_SIGNATURE_HEADER,
    SSHSIG_NAMESPACE as SSHSIG_NAMESPACE,
    public_key_text as public_key_text,
    sign_sshsig as sign_sshsig,
    sshsig_header as sshsig_header,
    verify_sshsig,
)
from houmao.gateway._access_storage import (
    GatewayAccessError as GatewayAccessError,
    GatewayAccessStore as GatewayAccessStore,
    load_gateway_signer as load_gateway_signer,
    read_private_access_file as read_private_access_file,
)
from houmao.gateway.access_models import (
    AccessClass as AccessClass,
    AdminMode as AdminMode,
    CHALLENGE_HEADER as CHALLENGE_HEADER,
    MAX_ACCESS_DOCUMENT as MAX_ACCESS_DOCUMENT,
    MAX_ADMIN_KEYS,
    SIGNATURE_HEADER as SIGNATURE_HEADER,
    GatewayAdminEnrollment,
    GatewayAdminKey as GatewayAdminKey,
    GatewayAdminState as GatewayAdminState,
    GatewayChallenge as GatewayChallenge,
    GatewayChallengeRequest as GatewayChallengeRequest,
    GatewayClientBinding as GatewayClientBinding,
    GatewayGrant as GatewayGrant,
    GatewayLaunchSeed as GatewayLaunchSeed,
    GatewayOwner as GatewayOwner,
    GatewayRequestBinding as GatewayRequestBinding,
    GatewaySelfKey as GatewaySelfKey,
    GatewayTarget as GatewayTarget,
    ProofPurpose as ProofPurpose,
    parse_access_document as parse_access_document,
    validate_gateway_base_url as validate_gateway_base_url,
)

CHALLENGE_LIFETIME_SECONDS = 30
_CHALLENGE_CAPACITY = 1024
_REGISTRATION_ROUTE = ("POST", "/v1/admin/keys")


@dataclass(frozen=True)
class _PendingChallenge:
    """Retain its local expiry independently of the issuer's wall clock."""

    challenge: GatewayChallenge
    deadline: float


class GatewayAccessPolicy:
    """Enforce one access policy for a specific ingress and managed owner."""

    def __init__(
        self,
        *,
        store: GatewayAccessStore,
        target: Callable[[], GatewayTarget],
        current_self: Callable[[], GatewaySelfKey | None],
    ) -> None:
        """Bind policy to owner-side authority lookups supplied by the ingress."""

        self.m_store: GatewayAccessStore = store
        self.m_target: Callable[[], GatewayTarget] = target
        self.m_self: Callable[[], GatewaySelfKey | None] = current_self
        self.m_challenges: dict[str, _PendingChallenge] = {}
        self.m_challenge_lock: threading.Lock = threading.Lock()

    @property
    def store(self) -> GatewayAccessStore:
        """Return the retained authority for this ingress."""

        return self.m_store

    def issue(self, issuer: str, request: GatewayChallengeRequest) -> GatewayChallenge:
        """Issue one bounded challenge for a validated ingress and request binding."""

        with self.m_store.read_locked() as state:
            target = self._current_target()
            key_id = request.key_id
            generation_id = None
            revision: int | None = state.revision
            if request.purpose == "self":
                binding = self._current_self(state.owner)
                if binding is None:
                    raise GatewayAccessError(401, "invalid_proof")
                generation_id = binding.generation_id
                key_id = binding.key_id
                revision = None
            elif request.purpose == "register":
                candidate = request.proposed_key
                if (
                    candidate is None
                    or _REGISTRATION_ROUTE != (request.request.method, request.request.path)
                    or request.request.query
                ):
                    raise GatewayAccessError(401, "invalid_proof")
                if state.mode != "open":
                    raise GatewayAccessError(409, "enrollment_conflict")
                key_id = candidate.key_id
            elif key_id is None or state.find(key_id) is None:
                raise GatewayAccessError(401, "invalid_proof")

            with self.m_challenge_lock:
                now = time.monotonic()
                self.m_challenges = {
                    key: pending
                    for key, pending in self.m_challenges.items()
                    if pending.deadline > now
                }
                if len(self.m_challenges) >= _CHALLENGE_CAPACITY:
                    raise GatewayAccessError(429, "challenge_capacity")
                challenge = GatewayChallenge(
                    challenge_id=secrets.token_urlsafe(32),
                    issuer=issuer,
                    target=target,
                    purpose=request.purpose,
                    request=request.request,
                    key_id=key_id,
                    expires_at=int(time.time()) + CHALLENGE_LIFETIME_SECONDS,
                    generation_id=generation_id,
                    revision=revision,
                    proposed_key=request.proposed_key,
                )
                self.m_challenges[challenge.challenge_id] = _PendingChallenge(
                    challenge, now + CHALLENGE_LIFETIME_SECONDS
                )
                return challenge

    def admit(
        self,
        access: AccessClass,
        *,
        issuer: str,
        request: GatewayRequestBinding,
        challenge_id: str | None = None,
        signature: str | None = None,
        registration: bool = False,
    ) -> GatewayGrant:
        """Consume one proof or apply the current unsigned admission rule."""

        if access == "public" and challenge_id is None and signature is None:
            return GatewayGrant(role="public", target=self._current_target())
        with self.m_store.read_locked() as state:
            target = self._current_target()
            if challenge_id is None and signature is None:
                if access == "admin" and state.mode == "open" and not registration:
                    return GatewayGrant(role="anonymous", target=target, revision=state.revision)
                raise GatewayAccessError(401, "proof_required")
            if challenge_id is None or signature is None:
                raise GatewayAccessError(401, "invalid_proof")
            challenge = self._consume(challenge_id, signature)
            if (challenge.issuer, challenge.target, challenge.request) != (issuer, target, request):
                raise GatewayAccessError(401, "invalid_proof")
            grant = self._verify(challenge, signature, state, registration=registration)
            if grant.role == "self" and access == "admin":
                if state.mode != "open" or registration:
                    raise GatewayAccessError(403, "insufficient_authority")
                # Self proof identifies the caller. The empty revision grants admin access.
                return grant.model_copy(update={"revision": state.revision})
            return grant

    def revalidate(self, grant: GatewayGrant) -> bool:
        """Check the current incarnation and the exact grant or open revision."""

        with self.m_store.read_locked() as state:
            if grant.target != self._current_target():
                return False
            if grant.role == "anonymous":
                return state.mode == "open" and grant.revision == state.revision
            if grant.role == "admin":
                return self._same_enrollment(grant, state)
            if grant.role == "self":
                binding = self._current_self(state.owner)
                return (
                    binding is not None
                    and (binding.key_id, binding.generation_id, binding.owner.agent_id)
                    == (grant.key_id, grant.generation_id, grant.principal)
                    and (
                        grant.revision is None
                        or (state.mode == "open" and grant.revision == state.revision)
                    )
                )
            return False

    def add_key(self, grant: GatewayGrant, key: GatewayAdminKey) -> GatewayAdminKey:
        """Commit the first-key or listed-admin addition against current owner state."""

        def update(state: GatewayAdminState) -> GatewayAdminState:
            """Recheck the admitted mutation against live revision and enrollment."""

            if grant.role == "register":
                if grant.proposed_key != key:
                    raise GatewayAccessError(401, "invalid_proof")
                if (
                    grant.target != self._current_target()
                    or state.mode != "open"
                    or grant.revision != state.revision
                ):
                    raise GatewayAccessError(409, "enrollment_conflict")
            else:
                self._require_current_admin(grant, state)
            if len(state.keys) >= MAX_ADMIN_KEYS or state.find(key.key_id) is not None:
                raise GatewayAccessError(409, "enrollment_conflict")
            revision = state.revision + 1
            return GatewayAdminState(
                owner=state.owner,
                revision=revision,
                keys=(*state.keys, GatewayAdminEnrollment(key=key, enrollment=revision)),
            )

        self.m_store.update(update)
        return key

    def remove_key(self, grant: GatewayGrant, key_id: str) -> None:
        """Commit revocation by a currently granted admin, including of its own key."""

        def update(state: GatewayAdminState) -> GatewayAdminState:
            """Recheck the current grant and revoke the selected membership."""

            self._require_current_admin(grant, state)
            keys = tuple(entry for entry in state.keys if entry.key_id != key_id)
            if len(keys) == len(state.keys):
                raise GatewayAccessError(404, "unknown_key")
            return GatewayAdminState(owner=state.owner, revision=state.revision + 1, keys=keys)

        self.m_store.update(update)

    def _consume(self, challenge_id: str, proof: str) -> GatewayChallenge:
        """Remove a bounded challenge so concurrent attempts cannot both use it."""

        if len(challenge_id) != 43 or not 1 <= len(proof) <= MAX_SIGNATURE_HEADER:
            raise GatewayAccessError(401, "invalid_proof")
        with self.m_challenge_lock:
            pending = self.m_challenges.pop(challenge_id, None)
            if pending is None or pending.deadline <= time.monotonic():
                raise GatewayAccessError(401, "invalid_proof")
        return pending.challenge

    def _current_target(self) -> GatewayTarget:
        """Check that the ingress's current target still has the configured owner."""

        try:
            target = self.m_target()
        except GatewayAccessError:
            raise
        except (OSError, ValueError, RuntimeError):
            raise GatewayAccessError(503, "policy_unavailable") from None
        if target.owner != self.m_store.owner:
            raise GatewayAccessError(503, "policy_unavailable")
        return target

    def _current_self(self, owner: GatewayOwner) -> GatewaySelfKey | None:
        """Read current-generation authority from the ingress's managed-state lookup."""

        try:
            binding = self.m_self()
        except GatewayAccessError:
            raise
        except (OSError, ValueError, RuntimeError):
            raise GatewayAccessError(503, "policy_unavailable") from None
        if binding is not None and binding.owner != owner:
            raise GatewayAccessError(503, "policy_unavailable")
        return binding

    def _verify(
        self,
        challenge: GatewayChallenge,
        signature: str,
        state: GatewayAdminState,
        *,
        registration: bool,
    ) -> GatewayGrant:
        """Select the current verification key and establish caller provenance."""

        generation_id = None
        enrollment = None
        candidate = challenge.proposed_key
        if challenge.purpose == "register":
            if not registration or candidate is None:
                raise GatewayAccessError(401, "invalid_proof")
            principal, public_key = candidate.principal, candidate.public_key
        elif challenge.purpose == "self":
            binding = self._current_self(state.owner)
            if binding is None or (challenge.key_id, challenge.generation_id) != (
                binding.key_id,
                binding.generation_id,
            ):
                raise GatewayAccessError(401, "invalid_proof")
            generation_id = binding.generation_id
            principal, public_key = binding.owner.agent_id, binding.public_key
        else:
            entry = state.find(challenge.key_id)
            if entry is None or state.revision != challenge.revision:
                raise GatewayAccessError(401, "invalid_proof")
            enrollment = entry.enrollment
            principal, public_key = entry.key.principal, entry.key.public_key
        if not verify_sshsig(public_key, challenge.signing_bytes(), signature):
            raise GatewayAccessError(401, "invalid_proof")
        if challenge.purpose == "register" and (
            state.mode != "open" or challenge.revision != state.revision
        ):
            raise GatewayAccessError(409, "enrollment_conflict")
        return GatewayGrant(
            role=challenge.purpose,
            target=challenge.target,
            principal=principal,
            key_id=challenge.key_id,
            generation_id=generation_id,
            revision=challenge.revision,
            enrollment=enrollment,
            proposed_key=candidate,
        )

    def _require_current_admin(self, grant: GatewayGrant, state: GatewayAdminState) -> None:
        """Recheck authority against the same state used by a membership commit."""

        if grant.role != "admin":
            raise GatewayAccessError(403, "insufficient_authority")
        if (
            grant.target != self._current_target()
            or grant.revision != state.revision
            or not self._same_enrollment(grant, state)
        ):
            raise GatewayAccessError(409, "enrollment_conflict")

    @staticmethod
    def _same_enrollment(grant: GatewayGrant, state: GatewayAdminState) -> bool:
        """Compare the key's current enrollment and principal with a verified grant."""

        entry = state.find(grant.key_id) if grant.key_id is not None else None
        return entry is not None and (entry.enrollment, entry.key.principal) == (
            grant.enrollment,
            grant.principal,
        )
