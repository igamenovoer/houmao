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


class SessionManifestError(BrainLaunchRuntimeError):
    """Raised when a persisted session manifest is invalid or unusable."""


class SchemaValidationError(BrainLaunchRuntimeError):
    """Raised when JSON payloads fail schema validation."""


class BackendExecutionError(BrainLaunchRuntimeError):
    """Raised when a backend command fails to execute successfully."""


class MailboxCommandError(BrainLaunchRuntimeError):
    """Raised when a runtime-owned mailbox command cannot complete safely."""


class MailboxResultParseError(MailboxCommandError):
    """Raised when a mailbox command result fails sentinel or JSON validation."""


class BackendInterrupted(BackendExecutionError):
    """Raised when a backend turn is interrupted."""


class BackendTerminated(BackendExecutionError):
    """Raised when a backend session is terminated."""
