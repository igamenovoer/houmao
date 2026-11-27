"""Owner-side admission and bounded dispatch for configured execution contexts.

The fixed stdio helper uses administrator-provisioned policy and the effective
OS identity. Request labels never grant authority. Context identity is created
only by an admitted mutation; read-only discovery never initializes state.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager, nullcontext, redirect_stdout
import hashlib
import json
import os
from pathlib import Path
import pwd
import socket
import stat
import sys
import tempfile
from time import monotonic
from typing import BinaryIO, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
import yaml

from houmao.execution.models import (
    ControllerScopeV1,
    ExecutionBindingV1,
    ExecutionProfileV1,
    ExecutionRequestV1,
    ExecutionResponseV1,
    JsonObject,
    route_fingerprint,
    validate_absolute_path,
)
from houmao.execution.arguments import (
    LaunchArguments,
    OwnerAdmissionError as OwnerAdmissionError,
    OwnerOperation,
    validate_owner_operation,
)
from houmao.execution.context import execution_binding_scope, execution_deadline_scope
from houmao.execution.protocol import (
    MAX_REQUEST_BYTES,
    ExecutionProtocolError,
    decode_request,
    encode_response,
)
from houmao.execution.tmux import tmux_server_scope

MAX_OWNER_POLICY_BYTES = 65_536


class OwnerPolicyV1(BaseModel):
    """Describe trusted target-side owner, controller, roots, and launch environment."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    schema_version: Literal[1] = 1
    profile: ExecutionProfileV1
    controller: ControllerScopeV1
    uid: int = Field(ge=0)
    gid: int = Field(ge=0)
    registry_root: str
    runtime_root: str
    tmux_socket: str | None = None

    _roots = field_validator("registry_root", "runtime_root")(validate_absolute_path)

    @field_validator("tmux_socket")
    @classmethod
    def _optional_socket(cls, value: str | None) -> str | None:
        """Keep socket selection target-local and explicit."""

        return validate_absolute_path(value) if value is not None else None

    @model_validator(mode="after")
    def _consistent_authority(self) -> OwnerPolicyV1:
        """Reject contradictory expected identities and transport/controller authority."""

        authorities = {
            "local": "local_uid",
            "sudo": "sudo_policy",
            "ssh": "ssh_account",
            "docker": "container_exec",
        }
        if self.controller.authority != authorities[self.profile.transport]:
            raise ValueError("controller authority differs from configured transport")
        if self.profile.expected_uid is not None and self.uid != self.profile.expected_uid:
            raise ValueError("policy UID differs from the configured expected UID")
        if self.profile.expected_gid is not None and self.gid != self.profile.expected_gid:
            raise ValueError("policy GID differs from the configured expected GID")
        return self

    @property
    def context_file(self) -> Path:
        """Return the owner-local context identity file without creating it."""

        return Path(self.runtime_root) / "execution-context.json"

    @property
    def socket_path(self) -> str:
        """Return the configured or owner-private delegated tmux socket."""

        return self.tmux_socket or str(Path(self.runtime_root) / "execution" / "tmux.sock")


