"""Update per-key administrator qualifications without changing scoped grants."""

from __future__ import annotations

from uuid import uuid4

from houmao.gateway._access_storage import GatewayAccessError
from houmao.gateway.access_models import GatewayAdminKey
from houmao.gateway.authorization_models import Credential, PolicySnapshot, Principal


def add_admin_key(state: PolicySnapshot, key: GatewayAdminKey) -> PolicySnapshot:
    """Qualify an enrolled key or bind a new key to a new operator principal."""

    existing = state.find_credential(key.key_id)
    if existing is not None:
        if existing.admin_revision is not None:
            raise GatewayAccessError(409, "enrollment_conflict")
        return state.model_copy(
            update={
                "credentials": tuple(
                    item.model_copy(update={"admin_revision": state.revision})
                    if item.key_id == key.key_id
                    else item
                    for item in state.credentials
                ),
            }
        )
    principal = Principal(principal_id=uuid4().hex, kind="operator", label=key.principal)
    enrolled = Credential(
        principal_id=principal.principal_id,
        public_key=key.public_key,
        admin_revision=state.revision,
    )
    return state.model_copy(
        update={
            "principals": (*state.principals, principal),
            "credentials": (*state.credentials, enrolled),
        }
    )


def remove_admin_key(state: PolicySnapshot, key_id: str) -> PolicySnapshot:
    """Drop only the selected qualification and preserve the scoped credential."""

    key = state.find_credential(key_id)
    if key is None or key.admin_revision is None:
        raise GatewayAccessError(404, "unknown_key")
    return state.model_copy(
        update={
            "credentials": tuple(
                item.model_copy(update={"admin_revision": None}) if item.key_id == key_id else item
                for item in state.credentials
            ),
        }
    )
