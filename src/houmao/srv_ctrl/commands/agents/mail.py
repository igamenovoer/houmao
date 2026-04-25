"""Managed-agent mail commands for `houmao-mgr agents`."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import cast

import click

from houmao.agents.realm_controller.gateway_models import GatewayMailAttachmentUploadV1
from houmao.mailbox.protocol import (
    HOUMAO_NO_REPLY_POLICY_VALUE,
    HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE,
    OperatorOriginReplyPolicy,
)

from ..common import managed_agent_selector_options, pair_port_option, resolve_body_text
from ..output import emit
from ..managed_agents import (
    mail_archive,
    mail_list,
    mail_mark,
    mail_move,
    mail_peek,
    mail_post,
    mail_read,
    mail_reply,
    mail_resolve_live,
    mail_send,
    mail_status,
    resolve_managed_agent_mail_target,
)


@click.group(name="mail")
def mail_group() -> None:
    """Managed-agent mailbox follow-up commands."""


@mail_group.command(name="status")
@pair_port_option()
@managed_agent_selector_options
def status_mail_command(port: int | None, agent_id: str | None, agent_name: str | None) -> None:
    """Show mailbox status for one managed agent."""

    target = resolve_managed_agent_mail_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(mail_status(target))


@mail_group.command(name="list")
@click.option("--box", default="inbox", show_default=True, help="Mailbox box/subdirectory to read.")
@click.option(
    "--read-state",
    type=click.Choice(["any", "read", "unread"], case_sensitive=False),
    default="any",
    show_default=True,
    help="Read-state filter.",
)
@click.option(
    "--answered-state",
    type=click.Choice(["any", "answered", "unanswered"], case_sensitive=False),
    default="any",
    show_default=True,
    help="Answered-state filter.",
)
@click.option("--archived/--not-archived", default=None, help="Archived-state filter.")
@click.option("--limit", default=None, type=int, help="Maximum number of messages to return.")
@click.option("--since", default=None, help="Optional RFC3339 lower bound.")
@click.option("--include-body", is_flag=True, help="Include full message body text.")
@pair_port_option()
@managed_agent_selector_options
def list_mail_command(
    port: int | None,
    box: str,
    read_state: str,
    answered_state: str,
    archived: bool | None,
    limit: int | None,
    since: str | None,
    include_body: bool,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """List mailbox contents for one managed agent."""

    target = resolve_managed_agent_mail_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(
        mail_list(
            target,
            box=box,
            read_state=read_state,
            answered_state=answered_state,
            archived=archived,
            limit=limit,
            since=since,
            include_body=include_body,
        )
    )


@mail_group.command(name="peek")
@click.option("--message-ref", required=True, help="Opaque message reference.")
@click.option("--box", default=None, help="Require the message to be in this box.")
@pair_port_option()
@managed_agent_selector_options
def peek_mail_command(
    port: int | None,
    message_ref: str,
    box: str | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Peek at one mailbox message without marking it read."""

    target = resolve_managed_agent_mail_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(mail_peek(target, message_ref=message_ref, box=box))


