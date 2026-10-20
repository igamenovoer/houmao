# Evidence: Codex hook payload catalog (codex-cli 0.163.0, openlux-auto lane)

Date: 2026-10-20. Iteration: [plan 1](../iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md). Key questions: [KQ-2](../key-questions/KQ-2-event-availability-payloads.md), [KQ-3](../key-questions/KQ-3-delivery-semantics.md), [KQ-4](../key-questions/KQ-4-blocked-state-permission.md).

Computed from every iteration-1 live run (S0, S1, S2-interactive, S3, S4, S5, S6, S7, F1, T1, T2 — 73 provider events across 11 sessions) by key-set inventory over `collector/events.ndjson`; payloads were kept pristine by the emitter (no injected fields), so these inventories are the provider's own. Schema ground truth: `extern/orphan/codex/codex-rs/hooks/schema/generated/` @ `0910087`.

## Event Availability at 0.163.0 (TUI mode)

| Event | Observed | n | Notes |
| --- | --- | --- | --- |
| SessionStart | yes | 15 | `source` ∈ {startup, resume, compact}; no `turn_id`; dispatched lazily at first turn start (and at the next turn after compaction), not at process launch |
| UserPromptSubmit | yes | 18 | carries `prompt` text; fires for steered mid-turn input with the running turn's `turn_id` |
| PreToolUse | yes | 4 | canonical `tool_name` (`Bash` observed); `tool_use_id` present |
| PermissionRequest | yes | 2 | **no `tool_use_id`**; fires only in the no-approvals-bypass lane; immediately follows its `PreToolUse` (+54 ms) |
| PostToolUse | yes | 3 | adds `tool_response` (string observed); same `tool_use_id` as its `PreToolUse` |
| PreCompact | yes | 1 | `trigger: manual`; no `permission_mode` |
| PostCompact | yes | 1 | `trigger: manual`; no `permission_mode` |
| Stop | yes | 13 | `stop_hook_active: false` everywhere (no blocking hooks); `last_assistant_message` present |
| Interrupt | yes | 2 | **no reason field**; fires on Esc and on approval-modal deny; never together with `Stop` |
| SessionEnd | yes | 15 | constant `reason: "other"`; no `turn_id`, no `model`, no `permission_mode`; absent on `kill -9` |
| PreModelRequest | **never** | 0 | schema exists; 0.163.0 neither dispatches it nor includes it in the trust-review set |
| PostModelRequest | **never** | 0 | same as above; `token_usage` therefore unobtainable via hooks at 0.163.0 |
| SubagentStart | **never** | 0 | no thread-spawn subagents in the scenario matrix; availability unconfirmed, not refuted |
| SubagentStop | **never** | 0 | same as above |

## Common Envelope (observed)

- All events: `session_id` (thread UUIDv7, preserved across resume generations), `cwd`, `hook_event_name`, `transcript_path` (always non-null in these runs).
- All turn-scoped events (everything except SessionStart/SessionEnd): `turn_id` (per-turn UUIDv7; distinct across turns; compaction mints a new one for the post-compact turn; steer shares the running one), `model` (`gpt-6.1-sol` on the openlux lane).
- `permission_mode` ∈ {`bypassPermissions` (bypass lane), `default` (on-request lane)} only — matching the source claim that the other enum values are never emitted at this version.
- No event carries a provider-side timestamp; collector `received_at_utc`/`received_at_monotonic` (ms) is the only time base. No monotonic turn counter.
- No undocumented/extra fields were observed anywhere; no schema-declared field was missing except the optional `agent_id`/`agent_type` (subagent context only, correctly absent).

## Per-Event Ordering Rules (measured)

1. Turn cycle: `UserPromptSubmit` → (`PreToolUse` → [`PermissionRequest`] → `PostToolUse`)×N → `Stop`.
2. `SessionStart(source=startup|resume)` precedes the generation's first `UserPromptSubmit` by ~50-110 ms; `SessionStart(source=compact)` is queued during compaction and dispatched at the NEXT turn start, before its `UserPromptSubmit`.
3. `PermissionRequest` fires ~50 ms after its `PreToolUse` and before the TUI modal's first captured frame; on allow the next event is `PostToolUse` with the same `tool_use_id` (blocked interval measured 457 ms); on deny the next event is `Interrupt` (63 ms after the Esc keypress) with no `PostToolUse` and no `Stop`.
4. Steered input: second `UserPromptSubmit` arrives ~2.9 s after typing (mid-turn, same `turn_id`), ~10.8 s before the single `Stop`; there is no queued second turn at 0.163.0.
5. Esc mid-generation: `Interrupt` 48 ms after the keypress, no `Stop`; TUI shows `Conversation interrupted` and an empty composer (no draft restore).
6. `kill -9`: no `Stop`, no `Interrupt`, no `SessionEnd` — the stream simply ends; collector heartbeat continues (terminal-gap fallback signature).
7. Clean exit (`/quit`): `SessionEnd` within ~60-600 ms of the command.

## Deviations from the Source-Derived Catalog

1. `PreModelRequest`/`PostModelRequest` do not fire at 0.163.0 despite the shared schema and the `HOOK_EVENT_NAMES` listing; they are also absent from the trust-review set (12 of 14 entries written by trust-all). Treat them as unavailable at the installed version; `token_usage` has no hook source.
2. The approval modal at 0.163.0 has no "No, continue without running it" option; deny is option 3 (`No, and tell Codex what to do differently`, Esc), which aborts the turn (`Interrupt`), not just the tool call. This changes the blocked-state settle rule: deny = turn abort.
3. `PermissionRequest.tool_input` carries a `description` justification field not present on the paired `PreToolUse.tool_input`.
4. Compaction does not preserve `turn_id` continuity: the post-compact turn gets a fresh `turn_id` (session id preserved).
