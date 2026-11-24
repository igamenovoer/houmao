"""Apply retained owner authorization at the offline inbox deposit boundary."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import ExitStack, contextmanager
from hashlib import sha256
from pathlib import Path
import sqlite3
from typing import TYPE_CHECKING

from houmao.execution.context import execution_binding_scope
from houmao.gateway._access_storage import GatewayAccessError
from houmao.gateway.authorization import GatewayAuthorizer, transport_principal
from houmao.gateway.authorization_catalog import MAIL_DELIVER
from houmao.gateway.authorization_models import AuthorizationActor
from houmao.mailbox.filesystem import MailboxRegistration
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR

if TYPE_CHECKING:
    from houmao.agents.realm_controller.gateway_access_runtime import GatewayRuntimeAccess


def _select_recipient(
    registration: MailboxRegistration,
    *,
    mailbox_root: Path,
    registry_root: Path | None,
    required: bool,
) -> GatewayRuntimeAccess | None:
    """Resolve a stopped or running recipient through its exact retained binding."""

    from houmao.agents.realm_controller.gateway_access_runtime import gateway_access_for_manifest
    from houmao.agents.realm_controller.manifest import (
        load_session_manifest,
        parse_session_manifest_payload,
    )
    from houmao.agents.realm_controller.registry_storage import (
        load_managed_agent_record_by_agent_id,
    )

    hint = registration.manifest_path_hint
    if registry_root is None and hint is not None:
        hinted = gateway_access_for_manifest(Path(hint))
        registry_root = Path(hinted.execution_binding.registry_root)
    env = (
        {HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: str(registry_root)}
        if registry_root is not None
        else None
    )
    record = load_managed_agent_record_by_agent_id(registration.owner_principal_id, env=env)
    if record is None:
        if required or hint is not None:
            raise GatewayAccessError(503, "recipient_policy_unavailable")
        return None
    current = gateway_access_for_manifest(Path(record.runtime.manifest_path))
    if (
        current.target.incarnation != record.generation_id
        or current.owner.agent_id != record.agent_id
        or current.execution_binding != record.execution_binding
    ):
        raise GatewayAccessError(503, "recipient_policy_unavailable")
    handle = load_session_manifest(current.manifest_path)
    manifest = parse_session_manifest_payload(handle.payload, source="recipient runtime manifest")
    durable = manifest.launch_plan.mailboxes.offline.binding
    if (
        manifest.registry_generation_id != record.generation_id
        or manifest.runtime.execution_binding != current.execution_binding
        or durable is None
        or durable.transport not in {"filesystem", "registry"}
        or durable.binding_id != registration.registration_id
        or durable.address != registration.address
        or durable.agent_id != registration.owner_principal_id
        or (
            durable.transport == "filesystem"
            and Path(durable.filesystem_root).resolve() != mailbox_root
        )
    ):
        raise GatewayAccessError(409, "recipient_mail_binding_changed")
    return current


@contextmanager
def require_open_provider_binding(
    manifest_path: Path, *, for_write: bool = False
) -> Iterator[None]:
    """Refuse managed provider access until all configured ingress paths are qualified."""

    from houmao.agents.realm_controller.gateway_access_runtime import gateway_access_for_manifest
    from houmao.agents.realm_controller.manifest import load_session_manifest
    from houmao.mailbox.online_models import OnlineBindingError

    try:
        handle = load_session_manifest(manifest_path)
        access = (
            gateway_access_for_manifest(manifest_path)
            if handle.payload.get("registry_generation_id") is not None
            else None
        )
    except (RuntimeError, OSError, ValueError):
        raise OnlineBindingError(
            "recipient_policy_unavailable", "Recipient policy is unavailable"
        ) from None
    if access is None:
        yield
        return
    with ExitStack() as stack:
        try:
            state = (
                stack.enter_context(access.store.transaction()).snapshot
                if for_write
                else access.store.snapshot()
            )
            access.require_current()
        except (RuntimeError, OSError, ValueError, sqlite3.Error):
            raise OnlineBindingError(
                "recipient_policy_unavailable", "Recipient policy is unavailable"
            ) from None
        if state.admin_mode != "open":
            raise OnlineBindingError(
                "provider_delivery_unqualified",
                "This provider inbox cannot enforce the current recipient policy",
            )
        yield


@contextmanager
def require_delivery_authority(
    connection: sqlite3.Connection,
    *,
    mailbox_root: Path,
    registry_root: Path | None,
    sender: MailboxRegistration,
    sender_verified: bool,
    recipients: Mapping[str, MailboxRegistration],
    message_id: str,
) -> Iterator[bool]:
    """Hold the recipient writer fences through the first visible delivery effect."""

    has_markers = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE name = 'offline_policy_members' AND type = 'table'"
    ).fetchone()
    pending = []
    for recipient in recipients.values():
        required = bool(
            has_markers
            and connection.execute(
                "SELECT 1 FROM offline_policy_members WHERE registration_id = ?",
                (recipient.registration_id,),
            ).fetchone()
        )
        try:
            with execution_binding_scope(None, inherit=False):
                access = _select_recipient(
                    recipient,
                    mailbox_root=mailbox_root,
                    registry_root=registry_root,
                    required=required,
                )
        except GatewayAccessError:
            raise
        except (RuntimeError, OSError, ValueError):
            raise GatewayAccessError(503, "recipient_policy_unavailable") from None
        if access is not None:
            pending.append(access)

    issuer = "offline:" + sha256(str(mailbox_root).encode()).hexdigest()
    with ExitStack() as fences:
        for access in sorted(pending, key=lambda item: item.private_root):
            try:
                transaction = fences.enter_context(access.store.transaction())
                with execution_binding_scope(None, inherit=False):
                    access.require_current()
            except (RuntimeError, OSError, ValueError, sqlite3.Error):
                raise GatewayAccessError(503, "recipient_policy_unavailable") from None
            state = transaction.snapshot
            if sender_verified:
                actor = AuthorizationActor(
                    kind="mail",
                    principal_id=transport_principal(state, sender.owner_principal_id),
                    transport_issuer=issuer,
                    transport_member=sender.owner_principal_id,
                    transport_binding=sender.registration_id,
                )
            elif state.admin_mode == "open":
                actor = AuthorizationActor(kind="anonymous")
            else:
                raise GatewayAccessError(401, "sender_authority_unverified")
            authorizer = GatewayAuthorizer(access.store, catalog=(MAIL_DELIVER,))
            decision = authorizer.authorize_snapshot(
                state, actor, (MAIL_DELIVER,), target=access.target, listener_id=issuer
            )
            operation_id = "mail:" + sha256(message_id.encode()).hexdigest()
            transaction.record_handoff(operation_id, decision)
        yield bool(pending)
