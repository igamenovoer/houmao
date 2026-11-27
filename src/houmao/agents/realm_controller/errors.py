"""Error types for the brain launch runtime."""

from __future__ import annotations

from enum import Enum


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


class RuntimeStartupRollbackError(BrainLaunchRuntimeError):
    """Report the launch failure and any resources that could not be released."""

    def __init__(self, startup_error: Exception, failures: tuple[str, ...]) -> None:
        self.startup_error = startup_error
        super().__init__(f"{startup_error}. Incomplete launch cleanup: {', '.join(failures)}")


class RetiredJoinedSessionError(SessionManifestError):
    """Reject retired adoption, retaining locators only to protect its artifacts."""

    def __init__(
        self,
        *,
        agent_id: str | None = None,
        agent_name: str | None = None,
        brain_manifest_path: str | None = None,
        home_path: str | None = None,
        mailbox_credential_refs: tuple[str, ...] = (),
    ) -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.brain_manifest_path = brain_manifest_path
        self.home_path = home_path
        self.mailbox_credential_refs = mailbox_credential_refs
        super().__init__(
            "Manual tmux adoption is retired. Use the owning Houmao release to wind down "
            "management of this session, then start a fresh supported managed launch."
        )


class SchemaValidationError(BrainLaunchRuntimeError):
    """Raised when JSON payloads fail schema validation."""


class BackendExecutionError(BrainLaunchRuntimeError):
    """Raised when a backend command fails to execute successfully."""


class HeadlessTurnSettlementUnknown(BackendExecutionError):
    """Signal that client completion leaves native execution unresolved."""


class ServiceStartupCheck(Enum):
    """Safe native startup diagnostics that can cross the owner boundary."""

    CODEX_EXECUTABLE_VERSION = "Codex app-server launch has an invalid executable version."
    CODEX_INITIALIZE = "Codex app-server failed the native initialize request."
    CODEX_HANDSHAKE = "Codex app-server handshake has an invalid user agent."
    CODEX_VERSION = "Codex app-server peer version does not match the selected executable."
    CODEX_HOME = "Codex app-server handshake did not confirm the selected private home."
    CODEX_THREAD = "Codex app-server did not bind the requested native thread and workspace."
    CODEX_ROLLOUT = "Codex native thread lacks exact persisted workspace evidence."
    CODEX_APPROVAL = "Codex app-server did not confirm the requested approval policy."
    CODEX_SANDBOX = "Codex app-server did not confirm the requested sandbox mode."
    CODEX_MODEL = "Codex app-server did not bind the configured native model."
    KIMI_EXECUTABLE_VERSION = "Kimi ACP launch has an invalid executable version."
    KIMI_INITIALIZE = "Kimi ACP failed the native initialize request."
    KIMI_PROTOCOL = "Kimi ACP did not negotiate the required protocol version 1."
    KIMI_CAPABILITIES = "Kimi ACP returned malformed agent or session capabilities."
    KIMI_VERSION = "Kimi ACP peer version does not match the selected executable."
    KIMI_CONTINUATION = "Kimi ACP did not advertise exact session continuation."
    KIMI_SESSION = "Kimi ACP did not bind the selected native session."
    KIMI_MODEL = "Kimi ACP did not bind the configured native model."
    KIMI_PERMISSION_MODE = "Kimi ACP did not confirm its native permission_mode."
    HERMES_DAEMON = "Hermes could not start or discover the native gateway for this home."
    HERMES_PROCESS = "Hermes ACP could not start its native process. See its private diagnostics."
    HERMES_INITIALIZE = "Hermes ACP did not negotiate the required protocol version 1."
    HERMES_SESSION = "Hermes ACP did not bind the requested native session and workspace."
    HERMES_APPROVAL_POLICY = "Hermes did not confirm its native unattended command approval policy."
    HERMES_EDIT_MODE = "Hermes ACP did not confirm the required native edit approval mode."


class ServiceStartupCompatibilityError(BackendExecutionError):
    """Report one allowlisted native startup check without including peer data."""

    def __init__(self, check: ServiceStartupCheck) -> None:
        self.check = check
        detail = check.value
        if check.name.startswith("CODEX_"):
            detail = f"{detail} Available alternatives are headless and tui."
        super().__init__(detail)


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
        error_code: str | None = None,
    ) -> None:
        """Keep the transport status and any recognized access reason."""

        self.method = method
        self.url = url
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
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
