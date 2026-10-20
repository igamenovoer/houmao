"""Unit tests for the append-only hook observation store."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

import houmao.hook_observation.store as store_module
from houmao.hook_observation.normalizer import normalize_envelope
from houmao.hook_observation.reducer import HookPostureReducer
from houmao.hook_observation.store import (
    ADAPTER_DIRNAMES,
    HookObservationStore,
    parse_envelope_line,
    read_store,
)


SAMPLE_EVENTS = (
    Path(__file__).resolve().parents[3]
    / "tmp"
    / "hook-capture"
    / "s1"
    / "run-20261019T131758Z"
    / "collector"
    / "events.ndjson"
)


def _session_start_payload(prompt: str = "SECRET_PROMPT") -> dict[str, object]:
    return {
        "hook_event_name": "SessionStart",
        "session_id": "3ea6b6c9-9a63-492c-8044-5c3ed201d0ed",
        "source": "startup",
        "model": "deepseek-flash[1m]",
        "cwd": "/tmp/workdir",
        "transcript_path": "/tmp/transcript.jsonl",
        "prompt": prompt,
    }


def test_append_event_writes_private_store_and_secret_free_status(tmp_path: Path) -> None:
    store = HookObservationStore(tmp_path, generation=1)
    envelope = store.append_event(
        _session_start_payload(),
        via="http",
        received_at_utc="2026-10-19T13:17:58+00:00",
    )

    assert envelope.sequence == 1
    assert envelope.channel_generation == 1
    assert envelope.via == "http"
    assert envelope.event_name == "SessionStart"

    lines = store.events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    boundary = json.loads(lines[0])
    assert boundary["record_type"] == "generation_boundary"
    assert boundary["sequence"] is None
    assert boundary["channel_generation"] == 1
    event = json.loads(lines[1])
    assert event["sequence"] == 1
    assert event["provider_event"]["hook_event_name"] == "SessionStart"
    assert event["received_at_utc"] == "2026-10-19T13:17:58+00:00"

    assert stat.S_IMODE(store.events_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(store.channel_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(store.directory.stat().st_mode) == 0o700
    assert stat.S_IMODE((tmp_path / "hook-observation").stat().st_mode) == 0o700

    channel = json.loads(store.channel_path.read_text(encoding="utf-8"))
    assert channel["status"] == "running"
    assert channel["generation"] == 1
    assert channel["last_sequence"] == 1
    assert channel["counts"]["accepted"] == 1
    assert channel["counts"]["generation_boundaries"] == 1
    assert channel["events_by_name"] == {"SessionStart": 1}
    serialized = json.dumps(channel)
    assert "SECRET_PROMPT" not in serialized
    assert "provider_event" not in channel
    assert not (store.directory / "channel.json.tmp").exists()


def test_sequence_resumes_and_equal_generation_does_not_duplicate_boundary(
    tmp_path: Path,
) -> None:
    first = HookObservationStore(tmp_path, generation=1)
    first.append_event({"hook_event_name": "SessionStart"})
    first.append_event({"hook_event_name": "UserPromptSubmit", "prompt_id": "p1"})

    resumed = HookObservationStore(tmp_path, generation=1)
    third = resumed.append_event({"hook_event_name": "Stop", "prompt_id": "p1"})
    assert third.sequence == 3
    assert resumed.begin_generation(1) is None

    result = read_store(resumed.events_path)
    boundaries = [item for item in result.envelopes if item.is_generation_boundary]
    events = [item for item in result.envelopes if not item.is_generation_boundary]
    assert len(boundaries) == 1
    assert [item.sequence for item in events] == [1, 2, 3]


def test_generation_rotation_appends_boundary_and_rejects_older_generation(
    tmp_path: Path,
) -> None:
    store = HookObservationStore(tmp_path, generation=1)
    store.append_event({"hook_event_name": "SessionStart"})

    boundary = store.begin_generation(2)
    assert boundary is not None
    assert boundary.is_generation_boundary
    assert boundary.channel_generation == 2
    assert boundary.sequence is None

    event = store.append_event({"hook_event_name": "SessionStart", "source": "resume"})
    assert event.channel_generation == 2
    assert event.sequence == 2

    channel = json.loads(store.channel_path.read_text(encoding="utf-8"))
    assert channel["generation"] == 2
    with pytest.raises(ValueError):
        store.begin_generation(1)

    result = read_store(store.events_path)
    assert [item.channel_generation for item in result.envelopes] == [1, 1, 2, 2]
    assert [item.is_generation_boundary for item in result.envelopes] == [
        True,
        False,
        True,
        False,
    ]


def test_read_store_skips_blank_garbage_oversized_invalid_and_incomplete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store_module, "MAX_ENVELOPE_LINE_BYTES", 512)
    store = HookObservationStore(tmp_path, generation=1)
    valid = json.dumps(
        {
            "sequence": 7,
            "received_at_utc": "2026-10-19T13:17:58+00:00",
            "channel_generation": 1,
            "via": "http",
            "provider_event": {"hook_event_name": "UserPromptSubmit"},
        },
        sort_keys=True,
    )
    garbage = "not json"
    invalid_shape = "123"
    invalid_generation = '{"channel_generation": "x"}'
    oversized = "{" + ("x" * 600) + "}"
    complete = "\n".join([valid, garbage, invalid_shape, invalid_generation, oversized, ""])
    with store.events_path.open("ab") as handle:
        handle.write(b"\n")
        handle.write(complete.encode("utf-8"))
        handle.write(b'{"channel_generation": 1')

    result = read_store(store.events_path)
    assert len(result.envelopes) == 2
    assert result.envelopes[0].is_generation_boundary
    assert result.envelopes[1].sequence == 7
    assert result.skipped_blank_lines == 1
    assert result.skipped_garbage_lines == 1
    assert result.skipped_invalid_lines == 2
    assert result.skipped_oversized_lines == 1
    assert result.skipped_incomplete_lines == 1


def test_parse_envelope_line_recognizes_generation_boundary_variants() -> None:
    canonical = parse_envelope_line(
        json.dumps(
            {
                "record_type": "generation_boundary",
                "sequence": None,
                "received_at_utc": "2026-10-19T13:17:58+00:00",
                "channel_generation": 2,
                "via": "http",
                "provider_event": {},
            }
        )
    )
    assert canonical.envelope is not None
    assert canonical.envelope.is_generation_boundary

    synthetic = parse_envelope_line(
        json.dumps(
            {
                "sequence": None,
                "received_at_utc": "2026-10-19T13:17:58+00:00",
                "channel_generation": 2,
                "via": "command",
                "provider_event": {"hook_event_name": "GenerationBoundary"},
            }
        )
    )
    assert synthetic.envelope is not None
    assert synthetic.envelope.is_generation_boundary

    collector_style = parse_envelope_line(
        json.dumps(
            {
                "record": "generation_boundary",
                "channel_generation": 3,
                "recorded_at_utc": "2026-10-19T13:17:58+00:00",
            }
        )
    )
    assert collector_style.envelope is not None
    assert collector_style.envelope.is_generation_boundary
    assert collector_style.envelope.received_at_utc == "2026-10-19T13:17:58+00:00"

    event = parse_envelope_line(
        json.dumps(
            {
                "sequence": 4,
                "received_at_utc": "2026-10-19T13:17:58+00:00",
                "channel_generation": 1,
                "via": "http",
                "provider_event": {"hook_event_name": "Stop"},
            }
        )
    )
    assert event.envelope is not None
    assert not event.envelope.is_generation_boundary


def test_store_resumes_a_collector_written_file(tmp_path: Path) -> None:
    directory = tmp_path / "hook-observation" / "claude"
    directory.mkdir(parents=True)
    events_path = directory / "events.ndjson"
    records = [
        {
            "record": "generation_boundary",
            "channel_generation": 1,
            "recorded_at_utc": "2026-10-19T13:17:58+00:00",
        },
        {
            "sequence": 1,
            "received_at_utc": "2026-10-19T13:17:58+00:00",
            "channel_generation": 1,
            "via": "http",
            "provider_event": {"hook_event_name": "SessionStart"},
        },
        {
            "sequence": 2,
            "received_at_utc": "2026-10-19T13:17:59+00:00",
            "channel_generation": 1,
            "via": "http",
            "provider_event": {"hook_event_name": "UserPromptSubmit", "prompt_id": "p1"},
        },
    ]
    events_path.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )

    store = HookObservationStore(tmp_path, generation=1)
    assert store.generation == 1
    assert store.next_sequence == 3
    appended = store.append_event({"hook_event_name": "Stop", "prompt_id": "p1"})

    assert appended.sequence == 3
    result = read_store(events_path)
    boundaries = [item for item in result.envelopes if item.is_generation_boundary]
    assert len(boundaries) == 1
    assert boundaries[0].channel_generation == 1
    assert [item.sequence for item in result.envelopes if not item.is_generation_boundary] == [
        1,
        2,
        3,
    ]

    observations = [normalize_envelope(item) for item in result.envelopes]
    assert [item.kind for item in observations] == [
        "generation_started",
        "session_started",
        "prompt_submitted",
        "turn_completed",
    ]
    reducer = HookPostureReducer()
    posture = reducer.posture
    for observation in observations:
        posture = reducer.reduce(observation)
    assert posture.terminal_result == "success"
    assert posture.armed_prompt_count == 0


def test_append_repairs_an_unterminated_final_line(tmp_path: Path) -> None:
    directory = tmp_path / "hook-observation" / "claude"
    directory.mkdir(parents=True)
    events_path = directory / "events.ndjson"
    record = {
        "sequence": 1,
        "received_at_utc": "2026-10-19T13:17:58+00:00",
        "channel_generation": 1,
        "via": "http",
        "provider_event": {"hook_event_name": "SessionStart"},
    }
    events_path.write_text(
        json.dumps(record) + "\n" + '{"channel_generation": 1',
        encoding="utf-8",
    )

    store = HookObservationStore(tmp_path, generation=1)
    appended = store.append_event({"hook_event_name": "Stop"})
    assert appended.sequence == 2

    result = read_store(events_path)
    assert [item.sequence for item in result.envelopes] == [1, 2]
    assert result.skipped_garbage_lines == 1


def test_channel_status_is_atomic_and_rejects_secret_fields(tmp_path: Path) -> None:
    store = HookObservationStore(tmp_path, generation=1)
    store.mark_running(port=33451)
    channel = json.loads(store.channel_path.read_text(encoding="utf-8"))
    assert channel["status"] == "running"
    assert channel["port"] == 33451

    store.write_channel_status(extra={"detail": "ready"})
    channel = json.loads(store.channel_path.read_text(encoding="utf-8"))
    assert channel["detail"] == "ready"
    assert not (store.directory / "channel.json.tmp").exists()

    with pytest.raises(ValueError):
        store.write_channel_status(extra={"token": "sekrit"})

    store.mark_stopped()
    channel = json.loads(store.channel_path.read_text(encoding="utf-8"))
    assert channel["status"] == "stopped"
    assert channel["stopped_at_utc"] is not None
    assert stat.S_IMODE(store.channel_path.stat().st_mode) == 0o600


def test_channel_status_failed_replace_keeps_previous_document(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = HookObservationStore(tmp_path, generation=1)
    original = store.channel_path.read_text(encoding="utf-8")

    def _fail_replace(source: object, destination: object) -> None:
        del source, destination
        raise OSError("simulated replace failure")

    monkeypatch.setattr(store_module.os, "replace", _fail_replace)
    with pytest.raises(OSError):
        store.mark_stopped()

    assert store.channel_path.read_text(encoding="utf-8") == original
    assert not (store.directory / "channel.json.tmp").exists()


def test_existing_store_files_are_tightened(tmp_path: Path) -> None:
    directory = tmp_path / "hook-observation" / "claude"
    directory.mkdir(parents=True)
    events_path = directory / "events.ndjson"
    record = {
        "sequence": 1,
        "received_at_utc": "2026-10-19T13:17:58+00:00",
        "channel_generation": 1,
        "via": "http",
        "provider_event": {"hook_event_name": "SessionStart"},
    }
    events_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    events_path.chmod(0o644)
    channel_path = directory / "channel.json"
    channel_path.write_text("{}", encoding="utf-8")
    channel_path.chmod(0o644)

    store = HookObservationStore(tmp_path, generation=1)

    assert stat.S_IMODE(events_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(channel_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert store.generation == 1
    assert store.next_sequence == 2
    assert len(read_store(events_path).envelopes) == 1


@pytest.mark.skipif(
    not SAMPLE_EVENTS.is_file(),
    reason="local campaign capture is not present",
)
def test_reads_real_captured_sample() -> None:
    result = read_store(SAMPLE_EVENTS)
    assert result.skipped_lines == 0
    assert [item.sequence for item in result.envelopes] == [1, 2, 3, 4, 5]
    assert [item.event_name for item in result.envelopes] == [
        "SessionStart",
        "UserPromptSubmit",
        "Stop",
        "UserPromptSubmit",
        "Stop",
    ]
    assert [item.channel_generation for item in result.envelopes] == [1, 1, 1, 1, 1]

    reducer = HookPostureReducer()
    observations = [normalize_envelope(item) for item in result.envelopes]
    assert [item.kind for item in observations] == [
        "session_started",
        "prompt_submitted",
        "turn_completed",
        "prompt_submitted",
        "turn_completed",
    ]
    posture = reducer.posture
    for observation in observations:
        posture = reducer.reduce(observation)
    assert posture.session_id == "3ea6b6c9-9a63-492c-8044-5c3ed201d0ed"
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "success"
    assert posture.work == "clear"
    assert posture.armed_prompt_count == 0
    assert posture.counters.orphan_terminals == 0


def test_kimi_adapter_uses_the_kimi_directory(tmp_path: Path) -> None:
    assert ADAPTER_DIRNAMES["kimi"] == "kimi"

    store = HookObservationStore(tmp_path, generation=1, adapter="kimi")
    store.append_event({"hook_event_name": "SessionStart"})

    assert store.directory == tmp_path / "hook-observation" / "kimi"
    assert store.events_path.is_file()
    assert store.channel_path.is_file()
    assert not (tmp_path / "hook-observation" / "claude").exists()
