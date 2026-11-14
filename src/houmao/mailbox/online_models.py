"""Operator contracts and immutable runtime scope for online mailbox controls."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from houmao.mailbox.errors import GatewayMailboxError


@dataclass(frozen=True)
class OnlineAuthorityContext:
    """Explicit local runtime authority; an agent ID alone grants no access."""

    manifest_path: Path
    agent_id: str
    session_id: str | None


@dataclass(frozen=True)
class OnlineFence:
    """Capture the configured binding and shared connection epoch for a worker."""

    agent_id: str
    session_id: str | None
    binding_id: str
    revision: str
    epoch_id: str
    account_id: str


class OnlineBindingError(GatewayMailboxError):
    """Expose a safe code and commit/uncertainty outcome without provider secrets."""

    def __init__(self, code: str, detail: str, *, uncertain: bool = False) -> None:
        super().__init__(detail)
        self.code = code
        self.uncertain = uncertain


class _OnlineModel(BaseModel):
    """Reject unknown operator inputs and coercion."""

    model_config = ConfigDict(extra="forbid", strict=True)


class OnlineAttachRequest(_OnlineModel):
    """Explicit existing-account attachment; no administrative credentials."""

    provider: Literal["stalwart"] = "stalwart"
    expected_revision: str = Field(min_length=1)
    address: str = Field(min_length=1)
    login_identity: str = Field(min_length=1)
    credential_source_ref: str = Field(min_length=1, repr=False)
    jmap_url: str | None = None
    base_url: str | None = None
    account_id: str | None = None
    replace: bool = False
    timeout_seconds: float = Field(default=10.0, gt=0, le=120)

    @model_validator(mode="after")
    def _endpoint_selected(self) -> OnlineAttachRequest:
        """Require exactly one explicit discovery endpoint or server base."""

        if (self.jmap_url is None) == (self.base_url is None):
            raise ValueError("Select exactly one of jmap_url and base_url")
        return self


class OnlineControlRequest(_OnlineModel):
    """Revision-pinned refresh, reconnect, or detach request."""

    expected_revision: str = Field(min_length=1)
    credential_source_ref: str | None = Field(default=None, repr=False)
    timeout_seconds: float = Field(default=10.0, gt=0, le=120)


class OnlineBindingStatus(_OnlineModel):
    """Safe configured identity and operational connection snapshot."""

    agent_id: str
    revision: str
    binding_id: str | None = None
    address: str | None = None
    provider: Literal["stalwart"] | None = None
    account_id: str | None = None
    identity_id: str | None = None
    epoch_id: str | None = None
    state: Literal["absent", "configured", "retiring", "degraded"]
    available: bool = False
    committed: bool = False
    warnings: list[str] = Field(default_factory=list)
