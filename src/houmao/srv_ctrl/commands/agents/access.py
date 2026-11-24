"""Owner and signed gateway access commands for selected managed agents."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import re
import time
from typing import Literal

import click

from houmao.ag_ui.authorization import supports_ag_ui_permission
from houmao.agents.realm_controller.errors import GatewayHttpError, SessionManifestError
from houmao.agents.realm_controller.gateway_access_runtime import (
    GatewayRuntimeAccess,
    gateway_access_for_manifest,
    load_gateway_admin_seed,
    load_gateway_deployment,
    owner_gateway_client_binding,
    save_gateway_deployment,
)
from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.agents.realm_controller.gateway_models import GATEWAY_PROTOCOL_VERSION
from houmao.agents.realm_controller.gateway_storage import (
    gateway_paths_from_manifest_path,
    load_gateway_current_instance,
)
from houmao.agents.realm_controller.self_manifest import resolve_self_manifest
from houmao.cao.rest_client import CaoApiError
from houmao.gateway._access_sshsig import PrivateKey
from houmao.gateway.access import (
    GatewayAccessError,
    GatewayAccessPolicy,
    GatewayAdminKey,
    GatewayChallengeRequest,
    GatewayClientBinding,
    GatewayLaunchSeed,
    GatewayOwner,
    GatewayRequestBinding,
    GatewayTarget,
    load_gateway_signer,
    public_key_text,
    sign_sshsig,
    sshsig_header,
    validate_gateway_base_url,
)
from houmao.gateway._access_sshsig import key_fingerprint
from houmao.gateway.access_models import MANAGED_SELF_PATH, ManagedSelfChange, ProofPurpose
from houmao.gateway.authorization import GatewayAuthorizer
from houmao.gateway.authorization_catalog import (
    DEFAULT_GROUP_SET,
    FILE_ACTIONS,
    PERMISSION_GROUPS,
    ROLE_TEMPLATE_ACTIONS,
    group_allows,
    is_admin_exclusive,
    peer_group_effects,
)
from houmao.gateway.authorization_models import (
    BUILTIN_PEER_ROLES,
    AuthorizationActor,
    Credential,
    DefaultPermissionGroupRequest,
    Permission,
    PermissionGroupName,
    PolicySnapshot,
    Principal,
    RoleAssignment,
    RoleDefinition,
    RoleTemplate,
    ScopedGrant,
    seed_snapshot,
)
from houmao.gateway.deployment import (
    GatewayDeployment,
    GatewayEndpointDescriptor,
    owner_gateway_base_url,
)
from houmao.gateway.operations import CORE_PERMISSIONS, supports_mail_permission
from houmao.passive_server.admission import PASSIVE_PERMISSIONS
from houmao.passive_server.client import PassiveServerClient
from houmao.srv_ctrl.commands.common import (
    ManagedAgentScopeContext,
    get_managed_agent_scope_context,
)
from houmao.srv_ctrl.commands.managed_agents import resolve_owner_gateway_access
from houmao.srv_ctrl.commands.output import emit

_FILE = click.Path(exists=True, dir_okay=False, path_type=Path)
_EXPIRES = click.IntRange(min=0)
_ENDPOINT_REFUSED = "Could not verify the selected gateway target and listener."
_FILE_RESOURCE = re.compile(r"files:[a-f0-9]{32}")
_INSPECTION_PERMISSIONS = (
    CORE_PERMISSIONS
    | PASSIVE_PERMISSIONS
    | {Permission(resource="plugins", action="plugin.status.read")}
)


@click.group(name="access")
def single_access_group() -> None:
    """Manage retained gateway policy or use a verified signed gateway caller."""


@click.group(name="access")
def self_access_group() -> None:
    """Inspect the managed caller's configured peer identity."""


@contextmanager
def _access_errors() -> Iterator[None]:
    """Display bounded diagnostics without signer paths or request details."""

    try:
        yield
    except GatewayAccessError as error:
        raise click.ClickException(f"{error.detail} ({error.code})") from None
    except (GatewayHttpError, CaoApiError) as error:
        if error.status_code is not None:
            raise click.ClickException(
                f"Gateway refused the operation (HTTP {error.status_code})."
            ) from None
        raise click.ClickException("Gateway response could not be confirmed.") from None
    except (OSError, SessionManifestError, ValueError):
        raise click.ClickException(
            "Gateway access input or owner authority is unavailable or invalid."
        ) from None


def _selected() -> ManagedAgentScopeContext:
    """Select the requested target independently of any signing identity."""

    scope = get_managed_agent_scope_context()
    assert scope is not None and scope.scope == "single"
    return scope


def _owner_access() -> GatewayRuntimeAccess:
    """Read the selected target's verified local owner authority."""

    scope = _selected()
    return resolve_owner_gateway_access(agent_id=scope.agent_id, agent_name=scope.agent_name)


def _summary(state: PolicySnapshot, **fields: object) -> dict[str, object]:
    """Render a bounded policy receipt or inspection header."""

    return {
        "agent_id": state.owner.agent_id,
        "context_id": state.owner.context_id,
        "policy_revision": state.revision,
        "roster_revision": state.roster_revision,
        "admin_mode": state.admin_mode,
        "default_permission_group": state.default_permission_group,
        "default_permission_group_version": state.default_permission_group_version,
        "default_permission_revision": state.default_permission_revision,
        **fields,
    }


