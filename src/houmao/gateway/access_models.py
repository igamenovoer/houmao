"""Strict document and wire models for managed gateway access."""

from __future__ import annotations

import hashlib
from ipaddress import IPv6Address
import json
from pathlib import PurePosixPath
import re
from typing import Annotated, Literal, TypeAlias, TypeVar
from urllib.parse import unquote, urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from houmao.gateway._access_sshsig import key_fingerprint, load_public_key, public_key_text

MAX_ACCESS_DOCUMENT = 1024 * 1024
MAX_ADMIN_KEYS = 256
CHALLENGE_HEADER = "Houmao-Challenge"
SIGNATURE_HEADER = "Houmao-Signature"

AccessClass: TypeAlias = Literal["public", "private", "admin"]
AdminMode: TypeAlias = Literal["open", "key_required"]
ProofPurpose: TypeAlias = Literal["self", "admin", "register"]
GrantRole: TypeAlias = Literal["public", "anonymous", "self", "admin", "register"]
_Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_][A-Za-z0-9_.:-]{0,127}$")]
_KeyId = Annotated[str, Field(pattern=r"^SHA256:[A-Za-z0-9_-]{43}$")]
_Document = TypeVar("_Document", bound=BaseModel)
_DNS_LABEL = re.compile(r"[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?")
_URL_ESCAPE = re.compile(r"%(?![A-Fa-f0-9]{2})|%2[fF]")


class _AccessModel(BaseModel):
    """Reject extra fields, coercion, and inclusion of input values in error text."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)


class GatewayOwner(_AccessModel):
    """Pin a logical agent to its observed execution context."""

    agent_id: _Identifier
    context_id: _Identifier


class GatewayTarget(_AccessModel):
    """Identify the current incarnation reachable through an ingress."""

    owner: GatewayOwner
    incarnation: _Identifier


class GatewayAdminKey(_AccessModel):
    """Bind a registered principal to a canonical OpenSSH public key."""

    principal: _Identifier
    public_key: str = Field(min_length=1, max_length=4096, repr=False)

    @field_validator("public_key")
    @classmethod
    def _canonicalize(cls, value: str) -> str:
        """Validate the key and discard its untrusted display comment."""

        return public_key_text(load_public_key(value))

    @property
    def key_id(self) -> str:
        """Return the URL-safe SHA256 fingerprint used for key lookup."""

        return key_fingerprint(self.public_key)


class GatewayLaunchSeed(_AccessModel):
    """Carry owner-authorized initial enrollment in a launch manifest."""

    admin_keys: tuple[GatewayAdminKey, ...] = Field(default=(), max_length=MAX_ADMIN_KEYS)

    @field_validator("admin_keys")
    @classmethod
    def _unique_keys(cls, keys: tuple[GatewayAdminKey, ...]) -> tuple[GatewayAdminKey, ...]:
        """Refuse duplicate key identities, including keys with different comments."""

        if len({entry.key_id for entry in keys}) != len(keys):
            raise ValueError("duplicate admin key")
        return keys


class GatewayAdminEnrollment(_AccessModel):
    """Give a key a stable grant identifier for the lifetime of its enrollment."""

    key: GatewayAdminKey
    enrollment: int = Field(ge=0)

    @property
    def key_id(self) -> str:
        """Return the canonical identifier of the enrolled key."""

        return self.key.key_id


class GatewayAdminState(_AccessModel):
    """Persist live key membership independently of gateway attach or launch generation."""

    schema_version: Literal[1] = 1
    owner: GatewayOwner
    revision: int = Field(ge=0)
    keys: tuple[GatewayAdminEnrollment, ...] = Field(max_length=MAX_ADMIN_KEYS, repr=False)

    @model_validator(mode="after")
    def _valid_enrollments(self) -> GatewayAdminState:
        """Refuse duplicate keys and impossible enrollment revisions."""

        if len({entry.key_id for entry in self.keys}) != len(self.keys):
            raise ValueError("duplicate admin key")
        if any(entry.enrollment > self.revision for entry in self.keys):
            raise ValueError("invalid admin enrollment")
        return self

    @property
    def mode(self) -> AdminMode:
        """Expose the current admission mode without returning membership."""

        return "key_required" if self.keys else "open"

    def find(self, key_id: str) -> GatewayAdminEnrollment | None:
        """Resolve a key ID only within this bound live membership list."""

        return next((entry for entry in self.keys if entry.key_id == key_id), None)


class GatewaySelfKey(_AccessModel):
    """Bind an Ed25519 public key to the current managed generation."""

    schema_version: Literal[1] = 1
    owner: GatewayOwner
    generation_id: _Identifier
    public_key: str = Field(min_length=1, max_length=4096, repr=False)

    @field_validator("public_key")
    @classmethod
    def _ed25519(cls, value: str) -> str:
        """Limit provisioned self credentials to managed Ed25519 keys."""

        normalized = public_key_text(load_public_key(value))
        if not normalized.startswith("ssh-ed25519 "):
            raise ValueError("managed self requires an Ed25519 key")
        return normalized

    @property
    def key_id(self) -> str:
        """Return the URL-safe fingerprint of this generation's public key."""

        return key_fingerprint(self.public_key)


