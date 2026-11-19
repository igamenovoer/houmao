"""DSH v4 accounting regressions using synthetic native-format journal rows."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from houmao.agents.realm_controller.usage_adapters.common import UsageParseContext
from houmao.agents.realm_controller.usage_adapters.dsh import (
    DSH_JOURNAL_PROFILE,
    DSH_SOURCE_REVISION,
    DshJournalError,
    DshUsageAdapterState,
    configure_dsh_journal,
    encode_dsh_session_segment,
    inspect_dsh_journal,
    normalize_dsh_usage,
    parse_dsh,
    select_dsh_journal,
)
from houmao.agents.realm_controller.usage_extraction import assemble_usage_record
from houmao.agents.realm_controller.usage_collection import UsageCollector
from houmao.agents.realm_controller.usage_models import (
    UsageObservation,
    UsageSourceBinding,
    UsageTurnSnapshot,
)
from houmao.agents.realm_controller.usage_store import UsageStore
from houmao.agents.realm_controller.usage_support import UsageService, persist_terminal_evidence


def _header(**updates: Any) -> dict[str, Any]:
    """Build a current physical header with a fixed synthetic native identity."""

    return {
        "type": "session",
        "version": 4,
        "id": "native-1",
        "createdAt": 1000,
        "isSeeded": False,
        "delegationDepth": 0,
        "cwd": "/synthetic/workspace",
        **updates,
    }


def _row(seq: int, event: str, data: dict[str, Any]) -> dict[str, Any]:
    """Construct one physical event while retaining explicit native sequence identity."""

    return {"type": event, "seq": seq, "time": 1001 + seq, "data": data}


def _usage(**updates: Any) -> dict[str, Any]:
    """Build disjoint cache and uncached counters with one exact full-call total."""

    return {
        "inputTokens": 12,
        "outputTokens": 9,
        "cacheReadTokens": 5,
        "cacheWriteTokens": 0,
        "reasoningTokens": 3,
        "totalTokens": 26,
        **updates,
    }


def _message(seq: int, *, turn: int = 1, step: int = 1, **updates: Any) -> dict[str, Any]:
    """Create a native assistant settlement with deliberately private content."""

    return _row(
        seq,
        "assistant/message",
        {
            "turn": turn,
            "step": step,
            "usage": _usage(),
            "stream": [
                {"type": "chunk", "time": 1001 + seq, "chunk": {"type": "usage", "usage": _usage()}}
            ],
            "message": {
                "id": "private-message-id",
                "role": "assistant",
                "content": [{"type": "text", "text": "PRIVATE TRANSCRIPT API_KEY=secret"}],
                "source": {"kind": "model", "provider": "controlled", "model": "tiny-model"},
            },
            **updates,
        },
    )


def _parse(
    rows: list[dict[str, Any]],
    state: DshUsageAdapterState | None = None,
) -> tuple[DshUsageAdapterState, list[UsageObservation]]:
    """Feed physical rows through the parser with stable opaque source positions."""

    state = state or DshUsageAdapterState(provider="dsh", provider_session_id="native-1")
    result = []
    for offset, row in enumerate(rows):
        state.sequence += 1
        result.extend(
            parse_dsh(
                row,
                state,
                UsageParseContext(source_ref=f"source-{'a' * 24}:{offset}", turn_id="managed-1"),
            )
        )
    return state, result


def _snapshot() -> UsageTurnSnapshot:
    """Return the managed turn identity independent of its native root turns."""

    return UsageTurnSnapshot(
        runtime_session_id="runtime-1",
        turn_id="managed-1",
        agent_id="agent-1",
        provider="dsh",
        provider_session_id="native-1",
        backend="dsh_acp",
        generation_id="generation-1",
        coverage="complete",
    )


def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write a complete synthetic raw journal inside a pytest-owned directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def test_final_settlement_overrides_embedded_sample_and_charges_once() -> None:
    message = _message(2)
    message["data"]["stream"][0]["chunk"]["usage"] = _usage(inputTokens=4, totalTokens=18)
    state, observations = _parse(
        [
            _header(),
            _row(0, "turn/start", {"turn": 1}),
            _row(1, "step/start", {"turn": 1, "step": 1}),
            message,
            _row(3, "step/end", {"turn": 1, "step": 1}),
            _row(4, "turn/end", {"turn": 1, "reason": {"kind": "completed"}}),
        ]
    )
    requests = [item for item in observations if item.kind == "request"]
    assert len(requests) == 1
    assert requests[0].values["input_tokens"] == 12
    assert requests[0].values["total_tokens"] == 26
    assert requests[0].metadata["sample_authority"] == "message_usage"
    assert requests[0].model == "tiny-model"
    assert requests[0].profile_id == DSH_JOURNAL_PROFILE
    assert requests[0].provider_version is None
    record = assemble_usage_record(_snapshot(), observations, outcome="completed")
    assert record.token_usage.total_tokens.value == 26
    assert record.token_semantics.cached_input_included_in_input is False
    assert record.token_usage.reasoning_output_tokens.value == 3
    assert "PRIVATE TRANSCRIPT" not in record.model_dump_json()
    assert "API_KEY" not in json.dumps(state.model_dump(mode="json"))


def test_failed_attempt_and_billed_retry_have_distinct_request_identities() -> None:
    state, first = _parse(
        [
            _header(),
            _row(0, "turn/start", {"turn": 1}),
            _row(1, "step/start", {"turn": 1, "step": 1}),
            _row(
                2,
                "request/header",
                {
                    "header": {
                        "config": {
                            "provider": "controlled",
                            "model": "small-model",
                            "apiKey": "DO NOT RETAIN",
                            "headers": {"Authorization": "DO NOT RETAIN"},
                        }
                    }
                },
            ),
            _row(
                3,
                "assistant/attempt",
                {
                    "turn": 1,
                    "step": 1,
                    "stream": [
                        {
                            "type": "chunk",
                            "time": 1004,
                            "chunk": {"type": "usage", "usage": _usage()},
                        },
                        {
                            "type": "chunk",
                            "time": 1005,
                            "chunk": {
                                "type": "finish",
                                "reason": {"kind": "error"},
                            },
                        },
                    ],
                },
            ),
            _row(4, "llm/retry", {"turn": 1, "step": 1}),
        ]
    )
    # Restore through JSON exactly as the shared source checkpoint does.
    restored = DshUsageAdapterState.model_validate_json(state.model_dump_json())
    _, second = _parse(
        [
            _row(5, "llm/retry-started", {"turn": 1, "step": 1, "retry": 1}),
            _message(6),
            _row(7, "step/end", {"turn": 1, "step": 1}),
            _row(8, "turn/end", {"turn": 1, "reason": {"kind": "completed"}}),
        ],
        restored,
    )
    requests = [item for item in first + second if item.kind == "request"]
    assert len(requests) == len({item.request_id for item in requests}) == 2
    assert requests[0].model == "small-model"
    assert "DO NOT RETAIN" not in state.model_dump_json()
    record = assemble_usage_record(_snapshot(), first + second, outcome="completed")
    assert record.token_usage.total_tokens.value == 52


def test_missing_cache_bucket_keeps_aggregate_unavailable_and_zero_distinct() -> None:
    usage = _usage()
    del usage["cacheReadTokens"]
    del usage["totalTokens"]
    assert normalize_dsh_usage(usage) == {
        "input_tokens": 12,
        "output_tokens": 9,
        "cache_write_input_tokens": 0,
        "reasoning_output_tokens": 3,
    }
    _, observations = _parse(
        [
            _header(),
            _row(0, "turn/start", {"turn": 1}),
            _row(1, "step/start", {"turn": 1, "step": 1}),
            _message(2, usage=usage),
            _row(3, "step/end", {"turn": 1, "step": 1}),
            _row(4, "turn/end", {"turn": 1, "reason": {"kind": "completed"}}),
        ]
    )
    record = assemble_usage_record(_snapshot(), observations, outcome="completed")
    assert record.token_usage.total_tokens.value is None
    assert record.token_usage.cached_input_tokens.availability == "unavailable"
    assert record.token_usage.cache_write_input_tokens.value == 0


def test_total_is_derived_only_from_all_disjoint_buckets() -> None:
    usage = _usage()
    del usage["totalTokens"]
    _, observations = _parse(
        [
            _header(),
            _row(0, "turn/start", {"turn": 1}),
            _row(1, "step/start", {"turn": 1, "step": 1}),
            _message(2, usage=usage),
            _row(3, "step/end", {"turn": 1, "step": 1}),
            _row(4, "turn/end", {"turn": 1, "reason": {"kind": "completed"}}),
        ]
    )
    record = assemble_usage_record(_snapshot(), observations, outcome="completed")
    assert record.token_usage.total_tokens.value == 26
    assert record.token_usage.total_tokens.provenance is not None
    assert record.token_usage.total_tokens.provenance.rule == "provider_disjoint_token_buckets"


@pytest.mark.parametrize(
    "changes",
    [
        {"inputTokens": -1},
        {"outputTokens": True},
        {"cacheReadTokens": 1.5},
        {"cacheWriteTokens": "secret"},
        {"reasoningTokens": 10},
        {"totalTokens": 25},
        {"totalTokens": 27},
        {"totalTokens": 1 << 53},
        {"inputTokens": (1 << 53) - 1, "cacheReadTokens": 1},
    ],
)
def test_invalid_counter_or_contradictory_total_is_not_charged(changes: dict[str, Any]) -> None:
    with pytest.raises(DshJournalError):
        normalize_dsh_usage(_usage(**changes))
    _, observations = _parse(
        [
            _header(),
            _row(0, "turn/start", {"turn": 1}),
            _row(1, "step/start", {"turn": 1, "step": 1}),
            _message(2, usage=_usage(**changes)),
        ]
    )
    assert observations[-1].values == {}
    assert observations[-1].coverage == "unknown"


def test_context_occupancy_never_becomes_consumption() -> None:
    state = DshUsageAdapterState(provider="dsh")
    assert (
        parse_dsh(
            {"sessionUpdate": "usage_update", "used": 900, "size": 1000},
            state,
            UsageParseContext(source_ref="acp", source_kind="structured_output"),
        )
        == []
    )


def test_header_and_contiguous_sequence_are_required() -> None:
    with pytest.raises(DshJournalError, match="header_missing"):
        _parse([_row(0, "turn/start", {"turn": 1})])
    with pytest.raises(DshJournalError, match="sequence_discontinuous"):
        _parse([_header(), _row(1, "turn/start", {"turn": 1})])
    with pytest.raises(DshJournalError, match="format_unsupported"):
        _parse([_header(version=5)])
    with pytest.raises(DshJournalError, match="identity_mismatch"):
        _parse([_header(id="some-other-agent")])


def test_missing_settlement_usage_stays_unknown_on_native_interruption() -> None:
    message = _message(2)
    message["data"].pop("usage")
    message["data"]["stream"] = []
    _, observations = _parse(
        [
            _header(),
            _row(0, "turn/start", {"turn": 1}),
            _row(1, "step/start", {"turn": 1, "step": 1}),
            message,
            _row(3, "step/end", {"turn": 1, "step": 1}),
            _row(4, "turn/end", {"turn": 1, "reason": {"kind": "aborted"}}),
        ]
    )
    assert observations[-1].lifecycle == "interrupted"
    record = assemble_usage_record(_snapshot(), observations, outcome="interrupted")
    assert record.token_usage.input_tokens.value is None
    assert record.token_usage.total_tokens.value is None


def test_seeded_source_uses_last_tagged_cut_not_an_ancestor_marker(tmp_path: Path) -> None:
    path = tmp_path / "project" / "native-1" / "session.v4.jsonl"
    rows = [
        _header(isSeeded=True, parentSession="parent-1"),
        _row(0, "session/end-seed", {"inherited": True}),
        _row(1, "turn/start", {"turn": 1}),
        _row(2, "step/start", {"turn": 1, "step": 1}),
        _message(3),
        _row(4, "session/end-seed", {"inherited": True}),
        _row(5, "step/end", {"turn": 1, "step": 1}),
        _row(6, "turn/end", {"turn": 1, "reason": {"kind": "forked"}}),
        _row(7, "turn/start", {"turn": 2}),
        _row(8, "step/start", {"turn": 2, "step": 1}),
        _message(9, turn=2),
        _row(10, "step/end", {"turn": 2, "step": 1}),
        _row(11, "turn/end", {"turn": 2, "reason": {"kind": "completed"}}),
    ]
    _write(path, rows)
    info = inspect_dsh_journal(path, "native-1")
    assert info.inherited_cut_seq == 4
    state = DshUsageAdapterState(provider="dsh")
    configure_dsh_journal(state, info)
    _, observations = _parse(rows, state)
    assert {item.provider_turn_id for item in observations} == {"2"}
    record = assemble_usage_record(_snapshot(), observations, outcome="completed")
    assert record.token_usage.total_tokens.value == 26
    assert select_dsh_journal(tmp_path, "native-1") == path


def test_seeded_source_without_inspected_cut_refuses_before_inherited_work() -> None:
    with pytest.raises(DshJournalError, match="seed_boundary_unverified"):
        _parse([_header(isSeeded=True)])


def test_seeded_checkpoint_preserves_active_attempt_on_source_revalidation(tmp_path: Path) -> None:
    path = tmp_path / "session.v4.jsonl"
    rows = [
        _header(isSeeded=True),
        _row(0, "session/end-seed", {"inherited": True}),
        _row(1, "turn/start", {"turn": 1}),
        _row(2, "step/start", {"turn": 1, "step": 1}),
    ]
    _write(path, rows)
    info = inspect_dsh_journal(path, "native-1")
    state = DshUsageAdapterState(provider="dsh")
    configure_dsh_journal(state, info)
    _parse(rows, state)
    restored = DshUsageAdapterState.model_validate_json(state.model_dump_json())
    configure_dsh_journal(restored, info)
    _, observations = _parse(
        [
            _message(3),
            _row(4, "step/end", {"turn": 1, "step": 1}),
            _row(5, "turn/end", {"turn": 1, "reason": {"kind": "completed"}}),
        ],
        restored,
    )
    assert observations[-1].lifecycle == "completed"
    assert restored.provider_turn_id is None


@pytest.mark.parametrize("generation", ["session.v5.jsonl", "session.v4.jsonl.zstd"])
def test_newer_or_compressed_generation_never_falls_back(tmp_path: Path, generation: str) -> None:
    directory = tmp_path / "project" / "native-1"
    _write(directory / "session.v3.jsonl", [_header(version=3)])
    _write(directory / generation, [_header(version=5 if "v5" in generation else 4)])
    with pytest.raises(DshJournalError, match="format_unsupported"):
        select_dsh_journal(tmp_path, "native-1")


def test_partial_header_is_not_accepted_and_partial_tail_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "session.v4.jsonl"
    path.write_text(json.dumps(_header()))
    with pytest.raises(DshJournalError, match="header_incomplete"):
        inspect_dsh_journal(path, "native-1")
    _write(
        path,
        [
            _header(isSeeded=True),
            _row(0, "session/end-seed", {"inherited": True}),
        ],
    )
    with path.open("a") as handle:
        handle.write('{"type":"assistant/message"')
    assert inspect_dsh_journal(path, "native-1").inherited_cut_seq == 0


def test_session_path_escaping_matches_utf16_native_rules() -> None:
    assert encode_dsh_session_segment("../native") == "..~002Fnative"
    assert encode_dsh_session_segment("..") == "~002E~002E"
    assert encode_dsh_session_segment("a~b") == "a~007Eb"
    assert encode_dsh_session_segment("😀") == "~D83D~DE00"


def test_real_controlled_rc3_capture_retains_two_resumed_native_turns() -> None:
    path = Path(__file__).parents[3] / "fixtures/agent-usage-records/dsh-0.2.2-rc.3-controlled.json"
    fixture = json.loads(path.read_text())
    state = DshUsageAdapterState(provider="dsh", provider_session_id=fixture["provider_session_id"])
    _, observations = _parse(fixture["native_records"], state)
    requests = [item for item in observations if item.kind == "request"]
    assert {item.provider_turn_id for item in requests} == {"1", "2"}
    assert len(requests) == 2
    assert all(item.values["total_tokens"] == 16 for item in requests)
    assert [item.lifecycle for item in observations if item.lifecycle] == [
        "started",
        "completed",
        "started",
        "completed",
    ]


def _managed_service(
    tmp_path: Path, *, backend: str = "dsh_acp"
) -> tuple[UsageService, Path, Path]:
    """Prepare a managed DSH service whose native process has not been created."""

    home = tmp_path / "private-home"
    manifest = tmp_path / "runtime" / "manifest.json"
    manifest.parent.mkdir()
    manifest.write_text(
        json.dumps(
            {
                "tool": "dsh",
                "backend": backend,
                "agent_id": "agent-1",
                "registry_generation_id": "generation-1",
                "runtime": {"session_id": "runtime-1"},
                "backend_state": {},
                "launch_plan": {"home_selector": {"home_path": str(home)}},
            }
        )
    )
    return UsageService.from_manifest(manifest), manifest, home


def _companion_evidence(turn_dir: Path, home: Path, *, generation: str = "generation-1") -> None:
    """Persist the same private identity envelope as the qualified native companion."""

    identity = {
        "version": 1,
        "attempt_id": "managed-1",
        "runtime_session_id": "runtime-1",
        "generation": generation,
        "native_session_id": "native-1",
        "process_id": 101,
    }
    (turn_dir / "dsh-native-binding.json").write_text(
        json.dumps(
            {
                **identity,
                "persistence_root": str(home / "sessions"),
                "source_revision": DSH_SOURCE_REVISION,
                "working_directory": "/synthetic/workspace",
            }
        )
    )
    common = {**identity, "host_incarnation": "host-1", "agent_incarnation": "agent-body-1"}
    _write(
        turn_dir / "dsh-native-evidence.jsonl",
        [
            {**common, "event": "turn/start", "turn": 1, "native_sequence": 0},
            {**common, "event": "claimed", "turn": 1, "message_id": "input-1"},
            {**common, "event": "turn/start", "turn": 2, "native_sequence": 5},
        ],
    )


def _three_native_turns(path: Path) -> None:
    """Write two proven owned roots and one unrelated root to test membership."""

    rows = [_header()]
    for turn in (1, 2, 3):
        offset = (turn - 1) * 5
        rows.extend(
            [
                _row(offset, "turn/start", {"turn": turn}),
                _row(offset + 1, "step/start", {"turn": turn, "step": 1}),
                _message(offset + 2, turn=turn),
                _row(offset + 3, "step/end", {"turn": turn, "step": 1}),
                _row(offset + 4, "turn/end", {"turn": turn, "reason": {"kind": "completed"}}),
            ]
        )
    _write(path, rows)


def test_managed_interval_counts_only_proven_roots_and_finalizes_once(tmp_path: Path) -> None:
    service, manifest, home = _managed_service(tmp_path)
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "managed-1"
    service.begin_headless_turn(
        turn_id="managed-1", turn_dir=turn_dir, turn_index=1, new_session=True
    )
    native = home / "sessions" / "project" / "native-1" / "session.v4.jsonl"
    _three_native_turns(native)
    _companion_evidence(turn_dir, home)
    persist_terminal_evidence(
        turn_dir, returncode=0, completed_at_utc="2026-11-16T01:00:00+00:00", wall_time_ms=25
    )
    # Recover under a newer controller generation and race independent readers.
    payload = json.loads(manifest.read_text())
    payload["registry_generation_id"] = "generation-2"
    payload["backend_state"] = {"session_id": "native-1"}
    manifest.write_text(json.dumps(payload))

    def finalize(_: int) -> Any:
        """Recover original terminal artifacts without launching another process."""

        return UsageService.from_manifest(manifest).finalize_headless_turn(turn_dir)

    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(finalize, range(3)))
    assert all(
        record is not None and record.token_usage.total_tokens.value == 52 for record in records
    )
    record = records[0]
    assert record.generation_id == "generation-1"
    assert record.provider_turn_id is None
    assert record.completed_at_utc == "2026-11-16T01:00:00+00:00"
    page = service.get_usage()
    assert len(page.records) == 1
    pending = service.store.get_pending_turn("managed-1")
    assert pending is not None
    assert pending.snapshot.metadata["native_turn_ids"] == ["1", "2"]
    for native_turn_id in ("1", "2"):
        assert (
            service.store.resolve_turn_id(
                binding_id=pending.snapshot.binding_id or "",
                provider_session_id="native-1",
                provider_turn_id=native_turn_id,
            )
            == "managed-1"
        )
    UsageService.from_manifest(manifest).collect(max_batches=32)
    assert len(service.get_usage().records) == 1
    assert service.get_usage(after=page.next_cursor).records == []
    public = record.model_dump_json()
    assert str(home) not in public and "PRIVATE TRANSCRIPT" not in public


def test_wrong_generation_evidence_preserves_outcome_with_unknown_usage(tmp_path: Path) -> None:
    service, manifest, home = _managed_service(tmp_path)
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "managed-1"
    service.begin_headless_turn(
        turn_id="managed-1", turn_dir=turn_dir, turn_index=1, new_session=True
    )
    _three_native_turns(home / "sessions/project/native-1/session.v4.jsonl")
    _companion_evidence(turn_dir, home, generation="wrong-generation")
    persist_terminal_evidence(
        turn_dir, returncode=2, completed_at_utc="2026-11-16T01:00:00+00:00", wall_time_ms=25
    )
    record = service.finalize_headless_turn(turn_dir)
    assert record is not None and record.outcome == "failed"
    assert record.token_usage.total_tokens.value is None
    assert "dsh_native_binding_identity_mismatch" in record.diagnostics


def _qualify_cli_attempt(turn_dir: Path, *, claimed_message: str = "input-1") -> None:
    """Add the CLI-specific bridge and actual native admission evidence."""

    binding_path = turn_dir / "dsh-native-binding.json"
    binding = json.loads(binding_path.read_text())
    binding["process_birth_token"] = "fixture-worker-birth"
    binding_path.write_text(json.dumps(binding))
    (turn_dir / "dsh-native-handoff.json").write_text(json.dumps(binding))
    (turn_dir / "process.json").write_text(
        json.dumps(
            {"child_pid": binding["process_id"], "child_birth_token": "fixture-worker-birth"}
        )
    )
    evidence_path = turn_dir / "dsh-native-evidence.jsonl"
    evidence = [json.loads(line) for line in evidence_path.read_text().splitlines()]
    evidence[1]["message_id"] = claimed_message
    _write(
        evidence_path, [{**evidence[1], "event": "admitted", "message_id": "input-1"}, *evidence]
    )


def _complete_cli_attempt(turn_dir: Path) -> None:
    """Install the bridge's post-flush closure marker from the owned handoff."""

    binding = json.loads((turn_dir / "dsh-native-handoff.json").read_text())
    (turn_dir / "dsh-native-closure.json").write_text(
        json.dumps(
            {
                **{
                    key: binding[key]
                    for key in (
                        "version",
                        "attempt_id",
                        "native_session_id",
                        "process_id",
                        "process_birth_token",
                    )
                },
                "source": "native_journal",
                "returncode": 0,
            }
        )
    )