def _update(
    audit_action: str,
    transform: Callable[[PolicySnapshot], PolicySnapshot],
    *,
    selected_access: GatewayRuntimeAccess | None = None,
    **fields: object,
) -> None:
    """Apply a local owner mutation under the current target and policy fence."""

    with _access_errors():
        access = selected_access if selected_access is not None else _owner_access()

        def apply(state: PolicySnapshot) -> PolicySnapshot:
            """Revalidate the selected generation inside the policy transaction."""

            access.require_current()
            return transform(state)

        state = access.store.update(apply, actor="owner", action=audit_action)
        emit(_summary(state, **fields))


@single_access_group.command(name="init")
@click.option("--empty", is_flag=True, help="Intentionally initialize an open admin roster.")
@click.option("--seed", type=_FILE, help="Owner-private JSON seed with the initial admin keys.")
@click.option(
    "--manifest",
    type=_FILE,
    help="Absolute owner runtime manifest when a retired registry record cannot be selected.",
)
def initialize_policy(empty: bool, seed: Path | None, manifest: Path | None) -> None:
    """Explicitly provision the selected owner's new-schema retained policy."""

    if empty == (seed is not None):
        raise click.UsageError("Choose exactly one of --empty or --seed.")
    with _access_errors():
        scope = _selected()
        access = resolve_owner_gateway_access(
            agent_id=scope.agent_id, agent_name=scope.agent_name, recovery_manifest=manifest
        )
        launch_seed = load_gateway_admin_seed(seed) if seed is not None else GatewayLaunchSeed()
        access.require_current()
        if launch_seed.admin_keys:
            access.require_keyed_mail_qualification()
        state = access.store.initialize(
            seed_snapshot(access.owner, launch_seed), allow_retired=True
        )
        access.require_current()
        emit(_summary(state))


@single_access_group.command(name="principal-add")
@click.argument("principal_id")
@click.option("--kind", type=click.Choice(("operator", "service", "agent")), required=True)
@click.option("--label", required=True, help="Owner-chosen display label.")
@click.option("--logical-agent-id", help="Stable logical ID required for an agent principal.")
def add_principal(principal_id: str, kind: str, label: str, logical_agent_id: str | None) -> None:
    """Add a stable target-local principal for a person, service, or peer."""

    def change(state: PolicySnapshot) -> PolicySnapshot:
        """Append a principal without implicitly linking it to any enrolled key."""

        principal = Principal.model_validate(
            {
                "principal_id": principal_id,
                "kind": kind,
                "label": label,
                "logical_agent_id": logical_agent_id,
            }
        )
        return state.model_copy(update={"principals": (*state.principals, principal)})

    _update("principal.add", change, principal_id=principal_id)


@single_access_group.command(name="credential-enroll")
@click.argument("principal_id")
@click.option("--public-key", "key_file", type=_FILE, required=True)
def enroll_credential(principal_id: str, key_file: Path) -> None:
    """Enroll an authenticated SSH public key for an existing principal."""

    with _access_errors():
        key = Credential(principal_id=principal_id, public_key=_read_public_key(key_file))
        _update(
            "credential.enroll",
            lambda state: state.model_copy(update={"credentials": (*state.credentials, key)}),
            principal_id=principal_id,
            key_id=key.key_id,
        )


@single_access_group.command(name="credential-revoke")
@click.argument("key_id")
def revoke_credential(key_id: str) -> None:
    """Revoke this key's credential and any admin qualification it carries."""

    def change(state: PolicySnapshot) -> PolicySnapshot:
        """Remove one exact key while retaining the principal and its permissions."""

        if state.find_credential(key_id) is None:
            raise GatewayAccessError(404, "unknown_key")
        return state.model_copy(
            update={"credentials": tuple(key for key in state.credentials if key.key_id != key_id)}
        )

    _update("credential.revoke", change, key_id=key_id)


@single_access_group.command(name="grant")
@click.argument("principal_id")
@click.argument("resource")
@click.argument("action")
@click.option("--expires-at", type=_EXPIRES, help="Expiry as UTC Unix seconds.")
def grant_permission(principal_id: str, resource: str, action: str, expires_at: int | None) -> None:
    """Grant or update one exact resource and action for a stable principal."""

    def change(state: PolicySnapshot) -> PolicySnapshot:
        """Replace the same principal/resource/action row to update its expiry."""

        permission = Permission(resource=resource, action=action)
        if is_admin_exclusive(permission):
            raise GatewayAccessError(403, "insufficient_authority")
        grant = ScopedGrant(principal_id=principal_id, permission=permission, expires_at=expires_at)
        remaining = tuple(
            row
            for row in state.grants
            if (row.principal_id, row.permission) != (principal_id, permission)
        )
        return state.model_copy(update={"grants": (*remaining, grant)})

    _update("grant.put", change, principal_id=principal_id, resource=resource, action=action)


