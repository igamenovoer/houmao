"""Stalwart provisioning and raw JMAP helpers."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import secrets
import shutil
from typing import Any, Mapping, Sequence, cast
from urllib import error, parse, request

from houmao.mailbox.protocol import validate_mailbox_address

STALWART_BASE_URL_ENV_VAR = "HOUMAO_STALWART_BASE_URL"
STALWART_MANAGEMENT_BEARER_TOKEN_ENV_VAR = "HOUMAO_STALWART_MANAGEMENT_BEARER_TOKEN"
STALWART_MANAGEMENT_API_KEY_ENV_VAR = "HOUMAO_STALWART_MANAGEMENT_API_KEY"
STALWART_MANAGEMENT_API_SECRET_ENV_VAR = "HOUMAO_STALWART_MANAGEMENT_API_SECRET"


class StalwartError(RuntimeError):
    """Raised when Stalwart provisioning or JMAP access fails."""


@dataclass(frozen=True)
class StalwartProvisionedBinding:
    """Provisioned Stalwart mailbox details."""

    jmap_url: str
    management_url: str
    login_identity: str
    credential_ref: str
    credential_file: Path


def build_stalwart_credential_ref(*, address: str, jmap_url: str) -> str:
    """Return a stable secret-free credential reference."""

    digest = hashlib.sha256(f"{jmap_url}\n{address}".encode("utf-8")).hexdigest()[:16]
    address_slug = address.replace("@", "-at-").replace(".", "-")
    return f"stalwart-{address_slug}-{digest}"


def runtime_stalwart_credential_path(runtime_root: Path, credential_ref: str) -> Path:
    """Return the runtime-owned persistent credential file path."""

    return runtime_root.resolve() / "mailbox-credentials" / "stalwart" / f"{credential_ref}.json"


def session_stalwart_credential_path(session_root: Path, credential_ref: str) -> Path:
    """Return the session-local credential file path."""

    return session_root.resolve() / "mailbox-secrets" / f"{credential_ref}.json"


def materialize_stalwart_session_credential(
    *,
    runtime_root: Path,
    session_root: Path,
    credential_ref: str,
) -> Path:
    """Materialize one session-local credential file from the runtime-owned store."""

    source_path = runtime_stalwart_credential_path(runtime_root, credential_ref)
    if not source_path.is_file():
        raise StalwartError(f"Stalwart credential material not found for `{credential_ref}`.")

    target_path = session_stalwart_credential_path(session_root, credential_ref)
    if target_path.is_file():
        return target_path.resolve()

    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    target_path.chmod(0o600)
    return target_path.resolve()


def load_stalwart_password(credential_file: Path) -> str:
    """Load the mailbox password from a runtime-owned credential file."""

    try:
        payload = json.loads(credential_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StalwartError(f"Stalwart credential file not found: {credential_file}") from exc
    except json.JSONDecodeError as exc:
        raise StalwartError(f"Stalwart credential file is invalid JSON: {credential_file}") from exc

    if not isinstance(payload, dict):
        raise StalwartError(f"Stalwart credential file must contain a JSON object: {credential_file}")
    password = payload.get("password")
    if not isinstance(password, str) or not password.strip():
        raise StalwartError(
            f"Stalwart credential file is missing a non-empty password: {credential_file}"
        )
    return password


def ensure_stalwart_mailbox(
    *,
    runtime_root: Path,
    session_root: Path,
    principal_id: str,
    address: str,
    jmap_url: str,
    management_url: str,
    login_identity: str,
) -> StalwartProvisionedBinding:
    """Provision or reuse one Stalwart mailbox binding."""

    normalized_address = validate_mailbox_address(address)
    domain = normalized_address.split("@", 1)[1]
    credential_ref = build_stalwart_credential_ref(address=normalized_address, jmap_url=jmap_url)
    runtime_credential_path = runtime_stalwart_credential_path(runtime_root, credential_ref)
    session_credential_path = session_stalwart_credential_path(session_root, credential_ref)

    password: str
    created_new_password = False
    if runtime_credential_path.is_file():
        password = load_stalwart_password(runtime_credential_path)
    else:
        password = secrets.token_urlsafe(24)
        created_new_password = True

    management = StalwartManagementClient(base_url=management_url)
    management.ensure_domain(domain)
    management.ensure_mailbox_account(
        principal_id=principal_id,
        address=normalized_address,
        login_identity=login_identity,
        password=password,
        rotate_secret=created_new_password,
    )

    if created_new_password:
        _write_secret_file(
            runtime_credential_path,
            {
                "credential_ref": credential_ref,
                "login_identity": login_identity,
                "password": password,
            },
        )

    session_credential_path.parent.mkdir(parents=True, exist_ok=True)
    if not session_credential_path.is_file():
        shutil.copy2(runtime_credential_path, session_credential_path)
        session_credential_path.chmod(0o600)

    return StalwartProvisionedBinding(
        jmap_url=jmap_url,
        management_url=management_url,
        login_identity=login_identity,
        credential_ref=credential_ref,
        credential_file=session_credential_path.resolve(),
    )


class StalwartManagementClient:
    """Thin Management API client used for mailbox provisioning."""

    def __init__(self, *, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.m_base_url = base_url.rstrip("/")
        self.m_timeout_seconds = timeout_seconds

    def list_principals(self, *, types: Sequence[str] | None = None) -> list[dict[str, Any]]:
        """List management principals."""

        query = ""
        if types:
            query = "?" + parse.urlencode({"types": ",".join(types)})
        payload = self._request_json("GET", f"/principal{query}")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise StalwartError("Stalwart principal list returned an invalid `data` payload.")
        items = data.get("items")
        if not isinstance(items, list):
            raise StalwartError("Stalwart principal list returned an invalid `items` payload.")
        return [item for item in items if isinstance(item, dict)]

    def ensure_domain(self, domain: str) -> dict[str, Any]:
        """Ensure a domain principal exists."""

        for principal in self.list_principals(types=("domain",)):
            if principal.get("name") == domain:
                return principal
        self.create_principal(
            {
                "type": "domain",
                "name": domain,
                "description": f"Houmao-managed mailbox domain {domain}",
                "quota": 0,
                "secrets": [],
                "emails": [],
                "urls": [],
                "memberOf": [],
                "roles": [],
                "lists": [],
                "members": [],
                "enabledPermissions": [],
                "disabledPermissions": [],
                "externalMembers": [],
            }
        )
        for principal in self.list_principals(types=("domain",)):
            if principal.get("name") == domain:
                return principal
        raise StalwartError(f"Stalwart domain provisioning did not create `{domain}`.")

    def ensure_mailbox_account(
        self,
        *,
        principal_id: str,
        address: str,
        login_identity: str,
        password: str,
        rotate_secret: bool,
    ) -> dict[str, Any]:
        """Ensure an individual mailbox account exists and is usable."""

        existing: dict[str, Any] | None = None
        for principal in self.list_principals(types=("individual",)):
            emails = principal.get("emails")
            if isinstance(emails, list) and address in emails:
                existing = principal
                break
            if principal.get("name") in {principal_id, login_identity, address}:
                existing = principal
                break

        if existing is None:
            self.create_principal(
                {
                    "type": "individual",
                    "name": principal_id,
                    "description": f"Houmao mailbox account for {address}",
                    "quota": 0,
                    "secrets": [password],
                    "emails": [address],
                    "urls": [],
                    "memberOf": [],
                    "roles": ["user"],
                    "lists": [],
                    "members": [],
                    "enabledPermissions": [],
                    "disabledPermissions": [],
                    "externalMembers": [],
                }
            )
            for principal in self.list_principals(types=("individual",)):
                emails = principal.get("emails")
                if isinstance(emails, list) and address in emails:
                    return principal
            raise StalwartError(f"Stalwart account provisioning did not create `{address}`.")

        principal_identifier = existing.get("id")
        if principal_identifier is None:
            raise StalwartError("Stalwart account lookup returned a principal without an id.")

        operations: list[dict[str, object]] = []
        emails = existing.get("emails")
        if not isinstance(emails, list) or address not in emails:
            operations.append({"action": "addItem", "field": "emails", "value": address})
        if rotate_secret:
            operations.append({"action": "set", "field": "secrets", "value": [password]})
        if operations:
            self.patch_principal(str(principal_identifier), operations)
        return existing

    def create_principal(self, payload: Mapping[str, object]) -> object:
        """Create one management principal."""

        response_payload = self._request_json("POST", "/principal", body=payload)
        return response_payload.get("data")

    def patch_principal(self, principal_id: str, operations: Sequence[Mapping[str, object]]) -> None:
        """Patch one management principal."""

        self._request_json(
            "PATCH",
            f"/principal/{parse.quote(principal_id, safe='')}",
            body=list(operations),
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: object | None = None,
    ) -> dict[str, Any]:
        """Send one JSON Management API request."""

        payload: bytes | None = None
        headers = {"Accept": "application/json", **_management_auth_headers()}
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        url = f"{self.m_base_url}{path}"
        return _request_json(method=method, url=url, body=payload, headers=headers, timeout=self.m_timeout_seconds)


class StalwartJmapClient:
    """Raw-HTTP JMAP client for Stalwart-backed mailbox operations."""

    def __init__(
        self,
        *,
        jmap_url: str,
        login_identity: str,
        credential_file: Path,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.m_jmap_url = jmap_url.rstrip("/")
        self.m_login_identity = login_identity
        self.m_credential_file = credential_file.resolve()
        self.m_timeout_seconds = timeout_seconds
        self.m_session: dict[str, Any] | None = None

    def status(self) -> dict[str, Any]:
        """Return session and account metadata for the mailbox binding."""

        session = self.session()
        account_id = self.primary_account_id()
        return {
            "session": session,
            "account_id": account_id,
        }

    def check(
        self,
        *,
        unread_only: bool,
        limit: int | None,
        since: str | None,
    ) -> list[dict[str, Any]]:
        """Fetch normalized JMAP message payloads."""

        account_id = self.primary_account_id()
        inbox_mailbox_id = self.mailbox_id_for_role("inbox")
        method_calls: list[list[object]] = [
            [
                "Email/query",
                {
                    "accountId": account_id,
                    "filter": {"inMailbox": inbox_mailbox_id} if inbox_mailbox_id is not None else None,
                    "sort": [{"property": "receivedAt", "isAscending": False}],
                    "limit": limit if limit is not None and limit > 0 else None,
                },
                "m1",
            ]
        ]
        response = self.call(method_calls)
        queried = _require_method_response(response, method_name="Email/query", call_id="m1")
        ids = queried.get("ids")
        if not isinstance(ids, list):
            raise StalwartError("JMAP Email/query response is missing an `ids` list.")
        email_ids = [item for item in ids if isinstance(item, str)]
        if not email_ids:
            return []

        response = self.call(
            [
                [
                    "Email/get",
                    {
                        "accountId": account_id,
                        "ids": email_ids,
                        "properties": [
                            "id",
                            "threadId",
                            "receivedAt",
                            "messageId",
                            "inReplyTo",
                            "references",
                            "from",
                            "to",
                            "cc",
                            "replyTo",
                            "subject",
                            "preview",
                            "keywords",
                            "attachments",
                            "textBody",
                            "bodyValues",
                        ],
                        "fetchTextBodyValues": True,
                        "maxBodyValueBytes": 16384,
                    },
                    "m2",
                ]
            ]
        )
        payload = _require_method_response(response, method_name="Email/get", call_id="m2")
        emails = payload.get("list")
        if not isinstance(emails, list):
            raise StalwartError("JMAP Email/get response is missing a `list` payload.")

        normalized: list[dict[str, Any]] = []
        since_timestamp = _parse_optional_timestamp(since)
        for raw_email in emails:
            if not isinstance(raw_email, dict):
                continue
            received_at = _require_string(raw_email, "receivedAt")
            if since_timestamp is not None and _parse_timestamp(received_at) < since_timestamp:
                continue
            unread = "$seen" not in _coerce_keywords(raw_email.get("keywords"))
            if unread_only and not unread:
                continue
            normalized.append(
                {
                    "id": _require_string(raw_email, "id"),
                    "threadId": _optional_string(raw_email, "threadId"),
                    "receivedAt": received_at,
                    "messageId": _coerce_string_list(raw_email.get("messageId")),
                    "inReplyTo": _coerce_string_list(raw_email.get("inReplyTo")),
                    "references": _coerce_string_list(raw_email.get("references")),
                    "from": _coerce_address_list(raw_email.get("from")),
                    "to": _coerce_address_list(raw_email.get("to")),
                    "cc": _coerce_address_list(raw_email.get("cc")),
                    "replyTo": _coerce_address_list(raw_email.get("replyTo")),
                    "subject": _optional_string(raw_email, "subject") or "(no subject)",
                    "preview": _optional_string(raw_email, "preview"),
                    "body": _extract_text_body(raw_email),
                    "attachments": _coerce_attachment_list(raw_email.get("attachments")),
                    "unread": unread,
                }
            )

        if limit is not None and limit > 0:
            return normalized[:limit]
        return normalized

    def send(
        self,
        *,
        sender_address: str,
        to_addresses: Sequence[str],
        cc_addresses: Sequence[str],
        subject: str,
        body_content: str,
        attachments: Sequence[Path],
        in_reply_to: Sequence[str] | None = None,
        references: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Compose and submit one JMAP-backed message."""

        account_id = self.primary_account_id()
        sent_mailbox_id = self.mailbox_id_for_role("sent")
        identity_id = self.primary_identity_id()
        attachment_parts = self.upload_attachments(account_id=account_id, attachments=attachments)

        create_payload: dict[str, Any] = {
            "from": [{"email": sender_address}],
            "to": [{"email": value} for value in to_addresses],
            "cc": [{"email": value} for value in cc_addresses],
            "subject": subject,
            "keywords": {},
            "bodyValues": {
                "text-1": {
                    "value": body_content,
                }
            },
            "textBody": [
                {
                    "partId": "text-1",
                    "type": "text/plain",
                }
            ],
        }
        if sent_mailbox_id is not None:
            create_payload["mailboxIds"] = {sent_mailbox_id: True}
        if attachment_parts:
            create_payload["attachments"] = attachment_parts
        if in_reply_to:
            create_payload["header:In-Reply-To:asMessageIds"] = list(in_reply_to)
        if references:
            create_payload["header:References:asMessageIds"] = list(references)

        response = self.call(
            [
                [
                    "Email/set",
                    {
                        "accountId": account_id,
                        "create": {"mail-1": create_payload},
                    },
                    "m1",
                ],
                [
                    "EmailSubmission/set",
                    {
                        "accountId": account_id,
                        "create": {
                            "submission-1": {
                                "identityId": identity_id,
                                "emailId": "#mail-1",
                            }
                        },
                    },
                    "m2",
                ],
            ]
        )
        created = _require_method_response(response, method_name="Email/set", call_id="m1")
        create_map = created.get("created")
        if not isinstance(create_map, dict):
            raise StalwartError("JMAP Email/set response is missing a `created` payload.")
        created_email = create_map.get("mail-1")
        if not isinstance(created_email, dict):
            raise StalwartError("JMAP Email/set response is missing the created email record.")
        email_id = _require_string(created_email, "id")
        fetched = self.get_email(email_id=email_id)
        return fetched

    def reply(
        self,
        *,
        message_ref: str,
        sender_address: str,
        body_content: str,
        attachments: Sequence[Path],
    ) -> dict[str, Any]:
        """Reply to one existing JMAP email."""

        email_id = message_ref.split(":", 1)[1] if ":" in message_ref else message_ref
        original = self.get_email(email_id=email_id)
        reply_targets = original["replyTo"] or original["from"]
        if not reply_targets:
            raise StalwartError(f"Stalwart reply target has no sender metadata: {message_ref}")
        reply_subject = original["subject"]
        if not reply_subject.lower().startswith("re:"):
            reply_subject = f"Re: {reply_subject}"

        references = list(cast(list[str], original["references"]))
        message_ids = cast(list[str], original["messageId"])
        in_reply_to = message_ids[-1:] if message_ids else []
        if in_reply_to:
            references = [*references, in_reply_to[-1]]

        return self.send(
            sender_address=sender_address,
            to_addresses=[item["email"] for item in cast(list[dict[str, str]], reply_targets)],
            cc_addresses=(),
            subject=reply_subject,
            body_content=body_content,
            attachments=attachments,
            in_reply_to=in_reply_to,
            references=references,
        )

    def get_email(self, *, email_id: str) -> dict[str, Any]:
        """Fetch one normalized email payload."""

        account_id = self.primary_account_id()
        response = self.call(
            [
                [
                    "Email/get",
                    {
                        "accountId": account_id,
                        "ids": [email_id],
                        "properties": [
                            "id",
                            "threadId",
                            "receivedAt",
                            "messageId",
                            "inReplyTo",
                            "references",
                            "from",
                            "to",
                            "cc",
                            "replyTo",
                            "subject",
                            "preview",
                            "keywords",
                            "attachments",
                            "textBody",
                            "bodyValues",
                        ],
                        "fetchTextBodyValues": True,
                        "maxBodyValueBytes": 16384,
                    },
                    "m1",
                ]
            ]
        )
        payload = _require_method_response(response, method_name="Email/get", call_id="m1")
        values = payload.get("list")
        if not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], dict):
            raise StalwartError(f"JMAP Email/get did not return the requested email `{email_id}`.")
        raw_email = values[0]
        return {
            "id": _require_string(raw_email, "id"),
            "threadId": _optional_string(raw_email, "threadId"),
            "receivedAt": _optional_string(raw_email, "receivedAt")
            or _utc_now_iso(),
            "messageId": _coerce_string_list(raw_email.get("messageId")),
            "inReplyTo": _coerce_string_list(raw_email.get("inReplyTo")),
            "references": _coerce_string_list(raw_email.get("references")),
            "from": _coerce_address_list(raw_email.get("from")),
            "to": _coerce_address_list(raw_email.get("to")),
            "cc": _coerce_address_list(raw_email.get("cc")),
            "replyTo": _coerce_address_list(raw_email.get("replyTo")),
            "subject": _optional_string(raw_email, "subject") or "(no subject)",
            "preview": _optional_string(raw_email, "preview"),
            "body": _extract_text_body(raw_email),
            "attachments": _coerce_attachment_list(raw_email.get("attachments")),
            "unread": "$seen" not in _coerce_keywords(raw_email.get("keywords")),
        }

    def upload_attachments(
        self,
        *,
        account_id: str,
        attachments: Sequence[Path],
    ) -> list[dict[str, Any]]:
        """Upload attachments through the JMAP upload surface."""

        upload_url_template = _require_string(self.session(), "uploadUrl")
        resolved_upload_url = upload_url_template.replace("{accountId}", parse.quote(account_id))
        parts: list[dict[str, Any]] = []
        for attachment_path in attachments:
            media_type = mimetypes.guess_type(attachment_path.name)[0] or "application/octet-stream"
            response_payload = _request_json(
                method="POST",
                url=resolved_upload_url,
                body=attachment_path.read_bytes(),
                headers={
                    "Authorization": self.authorization_header(),
                    "Content-Type": media_type,
                    "Accept": "application/json",
                },
                timeout=self.m_timeout_seconds,
            )
            blob_id = _require_string(response_payload, "blobId")
            parts.append(
                {
                    "blobId": blob_id,
                    "type": _optional_string(response_payload, "type") or media_type,
                    "name": attachment_path.name,
                    "size": response_payload.get("size"),
                    "disposition": "attachment",
                }
            )
        return parts

    def primary_identity_id(self) -> str:
        """Return the preferred identity id for submissions."""

        account_id = self.primary_account_id()
        response = self.call(
            [["Identity/get", {"accountId": account_id, "ids": None}, "m1"]]
        )
        payload = _require_method_response(response, method_name="Identity/get", call_id="m1")
        identities = payload.get("list")
        if not isinstance(identities, list):
            raise StalwartError("JMAP Identity/get response is missing a `list` payload.")
        for identity in identities:
            if not isinstance(identity, dict):
                continue
            if identity.get("email") == self.m_login_identity:
                return _require_string(identity, "id")
        for identity in identities:
            if isinstance(identity, dict):
                return _require_string(identity, "id")
        raise StalwartError("No JMAP identity is available for mailbox submission.")

    def mailbox_id_for_role(self, role: str) -> str | None:
        """Return the first mailbox id for one role."""

        account_id = self.primary_account_id()
        response = self.call(
            [["Mailbox/get", {"accountId": account_id, "ids": None}, "m1"]]
        )
        payload = _require_method_response(response, method_name="Mailbox/get", call_id="m1")
        mailboxes = payload.get("list")
        if not isinstance(mailboxes, list):
            raise StalwartError("JMAP Mailbox/get response is missing a `list` payload.")
        for mailbox in mailboxes:
            if isinstance(mailbox, dict) and mailbox.get("role") == role:
                return _require_string(mailbox, "id")
        return None

    def primary_account_id(self) -> str:
        """Return the preferred mail account id."""

        session = self.session()
        primary_accounts = session.get("primaryAccounts")
        if isinstance(primary_accounts, dict):
            for capability in ("urn:ietf:params:jmap:mail", "urn:ietf:params:jmap:submission"):
                value = primary_accounts.get(capability)
                if isinstance(value, str) and value.strip():
                    return value
        accounts = session.get("accounts")
        if not isinstance(accounts, dict) or not accounts:
            raise StalwartError("JMAP session is missing a usable `accounts` payload.")
        first_account_id = next(iter(accounts.keys()))
        if not isinstance(first_account_id, str) or not first_account_id.strip():
            raise StalwartError("JMAP session returned an invalid account identifier.")
        return first_account_id

    def session(self) -> dict[str, Any]:
        """Return the cached JMAP session object."""

        if self.m_session is not None:
            return self.m_session
        payload = _request_json(
            method="GET",
            url=self.m_jmap_url,
            body=None,
            headers={
                "Authorization": self.authorization_header(),
                "Accept": "application/json",
            },
            timeout=self.m_timeout_seconds,
        )
        self.m_session = payload
        return payload

    def call(self, method_calls: Sequence[Sequence[object]]) -> dict[str, Any]:
        """Call one raw JMAP request."""

        session = self.session()
        api_url = _require_string(session, "apiUrl")
        payload = {
            "using": [
                "urn:ietf:params:jmap:core",
                "urn:ietf:params:jmap:mail",
                "urn:ietf:params:jmap:submission",
            ],
            "methodCalls": [list(call) for call in method_calls],
        }
        return _request_json(
            method="POST",
            url=api_url,
            body=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": self.authorization_header(),
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=self.m_timeout_seconds,
        )

    def authorization_header(self) -> str:
        """Return the JMAP authorization header."""

        password = load_stalwart_password(self.m_credential_file)
        token = base64.b64encode(f"{self.m_login_identity}:{password}".encode("utf-8")).decode(
            "ascii"
        )
        return f"Basic {token}"


