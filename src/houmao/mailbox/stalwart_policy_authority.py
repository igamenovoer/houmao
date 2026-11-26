"""Apply protected Stalwart rules from an independently operated authority."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from houmao.mailbox.policy import (
    MailPolicyError,
    MailPolicyReceipt,
    SignedMailPolicyUpdate,
    apply_mail_policy,
    initialize_mail_policy,
    verify_mail_policy_update,
)
from houmao.mailbox.stalwart import (
    JMAP_SIEVE_CAPABILITY,
    MAX_SIEVE_SCRIPT_BYTES,
    StalwartError,
    StalwartJmapClient,
    StalwartMethodError,
    StalwartReadinessError,
    _assert_set_result,
    _require_method_response,
    _require_object_list,
    _require_string,
)

_POLICY_SCRIPT = "houmao-protected-archive"
_MAX_UPDATE_BYTES = 1024 * 1024


@dataclass(frozen=True)
class StalwartPolicyTarget:
    """Provider pins enrolled independently after validating delivery and runtime isolation."""

    backend_id: str
    binding_id: str
    account_id: str
    archive_id: str
    active_script_blob: str
    initial_policy_blob: str
    client: StalwartJmapClient
    runtime_client: StalwartJmapClient

    def apply(
        self, connection: sqlite3.Connection, request: SignedMailPolicyUpdate
    ) -> MailPolicyReceipt:
        """Verify, update only the enrolled native script, and record the observed result."""

        initialize_mail_policy(connection)
        connection.execute(
            """CREATE TABLE IF NOT EXISTS stalwart_policy_blob (
                binding_id TEXT PRIMARY KEY, blob_id TEXT NOT NULL
            )"""
        )
        connection.execute("BEGIN IMMEDIATE")
        prior = verify_mail_policy_update(
            connection, backend_id=self.backend_id, binding_id=self.binding_id, request=request
        )
        if prior is not None:
            return prior
        self.runtime_client.require_protected_runtime(self.account_id)
        if self.client.primary_account_id() != self.account_id:
            raise _unsupported("The connector's provider account does not match enrollment.")
        if self.client.mailbox_id_for_role("archive") != self.archive_id:
            raise _unsupported("The enrolled provider Archive role has changed.")
        state, script_id, current_blob = self._script_state()
        upload = _archive_script(request)
        if len(upload) > MAX_SIEVE_SCRIPT_BYTES:
            raise MailPolicyError("provider_policy_too_large", 400, "The rule list is too large.")
        current = self.client.download_sieve_script(
            account_id=self.account_id, blob_id=current_blob
        )
        if current != upload:
            previous = connection.execute(
                "SELECT blob_id FROM stalwart_policy_blob WHERE binding_id = ?", (self.binding_id,)
            ).fetchone()
            expected_blob = previous[0] if previous is not None else self.initial_policy_blob
            if current_blob != expected_blob:
                raise MailPolicyError(
                    "provider_policy_conflict", 409, "The provider policy needs reconciliation."
                )
            uploaded_blob = self.client.upload_sieve_script(
                account_id=self.account_id, script=upload
            )
            try:
                result = self._call(
                    "SieveScript/set",
                    {"ifInState": state, "update": {script_id: {"blobId": uploaded_blob}}},
                )
                _assert_set_result(result, method="SieveScript/set", key=script_id, action="update")
            except StalwartMethodError as exc:
                raise MailPolicyError(
                    "provider_policy_refused", 409, "The provider refused the rule change."
                ) from exc
            try:
                _, _, current_blob = self._script_state()
                installed = self.client.download_sieve_script(
                    account_id=self.account_id, blob_id=current_blob
                )
            except (StalwartError, MailPolicyError) as exc:
                raise StalwartError("The installed provider policy could not be verified.") from exc
            if installed != upload:
                raise StalwartError("The provider did not confirm the installed policy script.")
        receipt = apply_mail_policy(
            connection, backend_id=self.backend_id, binding_id=self.binding_id, request=request
        )
        connection.execute(
            "INSERT INTO stalwart_policy_blob(binding_id,blob_id) VALUES (?,?) "
            "ON CONFLICT(binding_id) DO UPDATE SET blob_id = excluded.blob_id",
            (self.binding_id, current_blob),
        )
        return receipt

    def _call(self, method: str, arguments: dict[str, object]) -> dict[str, object]:
        """Call an exact account's native Sieve method using owner credentials."""

        return _require_method_response(
            self.client.call(
                [[method, {"accountId": self.account_id, **arguments}, "policy"]],
                additional_capabilities=(JMAP_SIEVE_CAPABILITY,),
            ),
            method_name=method,
            call_id="policy",
        )

    def _script_state(self) -> tuple[str, str, str]:
        """Require the enrolled active wrapper and exactly one existing owned include."""

        result = self._call(
            "SieveScript/get", {"ids": None, "properties": ["id", "name", "blobId", "isActive"]}
        )
        scripts = _require_object_list(result, "list")
        active = [item for item in scripts if item.get("isActive") is True]
        owned = [item for item in scripts if item.get("name") == _POLICY_SCRIPT]
        if (
            result.get("accountId") != self.account_id
            or len(active) != 1
            or len(owned) != 1
            or active[0].get("blobId") != self.active_script_blob
            or owned[0].get("isActive") is not False
        ):
            raise _unsupported("The enrolled Sieve wrapper or protected script is unavailable.")
        return (
            _require_string(result, "state"),
            _require_string(owned[0], "id"),
            _require_string(owned[0], "blobId"),
        )


