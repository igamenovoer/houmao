"""Declare the gateway's externally available effects and canonical resources."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json

from houmao.agents.realm_controller.gateway_models import (
    GatewayPromptControlRequestV1,
    GatewayReminderCreateBatchV1,
    GatewayReminderDefinitionV1,
    GatewayReminderPutV1,
    GatewayRequestCreateV1,
    GatewayRequestPayloadSubmitPromptV1,
)
from houmao.gateway._access_storage import GatewayAccessError
from houmao.gateway.access_models import MANAGED_SELF_PATH, parse_access_document
from houmao.gateway.authorization_catalog import DEFAULT_GROUP_SET, MAIL_DELIVER
from houmao.gateway.authorization_models import Permission
from houmao.gateway.file_edits.contracts import FILE_EDIT_PATH, FILE_REQUESTS

WEB_ENTRY = Permission(resource="native:web", action="web.enter")
WORK_REQUEST = Permission(resource="agent", action="agent.request.submit")
PROMPT = Permission(resource="agent", action="agent.prompt.direct")
COMMAND_INVOKE = Permission(resource="agent", action="agent.command.invoke")
INTERRUPT = Permission(resource="agent", action="agent.interrupt")
RAW_INPUT = Permission(resource="agent", action="agent.input.raw")
SELECT_SESSION = Permission(resource="native", action="native.session.select")
OVERRIDE_MODEL = Permission(resource="native", action="native.model.override")
OPERATOR_PROMPT = Permission(resource="agent", action="agent.prompt.operator")
STATUS = Permission(resource="agent", action="agent.status.read")
ATTACHMENT_ACTION = "mail.attachment.owner_file"
ADMIN_ADD = Permission(resource="policy", action="admin.key.add")
ADMIN_REMOVE = Permission(resource="policy", action="admin.key.remove")
MANAGED_SELF_CHANGE = Permission(resource="policy", action="admin.self-key.manage")
PUBLIC_NOTICE = Permission(resource="agent", action="public.message")
PUBLIC_PROMPT = Permission(resource="agent", action="public.prompt")
PUBLIC_INPUT_PERMISSIONS = frozenset({PUBLIC_NOTICE, PUBLIC_PROMPT})
MAIL_ACTIONS = (
    "list",
    "peek",
    "read",
    "send",
    "reply",
    "mark",
    "move",
    "archive",
    "post",
)
_AG_UI_RESOLVED = frozenset(
    {
        ("POST", "/v1/ag-ui/connect"),
        ("POST", "/v1/ag-ui/runs"),
        ("POST", "/v1/ag-ui/events"),
        ("DELETE", "/v1/ag-ui/connections/{connection_id}"),
        ("PUT", "/v1/ag-ui/active-thread"),
        ("DELETE", "/v1/ag-ui/active-thread"),
    }
)
_DYNAMIC_MAIL_ACTIONS = frozenset({*(f"mail.{name}" for name in MAIL_ACTIONS), ATTACHMENT_ACTION})


@dataclass(frozen=True)
class GatewayOperation:
    """Describe an HTTP operation before selecting any body-specific effects."""

    path: str
    permission: Permission | None
    selector: str | None = None
    channel: str | None = None

    @property
    def transport_public(self) -> bool:
        """Return whether the route is a public transport entrypoint."""

        return self.permission is None and self.selector is None

    @property
    def direct_web_entry(self) -> bool:
        """Return whether this operation can enter a direct local native Web app."""

        return self.permission == WEB_ENTRY

    @property
    def registration(self) -> bool:
        """Return whether this route can consume first-key proof."""

        return self.permission == ADMIN_ADD

    def bind_channel(self, channel: str | None) -> GatewayOperation:
        """Carry the matched mailbox channel without reading the route template again."""

        return replace(self, channel=channel) if self.selector == "mail" else self

    def permissions(self, body: bytes) -> tuple[Permission, ...]:
        """Select all declared effects using the exact admitted raw body."""

        if self.selector in {"queue", "prompt"}:
            try:
                if self.selector == "queue":
                    request = parse_access_document(GatewayRequestCreateV1, body)
                    if request.kind == "submit_work_request":
                        return (WORK_REQUEST,)
                    if not isinstance(request.payload, GatewayRequestPayloadSubmitPromptV1):
                        return (INTERRUPT,)
                    payload: GatewayRequestPayloadSubmitPromptV1 | GatewayPromptControlRequestV1 = (
                        request.payload
                    )
                else:
                    payload = parse_access_document(GatewayPromptControlRequestV1, body)
            except ValueError:
                raise GatewayAccessError(422, "invalid_operation") from None
            return prompt_permissions(payload)
        if self.selector == "mail":
            assert self.permission is not None
            document = _operation_object(body)
            binding = document.get("expected_binding_id")
            if (
                not isinstance(binding, str)
                or not binding
                or self.channel
                not in {
                    "offline",
                    "online",
                }
            ):
                raise GatewayAccessError(422, "invalid_operation")
            resource = mailbox_resource(self.channel, binding)
            permissions = [Permission(resource=resource, action=self.permission.action)]
            if self.permission.action in {"mail.send", "mail.reply", "mail.post"} and document.get(
                "attachments"
            ):
                permissions.append(Permission(resource=resource, action=ATTACHMENT_ACTION))
            return tuple(permissions)
        if self.selector in {"reminder-create", "reminder-update"}:
            assert self.permission is not None
            try:
                if self.selector == "reminder-create":
                    reminders = parse_access_document(GatewayReminderCreateBatchV1, body).reminders
                else:
                    reminders = [parse_access_document(GatewayReminderPutV1, body)]
            except ValueError:
                raise GatewayAccessError(422, "invalid_operation") from None
            return tuple(
                dict.fromkeys(
                    (
                        self.permission,
                        *(
                            permission
                            for reminder in reminders
                            for permission in reminder_input_permissions(reminder)
                        ),
                    )
                )
            )
        return (self.permission,) if self.permission is not None else ()


def mailbox_resource(channel: str, binding_id: str) -> str:
    """Name one mailbox binding using its unambiguous exact identifier."""

    if channel not in {"offline", "online"}:
        raise ValueError("Invalid mailbox channel")
    digest = hashlib.sha256(binding_id.encode()).hexdigest()
    return f"mailbox:{channel}:{digest}"


def prompt_permissions(
    payload: GatewayRequestPayloadSubmitPromptV1 | GatewayPromptControlRequestV1,
) -> tuple[Permission, ...]:
    """Authorize requested native session, model, and operator effects separately."""

    permissions = list(direct_text_permissions(payload.prompt))
    if payload.chat_session is not None and SELECT_SESSION not in permissions:
        permissions.append(SELECT_SESSION)
    if payload.execution is not None:
        permissions.append(OVERRIDE_MODEL)
    if (
        isinstance(payload, GatewayPromptControlRequestV1)
        and payload.admission_policy != "ready_only"
    ):
        permissions.append(OPERATOR_PROMPT)
    return tuple(permissions)


def native_command_candidate(text: str) -> str | None:
    """Select the first slash token before choosing native control effects."""

    content = text.lstrip()
    if content.startswith("/"):
        return content.split(maxsplit=1)[0]
    return None


def direct_text_permissions(text: str) -> tuple[Permission, ...]:
    """Require command and context effects for slash-like direct text."""

    command = native_command_candidate(text)
    if command in {"/clear", "/new"}:
        return (PROMPT, COMMAND_INVOKE, SELECT_SESSION)
    if command is not None:
        return (PROMPT, COMMAND_INVOKE)
    return (PROMPT,)


def reminder_input_permissions(
    reminder: GatewayReminderDefinitionV1,
) -> tuple[Permission, ...]:
    """Select the same exact effects as equivalent immediate input."""

    if reminder.send_keys is not None:
        return (RAW_INPUT,)
    assert reminder.prompt is not None
    return direct_text_permissions(reminder.prompt)


def supports_mail_permission(permission: Permission) -> bool:
    """Recognize mailbox permissions for one canonical binding fingerprint."""

    prefix, _, digest = permission.resource.rpartition(":")
    return (
        prefix in {"mailbox:offline", "mailbox:online"}
        and len(digest) == 64
        and all(c in "0123456789abcdef" for c in digest)
        and permission.action in _DYNAMIC_MAIL_ACTIONS
    )


def _operation_object(body: bytes) -> dict[str, object]:
    """Reject ambiguous JSON before choosing an operation's required effects."""

    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        """Require a single value for each object member."""

        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate operation field")
            result[key] = value
        return result

    try:
        document = json.loads(body, object_pairs_hook=unique)
    except (UnicodeError, ValueError, RecursionError):
        raise GatewayAccessError(422, "invalid_operation") from None
    if not isinstance(document, dict):
        raise GatewayAccessError(422, "invalid_operation")
    return document


