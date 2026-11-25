"""Stalwart provisioning and raw JMAP helpers."""

from __future__ import annotations

import base64
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
import fcntl
from functools import wraps
import hashlib
import ipaddress
import json
import mimetypes
import math
import os
from pathlib import Path
import re
import secrets
import shutil
from tempfile import NamedTemporaryFile
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
_STALWART_REGISTRY = "urn:stalwart:jmap"
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


class StalwartConnectionPolicyError(StalwartError):
    """Carry a safe connection failure code and actionable detail."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(detail)


class StalwartReadinessError(StalwartError):
    """Report a missing or unusable resource for the selected mailbox."""

    code = "mailbox_not_ready"


@dataclass(frozen=True)
class StalwartProvisionedBinding:
    """Provisioned Stalwart mailbox details."""

    jmap_url: str
    management_url: str
    login_identity: str
    credential_ref: str
    credential_file: Path
    account_id: str
    identity_id: str
    api_origin: str
    mailbox_roles: Mapping[str, str]
    management_principal_id: str
    principal_name: str


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
    login_identity: str | None = None,
    trusted_jmap_origins: Sequence[str] = (),
    allow_create_domain: bool = True,
    management_auth_headers: Mapping[str, str] | None = None,
) -> StalwartProvisionedBinding:
    """Explicitly provision an account and verify its JMAP readiness."""

    discovery_origin, _ = _connection_origins(jmap_url, trusted_jmap_origins)
    normalized_address = validate_mailbox_address(address)
    domain = normalized_address.split("@", 1)[1].lower()
    if domain.split(".")[-1] in {"localhost", "test"}:
        raise StalwartReadinessError(
            f"Stalwart cannot create JMAP sending identities under {domain}. "
            "Select a mail domain with a recognized public suffix for this account."
        )
    credential_ref = build_stalwart_credential_ref(address=normalized_address, jmap_url=jmap_url)
    runtime_credential_path = runtime_stalwart_credential_path(runtime_root, credential_ref)
    session_credential_path = session_stalwart_credential_path(session_root, credential_ref)
    management = StalwartManagementClient(
        base_url=management_url, auth_headers=management_auth_headers
    )
    lock_key = build_stalwart_credential_ref(
        address=normalized_address.lower(), jmap_url=discovery_origin
    )
    with _provisioning_lock(runtime_credential_path.parent / f".{lock_key}.lock"):
        try:
            principal = management.find_mailbox_account(principal_id, normalized_address)
            credential_source = runtime_credential_path
            if principal is not None and not credential_source.is_file():
                credential_source = _previous_base_url_credential(
                    runtime_root, normalized_address, jmap_url
                )
            management.ensure_domain(domain, allow_create=allow_create_domain)
            if not credential_source.is_file():
                _write_secret_file(
                    runtime_credential_path,
                    {"credential_ref": credential_ref, "password": secrets.token_urlsafe(24)},
                )
            password = load_stalwart_password(credential_source)
            if principal is None:
                management.create_mailbox_account(
                    principal_id=principal_id, address=normalized_address, password=password
                )
                principal = management.find_mailbox_account(principal_id, normalized_address)
            if principal is None:
                raise StalwartError("The selected account is unavailable after principal creation.")
            principal_name = _require_string(principal, "name")
            principal_login = (
                _require_string(principal, "login") if "login" in principal else principal_name
            )
            provider_id = principal.get("id")
            if type(provider_id) not in {str, int} or not str(provider_id):
                raise StalwartError("The selected account has no management principal ID.")
        except StalwartError as exc:
            raise StalwartError(f"Stalwart principal provisioning failed. {exc}") from None

        login = (
            login_identity
            if login_identity is not None and login_identity.lower() != principal_id.lower()
            else principal_login
        )
        client = StalwartJmapClient(
            jmap_url=jmap_url,
            login_identity=principal_login,
            credential_file=credential_source,
            sender_address=normalized_address,
            allowed_api_origins=trusted_jmap_origins,
        )
        try:
            if login != principal_login:
                account_id = client.primary_account_id()
                api_origin = jmap_origin(_require_string(client.session(), "apiUrl"))
                client = StalwartJmapClient(
                    jmap_url=jmap_url,
                    login_identity=login,
                    credential_file=credential_source,
                    sender_address=normalized_address,
                    allowed_api_origins=trusted_jmap_origins,
                    account_id=account_id,
                    api_origin=api_origin,
                )
            client._ensure_provisioning_resources(normalized_address)
            validated = client.validate_binding()
        except (StalwartConnectionPolicyError, StalwartReadinessError):
            raise
        except StalwartError as exc:
            raise StalwartReadinessError(f"Stalwart JMAP readiness failed. {exc}") from None
        material = {"credential_ref": credential_ref, "login_identity": login, "password": password}
        if credential_source != runtime_credential_path:
            _write_secret_file(runtime_credential_path, material)
        _write_secret_file(session_credential_path, material)

    return StalwartProvisionedBinding(
        jmap_url=jmap_url,
        management_url=management_url,
        login_identity=login,
        credential_ref=credential_ref,
        credential_file=session_credential_path.resolve(),
        account_id=validated.account_id,
        identity_id=validated.identity_id,
        api_origin=jmap_origin(validated.api_url),
        mailbox_roles=validated.mailbox_roles,
        management_principal_id=str(provider_id),
        principal_name=principal_name,
    )


def _previous_base_url_credential(runtime_root: Path, address: str, jmap_url: str) -> Path:
    """Find an existing account's credential under the former derived discovery path."""
    suffix = "/.well-known/jmap"
    if jmap_url.endswith(suffix):
        reference = build_stalwart_credential_ref(
            address=address, jmap_url=f"{jmap_url.removesuffix(suffix)}/jmap"
        )
        candidate = runtime_stalwart_credential_path(runtime_root, reference)
        if candidate.is_file():
            return candidate
    raise StalwartError(
        "The existing principal has no owned provisioning credential. "
        "Attach it using its current mailbox credential."
    )


