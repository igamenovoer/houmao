"""Managed-agent mail commands for `houmao-mgr agents`."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import click

from houmao.agents.realm_controller.gateway_models import GatewayMailAttachmentUploadV1
from houmao.server.models import (
    HoumaoManagedAgentMailCheckRequest,
    HoumaoManagedAgentMailReplyRequest,
    HoumaoManagedAgentMailSendRequest,
)

from ..common import (
    emit_json,
    pair_port_option,
    pair_request,
    resolve_body_text,
    resolve_managed_agent_identity,
    resolve_pair_client,
)


@click.group(name="mail")
def mail_group() -> None:
    """Server-backed managed-agent mailbox follow-up commands."""


@mail_group.command(name="status")
@pair_port_option()
@click.argument("agent_ref")
def status_mail_command(port: int | None, agent_ref: str) -> None:
    """Show pair-owned mailbox status for one managed agent."""

    client = resolve_pair_client(port=port)
    resolved = resolve_managed_agent_identity(client, agent_ref=agent_ref)
    emit_json(pair_request(client.get_managed_agent_mail_status, resolved.tracked_agent_id))


@mail_group.command(name="check")
@click.option("--unread-only", is_flag=True, help="Return only unread messages.")
@click.option("--limit", default=None, type=int, help="Maximum number of messages to return.")
@click.option("--since", default=None, help="Optional RFC3339 lower bound.")
@pair_port_option()
@click.argument("agent_ref")
def check_mail_command(
    port: int | None,
    unread_only: bool,
    limit: int | None,
    since: str | None,
    agent_ref: str,
) -> None:
    """Check pair-owned mailbox contents for one managed agent."""

    client = resolve_pair_client(port=port)
    resolved = resolve_managed_agent_identity(client, agent_ref=agent_ref)
    emit_json(
        pair_request(
            client.check_managed_agent_mail,
            resolved.tracked_agent_id,
            HoumaoManagedAgentMailCheckRequest(
                unread_only=unread_only,
                limit=limit,
                since=since,
            ),
        )
    )


@mail_group.command(name="send")
@click.option("--to", "to_recipients", multiple=True, required=True, help="Recipient address.")
@click.option("--cc", "cc_recipients", multiple=True, help="CC recipient address.")
@click.option("--subject", required=True, help="Message subject.")
@click.option("--body-content", default=None, help="Inline body content.")
@click.option("--body-file", default=None, help="Body content file path.")
@click.option("--attach", "attachments", multiple=True, help="Attachment file path.")
@pair_port_option()
@click.argument("agent_ref")
def send_mail_command(
    port: int | None,
    to_recipients: tuple[str, ...],
    cc_recipients: tuple[str, ...],
    subject: str,
    body_content: str | None,
    body_file: str | None,
    attachments: tuple[str, ...],
    agent_ref: str,
) -> None:
    """Send one pair-owned mailbox message for a managed agent."""

    client = resolve_pair_client(port=port)
    resolved = resolve_managed_agent_identity(client, agent_ref=agent_ref)
    emit_json(
        pair_request(
            client.send_managed_agent_mail,
            resolved.tracked_agent_id,
            HoumaoManagedAgentMailSendRequest(
                to=list(to_recipients),
                cc=list(cc_recipients),
                subject=subject,
                body_content=resolve_body_text(body_content=body_content, body_file=body_file),
                attachments=_resolve_attachment_uploads(attachments),
            ),
        )
    )


@mail_group.command(name="reply")
@click.option(
    "--message-ref",
    required=True,
    help="Opaque message reference returned by `agents mail check`.",
)
@click.option("--body-content", default=None, help="Inline body content.")
@click.option("--body-file", default=None, help="Body content file path.")
@click.option("--attach", "attachments", multiple=True, help="Attachment file path.")
@pair_port_option()
@click.argument("agent_ref")
def reply_mail_command(
    port: int | None,
    message_ref: str,
    body_content: str | None,
    body_file: str | None,
    attachments: tuple[str, ...],
    agent_ref: str,
) -> None:
    """Reply through the pair-owned mailbox facade for one managed agent."""

    client = resolve_pair_client(port=port)
    resolved = resolve_managed_agent_identity(client, agent_ref=agent_ref)
    emit_json(
        pair_request(
            client.reply_managed_agent_mail,
            resolved.tracked_agent_id,
            HoumaoManagedAgentMailReplyRequest(
                message_ref=message_ref,
                body_content=resolve_body_text(body_content=body_content, body_file=body_file),
                attachments=_resolve_attachment_uploads(attachments),
            ),
        )
    )


def _resolve_attachment_uploads(attachments: Sequence[str]) -> list[GatewayMailAttachmentUploadV1]:
    """Resolve attachment inputs into gateway-compatible upload payloads."""

    uploads: list[GatewayMailAttachmentUploadV1] = []
    for value in attachments:
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise click.ClickException(f"Attachment path does not exist: `{path}`.")
        uploads.append(GatewayMailAttachmentUploadV1(path=str(path)))
    return uploads
