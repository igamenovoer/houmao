"""Operation-local execution authority for runtime construction and control."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
import json
import os
from pathlib import Path
import pwd
from typing import TYPE_CHECKING, get_args

from houmao.execution.models import (
    ControllerScopeV1,
    ExecutionBindingV1,
    ExecutionOperation,
    ExecutionProfileV1,
)
from houmao.execution.tmux import tmux_server_scope

if TYPE_CHECKING:
    from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4

_BINDING: ContextVar[ExecutionBindingV1 | None] = ContextVar(
    "houmao_execution_binding", default=None
)


def current_execution_binding() -> ExecutionBindingV1 | None:
    """Return the owner binding admitted for this operation, if present."""

    return _BINDING.get()


_READ_ONLY: ContextVar[bool] = ContextVar("houmao_execution_read_only", default=False)


def execution_is_read_only() -> bool:
    """Return whether this operation may only reconstruct and observe authority."""

    return _READ_ONLY.get()


@contextmanager
def execution_read_only_scope(read_only: bool = True) -> Iterator[None]:
    """Suppress implicit preparation without weakening an enclosing read-only request."""

    token = _READ_ONLY.set(execution_is_read_only() or read_only)
    try:
        yield
    finally:
        _READ_ONLY.reset(token)


def validate_execution_owner(binding: ExecutionBindingV1 | None) -> None:
    """Require persisted runtime authority to agree with this admitted OS owner."""

    admitted = current_execution_binding()
    if admitted is not None and binding != admitted:
        raise ValueError("Saved runtime execution binding differs from admitted owner")
    if binding is not None and (binding.uid != os.geteuid() or binding.gid != os.getegid()):
        raise ValueError("Saved runtime execution owner UID/GID differs from caller")
    if binding is not None and admitted is None:
        from houmao.execution.owner import validate_observed_binding

        validate_observed_binding(binding)


def require_owner_tmux_socket(binding: ExecutionBindingV1 | None, socket_path: str | None) -> str:
    """Require this execution owner and its explicit recorded socket."""

    validate_execution_owner(binding)
    if socket_path is None:
        raise ValueError("Live terminal inspection requires the recorded owner socket")
    if binding is not None and binding.tmux_socket is not None:
        if socket_path != binding.tmux_socket:
            raise ValueError("Recorded tmux socket differs from execution owner")
    return socket_path


@contextmanager
def execution_binding_scope(
    binding: ExecutionBindingV1 | None, *, inherit: bool = True
) -> Iterator[None]:
    """Restore one runtime's binding without changing another thread or caller."""

    selected = current_execution_binding() if inherit and binding is None else binding
    token = _BINDING.set(selected)
    try:
        yield
    finally:
        _BINDING.reset(token)


@contextmanager
def persisted_execution_scope(manifest_path: Path) -> Iterator[SessionManifestPayloadV4]:
    """Yield the parsed manifest while its owner and socket are selected."""

    from houmao.agents.realm_controller.manifest import (
        load_session_manifest,
        parse_session_manifest_payload,
    )

    handle = load_session_manifest(manifest_path)
    payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
    binding = payload.runtime.execution_binding
    validate_execution_owner(binding)
    socket_path = payload.tmux.socket_path if payload.tmux is not None else None
    if socket_path is None:
        raise ValueError("Persisted tmux scope requires a saved tmux socket")
    if binding is not None and binding.tmux_socket is not None:
        if socket_path != binding.tmux_socket:
            raise ValueError("Persisted tmux socket differs from execution binding")
    assert payload.tmux is not None
    with (
        execution_binding_scope(binding),
        tmux_server_scope(socket_path, allow_start=payload.tmux.server_allow_start is not False),
    ):
        yield payload


def parse_execution_binding(value: object) -> ExecutionBindingV1 | None:
    """Parse JSON-origin binding arrays using strict JSON validation semantics."""

    if value is None or isinstance(value, ExecutionBindingV1):
        return value
    if not isinstance(value, dict):
        raise ValueError("execution_binding must be a structured execution binding")
    return ExecutionBindingV1.model_validate_json(json.dumps(value))


def observed_local_binding(
    *,
    working_directory: Path,
    runtime_root: Path,
    registry_root: Path,
    tmux_socket: str | None,
) -> ExecutionBindingV1:
    """Record current-account ownership without changing its launch environment.

    The implicit policy records existing OS authority. It does not authorize a
    user switch or execute the placeholder policy/entrypoint paths.
    """

    from houmao.execution.owner import OwnerPolicyV1, observe_binding

    account = pwd.getpwuid(os.geteuid())
    root = runtime_root.resolve()
    project = str(working_directory.resolve())
    profile = ExecutionProfileV1(
        name=f"local-{os.geteuid()}",
        transport="local",
        account=account.pw_name,
        expected_uid=os.geteuid(),
        expected_gid=os.getegid(),
        entrypoint="/usr/bin/houmao-mgr",
        policy_path=str(root / "implicit-local-policy"),
        project_root=project,
    )
    policy = OwnerPolicyV1(
        profile=profile,
        controller=ControllerScopeV1(
            controller_id=f"local-{os.geteuid()}",
            authority="local_uid",
            operations=tuple(get_args(ExecutionOperation)),
            project_roots=(project,),
        ),
        uid=os.geteuid(),
        gid=os.getegid(),
        registry_root=str(registry_root.resolve()),
        runtime_root=str(root),
        tmux_socket=tmux_socket,
    )
    binding = observe_binding(policy, initialize=True)
    if binding is None:
        raise ValueError("Current-account execution context could not be initialized")
    return binding if tmux_socket is not None else binding.model_copy(update={"tmux_socket": None})
