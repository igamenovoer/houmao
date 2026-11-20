"""Connect to one process-owned Kimi Web loopback listener and private journal."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from http.client import HTTPConnection, HTTPException
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

from houmao.agents.realm_controller.backends.dsh_web_client import DshWebError
from houmao.agents.realm_controller.backends.kimi_acp_journal import _open_native_file
from houmao.agents.realm_controller.backends.web_entry import (
    owns_ipv4_web_listener as owned_listener,
)

_MAX_RESPONSE = 2 << 20
_MAX_JOURNAL = 16 << 20
_TOKEN = re.compile(r"[A-Za-z0-9_.=+-]{16,512}")
_KIMI_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")


def native_id(value: object) -> str:
    """Validate a native session or prompt path component."""

    if not isinstance(value, str) or _KIMI_ID.fullmatch(value) is None:
        raise DshWebError("identity_mismatch", "Kimi returned an invalid native identity")
    return value


@dataclass(frozen=True)
class KimiWebClient:
    """Independent authenticated HTTP connection to an owned Kimi Web process."""

    origin: str
    pid: int
    birth: str
    token_file: Path

    @property
    def port(self) -> int:
        """Return the verified origin's IPv4 loopback port."""

        parsed = urlsplit(self.origin)
        if parsed.scheme != "http" or parsed.netloc != f"127.0.0.1:{parsed.port}":
            raise DshWebError("invalid_origin", "Kimi Web requires its owned IPv4 listener")
        if (
            parsed.port is None
            or parsed.port == 0
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise DshWebError("invalid_origin", "Kimi Web requires a clean loopback origin")
        return parsed.port

    def credential(self) -> str:
        """Read a private Kimi token only for the verified listener."""

        if not owned_listener(self.pid, self.birth, self.port):
            raise DshWebError("stale_identity", "Kimi Web listener ownership changed")
        try:
            with _open_native_file(self.token_file) as stream:
                if os.fstat(stream.fileno()).st_mode & 0o077:
                    raise OSError("Kimi token permissions are too broad")
                token = stream.read(1024).decode("ascii").strip()
            if _TOKEN.fullmatch(token) is not None:
                return token
        except (OSError, UnicodeError):
            pass
        raise DshWebError("authentication_failed", "Private Kimi Web credential is unavailable")

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        before_send: Callable[[], None] | None = None,
        authenticated: bool = True,
        timeout: float = 10,
    ) -> dict[str, Any]:
        """Issue one bounded request and fence credential transmission against port reuse."""

        encoded = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        connection = HTTPConnection("127.0.0.1", self.port, timeout=timeout)
        sending = False
        try:
            if not owned_listener(self.pid, self.birth, self.port):
                raise DshWebError("stale_identity", "Kimi Web listener ownership changed")
            connection.connect()
            if authenticated:
                # The connected socket retains its original peer even if the listener closes.
                headers["Authorization"] = f"Bearer {self.credential()}"
            elif not owned_listener(self.pid, self.birth, self.port):
                raise DshWebError("stale_identity", "Kimi Web listener ownership changed")
            if before_send is not None:
                before_send()
            sending = True
            connection.request(method, "/api/v1" + path, body=encoded, headers=headers)
            response = connection.getresponse()
            if response.status in {401, 403}:
                raise DshWebError("authentication_failed", "Kimi Web refused the credential")
            if response.status >= 500 and method == "POST":
                raise DshWebError("outcome_uncertain", "Kimi Web did not confirm the mutation")
            if response.status != 200:
                raise DshWebError("invalid_request", "Kimi Web refused the native request")
            raw = response.read(_MAX_RESPONSE + 1)
            if len(raw) <= _MAX_RESPONSE:
                payload = json.loads(raw)
                if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
                    return dict(payload["data"])
                if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
                    raise DshWebError("invalid_request", "Kimi Web refused the native request")
        except (HTTPException, OSError, ValueError):
            pass
        finally:
            connection.close()
        code = "outcome_uncertain" if method == "POST" and sending else "unavailable"
        raise DshWebError(code, "Kimi Web did not return a verified response")


@dataclass(frozen=True)
class KimiWebJournalWindow:
    """A bounded set of complete native records and their stable file offsets."""

    device: int
    inode: int
    start: int
    end: int
    records: list[tuple[int, int, dict[str, Any]]]

    @classmethod
    def read(cls, path: Path, *, start: int | None = None) -> KimiWebJournalWindow:
        """Read a bounded tail or exact admission interval without waking a session."""

        try:
            with _open_native_file(path) as stream:
                info = os.fstat(stream.fileno())
                first = max(info.st_size - _MAX_JOURNAL, 0) if start is None else start
                if not 0 <= first <= info.st_size <= first + _MAX_JOURNAL:
                    raise DshWebError(
                        "outcome_uncertain", "Kimi Web journal interval is unavailable"
                    )
                stream.seek(max(0, first - 1))
                if first and stream.read(1) != b"\n":
                    if start is not None:
                        raise DshWebError("outcome_uncertain", "Kimi Web journal boundary changed")
                    stream.readline(info.st_size - first)
                first = stream.tell()
                records = list(_read_complete_rows(stream, info.st_size))
                return cls(info.st_dev, info.st_ino, first, stream.tell(), records)
        except FileNotFoundError:
            if start in {None, 0}:
                return cls(0, 0, 0, 0, [])
            raise DshWebError("outcome_uncertain", "Kimi Web journal disappeared") from None
        except (ValueError, OSError, UnicodeError):
            raise DshWebError("unavailable", "Kimi Web journal is unavailable") from None


def _read_complete_rows(stream: Any, limit: int) -> Iterator[tuple[int, int, dict[str, Any]]]:
    """Yield only complete native rows, leaving an unfinished final record unread."""

    while (position := stream.tell()) < limit:
        raw = stream.readline(limit - position)
        if not raw.endswith(b"\n"):
            stream.seek(position)
            return
        row = json.loads(raw)
        if isinstance(row, dict) and row.get("agentId") == "main":
            yield position, stream.tell(), row


def observed_at(row: dict[str, Any]) -> str:
    """Project a valid millisecond timestamp without returning native content."""

    timestamp = row.get("time")
    if type(timestamp) is int:
        try:
            return datetime.fromtimestamp(timestamp / 1000, UTC).isoformat()
        except (OverflowError, ValueError, OSError):
            pass
    return datetime.now(UTC).isoformat()
