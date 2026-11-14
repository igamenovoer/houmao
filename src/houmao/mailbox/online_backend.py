"""Lazy managed online backend admission independent of HTTP handler locks."""

from __future__ import annotations

from typing import Any, Callable

from houmao.agents.mailbox_runtime_models import StalwartMailboxResolvedConfig
from houmao.mailbox.online_authority import OnlineConnectionAuthority
from houmao.mailbox.online_models import OnlineAuthorityContext
from houmao.mailbox.stalwart import StalwartJmapClient


class ManagedOnlineBackend:
    """Acquire shared runtime admission around every managed provider operation."""

    def __init__(self) -> None:
        self.m_binding: StalwartMailboxResolvedConfig
        self.m_authority: OnlineConnectionAuthority
        self.m_factory: Callable[[StalwartMailboxResolvedConfig, StalwartJmapClient], Any]

    @classmethod
    def from_context(
        cls,
        binding: StalwartMailboxResolvedConfig,
        context: OnlineAuthorityContext,
        backend_factory: Callable[[StalwartMailboxResolvedConfig, StalwartJmapClient], Any],
    ) -> ManagedOnlineBackend:
        """Construct pure routing state; no credentials or provider discovery are read."""

        instance = cls()
        instance.m_binding = binding
        instance.m_authority = OnlineConnectionAuthority.from_context(context)
        instance.m_factory = backend_factory
        return instance

    def _invoke(self, operation: str, **kwargs: Any) -> Any:
        """Use one immutable selected connection through bounded provider effects."""

        with self.m_authority.operation(
            expected_binding_id=self.m_binding.binding_id
        ) as connection:
            backend = self.m_factory(connection.config, connection.client)
            return getattr(backend, operation)(**kwargs)

    def status(self) -> Any:
        """Probe the selected online provider under shared admission."""
        return self._invoke("status")

    def list_page(self, **kwargs: Any) -> Any:
        """List finite metadata through a pinned provider connection."""
        return self._invoke("list_page", **kwargs)

    def peek(self, **kwargs: Any) -> Any:
        """Retrieve selected content without marking read."""
        return self._invoke("peek", **kwargs)

    def read(self, **kwargs: Any) -> Any:
        """Retrieve selected content and mark read."""
        return self._invoke("read", **kwargs)

    def send(self, **kwargs: Any) -> Any:
        """Send once without replaying an uncertain provider submission."""
        return self._invoke("send", **kwargs)

    def reply(self, **kwargs: Any) -> Any:
        """Reply once within the admitted account scope."""
        return self._invoke("reply", **kwargs)

    def post(self, **kwargs: Any) -> Any:
        """Expose the provider's explicit unsupported-operation result."""
        return self._invoke("post", **kwargs)

    def mark(self, **kwargs: Any) -> Any:
        """Update selected provider flags within admitted scope."""
        return self._invoke("mark", **kwargs)

    def move(self, **kwargs: Any) -> Any:
        """Move selected provider messages within admitted scope."""
        return self._invoke("move", **kwargs)

    def archive(self, **kwargs: Any) -> Any:
        """Archive selected provider messages within admitted scope."""
        return self._invoke("archive", **kwargs)
