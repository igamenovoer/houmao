"""Unit tests for the consumer-side hook event store reader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from houmao.hook_observation.reader import HookObservationChannel, HookObservationReader
from houmao.hook_observation.store import HookObservationStore


def _event(event_name: str, **extra: object) -> dict[str, object]:
    return {"hook_event_name": event_name, **extra}


def test_reader_resumes_from_byte_offset(tmp_path: Path) -> None:
    store = HookObservationStore(tmp_path, generation=1)
    reader = HookObservationReader(store.events_path)

    first = reader.read_new()
    assert [observation.kind for observation in first.observations] == ["generation_started"]
    assert first.current_generation == 1
    assert first.retried_partial_line is False

    store.append_event(_event("UserPromptSubmit", prompt_id="p1"))
    second = reader.read_new()
    assert [observation.kind for observation in second.observations] == ["prompt_submitted"]
    assert second.observations[0].prompt_id == "p1"

    third = reader.read_new()
    assert third.observations == ()

    store.append_event(_event("Stop", prompt_id="p1"))
    fourth = reader.read_new()
    assert [observation.kind for observation in fourth.observations] == ["turn_completed"]
    assert reader.offset == store.events_path.stat().st_size


def test_reader_retries_unterminated_final_line(tmp_path: Path) -> None:
    store = HookObservationStore(tmp_path, generation=1)
    reader = HookObservationReader(store.events_path)
    reader.read_new()

    with store.events_path.open("ab") as handle:
        handle.write(b'{"sequence": 99, "received_at_utc": "2026-10-19T13:00:00+00:00", ')
    partial_offset = reader.offset

    partial = reader.read_new()
    assert partial.observations == ()
    assert partial.retried_partial_line is True
    assert reader.offset == partial_offset

    with store.events_path.open("ab") as handle:
        handle.write(
            b'"channel_generation": 1, "via": "http", '
            b'"provider_event": {"hook_event_name": "UserPromptSubmit", "prompt_id": "p9"}}\n'
        )
    completed = reader.read_new()
    assert [observation.kind for observation in completed.observations] == ["prompt_submitted"]
    assert completed.observations[0].prompt_id == "p9"
    assert completed.retried_partial_line is False


def test_reader_filters_older_generations_on_fresh_scan(tmp_path: Path) -> None:
    store = HookObservationStore(tmp_path, generation=1)
    store.append_event(_event("UserPromptSubmit", prompt_id="old"))
    store.begin_generation(2)
    store.append_event(_event("UserPromptSubmit", prompt_id="new"))

    reader = HookObservationReader(store.events_path)
    batch = reader.read_new()

    assert batch.current_generation == 2
    assert [observation.kind for observation in batch.observations] == [
        "generation_started",
        "prompt_submitted",
    ]
    assert batch.observations[-1].prompt_id == "new"
    assert batch.dropped_old_generation_lines == 2


def test_reader_filters_older_generations_on_incremental_read(tmp_path: Path) -> None:
    store = HookObservationStore(tmp_path, generation=1)
    store.append_event(_event("UserPromptSubmit", prompt_id="old"))
    reader = HookObservationReader(store.events_path)
    reader.read_new()

    store.begin_generation(2)
    store.append_event(_event("UserPromptSubmit", prompt_id="new"))
    batch = reader.read_new()

    assert batch.current_generation == 2
    assert [observation.kind for observation in batch.observations] == [
        "generation_started",
        "prompt_submitted",
    ]
    assert batch.observations[-1].prompt_id == "new"


def test_reader_counts_garbage_and_invalid_lines(tmp_path: Path) -> None:
    store = HookObservationStore(tmp_path, generation=1)
    with store.events_path.open("ab") as handle:
        handle.write(b"not json\n")
        handle.write(b'{"channel_generation": "one"}\n')
        handle.write(b"\n")

    reader = HookObservationReader(store.events_path)
    batch = reader.read_new()

    assert [observation.kind for observation in batch.observations] == ["generation_started"]
    assert batch.skipped_garbage_lines == 1
    assert batch.skipped_invalid_lines == 1
    assert batch.skipped_blank_lines == 1


def test_reader_rescans_after_truncation(tmp_path: Path) -> None:
    store = HookObservationStore(tmp_path, generation=1)
    reader = HookObservationReader(store.events_path)
    reader.read_new()

    store.events_path.write_text("", encoding="utf-8")
    store.append_event(_event("UserPromptSubmit", prompt_id="after-truncate"))
    batch = reader.read_new()

    assert [observation.kind for observation in batch.observations] == ["prompt_submitted"]
    assert batch.observations[0].prompt_id == "after-truncate"


def _write_kimi_events(events_path: Path, *provider_events: dict[str, object]) -> None:
    lines = [
        json.dumps(
            {
                "sequence": index,
                "received_at_utc": f"2026-10-20T13:00:{index:02d}+00:00",
                "channel_generation": 1,
                "via": "http",
                "provider_event": provider_event,
            }
        )
        for index, provider_event in enumerate(provider_events, start=1)
    ]
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_reader_selects_the_kimi_normalizer(tmp_path: Path) -> None:
    events_path = tmp_path / "events.ndjson"
    _write_kimi_events(
        events_path,
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "session-1",
            "prompt": [{"type": "text", "text": "Reply with exactly: OK"}],
            "is_steer": False,
        },
        {
            "hook_event_name": "TurnStarted",
            "session_id": "session-1",
            "turn_id": 0,
            "origin_kind": "user",
        },
        {
            "hook_event_name": "UserPromptQueued",
            "session_id": "session-1",
            "prompt_id": "msg_1",
            "queue_length": 1,
        },
    )

    reader = HookObservationReader(events_path, adapter="kimi")
    batch = reader.read_new()

    assert reader.adapter == "kimi"
    assert [observation.kind for observation in batch.observations] == [
        "prompt_submitted",
        "turn_started",
        "prompt_queued",
    ]
    assert batch.observations[0].prompt_text == "Reply with exactly: OK"
    assert batch.observations[1].turn_id == "0"
    assert batch.observations[2].queue_length == 1

    claude_reader = HookObservationReader(events_path, adapter="claude")
    claude_batch = claude_reader.read_new()
    assert [observation.kind for observation in claude_batch.observations] == [
        "prompt_submitted",
        "unknown",
        "unknown",
    ]


def test_reader_rejects_an_unsupported_adapter(tmp_path: Path) -> None:
    events_path = tmp_path / "events.ndjson"
    events_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported hook observation adapter"):
        HookObservationReader(events_path, adapter="other")  # type: ignore[arg-type]


def test_channel_from_session_root_supports_the_kimi_adapter(tmp_path: Path) -> None:
    channel_dir = tmp_path / "hook-observation" / "kimi"
    channel_dir.mkdir(parents=True)
    (channel_dir / "channel.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "running",
                "generation": 1,
                "started_at_utc": "2026-10-20T13:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    _write_kimi_events(
        channel_dir / "events.ndjson",
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "session-1",
            "prompt": [{"type": "text", "text": "OK"}],
            "is_steer": False,
        },
        {
            "hook_event_name": "TurnStarted",
            "session_id": "session-1",
            "turn_id": 0,
            "origin_kind": "user",
        },
    )

    channel = HookObservationChannel.from_session_root(tmp_path, adapter="kimi")
    assert channel is not None
    assert channel.adapter == "kimi"
    assert channel.events_path == channel_dir / "events.ndjson"

    cycle = channel.read_cycle(
        now_monotonic=0.0,
        now_utc="2026-10-20T13:00:00+00:00",
        tui_changed=False,
    )
    assert [observation.kind for observation in cycle.observations] == [
        "prompt_submitted",
        "turn_started",
    ]

    posture = None
    for observation in cycle.observations:
        posture = channel.reducer.reduce(observation)
    assert posture is not None
    assert posture.turn_phase == "active"
    assert posture.turn_id == "0"


def test_channel_from_session_root_requires_channel_status(tmp_path: Path) -> None:
    assert HookObservationChannel.from_session_root(None) is None
    assert HookObservationChannel.from_session_root(tmp_path) is None

    store = HookObservationStore(tmp_path, generation=1)
    channel = HookObservationChannel.from_session_root(tmp_path)
    assert channel is not None
    cycle = channel.read_cycle(
        now_monotonic=0.0, now_utc="2026-10-19T13:00:00+00:00", tui_changed=False
    )
    assert cycle.health.state == "active"
    assert [observation.kind for observation in cycle.observations] == ["generation_started"]
    assert store.channel_path.is_file()


def test_channel_from_session_root_ignores_unreadable_status(tmp_path: Path) -> None:
    channel_dir = tmp_path / "hook-observation" / "claude"
    channel_dir.mkdir(parents=True)
    (channel_dir / "channel.json").write_text("{not json", encoding="utf-8")

    assert HookObservationChannel.from_session_root(tmp_path) is None


def test_channel_honors_install_unavailable_over_stopped_liveness_status(
    tmp_path: Path,
) -> None:
    store = HookObservationStore(tmp_path, generation=1)
    status = json.loads(store.channel_path.read_text(encoding="utf-8"))
    status["status"] = "stopped"
    status["channel_state"] = "unavailable"
    status["install"] = {"detail": "settings conflict"}
    store.channel_path.write_text(json.dumps(status), encoding="utf-8")

    channel = HookObservationChannel.from_session_root(tmp_path)
    assert channel is not None
    cycle = channel.read_cycle(
        now_monotonic=0.0,
        now_utc="2026-10-19T13:00:00+00:00",
        tui_changed=False,
    )

    assert cycle.health.state == "unavailable"
    assert cycle.health.detail == "settings conflict"


def test_channel_reports_disabled_state_without_reading_events(tmp_path: Path) -> None:
    store = HookObservationStore(tmp_path, generation=1)
    store.append_event(_event("UserPromptSubmit", prompt_id="ignored"))
    status = json.loads(store.channel_path.read_text(encoding="utf-8"))
    status["state"] = "disabled_by_policy"
    store.channel_path.write_text(json.dumps(status), encoding="utf-8")

    channel = HookObservationChannel.from_session_root(tmp_path)
    assert channel is not None
    cycle = channel.read_cycle(
        now_monotonic=0.0,
        now_utc="2026-10-19T13:00:00+00:00",
        tui_changed=False,
    )

    assert cycle.health.state == "disabled_by_policy"
    assert cycle.observations == ()


def _write_collector_record(
    *,
    directory: Path,
    status: str = "stopped",
    generation: int = 1,
) -> None:
    payload = {
        "schema_version": 1,
        "status": status,
        "pid": 999999,
        "port": 43123,
        "generation": generation,
        "started_at_utc": "2026-10-19T13:00:00+00:00",
        "stopped_at_utc": ("2026-10-19T13:00:10+00:00" if status == "stopped" else None),
    }
    (directory / "collector.json").write_text(json.dumps(payload), encoding="utf-8")


def test_collector_stop_record_degrades_channel_without_tui_change(tmp_path: Path) -> None:
    store = HookObservationStore(tmp_path, generation=1)
    channel = HookObservationChannel.from_session_root(tmp_path)
    assert channel is not None
    active = channel.read_cycle(
        now_monotonic=0.0,
        now_utc="2026-10-19T13:00:00+00:00",
        tui_changed=False,
    )
    assert active.health.state == "active"

    _write_collector_record(directory=store.directory)
    stopped = channel.read_cycle(
        now_monotonic=1.0,
        now_utc="2026-10-19T13:00:01+00:00",
        tui_changed=False,
    )

    assert stopped.health.state == "stopped"
    assert stopped.health.detail == "The hook observation collector is stopped."


def test_collector_stop_record_from_older_generation_is_ignored(tmp_path: Path) -> None:
    store = HookObservationStore(tmp_path, generation=2)
    _write_collector_record(directory=store.directory, generation=1)

    channel = HookObservationChannel.from_session_root(tmp_path)
    assert channel is not None
    cycle = channel.read_cycle(
        now_monotonic=0.0,
        now_utc="2026-10-19T13:00:00+00:00",
        tui_changed=False,
    )

    assert cycle.health.state == "active"


def test_launch_unavailable_wins_over_stopped_collector(tmp_path: Path) -> None:
    store = HookObservationStore(tmp_path, generation=1)
    status = json.loads(store.channel_path.read_text(encoding="utf-8"))
    status["status"] = "stopped"
    status["channel_state"] = "unavailable"
    status["install"] = {"detail": "settings conflict"}
    store.channel_path.write_text(json.dumps(status), encoding="utf-8")
    _write_collector_record(directory=store.directory)

    channel = HookObservationChannel.from_session_root(tmp_path)
    assert channel is not None
    cycle = channel.read_cycle(
        now_monotonic=0.0,
        now_utc="2026-10-19T13:00:00+00:00",
        tui_changed=False,
    )

    assert cycle.health.state == "unavailable"
    assert cycle.health.detail == "settings conflict"