@contextmanager
def _provisioning_lock(path: Path) -> Iterator[None]:
    """Serialize local provisioning for the same provider and address."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("a") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class StalwartManagementClient:
    """Thin Management API client used for mailbox provisioning."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 10.0,
        auth_headers: Mapping[str, str] | None = None,
    ) -> None:
        jmap_origin(base_url)
        if "?" in base_url:
            raise StalwartError("Management base URL cannot contain a query.")
        self.m_base_url: str = base_url.rstrip("/")
        self.m_registry: bool = parse.urlsplit(self.m_base_url).path.endswith("/jmap")
        self.m_timeout_seconds: float = _finite_timeout(timeout_seconds)
        self.m_auth_headers: dict[str, str] = (
            _management_auth_headers() if auth_headers is None else dict(auth_headers)
        )

    def list_principals(self, *, types: Sequence[str] | None = None) -> list[dict[str, Any]]:
        """List management principals."""

        if self.m_registry:
            return self._list_registry_principals(types)
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

    def ensure_domain(self, domain: str, *, allow_create: bool = True) -> dict[str, Any]:
        """Ensure a domain principal exists."""

        for principal in self.list_principals(types=("domain",)):
            if principal.get("name") == domain:
                return principal
        if not allow_create:
            raise StalwartError(f"Required Stalwart domain {domain} does not exist.")
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

    def find_mailbox_account(self, principal_id: str, address: str) -> dict[str, Any] | None:
        """Read the selected account and reject name or address collisions."""
        selected: dict[str, Any] | None = None
        for principal in self.list_principals(types=("individual",)):
            name = principal.get("name")
            emails = principal.get("emails")
            same_name = isinstance(name, str) and name.lower() == principal_id.lower()
            if self.m_registry:
                login = _require_string(principal, "login").lower()
                domain = address.rsplit("@", 1)[1].lower()
                lookup = principal_id.lower()
                same_name = login == (lookup if "@" in lookup else f"{lookup}@{domain}")
            same_address = isinstance(emails, list) and any(
                isinstance(email, str) and email.lower() == address.lower() for email in emails
            )
            if not (same_name or same_address):
                continue
            if not (same_name and same_address) or selected is not None:
                raise StalwartError(
                    "The selected Stalwart login or address conflicts with an existing account. "
                    "Choose a distinct principal and address or attach the existing account."
                )
            selected = principal
        return selected

    def create_mailbox_account(self, *, principal_id: str, address: str, password: str) -> None:
        """Create one normal account with the selected private credential."""
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

    def create_principal(self, payload: Mapping[str, object]) -> object:
        """Create one management principal."""

        if self.m_registry:
            return self._create_registry_principal(payload)
        response_payload = self._request_json("POST", "/principal", body=payload)
        return response_payload.get("data")

    def delete_mailbox_account(self, *, name: str, provider_id: str) -> None:
        """Delete the selected mailbox by its provider identifier or legacy name."""

        if self.m_registry:
            self.registry_request("Account/set", {"destroy": [provider_id]})
        else:
            self._request_json("DELETE", "/principal/" + parse.quote(name, safe=""))

    def registry_request(self, method: str, arguments: Mapping[str, object]) -> dict[str, Any]:
        """Call one Stalwart registry method and check method and object errors."""

        wire_method = f"x:{method}"
        return self.jmap_request(wire_method, arguments, capability=_STALWART_REGISTRY)

    def jmap_request(
        self, method: str, arguments: Mapping[str, object], *, capability: str = _JMAP_MAIL
    ) -> dict[str, Any]:
        """Call a JMAP method using the configured administrative credentials."""

        if not self.m_registry:
            raise StalwartError("Select a /jmap management URL for Stalwart registry requests.")
        payload = self._request_json(
            "POST",
            "/",
            body={"using": [_JMAP_CORE, capability], "methodCalls": [[method, arguments, "0"]]},
        )
        responses = payload.get("methodResponses")
        if not isinstance(responses, list) or len(responses) != 1:
            raise StalwartError(f"Stalwart returned an invalid response to {method}.")
        response = responses[0]
        if (
            not isinstance(response, list)
            or len(response) != 3
            or not isinstance(response[1], dict)
        ):
            raise StalwartError(f"Stalwart returned an invalid response to {method}.")
        result: dict[str, Any] = response[1]
        if response[0] == "error":
            raise StalwartMethodError(method=method, error_type=str(result.get("type", "unknown")))
        if response[0] != method or response[2] != "0":
            raise StalwartError(f"Stalwart returned an unexpected response to {method}.")
        for key in ("notCreated", "notUpdated", "notDestroyed"):
            failures = result.get(key)
            if isinstance(failures, dict) and failures:
                first = next(iter(failures.values()))
                kind = first.get("type", "unknown") if isinstance(first, dict) else "unknown"
                raise StalwartMethodError(method=method, error_type=str(kind))
        return result

    def list_registry_objects(
        self,
        object_name: str,
        *,
        properties: Sequence[str],
        filters: Mapping[str, object] | None = None,
    ) -> list[dict[str, Any]]:
        """Read registry objects with bounded query and get batches."""

        position = 0
        objects: list[dict[str, Any]] = []
        while True:
            query = self.registry_request(
                f"{object_name}/query",
                {"filter": filters or {}, "position": position, "limit": 100},
            )
            ids = query.get("ids")
            if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
                raise StalwartError(f"Stalwart {object_name}/query returned invalid IDs.")
            if not ids:
                return objects
            fetched = self.registry_request(
                f"{object_name}/get", {"ids": ids, "properties": list(properties)}
            ).get("list")
            if not isinstance(fetched, list) or not all(isinstance(item, dict) for item in fetched):
                raise StalwartError(f"Stalwart {object_name}/get returned invalid objects.")
            objects.extend(fetched)
            if len(ids) < 100:
                return objects
            position += len(ids)

    def _list_registry_principals(self, types: Sequence[str] | None) -> list[dict[str, Any]]:
        """Map Stalwart registry users and domains to the provisioning principal shape."""

        domains = self.list_registry_objects("Domain", properties=("id", "name"))
        principals = (
            [{**row, "type": "domain"} for row in domains]
            if types is None or "domain" in types
            else []
        )
        if types is not None and "individual" not in types:
            return principals
        domains_by_id = {row["id"]: row["name"] for row in domains}
        accounts = self.list_registry_objects(
            "Account",
            properties=(
                "id",
                "@type",
                "name",
                "emailAddress",
                "aliases",
                "roles",
                "permissions",
                "description",
            ),
        )
        for account in accounts:
            if account.get("@type") != "User":
                continue
            login = _require_string(account, "emailAddress")
            emails = [login]
            for alias in account.get("aliases", {}).values():
                domain = domains_by_id.get(alias.get("domainId"))
                if domain and alias.get("enable", True):
                    emails.append(f"{alias['name']}@{domain}")
            principals.append({**account, "type": "individual", "login": login, "emails": emails})
        return principals

    def _create_registry_principal(self, payload: Mapping[str, object]) -> str:
        """Create a domain or mailbox on Stalwart's JMAP management API."""

        kind = _require_string(payload, "type")
        name = _require_string(payload, "name")
        description = payload.get("description")
        if kind == "domain":
            object_name = "Domain"
            record = {
                "name": name,
                "description": description,
                "certificateManagement": {"@type": "Manual"},
                "dkimManagement": {"@type": "Manual"},
                "dnsManagement": {"@type": "Manual"},
            }
        elif kind == "individual":
            object_name = "Account"
            emails = payload.get("emails")
            passwords = payload.get("secrets")
            roles = payload.get("roles")
            if not isinstance(emails, list) or not emails or not isinstance(passwords, list):
                raise StalwartError("Stalwart mailbox creation requires an address and password.")
            addresses = [validate_mailbox_address(address) for address in emails]
            primary_domain = addresses[0].rsplit("@", 1)[1]
            domains = {
                row["name"]: row["id"]
                for row in self.list_registry_objects("Domain", properties=("id", "name"))
            }
            local_name, separator, domain = name.partition("@")
            if separator and domain.casefold() != primary_domain.casefold():
                raise StalwartError(
                    "Stalwart login and primary mailbox address must share a domain."
                )
            if any(address.rsplit("@", 1)[1] not in domains for address in addresses):
                raise StalwartError(
                    "A Stalwart mailbox domain must exist before creating the account."
                )
            aliases = {
                str(index): {"name": local, "domainId": domains[domain_name]}
                for index, (local, domain_name) in enumerate(a.rsplit("@", 1) for a in addresses)
                if f"{local_name}@{primary_domain}".casefold()
                != f"{local}@{domain_name}".casefold()
            }
            record = {
                "@type": "User",
                "name": local_name,
                "domainId": domains[primary_domain],
                "description": description,
                "credentials": {
                    str(index): {"@type": "Password", "secret": password}
                    for index, password in enumerate(passwords)
                },
                "roles": {
                    "@type": "Admin" if isinstance(roles, list) and "admin" in roles else "User"
                },
                "aliases": aliases,
            }
        else:
            raise StalwartError(f"Unsupported Stalwart registry principal type {kind}.")
        reply = self.registry_request(f"{object_name}/set", {"create": {"new": record}})
        return _require_string(reply.get("created", {}).get("new", {}), "id")

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: object | None = None,
    ) -> dict[str, Any]:
        """Send one JSON Management API request."""

        payload: bytes | None = None
        headers = {"Accept": "application/json", **self.m_auth_headers}
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
        api_origin: str | None = None,
    ) -> None:
        discovery_origin, allowed_origins = _connection_origins(jmap_url, allowed_api_origins)
        self.m_jmap_url: str = jmap_url
        self.m_discovery_origin: str = discovery_origin
        self.m_allowed_origins: frozenset[str] = allowed_origins
        self.m_api_origin: str | None = (
            normalize_jmap_origins((api_origin,))[0] if api_origin is not None else None
        )
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

    @_bounded_operation
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
        account_id = self._require_submission_account()
        session = self.session()
        matches = self._matching_identities(account_id, address)
        if len(matches) != 1 or (
            self.m_identity_id is not None and matches[0] != self.m_identity_id
        ):
            raise StalwartReadinessError(
                "Requested address has no unambiguous authorized sending identity. "
                "Configure exactly one Stalwart JMAP identity for this address."
            )
        identity_id = matches[0]
        self._require_lifecycle_rights()
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

    def _require_submission_account(self) -> str:
        """Verify that the selected normal account can submit mail."""
        account_id = self.primary_account_id()
        session = self.session()
        account = session["accounts"][account_id]
        if (
            _JMAP_SUBMISSION not in session["capabilities"]
            or _JMAP_SUBMISSION not in account["accountCapabilities"]
            or account.get("isReadOnly") is not False
        ):
            raise StalwartReadinessError(
                "Selected account does not support writable mail submission. "
                "Enable JMAP mail submission for this account."
            )
        return account_id

    def _matching_identities(self, account_id: str, address: str) -> list[str]:
        """Read identity IDs that exactly match the requested sending address."""
        payload = _require_method_response(
            self.call(
                [
                    [
                        "Identity/get",
                        {"accountId": account_id, "ids": None, "properties": ["id", "email"]},
                        "identity",
                    ]
                ]
            ),
            method_name="Identity/get",
            call_id="identity",
        )
        return [
            _require_string(item, "id")
            for item in _require_object_list(payload, "list")
            if isinstance(item.get("email"), str) and item["email"].lower() == address.lower()
        ]

    def _require_lifecycle_rights(self) -> None:
        """Validate the roles and rights Houmao needs to read, send, reply, and archive."""
        self._load_mailboxes()
        by_id = {
            mailbox["id"]: mailbox
            for mailbox in self.m_mailboxes or []
            if isinstance(mailbox.get("id"), str)
        }
        for role, required in (
            ("inbox", ("mayReadItems", "maySetSeen", "maySetKeywords", "mayRemoveItems")),
            ("sent", ("mayAddItems",)),
            ("archive", ("mayAddItems",)),
        ):
            mailbox_id = self._cached_mailbox_id(role)
            rights = by_id[mailbox_id].get("myRights")
            for right in required:
                if not isinstance(rights, dict) or rights.get(right) is not True:
                    raise StalwartReadinessError(
                        f"Mailbox role `{role}` requires permission `{right}`. "
                        "Grant that right on the selected mailbox."
                    )

    @_bounded_operation
    def _ensure_provisioning_resources(self, address: str) -> None:
        """Create missing resources only during explicitly selected provisioning."""
        account_id = self._require_submission_account()
        matches = self._matching_identities(account_id, address)
        if len(matches) > 1:
            raise StalwartReadinessError(
                "Requested address has no unambiguous authorized sending identity. "
                "Resolve the duplicate identities before retrying provisioning."
            )
        self._load_mailboxes()
        missing_archive = "archive" not in self.m_roles
        if missing_archive and any(
            isinstance(mailbox.get("name"), str) and mailbox["name"].lower() == "archive"
            for mailbox in self.m_mailboxes or []
        ):
            raise StalwartReadinessError(
                "The Archive folder has no `archive` role. Assign the role to that folder "
                "or rename it before retrying provisioning."
            )
        if not matches:
            self._create_provisioning_resource(
                "Identity/set", account_id, {"name": address, "email": address}, "sending identity"
            )
        if missing_archive:
            self._create_provisioning_resource(
                "Mailbox/set", account_id, {"name": "Archive", "role": "archive"}, "Archive role"
            )
            self.m_mailboxes = None

    def _create_provisioning_resource(
        self, method: str, account_id: str, value: Mapping[str, str], resource: str
    ) -> None:
        """Create and require an explicit acknowledgement of one JMAP resource."""
        try:
            payload = _require_method_response(
                self.call(
                    [[method, {"accountId": account_id, "create": {"resource": value}}, "set"]]
                ),
                method_name=method,
                call_id="set",
            )
            _assert_set_result(payload, method=method, key="resource", action="create")
        except StalwartMethodError as exc:
            raise StalwartReadinessError(
                f"Stalwart rejected creation of the {resource} ({exc.error_type}). "
                "Check the account's sender address, domain, and mailbox permissions before retrying."
            ) from None

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
                timeout=self._timeout(None),
                mailbox_request=True,
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
            raise StalwartReadinessError(
                f"Required mailbox role `{role}` is unavailable. "
                "Assign that role to the selected account's folder."
            )
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
                    raise StalwartReadinessError(
                        "Provider returned an ambiguous mailbox role. "
                        "Assign each required role to a single folder."
                    )
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
            redirect_origin=self.m_discovery_origin,
            mailbox_request=True,
        )
        capabilities = payload.get("capabilities")
        if (
            not isinstance(capabilities, dict)
            or not {_JMAP_CORE, _JMAP_MAIL} <= capabilities.keys()
        ):
            raise StalwartReadinessError(
                "JMAP session lacks required core/mail capabilities. "
                "Enable JMAP mail for the selected account."
            )
        self._validated_api_url(payload)
        self._validate_advertised_url(_require_string(payload, "uploadUrl"))
        self.m_session = payload
        return payload

    def _validate_advertised_url(self, url: str, *, pinned_origin: str | None = None) -> None:
        """Reject credential forwarding to an unapproved advertised origin."""
        origin = jmap_origin(url)
        if pinned_origin is not None and origin != pinned_origin:
            raise StalwartConnectionPolicyError(
                "jmap_api_origin_changed",
                f"The JMAP method origin changed from {pinned_origin} to {origin}. "
                "Restore the selected provider or explicitly replace the online binding.",
            )
        if origin not in self.m_allowed_origins:
            raise StalwartConnectionPolicyError(
                "jmap_origin_unapproved",
                f"JMAP origin {origin} is unapproved. Verify the endpoint and approve this exact "
                "origin or configure the provider to advertise an approved HTTPS origin.",
            )

    def _validated_api_url(self, session: Mapping[str, object]) -> str:
        """Keep JMAP methods within the pinned provider's origin."""
        url = _require_string(session, "apiUrl")
        self._validate_advertised_url(url, pinned_origin=self.m_api_origin)
        return url

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
            url=self._validated_api_url(session),
            body=json.dumps(
                {"using": using, "methodCalls": [list(item) for item in method_calls]}
            ).encode(),
            headers={
                "Authorization": self.authorization_header(),
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=self._timeout(timeout_seconds),
            mailbox_request=True,
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
    """Publish a secret atomically from the same directory with mode 0600."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with NamedTemporaryFile(
        mode="w", dir=path.parent, prefix=f".{path.name}.", encoding="utf-8", delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(dict(payload), stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def _request_json(
    *,
    method: str,
    url: str,
    body: bytes | None,
    headers: Mapping[str, str],
    timeout: float,
    redirect_origin: str | None = None,
    mailbox_request: bool = False,
) -> dict[str, Any]:
    request_object = request.Request(url=url, data=body, method=method, headers=dict(headers))
    handlers: list[request.BaseHandler] = [_NoCredentialRedirect(redirect_origin)]
    if mailbox_request and request_object.type == "http":
        # A plaintext proxy would receive the mailbox Authorization header.
        handlers.append(request.ProxyHandler({}))
    try:
        with request.build_opener(*handlers).open(request_object, timeout=timeout) as response:
            content = response.read(8 * 1024 * 1024 + 1)
            if len(content) > 8 * 1024 * 1024:
                raise StalwartError("Provider response exceeds the supported 8 MiB transfer limit.")
            payload = json.loads(content.decode("utf-8"))
    except error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise StalwartConnectionPolicyError(
                "jmap_authentication_failed",
                f"Provider HTTP {method} rejected mailbox access with status={exc.code}.",
            ) from None
        if redirect_origin is not None:
            raise StalwartConnectionPolicyError(
                "endpoint_unavailable",
                f"JMAP discovery failed with HTTP status={exc.code}. Check the discovery URL.",
            ) from None
        raise StalwartError(f"Provider HTTP {method} failed with status={exc.code}.") from None
    except (error.URLError, TimeoutError, OSError):
        raise StalwartConnectionPolicyError(
            "endpoint_unavailable", f"Provider HTTP {method} connection failed or timed out."
        ) from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise StalwartError(f"Provider HTTP {method} returned invalid JSON.") from None

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

    def __init__(self, discovery_origin: str | None) -> None:
        self.m_discovery_origin: str | None = discovery_origin

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
        if req.get_method() != "GET":
            return None
        source = self.m_discovery_origin or _connection_origins(req.full_url, ())[0]
        if jmap_origin(newurl) != source:
            raise StalwartConnectionPolicyError(
                "jmap_origin_unapproved", "Discovery must stay on its selected origin."
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def jmap_origin(url: str) -> str:
    """Return one validated HTTP(S) origin without revealing path or query data."""
    try:
        if any(character.isspace() or not character.isprintable() for character in url):
            raise ValueError
        if not url.isascii() or "\\" in url or "#" in url:
            raise ValueError
        parsed = parse.urlsplit(url)
        host = parsed.hostname or ""
        port = parsed.port
        if parsed.scheme not in {"https", "http"} or port == 0:
            raise ValueError
        if ":" in host:
            if "%" in host:
                raise ValueError
            pattern = rf"\[{re.escape(host)}\](?::[0-9]+)?"
            normalized_host = f"[{ipaddress.IPv6Address(host).compressed}]"
        else:
            if len(host) > 253 or not all(
                re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                for label in host.removesuffix(".").split(".")
            ):
                raise ValueError
            pattern = rf"{re.escape(host)}(?::[0-9]+)?"
            normalized_host = host
        if re.fullmatch(pattern, parsed.netloc, re.IGNORECASE) is None:
            raise ValueError
    except ValueError:
        raise StalwartConnectionPolicyError(
            "endpoint_invalid", "Use a valid HTTP(S) JMAP URL without credentials or fragments."
        ) from None

    default_port = 443 if parsed.scheme == "https" else 80
    suffix = f":{port}" if port is not None and port != default_port else ""
    return f"{parsed.scheme}://{normalized_host}{suffix}"


def normalize_jmap_origins(origins: Sequence[str]) -> tuple[str, ...]:
    """Validate explicit origin-only approvals and deduplicate in request order."""
    normalized: dict[str, None] = {}
    for url in origins:
        origin = jmap_origin(url)
        if "?" in url or parse.urlsplit(url).path not in {"", "/"}:
            raise StalwartConnectionPolicyError(
                "endpoint_invalid", "Approve an exact JMAP origin without a path or query."
            )
        normalized[origin] = None
    return tuple(normalized)


def is_plaintext_jmap_origin(origin: str) -> bool:
    """Return whether an origin uses HTTP beyond the default loopback exception."""
    parsed = parse.urlsplit(origin)
    if parsed.scheme != "http":
        return False
    host = parsed.hostname or ""
    if host == "localhost":
        return False
    try:
        return not ipaddress.ip_address(host).is_loopback
    except ValueError:
        return True


def _connection_origins(
    jmap_url: str, allowed_api_origins: Sequence[str]
) -> tuple[str, frozenset[str]]:
    """Resolve the exact credential destinations before making a request."""
    discovery = jmap_origin(jmap_url)
    approvals = normalize_jmap_origins(allowed_api_origins)
    if is_plaintext_jmap_origin(discovery) and discovery not in approvals:
        raise StalwartConnectionPolicyError(
            "jmap_origin_unapproved",
            f"JMAP discovery at {discovery} requires approval of this exact HTTP origin. "
            "Approve the origin explicitly or use HTTPS.",
        )
    return discovery, frozenset((discovery, *approvals))


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
