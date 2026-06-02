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

    single_selector_fields = (
        _f(
            "agent_name",
            "--agent-name",
            "Friendly managed-agent name.",
            argv_insert_index=3,
        ),
        _f("agent_id", "--agent-id", "Managed-agent id.", argv_insert_index=3),
        _int("port", "--port", "Houmao pair authority port."),
    )
    self_selector_fields: tuple[TemplateField, ...] = ()
    command_fields: dict[str, tuple[TemplateField, ...]] = {
        "resolve-live": (),
        "status": (),
        "list": (
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
            _req("message_ref", "--message-ref", "Opaque message ref."),
            _f("box", "--box", "Required source box."),
        ),
        "read": (
            _req("message_ref", "--message-ref", "Opaque message ref."),
            _f("box", "--box", "Required source box."),
        ),
        "send": (
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
            _req("message_ref", "--message-ref", "Opaque message ref."),
            _f("body_content", "--body-content", "Inline reply body."),
            _path("body_file", "--body-file", "Reply body file."),
            _many("attach", "--attach", "Attachment path."),
        ),
        "mark": (
            _req_many("message_ref", "--message-ref", "Opaque message ref."),
            _flag("read", "--read", "Mark read.", negative_option="--unread"),
            _flag("answered", "--answered", "Mark answered.", negative_option="--unanswered"),
            _flag("archived", "--archived", "Mark archived.", negative_option="--unarchived"),
        ),
        "move": (
            _req_many("message_ref", "--message-ref", "Opaque message ref."),
            _req("destination_box", "--destination-box", "Destination mailbox box."),
        ),
        "archive": (_req_many("message_ref", "--message-ref", "Opaque message ref."),),
    }
    templates: list[CommandTemplate] = []
    for scope, selector_fields in (
        ("single", single_selector_fields),
        ("self", self_selector_fields),
    ):
        for verb, fields in command_fields.items():
            required_one_of: list[tuple[str, ...]] = []
            if scope == "single":
                required_one_of.append(("agent_name", "agent_id"))
            if verb == "mark":
                required_one_of.append(("read", "answered", "archived"))
            templates.append(
                _template(
                    f"agents.{scope}.mail.{verb}",
                    ("agents", scope, "mail", verb),
                    f"Managed-agent {scope} mail fallback {verb}.",
                    (*selector_fields, *fields),
                    family=f"agents.{scope}.mail",
                    conflicts=(
                        _conflict(
                            "agent_name",
                            "agent_id",
                            message="Agent selectors are mutually exclusive.",
                        ),
                        _conflict(
                            "body_content",
                            "body_file",
                            message="Body content and body file are mutually exclusive.",
                        ),
                    ),
                    required_one_of=tuple(required_one_of),
                )
            )
    return templates