@single_access_group.command(name="revoke")
@click.argument("principal_id")
@click.argument("resource")
@click.argument("action")
def revoke_permission(principal_id: str, resource: str, action: str) -> None:
    """Revoke this principal's exact direct grant."""

    def change(state: PolicySnapshot) -> PolicySnapshot:
        """Remove only the named direct grant."""

        permission = Permission(resource=resource, action=action)
        remaining = tuple(
            row
            for row in state.grants
            if (row.principal_id, row.permission) != (principal_id, permission)
        )
        if len(remaining) == len(state.grants):
            raise GatewayAccessError(404, "unknown_grant")
        return state.model_copy(update={"grants": remaining})

    _update("grant.revoke", change, principal_id=principal_id, resource=resource, action=action)


@single_access_group.command(name="role-put")
@click.argument("role_id")
@click.option("--permission", nargs=2, multiple=True, metavar="RESOURCE ACTION")
@click.option("--template", type=click.Choice(tuple(ROLE_TEMPLATE_ACTIONS)))
@click.option("--resource", help="Exact resource for a role template.")
@click.option("--action", multiple=True, help="Declared action for the plugin-actions template.")
def put_role(
    role_id: str,
    permission: tuple[tuple[str, str], ...],
    template: str | None,
    resource: str | None,
    action: tuple[str, ...],
) -> None:
    """Set a target-local role's exact permissions."""

    if template is None:
        if not permission or resource is not None or action:
            raise click.UsageError("Choose --permission or --template with --resource.")
    elif permission or resource is None or bool(action) != (template == "plugin-actions"):
        raise click.UsageError(
            "Use --template with --resource and supply --action only for plugin-actions."
        )
    with _access_errors():
        access = _owner_access()
        provenance = (
            RoleTemplate(name=template, resource=resource)
            if template is not None and resource is not None
            else None
        )
        role = RoleDefinition(
            role_id=role_id,
            permissions=(
                _template_permissions(access, provenance, action)
                if provenance is not None
                else tuple(Permission(resource=res, action=act) for res, act in permission)
            ),
            template=provenance,
        )
        if any(is_admin_exclusive(effect) for effect in role.permissions):
            raise GatewayAccessError(403, "insufficient_authority")

    def change(state: PolicySnapshot) -> PolicySnapshot:
        """Keep existing role assignments while replacing the role definition."""

        remaining = tuple(row for row in state.roles if row.role_id != role_id)
        return state.model_copy(update={"roles": (*remaining, role)})

    _update("role.put", change, selected_access=access, role_id=role_id)


def _template_permissions(
    access: GatewayRuntimeAccess, template: RoleTemplate, actions: tuple[str, ...]
) -> tuple[Permission, ...]:
    """Expand compatible effects of the selected exact resource kind."""

    effects = tuple(
        Permission(resource=template.resource, action=action)
        for action in ROLE_TEMPLATE_ACTIONS[template.name] or actions
    )
    if template.name == "plugin-actions":
        declared = _plugin_declared_permissions(access, template.resource)
        if not set(effects).issubset(declared):
            raise GatewayAccessError(422, "plugin_action_unverified")
    elif not all(_supports_inspection(effect) for effect in effects):
        raise GatewayAccessError(422, "invalid_template_resource")
    return effects


def _plugin_declared_permissions(
    access: GatewayRuntimeAccess, resource: str
) -> frozenset[Permission]:
    """Verify an exact binding and its host-declared actions on the live listener."""

    parts = resource.split(":")
    if len(parts) != 3 or parts[0] != "plugin" or not all(parts):
        raise GatewayAccessError(422, "invalid_template_resource")
    endpoint, port = _local_verified_endpoint(access)
    binding, _ = owner_gateway_client_binding(
        access.manifest_path, port=port, private=True, prefer_self=True
    )
    client = GatewayClient(
        base_url=endpoint.base_url,
        binding=binding,
        target_incarnation=access.target.incarnation,
        target_presence_id=endpoint.descriptor.presence_id,
        respect_proxy_env=False,
    )
    status = client.get_plugin_status(parts[1])
    if status.binding_id != parts[2]:
        raise GatewayAccessError(422, "plugin_binding_unverified")
    return frozenset(
        Permission(resource=resource, action=action) for action in status.declared_actions
    )


@single_access_group.command(name="role-assign")
@click.argument("principal_id")
@click.argument("role_id")
@click.option("--expires-at", type=_EXPIRES, help="Expiry as UTC Unix seconds.")
@click.option("--local", is_flag=True, help="Select a legacy local role with a built-in name.")
def assign_role(principal_id: str, role_id: str, expires_at: int | None, local: bool) -> None:
    """Assign or renew a target-local role for one principal."""

    def change(state: PolicySnapshot) -> PolicySnapshot:
        """Upsert one explicit assignment by principal and role."""

        assignment = RoleAssignment(
            principal_id=principal_id,
            role_id=role_id,
            expires_at=expires_at,
            builtin_version=1 if not local and role_id in BUILTIN_PEER_ROLES else None,
        )
        remaining = tuple(
            row
            for row in state.role_assignments
            if (row.principal_id, row.role_id, row.builtin_version)
            != (principal_id, role_id, assignment.builtin_version)
        )
        return state.model_copy(update={"role_assignments": (*remaining, assignment)})

    _update("role.assign", change, principal_id=principal_id, role_id=role_id)


