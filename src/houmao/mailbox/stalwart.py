"""Stalwart provisioning and raw JMAP helpers."""

from __future__ import annotations

import base64
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import wraps
import hashlib
import json
import mimetypes
import ipaddress
import math
import os
from pathlib import Path
import secrets
import shutil
from time import monotonic
from typing import Any, Callable, Iterator, Literal, Mapping, ParamSpec, Sequence, TypeVar, cast
from urllib import error, parse, request

from houmao.mailbox.protocol import validate_mailbox_address
from houmao.mailbox.stalwart_models import (
    JmapEmailChanges,
    JmapMetadataBatch,
    JmapMetadataPage,
    JmapMetadataQuery,
    JmapOperationMeter,
    JmapQueryChanges,
    ValidatedJmapBinding,
)

_JMAP_CORE = "urn:ietf:params:jmap:core"
_JMAP_MAIL = "urn:ietf:params:jmap:mail"
_JMAP_SUBMISSION = "urn:ietf:params:jmap:submission"
_METADATA_PROPERTIES = (
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
    "mailboxIds",
    "size",
    "hasAttachment",
)


_OPERATION_BUDGET: ContextVar[JmapOperationMeter | None] = ContextVar(
    "stalwart_operation_budget", default=None
)
_OperationParameters = ParamSpec("_OperationParameters")
_OperationResult = TypeVar("_OperationResult")


def _bounded_operation(
    method: Callable[_OperationParameters, _OperationResult],
) -> Callable[_OperationParameters, _OperationResult]:
    """Propagate finite caller deadlines through cold discovery and nested helpers."""

    @wraps(method)
    def bounded(
        *args: _OperationParameters.args, **kwargs: _OperationParameters.kwargs
    ) -> _OperationResult:
        """Reuse the current page budget or establish one operation deadline."""
        if _OPERATION_BUDGET.get() is not None:
            return method(*args, **kwargs)
        client = cast("StalwartJmapClient", args[0])
        requested = kwargs.get("timeout_seconds")
        timeout = client._timeout(float(requested) if isinstance(requested, (int, float)) else None)
        token = _OPERATION_BUDGET.set(
            JmapOperationMeter(deadline=monotonic() + timeout, remaining_methods=None)
        )
        try:
            return method(*args, **kwargs)
        finally:
            _OPERATION_BUDGET.reset(token)

    return bounded


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
        raise StalwartError(
            f"Stalwart credential file must contain a JSON object: {credential_file}"
        )
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

    def patch_principal(
        self, principal_id: str, operations: Sequence[Mapping[str, object]]
    ) -> None:
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
        return _request_json(
            method=method, url=url, body=payload, headers=headers, timeout=self.m_timeout_seconds
        )


class StalwartMethodError(StalwartError):
    """A provider explicitly rejected a JMAP method or an individual object."""

    def __init__(self, *, method: str, error_type: str, object_id: str | None = None) -> None:
        self.m_method: str = method
        self.m_error_type: str = error_type
        self.m_object_id: str | None = object_id
        super().__init__(f"JMAP {method} rejected: {error_type}.")

    @property
    def method(self) -> str:
        """Return the rejected method."""
        return self.m_method

    @property
    def error_type(self) -> str:
        """Return the protocol error code, without provider-supplied diagnostic text."""
        return self.m_error_type

    @property
    def object_id(self) -> str | None:
        """Return the rejected provider object, if known."""
        return self.m_object_id


class StalwartMutationError(StalwartError):
    """A failed mutation with explicit acknowledgement and reconciliation information."""

    def __init__(
        self,
        *,
        operation: str,
        outcome: Literal["uncertain", "confirmed", "rejected"],
        email_id: str | None = None,
        submission_id: str | None = None,
    ) -> None:
        self.m_operation: str = operation
        self.m_outcome: Literal["uncertain", "confirmed", "rejected"] = outcome
        self.m_email_id: str | None = email_id
        self.m_submission_id: str | None = submission_id
        super().__init__(f"JMAP {operation} outcome={outcome}; reconcile before repeating.")

    @property
    def operation(self) -> str:
        """Return the attempted mutation."""
        return self.m_operation

    @property
    def outcome(self) -> Literal["uncertain", "confirmed", "rejected"]:
        """Return whether provider acknowledgement is known."""
        return self.m_outcome

    @property
    def email_id(self) -> str | None:
        """Return the known draft/message ID for reconciliation."""
        return self.m_email_id

    @property
    def submission_id(self) -> str | None:
        """Return the confirmed submission ID when available."""
        return self.m_submission_id


