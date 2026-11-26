"""Independent owner proof, exact retry, and durable policy placement tests."""

from pathlib import Path
import sqlite3

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import pytest

from houmao.mailbox.policy import (
    MailPolicyError,
    MailPolicyUpdate,
    apply_mail_policy,
    initialize_mail_policy,
    mail_policy_blocks,
    mail_policy_is_protected,
    read_mail_policy_receipt,
    set_mail_policy_owner,
    sign_mail_policy_update,
)


def _public_key(key: Ed25519PrivateKey) -> str:
    """Encode the owner's separate public key in the enrollment format."""

    return key.public_key().public_bytes(Encoding.OpenSSH, PublicFormat.OpenSSH).decode()


def _update(
    operation_id: str = "op-1", *, revision: int = 0, senders: tuple[str, ...] = ("a@example.org",)
) -> MailPolicyUpdate:
    """Build one complete policy update for a test registration."""

    return MailPolicyUpdate(
        backend_id="registry",
        binding_id="recipient-v1",
        expected_revision=revision,
        operation_id=operation_id,
        blocked_senders=senders,
    )


def test_policy_commit_and_exact_retries_survive_restart(tmp_path: Path) -> None:
    """Retry evidence survives subsequent updates without reactivating older rules."""

    path = tmp_path / "registry.sqlite"
    owner = Ed25519PrivateKey.generate()
    signed = sign_mail_policy_update(_update(), owner)
    with sqlite3.connect(path) as connection:
        initialize_mail_policy(connection)
        set_mail_policy_owner(connection, "recipient-v1", _public_key(owner))
        first = apply_mail_policy(
            connection, backend_id="registry", binding_id="recipient-v1", request=signed
        )
    with sqlite3.connect(path) as resumed:
        assert mail_policy_blocks(
            resumed, binding_id="recipient-v1", sender_address="a@example.org"
        )
        applied = apply_mail_policy(
            resumed,
            backend_id="registry",
            binding_id="recipient-v1",
            request=sign_mail_policy_update(_update("op-2", revision=1, senders=()), owner),
        )
        assert applied.revision == 2
    with sqlite3.connect(path) as resumed:
        assert (
            apply_mail_policy(
                resumed, backend_id="registry", binding_id="recipient-v1", request=signed
            )
            == first
        )
        assert (
            read_mail_policy_receipt(resumed, binding_id="recipient-v1", operation_id="op-1")
            == first
        )
        assert not mail_policy_blocks(
            resumed, binding_id="recipient-v1", sender_address="a@example.org"
        )


def test_policy_fences_owner_binding_payload_and_revision() -> None:
    """Forgery and stale or widened updates leave the committed rule untouched."""

    owner = Ed25519PrivateKey.generate()
    request = sign_mail_policy_update(_update(), owner)
    with sqlite3.connect(":memory:") as connection:
        initialize_mail_policy(connection)
        set_mail_policy_owner(connection, "recipient-v1", _public_key(owner))
        from_another_key = sign_mail_policy_update(_update(), Ed25519PrivateKey.generate())
        with pytest.raises(MailPolicyError, match="proof refused"):
            apply_mail_policy(
                connection,
                backend_id="registry",
                binding_id="recipient-v1",
                request=from_another_key,
            )
        with pytest.raises(MailPolicyError, match="target does not match"):
            apply_mail_policy(
                connection, backend_id="elsewhere", binding_id="recipient-v1", request=request
            )
        apply_mail_policy(
            connection, backend_id="registry", binding_id="recipient-v1", request=request
        )
        with pytest.raises(MailPolicyError, match="operation ID was reused"):
            apply_mail_policy(
                connection,
                backend_id="registry",
                binding_id="recipient-v1",
                request=sign_mail_policy_update(_update(revision=1, senders=()), owner),
            )
        with pytest.raises(MailPolicyError, match="revision changed"):
            apply_mail_policy(
                connection,
                backend_id="registry",
                binding_id="recipient-v1",
                request=sign_mail_policy_update(_update("stale"), owner),
            )
        set_mail_policy_owner(connection, "recipient-v1", None)
        with pytest.raises(MailPolicyError, match="proof required"):
            apply_mail_policy(
                connection, backend_id="registry", binding_id="recipient-v1", request=request
            )
        assert mail_policy_is_protected(connection, "recipient-v1")
        assert mail_policy_blocks(
            connection, binding_id="recipient-v1", sender_address="a@example.org"
        )