def _op(path: str, resource: str, action: str) -> GatewayOperation:
    """Associate a route with one exact supported effect."""

    return GatewayOperation(path, Permission(resource=resource, action=action))


_public: tuple[tuple[str, str], ...] = (
    ("GET", "/"),
    ("GET", "/health"),
    ("GET", "/v1/endpoint"),
    ("GET", "/v1/web/enter"),
    ("POST", "/v1/auth/challenge"),
    ("POST", "/v1/web/login"),
    ("POST", "/v1/web/login/{attempt_id}/prove"),
    ("POST", "/v1/web/login/{attempt_id}/claim"),
)
_operations = (
    ("GET", "/v1/usage", "agent", "agent.usage.read"),
    ("GET", "/v1/memory", "memory", "memory.inspect"),
    ("GET", "/v1/memory/memo", "memory:memo", "memory.memo.read"),
    ("PUT", "/v1/memory/memo", "memory:memo", "memory.memo.write"),
    ("POST", "/v1/memory/memo/append", "memory:memo", "memory.memo.append"),
    ("GET", "/v1/mail/status", "mailbox", "mail.status.read"),
    ("GET", "/v1/plugins", "plugins", "plugin.list"),
    ("GET", "/v1/native-home", "native", "native.observe"),
    ("GET", "/v1/control/refresh", "native", "native.refresh.observe"),
    ("POST", "/v1/control/refresh", "native", "native.refresh.apply"),
    ("GET", "/v1/control/tui/state", "native:tui", "native.observe"),
    ("GET", "/v1/control/tui/history", "native:tui", "native.history.read"),
    ("GET", "/v1/control/web/state", "native:web", "native.observe"),
    ("GET", "/v1/control/web/history", "native:web", "native.history.read"),
    ("GET", "/v1/control/service/state", "native:service", "native.observe"),
    ("GET", "/v1/control/service/requests/{request_id}", "native:service", "native.request.read"),
    ("GET", "/v1/control/headless/state", "native:headless", "native.observe"),
    (
        "POST",
        "/v1/control/headless/next-prompt-session",
        "native:headless",
        "native.session.select",
    ),
    ("POST", "/v1/control/tui/note-prompt", "native:tui", "native.prompt.note"),
    ("GET", "/v1/reminders", "reminders", "reminder.list"),
    ("GET", "/v1/reminders/{reminder_id}", "reminders", "reminder.read"),
    ("DELETE", "/v1/reminders/{reminder_id}", "reminders", "reminder.delete"),
    ("GET", "/v1/mail/online/binding", "mailbox:online", "mail.binding.read"),
    ("PUT", "/v1/mail/online/binding", "mailbox:online", "mail.binding.attach"),
    ("POST", "/v1/mail/online/binding/refresh", "mailbox:online", "mail.binding.refresh"),
    ("POST", "/v1/mail/online/binding/reconnect", "mailbox:online", "mail.binding.reconnect"),
    ("DELETE", "/v1/mail/online/binding", "mailbox:online", "mail.binding.detach"),
    ("GET", "/v1/mail-notifier/{channel}", "mailbox", "mail.notifier.read"),
    ("PUT", "/v1/mail-notifier/{channel}", "mailbox", "mail.notifier.update"),
    ("DELETE", "/v1/mail-notifier/{channel}", "mailbox", "mail.notifier.delete"),
    ("GET", "/v1/ag-ui/capabilities", "ag-ui", "ag-ui.capabilities.read"),
    ("GET", "/v1/ag-ui/destination", "ag-ui", "ag-ui.destination.read"),
    ("GET", "/v1/ag-ui/active-thread", "ag-ui", "ag-ui.destination.read"),
    ("PUT", "/v1/ag-ui/active-thread", "ag-ui", "ag-ui.destination.update"),
    ("DELETE", "/v1/ag-ui/active-thread", "ag-ui", "ag-ui.destination.update"),
    ("POST", "/v1/ag-ui/connect", "ag-ui", "ag-ui.output.read"),
    ("POST", "/v1/ag-ui/runs", "ag-ui", "ag-ui.input.submit"),
    ("POST", "/v1/ag-ui/events", "ag-ui", "ag-ui.event.publish"),
    ("DELETE", "/v1/ag-ui/connections/{connection_id}", "ag-ui", "ag-ui.connection.close"),
)