@single_access_group.command(name="role-revoke")
@click.argument("principal_id")
@click.argument("role_id")
@click.option("--local", is_flag=True, help="Select a legacy local role with a built-in name.")
def revoke_role(principal_id: str, role_id: str, local: bool) -> None:
    """Revoke this principal's assignment to a target-local role."""

    def change(state: PolicySnapshot) -> PolicySnapshot:
        """Remove one exact role assignment without altering grants or credentials."""

        remaining = tuple(
            row
            for row in state.role_assignments
            if (row.principal_id, row.role_id, row.builtin_version)
            != (principal_id, role_id, 1 if not local and role_id in BUILTIN_PEER_ROLES else None)
        )
        if len(remaining) == len(state.role_assignments):
            raise GatewayAccessError(404, "unknown_assignment")
        return state.model_copy(update={"role_assignments": remaining})

    _update("role.revoke", change, principal_id=principal_id, role_id=role_id)


@single_access_group.command(name="list")
def list_policy() -> None:
    """Show public enrollment identifiers, grants, and roles for the owner."""

    with _access_errors():
        access = _owner_access()
        access.require_current()
        state = access.store.snapshot()
        emit(
            _summary(
                state,
                principals=[row.model_dump(mode="json") for row in state.principals],
                credentials=[
                    {
                        "key_id": row.key_id,
                        "principal_id": row.principal_id,
                        "admin": row.admin_revision is not None,
                    }
                    for row in state.credentials
                ],
                grants=[row.model_dump(mode="json") for row in state.grants],
                roles=[row.model_dump(mode="json") for row in state.roles],
                role_assignments=[row.model_dump(mode="json") for row in state.role_assignments],
                builtin_catalog={
                    "version": 1,
                    "assignable_roles": BUILTIN_PEER_ROLES,
                    "agent_effects": {
                        role: peer_group_effects(group)
                        for role, group in BUILTIN_PEER_ROLES.items()
                    },
                    "common_mount_effects": {
                        role: tuple(sorted(FILE_ACTIONS))
                        for role in ("builtin:agent-maintainer", "builtin:agent-operator")
                    },
                    "default_choices": PERMISSION_GROUPS,
                    "templates": ROLE_TEMPLATE_ACTIONS,
                },
            )
        )


@single_access_group.command(name="explain")
@click.argument("principal_id")
@click.argument("resource")
@click.argument("action")
@click.option("--key-id", help="Inspect a single fingerprint when a principal has several keys.")
def explain_permission(principal_id: str, resource: str, action: str, key_id: str | None) -> None:
    """Explain current policy for the selected principal's enrolled keys."""

    with _access_errors():
        access = _owner_access()
        access.require_current()
        state = access.store.snapshot()
        if not any(row.principal_id == principal_id for row in state.principals):
            raise GatewayAccessError(404, "unknown_principal")
        keys = [
            row
            for row in state.credentials
            if row.principal_id == principal_id and key_id in {None, row.key_id}
        ]
        if key_id is not None and not keys:
            raise GatewayAccessError(404, "unknown_key")
        permission = Permission(resource=resource, action=action)
        now = int(time.time())
        direct = next(
            (
                row
                for row in state.grants
                if row.principal_id == principal_id and row.permission == permission
            ),
            None,
        )
        roles = {role.role_id: role for role in state.roles if permission in role.permissions}
        matching_roles = [
            {
                "role_id": row.role_id,
                "expires_at": row.expires_at,
                "active": row.expires_at is None or row.expires_at > now,
                "builtin_version": row.builtin_version,
                "template": (
                    template.model_dump(mode="json")
                    if row.builtin_version is None
                    and (template := roles[row.role_id].template) is not None
                    else None
                ),
            }
            for row in state.role_assignments
            if row.principal_id == principal_id
            and (
                row.role_id in roles
                if row.builtin_version is None
                else group_allows(
                    BUILTIN_PEER_ROLES[row.role_id],
                    permission,
                    supports_self=lambda _: False,
                    supports_common=_supports_inspection,
                )
            )
        ]
        authorizer = GatewayAuthorizer(
            access.store,
            catalog=_INSPECTION_PERMISSIONS,
            supports=_supports_inspection,
            supports_common=_supports_inspection,
            self_permissions=_INSPECTION_PERMISSIONS,
            supports_self=_supports_inspection,
        )
        known_permission = permission in _INSPECTION_PERMISSIONS or _supports_inspection(permission)
        decisions: list[dict[str, object]] = []
        for key in keys:
            if action == "agent.prompt" and resource == "agent":
                decisions.append(
                    {"key_id": key.key_id, "allowed": False, "reason": "retired_effect"}
                )
                continue
            if not known_permission:
                decisions.append(
                    {
                        "key_id": key.key_id,
                        "allowed": None,
                        "reason": "operation_catalog_unverified",
                    }
                )
                continue
            try:
                decision = authorizer.authorize_snapshot(
                    state,
                    AuthorizationActor.from_credential(key),
                    (permission,),
                    target=access.target,
                    listener_id="owner-inspection",
                )
            except GatewayAccessError as error:
                if error.status_code not in {401, 403}:
                    raise
                decisions.append({"key_id": key.key_id, "allowed": False, "reason": error.code})
            else:
                decisions.append({"key_id": key.key_id, "allowed": True, "basis": decision.basis})
        emit(
            _summary(
                state,
                principal_id=principal_id,
                resource=resource,
                action=action,
                direct_grant=(
                    None
                    if direct is None
                    else {
                        "expires_at": direct.expires_at,
                        "active": direct.expires_at is None or direct.expires_at > now,
                    }
                ),
                matching_roles=matching_roles,
                resource_availability=(
                    "defined" if permission in _INSPECTION_PERMISSIONS else "unresolved"
                ),
                keys=decisions,
            )
        )


