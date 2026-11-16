"""Accounting-only reader for the qualified DSH v4 plaintext session journal.

The physical format and attempt boundaries are qualified against upstream
``39163dd30f703a79079e2d2446545cff3c453738``. This module never interprets ACP
context occupancy as token consumption, retains no message content, and leaves
source checkpoints and immutable finalization to the shared usage service.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from houmao.agents.realm_controller.usage_adapters.common import (
    UsageAdapterState,
    UsageParseContext,
    lifecycle_observation,
    mapping,
    observation,
    stable_key,
    text_id,
)
from houmao.agents.realm_controller.usage_models import (
    UsageNumber,
    UsageObservation,
    UsageTokenSemantics,
    UsageTurnSnapshot,
)

DSH_SOURCE_REVISION = "39163dd30f703a79079e2d2446545cff3c453738"
DSH_JOURNAL_VERSION = 4
DSH_JOURNAL_PROFILE = "dsh-v4-39163dd30f70-usage-v1"
DSH_MAX_JOURNAL_ROW_BYTES = 4 << 20
_MAX_SAFE_INTEGER = (1 << 53) - 1
_GENERATION = re.compile(r"session(?:\.v([1-9][0-9]*))?\.jsonl(\.zstd)?\Z")
_HEADER_KEYS = frozenset(
    {
        "type",
        "version",
        "id",
        "createdAt",
        "isSeeded",
        "delegationDepth",
        "cwd",
        "parentSession",
        "origin",
        "agentPreset",
    }
)
DSH_TOKEN_SEMANTICS = UsageTokenSemantics(
    cached_input_included_in_input=False,
    cache_write_included_in_input=False,
    reasoning_included_in_output=True,
)
_USAGE_FIELDS = {
    "inputTokens": "input_tokens",
    "outputTokens": "output_tokens",
    "cacheReadTokens": "cached_input_tokens",
    "cacheWriteTokens": "cache_write_input_tokens",
    "reasoningTokens": "reasoning_output_tokens",
    "totalTokens": "total_tokens",
}


class DshJournalError(ValueError):
    """Report a safe, content-free journal qualification or ownership failure."""


class DshJournalInfo(BaseModel):
    """Private verified journal identity and exact nonchargeable inherited cut."""

    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: str
    format_version: Literal[4] = 4
    seeded: bool = False
    inherited_cut_seq: int = -1
    parent_session_id: str | None = None
    origin: Literal["subagent"] | None = None
    cwd: str | None = None


class DshUsageAdapterState(UsageAdapterState):
    """Checkpointable native attempt state containing accounting metadata only."""

    header_verified: bool = False
    inherited_cut_seq: int | None = None
    next_native_seq: int = 0
    native_step: int | None = None
    attempt_index: int = 0
    attempt_phase: Literal["idle", "open", "finish_closed", "settled_message", "settled_retry"] = (
        "idle"
    )
    route_provider: str | None = None
    route_model: str | None = None
    parent_session_id: str | None = None
    native_subagent: bool = False
    awaiting_live_turn: bool = False
    source_invalid: bool = False
    limitations: list[str] = Field(default_factory=list)


class DshIntervalInfo(BaseModel):
    """Private exact native root set established by an owned ACP interval."""

    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: str
    root_turn_ids: list[str] = Field(default_factory=list)
    descendant_turn_ids: dict[str, list[str]] = Field(default_factory=dict)
    descendant_parents: dict[str, str] = Field(default_factory=dict)
    descendant_local: dict[str, bool] = Field(default_factory=dict)
    persistence_root: str | None = None
    working_directory: str | None = None
    coverage_complete: bool = True


def read_dsh_interval(turn_dir: Path, snapshot: UsageTurnSnapshot) -> DshIntervalInfo:
    """Validate driver binding and companion claims without using output timing.

    Only evidence carrying the original attempt/runtime/generation/native
    identity contributes. Root starts belong to the driver's exclusive ACP
    interval; at least one matching claimed input must establish admission.
    Native descendant sessions require separate explicit lineage and are not
    guessed from timestamps or recursively charged by this reader.
    """

    try:
        binding = json.loads((turn_dir / "dsh-native-binding.json").read_text())
    except (OSError, ValueError, UnicodeError) as exc:
        raise DshJournalError("dsh_native_binding_unavailable") from exc
    if not isinstance(binding, dict):
        raise DshJournalError("dsh_native_binding_invalid")
    expected = {
        "version": 1,
        "attempt_id": snapshot.turn_id,
        "runtime_session_id": snapshot.runtime_session_id,
        "generation": snapshot.generation_id,
    }
    if any(binding.get(key) != value for key, value in expected.items()):
        raise DshJournalError("dsh_native_binding_identity_mismatch")
    native_id = text_id(binding.get("native_session_id"))
    if native_id is None or snapshot.provider_session_id not in {None, native_id}:
        raise DshJournalError("dsh_native_binding_session_mismatch")
    if binding.get("source_revision") != DSH_SOURCE_REVISION:
        raise DshJournalError("dsh_native_binding_build_unsupported")
    persistence_root = binding.get("persistence_root")
    workspace = binding.get("working_directory")
    for value in (persistence_root, workspace):
        if value is not None and (not isinstance(value, str) or not Path(value).is_absolute()):
            raise DshJournalError("dsh_native_binding_location_invalid")
    process_id = _count(binding.get("process_id"))
    if not process_id:
        raise DshJournalError("dsh_native_binding_process_missing")
    expected["native_session_id"] = native_id
    expected["process_id"] = process_id
    starts: list[str] = []
    claimed: set[str] = set()
    incarnation: tuple[str, str] | None = None
    complete = True
    descendants: dict[str, str] = {}
    descendant_turns: dict[str, list[str]] = {}
    descendant_local: dict[str, bool] = {}
    try:
        with (turn_dir / "dsh-native-evidence.jsonl").open("rb") as handle:
            while line := handle.readline(DSH_MAX_JOURNAL_ROW_BYTES + 1):
                if len(line) > DSH_MAX_JOURNAL_ROW_BYTES:
                    raise DshJournalError("dsh_native_evidence_exceeds_read_bound")
                if not line.endswith(b"\n"):
                    complete = False
                    break
                event = json.loads(line)
                if not isinstance(event, dict) or event.get("event") not in {
                    "claimed",
                    "turn/start",
                    "descendant/created",
                    "descendant/turn/start",
                }:
                    continue
                if any(event.get(key) != value for key, value in expected.items()):
                    raise DshJournalError("dsh_native_evidence_identity_mismatch")
                host = text_id(event.get("host_incarnation"))
                agent = text_id(event.get("agent_incarnation"))
                if host is None or agent is None or incarnation not in {None, (host, agent)}:
                    raise DshJournalError("dsh_native_evidence_incarnation_mismatch")
                incarnation = (host, agent)
                if event["event"].startswith("descendant/"):
                    child = text_id(event.get("child_session_id"))
                    parent = text_id(event.get("parent_session_id"))
                    if (
                        child is None
                        or child == native_id
                        or parent not in {native_id, *descendants}
                    ):
                        raise DshJournalError("dsh_descendant_lineage_unverified")
                    if event["event"] == "descendant/created":
                        if parent != descendants.get(child, parent) or not isinstance(
                            event.get("local"), bool
                        ):
                            raise DshJournalError("dsh_descendant_lineage_unverified")
                        descendants[child] = parent
                        descendant_local[child] = event["local"]
                        descendant_turns.setdefault(child, [])
                    else:
                        turn = _count(event.get("turn"))
                        if child not in descendants or descendants[child] != parent or turn is None:
                            raise DshJournalError("dsh_descendant_turn_unverified")
                        if str(turn) not in descendant_turns[child]:
                            descendant_turns[child].append(str(turn))
                    continue
                turn = _count(event.get("turn"))
                if turn is None:
                    raise DshJournalError("dsh_native_evidence_turn_invalid")
                if event["event"] == "claimed":
                    if text_id(event.get("message_id")) is None:
                        raise DshJournalError("dsh_native_evidence_claim_invalid")
                    claimed.add(str(turn))
                elif str(turn) not in starts:
                    starts.append(str(turn))
    except DshJournalError:
        raise
    except (OSError, ValueError, UnicodeError) as exc:
        raise DshJournalError("dsh_native_evidence_unavailable") from exc
    if claimed and not claimed.issubset(starts):
        raise DshJournalError("dsh_native_evidence_claim_without_turn")
    roots = starts if claimed else []
    return DshIntervalInfo(
        session_id=native_id,
        root_turn_ids=roots,
        descendant_turn_ids=descendant_turns if claimed else {},
        descendant_parents=descendants if claimed else {},
        descendant_local=descendant_local if claimed else {},
        persistence_root=persistence_root,
        working_directory=workspace,
        coverage_complete=complete,
    )


def _count(value: Any) -> int | None:
    """Accept the nonnegative safe integers used by DSH's JavaScript counters."""

    return (
        value
        if isinstance(value, int)
        and not isinstance(value, bool)
        and 0 <= value <= _MAX_SAFE_INTEGER
        else None
    )


