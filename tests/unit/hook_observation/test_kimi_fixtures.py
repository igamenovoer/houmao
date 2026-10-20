"""Hermetic replay of the sanitized Kimi campaign fixtures.

Each fixture is derived from one 2026-10-20 Kimi Code hook capture. The
expected timeline is ported from the campaign's recorded zero-mismatch replay
output (``scripts/explore/kimi-hook-observation/replay_reduce.py``), so the
production normalizer and reducer are checked against the campaign's own
verdicts rather than against themselves.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from houmao.hook_observation.kimi_normalizer import KimiEventNormalizer
from houmao.hook_observation.models import HookEventEnvelope, HookObservation, HookPosture
from houmao.hook_observation.reducer import HookPostureReducer


FIXTURES = Path(__file__).parent / "fixtures" / "kimi"
SCENARIOS = ("s0", "s1", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "f1", "d1")
_CREDENTIAL_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"authorization", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
)


@dataclass(frozen=True)
class _Replay:
    """One fixture replay result."""

    normalizer: KimiEventNormalizer
    envelopes: tuple[HookEventEnvelope, ...]
    observations: tuple[HookObservation, ...]
    postures: tuple[HookPosture, ...]
    final: HookPosture


def _load_envelopes(scenario: str) -> list[HookEventEnvelope]:
    """Load one fixture as store envelopes in stream order."""

    envelopes: list[HookEventEnvelope] = []
    with (FIXTURES / f"{scenario}.ndjson").open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            envelopes.append(
                HookEventEnvelope(
                    received_at_utc=str(row["received_at_utc"]),
                    channel_generation=int(row["channel_generation"]),
                    via=row["via"],
                    provider_event=row["provider_event"],
                    sequence=row.get("sequence"),
                )
            )
    return envelopes


def _expected(scenario: str) -> dict[str, Any]:
    """Load one expected timeline document."""

    value = json.loads((FIXTURES / f"{scenario}.expected.json").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _replay(scenario: str) -> _Replay:
    """Normalize and reduce one fixture through the production channel code."""

    expected = _expected(scenario)
    finish = expected.get("finish", {})
    normalizer = KimiEventNormalizer()
    reducer = HookPostureReducer(adapter="kimi")
    envelopes = _load_envelopes(scenario)
    observations: list[HookObservation] = []
    postures: list[HookPosture] = []
    for envelope in envelopes:
        observation = normalizer.normalize_envelope(envelope)
        observations.append(observation)
        postures.append(reducer.reduce(observation))
    final = reducer.finish(
        headless=bool(finish.get("headless", False)),
        process_returncode=finish.get("process_returncode"),
    )
    return _Replay(
        normalizer=normalizer,
        envelopes=tuple(envelopes),
        observations=tuple(observations),
        postures=tuple(postures),
        final=final,
    )


def _row(posture: HookPosture) -> dict[str, Any]:
    """Project one posture onto the campaign timeline columns."""

    return {
        "event": posture.last_event_name,
        "turn_id": posture.turn_id,
        "presence": posture.presence,
        "turn_phase": posture.turn_phase,
        "blocked": posture.blocked,
        "maintenance_active": posture.maintenance_active,
        "last_turn_result": posture.terminal_result,
    }


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_fixture_matches_campaign_timeline(scenario: str) -> None:
    expected = _expected(scenario)
    replay = _replay(scenario)

    assert [observation.event_name for observation in replay.observations] == expected["events"]
    assert [_row(posture) for posture in replay.postures] == expected["rows"]

    final_expected = expected["final"]
    final = replay.final
    assert final.presence == final_expected["presence"]
    assert final.turn_phase == final_expected["turn_phase"]
    assert final.terminal_result == final_expected["last_turn_result"]
    if final_expected["last_turn_result"] != "none":
        assert final.terminal_source == "hook_observation"
    assert final.work == final_expected["work"]
    assert final.generation == final_expected["generation"]
    assert final.session_start_source == final_expected["session_start_source"]
    assert final.settled is False
    assert (
        len({envelope.channel_generation for envelope in replay.envelopes})
        == expected["generations"]
    )
    assert (
        sum(1 for envelope in replay.envelopes if envelope.via == "command_fallback")
        == (expected["fallback_events"])
    )

    counters_expected = final_expected["counters"]
    counters = final.counters
    for field, value in counters_expected.items():
        assert getattr(counters, field) == value, field
    assert counters.orphan_terminals == 0
    assert counters.duplicate_events == 0
    assert counters.unknown_events == 0
    assert counters.malformed_events == 0

    summary = replay.normalizer.summary
    assert list(summary.unavailable_families) == final_expected["unavailable_families"]
    assert summary.unknown_events == 0
    assert summary.malformed_events == 0

    diagnostic_kinds = {item.kind for item in final.diagnostics}
    for kind in final_expected["diagnostics_include"]:
        assert kind in diagnostic_kinds, kind


def test_s3_permission_pairing_and_deny_continuation() -> None:
    replay = _replay("s3")
    summary = replay.normalizer.summary
    assert summary.permission_requests == 2
    assert summary.permission_pairings == 2
    assert summary.unpaired_permission_requests == 0
    assert summary.unpaired_post_tool_uses == 0
    assert summary.tool_pairs == 2

    allow_request = next(
        observation
        for observation in replay.observations
        if observation.event_name == "PermissionRequest"
    )
    assert allow_request.tool_use_id == "tool_8IHFsvSl8v9sJ7a260y2kiOV"
    assert allow_request.turn_id == "0"

    # The allow window is held across PostToolUse, so it spans two timeline rows.
    blocked_rows = [posture for posture in replay.postures if posture.blocked]
    assert len(blocked_rows) == 3
    assert blocked_rows[0].blocked_tool_name == "Write"
    assert blocked_rows[0].blocked_tool_use_id == "tool_8IHFsvSl8v9sJ7a260y2kiOV"
    assert blocked_rows[1].blocked_tool_use_id == "tool_8IHFsvSl8v9sJ7a260y2kiOV"
    assert blocked_rows[2].blocked_tool_use_id == "tool_3pQqrH1B2oOahJClPSNG1w1U"

    assert replay.final.terminal_result == "success"
    assert replay.final.counters.allow_settles == 1
    assert replay.final.counters.deny_settles == 1
    assert replay.final.counters.interrupts == 0
    assert replay.final.counters.terminal_gaps == 0


def test_s3_allow_result_arrives_after_post_tool_use() -> None:
    replay = _replay("s3")
    names = [observation.event_name for observation in replay.observations]
    assert names.index("PostToolUse") < names.index("PermissionResult")

    post_tool_row = next(
        posture for posture in replay.postures if posture.last_event_name == "PostToolUse"
    )
    assert post_tool_row.turn_phase == "blocked"
    assert post_tool_row.blocked is True


def test_s5_interrupt_settles_interrupted_without_a_stop() -> None:
    replay = _replay("s5")
    assert replay.final.terminal_result == "interrupted"
    assert replay.final.counters.interrupts == 1
    assert replay.final.counters.terminal_gaps == 0
    assert "Stop" not in [observation.event_name for observation in replay.observations]

    interrupt = next(
        observation for observation in replay.observations if observation.event_name == "Interrupt"
    )
    assert interrupt.reason == "cancelled"
    assert interrupt.turn_id == "0"


def test_s4_compaction_holds_posture_and_mints_a_fresh_epoch() -> None:
    replay = _replay("s4")
    assert replay.final.counters.compaction_boundaries == 1
    assert replay.final.counters.turn_epochs == 2

    start_ids = [
        observation.turn_id
        for observation in replay.observations
        if observation.event_name == "TurnStarted"
    ]
    assert start_ids == ["0", "1"]

    compact_rows = [
        posture
        for posture in replay.postures
        if posture.last_event_name in ("PreCompact", "PostCompact")
    ]
    assert [posture.maintenance_active for posture in compact_rows] == [True, False]
    assert [posture.terminal_result for posture in compact_rows] == ["success", "success"]

    # Kimi emits no compaction-sourced session start.
    compact_index = next(
        index
        for index, posture in enumerate(replay.postures)
        if posture.last_event_name == "PreCompact"
    )
    assert "SessionStart" not in [
        posture.last_event_name for posture in replay.postures[compact_index:]
    ]


def test_s6_queued_input_does_not_open_a_second_turn() -> None:
    replay = _replay("s6")
    assert replay.final.counters.queued_prompts == 1
    assert replay.final.counters.turn_epochs == 1
    assert replay.final.counters.steer_events == 0
    assert replay.final.counters.heartbeats == 5
    assert replay.final.terminal_result == "success"

    queued = next(
        observation
        for observation in replay.observations
        if observation.event_name == "UserPromptQueued"
    )
    assert queued.kind == "prompt_queued"
    assert queued.prompt_id == "msg_01M5CRPZZM31SG8FVZVJAK8S1K"
    assert queued.queue_length == 1
    assert queued.turn_id is None

    queued_row = next(
        posture for posture in replay.postures if posture.last_event_name == "UserPromptQueued"
    )
    assert queued_row.turn_phase == "active"
    assert queued_row.turn_id == "0"


def test_s7_resume_continues_the_turn_counter_and_resets_turn_state() -> None:
    replay = _replay("s7")
    assert replay.final.generation == 2
    assert replay.final.counters.turn_epochs == 2
    assert replay.final.terminal_result == "success"
    assert replay.final.session_start_source == "resume"

    start_sources = [
        observation.source
        for observation in replay.observations
        if observation.event_name == "SessionStart"
    ]
    assert start_sources == ["startup", "resume"]
    turn_ids = [
        observation.turn_id
        for observation in replay.observations
        if observation.event_name == "TurnStarted"
    ]
    assert turn_ids == ["0", "1"]

    session_ids = {
        observation.session_id
        for observation in replay.observations
        if observation.session_id is not None
    }
    assert len(session_ids) == 1

    resume_start = next(
        posture
        for posture in replay.postures
        if posture.last_event_name == "SessionStart" and posture.generation == 2
    )
    assert resume_start.presence == "present"
    assert resume_start.turn_phase == "ready"
    assert resume_start.terminal_result == "none"
    assert resume_start.turn_id is None


def test_s8_headless_clean_exit_names_the_missing_session_end() -> None:
    replay = _replay("s8")
    assert replay.final.presence == "lost"
    assert replay.final.turn_phase == "ready"
    assert replay.final.terminal_result == "success"
    assert replay.final.counters.terminal_gaps == 0
    assert any(item.kind == "hook_headless_session_end_gap" for item in replay.final.diagnostics)
    assert "SessionEnd" not in [observation.event_name for observation in replay.observations]


def test_s9_nested_subagent_scope_does_not_mint_a_second_epoch() -> None:
    replay = _replay("s9")
    assert replay.final.counters.turn_epochs == 1
    assert replay.final.counters.subagent_starts == 1
    assert replay.final.counters.subagent_stops == 1
    assert replay.final.terminal_result == "success"

    nested_turn = next(
        observation
        for observation in replay.observations
        if observation.event_name == "TurnStarted" and observation.origin_name == "subagent"
    )
    assert nested_turn.origin_kind == "system_trigger"
    assert nested_turn.turn_id == "0"

    nested_stop_row = next(
        posture for posture in replay.postures if posture.last_event_name == "Stop"
    )
    assert nested_stop_row.turn_phase == "active"
    assert nested_stop_row.terminal_result == "none"
    assert nested_stop_row.turn_id == "0"
    assert any(item.kind == "hook_nested_scope_closed" for item in nested_stop_row.diagnostics)


def test_f1_terminal_gap_is_truthful_unknown() -> None:
    replay = _replay("f1")
    assert replay.final.presence == "lost"
    assert replay.final.turn_phase == "unknown"
    assert replay.final.terminal_result == "none"
    assert replay.final.counters.terminal_gaps == 1
    kinds = [item.kind for item in replay.final.diagnostics]
    assert "hook_terminal_gap" in kinds
    assert "hook_heartbeat_liveness_unavailable" in kinds


def test_d1_fallback_rows_replay_in_order() -> None:
    replay = _replay("d1")
    assert replay.final.terminal_result == "success"
    fallback = [
        observation
        for observation, envelope in zip(replay.observations, replay.envelopes, strict=True)
        if envelope.via == "command_fallback"
    ]
    assert [observation.event_name for observation in fallback] == [
        "UserPromptSubmit",
        "TurnStarted",
        "Stop",
        "SessionEnd",
    ]
    assert [observation.sequence for observation in fallback] == [None, None, None, None]
    assert replay.final.counters.turn_epochs == 1


def test_fixture_files_are_sanitized_and_credential_free() -> None:
    for scenario in SCENARIOS:
        text = (FIXTURES / f"{scenario}.ndjson").read_text(encoding="utf-8")
        assert "/data/" not in text
        assert "huangzhe" not in text
        assert "kimi-hook-capture" not in text
        assert "houmao-kimi-hook" not in text
        assert '"cwd": "/workdir"' in text
        for pattern in _CREDENTIAL_PATTERNS:
            assert pattern.search(text) is None, f"{scenario} matched {pattern.pattern}"
