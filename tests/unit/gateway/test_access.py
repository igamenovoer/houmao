"""Check owner storage, standard SSHSIG proofs, and live gateway admission."""

from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
import pytest

from houmao.gateway.access import (
    SSHSIG_NAMESPACE,
    GatewayAccessError,
    GatewayAccessPolicy,
    GatewayAccessStore,
    GatewayAdminKey,
    GatewayChallenge,
    GatewayChallengeRequest,
    GatewayClientBinding,
    GatewayGrant,
    GatewayLaunchSeed,
    GatewayOwner,
    GatewayRequestBinding,
    GatewayTarget,
    load_gateway_signer,
    parse_access_document,
    public_key_text,
    read_private_access_file,
    sign_sshsig,
    sshsig_header,
)
from houmao.gateway._access_sshsig import PrivateKey, verify_sshsig

ISSUER = "http://127.0.0.1:12345"
REQUEST = GatewayRequestBinding.from_request("GET", "/v1/status", "a=b&a=c", b"")
REGISTER = GatewayRequestBinding.from_request("POST", "/v1/admin/keys", "", b"exact input")


@dataclass
class _Authority:
    """Fixture-owned state for one active generation and one retained admin list."""

    store: GatewayAccessStore
    target: GatewayTarget

    def policy(self) -> GatewayAccessPolicy:
        """Create a new ingress that resolves this fixture's current generation."""

        return GatewayAccessPolicy(
            store=self.store,
            target=lambda: self.target,
            current_self=lambda: self.store.load_self(self.target.incarnation),
        )

    def self_signer(self) -> PrivateKey:
        """Select the current generation's explicit owner-local signing source."""

        return load_gateway_signer(self.store.self_signer_path(self.target.incarnation))


@pytest.fixture
def authority(tmp_path: Path) -> _Authority:
    """Provision active owner state under a private test root."""

    owner = GatewayOwner(agent_id="agent", context_id="context")
    store = GatewayAccessStore.from_root(tmp_path / "access", owner)
    store.initialize(GatewayLaunchSeed())
    store.provision_self("first")
    return _Authority(store=store, target=GatewayTarget(owner=owner, incarnation="first"))


def _admin(principal: str = "operator") -> tuple[GatewayAdminKey, PrivateKey]:
    """Generate a fixture admin's distinct verification and signing material."""

    signer = ed25519.Ed25519PrivateKey.generate()
    return GatewayAdminKey(
        principal=principal, public_key=public_key_text(signer.public_key())
    ), signer


def _proof(signer: PrivateKey, challenge: GatewayChallenge) -> dict[str, str]:
    """Encode a standard signature into the request's bounded proof values."""

    return {
        "challenge_id": challenge.challenge_id,
        "signature": sshsig_header(sign_sshsig(signer, challenge.signing_bytes())),
    }


def _registration(
    policy: GatewayAccessPolicy, key: GatewayAdminKey, signer: PrivateKey
) -> GatewayGrant:
    """Admit one registration against the currently recorded empty list."""

    challenge = policy.issue(
        ISSUER, GatewayChallengeRequest(purpose="register", request=REGISTER, proposed_key=key)
    )
    return policy.admit(
        "admin", issuer=ISSUER, request=REGISTER, registration=True, **_proof(signer, challenge)
    )


def _listed(
    policy: GatewayAccessPolicy,
    key: GatewayAdminKey,
    signer: PrivateKey,
    request: GatewayRequestBinding = REQUEST,
) -> GatewayGrant:
    """Admit an operation using one current admin enrollment."""

    challenge = policy.issue(
        ISSUER, GatewayChallengeRequest(purpose="admin", request=request, key_id=key.key_id)
    )
    return policy.admit("admin", issuer=ISSUER, request=request, **_proof(signer, challenge))


