"""Shared endpoint-bound HTTP client for independent gateway integrations."""

from __future__ import annotations

from pathlib import Path

from houmao.agents.realm_controller.errors import GatewayHttpError as GatewayHttpError
from houmao.agents.realm_controller.gateway_client import GatewayClient as GatewayClient
from houmao.gateway.access import (
    GatewayClientBinding,
    parse_access_document,
    read_private_access_file,
)


def load_gateway_client_binding(path: Path) -> GatewayClientBinding:
    """Load one explicit private client binding from approved private storage."""

    try:
        return parse_access_document(GatewayClientBinding, read_private_access_file(path))
    except (OSError, ValueError):
        raise ValueError("Gateway client binding is unavailable or invalid.") from None


def managed_self_gateway_client(*, base_url: str, timeout_seconds: float = 5.0) -> GatewayClient:
    """Select the current managed generation's signer for its exact owner endpoint."""

    from houmao.agents.instance_state import resolve_verified_self
    from houmao.agents.realm_controller.gateway_access_runtime import owner_gateway_client_binding
    from houmao.agents.realm_controller.gateway_storage import (
        gateway_paths_from_manifest_path,
        load_gateway_current_instance,
    )
    from houmao.gateway.deployment import owner_gateway_base_url

    try:
        identity = resolve_verified_self()
        paths = gateway_paths_from_manifest_path(identity.manifest_path)
        if paths is None:
            raise ValueError("Missing gateway capability.")
        current = load_gateway_current_instance(paths.current_instance_path)
        if owner_gateway_base_url(current.port) != base_url:
            raise ValueError("Gateway does not match the current managed self endpoint.")
        binding, generation = owner_gateway_client_binding(
            identity.manifest_path, port=current.port, private=True, prefer_self=True
        )
        if binding is None or generation != identity.generation_id:
            raise ValueError("Managed self generation has changed.")
    except (ValueError, OSError, RuntimeError):
        raise ValueError("Current managed self gateway authority is unavailable.") from None
    return GatewayClient(
        base_url=base_url,
        binding=binding,
        target_incarnation=generation,
        timeout_seconds=timeout_seconds,
    )