def create_stalwart_policy_app(*, database: Path, targets: list[StalwartPolicyTarget]) -> FastAPI:
    """Serve the signed update endpoint in a trusted account apart from the gateway."""

    by_binding = {(target.backend_id, target.binding_id): target for target in targets}
    if len(by_binding) != len(targets):
        raise ValueError("Stalwart policy authority has duplicate targets.")
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.post("/v1/mail-policy/apply")
    async def apply(request: Request) -> MailPolicyReceipt:
        """Keep unvalidated input and provider credentials out of application responses."""

        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > _MAX_UPDATE_BYTES:
                raise HTTPException(413, "Mail policy request exceeds its transfer limit.")
        try:
            signed = SignedMailPolicyUpdate.model_validate_json(body)
        except ValidationError:
            raise HTTPException(422, "Invalid mail policy request.") from None
        target = by_binding.get((signed.update.backend_id, signed.update.binding_id))
        if target is None:
            return MailPolicyReceipt(status="unsupported", operation_id=signed.update.operation_id)
        return await run_in_threadpool(_apply, database, target, signed)

    return app


def _apply(
    database: Path, target: StalwartPolicyTarget, request: SignedMailPolicyUpdate
) -> MailPolicyReceipt:
    """Serialize owner requests and keep ambiguous provider outcomes recoverable."""

    try:
        connection = sqlite3.connect(database)
        try:
            with connection:
                return target.apply(connection, request)
        finally:
            connection.close()
    except MailPolicyError as exc:
        return MailPolicyReceipt(
            status="unsupported" if exc.status == 501 else "refused",
            operation_id=request.update.operation_id,
            detail=str(exc),
        )
    except StalwartReadinessError:
        return MailPolicyReceipt(
            status="unsupported",
            operation_id=request.update.operation_id,
            detail="The provider lacks the enrolled native Sieve and Archive capabilities.",
        )
    except (StalwartError, sqlite3.Error):
        return MailPolicyReceipt(
            status="uncertain",
            operation_id=request.update.operation_id,
            detail="The Stalwart policy outcome requires owner verification.",
        )


def _archive_script(request: SignedMailPolicyUpdate) -> bytes:
    """Encode one signed operation into a deterministic, exact sender Sieve include."""

    update = request.update
    script = [f"# Houmao policy {sha256(update.signing_bytes()).hexdigest()}"]
    if update.blocked_senders:
        senders = ", ".join(
            json.dumps(_sender_pattern(sender)) for sender in update.blocked_senders
        )
        script.extend(
            [
                'require ["fileinto", "special-use", "regex"];',
                f'if address :regex :comparator "i;octet" "From" [{senders}] {{',
                '  fileinto :specialuse "\\\\Archive" "Archive";',
                "  stop;",
                "}",
            ]
        )
    return ("\n".join(script) + "\n").encode()


def _sender_pattern(sender: str) -> str:
    """Keep the exact local-part and accept either ASCII case for the domain."""

    local_part, domain = sender.split("@")
    domain_pattern = "".join(
        f"[{character.lower()}{character.upper()}]" if character.isalpha() else re.escape(character)
        for character in domain
    )
    return f"^{re.escape(local_part)}@{domain_pattern}$"


def _unsupported(message: str) -> MailPolicyError:
    """Report that an externally qualified native configuration is unavailable."""

    return MailPolicyError("protected_policy_unsupported", 501, message)
