"""Validate and retain bounded native Web observations without lifecycle actions."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from typing import Any, Callable, Literal

from pydantic import ValidationError

from houmao.agents.realm_controller.gateway_models import (
    GatewayAttachBackendMetadataWebV1,
    GatewayWebAdmissionV1,
    GatewayWebControlStateV1,
    GatewayWebExecutionIdentityV1,
    GatewayWebHistoryEntryV1,
    GatewayWebHistoryV1,
    GatewayWebInputClaimV1,
)

_PUBLIC_HISTORY_FIELDS = frozenset(
    {
        "native_sequence",
        "turn",
        "turn_start_sequence",
        "message_id",
        "operation_id",
        "result",
        "status",
        "placement",
        "operator",
        "admission_policy",
        "input_ids",
        "turns",
        "mixed_input",
    }
)


def web_state_is_fresh(state: GatewayWebControlStateV1, *, max_age_seconds: float = 5.0) -> bool:
    """Require a recent, timezone-qualified native observation."""

    try:
        observed = datetime.fromisoformat(state.observed_at_utc.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            return False
        age = (datetime.now(UTC) - observed).total_seconds()
        return -2.0 <= age <= max_age_seconds
    except ValueError:
        return False


class WebObservation:
    """Reconcile native history and pending interactions around fresh snapshots."""

    def __init__(
        self,
        *,
        metadata: GatewayAttachBackendMetadataWebV1,
        state: Callable[[], dict[str, Any]],
        history: Callable[..., dict[str, Any]],
        retention: int = 100,
        source: Literal["gateway", "direct"] = "direct",
    ) -> None:
        """Bind read-only callbacks to one exact owned Web incarnation."""

        self.m_metadata: GatewayAttachBackendMetadataWebV1 = metadata
        self.m_read_state: Callable[[], dict[str, Any]] = state
        self.m_read_history: Callable[..., dict[str, Any]] = history
        self.m_retention: int = max(1, min(retention, 500))
        self.m_source: Literal["gateway", "direct"] = source
        self.m_entries: deque[GatewayWebHistoryEntryV1] = deque(maxlen=self.m_retention)
        self.m_sequence: int | None = None
        self.m_reconciled: bool = False
        self.m_current: GatewayWebControlStateV1 | None = None

    def refresh(self) -> GatewayWebControlStateV1:
        """Read native state and pending interactions without activating an agent."""

        try:
            payload = self.m_read_state()
            if type(payload.get("protocol_version")) is not int or payload["protocol_version"] != 1:
                raise ValueError("Incompatible Web observation protocol")
            identity = GatewayWebExecutionIdentityV1.model_validate(payload["identity"])
            if identity != self.m_metadata.identity:
                raise ValueError("Web execution identity changed")
            available = payload["available"]
            if type(available) is not bool:
                raise ValueError("Unknown native availability")
            # Every field is required even when empty: missing native facts
            # cannot be interpreted as idle, unblocked, or no pending input.
            state = GatewayWebControlStateV1(
                identity=identity,
                origin=self.m_metadata.origin,
                browser_url=self.m_metadata.browser_url,
                availability="available" if available else "unavailable",
                control_available=True,
                host_process_alive=True,
                native_agent_live=available,
                observed_at_utc=payload["observed_at_utc"],
                sequence=payload["sequence"],
                cursor=payload["cursor"],
                active_turn=payload["active_turn"],
                last_turn=payload["last_turn"],
                pending_inbox=payload["pending_inbox"],
                interaction_waits=payload["interaction_waits"],
                admission=payload["admission"] if available else GatewayWebAdmissionV1(),
                model=payload["model"],
                can_accept_prompt_now=available and payload["admission"]["ready_only"],
                source=self.m_source,
            )
            if not web_state_is_fresh(state):
                raise ValueError("Native Web state is stale")
            self._reconcile_history(state)
            if not self.m_reconciled:
                raise ValueError("Native Web history has an unreconciled sequence gap")
            claims: list[GatewayWebInputClaimV1] = []
            origins: dict[int, set[bool]] = {}
            for entry in self.m_entries:
                if entry.event != "inbox/claimed":
                    continue
                message_id = entry.metadata.get("message_id")
                operation_id = entry.metadata.get("operation_id")
                turn = entry.metadata.get("turn")
                if not isinstance(message_id, str) or type(turn) is not int:
                    continue
                if operation_id is not None and not isinstance(operation_id, str):
                    continue
                claims.append(
                    GatewayWebInputClaimV1(
                        message_id=message_id,
                        operation_id=operation_id,
                        turn=turn,
                    )
                )
                origins.setdefault(turn, set()).add(operation_id is not None)
            state = state.model_copy(
                update={
                    "input_claims": claims,
                    "observed_mixed_input_turns": sorted(
                        turn for turn, kinds in origins.items() if len(kinds) > 1
                    ),
                }
            )
            self.m_current = state
        except (OSError, RuntimeError, ValueError, KeyError, TypeError, ValidationError):
            self.m_reconciled = False
            self.m_current = self.unavailable()
        return self.m_current

    def unavailable(self) -> GatewayWebControlStateV1:
        """Close all admission when authenticated native authority is unavailable."""

        return GatewayWebControlStateV1(
            identity=self.m_metadata.identity,
            origin=self.m_metadata.origin,
            browser_url=self.m_metadata.browser_url,
            availability="unavailable",
            observed_at_utc=datetime.now(UTC).isoformat(),
            sequence=self.m_sequence or 0,
            cursor=-1,
            source=self.m_source,
            diagnostics=["Verified fresh native Web authority is unavailable."],
        )

    def history(self, *, limit: int = 100) -> GatewayWebHistoryV1:
        """Return bounded native transitions in most-recent-first order."""

        return GatewayWebHistoryV1(
            identity=self.m_metadata.identity,
            sequence=self.m_sequence or 0,
            entries=list(reversed(self.m_entries))[: max(0, min(limit, 500))],
            has_more=len(self.m_entries) > limit,
            reconciled=self.m_reconciled,
        )

    def _reconcile_history(self, state: GatewayWebControlStateV1) -> None:
        """Fill sequence gaps from read-only native history and ignore repeats."""

        initial = self.m_sequence is None
        pending: list[GatewayWebHistoryEntryV1] = []
        after = self.m_sequence if self.m_sequence is not None else -1
        if not initial and state.sequence < after:
            raise ValueError("Native observation sequence regressed")
        if not initial and state.sequence == after:
            self.m_reconciled = True
            return
        for _ in range(20):
            page = self.m_read_history(after_sequence=after, limit=self.m_retention)
            if not initial and page.get("truncated", False):
                raise ValueError("Native history retention gap")
            if GatewayWebExecutionIdentityV1.model_validate(page["identity"]) != state.identity:
                raise ValueError("Native history identity changed")
            entries = page["entries"]
            if not isinstance(entries, list):
                raise ValueError("Unknown native history")
            for raw in entries:
                if not isinstance(raw, dict):
                    raise ValueError("Invalid native history entry")
                named = {
                    key: raw[key] for key in ("sequence", "event", "observed_at_utc", "identity")
                }
                named["metadata"] = {
                    key: value for key, value in raw.items() if key in _PUBLIC_HISTORY_FIELDS
                }
                entry = GatewayWebHistoryEntryV1.model_validate(named)
                if entry.identity != state.identity:
                    raise ValueError("Native transition identity changed")
                if entry.sequence <= after:
                    continue
                if not initial and entry.sequence != after + 1:
                    raise ValueError("Native history sequence gap")
                pending.append(entry)
                after = entry.sequence
            if not page.get("has_more", False):
                # A baseline can start after bounded retention. Subsequent
                # updates require complete continuity from that baseline.
                if initial and not entries and page.get("sequence") == state.sequence:
                    after = state.sequence
                if after < state.sequence:
                    raise ValueError("Native history did not reach the snapshot")
                self.m_sequence = after
                merged = {entry.sequence: entry for entry in self.m_entries}
                merged.update({entry.sequence: entry for entry in pending})
                self.m_entries.clear()
                self.m_entries.extend(merged[key] for key in sorted(merged)[-self.m_retention :])
                self.m_reconciled = True
                return
            initial = False
        raise ValueError("Native history reconciliation exceeded its bound")
