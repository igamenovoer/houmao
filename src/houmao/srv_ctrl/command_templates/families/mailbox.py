"""Command-template declarations for this command family."""

from __future__ import annotations

from ..builders import (
    _choice,
    _conflict,
    _f,
    _flag,
    _int,
    _many,
    _req,
    _req_path,
    _template,
)
from ..models import (
    CommandTemplate,
    TemplateField,
)


def templates() -> list[CommandTemplate]:
    """Return mailbox command templates."""

    mailbox_root_field = _f("mailbox_root", "--mailbox-root", "Shared mailbox root.")
    repair_fields = (
        _flag(
            "cleanup_staging",
            "--cleanup-staging",
            "Clean staging artifacts during repair.",
            negative_option="--no-cleanup-staging",
        ),
        _flag(
            "quarantine_staging",
            "--quarantine-staging",
            "Quarantine staging artifacts during repair.",
            negative_option="--remove-staging",
        ),
    )
    cleanup_fields = (
        _int(
            "inactive_older_than_seconds",
            "--inactive-older-than-seconds",
            "Inactive-registration age threshold.",
        ),
        _int(
            "stashed_older_than_seconds",
            "--stashed-older-than-seconds",
            "Stashed-registration age threshold.",
        ),
        _flag("dry_run", "--dry-run", "Preview without deleting."),
    )
    clear_message_fields = (
        _flag("dry_run", "--dry-run", "Preview without deleting."),
        _flag("yes", "--yes", "Confirm destructive action."),
    )
    templates: list[CommandTemplate] = []

    def _root_fields(family: str) -> tuple[TemplateField, ...]:
        """Return root-selector fields for one mailbox family."""

        if family == "mailbox":
            return (mailbox_root_field,)
        if family == "project.mailbox":
            return (_project_dir_field(),)
        return ()

    def _root_command_fields(*, family: str, verb: str) -> tuple[TemplateField, ...]:
        """Return fields for one root-level mailbox command."""

        root_fields = _root_fields(family)
        if verb in {"init", "status"}:
            return root_fields
        if verb == "register":
            return (
                *root_fields,
                _req("address", "--address", "Mailbox address."),
                _req("principal_id", "--principal-id", "Mailbox principal id."),
                _choice("mode", "--mode", "Registration mode.", ("safe", "force", "stash")),
                _flag("yes", "--yes", "Confirm destructive replacement."),
            )
        if verb == "unregister":
            return (
                *root_fields,
                _req("address", "--address", "Mailbox address."),
                _choice("mode", "--mode", "Deregistration mode.", ("deactivate", "purge")),
            )
        if verb == "repair":
            return (*root_fields, *repair_fields)
        if verb == "cleanup":
            return (*root_fields, *cleanup_fields)
        if verb == "clear-messages":
            return (*root_fields, *clear_message_fields)
        if verb == "export":
            return (
                *root_fields,
                _req_path("output_dir", "--output-dir", "Archive output directory."),
                _flag("all_accounts", "--all-accounts", "Export all accounts."),
                _many("address", "--address", "Address scope."),
                _choice(
                    "symlink_mode",
                    "--symlink-mode",
                    "Symlink mode.",
                    ("materialize", "preserve"),
                ),
            )
        raise AssertionError(f"Unhandled mailbox verb: {verb}")

    for prefix, family, root_verbs in (
        (
            ("mailbox",),
            "mailbox",
            (
                "init",
                "status",
                "register",
                "unregister",
                "repair",
                "cleanup",
                "clear-messages",
                "export",
            ),
        ),
        (
            ("project", "mailbox"),
            "project.mailbox",
            (
                "init",
                "status",
                "register",
                "unregister",
                "repair",
                "cleanup",
                "clear-messages",
                "export",
            ),
        ),
    ):
        for verb in root_verbs:
            templates.append(
                _template(
                    f"{family}.{verb}",
                    (*prefix, verb),
                    f"{family} {verb}.",
                    _root_command_fields(family=family, verb=verb),
                    family=family,
                    conflicts=(
                        _conflict(
                            "all_accounts",
                            "address",
                            message="Mailbox export scopes are mutually exclusive.",
                        ),
                    )
                    if verb == "export"
                    else (),
                    required_one_of=(("all_accounts", "address"),) if verb == "export" else (),
                )
            )
    for prefix, family in ((("mailbox",), "mailbox"), (("project", "mailbox"), "project.mailbox")):
        for noun, child_verbs in (
            ("accounts", ("list", "get")),
            ("messages", ("list", "get", "clear")),
        ):
            for verb in child_verbs:
                mailbox_fields: tuple[TemplateField, ...] = _root_fields(family)
                if noun == "accounts" and verb == "get":
                    mailbox_fields = (
                        *mailbox_fields,
                        _req("address", "--address", "Mailbox address."),
                    )
                elif noun == "messages":
                    mailbox_fields = (
                        *mailbox_fields,
                        _req("address", "--address", "Mailbox address."),
                    )
                    if verb == "get":
                        mailbox_fields = (
                            *mailbox_fields,
                            _req("message_id", "--message-id", "Canonical message id."),
                        )
                    elif verb == "clear":
                        mailbox_fields = (*mailbox_fields, *clear_message_fields)
                templates.append(
                    _template(
                        f"{family}.{noun}.{verb}",
                        (*prefix, noun, verb),
                        f"{family} {noun} {verb}.",
                        mailbox_fields,
                        family=family,
                    )
                )
    for verb in ("status", "register", "unregister"):
        fields_by_verb = {
            "status": (
                _f("agent_name", "--agent-name", "Friendly managed-agent name."),
                _f("agent_id", "--agent-id", "Managed-agent id."),
            ),
            "register": (
                _f("agent_name", "--agent-name", "Friendly managed-agent name."),
                _f("agent_id", "--agent-id", "Managed-agent id."),
                _f("principal_id", "--principal-id", "Mailbox principal id."),
                _f("address", "--address", "Mailbox address."),
                _f("mailbox_root", "--mailbox-root", "Mailbox root."),
                _choice("mode", "--mode", "Registration mode.", ("safe", "force", "stash")),
                _flag("yes", "--yes", "Confirm mutation."),
            ),
            "unregister": (
                _f("agent_name", "--agent-name", "Friendly managed-agent name."),
                _f("agent_id", "--agent-id", "Managed-agent id."),
                _choice("mode", "--mode", "Deregistration mode.", ("deactivate", "purge")),
            ),
        }
        templates.append(
            _template(
                f"agents.mailbox.{verb}",
                ("agents", "mailbox", verb),
                f"Managed-agent mailbox {verb}.",
                fields_by_verb[verb],
                family="agents.mailbox",
                conflicts=(
                    _conflict(
                        "agent_name", "agent_id", message="Agent selectors are mutually exclusive."
                    ),
                ),
            )
        )
    return templates


def _project_dir_field() -> TemplateField:
    """Return the optional project group selector field."""

    return _f(
        "project_dir",
        "--project-dir",
        "Human-facing project directory.",
        value_type="path",
        argv_insert_index=2,
    )