def test_seed_validates_canonical_keys_and_duplicate_fields() -> None:
    """Accept empty and multiple intentional seeds, rejecting ambiguous keys and fields."""

    first, _ = _admin()
    second, _ = _admin("other")
    assert parse_access_document(GatewayLaunchSeed, b"{}").admin_keys == ()
    payload = GatewayLaunchSeed(admin_keys=(first, second)).model_dump_json().encode()
    assert parse_access_document(GatewayLaunchSeed, payload).admin_keys == (first, second)
    commented = GatewayAdminKey(principal="different", public_key=first.public_key + " comment")
    assert commented.key_id == first.key_id
    with pytest.raises(ValueError, match="duplicate admin key"):
        GatewayLaunchSeed(admin_keys=(first, commented))
    with pytest.raises(ValueError, match="invalid access document"):
        parse_access_document(GatewayLaunchSeed, b'{"admin_keys":[],"admin_keys":[]}')
    nested = json.dumps(first.model_dump()).replace('"operator"', '"other","principal":"operator"')
    with pytest.raises(ValueError, match="invalid access document"):
        parse_access_document(GatewayLaunchSeed, ('{"admin_keys":[' + nested + "]}").encode())


@pytest.mark.parametrize("value", ["broken", "ssh-ed25519 !!!!", "ssh-rsa AAAAC3NzaC1lZDI1NTE5"])
def test_rejects_malformed_public_keys(value: str) -> None:
    """Reject malformed and mismatched wire formats before storing an admin seed."""

    with pytest.raises(ValueError, match="unsupported OpenSSH public key"):
        GatewayAdminKey(principal="operator", public_key=value)


def test_seed_applies_once_and_retained_state_survives_restart(tmp_path: Path) -> None:
    """Retain live membership and revisions independently of an ingress or first seed."""

    owner = GatewayOwner(agent_id="agent", context_id="context")
    root = tmp_path / "access"
    store = GatewayAccessStore.from_root(root, owner)
    first, first_signer = _admin()
    second, second_signer = _admin("other")
    seeded = store.initialize(GatewayLaunchSeed(admin_keys=(first, second)))
    assert seeded.mode == "key_required"
    restarted = GatewayAccessStore.from_root(root, owner)
    assert restarted.load() == seeded
    policy = GatewayAccessPolicy(
        store=restarted,
        target=lambda: GatewayTarget(owner=owner, incarnation="restart"),
        current_self=lambda: None,
    )
    with pytest.raises(GatewayAccessError) as denied:
        policy.admit("admin", issuer=ISSUER, request=REQUEST)
    assert denied.value.status_code == 401
    policy.remove_key(_listed(policy, second, second_signer), first.key_id)
    live = restarted.initialize(GatewayLaunchSeed(admin_keys=(first, second)))
    assert live.revision == 1
    assert [entry.key_id for entry in live.keys] == [second.key_id]
    with pytest.raises(GatewayAccessError):
        _listed(policy, first, first_signer)


@pytest.mark.parametrize(
    "damage", ["missing", "missing_directory", "corrupt", "other_owner", "mode"]
)
def test_initialized_damage_fails_closed(
    authority: _Authority, tmp_path: Path, damage: str
) -> None:
    """Never reset a known owner roster when its private source is unsafe or missing."""

    path = next((tmp_path / "access").glob("*/admin.json"))
    if damage == "missing":
        path.unlink()
    elif damage == "missing_directory":
        shutil.rmtree(path.parent)
    elif damage == "corrupt":
        path.write_bytes(b'{"revision":0,"revision":1}')
    elif damage == "other_owner":
        original = authority.store.load().model_dump()
        original["owner"]["context_id"] = "unrelated"
        path.write_text(json.dumps(original))
    else:
        path.chmod(0o640)
    for operation in (
        authority.store.load,
        lambda: authority.store.initialize(GatewayLaunchSeed()),
        lambda: authority.policy().admit("admin", issuer=ISSUER, request=REQUEST),
    ):
        with pytest.raises(GatewayAccessError) as unavailable:
            operation()
        assert unavailable.value.status_code == 503
        assert str(path) not in str(unavailable.value)


