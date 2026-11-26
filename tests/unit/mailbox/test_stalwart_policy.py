"""Exercise independent Stalwart rule authorization and provider reconciliation."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi.testclient import TestClient

from houmao.mailbox.policy import (
    MailPolicyUpdate,
    initialize_mail_policy,
    read_mail_policy_receipt,
    set_mail_policy_owner,
    sign_mail_policy_update,
)
from houmao.mailbox.stalwart import JMAP_SIEVE_CAPABILITY, StalwartError, StalwartJmapClient
from houmao.mailbox.stalwart_policy_authority import (
    StalwartPolicyTarget,
    create_stalwart_policy_app,
)


@dataclass
class _SieveProvider:
    """Model a provider-native managed include and its independently configured wrapper."""

    m_wrapper: str = "wrapper-0"
    m_blob: str = "policy-0"
    m_raw: bytes = b"# no rules\n"
    m_uploaded: bytes = b""
    m_mutations: int = 0
    m_gets: int = 0
    m_lose_acknowledgement: bool = False

    def require_protected_runtime(self, account_id: str) -> None:
        """Model a separately checked and isolated ordinary runtime login."""

        assert account_id == "account-1"

    def primary_account_id(self) -> str:
        """Expose the selected provider account."""

        return "account-1"

    def mailbox_id_for_role(self, role: str) -> str:
        """Report the enrolled Archive role while qualifying delivery."""

        assert role == "archive"
        return "archive-1"

    def download_sieve_script(self, *, account_id: str, blob_id: str) -> bytes:
        """Read the installed include as observed through the provider."""

        assert account_id == "account-1" and blob_id == self.m_blob
        return self.m_raw

    def upload_sieve_script(self, *, account_id: str, script: bytes) -> str:
        """Stage a raw script before the fenced update."""

        assert account_id == "account-1"
        self.m_uploaded = script
        return "upload-1"

    def call(
        self, method_calls: list[list[Any]], *, additional_capabilities: tuple[str, ...]
    ) -> dict[str, Any]:
        """Accept only CAS changes to the expected provider object."""

        assert additional_capabilities == (JMAP_SIEVE_CAPABILITY,)
        [(method, args, call_id)] = method_calls
        assert args["accountId"] == "account-1"
        if method == "SieveScript/get":
            self.m_gets += 1
            result = {
                "accountId": "account-1",
                "state": str(self.m_mutations),
                "list": [
                    {
                        "id": "managed",
                        "name": "houmao-protected-archive",
                        "isActive": False,
                        "blobId": self.m_blob,
                    },
                    {
                        "id": "wrapper",
                        "name": "site-rules",
                        "isActive": True,
                        "blobId": self.m_wrapper,
                    },
                ],
            }
        else:
            assert method == "SieveScript/set"
            assert args == {
                "accountId": "account-1",
                "ifInState": str(self.m_mutations),
                "update": {"managed": {"blobId": "upload-1"}},
            }
            self.m_mutations += 1
            self.m_blob = f"policy-{self.m_mutations}"
            self.m_raw = self.m_uploaded
            if self.m_lose_acknowledgement:
                raise StalwartError("Lost provider response after commit.")
            result = {"updated": {"managed": None}}
        return {"methodResponses": [[method, result, call_id]]}


def test_stalwart_connector_verifies_before_provider_and_reconciles_exact_retry(
    tmp_path: Path,
) -> None:
    """A wrong signer cannot write, and an ambiguous native update can be read back."""

    signer = Ed25519PrivateKey.generate()
    database = tmp_path / "owner.sqlite"
    with sqlite3.connect(database) as connection:
        initialize_mail_policy(connection)
        set_mail_policy_owner(
            connection,
            "binding-1",
            signer.public_key().public_bytes(Encoding.OpenSSH, PublicFormat.OpenSSH).decode(),
        )
    provider = _SieveProvider(m_lose_acknowledgement=True)
    target = StalwartPolicyTarget(
        backend_id="stalwart-1",
        binding_id="binding-1",
        account_id="account-1",
        archive_id="archive-1",
        active_script_blob="wrapper-0",
        initial_policy_blob="policy-0",
        client=cast(StalwartJmapClient, provider),
        runtime_client=cast(StalwartJmapClient, provider),
    )
    app = create_stalwart_policy_app(database=database, targets=[target])
    update = MailPolicyUpdate(
        backend_id="stalwart-1",
        binding_id="binding-1",
        expected_revision=0,
        operation_id="block-1",
        blocked_senders=("Alice+peer@example.test",),
    )
    path = "/v1/mail-policy/apply"
    signed = sign_mail_policy_update(update, signer)
    with TestClient(app) as client:
        forged = sign_mail_policy_update(update, Ed25519PrivateKey.generate())
        response = client.post(path, json=forged.model_dump(mode="json"))
        assert response.json()["status"] == "refused"
        assert not provider.m_gets and not provider.m_mutations
        provider.m_wrapper = "unqualified-wrapper"
        response = client.post(path, json=signed.model_dump(mode="json"))
        assert response.json()["status"] == "unsupported"
        assert not provider.m_mutations
        provider.m_wrapper = "wrapper-0"
        response = client.post(path, json=signed.model_dump(mode="json"))
        assert response.json()["status"] == "uncertain"
        assert provider.m_mutations == 1 and b'fileinto :specialuse "\\\\Archive"' in provider.m_raw
        response = client.post(path, json=signed.model_dump(mode="json"))
        assert response.json()["status"] == "applied" and response.json()["revision"] == 1
        assert provider.m_mutations == 1
        assert "Alice" not in response.text
        response = client.post(path, json=signed.model_dump(mode="json"))
        assert response.json()["revision"] == 1 and provider.m_mutations == 1
    with sqlite3.connect(database) as connection:
        receipt = read_mail_policy_receipt(
            connection, binding_id="binding-1", operation_id="block-1"
        )
    assert receipt is not None and receipt.revision == 1