def test_cli_usage_recovers_only_verified_closure_and_counts_the_journal_once(
    tmp_path: Path,
) -> None:
    """Native step summaries and a bare zero exit cannot establish accounting."""

    service, manifest, home = _managed_service(tmp_path, backend="dsh_headless")
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "managed-1"
    service.begin_headless_turn(
        turn_id="managed-1", turn_dir=turn_dir, turn_index=1, new_session=True
    )
    _three_native_turns(home / "sessions/project/native-1/session.v4.jsonl")
    _companion_evidence(turn_dir, home)
    _qualify_cli_attempt(turn_dir)
    _write(
        turn_dir / "stdout.jsonl",
        [
            {
                "type": "status",
                "phase": "step_end",
                "turn": 1,
                "step": 1,
                "usage": _usage(inputTokens=999),
            }
        ],
    )
    (turn_dir / "exitcode").write_text("0\n")
    service.reconcile()
    assert service.store.get_record("managed-1") is None
    _complete_cli_attempt(turn_dir)
    service.reconcile()
    record = service.store.get_record("managed-1")
    assert record is not None and record.outcome == "completed"
    assert record.token_usage.total_tokens.value == 52
    assert len(service.get_usage().records) == 1


@pytest.mark.parametrize("different_birth", [False, True])
def test_cli_usage_withholds_unbound_admission(tmp_path: Path, different_birth: bool) -> None:
    """An unrelated claimed input or recycled PID cannot attach native usage."""

    service, manifest, home = _managed_service(tmp_path, backend="dsh_headless")
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "managed-1"
    service.begin_headless_turn(
        turn_id="managed-1", turn_dir=turn_dir, turn_index=1, new_session=True
    )
    _three_native_turns(home / "sessions/project/native-1/session.v4.jsonl")
    _companion_evidence(turn_dir, home)
    _qualify_cli_attempt(turn_dir, claimed_message="input-1" if different_birth else "other-input")
    if different_birth:
        (turn_dir / "process.json").write_text(
            json.dumps({"child_pid": 101, "child_birth_token": "recycled-worker"})
        )
    persist_terminal_evidence(
        turn_dir, returncode=2, completed_at_utc="2026-11-16T01:00:00+00:00", wall_time_ms=25
    )
    record = service.finalize_headless_turn(turn_dir)
    assert record is not None and record.token_usage.total_tokens.value is None
    diagnostic = (
        "dsh_native_handoff_identity_mismatch"
        if different_birth
        else "dsh_native_admission_unverified"
    )
    assert diagnostic in record.diagnostics


