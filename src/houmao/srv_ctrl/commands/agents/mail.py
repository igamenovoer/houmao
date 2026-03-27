"""Managed-agent mail commands for `houmao-mgr agents`."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import click

from houmao.agents.realm_controller.gateway_models import GatewayMailAttachmentUploadV1

from ..common import emit_json, managed_agent_selector_options, pair_port_option, resolve_body_text
from ..managed_agents import (
    mail_check,
    mail_reply,
    mail_send,
    mail_status,
    resolve_managed_agent_target,
)


@click.group(name="mail")
def mail_group() -> None:
    """Managed-agent mailbox follow-up commands."""


@mail_group.command(name="status")
@pair_port_option()
@managed_agent_selector_options
def status_mail_command(port: int | None, agent_id: str | None, agent_name: str | None) -> None:
    """Show mailbox status for one managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit_json(mail_status(target))


@mail_group.command(name="check")
@click.option("--unread-only", is_flag=True, help="Return only unread messages.")
@click.option("--limit", default=None, type=int, help="Maximum number of messages to return.")
@click.option("--since", default=None, help="Optional RFC3339 lower bound.")
@pair_port_option()
@managed_agent_selector_options
def check_mail_command(
    port: int | None,
    unread_only: bool,
    limit: int | None,
    since: str | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Check mailbox contents for one managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit_json(mail_check(target, unread_only=unread_only, limit=limit, since=since))


@mail_group.command(name="send")
@click.option("--to", "to_recipients", multiple=True, required=True, help="Recipient address.")
@click.option("--cc", "cc_recipients", multiple=True, help="CC recipient address.")
@click.option("--subject", required=True, help="Message subject.")
@click.option("--body-content", default=None, help="Inline body content.")
@click.option("--body-file", default=None, help="Body content file path.")
@click.option("--attach", "attachments", multiple=True, help="Attachment file path.")
@pair_port_option()
@managed_agent_selector_options
def send_mail_command(
    port: int | None,
    to_recipients: tuple[str, ...],
    cc_recipients: tuple[str, ...],
    subject: str,
    body_content: str | None,
    body_file: str | None,
    attachments: tuple[str, ...],
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Send one mailbox message for a managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit_json(
        mail_send(
            target,
            to_recipients=list(to_recipients),
            cc_recipients=list(cc_recipients),
            subject=subject,
            body_content=resolve_body_text(body_content=body_content, body_file=body_file),
            attachments=_resolve_attachment_uploads(attachments),
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
@managed_agent_selector_options
def reply_mail_command(
    port: int | None,
    message_ref: str,
    body_content: str | None,
    body_file: str | None,
    attachments: tuple[str, ...],
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Reply to one mailbox message for a managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit_json(
        mail_reply(
            target,
            message_ref=message_ref,
            body_content=resolve_body_text(body_content=body_content, body_file=body_file),
            attachments=_resolve_attachment_uploads(attachments),
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