def _supports_inspection(permission: Permission) -> bool:
    """Recognize dynamic core operation resources without starting an agent."""

    return (
        supports_mail_permission(permission)
        or supports_ag_ui_permission(permission)
        or (
            _FILE_RESOURCE.fullmatch(permission.resource) is not None
            and permission.action in {"files.read", "files.edit", "files.push"}
        )
    )


@single_access_group.command(name="peer-signer")
@click.option("--key", type=_FILE, required=True, help="Absolute owner-private peer signing key.")
def select_peer_signer(key: Path) -> None:
    """Configure a stable signer for the selected local source agent."""

    with _access_errors():
        access = _owner_access()
        selection = str(key)
        private = load_gateway_signer(key)
        identity = _peer_public_key(access, public_key_text(private.public_key()))
        deployment = load_gateway_deployment(access.manifest_path) or GatewayDeployment()
        choices = deployment.model_dump()
        choices["peer_signer_path"] = selection
        access.require_current()
        save_gateway_deployment(access.manifest_path, GatewayDeployment.model_validate(choices))
        emit(identity)


@self_access_group.command(name="public-key")
def export_peer_key() -> None:
    """Print this logical agent's selected peer public key and fingerprint."""

    with _access_errors():
        access = _source_access(None)
        private = load_gateway_signer(_peer_signer_path(access))
        emit(_peer_public_key(access, public_key_text(private.public_key())))


def _read_public_key(path: Path) -> str:
    """Read a bounded public key file for enrollment."""

    with path.open("rb") as stream:
        raw = stream.read(4097)
    if len(raw) > 4096:
        raise ValueError("Oversized public key.")
    return raw.decode().strip()


def _peer_public_key(access: GatewayRuntimeAccess, public_key: str) -> dict[str, str]:
    """Export the logical ID and peer key without private material or paths."""

    key = Credential(principal_id=access.owner.agent_id, public_key=public_key)
    return {
        "logical_agent_id": access.owner.agent_id,
        "public_key": key.public_key,
        "key_id": key.key_id,
    }


def _peer_signer_path(access: GatewayRuntimeAccess) -> Path:
    """Resolve a configured owner-private stable signer independent of the target."""

    access.require_current()
    deployment = load_gateway_deployment(access.manifest_path)
    if deployment is None or deployment.peer_signer_path is None:
        raise click.ClickException(
            "Configure the source agent's peer signer with `access peer-signer`."
        )
    return Path(deployment.peer_signer_path)


def _source_access(source_agent_id: str | None) -> GatewayRuntimeAccess:
    """Verify current self or an explicitly selected source owner's local manifest."""

    if source_agent_id is not None:
        return resolve_owner_gateway_access(agent_id=source_agent_id, agent_name=None)
    manifest = resolve_self_manifest()
    access = gateway_access_for_manifest(manifest.path)
    if (
        access.owner.agent_id != manifest.agent_id
        or access.execution_binding != manifest.record.execution_binding
        or access.target.incarnation != manifest.record.generation_id
    ):
        raise click.ClickException("The managed source execution changed.")
    return access


@dataclass(frozen=True)
class _VerifiedEndpoint:
    """Pin the selected target and listener independently of its signer."""

    base_url: str
    ca_bundle: Path | None
    descriptor: GatewayEndpointDescriptor

    def signed_client(
        self,
        signer: Path,
        *,
        purpose: ProofPurpose = "caller",
        registration_key: GatewayAdminKey | None = None,
    ) -> GatewayClient:
        """Bind a local signer only after target identity and transport were verified."""

        return GatewayClient(
            binding=GatewayClientBinding(
                base_url=self.base_url,
                owner=self.descriptor.target.owner,
                purpose=purpose,
                private_key_path=str(signer),
                ca_bundle_path=str(self.ca_bundle) if self.ca_bundle is not None else None,
            ),
            target_incarnation=self.descriptor.target.incarnation,
            target_presence_id=self.descriptor.presence_id,
            registration_key=registration_key,
            respect_proxy_env=False,
        )

    def observe(self) -> GatewayEndpointDescriptor:
        """Read endpoint metadata and match the same exact live listener."""

        return _probe_endpoint(
            self.base_url,
            self.ca_bundle,
            self.descriptor.target,
            self.descriptor.presence_id,
        )


