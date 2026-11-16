"""Provider-aware accounting adapters for structured output and native logs."""

from __future__ import annotations

from collections.abc import Mapping
import re
from pathlib import Path
from typing import Any, Self

from houmao.agents.realm_controller.usage_adapters.claude import parse_claude
from houmao.agents.realm_controller.usage_adapters.codex import parse_codex
from houmao.agents.realm_controller.usage_adapters.common import (
    UsageAdapterState,
    UsageParseContext,
)
from houmao.agents.realm_controller.usage_adapters.kimi import parse_kimi
from houmao.agents.realm_controller.usage_adapters.dsh import (
    DshUsageAdapterState,
    configure_dsh_journal,
    inspect_dsh_journal,
    parse_dsh,
)
from houmao.agents.realm_controller.usage_models import UsageObservation, UsageSourceKind

_QUALIFIED_VERSIONS = {
    "claude": {"2.1.323"},
    "codex": {"0.167.2"},
    "kimi": {"2.6.0"},
    "dsh": {"0.2.2-rc.3"},
}


class UsageAdapter:
    """Incremental provider parser with checkpointable native-turn state."""

    def __init__(self) -> None:
        """Initialize an unconfigured adapter."""

        self.m_state: UsageAdapterState = UsageAdapterState(provider="unknown")

    @classmethod
    def from_provider(
        cls,
        provider: str,
        provider_session_id: str | None = None,
        profile_id: str | None = None,
    ) -> Self:
        """Create an adapter for one supported provider stream."""

        if provider not in {"claude", "codex", "kimi", "dsh"}:
            raise ValueError(f"Unsupported usage provider: {provider}")
        instance = cls()
        state_type = DshUsageAdapterState if provider == "dsh" else UsageAdapterState
        instance.m_state = state_type(
            provider=provider, provider_session_id=provider_session_id, profile_id=profile_id
        )
        return instance

    @property
    def provider_session_id(self) -> str | None:
        """Return the latest verified provider session identity."""

        return self.m_state.provider_session_id

    @property
    def provider_turn_id(self) -> str | None:
        """Return the current native turn identity when structured evidence exposes it."""

        return self.m_state.provider_turn_id

    def snapshot_state(self) -> dict[str, Any]:
        """Return JSON-safe parser state for the source checkpoint transaction."""

        return self.m_state.model_dump(mode="json")

    def restore_state(self, state: Mapping[str, Any]) -> None:
        """Restore a previously persisted state for the same configured provider."""

        state_type = DshUsageAdapterState if self.m_state.provider == "dsh" else UsageAdapterState
        restored = state_type.model_validate(dict(state))
        if restored.provider != self.m_state.provider:
            raise ValueError("Usage adapter checkpoint belongs to another provider")
        self.m_state = restored

    def configure_native_source(self, path: Path) -> None:
        """Verify provider-specific source framing before reading event rows."""

        if isinstance(self.m_state, DshUsageAdapterState):
            if not self.m_state.provider_session_id:
                raise ValueError("dsh_journal_session_identity_missing")
            info = inspect_dsh_journal(path, self.m_state.provider_session_id)
            configure_dsh_journal(self.m_state, info)

    def parse(
        self,
        payload: Mapping[str, Any],
        *,
        source_ref: str,
        source_kind: UsageSourceKind = "native_session_log",
        turn_id: str | None = None,
        binding_id: str | None = None,
    ) -> list[UsageObservation]:
        """Parse one raw provider or canonical event without performing I/O."""

        self.m_state.sequence += 1
        raw = payload.get("raw_payload")
        if isinstance(raw, dict):
            payload = raw
        self._observe_version(payload)
        context = UsageParseContext(
            source_ref=source_ref,
            source_kind=source_kind,
            turn_id=turn_id,
            binding_id=binding_id,
        )
        if isinstance(self.m_state, DshUsageAdapterState):
            result = parse_dsh(payload, self.m_state, context)
        else:
            parser = {"claude": parse_claude, "codex": parse_codex, "kimi": parse_kimi}[
                self.m_state.provider
            ]
            result = parser(payload, self.m_state, context)
        for item in result:
            if item.kind == "cumulative" and item.measurement_scope == "session_cumulative":
                for key, value in item.values.items():
                    if value is not None:
                        self.m_state.previous_totals[key] = value
                        self.m_state.previous_total_source_ids[key] = [item.source_ref]
        return result

    def _observe_version(self, payload: Mapping[str, Any]) -> None:
        """Qualify explicit client versions without treating protocol IDs as versions."""

        version = payload.get("cli_version")
        if self.m_state.provider == "claude":
            version = version or payload.get("version")
        elif self.m_state.provider == "codex" and payload.get("type") == "session_meta":
            data = payload.get("payload")
            if isinstance(data, dict):
                version = data.get("cli_version") or version
        if not isinstance(version, str) or not re.fullmatch(
            r"[0-9]+(?:\.[0-9]+){1,3}(?:[-+][A-Za-z0-9._-]+)?", version
        ):
            return
        if self.m_state.provider_version not in {None, version}:
            self.m_state.previous_totals.clear()
            self.m_state.previous_total_source_ids.clear()
        self.m_state.provider_version = version
        self.m_state.qualified_version = version in _QUALIFIED_VERSIONS[self.m_state.provider]


def parse_usage_payload(
    provider: str,
    payload: Mapping[str, Any],
    *,
    source_ref: str,
    source_kind: UsageSourceKind = "native_session_log",
    provider_session_id: str | None = None,
    provider_turn_id: str | None = None,
    turn_id: str | None = None,
    binding_id: str | None = None,
    profile_id: str | None = None,
) -> list[UsageObservation]:
    """Parse an independent payload whose native association is already known."""

    adapter = UsageAdapter.from_provider(provider, provider_session_id, profile_id)
    adapter.m_state.provider_turn_id = provider_turn_id
    return adapter.parse(
        payload,
        source_ref=source_ref,
        source_kind=source_kind,
        turn_id=turn_id,
        binding_id=binding_id,
    )
