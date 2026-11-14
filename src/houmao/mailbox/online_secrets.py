"""Private immutable account credential copies for managed online connections."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from uuid import uuid4

from houmao.mailbox.online_models import OnlineBindingError
from houmao.mailbox.stalwart import session_stalwart_credential_path


def prepare_online_credential(source: Path, *, session_root: Path) -> tuple[str, Path]:
    """Copy one explicit private password JSON source without modifying its inode."""

    try:
        with source.expanduser().open("rb") as stream:
            metadata = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or metadata.st_mode & 0o077
            ):
                raise OnlineBindingError(
                    "credential_source_invalid", "Credential source must be owner-private"
                )
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError("oversized credential source")
        payload = json.loads(raw)
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("password"), str)
            or not payload["password"].strip()
        ):
            raise ValueError("missing password")
    except OnlineBindingError:
        raise
    except (OSError, ValueError):
        raise OnlineBindingError(
            "credential_source_invalid", "Credential source is unavailable or invalid"
        ) from None
    reference = "online-" + uuid4().hex
    target = session_stalwart_credential_path(session_root, reference)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    target.parent.chmod(0o700)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return reference, target


def retire_online_credential(
    reference: str, *, session_root: Path, protected_source: str | None = None
) -> None:
    """Remove only a managed immutable copy, never an externally selected source."""

    if not reference.startswith("online-") or not reference[7:].isalnum():
        return
    target = session_stalwart_credential_path(session_root, reference)
    if (
        protected_source is not None
        and target.resolve() == Path(protected_source).expanduser().resolve()
    ):
        return
    target.unlink(missing_ok=True)
