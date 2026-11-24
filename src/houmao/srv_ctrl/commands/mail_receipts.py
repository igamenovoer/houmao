"""Project mailbox writes into manager CLI receipts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from houmao.agents.mailbox_runtime_models import MailboxChannel
from houmao.mailbox.models import GatewayMailActionResponseV1


def verified_mail_receipt(
    payload: GatewayMailActionResponseV1,
    *,
    channel: MailboxChannel,
    binding_id: str,
    execution_path: Literal["gateway_backed", "manager_direct"],
    parent_message_ref: str | None = None,
) -> dict[str, object]:
    """Return the acknowledged envelope and the binding that owns its reference."""

    message = payload.message
    receipt: dict[str, object] = {
        "schema_version": 1,
        "operation": payload.operation,
        "status": "verified",
        "authoritative": True,
        "execution_path": execution_path,
        "channel": channel,
        "binding_id": binding_id,
        "transport": payload.transport,
        "principal_id": payload.principal_id,
        "address": payload.address,
        "sender_address": message.sender.address,
        "to": [participant.address for participant in message.to],
        "cc": [participant.address for participant in message.cc],
        "subject": message.subject,
        "message_ref": message.message_ref,
        "created_at_utc": message.created_at_utc,
    }
    if parent_message_ref is not None:
        receipt["parent_message_ref"] = parent_message_ref
    return receipt


def submitted_mail_receipt(
    payload: Mapping[str, object],
    *,
    channel: MailboxChannel,
    binding_id: str,
) -> dict[str, object]:
    """Retain submission evidence and give a scoped read-only follow-up."""

    return {
        "schema_version": 1,
        "operation": payload["operation"],
        "status": payload["status"],
        "authoritative": False,
        "execution_path": "tui_submission",
        "channel": channel,
        "binding_id": binding_id,
        "transport": payload["transport"],
        "principal_id": payload["principal_id"],
        "address": payload["address"],
        "sender_address": payload["address"],
        "request_id": payload["request_id"],
        **{key: payload[key] for key in ("submitted_at_utc", "detail") if key in payload},
        "verification": "Check mail list --box sent on the original channel and binding "
        "when authoritative lookup is available.",
    }
