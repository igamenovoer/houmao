"""Define the host-owned permission groups and resource role templates."""

from collections.abc import Callable
from typing import get_args

from houmao.gateway.authorization_models import Permission, PermissionGroupName

PERMISSION_GROUPS: tuple[PermissionGroupName, ...] = get_args(PermissionGroupName)
DEFAULT_GROUP_SET = Permission(resource="policy", action="admin.default-group.set")
DEFAULT_FALLBACK_SET = Permission(resource="policy", action="admin.default-fallback.set")
RETIRED_MAIL_DELIVER = Permission(resource="agent", action="agent.mail.deliver")
RETIRED_PROMPT = Permission(resource="agent", action="agent.prompt")

_PEER_EFFECTS: tuple[frozenset[str], ...] = (
    frozenset({"agent.status.read", "agent.request.submit"}),
    frozenset(),
    frozenset({"agent.prompt.direct", "agent.command.invoke", "agent.interrupt"}),
)
_PEER_GROUPS = PERMISSION_GROUPS[:3]
FILE_ACTIONS = frozenset({"files.read", "files.edit", "files.push"})
ROLE_TEMPLATE_ACTIONS: dict[str, tuple[str, ...]] = {
    "skill-reviewer": ("files.read",),
    "skill-editor": ("files.read", "files.edit"),
    "skill-publisher": ("files.read", "files.push"),
    "skill-maintainer": ("files.read", "files.edit", "files.push"),
    "mailbox-reader": ("mail.list", "mail.peek"),
    "mailbox-sender": ("mail.send",),
    "ag-ui-viewer": ("ag-ui.output.read",),
    "ag-ui-runner": ("ag-ui.output.read", "ag-ui.input.submit"),
    "plugin-actions": (),
}


def is_admin_exclusive(permission: Permission) -> bool:
    """Identify effects reserved for effective administrators on the target."""

    return (permission.resource == "policy" and permission.action.startswith("admin.")) or (
        permission.resource.startswith("mailbox:")
        and permission.action in {"mail.attachment.owner_file", "mail.post"}
    )


def peer_group_effects(group: PermissionGroupName) -> tuple[str, ...]:
    """List the exact agent effects at one cumulative peer tier."""

    return tuple(sorted(set().union(*_PEER_EFFECTS[: _PEER_GROUPS.index(group) + 1])))


def group_allows(
    group: PermissionGroupName,
    permission: Permission,
    *,
    supports_self: Callable[[Permission], bool],
    supports_common: Callable[[Permission], bool] | None,
) -> bool:
    """Expand a version-one group only for an already supported exact effect."""

    if group == "agent-admin":
        return True
    if group == "managed-self":
        return not is_admin_exclusive(permission) and supports_self(permission)
    tier = _PEER_GROUPS.index(group)
    return (
        permission.resource == "agent"
        and any(permission.action in effects for effects in _PEER_EFFECTS[: tier + 1])
    ) or (
        tier >= 1
        and permission.action in FILE_ACTIONS
        and permission.resource.startswith("files:")
        and supports_common is not None
        and supports_common(permission)
    )