def test_private_source_rejects_shared_symlink_checkout_and_oversize(tmp_path: Path) -> None:
    """Refuse unsafe credential source types and private file locations."""

    key = tmp_path / "source"
    key.write_bytes(b"abcd")
    key.chmod(0o600)
    assert read_private_access_file(key, limit=4) == b"abcd"
    with pytest.raises(ValueError):
        read_private_access_file(key, limit=3)
    alias = tmp_path / "symlink"
    alias.symlink_to(key)
    with pytest.raises(ValueError):
        read_private_access_file(alias)
    hardlink = tmp_path / "hardlink"
    hardlink.hardlink_to(key)
    with pytest.raises(ValueError):
        read_private_access_file(hardlink)
    hardlink.unlink()
    key.chmod(0o644)
    with pytest.raises(ValueError):
        read_private_access_file(key)
    key.chmod(0o600)
    (tmp_path / ".git").mkdir()
    with pytest.raises(ValueError):
        read_private_access_file(key)


def test_private_source_allows_only_purpose_specific_checkout_tmp(tmp_path: Path) -> None:
    """Permit campaign scratch credentials without weakening other checkout boundaries."""

    repo = tmp_path / "repo"
    campaign = repo / "tmp" / "campaign"
    campaign.mkdir(parents=True)
    (repo / ".git").mkdir()
    key = campaign / "source"
    key.write_bytes(b"abcd")
    key.chmod(0o600)
    assert read_private_access_file(key, limit=4) == b"abcd"

    direct = repo / "tmp" / "source"
    direct.write_bytes(b"abcd")
    direct.chmod(0o600)
    with pytest.raises(ValueError):
        read_private_access_file(direct)

    (campaign / ".git").mkdir()
    with pytest.raises(ValueError):
        read_private_access_file(key)


@pytest.mark.parametrize(
    "base_url",
    [
        "http://gateway.example",
        "http://127.0.0.2",
        "https://invalid%2eexample",
        "https://user@example.test",
        "https://example.test:0",
        "https://example.test/a/%2e%2e/other",
        "https://example.test/a/%26%23",
        "https://example.test/a%3fb",
        "https://example.test/a%2Fb",
        "https://example.test/a?",
    ],
)
def test_invalid_client_binding(base_url: str, authority: _Authority) -> None:
    """Require a stable exact HTTPS endpoint or literal owner-local loopback URL."""

    with pytest.raises(ValueError) as denied:
        GatewayClientBinding(
            base_url=base_url,
            owner=authority.target.owner,
            purpose="admin",
            private_key_path="/fixture/private-signing-key",
        )
    assert "/fixture/private-signing-key" not in str(denied.value)


def test_self_key_is_per_generation_and_has_owner_private_source(
    authority: _Authority,
) -> None:
    """Preserve same-generation keys and reject an earlier or foreign signer."""

    policy = authority.policy()
    original = authority.store.load_self("first")
    assert authority.store.self_signer_path("first").stat().st_mode & 0o777 == 0o600
    assert authority.store.provision_self("first") == original
    signer = authority.self_signer()
    challenge_request = GatewayChallengeRequest(purpose="self", request=REQUEST)
    old_challenge = policy.issue(ISSUER, challenge_request)
    second = authority.store.provision_self("replacement")
    assert second.public_key != original.public_key
    authority.target = authority.target.model_copy(update={"incarnation": "replacement"})
    with pytest.raises(GatewayAccessError) as stale:
        policy.admit("private", issuer=ISSUER, request=REQUEST, **_proof(signer, old_challenge))
    assert stale.value.status_code == 401

    restarted = authority.policy()
    challenge = restarted.issue(ISSUER, challenge_request)
    with pytest.raises(GatewayAccessError):
        restarted.admit("private", issuer=ISSUER, request=REQUEST, **_proof(signer, challenge))
    challenge = restarted.issue(ISSUER, challenge_request)
    admitted = restarted.admit(
        "private", issuer=ISSUER, request=REQUEST, **_proof(authority.self_signer(), challenge)
    )
    assert admitted.role == "self"
    assert restarted.revalidate(admitted)