def _descendant_evidence(turn_dir: Path, *, local: bool = True) -> None:
    """Append native identity-only child creation and current-turn evidence."""

    path = turn_dir / "dsh-native-evidence.jsonl"
    common = json.loads(path.read_text().splitlines()[0])
    with path.open("a") as stream:
        stream.write(
            json.dumps(
                {
                    **common,
                    "event": "descendant/created",
                    "child_session_id": "child-1",
                    "parent_session_id": "native-1",
                    "local": local,
                }
            )
            + "\n"
        )
        if local:
            stream.write(
                json.dumps(
                    {
                        **common,
                        "event": "descendant/turn/start",
                        "child_session_id": "child-1",
                        "parent_session_id": "native-1",
                        "turn": 2,
                    }
                )
                + "\n"
            )


def test_proven_child_scope_is_separate_and_previous_child_turn_is_excluded(tmp_path: Path) -> None:
    """Charge only companion-proven child activity and keep its requests out of root totals."""

    service, manifest, home = _managed_service(tmp_path)
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "managed-1"
    service.begin_headless_turn(
        turn_id="managed-1", turn_dir=turn_dir, turn_index=1, new_session=True
    )
    _three_native_turns(home / "sessions/project/native-1/session.v4.jsonl")
    _companion_evidence(turn_dir, home)
    _descendant_evidence(turn_dir)
    child_path = home / "sessions/project/child-1/session.v4.jsonl"
    _three_native_turns(child_path)
    rows = [json.loads(line) for line in child_path.read_text().splitlines()]
    rows[0].update(id="child-1", origin="subagent", parentSession="native-1", delegationDepth=1)
    _write(child_path, rows)
    persist_terminal_evidence(
        turn_dir, returncode=0, completed_at_utc="2026-11-16T01:00:00+00:00", wall_time_ms=25
    )
    record = service.finalize_headless_turn(turn_dir)
    assert record is not None
    assert record.token_usage.total_tokens.value == 52
    assert record.subagent_accounting == "separate"
    assert len(record.subagent_usage) == 1
    child = record.subagent_usage[0]
    assert child.child_id == "child-1"
    assert child.included_in_parent is False
    assert child.token_usage.total_tokens.value == 26
    assert child.parent_turn_id == "managed-1"
    service.collect(max_batches=32)
    assert len(service.get_usage().records) == 1


