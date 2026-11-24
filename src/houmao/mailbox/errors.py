"""Shared safe mailbox backend failures without service import dependencies."""


class MailboxError(RuntimeError):
    """Base error raised by mailbox helpers."""


class MailboxProtocolError(MailboxError):
    """Raised when canonical mailbox data is invalid or malformed."""


class MailboxBootstrapError(MailboxError):
    """Raised when filesystem mailbox bootstrap cannot complete safely."""


class GatewayMailboxError(RuntimeError):
    """Raised when a managed mailbox cannot satisfy a request."""


class GatewayMailboxRecipientPolicyError(GatewayMailboxError):
    """Preserve the recipient policy result without identifying a refused recipient."""

    def __init__(self, *, unavailable: bool) -> None:
        self.code = "recipient_policy_unavailable" if unavailable else "recipient_policy_refused"
        detail = (
            "Recipient mail policy is unavailable"
            if unavailable
            else "Recipient mail policy refused delivery"
        )
        super().__init__(detail)


class GatewayMailboxUnsupportedError(GatewayMailboxError):
    """Raised when a provider does not implement the selected operation."""


class GatewayMailboxMutationError(GatewayMailboxError):
    """Preserve one provider mutation outcome and its original managed binding."""

    def __init__(
        self,
        *,
        operation: str,
        outcome: str,
        email_id: str | None,
        submission_id: str | None,
        agent_id: str,
        binding_id: str,
        revision: str,
    ) -> None:
        super().__init__(f"Online {operation} outcome={outcome}; reconcile before repeating")
        self.operation = operation
        self.outcome = outcome
        self.email_id = email_id
        self.submission_id = submission_id
        self.agent_id = agent_id
        self.binding_id = binding_id
        self.revision = revision

    def safe_payload(self) -> dict[str, str | None]:
        """Return reconciliation facts without provider diagnostics or secrets."""

        return {
            "error_code": "mail_mutation_outcome",
            "detail": str(self),
            "operation": self.operation,
            "outcome": self.outcome,
            "email_id": self.email_id,
            "submission_id": self.submission_id,
            "agent_id": self.agent_id,
            "binding_id": self.binding_id,
            "revision": self.revision,
        }
