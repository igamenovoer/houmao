"""Command-template declarations for this command family."""

from __future__ import annotations

from ..builders import (
    _choice,
    _conflict,
    _f,
    _flag,
    _int,
    _many,
    _path,
    _req,
    _req_many,
    _template,
)
from ..models import (
    CommandTemplate,
    TemplateField,
)


def templates() -> list[CommandTemplate]:
    """Return managed-agent mail fallback command templates."""

    selector_fields = (
        _f("agent_name", "--agent-name", "Friendly managed-agent name."),
        _f("agent_id", "--agent-id", "Managed-agent id."),
        _int("port", "--port", "Houmao pair authority port."),
    )
    command_fields: dict[str, tuple[TemplateField, ...]] = {
        "resolve-live": selector_fields,
        "status": selector_fields,
        "list": (
            *selector_fields,
            _f("box", "--box", "Mailbox box/subdirectory."),
            _choice("read_state", "--read-state", "Read state filter.", ("read", "unread", "any")),
            _choice(
                "answered_state",
                "--answered-state",
                "Answered state filter.",
                ("answered", "unanswered", "any"),
            ),
            _flag(
                "archived",
                "--archived",
                "Archived-state filter.",
                negative_option="--not-archived",
            ),
            _int("limit", "--limit", "Maximum messages."),
            _f("since", "--since", "RFC3339 lower bound."),
            _flag("include_body", "--include-body", "Include full message bodies."),
        ),
        "peek": (
            *selector_fields,
            _req("message_ref", "--message-ref", "Opaque message ref."),
            _f("box", "--box", "Required source box."),
        ),
        "read": (
            *selector_fields,
            _req("message_ref", "--message-ref", "Opaque message ref."),
            _f("box", "--box", "Required source box."),
        ),
        "send": (
            *selector_fields,
            _req_many("to", "--to", "Recipient address."),
            _many("cc", "--cc", "CC recipient address."),
            _req("subject", "--subject", "Message subject."),
            _f("body_content", "--body-content", "Inline message body."),
            _path("body_file", "--body-file", "Message body file."),
            _many("attach", "--attach", "Attachment path."),
            _f("notify_block", "--notify-block", "Sender-marked notification block."),
            _choice(
                "notify_block_placement",
                "--notify-block-placement",
                "Notification block placement.",
                ("append", "prepend"),
            ),
        ),
        "post": (
            *selector_fields,
            _req("subject", "--subject", "Message subject."),
            _f("body_content", "--body-content", "Inline message body."),
            _path("body_file", "--body-file", "Message body file."),
            _choice(
                "reply_policy",
                "--reply-policy",
                "Operator-origin reply policy.",
                ("none", "operator_mailbox"),
            ),
            _many("attach", "--attach", "Attachment path."),
            _f("notify_block", "--notify-block", "Sender-marked notification block."),
            _choice(
                "notify_block_placement",
                "--notify-block-placement",
                "Notification block placement.",
                ("append", "prepend"),
            ),
        ),
        "reply": (
            *selector_fields,
            _req("message_ref", "--message-ref", "Opaque message ref."),
            _f("body_content", "--body-content", "Inline reply body."),
            _path("body_file", "--body-file", "Reply body file."),
            _many("attach", "--attach", "Attachment path."),
        ),
        "mark": (
            *selector_fields,
            _req_many("message_ref", "--message-ref", "Opaque message ref."),
            _flag("read", "--read", "Mark read.", negative_option="--unread"),
            _flag("answered", "--answered", "Mark answered.", negative_option="--unanswered"),
            _flag("archived", "--archived", "Mark archived.", negative_option="--unarchived"),
        ),
        "move": (
            *selector_fields,
            _req_many("message_ref", "--message-ref", "Opaque message ref."),
            _req("destination_box", "--destination-box", "Destination mailbox box."),
        ),
        "archive": (
            *selector_fields,
            _req_many("message_ref", "--message-ref", "Opaque message ref."),
        ),
    }
    return [
        _template(
            f"agents.mail.{verb}",
            ("agents", "mail", verb),
            f"Managed-agent mail fallback {verb}.",
            fields,
            family="agents.mail",
            conflicts=(
                _conflict(
                    "agent_name", "agent_id", message="Agent selectors are mutually exclusive."
                ),
                _conflict(
                    "body_content",
                    "body_file",
                    message="Body content and body file are mutually exclusive.",
                ),
            ),
            required_one_of=(("read", "answered", "archived"),) if verb == "mark" else (),
        )
        for verb, fields in command_fields.items()
    ]