@pytest.mark.parametrize("local", [False, True])
def test_unavailable_descendant_evidence_reports_unknown_inclusion(
    tmp_path: Path, local: bool
) -> None:
    """Expose a proven external child's scope without inventing a native journal or token share."""

    service, manifest, home = _managed_service(tmp_path)
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "managed-1"
    service.begin_headless_turn(
        turn_id="managed-1", turn_dir=turn_dir, turn_index=1, new_session=True
    )
    _three_native_turns(home / "sessions/project/native-1/session.v4.jsonl")
    _companion_evidence(turn_dir, home)
    _descendant_evidence(turn_dir, local=local)
    persist_terminal_evidence(
        turn_dir, returncode=0, completed_at_utc="2026-11-16T01:00:00+00:00", wall_time_ms=25
    )
    record = service.finalize_headless_turn(turn_dir)
    assert record is not None and record.token_usage.total_tokens.value == 52
    assert record.subagent_accounting == "unknown"
    child = record.subagent_usage[0]
    assert child.included_in_parent is None
    assert child.token_usage.total_tokens.value is None
    assert "dsh_descendant_usage_unverified" in record.diagnostics


def test_concurrent_reconciliation_retains_original_generation_and_cutoff(tmp_path: Path) -> None:
    """Independent recovery controllers insert one immutable terminal row under its birth identity."""

    service, manifest, home = _managed_service(tmp_path)
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "managed-1"
    service.begin_headless_turn(
        turn_id="managed-1", turn_dir=turn_dir, turn_index=1, new_session=True
    )
    _three_native_turns(home / "sessions/project/native-1/session.v4.jsonl")
    _companion_evidence(turn_dir, home)
    persist_terminal_evidence(
        turn_dir, returncode=0, completed_at_utc="2026-11-16T01:00:00+00:00", wall_time_ms=25
    )
    payload = json.loads(manifest.read_text())
    payload["registry_generation_id"] = "generation-after-restart"
    payload["backend_state"] = {"session_id": "native-1"}
    manifest.write_text(json.dumps(payload))

    def recover(_: int) -> Any:
        """Reconcile from durable terminal artifacts without replaying the provider."""

        recovered = UsageService.from_manifest(manifest)
        recovered.reconcile()
        return recovered.get_usage().records

    with ThreadPoolExecutor(max_workers=4) as pool:
        pages = list(pool.map(recover, range(4)))
    assert all(len(page) == 1 for page in pages)
    records = [page[0] for page in pages]
    assert len({record.record_id for record in records}) == 1
    assert all(record.generation_id == "generation-1" for record in records)
    assert all(record.completed_at_utc == "2026-11-16T01:00:00+00:00" for record in records)
    assert all(record.token_usage.total_tokens.value == 52 for record in records)
    before = service.store.get_pending_turn("managed-1")
    assert before is not None and before.finalization is not None
    cutoff = before.finalization.model_dump()
    service.reconcile()
    after = service.store.get_pending_turn("managed-1")
    assert after is not None and after.finalization is not None
    assert after.finalization.model_dump() == cutoff
    assert len(service.get_usage().records) == 1