class GatewayClientBinding(_AccessModel):
    """Select an exact target, endpoint, signer, and optional deployment CA."""

    base_url: str = Field(max_length=2048)
    owner: GatewayOwner
    purpose: ProofPurpose
    private_key_path: str = Field(max_length=4096, repr=False)
    ca_bundle_path: str | None = Field(default=None, max_length=4096, repr=False)

    @field_validator("base_url")
    @classmethod
    def _endpoint(cls, value: str) -> str:
        """Apply the gateway transport and URL requirements to credentials."""

        return validate_gateway_base_url(value)

    @field_validator("private_key_path", "ca_bundle_path")
    @classmethod
    def _absolute(cls, value: str | None) -> str | None:
        """Keep selected credential sources explicit and lexical."""

        if value is not None and (
            not PurePosixPath(value).is_absolute()
            or ".." in PurePosixPath(value).parts
            or any(ord(char) < 32 for char in value)
        ):
            raise ValueError("private source requires a safe absolute path")
        return value


class GatewayRequestBinding(_AccessModel):
    """Name the exact HTTP operation and digest of its untranslated body."""

    method: str = Field(pattern=r"^[A-Z]{1,16}$")
    path: str = Field(min_length=1, max_length=4096)
    query: str = Field(default="", max_length=4096)
    body_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @field_validator("path", "query")
    @classmethod
    def _ascii(cls, value: str) -> str:
        """Require raw, percent-encoded HTTP request components."""

        if any(not 33 <= ord(char) <= 126 for char in value):
            raise ValueError("HTTP target contains invalid bytes")
        return value

    @field_validator("path")
    @classmethod
    def _path(cls, value: str) -> str:
        """Accept one origin-relative operation path."""

        if (
            not value.startswith("/")
            or value.startswith("//")
            or any(char in value for char in "?#\\")
        ):
            raise ValueError("invalid request path")
        return value

    @classmethod
    def from_request(cls, method: str, path: str, query: str, body: bytes) -> GatewayRequestBinding:
        """Bind the exact method, app-relative path, query, and bounded raw body."""

        return cls(
            method=method,
            path=path,
            query=query,
            body_sha256=hashlib.sha256(body).hexdigest(),
        )


class GatewayChallengeRequest(_AccessModel):
    """Request one challenge for a purpose and an exact application operation."""

    purpose: ProofPurpose
    request: GatewayRequestBinding
    key_id: _KeyId | None = None
    proposed_key: GatewayAdminKey | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def _key_selection(self) -> GatewayChallengeRequest:
        """Limit listed and proposed key selectors to their own proof purposes."""

        if self.purpose == "admin" and self.key_id is None:
            raise ValueError("admin proof requires a key ID")
        if self.purpose == "register" and self.proposed_key is None:
            raise ValueError("registration requires a proposed key")
        if self.purpose != "admin" and self.key_id is not None:
            raise ValueError("unexpected admin key ID")
        if self.purpose != "register" and self.proposed_key is not None:
            raise ValueError("unexpected proposed key")
        return self