@pytest.mark.parametrize("kind", ["ed25519", "rsa", "ecdsa"])
def test_sshsig_in_process_framing(kind: str) -> None:
    """Sign supported algorithms and reject wrong keys, malformed framing, and namespace."""

    signer: PrivateKey
    if kind == "ed25519":
        signer = ed25519.Ed25519PrivateKey.generate()
    elif kind == "rsa":
        signer = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    else:
        signer = ec.generate_private_key(ec.SECP256R1())
    key = public_key_text(signer.public_key())
    message = b"bound input"
    proof = sshsig_header(sign_sshsig(signer, message))
    assert verify_sshsig(key, message, proof)
    assert not verify_sshsig(key, b"other input", proof)
    assert not verify_sshsig(_admin()[0].public_key, message, proof)
    assert not verify_sshsig(
        key, message, sshsig_header(sign_sshsig(signer, message, namespace="file"))
    )
    blob = base64.b64decode(proof)
    assert not verify_sshsig(key, message, base64.b64encode(blob + b"trailing").decode())
    assert not verify_sshsig(key, message, base64.b64encode(blob[:-1]).decode())
    assert not verify_sshsig(
        key, message, base64.b64encode(blob.replace(b"sha512", b"sha999")).decode()
    )
    if kind == "rsa":
        assert not verify_sshsig(
            key,
            message,
            base64.b64encode(blob.replace(b"rsa-sha2-512", b"rsa-sha2-999")).decode(),
        )
    assert not verify_sshsig(
        key, message, base64.b64encode(blob[:9] + b"\x02" + blob[10:]).decode()
    )
    assert not verify_sshsig(key, message, "A" * 10000)


@pytest.mark.parametrize("kind", ["ed25519", "rsa", "ecdsa"])
def test_sshsig_interoperates_with_stock_ssh_keygen(tmp_path: Path, kind: str) -> None:
    """Check SSHSIG in both directions against the system OpenSSH tool."""

    tool = shutil.which("ssh-keygen")
    if tool is None:
        pytest.skip("stock ssh-keygen is unavailable")
    private = tmp_path / "ssh-key"
    subprocess.run([tool, "-q", "-t", kind, "-N", "", "-f", str(private)], check=True)
    signer = load_gateway_signer(private)
    public = public_key_text(signer.public_key())
    message = tmp_path / "challenge"
    payload = b"bounded interoperability challenge"
    message.write_bytes(payload)
    subprocess.run(
        [
            tool,
            "-Y",
            "sign",
            "-f",
            str(private),
            "-n",
            SSHSIG_NAMESPACE,
            "-O",
            "hashalg=sha256",
            str(message),
        ],
        check=True,
        capture_output=True,
    )
    signature = message.with_suffix(".sig")
    assert verify_sshsig(public, payload, sshsig_header(signature.read_bytes()))
    signature.write_bytes(sign_sshsig(signer, payload))
    allowed = tmp_path / "allowed-signers"
    allowed.write_text(f"operator {public}\n")
    subprocess.run(
        [
            tool,
            "-Y",
            "verify",
            "-f",
            str(allowed),
            "-I",
            "operator",
            "-n",
            SSHSIG_NAMESPACE,
            "-s",
            str(signature),
        ],
        input=payload,
        check=True,
        capture_output=True,
    )


@pytest.mark.parametrize("change", ["method", "path", "query", "body_sha256", "issuer"])
def test_challenge_cannot_be_retargeted(
    authority: _Authority,
    change: str,
) -> None:
    """Reject a signature when any part of the original binding has changed."""

    policy = authority.policy()
    challenge = policy.issue(ISSUER, GatewayChallengeRequest(purpose="self", request=REQUEST))
    issuer = ISSUER
    request = REQUEST
    if change == "issuer":
        issuer = "http://127.0.0.1:12346"
    else:
        request = REQUEST.model_copy(
            update={
                change: {
                    "method": "POST",
                    "path": "/other",
                    "query": "b=c",
                    "body_sha256": "b" * 64,
                }[change]
            }
        )
    with pytest.raises(GatewayAccessError) as mismatched:
        policy.admit(
            "private", issuer=issuer, request=request, **_proof(authority.self_signer(), challenge)
        )
    assert mismatched.value.status_code == 401


