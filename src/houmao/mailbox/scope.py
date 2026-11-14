"""Owner and binding scope for mail handles and operation admission."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json

from houmao.mailbox.models import MailChannel


class MailboxScopeError(ValueError):
    """A handle or operation belongs to another mail authority."""


@dataclass(frozen=True)
class MailScope:
    """Immutable operation scope, independent of a preferred mail address."""

    agent_id: str
    channel: MailChannel
    binding_id: str

    def require_binding(self, expected_binding_id: str) -> None:
        """Reject stale operation targeting before any backend effects."""

        if expected_binding_id != self.binding_id:
            raise MailboxScopeError("Mailbox binding changed; resolve the selected channel again")

    def encode(self, reference: str, *, kind: str = "message") -> str:
        """Wrap a backend handle in its exact owner/channel/binding scope."""

        payload = [1, self.agent_id, self.channel, self.binding_id, kind, reference]
        encoded = (
            base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
            .decode("ascii")
            .rstrip("=")
        )
        return f"houmao-mail:{encoded}"

    def decode(self, reference: str, *, kind: str = "message") -> str:
        """Validate a handle completely before exposing its backend identity."""

        if len(reference) > 16384 or not reference.startswith("houmao-mail:"):
            raise MailboxScopeError("Expected an owner-scoped mail reference")
        try:
            encoded = reference.removeprefix("houmao-mail:")
            payload = json.loads(
                base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
            )
        except (ValueError, UnicodeError) as exc:
            raise MailboxScopeError("Malformed mail reference") from exc
        expected = [1, self.agent_id, self.channel, self.binding_id, kind]
        if (
            not isinstance(payload, list)
            or len(payload) != 6
            or payload[:5] != expected
            or not isinstance(payload[5], str)
            or not payload[5]
        ):
            raise MailboxScopeError("Mail reference belongs to another owner, channel, or binding")
        return payload[5]
