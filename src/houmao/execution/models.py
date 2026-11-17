"""Strict public contracts for configured execution routes and observed owners."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import PurePosixPath
import re
from typing import Literal, TypeAlias
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

ExecutionTransport: TypeAlias = Literal["local", "sudo", "ssh", "docker"]
ExecutionOperation: TypeAlias = Literal[
    "describe",
    "launch",
    "state",
    "inspect",
    "capture",
    "resume",
    "prompt",
    "interrupt",
    "stop",
    "relaunch",
    "home",
    "status",
    "refresh_check",
    "refresh",
    "gateway_status",
    "gateway_attach",
    "gateway_detach",
    "cleanup",
]
ExecutionAuthority: TypeAlias = Literal["local_uid", "sudo_policy", "ssh_account", "container_exec"]
JsonObject: TypeAlias = dict[str, JsonValue]
_SAFE_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}\Z")
_SAFE_ACCOUNT = re.compile(r"(?:[A-Za-z_][A-Za-z0-9_-]*\$?|[0-9]+(?::[0-9]+)?)\Z")
_SAFE_HOST = re.compile(r"[A-Za-z0-9][A-Za-z0-9.:-]{0,252}\Z")
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_HEX_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def validate_selector(value: str) -> str:
    """Validate one filesystem-safe configuration or identity selector."""

    if not _SAFE_NAME.fullmatch(value) or value in {".", ".."}:
        raise ValueError("invalid execution selector")
    return value


def validate_absolute_path(value: str) -> str:
    """Validate a target path lexically without opening it on the caller's host."""

    path = PurePosixPath(value)
    if not path.is_absolute() or "\x00" in value or "\n" in value or ".." in path.parts:
        raise ValueError("execution path must be absolute and traversal-free")
    return value