def _header(payload: Mapping[str, Any], expected_session_id: str | None) -> DshJournalInfo:
    """Validate the current physical header before interpreting any event rows."""

    if payload.get("type") != "session" or payload.get("version") != DSH_JOURNAL_VERSION:
        raise DshJournalError("dsh_journal_format_unsupported")
    session_id = payload.get("id")
    if (
        not isinstance(session_id, str)
        or not session_id
        or (expected_session_id is not None and session_id != expected_session_id)
    ):
        raise DshJournalError("dsh_journal_session_identity_mismatch")
    if (
        set(payload) - _HEADER_KEYS
        or _count(payload.get("createdAt")) is None
        or _count(payload.get("delegationDepth")) is None
        or not isinstance(payload.get("isSeeded"), bool)
    ):
        raise DshJournalError("dsh_journal_header_invalid")
    for key in ("cwd", "parentSession", "agentPreset"):
        if key in payload and not isinstance(payload[key], str):
            raise DshJournalError("dsh_journal_header_invalid")
    cwd = payload.get("cwd")
    if isinstance(cwd, str) and not Path(cwd).is_absolute():
        raise DshJournalError("dsh_journal_header_invalid")
    origin = payload.get("origin")
    if "origin" in payload and origin != "subagent":
        raise DshJournalError("dsh_journal_header_invalid")
    return DshJournalInfo(
        session_id=session_id,
        seeded=payload["isSeeded"],
        parent_session_id=payload.get("parentSession"),
        origin=origin,
        cwd=cwd,
    )


