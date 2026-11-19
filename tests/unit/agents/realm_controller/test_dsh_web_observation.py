"""Hermetic native Web projection and freshness regressions."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from houmao.agents.realm_controller.gateway_models import (
    GatewayAttachBackendMetadataWebV1,
    GatewayWebExecutionIdentityV1,
)
from houmao.agents.realm_controller.web_observation import WebObservation


def _metadata() -> GatewayAttachBackendMetadataWebV1:
    """Build credential-free synthetic authority for one exact execution."""

    return GatewayAttachBackendMetadataWebV1(
        origin="http://127.0.0.1:43123",
        browser_url="http://127.0.0.1:43123",
        identity=GatewayWebExecutionIdentityV1(
            agent_id="owner",
            runtime_session_id="runtime",
            generation="generation",
            host_incarnation="host",
            native_session_id="native",
            agent_incarnation="body",
        ),
    )


def _state(sequence: int = 1) -> dict[str, Any]:
    """Represent every required native fact, including genuinely empty pending state."""

    return {
        "protocol_version": 1,
        "identity": _metadata().identity.model_dump(),
        "observed_at_utc": datetime.now(UTC).isoformat(),
        "sequence": sequence,
        "cursor": 10,
        "available": True,
        "active_turn": None,
        "last_turn": None,
        "pending_inbox": [],
        "interaction_waits": [],
        "admission": {"ready_only": True, "if_no_pending": True, "always": True, "reason": None},
        "model": {"provider": "controlled", "model": "first", "reasoning_effort": None},
    }


def _entry(sequence: int, event: str = "state_changed") -> dict[str, Any]:
    """Create a metadata-only native transition."""

    return {
        "sequence": sequence,
        "event": event,
        "identity": _metadata().identity.model_dump(),
        "observed_at_utc": datetime.now(UTC).isoformat(),
        "native_sequence": 10 + sequence,
    }


def _page(*sequences: int) -> dict[str, Any]:
    """Return one inclusive native history page."""

    return {
        "identity": _metadata().identity.model_dump(),
        "sequence": max(sequences, default=1),
        "entries": [_entry(sequence) for sequence in sequences],
        "has_more": False,
        "truncated": False,
    }


def test_native_web_baseline_gap_reconciliation_and_repeats_keep_bounded_identity() -> None:
    """A fresh snapshot reconciles missing transitions and never duplicates repeats."""

    payload = _state()
    history = Mock(side_effect=[_page(1), _page(2, 3)])
    observer = WebObservation(
        metadata=_metadata(), state=lambda: deepcopy(payload), history=history, retention=2
    )
    assert observer.refresh().can_accept_prompt_now
    payload["sequence"] = 3
    payload["active_turn"] = {"turn": 4, "start_sequence": 17}
    payload["admission"]["ready_only"] = False
    payload["model"]["model"] = "browser-selected"
    active = observer.refresh()
    assert active.active_turn is not None and active.active_turn.start_sequence == 17
    assert active.model is not None and active.model.model == "browser-selected"
    assert not active.can_accept_prompt_now
    observer.refresh()
    assert history.call_count == 2
    assert [entry.sequence for entry in observer.history().entries] == [3, 2]
    assert all(entry.identity == _metadata().identity for entry in observer.history().entries)
    assert "editing_input" not in active.model_dump_json()


@pytest.mark.parametrize(
    "damage", ["stale", "generation", "missing_pending", "unknown_available", "credential_revoked"]
)
def test_native_web_unknown_or_stale_authority_never_retains_idle_readiness(damage: str) -> None:
    """Native authority loss replaces prior ready facts with explicit unavailable state."""

    payload = _state()
    read_state = Mock(side_effect=lambda: deepcopy(payload))
    observer = WebObservation(metadata=_metadata(), state=read_state, history=lambda **_: _page(1))
    assert observer.refresh().can_accept_prompt_now
    if damage == "stale":
        payload["observed_at_utc"] = (datetime.now(UTC) - timedelta(seconds=30)).isoformat()
    elif damage == "generation":
        payload["identity"]["generation"] = "replacement"
    elif damage == "missing_pending":
        del payload["pending_inbox"]
    elif damage == "unknown_available":
        payload["available"] = None
    else:
        read_state.side_effect = RuntimeError("private credential error")
    unavailable = observer.refresh()
    assert unavailable.availability == "unavailable"
    assert not unavailable.can_accept_prompt_now
    assert not any(
        (
            unavailable.admission.ready_only,
            unavailable.admission.if_no_pending,
            unavailable.admission.always,
        )
    )
    assert "private" not in unavailable.model_dump_json()
    assert not observer.history().reconciled


def test_native_interactions_refresh_without_state_sequence_or_browser_draft_invention() -> None:
    """Pending-event changes close admission even when the native state cursor repeats."""

    payload = _state()
    observer = WebObservation(
        metadata=_metadata(), state=lambda: deepcopy(payload), history=lambda **_: _page(1)
    )
    assert observer.refresh().can_accept_prompt_now
    payload["interaction_waits"] = ["approval", "question"]
    payload["admission"] = {
        "ready_only": False,
        "if_no_pending": False,
        "always": True,
        "reason": "interaction",
    }
    blocked = observer.refresh()
    assert blocked.interaction_waits == ["approval", "question"]
    assert not blocked.can_accept_prompt_now
    payload["interaction_waits"] = []
    payload["admission"] = _state()["admission"]
    assert observer.refresh().can_accept_prompt_now


def test_kimi_sparse_web_history_requires_a_verified_prior_offset() -> None:
    """Journal byte offsets can skip rows while the previous transition stays covered."""

    payload = _state(sequence=100)
    page = _page(100)
    observer = WebObservation(
        metadata=_metadata(),
        state=lambda: deepcopy(payload),
        history=lambda **_: deepcopy(page),
        sparse_history=True,
    )
    assert observer.refresh().can_accept_prompt_now
    payload["sequence"] = 204
    page = _page(204)
    page["previous_sequence"] = 93
    assert observer.refresh().availability == "unavailable"
    assert [item.sequence for item in observer.history().entries] == [100]
    page["previous_sequence"] = 100
    assert observer.refresh().can_accept_prompt_now
    assert [item.sequence for item in observer.history().entries] == [204, 100]


@pytest.mark.parametrize("gap", ["missing", "truncated", "replaced_row"])
def test_native_history_gap_or_rebinding_requires_verified_reconciliation(gap: str) -> None:
    """An unreconciled history gap closes readiness and commits no partial history."""

    payload = _state()
    page = _page(1)
    observer = WebObservation(
        metadata=_metadata(), state=lambda: deepcopy(payload), history=lambda **_: deepcopy(page)
    )
    observer.refresh()
    payload["sequence"] = 3
    page = _page(2, 3)
    if gap == "missing":
        page = _page(3)
    elif gap == "truncated":
        page["truncated"] = True
    else:
        page["entries"][1]["identity"]["agent_incarnation"] = "replacement"
    assert observer.refresh().availability == "unavailable"
    assert [entry.sequence for entry in observer.history().entries] == [1]
    page = _page(2, 3)
    assert observer.refresh().availability == "available"
    assert [entry.sequence for entry in observer.history().entries] == [3, 2, 1]


@pytest.mark.parametrize(
    "location",
    [
        "http://127.0.0.1:43123/?token=secret",
        "http://user:secret@127.0.0.1:43123",
        "https://public.example:443",
        "http://127.0.0.1",
    ],
)
def test_web_public_locations_reject_connection_credentials_and_remote_hosts(location: str) -> None:
    """Public inspection metadata cannot contain a private sign-in URL."""

    with pytest.raises(ValidationError):
        GatewayAttachBackendMetadataWebV1.model_validate(
            {
                **_metadata().model_dump(),
                "origin": location,
            }
        )


def test_native_history_projection_publishes_only_named_execution_metadata() -> None:
    """Unexpected native payload fields never enter public state history."""

    page = _page(1)
    page["entries"][0].update({"prompt": "private prompt", "cookie": "private credential"})
    observer = WebObservation(metadata=_metadata(), state=_state, history=lambda **_: page)
    assert observer.refresh().availability == "available"
    public = observer.history().model_dump_json()
    assert "native_sequence" in public
    assert "private" not in public and "cookie" not in public and '"prompt"' not in public


def test_native_input_claims_preserve_mixed_turn_and_separate_human_followup() -> None:
    """Native claims identify shared work without attributing a later human turn by wait timing."""

    page = _page(1, 2, 3, 4)
    for row, message_id, operation_id, turn in zip(
        page["entries"][1:],
        ["managed", "steer", "later"],
        ["operation", None, None],
        [5, 5, 6],
        strict=True,
    ):
        row.update(
            event="inbox/claimed", message_id=message_id, operation_id=operation_id, turn=turn
        )
    observer = WebObservation(
        metadata=_metadata(), state=lambda: _state(4), history=lambda **_: page
    )
    state = observer.refresh()
    assert [(claim.operation_id, claim.turn) for claim in state.input_claims] == [
        ("operation", 5),
        (None, 5),
        (None, 6),
    ]
    assert state.observed_mixed_input_turns == [5]