def test_resume_boundary_excludes_all_previous_completed_roots(tmp_path: Path) -> None:
    _, manifest, home = _managed_service(tmp_path)
    native = home / "sessions/project/native-1/session.v4.jsonl"
    _three_native_turns(native)
    payload = json.loads(manifest.read_text())
    payload["backend_state"] = {"session_id": "native-1"}
    manifest.write_text(json.dumps(payload))
    service = UsageService.from_manifest(manifest)
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "managed-1"
    service.begin_headless_turn(
        turn_id="managed-1", turn_dir=turn_dir, turn_index=1, new_session=False
    )
    with native.open("a") as handle:
        rows = [
            _row(15, "turn/start", {"turn": 4}),
            _row(16, "step/start", {"turn": 4, "step": 1}),
            _message(17, turn=4),
            _row(18, "step/end", {"turn": 4, "step": 1}),
            _row(19, "turn/end", {"turn": 4, "reason": {"kind": "completed"}}),
        ]
        handle.write("".join(json.dumps(row) + "\n" for row in rows))
    _companion_evidence(turn_dir, home)
    evidence_path = turn_dir / "dsh-native-evidence.jsonl"
    evidence = [json.loads(line) for line in evidence_path.read_text().splitlines()]
    for event in evidence[:2]:
        event["turn"] = 4
    _write(evidence_path, evidence[:2])
    persist_terminal_evidence(
        turn_dir, returncode=0, completed_at_utc="2026-11-16T01:00:00+00:00", wall_time_ms=25
    )
    record = service.finalize_headless_turn(turn_dir)
    assert record is not None and record.token_usage.total_tokens.value == 26
    assert record.provider_turn_id == "4"
    assert len(service.get_usage().records) == 1