def inspect_dsh_journal(path: Path, expected_session_id: str | None) -> DshJournalInfo:
    """Verify a plaintext generation and find its last inherited seed marker.

    Parameters
    ----------
    path:
        Exact physical artifact inside the already bound private persistence root.
    expected_session_id:
        Optional exact native identity. A caller omitting it must validate the returned
        identity and parent lineage against an explicit managed binding before use.

    Returns
    -------
    DshJournalInfo
        Header metadata and the exact inherited prefix cut. A seeded source must
        supply this cut to its parser before any observations are accepted.
    """

    match = _GENERATION.fullmatch(path.name)
    if match is None or match[2] is not None or int(match[1] or 0) != DSH_JOURNAL_VERSION:
        raise DshJournalError("dsh_journal_format_unsupported")
    with path.open("rb") as handle:
        line = handle.readline(DSH_MAX_JOURNAL_ROW_BYTES + 1)
        if not line.endswith(b"\n") or len(line) > DSH_MAX_JOURNAL_ROW_BYTES:
            raise DshJournalError("dsh_journal_header_incomplete")
        try:
            payload = json.loads(line)
        except (ValueError, UnicodeError) as exc:
            raise DshJournalError("dsh_journal_header_invalid") from exc
        if not isinstance(payload, dict):
            raise DshJournalError("dsh_journal_header_invalid")
        info = _header(payload, expected_session_id)
        if not info.seeded:
            return info
        inherited_cut = -1
        while line := handle.readline(DSH_MAX_JOURNAL_ROW_BYTES + 1):
            if len(line) > DSH_MAX_JOURNAL_ROW_BYTES:
                raise DshJournalError("dsh_journal_row_exceeds_read_bound")
            if not line.endswith(b"\n"):
                break
            try:
                event = json.loads(line)
            except (ValueError, UnicodeError) as exc:
                raise DshJournalError("dsh_journal_event_invalid") from exc
            if not isinstance(event, dict):
                raise DshJournalError("dsh_journal_event_invalid")
            if (
                event.get("type") == "session/end-seed"
                and mapping(event.get("data")).get("inherited") is True
            ):
                seq = _count(event.get("seq"))
                if seq is None or seq <= inherited_cut:
                    raise DshJournalError("dsh_journal_seed_boundary_invalid")
                inherited_cut = seq
        if inherited_cut < 0:
            raise DshJournalError("dsh_journal_seed_boundary_missing")
        return info.model_copy(update={"inherited_cut_seq": inherited_cut})


