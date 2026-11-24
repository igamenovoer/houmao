"""Verify one-use SSHSIG proofs for an exact owner ingress and operation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import secrets
import threading
import time

from houmao.gateway._access_sshsig import MAX_SIGNATURE_HEADER, verify_sshsig
from houmao.gateway._access_storage import GatewayAccessError
from houmao.gateway.access_models import (
    GatewayAdminKey,
    GatewayChallenge,
    GatewayChallengeRequest,
    GatewayRequestBinding,
    GatewaySelfKey,
    GatewayTarget,
)
from houmao.gateway.authorization_models import AuthorizationActor, PolicySnapshot
from houmao.gateway.authorization_store import AuthorizationStore

CHALLENGE_LIFETIME_SECONDS = 30
_CHALLENGE_CAPACITY = 1024
_REGISTRATION_ROUTE = ("POST", "/v1/admin/keys")


@dataclass(frozen=True)
class FirstEnrollment:
    """Record proof for the proposed key under the exact empty roster."""

    target: GatewayTarget
    listener_id: str
    policy_id: str
    roster_revision: int
    key: GatewayAdminKey


@dataclass(frozen=True)
class _PendingChallenge:
    """Retain issuer proof and a monotonic deadline."""

    challenge: GatewayChallenge
    deadline: float


class CallerProofs:
    """Establish identity and preserve enrollment evidence separately from permissions."""

    def __init__(
        self,
        *,
        store: AuthorizationStore,
        target: Callable[[], GatewayTarget],
        current_self: Callable[[], GatewaySelfKey | None],
        listener_id: str,
    ) -> None:
        """Bind transient challenges to one ingress and a retained owner policy."""

        self.m_store: AuthorizationStore = store
        self.m_target: Callable[[], GatewayTarget] = target
        self.m_current_self: Callable[[], GatewaySelfKey | None] = current_self
        self.m_listener_id: str = listener_id
        self.m_challenges: dict[str, _PendingChallenge] = {}
        self.m_lock: threading.Lock = threading.Lock()

    def issue(self, issuer: str, payload: GatewayChallengeRequest) -> GatewayChallenge:
        """Identify the current credential and issue one bounded challenge."""

        target = self.target()
        state = self.m_store.snapshot()
        candidate = payload.proposed_key
        generation_id = None
        enrollment_id = None
        revision = None
        if candidate is not None:
            if (
                payload.request.method,
                payload.request.path,
            ) != _REGISTRATION_ROUTE or payload.request.query:
                raise GatewayAccessError(401, "invalid_proof")
            if state.admin_mode != "open":
                raise GatewayAccessError(409, "enrollment_conflict")
            key_id = candidate.key_id
            revision = state.roster_revision
        else:
            assert payload.key_id is not None
            key_id = payload.key_id
            key = state.find_credential(key_id)
            if key is not None:
                enrollment_id = key.enrollment_id
            else:
                binding = self._self(target, key_id)
                generation_id = binding.generation_id
        challenge = GatewayChallenge(
            challenge_id=secrets.token_urlsafe(32),
            issuer=issuer,
            target=target,
            listener_id=self.m_listener_id,
            purpose=payload.purpose,
            request=payload.request,
            expires_at=int(time.time()) + CHALLENGE_LIFETIME_SECONDS,
            key_id=key_id,
            generation_id=generation_id,
            enrollment_id=enrollment_id,
            policy_id=state.policy_id,
            revision=revision,
            proposed_key=candidate,
        )
        with self.m_lock:
            now = time.monotonic()
            self.m_challenges = {
                key: pending for key, pending in self.m_challenges.items() if pending.deadline > now
            }
            if len(self.m_challenges) >= _CHALLENGE_CAPACITY:
                raise GatewayAccessError(429, "challenge_capacity")
            self.m_challenges[challenge.challenge_id] = _PendingChallenge(
                challenge, now + CHALLENGE_LIFETIME_SECONDS
            )
        return challenge

    def verify(
        self,
        issuer: str,
        request: GatewayRequestBinding,
        challenge_id: str | None,
        signature: str | None,
        *,
        registration: bool = False,
    ) -> AuthorizationActor | FirstEnrollment:
        """Consume the proof before using it for this request's authorization."""

        if challenge_id is None or signature is None:
            raise GatewayAccessError(401, "invalid_proof")
        challenge = self._consume(challenge_id, signature)
        target = self.target()
        if (
            challenge.target != target
            or challenge.issuer != issuer
            or challenge.request != request
            or challenge.listener_id != self.m_listener_id
        ):
            raise GatewayAccessError(401, "invalid_proof")
        state = self.m_store.snapshot()
        if challenge.policy_id != state.policy_id:
            raise GatewayAccessError(401, "invalid_proof")
        candidate = challenge.proposed_key
        if candidate is not None:
            if not registration or not self._valid(candidate.public_key, challenge, signature):
                raise GatewayAccessError(401, "invalid_proof")
            if state.admin_mode != "open" or state.roster_revision != challenge.revision:
                raise GatewayAccessError(409, "enrollment_conflict")
            return FirstEnrollment(
                target, self.m_listener_id, state.policy_id, state.roster_revision, candidate
            )
        return self._caller(challenge, signature, state)

    def target(self) -> GatewayTarget:
        """Resolve current authority and verify its precise owner domain."""

        target = self.m_target()
        if target.owner != self.m_store.owner:
            raise GatewayAccessError(503, "policy_unavailable")
        return target

    def _caller(
        self, challenge: GatewayChallenge, signature: str, state: PolicySnapshot
    ) -> AuthorizationActor:
        """Require the current enrollment or managed self generation named by proof."""

        if challenge.generation_id is not None:
            binding = self._self(challenge.target, challenge.key_id)
            if binding.generation_id != challenge.generation_id or not self._valid(
                binding.public_key, challenge, signature
            ):
                raise GatewayAccessError(401, "invalid_proof")
            return AuthorizationActor.from_self(binding)
        enrolled = state.find_credential(challenge.key_id)
        if (
            enrolled is None
            or enrolled.enrollment_id != challenge.enrollment_id
            or not self._valid(enrolled.public_key, challenge, signature)
        ):
            raise GatewayAccessError(401, "invalid_proof")
        return AuthorizationActor.from_credential(enrolled)

    def _self(self, target: GatewayTarget, key_id: str) -> GatewaySelfKey:
        """Resolve only same-target self without looking up enrolled peers."""

        binding = self.m_current_self()
        if (
            binding is None
            or binding.owner != target.owner
            or binding.generation_id != target.incarnation
            or binding.key_id != key_id
        ):
            raise GatewayAccessError(401, "invalid_proof")
        return binding

    def _consume(self, challenge_id: str, signature: str) -> GatewayChallenge:
        """Remove the challenge before any subsequent verification or effect."""

        if len(challenge_id) != 43 or not 1 <= len(signature) <= MAX_SIGNATURE_HEADER:
            raise GatewayAccessError(401, "invalid_proof")
        with self.m_lock:
            pending = self.m_challenges.pop(challenge_id, None)
        if pending is None or pending.deadline <= time.monotonic():
            raise GatewayAccessError(401, "invalid_proof")
        return pending.challenge

    @staticmethod
    def _valid(public_key: str, challenge: GatewayChallenge, signature: str) -> bool:
        """Verify the signature over the canonical wire document."""

        return verify_sshsig(public_key, challenge.signing_bytes(), signature)
