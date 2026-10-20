"""Hermetic replay of the sanitized campaign fixtures against expected timelines.

Each fixture is derived from one 2026-10-20 Codex hook capture. The expected
timeline is parsed from the campaign's recorded zero-mismatch replay output
(``tmp/codex-hook-capture/replay-all-timeline.log``), so the production
normalizer and reducer are checked against the campaign's own expectations.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from houmao.hook_observation.codex_normalizer import CodexEventNormalizer
from houmao.hook_observation.models import HookEventEnvelope, HookObservation, HookPosture
from houmao.hook_observation.reducer import HookPostureReducer


FIXTURES = Path(__file__).parent / "fixtures" / "codex"
SCENARIOS = ("s1", "s3", "s4", "s5", "s6", "s7", "f1")
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

    normalizer: CodexEventNormalizer
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

    normalizer = CodexEventNormalizer()
    reducer = HookPostureReducer(adapter="codex")
    observations: list[HookObservation] = []
    postures: list[HookPosture] = []
    for envelope in _load_envelopes(scenario):
        observation = normalizer.normalize_envelope(envelope)
        observations.append(observation)
        postures.append(reducer.reduce(observation))
    final = reducer.finish()
    return _Replay(
        normalizer=normalizer,
        observations=tuple(observations),
        postures=tuple(postures),
        final=final,
    )


def _row(posture: HookPosture) -> dict[str, Any]:
    """Project one posture onto the campaign timeline columns."""

    return {
        "event": posture.last_event_name,
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
    assert final.work == final_expected["work"]
    assert final.generation == final_expected["generation"]
    assert final.settled is False

    counters_expected = final_expected["counters"]
    counters = final.counters
    assert counters.events_seen == counters_expected["events_seen"]
    assert counters.turn_epochs == counters_expected["turn_epochs"]
    assert counters.steer_events == counters_expected["steer_events"]
    assert counters.compaction_boundaries == counters_expected["compaction_boundaries"]
    assert counters.allow_settles == counters_expected["allow_settles"]
    assert counters.deny_settles == counters_expected["deny_settles"]
    assert counters.terminal_gaps == counters_expected["terminal_gaps"]
    assert counters.orphan_terminals == 0
    assert counters.duplicate_events == 0
    assert counters.unknown_events == 0
    assert counters.malformed_events == 0

    summary = replay.normalizer.summary
    assert list(summary.unavailable_families) == final_expected["unavailable_families"]
    assert summary.unknown_events == 0
    assert summary.malformed_events == 0


def test_s3_permission_pairing_and_deny_abort() -> None:
    replay = _replay("s3")
    summary = replay.normalizer.summary
    assert summary.permission_requests == 2
    assert summary.permission_pairings == 2
    assert summary.unpaired_permission_requests == 0
    assert summary.unpaired_post_tool_uses == 0

    allow_request = next(
        observation
        for observation in replay.observations
        if observation.event_name == "PermissionRequest"
    )
    assert allow_request.tool_use_id == "exec-c30a2560-0e8c-4406-89db-4473059e051b"

    blocked_rows = [posture for posture in replay.postures if posture.blocked]
    assert len(blocked_rows) == 2
    assert blocked_rows[0].blocked_tool_name == "Bash"
    assert blocked_rows[0].blocked_tool_use_id == "exec-c30a2560-0e8c-4406-89db-4473059e051b"
    assert blocked_rows[1].blocked_tool_use_id == "exec-eb6d114e-f359-48f5-8332-446e5aaa60d1"

    assert replay.final.terminal_result == "interrupted"
    assert replay.final.counters.allow_settles == 1
    assert replay.final.counters.deny_settles == 1
    assert replay.final.counters.terminal_gaps == 0


def test_f1_terminal_gap_is_truthful_unknown() -> None:
    replay = _replay("f1")

    assert replay.final.presence == "lost"
    assert replay.final.turn_phase == "unknown"
    assert replay.final.terminal_result == "none"
    assert replay.final.counters.terminal_gaps == 1
    assert any(item.kind == "hook_terminal_gap" for item in replay.final.diagnostics)


def test_s7_generation_and_resume_reset_turn_state() -> None:
    replay = _replay("s7")

    assert replay.final.generation == 2
    assert replay.final.session_id == "01a1578d-d1da-7bf3-bfa7-9d189aad60ce"
    assert replay.final.session_start_source == "resume"
    assert replay.final.counters.turn_epochs == 2

    resume_postures = [
        posture for posture in replay.postures if posture.last_event_name == "SessionStart"
    ]
    assert [posture.generation for posture in resume_postures] == [1, 2]
    assert resume_postures[1].presence == "present"
    assert resume_postures[1].turn_phase == "ready"
    assert resume_postures[1].terminal_result == "none"


def test_fixture_files_are_sanitized_and_credential_free() -> None:
    for scenario in SCENARIOS:
        text = (FIXTURES / f"{scenario}.ndjson").read_text(encoding="utf-8")
        assert "/data/" not in text
        assert "huangzhe" not in text
        assert "codex-hook-capture" not in text
        assert '"cwd": "/workdir"' in text
        assert '"transcript_path": "/codex-home/sessions/rollout-' in text
        for pattern in _CREDENTIAL_PATTERNS:
            assert pattern.search(text) is None, f"{scenario} matched {pattern.pattern}"