def encode_dsh_session_segment(value: str) -> str:
    """Match DSH's injective UTF-16 path escaping without admitting traversal."""

    if not value:
        raise DshJournalError("dsh_journal_session_identity_missing")
    if value in {".", ".."}:
        return "~002E" * len(value)
    encoded = value.encode("utf-16-be", errors="surrogatepass")
    result: list[str] = []
    for offset in range(0, len(encoded), 2):
        code = int.from_bytes(encoded[offset : offset + 2], "big")
        character = chr(code)
        result.append(character if re.fullmatch(r"[A-Za-z0-9._-]", character) else f"~{code:04X}")
    return "".join(result)


def select_dsh_journal(root: Path, expected_session_id: str) -> Path | None:
    """Select the highest canonical generation of the exact bound native session.

    A newer unsupported or compressed generation refuses collection instead of
    silently falling back to an older readable copy. Ambiguous ownership also
    refuses collection. The caller owns diagnostics and source checkpoint I/O.
    """

    root = root.resolve()
    if not root.is_dir():
        return None
    segment = encode_dsh_session_segment(expected_session_id)
    selected: list[Path] = []
    for directory in root.glob(f"*/{segment}"):
        resolved = directory.resolve()
        if not resolved.is_relative_to(root) or not resolved.is_dir():
            continue
        candidates: list[tuple[int, Path]] = []
        for path in resolved.iterdir():
            match = _GENERATION.fullmatch(path.name)
            if match is not None and path.is_file():
                if not path.resolve().is_relative_to(root):
                    raise DshJournalError("dsh_journal_source_outside_bound_root")
                candidates.append((int(match[1] or 0), path))
        if not candidates:
            continue
        highest = max(version for version, _ in candidates)
        latest = [path for version, path in candidates if version == highest]
        if len(latest) != 1:
            raise DshJournalError("dsh_journal_encoding_ambiguous")
        inspect_dsh_journal(latest[0], expected_session_id)
        selected.append(latest[0])
    if len(selected) > 1:
        raise DshJournalError("dsh_journal_session_ownership_ambiguous")
    return selected[0] if selected else None


def configure_dsh_journal(state: DshUsageAdapterState, info: DshJournalInfo) -> None:
    """Bind verified seed and ancestry facts before parsing or restoring a source."""

    if state.provider != "dsh" or state.provider_session_id not in {None, info.session_id}:
        raise DshJournalError("dsh_journal_session_identity_mismatch")
    if state.header_verified and state.inherited_cut_seq != info.inherited_cut_seq:
        raise DshJournalError("dsh_journal_seed_boundary_changed")
    state.provider_session_id = info.session_id
    state.inherited_cut_seq = info.inherited_cut_seq
    state.parent_session_id = info.parent_session_id
    state.native_subagent = info.origin == "subagent"
    if not state.header_verified:
        state.awaiting_live_turn = info.seeded


def normalize_dsh_usage(usage: Mapping[str, Any]) -> dict[str, UsageNumber | None]:
    """Normalize validated disjoint buckets, keeping missing measurements unknown.

    An exact total can establish a full-call total when a cache bucket is
    absent. Missing cache buckets never become zero. Invalid or contradictory
    samples fail closed; final message usage takes precedence over its embedded
    stream, matching the native attempt fold.
    """

    if any(_count(value) is None for key, value in usage.items() if key in _USAGE_FIELDS):
        raise DshJournalError("dsh_usage_invalid_counter")
    values: dict[str, UsageNumber | None] = {
        target: _count(usage[source]) for source, target in _USAGE_FIELDS.items() if source in usage
    }
    uncached = _count(usage.get("inputTokens"))
    output = _count(usage.get("outputTokens"))
    reasoning = _count(usage.get("reasoningTokens"))
    if reasoning is not None and output is not None and reasoning > output:
        raise DshJournalError("dsh_usage_reasoning_exceeds_output")
    total = _count(usage.get("totalTokens"))
    if uncached is None or output is None:
        return values
    known_input = sum(
        _count(usage.get(key)) or 0
        for key in ("inputTokens", "cacheReadTokens", "cacheWriteTokens")
    )
    if known_input > _MAX_SAFE_INTEGER:
        raise DshJournalError("dsh_usage_counter_overflow")
    both_cache_buckets = all(key in usage for key in ("cacheReadTokens", "cacheWriteTokens"))
    if total is not None:
        exact_input = total - output
        if exact_input < known_input or (both_cache_buckets and exact_input != known_input):
            raise DshJournalError("dsh_usage_contradictory_total")
    # Let the shared assembler derive an absent total with explicit provenance.
    if total is None and both_cache_buckets and known_input + output > _MAX_SAFE_INTEGER:
        raise DshJournalError("dsh_usage_counter_overflow")
    return values