class GatewayChallenge(_AccessModel):
    """Describe the complete scope of one expiring gateway proof."""

    schema_version: Literal[1] = 1
    challenge_id: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$", repr=False)
    issuer: str = Field(min_length=1, max_length=2048)
    target: GatewayTarget
    purpose: ProofPurpose
    request: GatewayRequestBinding = Field(repr=False)
    expires_at: int = Field(ge=0)
    key_id: _KeyId
    generation_id: _Identifier | None = None
    revision: int | None = Field(default=None, ge=0)
    proposed_key: GatewayAdminKey | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def _proof_scope(self) -> GatewayChallenge:
        """Require generation or roster revision according to the proof purpose."""

        if self.purpose == "self":
            if self.generation_id is None or self.revision is not None:
                raise ValueError("invalid self challenge scope")
        elif self.generation_id is not None or self.revision is None:
            raise ValueError("invalid admin challenge scope")
        if self.purpose == "register":
            if self.proposed_key is None or self.key_id != self.proposed_key.key_id:
                raise ValueError("invalid first-registration challenge")
        elif self.proposed_key is not None:
            raise ValueError("unexpected registration scope")
        return self

    def signing_bytes(self) -> bytes:
        """Return the canonical UTF-8 JSON document covered by SSHSIG."""

        return json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        ).encode("ascii")


class GatewayGrant(_AccessModel):
    """Record authorized provenance and the grant needed for revalidation."""

    role: GrantRole
    target: GatewayTarget
    principal: _Identifier | None = None
    key_id: _KeyId | None = None
    generation_id: _Identifier | None = None
    revision: int | None = Field(default=None, ge=0)
    enrollment: int | None = Field(default=None, ge=0)
    proposed_key: GatewayAdminKey | None = Field(default=None, repr=False)


def parse_access_document(model: type[_Document], payload: bytes) -> _Document:
    """Read a strict JSON model after rejecting repeated fields at every depth."""

    if len(payload) > MAX_ACCESS_DOCUMENT:
        raise ValueError("access document exceeds its size limit")
    try:
        json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_fields)
        return model.model_validate_json(payload)
    except (ValueError, RecursionError):
        raise ValueError("invalid access document") from None


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Refuse repeated JSON keys before model validation can choose a value."""

    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate access document field")
        result[name] = value
    return result


def validate_gateway_base_url(value: str) -> str:
    """Accept verified HTTPS or literal loopback HTTP with an exact base path."""

    if not value or len(value) > 2048 or any(not 33 <= ord(char) <= 126 for char in value):
        raise ValueError("invalid gateway base URL")
    try:
        url = urlsplit(value)
        port = url.port
    except ValueError:
        raise ValueError("invalid gateway base URL") from None
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username is not None
        or url.password is not None
        or "#" in value
        or "?" in value
        or "\\" in value
        or url.netloc.endswith(":")
        or port == 0
    ):
        raise ValueError("invalid gateway base URL")
    if url.scheme == "http" and url.hostname not in {"127.0.0.1", "::1"}:
        raise ValueError("gateway HTTP requires a literal loopback endpoint")
    host = url.hostname
    if url.netloc.startswith("["):
        try:
            if "%" in host:
                raise ValueError
            IPv6Address(host)
        except ValueError:
            raise ValueError("invalid gateway base host") from None
    elif len(host) > 253 or not all(_DNS_LABEL.fullmatch(label) for label in host.split(".")):
        raise ValueError("invalid gateway base host")
    netloc = f"[{host}]" if ":" in host else host
    if port is not None:
        netloc += f":{port}"
    if url.netloc.lower() != netloc:
        raise ValueError("invalid gateway base host or port")
    path = unquote(url.path)
    if (
        "//" in path
        or any(char in path for char in "\\?#")
        or _URL_ESCAPE.search(url.path)
        or any(part in {".", ".."} for part in path.split("/"))
        or any(not 33 <= ord(char) <= 126 for char in path)
    ):
        raise ValueError("invalid gateway base path")
    return f"{url.scheme}://{netloc}{url.path.rstrip('/')}"