def test_collector_waits_for_partial_rows_and_deduplicates_replaced_copy(tmp_path: Path) -> None:
    home = tmp_path / "home"
    path = home / "sessions/project/native-1/session.v4.jsonl"
    rows = [
        _header(),
        _row(0, "turn/start", {"turn": 1}),
        _row(1, "step/start", {"turn": 1, "step": 1}),
        _message(2),
        _row(3, "step/end", {"turn": 1, "step": 1}),
        _row(4, "turn/end", {"turn": 1, "reason": {"kind": "completed"}}),
    ]
    _write(path, rows)
    incomplete = json.dumps(_row(5, "turn/start", {"turn": 2}))
    with path.open("a") as handle:
        handle.write(incomplete[: len(incomplete) // 2])
    binding = UsageSourceBinding(
        binding_id="binding-1",
        agent_id="agent-1",
        runtime_session_id="runtime-1",
        provider="dsh",
        home_path=str(home),
        provider_session_id="native-1",
        metadata={"fresh_session": True},
    )
    store = UsageStore.from_path(tmp_path / "usage.sqlite3", "runtime-1")
    collector = UsageCollector.from_binding(store, binding)
    first = collector.collect(max_batches=32)
    assert len([item for item in first if item.kind == "request"]) == 1
    assert not collector.caught_up
    assert "native_source_partial_record" in collector.diagnostics
    following = [
        _row(6, "step/start", {"turn": 2, "step": 1}),
        _message(7, turn=2),
        _row(8, "step/end", {"turn": 2, "step": 1}),
        _row(9, "turn/end", {"turn": 2, "reason": {"kind": "completed"}}),
    ]
    with path.open("a") as handle:
        handle.write(incomplete[len(incomplete) // 2 :] + "\n")
        handle.write("".join(json.dumps(row) + "\n" for row in following))
    restarted = UsageCollector.from_binding(store, binding)
    second = restarted.collect(max_batches=32)
    assert len([item for item in second if item.kind == "request"]) == 1
    assert restarted.caught_up
    replacement = path.with_suffix(".replacement")
    _write(replacement, rows + [_row(5, "turn/start", {"turn": 2}), *following])
    replacement.replace(path)
    replaced = UsageCollector.from_binding(store, binding)
    assert replaced.collect(max_batches=32) == []
    assert "native_source_replaced_or_truncated" in replaced.diagnostics
    assert len([item for item in store.list_observations() if item.kind == "request"]) == 2


def test_checkpoint_failure_reprocesses_native_attempts_without_duplicates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    _three_native_turns(home / "sessions/project/native-1/session.v4.jsonl")
    binding = UsageSourceBinding(
        binding_id="binding-1",
        agent_id="agent-1",
        runtime_session_id="runtime-1",
        provider="dsh",
        home_path=str(home),
        provider_session_id="native-1",
        metadata={"fresh_session": True},
    )
    store = UsageStore.from_path(tmp_path / "usage.sqlite3", "runtime-1")
    collector = UsageCollector.from_binding(store, binding)
    original = store.ingest_batch

    def unavailable(**_: Any) -> Any:
        """Model a recorder outage after native parsing but before source commit."""

        raise OSError("synthetic recorder unavailable")

    monkeypatch.setattr(store, "ingest_batch", unavailable)
    assert collector.collect(max_batches=32) == []
    assert store.list_checkpoints() == []
    assert store.list_observations() == []
    monkeypatch.setattr(store, "ingest_batch", original)
    recovered = UsageCollector.from_binding(store, binding)
    assert len([item for item in recovered.collect(max_batches=32) if item.kind == "request"]) == 3
    assert recovered.collect(max_batches=32) == []
    assert len([item for item in store.list_observations() if item.kind == "request"]) == 3


def test_recording_outage_recovers_the_original_cached_finalization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, manifest, home = _managed_service(tmp_path)
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "managed-1"
    service.begin_headless_turn(
        turn_id="managed-1", turn_dir=turn_dir, turn_index=1, new_session=True
    )
    _three_native_turns(home / "sessions/project/native-1/session.v4.jsonl")
    _companion_evidence(turn_dir, home)
    persist_terminal_evidence(
        turn_dir, returncode=0, completed_at_utc="2026-11-16T01:00:00+00:00", wall_time_ms=25
    )

    def unavailable(_: Any) -> Any:
        """Fail after the immutable artifact cache exists but before row insertion."""

        raise OSError("synthetic recorder unavailable")

    monkeypatch.setattr(service.store, "finalize", unavailable)
    with pytest.raises(OSError):
        service.finalize_headless_turn(turn_dir)
    assert (turn_dir / "usage-record.json").exists()
    payload = json.loads(manifest.read_text())
    payload["registry_generation_id"] = "generation-2"
    payload["backend_state"] = {"session_id": "native-1"}
    manifest.write_text(json.dumps(payload))
    recovered = UsageService.from_manifest(manifest)
    recovered.reconcile()
    page = recovered.get_usage()
    assert len(page.records) == 1
    assert page.records[0].generation_id == "generation-1"
    assert page.records[0].completed_at_utc == "2026-11-16T01:00:00+00:00"
    assert page.records[0].token_usage.total_tokens.value == 52