def _stream_usage(value: Any) -> Mapping[str, Any] | None:
    """Read the last raw usage chunk without materializing text or tool streams."""

    if not isinstance(value, list):
        return None
    for record in reversed(value):
        record = mapping(record)
        chunk = mapping(record.get("chunk")) if record.get("type") == "chunk" else {}
        if chunk.get("type") == "usage" and isinstance(chunk.get("usage"), dict):
            return mapping(chunk["usage"])
    return None


def _invalidate(state: DshUsageAdapterState, diagnostic: str) -> None:
    """Poison a discontinuous source so later rows cannot regain attribution."""

    state.source_invalid = True
    if diagnostic not in state.limitations:
        state.limitations.append(diagnostic)
    raise DshJournalError(diagnostic)


def _attempt_observation(
    payload: Mapping[str, Any],
    data: Mapping[str, Any],
    state: DshUsageAdapterState,
    context: UsageParseContext,
) -> UsageObservation:
    """Emit one settled provider attempt, selecting a single authoritative sample."""

    stream_sample = _stream_usage(data.get("stream"))
    sample = mapping(data["usage"]) if isinstance(data.get("usage"), dict) else stream_sample
    values: dict[str, UsageNumber | None] = {}
    diagnostic: str | None = None
    if sample is not None:
        try:
            values = normalize_dsh_usage(sample)
        except DshJournalError as exc:
            diagnostic = str(exc)
    source = mapping(mapping(data.get("message")).get("source"))
    provider = text_id(source.get("provider")) or state.route_provider
    model = text_id(source.get("model")) or state.route_model
    state.model = model
    complete = diagnostic is None and all(
        key in values and values[key] is not None for key in ("input_tokens", "output_tokens")
    )
    result = observation(
        state,
        context,
        payload,
        event_type=str(payload["type"]),
        values=values,
        request_id="dsh-attempt-"
        + stable_key(
            state.provider_session_id,
            state.provider_turn_id,
            state.native_step,
            state.attempt_index,
        ),
        accounting={
            "provider": provider,
            "model": model,
            "usage": {
                source_key: values[target]
                for source_key, target in _USAGE_FIELDS.items()
                if target in values
            },
        },
        semantics=DSH_TOKEN_SEMANTICS.model_copy(),
        coverage="complete" if complete else "partial" if values else "unknown",
        metadata={
            "native_step": state.native_step,
            "native_attempt": state.attempt_index,
            "model_provider": provider,
            "sample_authority": "message_usage"
            if isinstance(data.get("usage"), dict)
            else "last_stream_usage"
            if stream_sample is not None
            else "unavailable",
            **({"limitation": diagnostic} if diagnostic else {}),
        },
    )
    if state.native_subagent:
        result.is_sidechain = True
        result.metadata["parent_session_id"] = state.parent_session_id
        result.metadata["parent_inclusion"] = "unknown"
    return result


