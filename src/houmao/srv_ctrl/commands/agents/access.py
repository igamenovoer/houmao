"""Owner and signed gateway access commands for selected managed agents."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import time

import click

from houmao.ag_ui.authorization import supports_ag_ui_permission
from houmao.agents.realm_controller.errors import GatewayHttpError, SessionManifestError
from houmao.agents.realm_controller.gateway_access_runtime import (
    GatewayRuntimeAccess,
    gateway_access_for_manifest,
    load_gateway_admin_seed,
    load_gateway_deployment,
    save_gateway_deployment,
)
from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.agents.realm_controller.gateway_models import GATEWAY_PROTOCOL_VERSION
from houmao.agents.realm_controller.gateway_storage import (
    gateway_paths_from_manifest_path,
    load_gateway_current_instance,
)
from houmao.agents.realm_controller.self_manifest import resolve_self_manifest
from houmao.gateway.access import (
    GatewayAccessError,
    GatewayAdminKey,
    GatewayClientBinding,
    GatewayLaunchSeed,
    GatewayOwner,
    GatewayTarget,
    load_gateway_signer,
    public_key_text,
)
from houmao.gateway.access_models import ProofPurpose
from houmao.gateway.authorization import GatewayAuthorizer
from houmao.gateway.authorization_models import (
    AuthorizationActor,
    Credential,
    Permission,
    PolicySnapshot,
    Principal,
    RoleAssignment,
    RoleDefinition,
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
from houmao.srv_ctrl.commands.common import (
    ManagedAgentScopeContext,
    get_managed_agent_scope_context,
)
from houmao.srv_ctrl.commands.managed_agents import resolve_owner_gateway_access
from houmao.srv_ctrl.commands.output import emit

_FILE = click.Path(exists=True, dir_okay=False, path_type=Path)
_EXPIRES = click.IntRange(min=0)
_ENDPOINT_REFUSED = "Could not verify the selected gateway target and listener."
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
    except GatewayHttpError as error:
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
        **fields,
    }


def _update(
    audit_action: str, transform: Callable[[PolicySnapshot], PolicySnapshot], **fields: object
) -> None:
    """Apply a local owner mutation under the current target and policy fence."""

    with _access_errors():
        access = _owner_access()

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
        state = access.store.initialize(seed_snapshot(access.owner, launch_seed), allow_retired=True)
        access.require_current()
        access.self_store.provision_self(access.target.incarnation)
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
@click.option("--permission", nargs=2, multiple=True, required=True, metavar="RESOURCE ACTION")
def put_role(role_id: str, permission: tuple[tuple[str, str], ...]) -> None:
    """Set a target-local role's exact permissions."""

    def change(state: PolicySnapshot) -> PolicySnapshot:
        """Keep existing role assignments while replacing the role definition."""

        role = RoleDefinition(
            role_id=role_id,
            permissions=tuple(
                Permission(resource=resource, action=action) for resource, action in permission
            ),
        )
        remaining = tuple(row for row in state.roles if row.role_id != role_id)
        return state.model_copy(update={"roles": (*remaining, role)})

    _update("role.put", change, role_id=role_id)


@single_access_group.command(name="role-assign")
@click.argument("principal_id")
@click.argument("role_id")
@click.option("--expires-at", type=_EXPIRES, help="Expiry as UTC Unix seconds.")
def assign_role(principal_id: str, role_id: str, expires_at: int | None) -> None:
    """Assign or renew a target-local role for one principal."""

    def change(state: PolicySnapshot) -> PolicySnapshot:
        """Upsert one explicit assignment by principal and role."""

        assignment = RoleAssignment(
            principal_id=principal_id, role_id=role_id, expires_at=expires_at
        )
        remaining = tuple(
            row
            for row in state.role_assignments
            if (row.principal_id, row.role_id) != (principal_id, role_id)
        )
        return state.model_copy(update={"role_assignments": (*remaining, assignment)})

    _update("role.assign", change, principal_id=principal_id, role_id=role_id)


@single_access_group.command(name="role-revoke")
@click.argument("principal_id")
@click.argument("role_id")
def revoke_role(principal_id: str, role_id: str) -> None:
    """Revoke this principal's assignment to a target-local role."""

    def change(state: PolicySnapshot) -> PolicySnapshot:
        """Remove one exact role assignment without altering grants or credentials."""

        remaining = tuple(
            row
            for row in state.role_assignments
            if (row.principal_id, row.role_id) != (principal_id, role_id)
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
        roles = {role.role_id for role in state.roles if permission in role.permissions}
        matching_roles = [
            {
                "role_id": row.role_id,
                "expires_at": row.expires_at,
                "active": row.expires_at is None or row.expires_at > now,
            }
            for row in state.role_assignments
            if row.principal_id == principal_id and row.role_id in roles
        ]
        authorizer = GatewayAuthorizer(
            access.store, catalog=_INSPECTION_PERMISSIONS, supports=_supports_inspection
        )
        known_permission = permission in _INSPECTION_PERMISSIONS or _supports_inspection(permission)
        decisions: list[dict[str, object]] = []
        for key in keys:
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
                keys=decisions,
            )
        )


def _supports_inspection(permission: Permission) -> bool:
    """Recognize dynamic core operation resources without starting an agent."""

    return supports_mail_permission(permission) or supports_ag_ui_permission(permission)


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
        access = _owner_access()
        paths = gateway_paths_from_manifest_path(access.manifest_path)
        if paths is None:
            raise click.ClickException("No gateway is attached to the selected target.")
        instance = load_gateway_current_instance(paths.current_instance_path)
        retained = instance.endpoint_descriptor
        if retained is None or retained.target != access.target:
            raise click.ClickException(_ENDPOINT_REFUSED)
        base_url = owner_gateway_base_url(instance.port)
        expected = access.target
        presence = retained.presence_id
        access.require_current()
    else:
        if not (scope.agent_id and context_id and generation and presence):
            raise click.UsageError(
                "With --url, select --agent-id, --context-id, --generation, and --presence."
            )
        base_url = url
        expected = GatewayTarget(
            owner=GatewayOwner(agent_id=scope.agent_id, context_id=context_id),
            incarnation=generation,
        )
    descriptor = _probe_endpoint(base_url, ca_bundle, expected, presence)
    return _VerifiedEndpoint(base_url, ca_bundle, descriptor)


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