def test_admin_proof_cannot_move_to_another_target_incarnation(authority: _Authority) -> None:
    """Keep the admin roster and signer constant while replacing only the target."""

    key, signer = _admin()
    policy = authority.policy()
    policy.add_key(_registration(policy, key, signer), key)
    challenge = policy.issue(
        ISSUER, GatewayChallengeRequest(purpose="admin", request=REQUEST, key_id=key.key_id)
    )
    authority.target = authority.target.model_copy(update={"incarnation": "replacement"})
    with pytest.raises(GatewayAccessError) as replaced:
        policy.admit("private", issuer=ISSUER, request=REQUEST, **_proof(signer, challenge))
    assert replaced.value.status_code == 401
    assert _listed(policy, key, signer).target == authority.target


def test_self_challenge_checks_current_key_and_generation(authority: _Authority) -> None:
    """Reject stale self scope even when the ingress still names the same target."""

    generation = "first"
    policy = GatewayAccessPolicy(
        store=authority.store,
        target=lambda: authority.target,
        current_self=lambda: authority.store.load_self(generation),
    )
    signer = authority.self_signer()
    challenge = policy.issue(ISSUER, GatewayChallengeRequest(purpose="self", request=REQUEST))
    generation = "replacement"
    authority.store.provision_self(generation)
    with pytest.raises(GatewayAccessError) as stale:
        policy.admit("private", issuer=ISSUER, request=REQUEST, **_proof(signer, challenge))
    assert stale.value.status_code == 401