def _probe_endpoint(
    base_url: str, ca_bundle_path: Path | None, target: GatewayTarget, presence_id: str
) -> GatewayEndpointDescriptor:
    """Verify TLS or local transport and the expected target before binding a signer."""

    descriptor = GatewayClient(
        base_url=base_url, ca_bundle_path=ca_bundle_path, respect_proxy_env=False
    ).describe_endpoint()
    if (
        descriptor.target != target
        or descriptor.presence_id != presence_id
        or descriptor.protocol != GATEWAY_PROTOCOL_VERSION
        or descriptor.proof_protocol != "sshsig-v2"
    ):
        raise click.ClickException(_ENDPOINT_REFUSED)
    return descriptor


def _verified_endpoint(
    url: str | None,
    context_id: str | None,
    generation: str | None,
    presence: str | None,
    ca_bundle: Path | None,
) -> _VerifiedEndpoint:
    """Read a verified owner-local listener or match explicit remote coordinates."""

    scope = _selected()
    if url is None:
        if any(value is not None for value in (context_id, generation, presence, ca_bundle)):
            raise click.UsageError("Explicit gateway coordinates require --url.")
        endpoint, _ = _local_verified_endpoint(_owner_access())
        return endpoint
    if not (scope.agent_id and context_id and generation and presence):
        raise click.UsageError(
            "With --url, select --agent-id, --context-id, --generation, and --presence."
        )
    expected = GatewayTarget(
        owner=GatewayOwner(agent_id=scope.agent_id, context_id=context_id),
        incarnation=generation,
    )
    descriptor = _probe_endpoint(url, ca_bundle, expected, presence)
    return _VerifiedEndpoint(url, ca_bundle, descriptor)


def _local_verified_endpoint(access: GatewayRuntimeAccess) -> tuple[_VerifiedEndpoint, int]:
    """Match a local listener to the already-verified owner manifest."""

    paths = gateway_paths_from_manifest_path(access.manifest_path)
    if paths is None:
        raise click.ClickException("No gateway is attached to the selected target.")
    instance = load_gateway_current_instance(paths.current_instance_path)
    retained = instance.endpoint_descriptor
    if retained is None or retained.target != access.target:
        raise click.ClickException(_ENDPOINT_REFUSED)
    base_url = owner_gateway_base_url(instance.port)
    access.require_current()
    descriptor = _probe_endpoint(base_url, None, access.target, retained.presence_id)
    return _VerifiedEndpoint(base_url, None, descriptor), instance.port


def _endpoint_options(command: Callable[..., None]) -> Callable[..., None]:
    """Expose explicit remote coordinates and independent certificate trust."""

    options = (
        click.option("--url", help="Trusted gateway base URL. Omit for the verified local target."),
        click.option("--context-id", help="Expected remote execution context ID."),
        click.option("--generation", help="Expected remote runtime incarnation."),
        click.option("--presence", help="Expected remote listener presence ID."),
        click.option(
            "--ca-bundle", type=_FILE, help="Independently provisioned remote TLS CA bundle."
        ),
    )
    for option in reversed(options):
        command = option(command)
    return command


def _retained_actor(
    access: GatewayRuntimeAccess,
    *,
    method: str,
    path: str,
    body: bytes,
    signer: Path | PrivateKey | None,
) -> tuple[GatewayAccessPolicy, AuthorizationActor]:
    """Bind local retained admission to the same request and proof as HTTP ingress."""

    def target() -> GatewayTarget:
        """Recheck the owner manifest before using the retained policy."""

        access.require_current()
        return access.target

    policy = GatewayAccessPolicy(
        store=access.store,
        target=target,
        current_self=access.current_self,
        listener_id="owner-retained",
    )
    if signer is None:
        return policy, AuthorizationActor(kind="anonymous")
    private_key = load_gateway_signer(signer) if isinstance(signer, Path) else signer
    request = GatewayRequestBinding.from_request(method, path, "", body)
    challenge = policy.issue(
        "owner-retained",
        GatewayChallengeRequest(
            purpose="caller",
            request=request,
            key_id=key_fingerprint(public_key_text(private_key.public_key())),
        ),
    )
    return policy, policy.authenticate(
        issuer="owner-retained",
        request=request,
        challenge_id=challenge.challenge_id,
        signature=sshsig_header(sign_sshsig(private_key, challenge.signing_bytes())),
    )


@single_access_group.group(name="default-group")
def default_group() -> None:
    """Manage the selected agent's retained default caller permissions."""