class StalwartJmapClient:
    """One immutable credential epoch with bounded JMAP metadata and explicit content APIs."""

    def __init__(
        self,
        *,
        jmap_url: str,
        login_identity: str,
        credential_file: Path,
        timeout_seconds: float = 10.0,
        sender_address: str | None = None,
        account_id: str | None = None,
        identity_id: str | None = None,
        allowed_api_origins: Sequence[str] = (),
    ) -> None:
        self.m_jmap_url: str = _validate_connection_url(jmap_url)
        self.m_login_identity: str = login_identity
        self.m_credential_file: Path = credential_file.resolve()
        self.m_timeout_seconds: float = _finite_timeout(timeout_seconds)
        password = load_stalwart_password(self.m_credential_file)
        token = base64.b64encode(f"{login_identity}:{password}".encode()).decode("ascii")
        self.m_authorization_header: str = f"Basic {token}"
        self.m_session: dict[str, Any] | None = None
        self.m_account_id: str | None = account_id
        self.m_identity_id: str | None = identity_id
        self.m_sender_address: str | None = sender_address
        self.m_mailboxes: list[dict[str, Any]] | None = None
        self.m_roles: dict[str, str] = {}
        self.m_roles_loaded_at: float = 0.0
        self.m_validated_binding: ValidatedJmapBinding | None = None
        self.m_method_call_count: int = 0
        self.m_allowed_origins: set[tuple[str, str, int]] = {
            _url_origin(self.m_jmap_url),
            *(_url_origin(_validate_connection_url(url)) for url in allowed_api_origins),
        }

    @property
    def method_call_count(self) -> int:
        """Return the number of attempted JMAP methods, including failed requests."""
        return self.m_method_call_count

    @contextmanager
    def operation_meter(
        self, *, max_method_calls: int | None = None, timeout_seconds: float | None = None
    ) -> Iterator[JmapOperationMeter]:
        """Count only this execution context, propagating nested page work and failures."""
        if max_method_calls is not None and (
            type(max_method_calls) is not int or max_method_calls < 0
        ):
            raise StalwartError("Method budget must be a non-negative integer.")
        parent = _OPERATION_BUDGET.get()
        allowance = max_method_calls
        if parent is not None and parent.remaining_methods is not None:
            allowance = (
                min(allowance, parent.remaining_methods)
                if allowance is not None
                else parent.remaining_methods
            )
        meter = JmapOperationMeter(
            deadline=monotonic() + self._timeout(timeout_seconds), remaining_methods=allowance
        )
        token = _OPERATION_BUDGET.set(meter)
        try:
            yield meter
        finally:
            _OPERATION_BUDGET.reset(token)
            if parent is not None:
                parent.attempted_methods += meter.attempted_methods
                if parent.remaining_methods is not None:
                    parent.remaining_methods -= meter.attempted_methods

    @property
    def max_objects_in_get(self) -> int:
        """Return the provider's finite get cap, constrained by Houmao's batch maximum."""
        return self._core_limit("maxObjectsInGet", 200)

    @property
    def max_calls_in_request(self) -> int:
        """Return the advertised maximum methods in a request."""
        return self._core_limit("maxCallsInRequest", 16)

    def _core_limit(self, name: str, default: int) -> int:
        """Read a positive advertised core limit."""
        capabilities = self.session().get("capabilities", {})
        core = capabilities.get(_JMAP_CORE, {}) if isinstance(capabilities, dict) else {}
        value = core.get(name) if isinstance(core, dict) else None
        return min(value, default) if type(value) is int and value > 0 else default

    def validate_binding(self, *, sender_address: str | None = None) -> ValidatedJmapBinding:
        """Validate the exact account and authorized address without provisioning anything."""
        address = sender_address or self.m_sender_address
        if address is None:
            raise StalwartError("An explicit sending address is required to validate a binding.")
        address = validate_mailbox_address(address)
        if self.m_sender_address is not None and address.lower() != self.m_sender_address.lower():
            raise StalwartError("Requested sending address differs from the pinned address.")
        if self.m_validated_binding is not None:
            return self.m_validated_binding
        session = self.session()
        account_id = self.primary_account_id()
        accounts = session["accounts"]
        account = accounts[account_id]
        account_capabilities = account.get("accountCapabilities", {})
        if _JMAP_SUBMISSION not in session.get("capabilities", {}) or (
            _JMAP_SUBMISSION not in account_capabilities or account.get("isReadOnly") is True
        ):
            raise StalwartError("Selected account does not support writable mail submission.")
        response = self.call(
            [
                [
                    "Identity/get",
                    {"accountId": account_id, "ids": None, "properties": ["id", "email"]},
                    "identity",
                ]
            ]
        )
        payload = _require_method_response(response, method_name="Identity/get", call_id="identity")
        identities = _require_object_list(payload, "list")
        matches = [
            item
            for item in identities
            if isinstance(item.get("email"), str) and item["email"].lower() == address.lower()
        ]
        if self.m_identity_id is not None:
            matches = [item for item in matches if item.get("id") == self.m_identity_id]
        if len(matches) != 1:
            raise StalwartError("Requested address has no unambiguous authorized sending identity.")
        identity_id = _require_string(matches[0], "id")
        self._load_mailboxes()
        inbox_id = self.mailbox_id_for_role("inbox")
        for mailbox in self.m_mailboxes or []:
            if mailbox.get("id") == inbox_id:
                rights = mailbox.get("myRights")
                if isinstance(rights, dict) and rights.get("mayReadItems") is False:
                    raise StalwartError("Selected inbox does not permit reading messages.")
        self.m_identity_id = identity_id
        self.m_sender_address = address
        result = ValidatedJmapBinding(
            account_id=account_id,
            identity_id=identity_id,
            sender_address=address,
            discovery_url=self.m_jmap_url,
            api_url=_require_string(session, "apiUrl"),
            capabilities=dict(session["capabilities"]),
            mailbox_roles=dict(self.m_roles),
            max_objects_in_get=self.max_objects_in_get,
            max_calls_in_request=self.max_calls_in_request,
        )
        self.m_validated_binding = result
        return result

    def status(self) -> dict[str, Any]:
        """Inspect the selected provider account without exposing credentials."""
        account_id = self.primary_account_id()
        if self.m_sender_address is not None:
            self.validate_binding()
        return {"session": self.session(), "account_id": account_id}

    def query_metadata_page(
        self,
        *,
        query: JmapMetadataQuery,
        limit: int = 50,
        position: int = 0,
        expected_query_state: str | None = None,
        timeout_seconds: float | None = None,
        max_method_calls: int | None = None,
    ) -> JmapMetadataPage:
        """Query an exact metadata view before pagination, checking continuation state."""
        with self.operation_meter(
            max_method_calls=max_method_calls, timeout_seconds=timeout_seconds
        ):
            return self._query_metadata_page(
                query=query,
                limit=limit,
                position=position,
                expected_query_state=expected_query_state,
                timeout_seconds=timeout_seconds,
                max_method_calls=max_method_calls,
            )

    def _query_metadata_page(
        self,
        *,
        query: JmapMetadataQuery,
        limit: int,
        position: int,
        expected_query_state: str | None,
        timeout_seconds: float | None,
        max_method_calls: int | None,
    ) -> JmapMetadataPage:
        """Execute a metadata page under the caller's propagated finite budget."""
        if type(limit) is not int or not 1 <= limit <= 200:
            raise StalwartError("Metadata page limit must be between 1 and 200.")
        if type(position) is not int or position < 0:
            raise StalwartError("Metadata page position must be non-negative.")
        if max_method_calls is not None and max_method_calls < 2:
            raise StalwartError("A metadata page requires a budget of at least two methods.")
        deadline = monotonic() + self._timeout(timeout_seconds)
        before = self._operation_method_count()
        page_limit = min(limit, self.max_objects_in_get)
        old_fingerprint = self.query_fingerprint(query) if self.m_mailboxes is not None else None
        arguments = self._query_arguments(query)
        if old_fingerprint is not None and old_fingerprint != self.query_fingerprint(query):
            raise StalwartMethodError(method="Email/query", error_type="staleCursor")
        arguments.update(position=position, limit=page_limit + 1, calculateTotal=False)
        payload = _require_method_response(
            self.call([["Email/query", arguments, "query"]], timeout_seconds=_remaining(deadline)),
            method_name="Email/query",
            call_id="query",
        )
        query_state = _require_string(payload, "queryState")
        if expected_query_state is not None and query_state != expected_query_state:
            raise StalwartMethodError(method="Email/query", error_type="staleCursor")
        if payload.get("position") != position:
            raise StalwartMethodError(method="Email/query", error_type="staleCursor")
        ids = _require_string_list(payload, "ids")
        if len(ids) > page_limit + 1:
            raise StalwartError("Provider exceeded the requested query page bound.")
        has_more = len(ids) > page_limit
        selected_ids = ids[:page_limit]
        # A server may impose a smaller query cap. A full capped response is not exhaustion.
        if not has_more and selected_ids:
            if (
                max_method_calls is not None
                and self._operation_method_count() - before + 2 > max_method_calls
            ):
                has_more = True
            else:
                probe_args = dict(arguments, position=position + len(selected_ids), limit=1)
                probe = _require_method_response(
                    self.call(
                        [["Email/query", probe_args, "probe"]], timeout_seconds=_remaining(deadline)
                    ),
                    method_name="Email/query",
                    call_id="probe",
                )
                if _require_string(probe, "queryState") != query_state:
                    raise StalwartMethodError(method="Email/query", error_type="staleCursor")
                has_more = bool(_require_string_list(probe, "ids"))
        batch = self.get_metadata(email_ids=selected_ids, timeout_seconds=_remaining(deadline))
        if batch.not_found:
            raise StalwartMethodError(method="Email/query", error_type="staleCursor")
        by_id = {item["id"]: item for item in batch.messages}
        if set(by_id) != set(selected_ids):
            raise StalwartError("Provider metadata response did not reconcile every queried ID.")
        if any(not self.metadata_matches_query(item, query) for item in batch.messages):
            raise StalwartMethodError(method="Email/query", error_type="staleCursor")
        return JmapMetadataPage(
            messages=[by_id[email_id] for email_id in selected_ids],
            query_state=query_state,
            position=position,
            has_more=has_more,
            complete=not has_more,
            next_position=position + len(selected_ids) if has_more else None,
            method_calls=self._operation_method_count() - before,
        )

    @_bounded_operation
    def get_metadata(
        self, *, email_ids: Sequence[str], timeout_seconds: float | None = None
    ) -> JmapMetadataBatch:
        """Retrieve one finite ID batch without body structures or attachment properties."""
        ids = list(dict.fromkeys(email_ids))
        if len(ids) > self.max_objects_in_get:
            raise StalwartError("Metadata batch exceeds the provider get limit.")
        payload = _require_method_response(
            self.call(
                [
                    [
                        "Email/get",
                        {
                            "accountId": self.primary_account_id(),
                            "ids": ids,
                            "properties": list(_METADATA_PROPERTIES),
                        },
                        "metadata",
                    ]
                ],
                timeout_seconds=timeout_seconds,
            ),
            method_name="Email/get",
            call_id="metadata",
        )
        messages = _require_object_list(payload, "list")
        not_found = _require_string_list(payload, "notFound")
        requested = set(ids)
        returned = [_require_string(item, "id") for item in messages]
        if len(returned) != len(set(returned)) or (
            set(returned) | set(not_found) != requested or set(returned) & set(not_found)
        ):
            raise StalwartError("Provider metadata response did not reconcile requested IDs.")
        return JmapMetadataBatch(
            messages=[self._normalize_email(item) for item in messages],
            not_found=not_found,
            state=_require_string(payload, "state"),
        )

    @_bounded_operation
    def email_state(self, *, timeout_seconds: float | None = None) -> str:
        """Capture an object-state boundary without enumerating retained messages."""
        payload = _require_method_response(
            self.call(
                [
                    [
                        "Email/get",
                        {"accountId": self.primary_account_id(), "ids": [], "properties": ["id"]},
                        "state",
                    ]
                ],
                timeout_seconds=timeout_seconds,
            ),
            method_name="Email/get",
            call_id="state",
        )
        return _require_string(payload, "state")

    @_bounded_operation
    def changes(
        self,
        *,
        since_state: str,
        max_changes: int = 100,
        timeout_seconds: float | None = None,
    ) -> JmapEmailChanges:
        """Return one bounded email-object delta, retaining its intermediate state."""
        if type(max_changes) is not int or not 1 <= max_changes <= 500:
            raise StalwartError("Change batch limit must be between 1 and 500.")
        payload = _require_method_response(
            self.call(
                [
                    [
                        "Email/changes",
                        {
                            "accountId": self.primary_account_id(),
                            "sinceState": since_state,
                            "maxChanges": max_changes,
                        },
                        "changes",
                    ]
                ],
                timeout_seconds=timeout_seconds,
            ),
            method_name="Email/changes",
            call_id="changes",
        )
        old_state = _require_string(payload, "oldState")
        if old_state != since_state or not isinstance(payload.get("hasMoreChanges"), bool):
            raise StalwartError("Provider returned inconsistent change-state metadata.")
        created = _require_string_list(payload, "created")
        updated = _require_string_list(payload, "updated")
        destroyed = _require_string_list(payload, "destroyed")
        if len(created) + len(updated) + len(destroyed) > max_changes:
            raise StalwartError("Provider exceeded the requested change batch bound.")
        return JmapEmailChanges(
            old_state=old_state,
            new_state=_require_string(payload, "newState"),
            has_more_changes=payload["hasMoreChanges"],
            created=created,
            updated=updated,
            destroyed=destroyed,
        )

    @_bounded_operation
    def query_changes(
        self,
        *,
        query: JmapMetadataQuery,
        since_query_state: str,
        max_changes: int = 100,
        timeout_seconds: float | None = None,
    ) -> JmapQueryChanges:
        """Expose an optional bounded query delta without inventing object-change pagination."""
        if type(max_changes) is not int or not 1 <= max_changes <= 500:
            raise StalwartError("Query change limit must be between 1 and 500.")
        arguments = self._query_arguments(query)
        arguments.update(
            sinceQueryState=since_query_state, maxChanges=max_changes, calculateTotal=False
        )
        payload = _require_method_response(
            self.call(
                [["Email/queryChanges", arguments, "query-changes"]],
                timeout_seconds=timeout_seconds,
            ),
            method_name="Email/queryChanges",
            call_id="query-changes",
        )
        removed = _require_string_list(payload, "removed")
        added = _require_object_list(payload, "added")
        if len(removed) + len(added) > max_changes:
            raise StalwartMethodError(method="Email/queryChanges", error_type="tooManyChanges")
        for item in added:
            _require_string(item, "id")
            if type(item.get("index")) is not int or item["index"] < 0:
                raise StalwartError("Provider query delta contains an invalid position.")
        if _require_string(payload, "oldQueryState") != since_query_state:
            raise StalwartError("Provider returned a mismatched query-state boundary.")
        return JmapQueryChanges(
            old_query_state=since_query_state,
            new_query_state=_require_string(payload, "newQueryState"),
            removed=removed,
            added=added,
            total_count=payload.get("total") if type(payload.get("total")) is int else None,
        )

    def query_fingerprint(self, query: JmapMetadataQuery) -> str:
        """Fingerprint prepared role state without network I/O or unbudgeted refresh."""
        arguments = self._query_arguments(query, refresh_roles=False)
        return hashlib.sha256(
            json.dumps(arguments, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def _query_arguments(
        self, query: JmapMetadataQuery, *, refresh_roles: bool = True
    ) -> dict[str, Any]:
        """Build only explicitly supported server filters, never an account-wide fallback."""
        if query.read_state not in {"any", "read", "unread"}:
            raise StalwartError("Unsupported read-state filter.")
        if query.answered_state not in {"any", "answered", "unanswered"}:
            raise StalwartError("Unsupported answered-state filter.")
        if query.archived is not None and not isinstance(query.archived, bool):
            raise StalwartError("Archive-membership filter must be boolean or absent.")
        if refresh_roles:
            self._load_mailboxes()
        conditions: list[dict[str, Any]] = [{"inMailbox": self._cached_mailbox_id(query.box)}]
        if query.read_state != "any":
            conditions.append(
                {"hasKeyword" if query.read_state == "read" else "notKeyword": "$seen"}
            )
        if query.answered_state != "any":
            conditions.append(
                {"hasKeyword" if query.answered_state == "answered" else "notKeyword": "$answered"}
            )
        if query.archived is not None:
            archive = {"inMailbox": self._cached_mailbox_id("archive")}
            conditions.append(
                archive if query.archived else {"operator": "NOT", "conditions": [archive]}
            )
        if query.since is not None:
            timestamp = _parse_timestamp(query.since)
            conditions.append(
                {"after": timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")}
            )
        return {
            "accountId": self.primary_account_id(),
            "filter": conditions[0]
            if len(conditions) == 1
            else {"operator": "AND", "conditions": conditions},
            "sort": [{"property": "receivedAt", "isAscending": False}],
            "collapseThreads": False,
        }

    def metadata_matches_query(self, message: Mapping[str, Any], query: JmapMetadataQuery) -> bool:
        """Evaluate an exact cached view from full memberships without issuing a request."""
        if self.m_mailboxes is None:
            raise StalwartError("Validate mailbox roles before matching cached metadata.")
        mailbox_ids = message.get("mailboxIds", {})
        if not isinstance(mailbox_ids, dict) or not mailbox_ids.get(
            self.m_roles.get(query.box, "")
        ):
            return False
        if query.archived is not None:
            archive_id = self.m_roles.get("archive")
            if archive_id is None:
                raise StalwartError("Required mailbox role `archive` is unavailable.")
            if bool(mailbox_ids.get(archive_id)) != query.archived:
                return False
        read = bool(message.get("read"))
        answered = bool(message.get("answered"))
        if query.read_state != "any" and read != (query.read_state == "read"):
            return False
        if query.answered_state != "any" and answered != (query.answered_state == "answered"):
            return False
        return query.since is None or _parse_timestamp(
            _require_string(message, "receivedAt")
        ) > _parse_timestamp(query.since)

    def list_messages(
        self,
        *,
        box: str,
        read_state: str,
        answered_state: str,
        archived: bool | None,
        limit: int | None,
        since: str | None,
    ) -> list[dict[str, Any]]:
        """Return one bounded metadata page; explicit content uses get_content."""
        return self.query_metadata_page(
            query=JmapMetadataQuery(box, read_state, answered_state, archived, since),
            limit=50 if limit is None else limit,
        ).messages

    def check(
        self, *, unread_only: bool, limit: int | None, since: str | None
    ) -> list[dict[str, Any]]:
        """Return one bounded inbox metadata sample."""
        return self.list_messages(
            box="inbox",
            read_state="unread" if unread_only else "any",
            answered_state="any",
            archived=False,
            limit=limit,
            since=since,
        )

    @_bounded_operation
    def get_content(
        self,
        *,
        email_id: str,
        max_body_value_bytes: int = 1048576,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        """Read selected text with visible truncation, encoding, and aggregate limits."""
        if type(max_body_value_bytes) is not int or not 1 <= max_body_value_bytes <= 1048576:
            raise StalwartError("Content byte limit must be between 1 and 1048576.")
        self._load_mailboxes()
        payload = _require_method_response(
            self.call(
                [
                    [
                        "Email/get",
                        {
                            "accountId": self.primary_account_id(),
                            "ids": [email_id],
                            "properties": [
                                *_METADATA_PROPERTIES,
                                "attachments",
                                "textBody",
                                "bodyValues",
                            ],
                            "fetchTextBodyValues": True,
                            "maxBodyValueBytes": max_body_value_bytes,
                        },
                        "content",
                    ]
                ],
                timeout_seconds=timeout_seconds,
            ),
            method_name="Email/get",
            call_id="content",
        )
        emails = _require_object_list(payload, "list")
        if len(emails) != 1 or emails[0].get("id") != email_id:
            raise StalwartMethodError(method="Email/get", error_type="notFound", object_id=email_id)
        raw_email = emails[0]
        normalized = self._normalize_email(raw_email)
        parts = raw_email.get("textBody", [])
        values = raw_email.get("bodyValues", {})
        texts: list[str] = []
        reasons: set[str] = set()
        if not isinstance(parts, list) or not isinstance(values, dict):
            raise StalwartError("Provider returned invalid selected content.")
        if not parts:
            reasons.add("text_body_unavailable")
        for part in parts:
            value = values.get(part.get("partId")) if isinstance(part, dict) else None
            if not isinstance(value, dict) or not isinstance(value.get("value"), str):
                reasons.add("missing_body_value")
                continue
            texts.append(value["value"])
            if value.get("isTruncated") is not False:
                reasons.add(
                    "body_value_truncated" if value.get("isTruncated") else "unknown_completeness"
                )
            if value.get("isEncodingProblem") is True:
                reasons.add("encoding_problem")
        content = "\n".join(texts)
        if len(content.encode()) > max_body_value_bytes:
            content = content.encode()[:max_body_value_bytes].decode("utf-8", errors="ignore")
            reasons.add("aggregate_content_limit")
        normalized.update(
            body=content,
            attachments=_coerce_attachment_list(raw_email.get("attachments")),
            content_complete=not reasons,
            content_limit_bytes=max_body_value_bytes,
            content_limit_reason=",".join(sorted(reasons)) if reasons else None,
        )
        return normalized

    def get_email(self, *, email_id: str) -> dict[str, Any]:
        """Retrieve explicitly selected content; metadata paths never call this method."""
        return self.get_content(email_id=email_id)

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
        """Create and submit once, preserving acknowledgement if later inspection fails."""
        binding = self.validate_binding(sender_address=sender_address)
        for address in (*to_addresses, *cc_addresses):
            validate_mailbox_address(address)
        sent_mailbox_id = self.mailbox_id_for_role("sent")
        self._assert_mailbox_right(sent_mailbox_id, "mayAddItems")
        attachment_parts = self.upload_attachments(
            account_id=binding.account_id, attachments=attachments
        )
        create_payload: dict[str, Any] = {
            "from": [{"email": sender_address}],
            "to": [{"email": value} for value in to_addresses],
            "cc": [{"email": value} for value in cc_addresses],
            "subject": subject,
            "keywords": {},
            "bodyValues": {"text-1": {"value": body_content}},
            "textBody": [{"partId": "text-1", "type": "text/plain"}],
            "mailboxIds": {sent_mailbox_id: True},
        }
        if attachment_parts:
            create_payload["attachments"] = attachment_parts
        if in_reply_to:
            create_payload["header:In-Reply-To:asMessageIds"] = list(in_reply_to)
        if references:
            create_payload["header:References:asMessageIds"] = list(references)
        try:
            response = self.call(
                [
                    [
                        "Email/set",
                        {"accountId": binding.account_id, "create": {"mail-1": create_payload}},
                        "create",
                    ]
                ]
            )
            created = _require_method_response(response, method_name="Email/set", call_id="create")
            _assert_set_result(created, method="Email/set", key="mail-1", action="create")
            email_id = _require_string(created["created"]["mail-1"], "id")
        except StalwartMethodError:
            raise
        except StalwartError as exc:
            raise StalwartMutationError(operation="send-create", outcome="uncertain") from exc
        try:
            response = self.call(
                [
                    [
                        "EmailSubmission/set",
                        {
                            "accountId": binding.account_id,
                            "create": {
                                "submission-1": {
                                    "identityId": binding.identity_id,
                                    "emailId": email_id,
                                }
                            },
                        },
                        "submit",
                    ]
                ]
            )
            submitted = _require_method_response(
                response, method_name="EmailSubmission/set", call_id="submit"
            )
            _assert_set_result(
                submitted, method="EmailSubmission/set", key="submission-1", action="create"
            )
            submission_id = _require_string(submitted["created"]["submission-1"], "id")
        except StalwartMethodError as exc:
            raise StalwartMutationError(
                operation="send-submit", outcome="rejected", email_id=email_id
            ) from exc
        except StalwartError as exc:
            raise StalwartMutationError(
                operation="send-submit", outcome="uncertain", email_id=email_id
            ) from exc
        try:
            result = self._one_metadata(email_id)
        except StalwartError as exc:
            raise StalwartMutationError(
                operation="send-followup",
                outcome="confirmed",
                email_id=email_id,
                submission_id=submission_id,
            ) from exc
        result["mutation_receipt"] = {
            "operation": "send",
            "outcome": "confirmed",
            "email_id": email_id,
            "submission_id": submission_id,
        }
        return result

    def reply(
        self,
        *,
        message_ref: str,
        sender_address: str,
        body_content: str,
        attachments: Sequence[Path],
    ) -> dict[str, Any]:
        """Submit one reply from parent metadata, then acknowledge the parent separately."""
        email_id = _raw_email_id(message_ref)
        original = self._one_metadata(email_id)
        targets = original["replyTo"] or original["from"]
        if not targets:
            raise StalwartError("Reply target has no sender metadata.")
        subject = original["subject"]
        references = list(original["references"])
        in_reply_to = original["messageId"][-1:]
        sent = self.send(
            sender_address=sender_address,
            to_addresses=[item["email"] for item in targets],
            cc_addresses=(),
            subject=subject if subject.lower().startswith("re:") else f"Re: {subject}",
            body_content=body_content,
            attachments=attachments,
            in_reply_to=in_reply_to,
            references=[*references, *in_reply_to],
        )
        try:
            self.mark(message_ref=email_id, read=True, answered=True, archived=None)
        except StalwartError as exc:
            receipt = sent["mutation_receipt"]
            raise StalwartMutationError(
                operation="reply-parent-followup",
                outcome="confirmed",
                email_id=sent["id"],
                submission_id=receipt["submission_id"],
            ) from exc
        sent["mutation_receipt"]["operation"] = "reply"
        return sent

    def mark(
        self, *, message_ref: str, read: bool | None, answered: bool | None, archived: bool | None
    ) -> dict[str, Any]:
        """Apply one acknowledged patch; partial and uncertain results are never retried."""
        email_id = _raw_email_id(message_ref)
        patch: dict[str, object] = {}
        original = self._one_metadata(email_id)
        mailbox_ids = original["mailboxIds"]
        if read is not None:
            patch["keywords/$seen"] = True if read else None
        if answered is not None:
            patch["keywords/$answered"] = True if answered else None
        if archived is not None:
            destination = self.mailbox_id_for_role("archive" if archived else "inbox")
            self._assert_mailbox_right(destination, "mayAddItems")
            patch[f"mailboxIds/{destination}"] = True
            for mailbox_id in mailbox_ids:
                if mailbox_id != destination:
                    self._assert_mailbox_right(mailbox_id, "mayRemoveItems")
                    patch[f"mailboxIds/{mailbox_id}"] = None
            if archived:
                patch["keywords/$seen"] = True
        for mailbox_id in mailbox_ids:
            if read is not None or archived is True:
                self._assert_mailbox_right(mailbox_id, "maySetSeen")
            if answered is not None:
                self._assert_mailbox_right(mailbox_id, "maySetKeywords")
        return self._apply_patch(email_id, patch, operation="mark") if patch else original

    def update_read_state(self, *, message_ref: str, read: bool) -> dict[str, Any]:
        """Update the provider's read flag without requesting content."""
        return self.mark(message_ref=message_ref, read=read, answered=None, archived=None)

    def move(self, *, message_ref: str, destination_box: str) -> dict[str, Any]:
        """Move once between explicit roles and return metadata only."""
        email_id = _raw_email_id(message_ref)
        destination = self.mailbox_id_for_role(destination_box)
        self._assert_mailbox_right(destination, "mayAddItems")
        original = self._one_metadata(email_id)
        patch: dict[str, object] = {f"mailboxIds/{destination}": True}
        for mailbox_id in original["mailboxIds"]:
            if mailbox_id != destination:
                self._assert_mailbox_right(mailbox_id, "mayRemoveItems")
                patch[f"mailboxIds/{mailbox_id}"] = None
            if destination_box == "archive":
                self._assert_mailbox_right(mailbox_id, "maySetSeen")
        if destination_box == "archive":
            patch["keywords/$seen"] = True
        return self._apply_patch(email_id, patch, operation="move")

    def archive(self, *, message_ref: str) -> dict[str, Any]:
        """Archive provider work, removing inbox membership and marking it read."""
        return self.move(message_ref=message_ref, destination_box="archive")

    def _apply_patch(
        self, email_id: str, patch: dict[str, object], *, operation: str
    ) -> dict[str, Any]:
        """Apply and inspect one patch while preserving its acknowledgement boundary."""
        try:
            response = self.call(
                [
                    [
                        "Email/set",
                        {"accountId": self.primary_account_id(), "update": {email_id: patch}},
                        "patch",
                    ]
                ]
            )
            payload = _require_method_response(response, method_name="Email/set", call_id="patch")
            _assert_set_result(payload, method="Email/set", key=email_id, action="update")
        except StalwartMethodError:
            raise
        except StalwartError as exc:
            raise StalwartMutationError(
                operation=operation, outcome="uncertain", email_id=email_id
            ) from exc
        try:
            return self._one_metadata(email_id)
        except StalwartError as exc:
            raise StalwartMutationError(
                operation=operation, outcome="confirmed", email_id=email_id
            ) from exc

    def _one_metadata(self, email_id: str) -> dict[str, Any]:
        """Require a selected message using metadata only."""
        batch = self.get_metadata(email_ids=[email_id])
        if not batch.messages:
            raise StalwartMethodError(method="Email/get", error_type="notFound", object_id=email_id)
        return batch.messages[0]

    def upload_attachments(
        self, *, account_id: str, attachments: Sequence[Path]
    ) -> list[dict[str, Any]]:
        """Upload only explicitly supplied files through the validated connection policy."""
        template = _require_string(self.session(), "uploadUrl")
        url = template.replace("{accountId}", parse.quote(account_id, safe=""))
        self._validate_advertised_url(url)
        parts: list[dict[str, Any]] = []
        for path in attachments:
            media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            payload = _request_json(
                method="POST",
                url=url,
                body=path.read_bytes(),
                headers={
                    "Authorization": self.authorization_header(),
                    "Content-Type": media_type,
                    "Accept": "application/json",
                },
                timeout=self.m_timeout_seconds,
            )
            parts.append(
                {
                    "blobId": _require_string(payload, "blobId"),
                    "type": _optional_string(payload, "type") or media_type,
                    "name": path.name,
                    "size": payload.get("size"),
                    "disposition": "attachment",
                }
            )
        return parts

    def primary_identity_id(self) -> str:
        """Return only the explicitly validated sending identity."""
        return self.validate_binding().identity_id

    def mailbox_id_for_role(self, role: str) -> str:
        """Require one unambiguous role; never widen a missing-role query."""
        self._load_mailboxes()
        return self._cached_mailbox_id(role)

    def _cached_mailbox_id(self, role: str) -> str:
        """Require a prepared role without performing any network operation."""
        if self.m_mailboxes is None:
            raise StalwartError("Validate mailbox roles before preparing a query fingerprint.")
        mailbox_id = self.m_roles.get(role)
        if mailbox_id is None:
            raise StalwartError(f"Required mailbox role `{role}` is unavailable.")
        return mailbox_id

    def _load_mailboxes(self) -> None:
        """Reuse mailbox roles per epoch, with a finite sixty-second refresh policy."""
        if self.m_mailboxes is not None and monotonic() - self.m_roles_loaded_at < 60:
            return
        payload = _require_method_response(
            self.call(
                [
                    [
                        "Mailbox/get",
                        {
                            "accountId": self.primary_account_id(),
                            "ids": None,
                            "properties": ["id", "role", "name", "myRights"],
                        },
                        "roles",
                    ]
                ]
            ),
            method_name="Mailbox/get",
            call_id="roles",
        )
        mailboxes = _require_object_list(payload, "list")
        roles: dict[str, str] = {}
        for mailbox in mailboxes:
            role = mailbox.get("role")
            if isinstance(role, str) and role:
                if role in roles:
                    raise StalwartError("Provider returned an ambiguous mailbox role.")
                roles[role] = _require_string(mailbox, "id")
        self.m_mailboxes = mailboxes
        self.m_roles = roles
        self.m_roles_loaded_at = monotonic()

    def _assert_mailbox_right(self, mailbox_id: str, right: str) -> None:
        """Reject explicitly denied provider mailbox permissions before mutation."""
        self._load_mailboxes()
        for mailbox in self.m_mailboxes or []:
            if mailbox.get("id") == mailbox_id:
                rights = mailbox.get("myRights")
                if isinstance(rights, dict) and rights.get(right) is False:
                    raise StalwartError(f"Selected mailbox does not permit {right}.")
                return
        raise StalwartError("Provider mailbox is no longer available.")

    def _box_name_for_mailbox_ids(self, value: object) -> str | None:
        """Normalize memberships from cached roles, preferring inbox over archive."""
        if not isinstance(value, dict):
            return None
        for role in ("inbox", "sent", "archive"):
            if value.get(self.m_roles.get(role, "")):
                return role
        return next(
            (role for role, mailbox_id in self.m_roles.items() if value.get(mailbox_id)), None
        )

    def _normalize_email(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        """Project metadata without fetching roles or including selected content."""
        keywords = _coerce_keywords(raw.get("keywords"))
        memberships = raw.get("mailboxIds")
        memberships = dict(memberships) if isinstance(memberships, dict) else {}
        return {
            "id": _require_string(raw, "id"),
            "threadId": _optional_string(raw, "threadId"),
            "receivedAt": _require_string(raw, "receivedAt"),
            "messageId": _coerce_string_list(raw.get("messageId")),
            "inReplyTo": _coerce_string_list(raw.get("inReplyTo")),
            "references": _coerce_string_list(raw.get("references")),
            "from": _coerce_address_list(raw.get("from")),
            "to": _coerce_address_list(raw.get("to")),
            "cc": _coerce_address_list(raw.get("cc")),
            "replyTo": _coerce_address_list(raw.get("replyTo")),
            "subject": _optional_string(raw, "subject") or "(no subject)",
            "preview": (_optional_string(raw, "preview") or "")[:512],
            "body": None,
            "attachments": [],
            "hasAttachment": raw.get("hasAttachment") is True,
            "size": raw.get("size"),
            "keywords": {keyword: True for keyword in keywords},
            "mailboxIds": memberships,
            "read": "$seen" in keywords,
            "answered": "$answered" in keywords,
            "unread": "$seen" not in keywords,
            "archived": bool(memberships.get(self.m_roles.get("archive", ""))),
            "box": self._box_name_for_mailbox_ids(memberships),
            "content_complete": None,
            "content_limit_bytes": None,
            "content_limit_reason": None,
        }

    def primary_account_id(self) -> str:
        """Select the pinned, valid primary, or sole eligible account, never the first."""
        session = self.session()
        accounts = session.get("accounts")
        if not isinstance(accounts, dict):
            raise StalwartError("JMAP session has no usable mail accounts.")
        eligible = {
            key
            for key, account in accounts.items()
            if isinstance(key, str)
            and key
            and isinstance(account, dict)
            and isinstance(account.get("accountCapabilities"), dict)
            and _JMAP_MAIL in account["accountCapabilities"]
        }
        account_id = self.m_account_id
        if account_id is None:
            primary = session.get("primaryAccounts", {})
            candidate = primary.get(_JMAP_MAIL) if isinstance(primary, dict) else None
            if isinstance(candidate, str) and candidate in eligible:
                account_id = candidate
            elif len(eligible) == 1:
                account_id = next(iter(eligible))
        if account_id is None or account_id not in eligible:
            raise StalwartError("JMAP account selection is missing, ambiguous, or unauthorized.")
        self.m_account_id = account_id
        return account_id

    def session(self) -> dict[str, Any]:
        """Discover once and validate the advertised request origin and capabilities."""
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
            timeout=self._timeout(None),
        )
        capabilities = payload.get("capabilities")
        if (
            not isinstance(capabilities, dict)
            or not {_JMAP_CORE, _JMAP_MAIL} <= capabilities.keys()
        ):
            raise StalwartError("JMAP session lacks required core/mail capabilities.")
        self._validate_advertised_url(_require_string(payload, "apiUrl"))
        self.m_session = payload
        return payload

    def _validate_advertised_url(self, url: str) -> None:
        """Reject credential forwarding to an unapproved advertised origin."""
        if _url_origin(_validate_connection_url(url)) not in self.m_allowed_origins:
            raise StalwartError("Advertised JMAP URL has an unapproved origin.")

    def _timeout(self, timeout_seconds: float | None) -> float:
        """Constrain a finite operation timeout to the connection request limit."""
        timeout = (
            min(self.m_timeout_seconds, _finite_timeout(timeout_seconds))
            if timeout_seconds is not None
            else self.m_timeout_seconds
        )
        budget = _OPERATION_BUDGET.get()
        return min(timeout, _remaining(budget.deadline)) if budget is not None else timeout

    def _operation_method_count(self) -> int:
        """Read the current operation's counter without charging concurrent requests."""
        budget = _OPERATION_BUDGET.get()
        return budget.attempted_methods if budget is not None else self.method_call_count

    @_bounded_operation
    def call(
        self, method_calls: Sequence[Sequence[object]], *, timeout_seconds: float | None = None
    ) -> dict[str, Any]:
        """Call a finite method envelope with no retries and count each attempted method."""
        session = self.session()
        if not method_calls or len(method_calls) > self.max_calls_in_request:
            raise StalwartError("JMAP method envelope exceeds the provider call limit.")
        budget = _OPERATION_BUDGET.get()
        if budget is not None and budget.remaining_methods is not None:
            if len(method_calls) > budget.remaining_methods:
                raise StalwartError("JMAP operation method budget is exhausted.")
            budget.remaining_methods -= len(method_calls)
        if budget is not None:
            budget.attempted_methods += len(method_calls)
        capabilities = session["capabilities"]
        using = [_JMAP_CORE, _JMAP_MAIL]
        if _JMAP_SUBMISSION in capabilities:
            using.append(_JMAP_SUBMISSION)
        self.m_method_call_count += len(method_calls)
        return _request_json(
            method="POST",
            url=_require_string(session, "apiUrl"),
            body=json.dumps(
                {"using": using, "methodCalls": [list(item) for item in method_calls]}
            ).encode(),
            headers={
                "Authorization": self.authorization_header(),
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=self._timeout(timeout_seconds),
        )

    def authorization_header(self) -> str:
        """Return the immutable epoch credential, never rereading an external source."""
        return self.m_authorization_header


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
        with request.build_opener(_NoCredentialRedirect()).open(
            request_object, timeout=timeout
        ) as response:
            content = response.read(8 * 1024 * 1024 + 1)
            if len(content) > 8 * 1024 * 1024:
                raise StalwartError("Provider response exceeds the supported 8 MiB transfer limit.")
            payload = json.loads(content.decode("utf-8"))
    except error.HTTPError as exc:
        raise StalwartError(f"Provider HTTP {method} failed with status={exc.code}.") from exc
    except (error.URLError, TimeoutError, OSError) as exc:
        raise StalwartError(f"Provider HTTP {method} connection failed or timed out.") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise StalwartError(f"Provider HTTP {method} returned invalid JSON.") from exc

    if not isinstance(payload, dict):
        raise StalwartError(f"Provider HTTP {method} returned a non-object JSON payload.")
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
        if response_entry[0] == "error" and response_entry[2] == call_id:
            detail = response_entry[1]
            error_type = detail.get("type") if isinstance(detail, dict) else None
            raise StalwartMethodError(method=method_name, error_type=_safe_error_type(error_type))
        if response_entry[0] == method_name and response_entry[2] == call_id:
            if isinstance(response_entry[1], dict):
                return cast(dict[str, Any], response_entry[1])
            raise StalwartError(
                f"JMAP {method_name} response for call id `{call_id}` was not an object."
            )
    raise StalwartError(f"JMAP response is missing {method_name} for call id `{call_id}`.")


class _NoCredentialRedirect(request.HTTPRedirectHandler):
    """Allow only same-origin discovery GET redirects, never mutation replay."""

    def redirect_request(
        self,
        req: request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> request.Request | None:
        """Keep redirected discovery within its authorized origin and standard hop cap."""
        if req.get_method() != "GET" or _url_origin(req.full_url) != _url_origin(newurl):
            return None
        _validate_connection_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _url_origin(url: str) -> tuple[str, str, int]:
    """Return a normalized origin including its effective port."""
    parsed = parse.urlsplit(url)
    return (
        parsed.scheme.lower(),
        (parsed.hostname or "").lower(),
        parsed.port or (443 if parsed.scheme.lower() == "https" else 80),
    )


def _validate_connection_url(url: str) -> str:
    """Require HTTPS or loopback HTTP without embedded credentials or fragments."""
    try:
        parsed = parse.urlsplit(url)
        host = parsed.hostname or ""
        parsed.port
    except ValueError as exc:
        raise StalwartError("Invalid JMAP connection URL.") from exc
    if not host or parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise StalwartError("JMAP URLs require a host and cannot contain credentials or fragments.")
    loopback = host.lower() == "localhost"
    try:
        loopback = loopback or ipaddress.ip_address(host).is_loopback
    except ValueError:
        pass
    if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
        raise StalwartError("JMAP connections require HTTPS or loopback HTTP.")
    return url


def _finite_timeout(value: float) -> float:
    """Require a positive finite request timeout."""
    if not math.isfinite(value) or value <= 0:
        raise StalwartError("Request timeout must be positive and finite.")
    return value


def _remaining(deadline: float) -> float:
    """Return the positive remaining work budget, failing before another request."""
    return _finite_timeout(deadline - monotonic())


def _require_object_list(payload: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    """Reject incomplete or malformed wire object arrays."""
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise StalwartError(f"JMAP response is missing a valid `{key}` object list.")
    return cast(list[dict[str, Any]], value)


def _require_string_list(payload: Mapping[str, Any], key: str) -> list[str]:
    """Reject incomplete or malformed wire identifier arrays."""
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise StalwartError(f"JMAP response is missing a valid `{key}` identifier list.")
    return cast(list[str], value)


def _safe_error_type(value: object) -> str:
    """Keep only a bounded protocol code, never provider-supplied diagnostic prose."""
    return (
        value
        if isinstance(value, str) and value.isascii() and value.isalnum() and len(value) <= 64
        else "providerError"
    )


def _assert_set_result(
    payload: Mapping[str, Any], *, method: str, key: str, action: Literal["create", "update"]
) -> None:
    """Require positive per-object acknowledgement rather than ignoring notCreated/notUpdated."""
    failure_key = "notCreated" if action == "create" else "notUpdated"
    failures = payload.get(failure_key, {})
    if isinstance(failures, dict) and key in failures:
        detail = failures[key]
        raise StalwartMethodError(
            method=method,
            error_type=_safe_error_type(detail.get("type") if isinstance(detail, dict) else None),
            object_id=key,
        )
    successful = payload.get("created" if action == "create" else "updated")
    if not isinstance(successful, dict) or key not in successful:
        raise StalwartError("Provider did not acknowledge the requested object mutation.")


def _raw_email_id(message_ref: str) -> str:
    """Unwrap only the backend reference prefix, preserving opaque provider IDs."""
    return message_ref.removeprefix("stalwart:")


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


def _parse_timestamp(value: str) -> datetime:
    """Require an explicit RFC3339 timezone for cross-channel boundary consistency."""
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise StalwartError("Timestamp must use RFC3339 with an explicit timezone.") from exc
    if parsed.tzinfo is None:
        raise StalwartError("Timestamp must use RFC3339 with an explicit timezone.")
    return parsed.astimezone(UTC)