CORE_OPERATIONS = {
    **{(method, path): GatewayOperation(path, None) for method, path in _public},
    **{
        ("POST", f"{FILE_EDIT_PATH}/{name}"): GatewayOperation(
            f"{FILE_EDIT_PATH}/{name}", None, selector="files-resolved"
        )
        for name in FILE_REQUESTS
    },
    **{
        (method, path): (
            GatewayOperation(path, None, selector="ag-ui-resolved")
            if (method, path) in _AG_UI_RESOLVED
            else _op(path, resource, action)
        )
        for method, path, resource, action in _operations
    },
    **{
        ("POST", f"/v1/memory/pages/{name}"): _op(
            f"/v1/memory/pages/{name}", "memory:pages", f"memory.page.{name}"
        )
        for name in ("tree", "resolve", "read", "write", "append", "delete")
    },
    **{
        ("POST", f"/v1/mail/{{channel}}/{name}"): GatewayOperation(
            f"/v1/mail/{{channel}}/{name}",
            Permission(resource="mailbox", action=f"mail.{name}"),
            selector="mail",
        )
        for name in MAIL_ACTIONS
    },
    ("GET", "/v1/status"): GatewayOperation("/v1/status", STATUS),
    ("POST", "/v1/messages"): GatewayOperation("/v1/messages", PUBLIC_NOTICE),
    ("POST", "/v1/public/prompt"): GatewayOperation("/v1/public/prompt", PUBLIC_PROMPT),
    ("POST", "/v1/requests"): GatewayOperation("/v1/requests", None, selector="queue"),
    ("POST", "/v1/control/prompt"): GatewayOperation(
        "/v1/control/prompt", PROMPT, selector="prompt"
    ),
    ("POST", "/v1/control/send-keys"): GatewayOperation("/v1/control/send-keys", RAW_INPUT),
    ("POST", "/v1/reminders"): GatewayOperation(
        "/v1/reminders",
        Permission(resource="reminders", action="reminder.create"),
        selector="reminder-create",
    ),
    ("PUT", "/v1/reminders/{reminder_id}"): GatewayOperation(
        "/v1/reminders/{reminder_id}",
        Permission(resource="reminders", action="reminder.update"),
        selector="reminder-update",
    ),
    ("POST", "/v1/web/entry-ticket"): GatewayOperation("/v1/web/entry-ticket", WEB_ENTRY),
    ("POST", "/v1/admin/keys"): GatewayOperation("/v1/admin/keys", ADMIN_ADD),
    ("DELETE", "/v1/admin/keys/{key_id}"): GatewayOperation(
        "/v1/admin/keys/{key_id}", ADMIN_REMOVE
    ),
    ("PUT", MANAGED_SELF_PATH): GatewayOperation(
        MANAGED_SELF_PATH, MANAGED_SELF_CHANGE, selector="self-registration"
    ),
    ("PUT", "/v1/admin/default-permission-group"): GatewayOperation(
        "/v1/admin/default-permission-group", DEFAULT_GROUP_SET
    ),
}

CORE_PERMISSIONS = frozenset(
    {
        MAIL_DELIVER,
        WORK_REQUEST,
        PROMPT,
        COMMAND_INVOKE,
        INTERRUPT,
        SELECT_SESSION,
        OVERRIDE_MODEL,
        OPERATOR_PROMPT,
        *(
            operation.permission
            for operation in CORE_OPERATIONS.values()
            if operation.permission is not None and operation.selector != "mail"
        ),
    }
)