class _OwnerContextV1(BaseModel):
    """Persist one atomically published owner-context identity."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    schema_version: Literal[1] = 1
    context_id: str
    uid: int = Field(ge=0)
    gid: int = Field(ge=0)
    host_id: str
    registry_root: str
    runtime_root: str
    config_root: str | None = None

    _roots = field_validator("registry_root", "runtime_root")(validate_absolute_path)

    @field_validator("config_root")
    @classmethod
    def _config_path(cls, value: str | None) -> str | None:
        """Keep the captured owner configuration root lexical and absolute."""

        return validate_absolute_path(value) if value is not None else None

    @field_validator("context_id")
    @classmethod
    def _uuid(cls, value: str) -> str:
        """Prevent uninitialized or caller-selected labels from becoming context IDs."""

        if str(UUID(value)) != value:
            raise ValueError("context ID must be a canonical UUID")
        return value


OwnerDispatcher = Callable[[OwnerOperation, ExecutionBindingV1, OwnerPolicyV1], JsonObject]


def load_owner_policy(path: Path) -> OwnerPolicyV1:
    """Read a bounded, non-symlink, root/owner-controlled admission policy.

    Parameters
    ----------
    path : Path
        Explicit policy path fixed by the installed helper or native OS policy.

    Returns
    -------
    OwnerPolicyV1
        Validated target-side policy; request data does not select its contents.
    """

    try:
        data = _read_trusted_file(path, limit=MAX_OWNER_POLICY_BYTES)
        document: object = yaml.safe_load(data)
        if not isinstance(document, dict):
            raise ValueError("policy must be an object")
        return OwnerPolicyV1.model_validate_json(json.dumps(document, allow_nan=False))
    except (OSError, ValueError, TypeError, yaml.YAMLError, ValidationError):
        raise OwnerAdmissionError(
            "invalid_owner_policy", "Owner policy is unavailable, untrusted, or incompatible."
        ) from None


def observe_binding(
    policy: OwnerPolicyV1, *, initialize: bool = False
) -> ExecutionBindingV1 | None:
    """Observe the effective owner and existing context, initializing only when requested.

    Parameters
    ----------
    policy : OwnerPolicyV1
        Previously loaded trusted admission policy.
    initialize : bool
        Allow atomic context initialization for an admitted mutating operation.

    Returns
    -------
    ExecutionBindingV1 or None
        Observed binding, or None when read-only discovery finds no context yet.
    """

    _validate_identity(policy)
    host_id = _host_identity()
    context = _read_context(policy.context_file)
    if context is None and initialize:
        context = _initialize_context(policy, host_id)
    if context is None:
        return None
    if (
        context.uid,
        context.gid,
        context.host_id,
        context.registry_root,
        context.runtime_root,
    ) != (policy.uid, policy.gid, host_id, policy.registry_root, policy.runtime_root):
        raise OwnerAdmissionError("context_mismatch", "Owner context identity has changed.")
    account = pwd.getpwuid(os.geteuid())
    return ExecutionBindingV1(
        context_id=context.context_id,
        host_id=host_id,
        account=account.pw_name,
        uid=os.geteuid(),
        gid=os.getegid(),
        groups=tuple(sorted(set(os.getgroups()))),
        registry_root=policy.registry_root,
        runtime_root=policy.runtime_root,
        project_root=policy.profile.project_root,
        profile_name=policy.profile.name,
        transport=policy.profile.transport,
        controller=policy.controller,
        route_fingerprint=route_fingerprint(policy.profile),
        container_id=policy.profile.container_id,
        tmux_socket=policy.socket_path,
    )


def validate_observed_binding(binding: ExecutionBindingV1) -> None:
    """Validate saved runtime authority against this owner without repairing state.

    Parameters
    ----------
    binding : ExecutionBindingV1
        Persisted owner-local runtime binding, already selected by its control route.

    Raises
    ------
    OwnerAdmissionError
        Effective ownership, context, host, roots, or groups differ from the binding.
    """

    _bound_owner_context(binding)


def retained_owner_config_root(binding: ExecutionBindingV1, *, initialize: bool = False) -> Path:
    """Resolve a captured owner config root independent of the current environment."""

    from houmao.owned_paths import resolve_houmao_home_root

    context = _bound_owner_context(binding)
    if context.config_root is not None:
        return Path(context.config_root)
    # Older contexts retain their original identity. Capture their selected config
    # root before provisioning the first SQLite-backed generation.
    path = Path(context.runtime_root) / f".gateway-config-{context.context_id}"
    try:
        return Path(validate_absolute_path(_read_trusted_file(path, limit=4096).decode()))
    except FileNotFoundError:
        root = resolve_houmao_home_root()
        if not initialize:
            return root
    descriptor, temporary = tempfile.mkstemp(prefix=".gateway-config-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(os.fsencode(root))
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError:
            return Path(validate_absolute_path(_read_trusted_file(path, limit=4096).decode()))
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return root
    finally:
        os.unlink(temporary)


def _bound_owner_context(binding: ExecutionBindingV1) -> _OwnerContextV1:
    """Read the trusted saved context for this verified Linux owner."""

    if (binding.uid, binding.gid) != (os.geteuid(), os.getegid()):
        raise OwnerAdmissionError(
            "owner_mismatch", "Saved execution owner UID/GID differs from caller."
        )
    try:
        account = pwd.getpwuid(os.geteuid())
    except KeyError:
        raise OwnerAdmissionError(
            "owner_unavailable", "Effective owner has no account record."
        ) from None
    if binding.account != account.pw_name or binding.groups != tuple(sorted(set(os.getgroups()))):
        raise OwnerAdmissionError(
            "owner_mismatch", "Saved execution account or groups differ from caller."
        )
    context = _read_context(Path(binding.runtime_root) / "execution-context.json")
    if context is None:
        raise OwnerAdmissionError(
            "context_uninitialized", "Saved execution context is unavailable."
        )
    if (
        context.context_id,
        context.uid,
        context.gid,
        context.host_id,
        context.registry_root,
        context.runtime_root,
    ) != (
        binding.context_id,
        binding.uid,
        binding.gid,
        binding.host_id,
        binding.registry_root,
        binding.runtime_root,
    ) or binding.host_id != _host_identity():
        raise OwnerAdmissionError(
            "context_mismatch", "Saved execution context differs from observed authority."
        )
    return context


def handle_request(
    request: ExecutionRequestV1,
    policy: OwnerPolicyV1,
    dispatch: OwnerDispatcher,
    *,
    started_at: float | None = None,
) -> ExecutionResponseV1:
    """Admit one finite request and retain uncertainty after dispatch begins."""

    deadline = (monotonic() if started_at is None else started_at) + request.deadline_seconds
    binding: ExecutionBindingV1 | None = None
    admitted = False
    try:
        _validate_identity(policy)
        if request.expected_route_fingerprint not in {None, route_fingerprint(policy.profile)}:
            raise OwnerAdmissionError(
                "context_mismatch", "Configured execution route differs from owner policy."
            )
        if request.operation not in policy.controller.operations:
            raise OwnerAdmissionError(
                "operation_denied", "Owner policy does not allow this operation."
            )
        with owner_environment(policy):
            operation = prepare_owner_operation(request, policy)
        binding = observe_binding(
            policy,
            initialize=not operation.read_only and request.expected_binding is None,
        )
        if request.expected_binding is not None and binding != request.expected_binding:
            raise OwnerAdmissionError(
                "context_mismatch", "Recorded execution binding does not match the owner."
            )
        if binding is None:
            if request.operation != "describe" or request.agent_id is not None:
                raise OwnerAdmissionError(
                    "context_uninitialized", "Owner execution context has not been initialized."
                )
            return ExecutionResponseV1(
                request_id=request.request_id,
                outcome="completed",
                admitted=True,
                result={"initialized": False, "uid": policy.uid, "gid": policy.gid},
                capabilities=policy.controller.operations,
            )
        admitted = True
        with (
            owner_environment(policy),
            execution_binding_scope(binding),
            tmux_server_scope(binding.tmux_socket),
            execution_deadline_scope(deadline) if request.operation == "prompt" else nullcontext(),
        ):
            # Protocol stdout must contain only the response, even if an existing
            # application helper writes a diagnostic during execution.
            with redirect_stdout(sys.stderr):
                result = dispatch(operation, binding, policy)
        return ExecutionResponseV1(
            request_id=request.request_id,
            outcome="completed",
            admitted=True,
            binding=binding,
            result=result,
            capabilities=policy.controller.operations,
        )
    except OwnerAdmissionError as exc:
        return ExecutionResponseV1(
            request_id=request.request_id,
            outcome="rejected",
            admitted=False,
            binding=binding,
            error_code=exc.code,
            error_message=str(exc),
            capabilities=policy.controller.operations,
        )
    except Exception:
        return ExecutionResponseV1(
            request_id=request.request_id,
            outcome="indeterminate" if admitted else "rejected",
            admitted=admitted,
            binding=binding,
            error_code="owner_operation_failed",
            error_message=(
                "Owner operation did not return a confirmed result; inspect before retrying."
                if admitted
                else "Owner could not admit this execution request."
            ),
        )


@contextmanager
def owner_environment(policy: OwnerPolicyV1) -> Iterator[None]:
    """Apply provisioned target environment only within the one-shot owner helper."""

    account = pwd.getpwuid(os.geteuid())
    previous = dict(os.environ)
    environment = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        **policy.profile.environment,
        "HOME": account.pw_dir,
        "USER": account.pw_name,
        "LOGNAME": account.pw_name,
        "SHELL": account.pw_shell or "/bin/sh",
        "HOUMAO_GLOBAL_REGISTRY_DIR": policy.registry_root,
        "HOUMAO_GLOBAL_RUNTIME_DIR": policy.runtime_root,
    }
    os.environ.clear()
    os.environ.update(environment)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous)


def serve_stdio(
    policy_path: Path,
    *,
    input_stream: BinaryIO | None = None,
    output_stream: BinaryIO | None = None,
    dispatch: OwnerDispatcher | None = None,
) -> int:
    """Read one bounded private request and write exactly one bounded response."""

    started = monotonic()
    source = input_stream if input_stream is not None else sys.stdin.buffer
    target = output_stream if output_stream is not None else sys.stdout.buffer
    request_id = "invalid-request"
    response: ExecutionResponseV1
    try:
        request = decode_request(source.read(MAX_REQUEST_BYTES + 1))
        request_id = request.request_id
        policy = load_owner_policy(policy_path)
        if dispatch is None:
            dispatch = _application_dispatch
        response = handle_request(request, policy, dispatch, started_at=started)
    except (OwnerAdmissionError, ExecutionProtocolError):
        response = ExecutionResponseV1(
            request_id=request_id,
            outcome="rejected",
            admitted=False,
            error_code="owner_admission_failed",
            error_message="Owner could not admit this request.",
        )
    try:
        payload = encode_response(response)
    except ExecutionProtocolError:
        response = ExecutionResponseV1(
            request_id=request_id,
            outcome="indeterminate",
            admitted=True,
            binding=response.binding,
            error_code="owner_response_limit",
            error_message="Owner result exceeded protocol limits; inspect before retrying.",
        )
        payload = encode_response(response)
    target.write(payload)
    target.flush()
    return 0 if response.outcome == "completed" else 1


def _application_dispatch(
    operation: OwnerOperation,
    binding: ExecutionBindingV1,
    policy: OwnerPolicyV1,
) -> JsonObject:
    """Load application services only after owner and operation admission."""

    from houmao.execution.application import dispatch_operation

    return dispatch_operation(operation, binding, policy)


def _validate_identity(policy: OwnerPolicyV1) -> None:
    """Require actual effective UID/GID and account to match provisioned owner policy."""

    if (os.geteuid(), os.getegid()) != (policy.uid, policy.gid):
        raise OwnerAdmissionError(
            "owner_mismatch", "Effective owner UID/GID does not match policy."
        )
    try:
        account = pwd.getpwuid(os.geteuid())
    except KeyError:
        raise OwnerAdmissionError(
            "owner_unavailable", "Effective owner has no account record."
        ) from None
    if policy.profile.account not in {
        account.pw_name,
        str(policy.uid),
        f"{policy.uid}:{policy.gid}",
    }:
        raise OwnerAdmissionError(
            "owner_mismatch", "Effective account does not match execution profile."
        )


def prepare_owner_operation(request: ExecutionRequestV1, policy: OwnerPolicyV1) -> OwnerOperation:
    """Validate the finite operation and resolve its project paths inside the owner."""

    started = monotonic()
    operation = validate_owner_operation(request)
    arguments = operation.arguments
    if not isinstance(arguments, LaunchArguments):
        return operation

    roots = tuple(
        Path(root).resolve()
        for root in (policy.controller.project_roots or (policy.profile.project_root,))
    )
    owner_root = Path(policy.profile.project_root)
    project = _scoped_launch_path(arguments.project_dir, base=owner_root, roots=roots)
    workdir = _scoped_launch_path(request.arguments.get("workdir"), base=project, roots=roots)
    if arguments.workdir is not None and not workdir.is_dir():
        raise OwnerAdmissionError("invalid_target_path", "Target workdir is unavailable.")
    for directory in (arguments.mail_root, arguments.mail_account_dir):
        if directory is not None and directory.exists() and not directory.is_dir():
            raise OwnerAdmissionError("invalid_arguments", "Invalid project launch value.")
    seed = arguments.gateway_admin_seed_path
    if seed is not None and (project / seed).is_dir():
        raise OwnerAdmissionError("invalid_arguments", "Invalid project launch value.")
    tool_params = arguments.tool_params
    if tool_params is not None and tool_params.startswith("@") and len(tool_params) > 1:
        tool_params = f"@{project / Path(tool_params[1:]).expanduser()}"
    if monotonic() - started >= request.deadline_seconds:
        raise OwnerAdmissionError(
            "deadline_exhausted", "Execution deadline expired before launch preparation."
        )

    return OwnerOperation(
        request,
        arguments.model_copy(
            update={"project_dir": str(project), "workdir": workdir, "tool_params": tool_params}
        ),
        operation.read_only,
    )


def _scoped_launch_path(value: object, *, base: Path, roots: tuple[Path, ...]) -> Path:
    """Resolve an owner path against its effective project and admitted roots."""

    if value is not None and (not isinstance(value, str) or not value or "\x00" in value):
        raise OwnerAdmissionError("invalid_target_path", "Requested owner path is invalid.")
    path = base.resolve() if value is None else (base / Path(value).expanduser()).resolve()
    if not any(path.is_relative_to(root) for root in roots):
        raise OwnerAdmissionError(
            "project_scope_denied", "Requested path is outside the admitted project scope."
        )
    return path


def _read_trusted_file(path: Path, *, limit: int) -> bytes:
    """Read one regular root/owner-owned file without following its final symlink."""

    if not path.is_absolute() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError("owner file path must be absolute without symlink ancestors")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as source:
        metadata = os.fstat(source.fileno())
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid not in {0, os.geteuid()}
            or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        ):
            raise ValueError("untrusted owner file")
        payload = source.read(limit + 1)
        if len(payload) > limit:
            raise ValueError("owner file exceeds limit")
        return payload


def _read_context(path: Path) -> _OwnerContextV1 | None:
    """Read an existing owner-context record without creating or repairing files."""

    try:
        return _OwnerContextV1.model_validate_json(_read_trusted_file(path, limit=4096))
    except FileNotFoundError:
        return None
    except (OSError, ValueError, ValidationError):
        raise OwnerAdmissionError(
            "invalid_owner_context", "Owner execution context is untrusted or incompatible."
        ) from None


def _initialize_context(policy: OwnerPolicyV1, host_id: str) -> _OwnerContextV1:
    """Publish a context atomically without replacing a concurrently created identity."""

    from houmao.owned_paths import resolve_houmao_home_root

    path = policy.context_file
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    context = _OwnerContextV1(
        context_id=str(uuid4()),
        uid=policy.uid,
        gid=policy.gid,
        host_id=host_id,
        registry_root=policy.registry_root,
        runtime_root=policy.runtime_root,
        config_root=str(resolve_houmao_home_root()),
    )
    descriptor, temporary = tempfile.mkstemp(prefix=".execution-context-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(context.model_dump_json().encode())
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError:
            existing = _read_context(path)
            if existing is None:
                raise OwnerAdmissionError(
                    "context_conflict", "Owner context changed during admission."
                ) from None
            return existing
        return context
    finally:
        os.unlink(temporary)


def _host_identity() -> str:
    """Fingerprint observed host identity without trusting request labels or environment."""

    machine = b""
    try:
        with Path("/etc/machine-id").open("rb") as stream:
            machine = stream.read(4096).strip()
    except OSError:
        pass
    return hashlib.sha256(machine + b"\x00" + socket.gethostname().encode()).hexdigest()