@default_group.command(name="set")
@click.argument("group", type=click.Choice(PERMISSION_GROUPS))
@_endpoint_options
@click.option("--retained", is_flag=True, help="Use the selected local policy directly.")
@click.option("--passive-url", help="Use the direct route at this trusted passive listener.")
@click.option("--signer", type=_FILE, help="Explicit private key for an authenticated call.")
def set_default_group(
    group: PermissionGroupName,
    url: str | None,
    context_id: str | None,
    generation: str | None,
    presence: str | None,
    ca_bundle: Path | None,
    retained: bool,
    passive_url: str | None,
    signer: Path | None,
) -> None:
    """Set one of the six built-in groups through a single chosen path."""

    if sum((url is not None, retained, passive_url is not None)) > 1:
        raise click.UsageError("Choose one of --url, --passive-url, or --retained.")
    payload = DefaultPermissionGroupRequest(group=group)
    with _access_errors():
        if retained:
            if any(value is not None for value in (context_id, generation, presence, ca_bundle)):
                raise click.UsageError("Retained access uses the verified local owner coordinates.")
            access = _owner_access()
            policy, actor = _retained_actor(
                access,
                method="PUT",
                path="/v1/admin/default-permission-group",
                body=payload.model_dump_json().encode(),
                signer=signer,
            )
            receipt = policy.set_default_permission_group(
                policy.authorize(actor, (DEFAULT_GROUP_SET,)), group
            )
        elif passive_url is not None:
            if any(value is not None for value in (context_id, generation, presence)):
                raise click.UsageError(
                    "The passive path uses the verified local owner coordinates."
                )
            access = _owner_access()
            passive_url = validate_gateway_base_url(passive_url)
            binding = (
                GatewayClientBinding(
                    base_url=passive_url,
                    owner=access.owner,
                    purpose="caller",
                    private_key_path=str(signer),
                    ca_bundle_path=str(ca_bundle) if ca_bundle is not None else None,
                )
                if signer is not None
                else None
            )
            if ca_bundle is not None and binding is None:
                raise click.UsageError("A custom passive CA bundle requires --signer.")
            client_passive = PassiveServerClient(
                passive_url, binding=binding, target_incarnation=access.target.incarnation
            )
            selected = client_passive.describe_agent_proof(access.owner.agent_id)
            if selected.target != access.target:
                raise click.ClickException(_ENDPOINT_REFUSED)
            receipt = client_passive.set_default_permission_group(
                access.owner.agent_id,
                DefaultPermissionGroupRequest(
                    group=group,
                    expected_target=selected.target,
                    expected_listener_id=selected.presence_id,
                ),
            )
        else:
            endpoint = _verified_endpoint(url, context_id, generation, presence, ca_bundle)
            client = (
                endpoint.signed_client(signer)
                if signer is not None
                else GatewayClient(
                    base_url=endpoint.base_url,
                    ca_bundle_path=endpoint.ca_bundle,
                    respect_proxy_env=False,
                )
            )
            receipt = client.set_default_permission_group(
                DefaultPermissionGroupRequest(
                    group=group,
                    expected_target=endpoint.descriptor.target,
                    expected_listener_id=endpoint.descriptor.presence_id,
                )
            )
        if receipt.default_permission_group != group:
            raise click.ClickException("The selected path returned a different retained group.")
        emit(receipt.model_dump(mode="json"))


def _self_revision(access: GatewayRuntimeAccess) -> int:
    """Resolve the last committed revision for the selected managed generation."""

    access.require_live_generation()
    revision = access.store.self_revision(access.target.incarnation)
    if revision is None:
        raise GatewayAccessError(503, "self_authorization_unavailable")
    return revision


@single_access_group.command(name="self-key")
@_endpoint_options
@click.argument("operation", type=click.Choice(("rotate", "revoke")))
@click.option("--signer", type=_FILE, help="Use this private key to prove effective admin.")
@click.option("--expected-revision", type=click.IntRange(min=1))
@click.option("--retained", is_flag=True, help="Use verified local authority without a listener.")
def change_managed_self(
    url: str | None,
    context_id: str | None,
    generation: str | None,
    presence: str | None,
    ca_bundle: Path | None,
    operation: Literal["rotate", "revoke"],
    signer: Path | None,
    expected_revision: int | None,
    retained: bool,
) -> None:
    """Rotate or revoke the current managed-self key using effective admin authority."""

    with _access_errors():
        if retained and any(
            value is not None for value in (url, context_id, generation, presence, ca_bundle)
        ):
            raise click.UsageError("Use --retained with a verified local target.")
        if expected_revision is None and url is not None:
            raise click.UsageError("Use --expected-revision for a remote target.")
        if retained:
            access = _owner_access()
            change = ManagedSelfChange(
                operation=operation,
                generation_id=access.target.incarnation,
                expected_revision=expected_revision or _self_revision(access),
            )
            policy, actor = _retained_actor(
                access,
                method="PUT",
                path=MANAGED_SELF_PATH,
                body=change.model_dump_json().encode(),
                signer=signer,
            )
            result = policy.change_self_registration(
                actor, change, require_live_target=access.require_live_generation
            )
        else:
            endpoint = _verified_endpoint(url, context_id, generation, presence, ca_bundle)
            target = endpoint.descriptor.target
            if expected_revision is None:
                access = _owner_access()
                if access.target != target:
                    raise click.ClickException(_ENDPOINT_REFUSED)
                expected_revision = _self_revision(access)
            change = ManagedSelfChange(
                operation=operation,
                generation_id=target.incarnation,
                expected_revision=expected_revision,
            )
            client = (
                endpoint.signed_client(signer)
                if signer is not None
                else GatewayClient(
                    base_url=endpoint.base_url,
                    ca_bundle_path=endpoint.ca_bundle,
                    respect_proxy_env=False,
                )
            )
            result = client.change_managed_self(change)
        emit(result.model_dump(mode="json"))