@mail_group.command(name="read")
@click.option("--message-ref", required=True, help="Opaque message reference.")
@click.option("--box", default=None, help="Require the message to be in this box.")
@pair_port_option()
@managed_agent_selector_options
def read_mail_command(
    port: int | None,
    message_ref: str,
    box: str | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Read one mailbox message and mark it read."""

    target = resolve_managed_agent_mail_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(mail_read(target, message_ref=message_ref, box=box))


@mail_group.command(name="send")
@click.option("--to", "to_recipients", multiple=True, required=True, help="Recipient address.")
@click.option("--cc", "cc_recipients", multiple=True, help="CC recipient address.")
@click.option("--subject", required=True, help="Message subject.")
@click.option("--body-content", default=None, help="Inline body content.")
@click.option("--body-file", default=None, help="Body content file path.")
@click.option("--attach", "attachments", multiple=True, help="Attachment file path.")
@click.option(
    "--notify-block",
    "notify_block",
    default=None,
    help=(
        "Sender-marked notification block. When omitted, the body is scanned for the "
        "first ```houmao-notify fenced block."
    ),
)
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
    notify_block: str | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Send one mailbox message for a managed agent."""

    target = resolve_managed_agent_mail_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(
        mail_send(
            target,
            to_recipients=list(to_recipients),
            cc_recipients=list(cc_recipients),
            subject=subject,
            body_content=resolve_body_text(body_content=body_content, body_file=body_file),
            attachments=_resolve_attachment_uploads(attachments),
            notify_block=notify_block,
        )
    )


@mail_group.command(name="post")
@click.option("--subject", required=True, help="Message subject.")
@click.option("--body-content", default=None, help="Inline body content.")
@click.option("--body-file", default=None, help="Body content file path.")
@click.option(
    "--reply-policy",
    type=click.Choice(
        [HOUMAO_NO_REPLY_POLICY_VALUE, HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE],
        case_sensitive=False,
    ),
    default=HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE,
    show_default=True,
    help="Operator-origin reply policy.",
)
@click.option("--attach", "attachments", multiple=True, help="Attachment file path.")
@click.option(
    "--notify-block",
    "notify_block",
    default=None,
    help=(
        "Sender-marked notification block. When omitted, the body is scanned for the "
        "first ```houmao-notify fenced block."
    ),
)
@pair_port_option()
@managed_agent_selector_options
def post_mail_command(
    port: int | None,
    subject: str,
    body_content: str | None,
    body_file: str | None,
    reply_policy: str,
    attachments: tuple[str, ...],
    notify_block: str | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Post one operator-origin mailbox note into a managed agent inbox."""

    target = resolve_managed_agent_mail_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(
        mail_post(
            target,
            subject=subject,
            body_content=resolve_body_text(body_content=body_content, body_file=body_file),
            reply_policy=cast(OperatorOriginReplyPolicy, reply_policy),
            attachments=_resolve_attachment_uploads(attachments),
            notify_block=notify_block,
        )
    )


@mail_group.command(name="reply")
@click.option(
    "--message-ref",
    required=True,
    help="Opaque message reference returned by `agents mail list`.",
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

    target = resolve_managed_agent_mail_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(
        mail_reply(
            target,
            message_ref=message_ref,
            body_content=resolve_body_text(body_content=body_content, body_file=body_file),
            attachments=_resolve_attachment_uploads(attachments),
        )
    )


@mail_group.command(name="mark")
@click.option(
    "--message-ref", "message_refs", multiple=True, required=True, help="Message reference."
)
@click.option("--read/--unread", default=None, help="Set read state.")
@click.option("--answered/--unanswered", default=None, help="Set answered state.")
@click.option("--archived/--unarchived", default=None, help="Set archived state.")
@pair_port_option()
@managed_agent_selector_options
def mark_mail_command(
    port: int | None,
    message_refs: tuple[str, ...],
    read: bool | None,
    answered: bool | None,
    archived: bool | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Mark selected mailbox messages for a managed agent."""

    if read is answered is archived is None:
        raise click.ClickException(
            "At least one of --read/--unread, --answered/--unanswered, or --archived/--unarchived is required."
        )

    target = resolve_managed_agent_mail_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(
        mail_mark(
            target,
            message_refs=list(message_refs),
            read=read,
            answered=answered,
            archived=archived,
        )
    )


@mail_group.command(name="move")
@click.option(
    "--message-ref", "message_refs", multiple=True, required=True, help="Message reference."
)
@click.option("--destination-box", required=True, help="Destination mailbox box/subdirectory.")
@pair_port_option()
@managed_agent_selector_options
def move_mail_command(
    port: int | None,
    message_refs: tuple[str, ...],
    destination_box: str,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Move selected mailbox messages for a managed agent."""

    target = resolve_managed_agent_mail_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(mail_move(target, message_refs=list(message_refs), destination_box=destination_box))


@mail_group.command(name="archive")
@click.option(
    "--message-ref", "message_refs", multiple=True, required=True, help="Message reference."
)
@pair_port_option()
@managed_agent_selector_options
def archive_mail_command(
    port: int | None,
    message_refs: tuple[str, ...],
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Archive selected mailbox messages for a managed agent."""

    target = resolve_managed_agent_mail_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(mail_archive(target, message_refs=list(message_refs)))


@mail_group.command(name="resolve-live")
@pair_port_option()
@managed_agent_selector_options
def resolve_live_mail_command(
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Resolve live mailbox bindings and optional gateway metadata for one managed agent."""

    target = resolve_managed_agent_mail_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(mail_resolve_live(target))


def _resolve_attachment_uploads(attachments: Sequence[str]) -> list[GatewayMailAttachmentUploadV1]:
    """Resolve attachment inputs into gateway-compatible upload payloads."""

    uploads: list[GatewayMailAttachmentUploadV1] = []
    for value in attachments:
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise click.ClickException(f"Attachment path does not exist: `{path}`.")
        uploads.append(GatewayMailAttachmentUploadV1(path=str(path)))
    return uploads