def test_proof_expiry_capacity_replay_and_no_ssh_dependency(
    authority: _Authority,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bound issuance, consume valid proof once, and authenticate without SSH executables."""

    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr("houmao.gateway.access._CHALLENGE_CAPACITY", 1)
    fixture_clock = SimpleNamespace(now=100.0)
    monkeypatch.setattr(
        "houmao.gateway.access.time",
        SimpleNamespace(time=lambda: fixture_clock.now, monotonic=lambda: fixture_clock.now),
    )
    policy = authority.policy()
    signer = authority.self_signer()
    request = GatewayChallengeRequest(purpose="self", request=REQUEST)
    expired = policy.issue(ISSUER, request)
    with pytest.raises(GatewayAccessError) as capacity:
        policy.issue(ISSUER, request)
    assert capacity.value.status_code == 429
    fixture_clock.now = 131
    valid = policy.issue(ISSUER, request)
    with pytest.raises(GatewayAccessError):
        policy.admit("private", issuer=ISSUER, request=REQUEST, **_proof(signer, expired))
    proof = _proof(signer, valid)
    assert policy.admit("private", issuer=ISSUER, request=REQUEST, **proof).role == "self"
    with pytest.raises(GatewayAccessError):
        policy.admit("private", issuer=ISSUER, request=REQUEST, **proof)


def test_competing_first_registration_and_wrong_purpose(authority: _Authority) -> None:
    """Verify the proposed key, reject reuse by purpose, and serialize the first commit."""

    first, first_signer = _admin("first")
    second, second_signer = _admin("second")
    policy = authority.policy()
    request = GatewayChallengeRequest(purpose="register", request=REGISTER, proposed_key=first)
    challenge = policy.issue(ISSUER, request)
    with pytest.raises(GatewayAccessError) as wrong_purpose:
        policy.admit("admin", issuer=ISSUER, request=REGISTER, **_proof(first_signer, challenge))
    assert wrong_purpose.value.status_code == 401
    challenge = policy.issue(ISSUER, request)
    with pytest.raises(GatewayAccessError) as wrong_key:
        policy.admit(
            "admin",
            issuer=ISSUER,
            request=REGISTER,
            registration=True,
            **_proof(second_signer, challenge),
        )
    assert wrong_key.value.status_code == 401
    assert authority.store.load().mode == "open"

    first_grant = _registration(policy, first, first_signer)
    second_grant = _registration(policy, second, second_signer)
    late = policy.issue(ISSUER, request)
    with ThreadPoolExecutor(max_workers=2) as workers:
        writes = [
            workers.submit(authority.policy().add_key, grant, key)
            for grant, key in ((first_grant, first), (second_grant, second))
        ]
        outcomes = [write.exception() for write in writes]
    assert outcomes.count(None) == 1
    conflict = next(error for error in outcomes if error is not None)
    assert isinstance(conflict, GatewayAccessError) and conflict.status_code == 409
    assert authority.store.load().revision == 1
    with pytest.raises(GatewayAccessError) as late_conflict:
        policy.admit(
            "admin",
            issuer=ISSUER,
            request=REGISTER,
            registration=True,
            **_proof(first_signer, late),
        )
    assert late_conflict.value.status_code == 409


def test_live_revocation_invalidates_only_affected_grants(authority: _Authority) -> None:
    """Enforce admin privilege, revision races, current enrollments, and final reopening."""

    policy = authority.policy()
    first, first_signer = _admin("first")
    second, second_signer = _admin("second")
    open_grant = policy.admit("admin", issuer=ISSUER, request=REQUEST)
    assert open_grant.role == "anonymous"
    assert policy.admit("private", issuer=ISSUER, request=REQUEST) == open_grant
    with pytest.raises(GatewayAccessError) as invalid_proof:
        policy.admit("private", issuer=ISSUER, request=REQUEST, challenge_id="invalid")
    assert invalid_proof.value.code == "invalid_proof"
    signed_self = policy.issue(ISSUER, GatewayChallengeRequest(purpose="self", request=REQUEST))
    register = _registration(policy, first, first_signer)
    assert policy.add_key(register, first) == first
    assert not policy.revalidate(open_grant)
    with pytest.raises(GatewayAccessError) as private_denial:
        policy.admit("private", issuer=ISSUER, request=REQUEST)
    assert private_denial.value.status_code == 401
    assert (
        policy.admit(
            "private",
            issuer=ISSUER,
            request=REQUEST,
            **_proof(authority.self_signer(), signed_self),
        ).role
        == "self"
    )
    signed_self = policy.issue(ISSUER, GatewayChallengeRequest(purpose="self", request=REQUEST))
    with pytest.raises(GatewayAccessError) as insufficient:
        policy.admit(
            "admin", issuer=ISSUER, request=REQUEST, **_proof(authority.self_signer(), signed_self)
        )
    assert insufficient.value.status_code == 403

    first_grant = _listed(policy, first, first_signer)
    stale = policy.issue(
        ISSUER, GatewayChallengeRequest(purpose="admin", request=REQUEST, key_id=first.key_id)
    )
    policy.add_key(first_grant, second)
    with pytest.raises(GatewayAccessError) as wrong_revision:
        policy.admit("admin", issuer=ISSUER, request=REQUEST, **_proof(first_signer, stale))
    assert wrong_revision.value.status_code == 401
    with pytest.raises(GatewayAccessError) as stale_commit:
        policy.remove_key(first_grant, second.key_id)
    assert stale_commit.value.status_code == 409

    second_grant = _listed(policy, second, second_signer)
    policy.remove_key(second_grant, first.key_id)
    assert not policy.revalidate(first_grant)
    assert policy.revalidate(second_grant)
    policy.add_key(_listed(policy, second, second_signer), first)
    assert not policy.revalidate(first_grant)
    policy.remove_key(_listed(policy, first, first_signer), second.key_id)
    policy.remove_key(_listed(policy, first, first_signer), first.key_id)
    reopened = policy.admit("admin", issuer=ISSUER, request=REQUEST)
    assert reopened.role == "anonymous"
    assert policy.admit("private", issuer=ISSUER, request=REQUEST) == reopened
    assert not policy.revalidate(open_grant)
    assert policy.revalidate(reopened)
    policy.add_key(_registration(policy, second, second_signer), second)
    assert _listed(policy, second, second_signer).principal == "second"
