"""Error types for the brain launch runtime."""

from __future__ import annotations


class BrainLaunchRuntimeError(RuntimeError):
    """Base runtime error.

    Notes
    -----
    Subclasses provide more specific failure reasons for callers that need to
    branch on error class.
    """


class LaunchPlanError(BrainLaunchRuntimeError):
    """Raised when launch-plan composition fails."""


class LaunchPolicyResolutionError(LaunchPlanError):
    """Raised when startup-prompt policy resolution blocks provider launch."""

    def __init__(
        self,
        *,
        requested_operator_prompt_mode: str,
        tool: str,
        policy_backend: str,
        detected_version: str,
        detail: str,
    ) -> None:
        self.requested_operator_prompt_mode = requested_operator_prompt_mode
        self.tool = tool
        self.policy_backend = policy_backend
        self.detected_version = detected_version
        self.detail = detail
        super().__init__(detail)


class SessionManifestError(BrainLaunchRuntimeError):
    """Raised when a persisted session manifest is invalid or unusable."""


class SchemaValidationError(BrainLaunchRuntimeError):
    """Raised when JSON payloads fail schema validation."""


class BackendExecutionError(BrainLaunchRuntimeError):
    """Raised when a backend command fails to execute successfully."""


class GatewayError(BrainLaunchRuntimeError):
    """Raised when gateway lifecycle, discovery, or request handling fails."""


class GatewayDiscoveryError(GatewayError):
    """Raised when stable or live gateway discovery pointers are missing or invalid."""


class GatewayNoLiveInstanceError(GatewayError):
    """Raised when a gateway-aware operation requires a live gateway instance."""


class GatewayUnsupportedBackendError(GatewayError):
    """Raised when a live gateway action targets an unsupported backend."""


class GatewayAttachError(GatewayError):
    """Raised when gateway attach or startup fails."""


class GatewayProtocolError(GatewayError):
    """Raised when gateway protocol versions or payloads are incompatible."""


class GatewayHttpError(GatewayError):
    """Raised when a gateway HTTP request fails."""

    def __init__(
        self,
        *,
        method: str,
        url: str,
        detail: str,
        status_code: int | None = None,
    ) -> None:
        self.method = method
        self.url = url
        self.detail = detail
        self.status_code = status_code
        status = f"status={status_code}" if status_code is not None else "status=unavailable"
        super().__init__(f"Gateway HTTP error for {method} {url}: {status}, detail={detail}")


class MailboxCommandError(BrainLaunchRuntimeError):
    """Raised when a runtime-owned mailbox command cannot complete safely."""


class MailboxResultParseError(MailboxCommandError):
    """Raised when a mailbox command result fails sentinel or JSON validation."""


class BackendInterrupted(BackendExecutionError):
    """Raised when a backend turn is interrupted."""


class BackendTerminated(BackendExecutionError):
    """Raised when a backend session is terminated."""