class _ExecutionModel(BaseModel):
    """Forbid unrecognized fields and implicit boundary coercion."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False, frozen=True)


class ControllerScopeV1(_ExecutionModel):
    """Record controller scope admitted by provisioned OS transport policy."""

    controller_id: str
    authority: ExecutionAuthority
    operations: tuple[ExecutionOperation, ...]
    project_roots: tuple[str, ...] = ()

    _controller_name = field_validator("controller_id")(validate_selector)

    @field_validator("project_roots")
    @classmethod
    def _absolute_roots(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        """Keep admitted project roots target-local and absolute."""

        return tuple(validate_absolute_path(value) for value in values)


class ExecutionProfileV1(_ExecutionModel):
    """Select one pre-provisioned owner through a closed native transport."""

    schema_version: Literal[1] = 1
    name: str
    transport: ExecutionTransport
    account: str
    entrypoint: str
    policy_path: str
    project_root: str
    environment: dict[str, str] = Field(default_factory=dict)
    expected_uid: int | None = Field(default=None, ge=0)
    expected_gid: int | None = Field(default=None, ge=0)
    ssh_host: str | None = None
    ssh_port: int = Field(default=22, ge=1, le=65535)
    identity_file: str | None = None
    known_hosts_file: str | None = None
    container_id: str | None = None
    timeout_seconds: float = Field(default=30.0, gt=0, le=120)

    _name = field_validator("name")(validate_selector)
    _paths = field_validator("entrypoint", "policy_path", "project_root")(validate_absolute_path)

    @field_validator("account")
    @classmethod
    def _account(cls, value: str) -> str:
        """Prevent native option injection through an account selector."""

        if not _SAFE_ACCOUNT.fullmatch(value):
            raise ValueError("invalid execution account")
        return value

    @field_validator("identity_file", "known_hosts_file")
    @classmethod
    def _optional_local_path(cls, value: str | None) -> str | None:
        """Accept only explicit local authentication-reference paths."""

        return validate_absolute_path(value) if value is not None else None

    @field_validator("environment")
    @classmethod
    def _environment(cls, values: dict[str, str]) -> dict[str, str]:
        """Reject identity overrides, delegation state, and inline secret settings."""

        for key, value in values.items():
            upper = key.upper()
            if (
                not _ENV_NAME.fullmatch(key)
                or upper in {"HOME", "USER", "LOGNAME", "TMUX", "TMUX_PANE", "SSH_AUTH_SOCK"}
                or upper.startswith(("SUDO_", "SSH_", "DOCKER_", "LD_", "PYTHON"))
                or any(
                    marker in upper
                    for marker in ("PASSWORD", "SECRET", "TOKEN", "API_KEY", "PRIVATE_KEY")
                )
                or "\x00" in value
            ):
                raise ValueError("execution environment contains an unsupported or secret setting")
        return values

    @model_validator(mode="after")
    def _transport_fields(self) -> ExecutionProfileV1:
        """Validate transport-specific target coordinates without cross-kind fallbacks."""

        if self.transport == "ssh":
            if self.ssh_host is None or not _SAFE_HOST.fullmatch(self.ssh_host):
                raise ValueError("SSH transport requires a literal safe host selector")
            if self.known_hosts_file is None or ":" in self.account:
                raise ValueError("SSH transport requires known-hosts state and one account")
        elif (
            any(
                value is not None
                for value in (self.ssh_host, self.identity_file, self.known_hosts_file)
            )
            or self.ssh_port != 22
        ):
            raise ValueError("SSH fields require SSH transport")
        if self.transport == "docker":
            if self.container_id is None or not _HEX_DIGEST.fullmatch(self.container_id):
                raise ValueError("Docker transport requires an immutable full container ID")
        elif self.container_id is not None:
            raise ValueError("container_id requires Docker transport")
        if self.transport != "docker" and ":" in self.account:
            raise ValueError("UID:GID account form requires Docker transport")
        return self


class ExecutionBindingV1(_ExecutionModel):
    """Separate observed owner identity and controller scope from logical agent identity."""

    schema_version: Literal[1] = 1
    context_id: str
    host_id: str
    account: str
    uid: int = Field(ge=0)
    gid: int = Field(ge=0)
    groups: tuple[int, ...] = ()
    registry_root: str
    runtime_root: str
    project_root: str
    profile_name: str
    transport: ExecutionTransport
    controller: ControllerScopeV1
    route_fingerprint: str
    container_id: str | None = None
    tmux_socket: str | None = None

    _profile = field_validator("profile_name")(validate_selector)
    _paths = field_validator("registry_root", "runtime_root", "project_root")(
        validate_absolute_path
    )

    @field_validator("context_id", "host_id", "account")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Reject unobserved or unsafe owner identity material."""

        if not value.strip() or value != value.strip() or any(c in value for c in "\x00\r\n"):
            raise ValueError("execution identity must be a nonempty single-line value")
        return value

    @field_validator("route_fingerprint", "container_id")
    @classmethod
    def _digest(cls, value: str | None) -> str | None:
        """Require immutable route/container digests where supplied."""

        if value is not None and not _HEX_DIGEST.fullmatch(value):
            raise ValueError("execution digest must be 64 lowercase hexadecimal characters")
        return value

    @field_validator("tmux_socket")
    @classmethod
    def _socket(cls, value: str | None) -> str | None:
        """Keep saved socket authority absolute in its owner context."""

        return validate_absolute_path(value) if value is not None else None

    @field_validator("groups")
    @classmethod
    def _groups(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        """Reject impossible observed group identifiers."""

        if any(value < 0 for value in values):
            raise ValueError("group identifiers must be nonnegative")
        return values


class ContextPathV1(_ExecutionModel):
    """Qualify an owner-local path so callers cannot mistake it for a local resource."""

    context_id: str
    path: str

    _path = field_validator("path")(validate_absolute_path)


class ExecutionRequestV1(_ExecutionModel):
    """Carry one finite typed operation without shell or unrestricted argv execution."""

    schema_version: Literal[1] = 1
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    operation: ExecutionOperation
    deadline_seconds: float = Field(default=30.0, gt=0, le=120)
    arguments: JsonObject = Field(default_factory=dict)
    expected_route_fingerprint: str | None = None
    expected_binding: ExecutionBindingV1 | None = None
    agent_id: str | None = None
    generation_id: str | None = None

    _request_id = field_validator("request_id")(validate_selector)

    @field_validator("expected_route_fingerprint")
    @classmethod
    def _expected_route(cls, value: str | None) -> str | None:
        """Carry a consistency expectation, never an authentication credential."""

        if value is not None and not _HEX_DIGEST.fullmatch(value):
            raise ValueError("expected route fingerprint must be a SHA-256 digest")
        return value

    @field_validator("agent_id", "generation_id")
    @classmethod
    def _optional_selector(cls, value: str | None) -> str | None:
        """Keep target identity independent of path or shell interpretation."""

        return validate_selector(value) if value is not None else None

    @field_validator("deadline_seconds")
    @classmethod
    def _finite_deadline(cls, value: float) -> float:
        """Reject non-finite deadline values before transport admission."""

        if not math.isfinite(value):
            raise ValueError("deadline must be finite")
        return value

    @field_validator("arguments")
    @classmethod
    def _operation_arguments(cls, value: JsonObject) -> JsonObject:
        """Reject generic execution hooks; owner dispatch validates operation-specific keys."""

        if {"argv", "command", "shell", "transport", "executor", "controller"}.intersection(value):
            raise ValueError("execution arguments cannot supply execution authority or commands")
        return value


class ExecutionResponseV1(_ExecutionModel):
    """Report owner admission separately from completion and transport uncertainty."""

    schema_version: Literal[1] = 1
    request_id: str
    outcome: Literal["completed", "rejected", "indeterminate"]
    admitted: bool | None
    binding: ExecutionBindingV1 | None = None
    result: JsonObject = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    capabilities: tuple[ExecutionOperation, ...] = ()

    _request_id = field_validator("request_id")(validate_selector)

    @model_validator(mode="after")
    def _outcome(self) -> ExecutionResponseV1:
        """Disallow reports that treat uncertain completion as a safe rejection."""

        if self.outcome == "completed" and (not self.admitted or self.error_code is not None):
            raise ValueError("completed responses require admission without an error")
        if self.outcome == "rejected" and self.admitted:
            raise ValueError("admitted operations cannot be reported as rejected")
        if self.outcome == "rejected" and self.admitted is not False:
            raise ValueError("rejection requires confirmed non-admission")
        if self.outcome == "indeterminate" and self.admitted is False:
            raise ValueError("indeterminate responses cannot claim confirmed non-admission")
        if self.outcome != "completed" and not self.error_code:
            raise ValueError("failed responses require a safe error code")
        return self


def route_fingerprint(profile: ExecutionProfileV1) -> str:
    """Hash non-secret authority settings while allowing transport-key rotation."""

    fields = profile.model_dump(
        mode="json", exclude={"timeout_seconds", "identity_file", "known_hosts_file"}
    )
    return hashlib.sha256(
        json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
