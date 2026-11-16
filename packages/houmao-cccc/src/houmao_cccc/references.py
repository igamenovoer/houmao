"""Opaque authenticated CCCC references contained in one owner and binding scope."""

from __future__ import annotations

import base64
import hmac
import json
import os
from pathlib import Path
import secrets
import stat
import tempfile

from pydantic import JsonValue, ValidationError

from houmao.gateway.plugins import PluginContext
from houmao_cccc.models import JSON_OBJECT

_MAX_REFERENCE_BYTES = 16384


class ReferenceError(ValueError):
    """Reject malformed, tampered, or stale handles without echoing their value."""


def _encode(value: bytes) -> str:
    """Encode bytes using canonical unpadded URL-safe base64."""

    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    """Decode canonical URL-safe base64 without accepting padding aliases."""

    try:
        result = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError):
        raise ReferenceError("Invalid or stale CCCC reference") from None
    if _encode(result) != value:
        raise ReferenceError("Invalid or stale CCCC reference")
    return result


def _private_key(path: Path) -> bytes:
    """Create an atomically published private signing key or validate its existing file."""

    if not path.exists():
        temporary: str | None = None
        try:
            descriptor, temporary = tempfile.mkstemp(prefix=".cccc-reference-", dir=path.parent)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(secrets.token_bytes(32))
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path, follow_symlinks=False)
            except FileExistsError:
                pass
        except OSError:
            raise ReferenceError("CCCC reference key is unavailable") from None
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_mode & 0o077
                or info.st_size != 32
                or (hasattr(os, "getuid") and info.st_uid != os.getuid())
            ):
                raise ReferenceError("CCCC reference key is unavailable")
            return stream.read(33)
    except OSError:
        raise ReferenceError("CCCC reference key is unavailable") from None


class ReferenceCodec:
    """Authenticate targeting and continuation handles across gateway restarts."""

    def __init__(self) -> None:
        """Create a codec without touching private state during route staging."""

        self.m_key: bytes | None = None
        self.m_scope: dict[str, JsonValue] = {}

    @classmethod
    def from_context(cls, context: PluginContext) -> ReferenceCodec:
        """Load private non-message signing state inside the SDK-selected binding."""

        codec = cls()
        codec.m_key = _private_key(context.state.path("reference-key"))
        codec.m_scope = {
            "owner": context.owner.agent_id,
            "runtime": context.owner.runtime_session_id,
            "instance": context.instance_id,
            "binding": context.binding_id,
        }
        return codec

    def encode(self, kind: str, value: JsonValue) -> str:
        """Create one opaque handle for non-message targeting metadata."""

        if self.m_key is None or not kind or len(kind) > 64:
            raise ReferenceError("CCCC reference codec is unavailable")
        try:
            payload = json.dumps(
                {"version": 1, **self.m_scope, "kind": kind, "value": value},
                sort_keys=True,
                ensure_ascii=True,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError):
            raise ReferenceError("Invalid CCCC reference metadata") from None
        result = (
            "cccc1." + _encode(payload) + "." + _encode(hmac.digest(self.m_key, payload, "sha256"))
        )
        if len(result) > _MAX_REFERENCE_BYTES:
            raise ReferenceError("CCCC reference metadata exceeds the supported limit")
        return result

    def decode(self, handle: str, kind: str) -> JsonValue:
        """Verify kind, owner, runtime, and service binding before returning metadata."""

        if self.m_key is None or len(handle) > _MAX_REFERENCE_BYTES:
            raise ReferenceError("Invalid or stale CCCC reference")
        parts = handle.split(".")
        if len(parts) != 3 or parts[0] != "cccc1":
            raise ReferenceError("Invalid or stale CCCC reference")
        payload, signature = _decode(parts[1]), _decode(parts[2])
        if not hmac.compare_digest(hmac.digest(self.m_key, payload, "sha256"), signature):
            raise ReferenceError("Invalid or stale CCCC reference")
        try:
            value = JSON_OBJECT.validate_python(json.loads(payload), strict=True)
        except (ValueError, ValidationError, UnicodeDecodeError):
            raise ReferenceError("Invalid or stale CCCC reference") from None
        if (
            type(value.get("version")) is not int
            or value.get("version") != 1
            or value.get("kind") != kind
            or any(value.get(key) != expected for key, expected in self.m_scope.items())
            or "value" not in value
        ):
            raise ReferenceError("Invalid or stale CCCC reference")
        return value["value"]