def parse_dsh(
    payload: Mapping[str, Any], state: DshUsageAdapterState, context: UsageParseContext
) -> list[UsageObservation]:
    """Read one qualified physical event with strict native attempt association."""

    if context.source_kind != "native_session_log":
        return []
    if state.source_invalid:
        raise DshJournalError("dsh_journal_source_discontinuous")
    event = payload.get("type")
    if event == "session":
        if state.header_verified:
            _invalidate(state, "dsh_journal_header_repeated")
        info = _header(payload, state.provider_session_id)
        if info.seeded and state.inherited_cut_seq is None:
            _invalidate(state, "dsh_journal_seed_boundary_unverified")
        if not info.seeded:
            state.inherited_cut_seq = -1
        state.provider_session_id = info.session_id
        state.parent_session_id = info.parent_session_id
        state.native_subagent = info.origin == "subagent"
        state.header_verified = True
        state.profile_id = DSH_JOURNAL_PROFILE
        return []
    if not state.header_verified:
        _invalidate(state, "dsh_journal_header_missing")
    sequence = _count(payload.get("seq"))
    if sequence != state.next_native_seq:
        _invalidate(state, "dsh_journal_sequence_discontinuous")
    state.next_native_seq += 1
    inherited_cut = state.inherited_cut_seq if state.inherited_cut_seq is not None else -1
    if sequence is not None and sequence <= inherited_cut:
        return []
    data = mapping(payload.get("data"))
    if event == "session/end-seed" and data.get("inherited") is True:
        _invalidate(state, "dsh_journal_seed_boundary_changed")
    if event == "request/header":
        config = mapping(mapping(data.get("header")).get("config"))
        state.route_provider = text_id(config.get("provider"))
        state.route_model = text_id(config.get("model"))
        return []
    if event == "turn/start":
        turn = _count(data.get("turn"))
        if turn is None or state.attempt_phase != "idle" or state.provider_turn_id is not None:
            _invalidate(state, "dsh_turn_boundary_invalid")
        state.provider_turn_id = str(turn)
        state.awaiting_live_turn = False
        start_observation = lifecycle_observation(state, context, payload, str(event), "started")
        start_observation.metadata["native_sequence"] = sequence
        return [start_observation]
    if event == "user/message" and state.provider_turn_id is not None:
        # Input membership is accounting evidence. Never retain its body or RPC
        # request identifier, which can contain arbitrary caller text.
        if mapping(data.get("source")).get("kind") not in {"user", "user-question-reply"}:
            return []
        message_id = text_id(data.get("id"))
        if message_id is None:
            return []
        input_observation = lifecycle_observation(state, context, payload, str(event), "started")
        input_observation.lifecycle = None
        input_observation.accounting_kind = "dsh_native_input"
        input_observation.metadata.update(native_sequence=sequence, native_message_id=message_id)
        return [input_observation]
    if event == "turn/end":
        if state.awaiting_live_turn:
            return []
        if str(data.get("turn")) != state.provider_turn_id or state.attempt_phase != "idle":
            _invalidate(state, "dsh_turn_boundary_invalid")
        reason = mapping(data.get("reason")).get("kind")
        lifecycle = (
            "completed"
            if reason == "completed"
            else "interrupted"
            if reason in {"aborted", "interrupted"}
            else "failed"
        )
        terminal = lifecycle_observation(state, context, payload, str(event), lifecycle)
        terminal.metadata["native_sequence"] = sequence
        result = [terminal]
        state.provider_turn_id = None
        return result
    if event not in {
        "step/start",
        "step/end",
        "assistant/message",
        "assistant/attempt",
        "llm/retry",
        "llm/retry-started",
    }:
        return []
    if event == "step/end" and state.awaiting_live_turn:
        return []
    if state.provider_turn_id is None or str(data.get("turn")) != state.provider_turn_id:
        _invalidate(state, "dsh_attempt_turn_mismatch")
    step = _count(data.get("step"))
    if event == "step/start":
        if step is None or state.attempt_phase != "idle":
            _invalidate(state, "dsh_attempt_step_boundary_invalid")
        state.native_step = step
        state.attempt_index = 0
        state.attempt_phase = "open"
        return []
    if step is None or step != state.native_step:
        _invalidate(state, "dsh_attempt_step_mismatch")
    if event == "llm/retry-started":
        if state.attempt_phase != "settled_retry":
            _invalidate(state, "dsh_attempt_retry_boundary_invalid")
        state.attempt_index += 1
        state.attempt_phase = "open"
        return []
    if event in {"assistant/message", "assistant/attempt"}:
        if state.attempt_phase != "open":
            _invalidate(state, "dsh_attempt_settlement_invalid")
        attempt = _attempt_observation(payload, data, state, context)
        state.attempt_phase = "settled_message" if event == "assistant/message" else "finish_closed"
        return [attempt]
    if event == "llm/retry":
        if state.attempt_phase not in {"open", "finish_closed"}:
            _invalidate(state, "dsh_attempt_retry_boundary_invalid")
        result = []
        if state.attempt_phase == "open":
            result = [_attempt_observation(payload, data, state, context)]
        state.attempt_phase = "settled_retry"
        return result
    result = []
    if state.attempt_phase == "open":
        result = [_attempt_observation(payload, data, state, context)]
    state.attempt_phase = "idle"
    state.native_step = None
    return result
