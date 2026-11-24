"""Resolve gateway access from captured runtime and execution authority."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from houmao.agents.realm_controller.backends.tmux_runtime import TmuxCommandError, list_tmux_panes
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.agents.realm_controller.registry_storage import (
    is_live_agent_record_fresh,
    load_managed_agent_record_by_agent_id,
)
from houmao.execution.context import validate_execution_owner
from houmao.execution.models import ExecutionBindingV1
from houmao.execution.tmux import tmux_server_scope
from houmao.gateway.access import (
    GatewayAccessStore,
    GatewayClientBinding,
    GatewayLaunchSeed,
    GatewayOwner,
    GatewaySelfKey,
    GatewayTarget,
    load_gateway_signer,
    parse_access_document,
    read_private_access_file,
)
from houmao.gateway.deployment import GatewayDeployment, owner_gateway_base_url
from houmao.gateway.authorization_models import seed_snapshot
from houmao.gateway.authorization_store import AuthorizationStore
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, resolve_houmao_home_root


@dataclass(frozen=True)
class GatewayRuntimeAccess:
    """Owner-local policy and current generation selected from a runtime manifest."""

    manifest_path: Path
    execution_binding: ExecutionBindingV1
    target: GatewayTarget
    private_root: Path
    store: AuthorizationStore
    self_store: GatewayAccessStore

    @property
    def owner(self) -> GatewayOwner:
        """Return the retained policy owner independent of the generation."""

        return self.target.owner

    def require_current(self) -> None:
        """Require that the selected manifest still names the admitted generation."""

        current = gateway_access_for_manifest(self.manifest_path)
        if current.target != self.target or current.execution_binding != self.execution_binding:
            raise SessionManifestError("Gateway execution authority has changed.")

    def current_self(self) -> GatewaySelfKey | None:
        """Resolve self only for the current active registry generation."""

        self.require_current()
        record = load_managed_agent_record_by_agent_id(
            self.owner.agent_id,
            env={HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: self.execution_binding.registry_root},
        )
        if (
            record is None
            or record.lifecycle.state != "active"
            or not is_live_agent_record_fresh(record)
            or record.generation_id != self.target.incarnation
            or Path(record.runtime.manifest_path) != self.manifest_path
            or record.execution_binding != self.execution_binding
            or record.terminal.current_session_name is None
        ):
            return None
        try:
            with tmux_server_scope(record.terminal.socket_path):
                panes = list_tmux_panes(session_name=record.terminal.current_session_name)
        except TmuxCommandError:
            return None
        if not any(
            pane.window_index == "0" and pane.pane_index == "0" and not pane.pane_dead
            for pane in panes
        ):
            return None
        return self.self_store.load_self(self.target.incarnation)


def _owner_access(binding: ExecutionBindingV1, agent_id: str) -> tuple[GatewayOwner, Path]:
    """Select one external owner-private directory for a bound logical agent."""

    validate_execution_owner(binding)
    owner = GatewayOwner(agent_id=agent_id, context_id=binding.context_id)
    scope = hashlib.sha256(f"{binding.context_id}\0{agent_id}".encode()).hexdigest()
    root = resolve_houmao_home_root() / "gateway-access" / scope
    return owner, root


def gateway_access_for_manifest(manifest_path: Path) -> GatewayRuntimeAccess:
    """Resolve retained policy and target without initializing or repairing state."""

    try:
        if not manifest_path.is_absolute() or manifest_path.is_symlink():
            raise ValueError("Gateway authority requires a runtime-owned manifest.")
        handle = load_session_manifest(manifest_path)
        payload = parse_session_manifest_payload(handle.payload, source="runtime manifest")
        binding = payload.runtime.execution_binding
        if binding is None or payload.registry_generation_id is None:
            raise ValueError("Gateway access requires a bound managed generation.")
        owner, root = _owner_access(binding, payload.agent_id)
    except (SessionManifestError, OSError, ValueError, RuntimeError):
        raise SessionManifestError("Gateway execution authority is unavailable.") from None
    return GatewayRuntimeAccess(
        manifest_path=manifest_path,
        execution_binding=binding,
        target=GatewayTarget(owner=owner, incarnation=payload.registry_generation_id),
        private_root=root,
        store=AuthorizationStore(root, owner),
        self_store=GatewayAccessStore.from_root(root, owner),
    )


def provision_gateway_generation(
    *,
    binding: ExecutionBindingV1,
    agent_id: str,
    generation_id: str,
    seed: GatewayLaunchSeed | None = None,
) -> None:
    """Prepare a fresh generation, optionally initializing the first owner policy."""

    owner, root = _owner_access(binding, agent_id)
    store = AuthorizationStore(root, owner)
    if seed is None:
        store.snapshot()
    else:
        record = load_managed_agent_record_by_agent_id(
            agent_id, env={HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: binding.registry_root}
        )
        previous_binding = record.execution_binding if record is not None else None
        if previous_binding is not None and previous_binding.context_id == owner.context_id:
            store.snapshot()
        else:
            store.initialize(seed_snapshot(owner, seed))
    GatewayAccessStore.from_root(root, owner).provision_self(generation_id)


def load_gateway_access_config(path: Path) -> GatewayDeployment:
    """Read owner-selected deployment settings from a private file."""

    try:
        deployment = parse_access_document(GatewayDeployment, read_private_access_file(path))
        for signer_path in (deployment.admin_signer_path, deployment.peer_signer_path):
            if signer_path is not None:
                load_gateway_signer(Path(signer_path))
        return deployment
    except (OSError, ValueError):
        raise SessionManifestError(
            "Gateway access configuration is unavailable or invalid."
        ) from None


def load_gateway_admin_seed(path: Path) -> GatewayLaunchSeed:
    """Read an explicit launch seed before runtime or backend changes."""

    try:
        raw = read_private_access_file(path)
        seed = parse_access_document(GatewayLaunchSeed, raw)
        if json.loads(raw).get("schema_version") != 2:
            raise ValueError("An explicit current seed schema is required.")
        return seed
    except (OSError, ValueError):
        raise SessionManifestError("Gateway admin seed is unavailable or invalid.") from None


def load_gateway_deployment(manifest_path: Path) -> GatewayDeployment | None:
    """Load retained deployment settings when explicitly selected."""

    access = gateway_access_for_manifest(manifest_path)
    path = access.private_root / "deployment.json"
    try:
        return parse_access_document(GatewayDeployment, read_private_access_file(path))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        raise SessionManifestError(
            "Retained gateway deployment is unavailable or invalid."
        ) from None


def save_gateway_deployment(manifest_path: Path, deployment: GatewayDeployment) -> None:
    """Atomically retain selected deployment settings after validating owner authority."""

    access = gateway_access_for_manifest(manifest_path)
    access.store.snapshot()
    descriptor, temporary = tempfile.mkstemp(prefix=".deployment-", dir=access.private_root)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(deployment.model_dump_json().encode())
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(access.private_root / "deployment.json")
        directory = os.open(access.private_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary_path.unlink(missing_ok=True)


def owner_gateway_client_binding(
    manifest_path: Path, *, port: int, private: bool, prefer_self: bool = False
) -> tuple[GatewayClientBinding | None, str | None]:
    """Select explicit admin authority or the current self key for an owner-local call."""

    access = gateway_access_for_manifest(manifest_path)
    deployment = load_gateway_deployment(manifest_path)
    base_url = owner_gateway_base_url(port)
    generation = access.target.incarnation
    if not prefer_self and deployment is not None and deployment.admin_signer_path is not None:
        return (
            GatewayClientBinding(
                base_url=base_url,
                owner=access.owner,
                purpose="caller",
                private_key_path=deployment.admin_signer_path,
            ),
            generation,
        )
    if not private:
        return None, generation
    if access.current_self() is None:
        raise SessionManifestError("Current self signing authority is unavailable.")
    return (
        GatewayClientBinding(
            base_url=base_url,
            owner=access.owner,
            purpose="caller",
            private_key_path=str(access.self_store.self_signer_path(generation)),
        ),
        generation,
    )
