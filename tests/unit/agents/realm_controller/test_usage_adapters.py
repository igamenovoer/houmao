"""Provider-format accounting regressions backed by sanitized real captures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from houmao.agents.realm_controller.usage_adapters import UsageAdapter, parse_usage_payload


def _fixture(provider: str) -> dict:
    """Read one exact-version sanitized provider capture."""

    root = Path(__file__).parents[3] / "fixtures" / "agent-usage-records"
    return json.loads(next(root.glob(f"{provider}-*-qwen.json")).read_text())


@pytest.mark.parametrize("provider", ["claude", "codex", "kimi"])
def test_captured_native_stream_retains_turn_boundaries_and_request_usage(provider: str) -> None:
    fixture = _fixture(provider)
    adapter = UsageAdapter.from_provider(provider, fixture["provider_session_id"])
    observations = [
        item
        for payload in fixture["native_records"]
        for item in adapter.parse(payload, source_ref="capture-native")
    ]
    requests = [item for item in observations if item.kind == "request"]
    starts = [item for item in observations if item.lifecycle == "started"]
    completions = [item for item in observations if item.lifecycle == "completed"]
    assert len(starts) == 2
    assert len({item.provider_turn_id for item in starts}) == 2
    assert {item.provider_turn_id for item in starts} == {
        item.provider_turn_id for item in completions
    }
    assert len({item.request_id for item in requests}) == 2
    assert all(item.provider_turn_id is not None for item in requests)
    assert all(item.values.get("input_tokens", 0) > 0 for item in requests)


def test_codex_request_record_and_token_count_do_not_duplicate_usage() -> None:
    fixture = _fixture("codex")
    adapter = UsageAdapter.from_provider("codex", fixture["provider_session_id"])
    observations = [
        item
        for record in fixture["native_records"]
        for item in adapter.parse(record, source_ref="native")
    ]
    requests = [item for item in observations if item.kind == "request"]
    assert len(requests) == 2
    assert all(item.provider_event_type == "token_usage_record" for item in requests)
    assert all(item.token_semantics.cached_input_included_in_input is True for item in requests)


def test_codex_exec_completion_is_cumulative_on_resume() -> None:
    fixture = _fixture("codex")
    adapter = UsageAdapter.from_provider("codex")
    observations = [
        item
        for turn in fixture["headless_turns"]
        for record in turn
        for item in adapter.parse(record, source_ref="stdout", source_kind="structured_output")
    ]
    usage = [item for item in observations if item.values]
    assert len(usage) == 2
    assert all(item.measurement_scope == "session_cumulative" for item in usage)
    assert usage[1].values["input_tokens"] > usage[0].values["input_tokens"]


def test_claude_summary_tokens_and_cost_have_distinct_scopes() -> None:
    fixture = _fixture("claude")
    adapter = UsageAdapter.from_provider("claude")
    records = [
        item
        for turn in fixture["headless_turns"]
        for record in turn
        for item in adapter.parse(record, source_ref="stdout", source_kind="structured_output")
    ]
    summaries = [item for item in records if item.kind == "summary"]
    cumulative = [item for item in records if item.kind == "cumulative"]
    assert len(summaries) == len(cumulative) == 2
    assert all("cost_usd" not in item.values for item in summaries)
    assert all("duration_api_ms" not in item.values for item in summaries)
    assert all("duration_ms" in item.values for item in summaries)
    assert cumulative[1].values["cost_usd"] > cumulative[0].values["cost_usd"]
    assert (
        adapter.snapshot_state()["previous_totals"]["cost_usd"] == cumulative[-1].values["cost_usd"]
    )


def test_kimi_step_end_is_not_an_extra_request_and_missing_cache_remains_missing() -> None:
    fixture = _fixture("kimi")
    adapter = UsageAdapter.from_provider("kimi", fixture["provider_session_id"])
    requests = [
        item
        for record in fixture["native_records"]
        for item in adapter.parse(record, source_ref="wire")
        if item.kind == "request"
    ]
    assert len(requests) == 2
    assert requests[0].provider_turn_id == "0"
    assert "cached_input_tokens" not in requests[0].values
    assert requests[0].values["cache_write_input_tokens"] == 0


def test_kimi_session_scope_does_not_assert_cumulative_additivity() -> None:
    observations = parse_usage_payload(
        "kimi",
        {"type": "usage.record", "usageScope": "session", "usage": {"inputOther": 12}},
        source_ref="wire",
    )
    assert observations[0].measurement_scope == "unknown"
    assert observations[0].metadata["limitation"] == "unverified_session_usage_scope"


def test_adapter_checkpoint_restores_native_turn_and_cumulative_baseline() -> None:
    adapter = UsageAdapter.from_provider("codex", "session")
    adapter.parse(
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "t"}},
        source_ref="native",
    )
    payload = {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "last_token_usage": {"input_tokens": 7, "output_tokens": 2},
                "total_token_usage": {"input_tokens": 7, "output_tokens": 2},
            },
        },
    }
    first = adapter.parse(payload, source_ref="native")
    restored = UsageAdapter.from_provider("codex")
    restored.restore_state(adapter.snapshot_state())
    replay = restored.parse(payload, source_ref="native")
    assert any(item.kind == "request" for item in first)
    assert all(item.kind != "request" for item in replay)
    assert restored.provider_session_id == "session"
    assert restored.provider_turn_id == "t"
    with pytest.raises(ValueError, match="another provider"):
        UsageAdapter.from_provider("claude").restore_state(adapter.snapshot_state())


def test_fork_replay_is_skipped_until_verified_child_start() -> None:
    adapter = UsageAdapter.from_provider("codex")
    adapter.parse(
        {"type": "session_meta", "payload": {"id": "child", "forked_from_id": "parent"}},
        source_ref="child",
    )
    request = {
        "type": "token_usage_record",
        "payload": {
            "response_id": "copied",
            "turn_id": "parent-turn",
            "usage": {"input_tokens": 10, "output_tokens": 1},
        },
    }
    assert adapter.parse(request, source_ref="child") == []
    adapter.parse(
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "child-turn"}},
        source_ref="child",
    )
    request["payload"].update(response_id="new", turn_id="child-turn")
    assert adapter.parse(request, source_ref="child")[0].request_id == "new"


@pytest.mark.parametrize("marker_first", [True, False])
def test_legacy_compaction_requires_a_matching_response_id(marker_first: bool) -> None:
    adapter = UsageAdapter.from_provider("codex", "session")
    record = {
        "type": "token_usage_record",
        "payload": {
            "response_id": "compact-response",
            "usage": {"input_tokens": 50, "output_tokens": 4},
        },
    }
    marker = {"type": "compacted", "payload": {"compaction_response_id": "compact-response"}}
    observations = []
    for payload in [marker, record] if marker_first else [record, marker]:
        observations.extend(adapter.parse(payload, source_ref="native"))
    assert len(observations) == 1
    assert observations[0].accounting_kind == "compaction"


def test_adapter_does_not_coerce_invalid_or_absent_counters_to_zero() -> None:
    observations = parse_usage_payload(
        "codex",
        {
            "type": "token_usage_record",
            "payload": {
                "response_id": "resp",
                "turn_id": "t",
                "usage": {
                    "input_tokens": -1,
                    "output_tokens": False,
                    "cached_input_tokens": "secret",
                },
            },
        },
        source_ref="/private/log.jsonl",
    )
    assert observations[0].values == {
        "input_tokens": None,
        "output_tokens": None,
        "cached_input_tokens": None,
    }
    assert "/private" not in observations[0].source_ref


def test_local_compaction_snapshot_and_marker_count_once() -> None:
    adapter = UsageAdapter.from_provider("codex", "session")
    record = {
        "type": "token_usage_record",
        "payload": {"response_id": "compact", "usage": {"input_tokens": 50, "output_tokens": 4}},
    }
    assert adapter.parse(record, source_ref="native") == []
    snapshot = {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "last_token_usage": {"input_tokens": 50, "output_tokens": 4},
                "total_token_usage": {"input_tokens": 50, "output_tokens": 4},
            },
        },
    }
    observations = adapter.parse(snapshot, source_ref="native")
    observations += adapter.parse(
        {"type": "compacted", "payload": {"compaction_response_id": "compact"}}, source_ref="native"
    )
    assert len([item for item in observations if item.kind == "request"]) == 1


def test_identical_later_request_is_not_suppressed_by_previous_response() -> None:
    adapter = UsageAdapter.from_provider("codex", "session")
    adapter.parse(
        {
            "type": "token_usage_record",
            "payload": {
                "response_id": "first",
                "turn_id": "t",
                "usage": {"input_tokens": 50, "output_tokens": 4},
                "thread_token_usage": {"input_tokens": 50, "output_tokens": 4},
            },
        },
        source_ref="native",
    )

    def snapshot(total):
        return {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {"input_tokens": 50, "output_tokens": 4},
                    "total_token_usage": {"input_tokens": total, "output_tokens": total // 50 * 4},
                },
            },
        }

    assert all(item.kind != "request" for item in adapter.parse(snapshot(50), source_ref="native"))
    assert any(item.kind == "request" for item in adapter.parse(snapshot(100), source_ref="native"))


def test_native_client_version_is_retained_in_observations_and_checkpoints() -> None:
    """A qualified native client version remains visible after parser recovery."""

    adapter = UsageAdapter.from_provider("codex")
    adapter.parse(
        {"type": "session_meta", "payload": {"id": "session", "cli_version": "0.167.2"}},
        source_ref="native",
    )
    restored = UsageAdapter.from_provider("codex")
    restored.restore_state(adapter.snapshot_state())
    observed = restored.parse(
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "turn"}},
        source_ref="native",
    )
    assert observed[0].provider_version == "0.167.2"
    assert observed[0].profile_id == "codex-0.167.2-v1"


@pytest.mark.parametrize("provider", ["claude", "codex", "kimi"])
def test_explicit_unknown_client_version_retains_unqualified_raw_accounting(provider: str) -> None:
    """A future binary cannot inherit qualified token scopes and inclusion rules."""

    fixture = _fixture(provider)
    adapter = UsageAdapter.from_provider(provider, fixture["provider_session_id"])
    adapter.parse({"cli_version": "999.0.0"}, source_ref="version")
    observations = []
    for payload in fixture["native_records"]:
        # The injected version models an explicit unqualified client, rather
        # than this fixture's own qualified session-meta version declaration.
        data = payload.get("payload", {})
        if payload.get("type") == "session_meta" and isinstance(data, dict):
            payload = {**payload, "payload": {**data, "cli_version": "999.0.0"}}
        observations.extend(adapter.parse(payload, source_ref="future-native"))
    usage = [item for item in observations if item.values]
    assert usage
    assert all(item.provider_version == "999.0.0" for item in usage)
    assert all(item.measurement_scope == "unknown" for item in usage)
    assert all(item.token_semantics.cached_input_included_in_input is None for item in usage)
    assert all(item.metadata["qualification"] == "unsupported_client_version" for item in usage)
