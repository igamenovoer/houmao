"""Safe public failure contracts for plugin configuration and event dispatch."""

from __future__ import annotations

from typing import Literal


class PluginConfigurationError(ValueError):
    """Report invalid configuration without echoing configuration values."""


class PluginDispatchError(RuntimeError):
    """Report a request-scoped delivery failure without scheduling a retry."""

    def __init__(
        self,
        *,
        error_code: str,
        status_code: int,
        retryable: bool,
        dispatch_outcome: Literal["not_sent", "unknown"] = "not_sent",
        source_event_id: str | None = None,
        message: str = "Plugin event dispatch failed.",
    ) -> None:
        """Store safe response metadata; callers must not pass raw exceptions."""

        super().__init__(message)
        self.m_error_code: str = error_code
        self.m_status_code: int = status_code
        self.m_retryable: bool = retryable
        self.m_dispatch_outcome: Literal["not_sent", "unknown"] = dispatch_outcome
        self.m_source_event_id: str | None = source_event_id
        self.m_message: str = message

    @property
    def error_code(self) -> str:
        """Return the safe machine-readable failure category."""

        return self.m_error_code

    @property
    def status_code(self) -> int:
        """Return the HTTP status corresponding to this typed SDK failure."""

        return self.m_status_code

    @property
    def retryable(self) -> bool:
        """Return whether sender-side retry can be appropriate."""

        return self.m_retryable

    @property
    def dispatch_outcome(self) -> Literal["not_sent", "unknown"]:
        """Return whether a possibly completed handoff makes delivery uncertain."""

        return self.m_dispatch_outcome

    @property
    def source_event_id(self) -> str | None:
        """Return caller correlation identity without claiming idempotence."""

        return self.m_source_event_id

    @property
    def message(self) -> str:
        """Return the safe human-readable explanation."""

        return self.m_message

    def to_detail(self) -> dict[str, str | bool | None]:
        """Serialize safe detail for an HTTP-facing plugin error response."""

        return {
            "error_code": self.m_error_code,
            "retryable": self.m_retryable,
            "dispatch_outcome": self.m_dispatch_outcome,
            "source_event_id": self.m_source_event_id,
            "message": self.m_message,
        }
