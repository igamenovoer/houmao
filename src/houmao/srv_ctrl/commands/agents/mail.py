"""Managed-agent mail commands for `houmao-mgr agents`."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import shlex

import click

from houmao.agents.realm_controller.gateway_models import GatewayMailAttachmentUploadV1

from ..common import emit_json, managed_agent_selector_options, pair_port_option, resolve_body_text
from ..managed_agents import (
    mail_check,
    mail_mark_read,
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

    target = resolve_managed_agent_mail_target(agent_id=agent_id, agent_name=agent_name, port=port)
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

    target = resolve_managed_agent_mail_target(agent_id=agent_id, agent_name=agent_name, port=port)
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

    target = resolve_managed_agent_mail_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit_json(
        mail_reply(
            target,
            message_ref=message_ref,
            body_content=resolve_body_text(body_content=body_content, body_file=body_file),
            attachments=_resolve_attachment_uploads(attachments),
        )
    )


@mail_group.command(name="mark-read")
@click.option(
    "--message-ref",
    required=True,
    help="Opaque message reference returned by `agents mail check`.",
)
@pair_port_option()
@managed_agent_selector_options
def mark_read_mail_command(
    port: int | None,
    message_ref: str,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Mark one mailbox message read for a managed agent."""

    target = resolve_managed_agent_mail_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit_json(mail_mark_read(target, message_ref=message_ref))


@mail_group.command(name="resolve-live")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(("json", "shell"), case_sensitive=False),
    default="json",
    show_default=True,
    help="Output format for live mailbox bindings.",
)
@pair_port_option()
@managed_agent_selector_options
def resolve_live_mail_command(
    port: int | None,
    output_format: str,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Resolve live mailbox bindings and optional gateway metadata for one managed agent."""

    target = resolve_managed_agent_mail_target(agent_id=agent_id, agent_name=agent_name, port=port)
    payload = mail_resolve_live(target)
    if output_format == "json":
        emit_json(payload)
        return
    for line in _shell_lines_for_resolve_live(payload):
        click.echo(line)


def _resolve_attachment_uploads(attachments: Sequence[str]) -> list[GatewayMailAttachmentUploadV1]:
    """Resolve attachment inputs into gateway-compatible upload payloads."""

    uploads: list[GatewayMailAttachmentUploadV1] = []
    for value in attachments:
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise click.ClickException(f"Attachment path does not exist: `{path}`.")
        uploads.append(GatewayMailAttachmentUploadV1(path=str(path)))
    return uploads


def _shell_lines_for_resolve_live(payload: dict[str, object]) -> list[str]:
    """Render `resolve-live` output as stable shell assignments."""

    managed_agent = payload.get("managed_agent")
    env_payload = payload.get("env")
    gateway_payload = payload.get("gateway")

    assignments: list[tuple[str, str]] = [
        ("HOUMAO_MANAGED_AGENT_MODE", _shell_text_value(_mapping_value(managed_agent, "mode"))),
        ("HOUMAO_MANAGED_AGENT_REF", _shell_text_value(_mapping_value(managed_agent, "agent_ref"))),
        (
            "HOUMAO_MANAGED_AGENT_NAME",
            _shell_text_value(_mapping_value(managed_agent, "agent_name")),
        ),
        ("HOUMAO_MANAGED_AGENT_ID", _shell_text_value(_mapping_value(managed_agent, "agent_id"))),
        (
            "HOUMAO_MANAGED_AGENT_TMUX_SESSION_NAME",
            _shell_text_value(_mapping_value(managed_agent, "tmux_session_name")),
        ),
        ("AGENTSYS_MAILBOX_BINDINGS_SOURCE", _shell_text_value(payload.get("source"))),
    ]

    if isinstance(env_payload, dict):
        for key in sorted(env_payload):
            value = env_payload.get(key)
            if isinstance(key, str):
                assignments.append((key, _shell_text_value(value)))

    assignments.extend(
        [
            (
                "AGENTSYS_MAILBOX_GATEWAY_AVAILABLE",
                "1" if isinstance(gateway_payload, dict) else "0",
            ),
            (
                "AGENTSYS_MAILBOX_GATEWAY_SOURCE",
                _shell_text_value(_mapping_value(gateway_payload, "source")),
            ),
            (
                "AGENTSYS_MAILBOX_GATEWAY_HOST",
                _shell_text_value(_mapping_value(gateway_payload, "host")),
            ),
            (
                "AGENTSYS_MAILBOX_GATEWAY_PORT",
                _shell_text_value(_mapping_value(gateway_payload, "port")),
            ),
            (
                "AGENTSYS_MAILBOX_GATEWAY_BASE_URL",
                _shell_text_value(_mapping_value(gateway_payload, "base_url")),
            ),
            (
                "AGENTSYS_MAILBOX_GATEWAY_PROTOCOL_VERSION",
                _shell_text_value(_mapping_value(gateway_payload, "protocol_version")),
            ),
            (
                "AGENTSYS_MAILBOX_GATEWAY_STATE_PATH",
                _shell_text_value(_mapping_value(gateway_payload, "state_path")),
            ),
        ]
    )

    return [f"export {name}={shlex.quote(value)}" for name, value in assignments]


def _mapping_value(payload: object, key: str) -> object | None:
    """Return one optional mapping value without assuming exact payload shape."""

    if not isinstance(payload, dict):
        return None
    return payload.get(key)


def _shell_text_value(value: object) -> str:
    """Normalize one JSON-compatible value into a shell-safe text payload."""

    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)
