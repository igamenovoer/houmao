"""Validated arguments and read-only classification for owner v1 operations."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from houmao.agents.realm_controller.gateway_models import GatewayTuiTrackingTimingOverridesV1
from houmao.agents.realm_controller.models import RelaunchChatSessionSelection
from houmao.execution.models import ExecutionOperation, ExecutionRequestV1
from houmao.execution.tmux_selection import TmuxServerSelector
from houmao.gateway.deployment import validate_gateway_access_config_path
from houmao.project.launch_request import ProjectLaunchRequest


class OwnerAdmissionError(ValueError):
    """Reject an operation before mutation using a safe public diagnostic.

    A failure after mutation begins must retain uncertainty.
    """

    def __init__(self, code: str, message: str) -> None:
        """Keep the stable refusal code separate from the message."""

        super().__init__(message)
        self.m_code: str = code

    @property
    def code(self) -> str:
        """Return the machine-readable refusal code."""

        return self.m_code


class LaunchArguments(ProjectLaunchRequest):
    """Launch options and a project directory interpreted by the owner."""

    project_dir: str | None = None


class NoArguments(BaseModel):
    """Accept no operation-specific parameters."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class PromptArguments(NoArguments):
    """Provider prompt and optional model overrides."""

    prompt: str = Field(min_length=1)
    model: str | None = None
    reasoning_level: int | None = Field(default=None, ge=0)


class RefreshArguments(NoArguments):
    """Bound the owner-side refresh by the v1 operation deadline."""

    timeout_seconds: float = Field(gt=0, le=120)


class RelaunchArguments(NoArguments):
    """Choose a provider chat session for relaunch."""

    chat_session: RelaunchChatSessionSelection | None = None


class GatewayAttachArguments(NoArguments):
    """Gateway startup posture and an optional owner-side access policy."""

    background: bool = False
    tui_tracking_timing_overrides: GatewayTuiTrackingTimingOverridesV1 | None = None
    access_config_path: str | None = None

    @field_validator("access_config_path", mode="before")
    @classmethod
    def _valid_access_path(cls, value: object) -> str:
        """Check the path shape without opening it."""

        return validate_gateway_access_config_path(value)


class CleanupArguments(NoArguments):
    """Select a cleanup operation and whether it may have effects."""

    kind: Literal["session", "logs", "mailbox"]
    dry_run: bool = False
    purge_registry: bool = False


@dataclass(frozen=True)
class OwnerOperation:
    """A request whose finite arguments have been validated before owner setup."""

    request: ExecutionRequestV1
    arguments: NoArguments | LaunchArguments
    read_only: bool


@dataclass(frozen=True)
class _ControlOperation:
    """Pair a control argument schema with its default effect classification."""

    arguments: type[NoArguments] = NoArguments
    read_only: bool = False


_OBSERVE = _ControlOperation(read_only=True)
_CONTROL_OPERATIONS: dict[ExecutionOperation, _ControlOperation] = {
    "describe": _OBSERVE,
    "state": _OBSERVE,
    "inspect": _OBSERVE,
    "capture": _OBSERVE,
    "resume": _OBSERVE,
    "home": _OBSERVE,
    "status": _OBSERVE,
    "refresh_check": _OBSERVE,
    "gateway_status": _OBSERVE,
    "interrupt": _ControlOperation(),
    "stop": _ControlOperation(),
    "gateway_detach": _ControlOperation(),
    "prompt": _ControlOperation(PromptArguments),
    "refresh": _ControlOperation(RefreshArguments),
    "relaunch": _ControlOperation(RelaunchArguments),
    "gateway_attach": _ControlOperation(GatewayAttachArguments),
    "cleanup": _ControlOperation(CleanupArguments),
}


def validate_owner_operation(request: ExecutionRequestV1) -> OwnerOperation:
    """Validate the unchanged v1 wire shape for a single owner operation."""

    if request.operation == "launch":
        return OwnerOperation(request, _launch_arguments(request), read_only=False)
    definition = _CONTROL_OPERATIONS[request.operation]
    values = dict(request.arguments)
    if set(values) - set(definition.arguments.model_fields):
        raise OwnerAdmissionError("invalid_arguments", "Unsupported finite operation arguments.")
    if request.operation != "describe" and request.agent_id is None:
        raise OwnerAdmissionError("agent_required", "An exact managed-agent ID is required.")
    if request.operation == "refresh":
        values.setdefault("timeout_seconds", request.deadline_seconds)
    try:
        # JSON mode accepts the nested relaunch selection in its wire form.
        arguments = definition.arguments.model_validate_json(json.dumps(values))
    except ValidationError:
        raise OwnerAdmissionError(
            "invalid_arguments", "Invalid finite operation arguments."
        ) from None
    read_only = definition.read_only or (
        isinstance(arguments, CleanupArguments) and arguments.dry_run
    )
    return OwnerOperation(request, arguments, read_only)


def _launch_arguments(request: ExecutionRequestV1) -> LaunchArguments:
    """Validate launch options without consulting the CLI parser."""

    values = request.arguments
    if set(values) - set(LaunchArguments.model_fields):
        raise OwnerAdmissionError("invalid_arguments", "Unsupported project launch parameter.")
    sources = [
        value for field in ("profile", "specialist") if (value := values.get(field)) is not None
    ]
    if len(sources) != 1 or not isinstance(sources[0], str) or not sources[0].strip():
        raise OwnerAdmissionError(
            "invalid_arguments", "Select exactly one nonempty project launch source."
        )
    if "project_dir" in values and not isinstance(values["project_dir"], str):
        raise OwnerAdmissionError("invalid_arguments", "Invalid project launch path.")
    server, socket_path = values.get("tmux_server"), values.get("tmux_socket_path")
    if server is not None or socket_path is not None:
        try:
            TmuxServerSelector.model_validate({"server": server, "socket_path": socket_path})
        except ValueError:
            raise OwnerAdmissionError(
                "invalid_tmux_server",
                "Invalid tmux selector. Use an absolute --tmux-socket-path with --tmux-server socket.",
            ) from None
    try:
        arguments = LaunchArguments.model_validate(values)
    except ValidationError:
        raise OwnerAdmissionError("invalid_arguments", "Invalid project launch value.") from None
    try:
        arguments.validate_combinations()
    except ValueError as exc:
        raise OwnerAdmissionError("invalid_arguments", str(exc)) from None
    return arguments