@self_access_group.command(name="self-key")
@click.argument("operation", type=click.Choice(("rotate", "revoke")))
@click.option("--retained", is_flag=True, help="Use the current signer without a listener.")
def change_own_managed_self(operation: Literal["rotate", "revoke"], retained: bool) -> None:
    """Rotate or revoke this runtime's current managed-self key with its own proof."""

    with _access_errors():
        access = _source_access(None)
        change = ManagedSelfChange(
            operation=operation,
            generation_id=access.target.incarnation,
            expected_revision=_self_revision(access),
        )
        if retained:
            _, signer = access.load_self_signer()
            policy, actor = _retained_actor(
                access,
                method="PUT",
                path=MANAGED_SELF_PATH,
                body=change.model_dump_json().encode(),
                signer=signer,
            )
            result = policy.change_self_registration(
                actor, change, require_live_target=access.require_live_generation
            )
            emit(result.model_dump(mode="json"))
            return
        paths = gateway_paths_from_manifest_path(access.manifest_path)
        if paths is None:
            raise click.ClickException("No gateway is attached to this runtime.")
        instance = load_gateway_current_instance(paths.current_instance_path)
        descriptor = instance.endpoint_descriptor
        if descriptor is None or descriptor.target != access.target:
            raise click.ClickException(_ENDPOINT_REFUSED)
        binding, incarnation = owner_gateway_client_binding(
            access.manifest_path, port=instance.port, private=True, prefer_self=True
        )
        assert binding is not None
        result = GatewayClient(
            binding=binding,
            target_incarnation=incarnation,
            target_presence_id=descriptor.presence_id,
            respect_proxy_env=False,
        ).change_managed_self(change)
        emit(result.model_dump(mode="json"))


@single_access_group.command(name="admin-add")
@_endpoint_options
@click.option("--first", is_flag=True, help="Prove this proposed key and claim the empty roster.")
@click.option("--signer", type=_FILE, required=True, help="Absolute private signing key.")
@click.option("--public-key", "key_file", type=_FILE, required=True)
@click.option("--principal", required=True, help="Display label for a new operator principal.")
def add_admin(
    url: str | None,
    context_id: str | None,
    generation: str | None,
    presence: str | None,
    ca_bundle: Path | None,
    first: bool,
    signer: Path,
    key_file: Path,
    principal: str,
) -> None:
    """Enroll the first admin key or qualify a key using current signed admin authority."""

    with _access_errors():
        endpoint = _verified_endpoint(url, context_id, generation, presence, ca_bundle)
        key = GatewayAdminKey(principal=principal, public_key=_read_public_key(key_file))
        expected = "open" if first else "keyed"
        if endpoint.descriptor.admin_mode != expected:
            raise click.ClickException(
                f"Admin enrollment requires a verified {expected} roster for this command."
            )
        client = endpoint.signed_client(
            signer,
            purpose="register" if first else "caller",
            registration_key=key if first else None,
        )
        try:
            key_id = client.add_admin_key(key)
        except GatewayHttpError as error:
            if first and error.status_code == 409:
                raise click.ClickException(
                    "First-key enrollment conflicted with a current admin roster change."
                ) from None
            raise
        emit({"key_id": key_id, "admin_mode": "keyed"})


@single_access_group.command(name="admin-remove")
@_endpoint_options
@click.argument("key_id")
@click.option("--signer", type=_FILE, required=True, help="Absolute current admin private key.")
def remove_admin(
    url: str | None,
    context_id: str | None,
    generation: str | None,
    presence: str | None,
    ca_bundle: Path | None,
    key_id: str,
    signer: Path,
) -> None:
    """Remove one admin qualification with current signed admin authority."""

    with _access_errors():
        endpoint = _verified_endpoint(url, context_id, generation, presence, ca_bundle)
        if endpoint.descriptor.admin_mode != "keyed":
            raise click.ClickException("Admin removal requires a verified keyed roster.")
        endpoint.signed_client(signer).remove_admin_key(key_id)
        mode: str
        try:
            mode = endpoint.observe().admin_mode
        except (click.ClickException, GatewayHttpError, ValueError):
            mode = "unknown"
        emit({"key_id": key_id, "admin_mode": mode, "removed": True})


@single_access_group.command(name="request")
@_endpoint_options
@click.argument("method", type=click.Choice(("GET", "POST", "PUT", "PATCH", "DELETE")))
@click.argument("path")
@click.option("--body", type=click.File("r"), help="Read a JSON object from a file or - for stdin.")
@click.option(
    "--source-agent-id", help="Choose a verified local source agent, including a stopped source."
)
def signed_peer_request(
    url: str | None,
    context_id: str | None,
    generation: str | None,
    presence: str | None,
    ca_bundle: Path | None,
    method: str,
    path: str,
    body: click.utils.LazyFile | None,
    source_agent_id: str | None,
) -> None:
    """Call a supported gateway JSON operation using the source's enrolled peer key."""

    with _access_errors():
        endpoint = _verified_endpoint(url, context_id, generation, presence, ca_bundle)
        source = _source_access(source_agent_id)
        signer = _peer_signer_path(source)
        payload = json.load(body) if body is not None else None
        if body is not None and not isinstance(payload, dict):
            raise click.UsageError("--body must contain a JSON object.")
        emit(endpoint.signed_client(signer).request_json(method, path, body=payload))
