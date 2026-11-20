"""Build owner-private browser locations for verified native Web listeners."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token
from houmao.agents.realm_controller.native_surface import validate_web_origin


@dataclass(frozen=True, repr=False)
class NativeWebEntry:
    """Hold backend-owned browser sign-in components in memory until redemption."""

    origin: str
    path: str = "/"
    query: tuple[tuple[str, str], ...] = ()
    fragment: tuple[tuple[str, str], ...] = ()

    def redirect_url(self, *, expected_origin: str) -> str:
        """Encode the native destination under the exact verified loopback authority."""

        try:
            origin = validate_web_origin(self.origin)
            if origin != validate_web_origin(expected_origin):
                raise ValueError
            base = urlsplit(origin)
            if (
                not self.path.startswith("/")
                or self.path.startswith("//")
                or "\\" in self.path
                or any(segment in {".", ".."} for segment in self.path.split("/"))
            ):
                raise ValueError
            return urlunsplit(
                (
                    base.scheme,
                    base.netloc,
                    quote(self.path, safe="/"),
                    urlencode(self.query, quote_via=quote),
                    urlencode(self.fragment, quote_via=quote),
                )
            )
        except ValueError:
            raise ValueError("Native Web browser location is invalid") from None


def owns_ipv4_web_listener(pid: int, birth: str, port: int) -> bool:
    """Check that the captured process still owns the exact 127.0.0.1 listener."""

    if _dispatch_origin_birth_token(pid) != birth:
        return False
    address = f"0100007F:{port:04X}"
    try:
        inodes = set()
        for line in Path(f"/proc/{pid}/net/tcp").read_text(encoding="ascii").splitlines()[1:]:
            columns = line.split()
            if len(columns) > 9 and columns[1] == address and columns[3] == "0A":
                inodes.add(f"socket:[{columns[9]}]")
        if len(inodes) != 1:
            return False
        for fd in Path(f"/proc/{pid}/fd").iterdir():
            try:
                if os.readlink(fd) in inodes:
                    return _dispatch_origin_birth_token(pid) == birth
            except FileNotFoundError:
                continue
    except (OSError, UnicodeError):
        pass
    return False