def _management_auth_headers() -> dict[str, str]:
    """Return Management API auth headers from the ambient environment."""

    bearer_token = _optional_env(STALWART_MANAGEMENT_BEARER_TOKEN_ENV_VAR)
    if bearer_token is not None:
        return {"Authorization": f"Bearer {bearer_token}"}

    api_key = _optional_env(STALWART_MANAGEMENT_API_KEY_ENV_VAR)
    api_secret = _optional_env(STALWART_MANAGEMENT_API_SECRET_ENV_VAR)
    if api_key is not None and api_secret is not None:
        token = base64.b64encode(f"{api_key}:{api_secret}".encode("utf-8")).decode("ascii")
        return {"Authorization": f"Basic {token}"}
    return {}


def _optional_env(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped or None


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _write_secret_file(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _request_json(
    *,
    method: str,
    url: str,
    body: bytes | None,
    headers: Mapping[str, str],
    timeout: float,
) -> dict[str, Any]:
    request_object = request.Request(url=url, data=body, method=method, headers=dict(headers))
    try:
        with request.urlopen(request_object, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise StalwartError(f"{method} {url} failed with status={exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise StalwartError(f"{method} {url} failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise StalwartError(f"{method} {url} returned invalid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise StalwartError(f"{method} {url} returned a non-object JSON payload.")
    return cast(dict[str, Any], payload)


def _require_method_response(
    payload: Mapping[str, object],
    *,
    method_name: str,
    call_id: str,
) -> dict[str, Any]:
    responses = payload.get("methodResponses")
    if not isinstance(responses, list):
        raise StalwartError("JMAP response is missing `methodResponses`.")
    for response_entry in responses:
        if not isinstance(response_entry, list) or len(response_entry) < 3:
            continue
        if response_entry[0] == method_name and response_entry[2] == call_id:
            if isinstance(response_entry[1], dict):
                return cast(dict[str, Any], response_entry[1])
            raise StalwartError(
                f"JMAP {method_name} response for call id `{call_id}` was not an object."
            )
    raise StalwartError(f"JMAP response is missing {method_name} for call id `{call_id}`.")


def _require_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise StalwartError(f"Expected a non-empty string for `{key}`.")
    return value


def _optional_string(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise StalwartError(f"Expected `{key}` to be a string when present.")
    stripped = value.strip()
    return stripped or None


def _coerce_keywords(raw_keywords: object) -> set[str]:
    if not isinstance(raw_keywords, dict):
        return set()
    return {str(key) for key, value in raw_keywords.items() if value is True}


def _coerce_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _coerce_address_list(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        email = item.get("email")
        if not isinstance(email, str) or not email.strip():
            continue
        normalized.append(
            {
                "email": email.strip(),
                "name": str(item.get("name")).strip()
                if isinstance(item.get("name"), str) and str(item.get("name")).strip()
                else "",
            }
        )
    return normalized


def _coerce_attachment_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        blob_id = item.get("blobId")
        if not isinstance(blob_id, str) or not blob_id.strip():
            continue
        normalized.append(
            {
                "blobId": blob_id,
                "name": item.get("name") if isinstance(item.get("name"), str) else None,
                "type": item.get("type") if isinstance(item.get("type"), str) else None,
                "size": item.get("size") if isinstance(item.get("size"), int) else None,
            }
        )
    return normalized


def _extract_text_body(raw_email: Mapping[str, object]) -> str | None:
    text_body = raw_email.get("textBody")
    body_values = raw_email.get("bodyValues")
    if not isinstance(text_body, list) or not isinstance(body_values, dict):
        return None
    collected: list[str] = []
    for body_part in text_body:
        if not isinstance(body_part, dict):
            continue
        part_id = body_part.get("partId")
        if not isinstance(part_id, str):
            continue
        raw_value = body_values.get(part_id)
        if not isinstance(raw_value, dict):
            continue
        value = raw_value.get("value")
        if isinstance(value, str) and value:
            collected.append(value)
    if not collected:
        return None
    return "\n".join(collected)


def _parse_optional_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    return _parse_timestamp(value)


def _parse_timestamp(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
