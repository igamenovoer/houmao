# KQ-2: Event Availability and Payload Catalog

Status: resolved (iteration 1, 2026-10-20; named leftovers: `apply_patch` payload shape, SubagentStart/SubagentStop availability, model-request events refuted at 0.163.0). Owner: iteration 1. Campaign: [debug-intent.md](../debug-intent.md).

## Question

Which of the 14 Codex hook events actually fire in TUI mode at the installed version (0.163.0), and what are the exact observed payloads per event — confirming or correcting the source-derived catalog?

Source baseline: generated schemas at `codex-rs/hooks/schema/generated/`; dispatch sites in `codex-rs/core/src/hook_runtime.rs`, `session/turn.rs`, `compact.rs`, `session/handlers.rs`.

## Propositions

### P2.1 Lifecycle events fire as documented

`SessionStart(source=startup)`, `UserPromptSubmit`, `Stop`, and `SessionEnd(reason="other")` fire in S1 with the documented envelope fields (`session_id`, `turn_id` where applicable, `cwd`, `hook_event_name`, `model`, `transcript_path`, `permission_mode`). Test: diff observed payloads against the generated schemas; record every absent/extra/null field.

### P2.2 Turn correlation works as documented

`turn_id` is present and identical across `UserPromptSubmit`, `Pre/PostModelRequest`, `Pre/PostToolUse`, and `Stop` of one turn, and changes across turns. Test: S1 two-turn session; group events by `turn_id` and verify grouping matches the labeled turn boundaries. Record whether a `PermissionRequest` in the same turn can be associated despite lacking `tool_use_id`.

### P2.3 Tool events carry usable payloads

`PreToolUse`/`PostToolUse` fire for shell (`Bash`) and file-edit (`apply_patch`) tools with `tool_use_id` pairing and canonical tool names. Test: S1 frozen prompt forces at least one shell command and one file edit; record `tool_name`, `tool_input` shape, `tool_response` presence.

### P2.4 Compaction events fire with real signals

Manual `/compact` emits `PreCompact`/`PostCompact(trigger="manual")` and a follow-up `SessionStart(source="compact")`. Test: S4; record payload fields and ordering against the TUI compaction indicator.

### P2.5 Interrupt and terminal gaps confirmed

Esc mid-turn emits `Interrupt` and no `Stop`; process kill emits neither `Stop` nor `SessionEnd`. Test: S5 plus one kill -9 on a live session (fault arm); record exactly which events arrive and the session's terminal posture evidence.

### P2.6 Model-request events fire per sampling step

`PreModelRequest`/`PostModelRequest` fire at least once per turn, possibly multiple times (retries, multi-step), with `status` and `token_usage` on the post event. Test: count them per turn in S1; record the observed `token_usage` object shape.

## Answer

Iteration 1, 2026-10-20, codex-cli 0.163.0. Full inventory: [payload catalog](../evidences/2026-10-20-codex-hook-payload-catalog.md).

- **P2.1 confirmed.** `SessionStart`, `UserPromptSubmit`, `Stop`, `SessionEnd` all fire with the documented envelope; `SessionEnd` is constant `reason: "other"` and lacks `turn_id`/`model`/`permission_mode`. One timing correction: `SessionStart` is lazy — dispatched at first turn start, not process launch.
- **P2.2 confirmed.** `turn_id` is identical across all events of one turn and distinct across turns (verified in S1/S4/S7); a mid-turn steer shares the running turn's id; resume keeps `session_id` and mints a new `turn_id`; compaction ends turn-id continuity (the post-compact turn gets a fresh id). `PermissionRequest` associates with its turn via `turn_id` despite lacking `tool_use_id`; call-level pairing uses the immediately preceding `PreToolUse` (see KQ-4 P4.5).
- **P2.3 partially confirmed.** `PreToolUse`/`PostToolUse` fire with `tool_use_id` pairing and canonical names — but only `Bash` was observed across all runs; the frozen prompts never induced `apply_patch`, so its payload shape (and the `Write`/`Edit` matcher-alias behavior) is **uncaptured** and named as an iteration-2 leftover.
- **P2.4 confirmed.** Manual `/compact` emits `PreCompact`/`PostCompact(trigger="manual")` (no `permission_mode`), and `SessionStart(source="compact")` follows — queued during compaction, dispatched at the next turn start before its `UserPromptSubmit`.
- **P2.5 confirmed.** Esc emits `Interrupt` (48 ms after the keypress) and no `Stop`; `kill -9` emits nothing further — no `Stop`, `Interrupt`, or `SessionEnd`; the stream simply ends while the collector heartbeat continues.
- **P2.6 refuted at 0.163.0.** `PreModelRequest`/`PostModelRequest` never fired in any of 11 sessions (tool-using, compaction, interrupt, and resume turns included), and 0.163.0 excludes both from the trust-review install set. The shared `model-request` schema exists, but the events are unavailable at the installed version; `token_usage` has no hook source. Availability of `SubagentStart`/`SubagentStop` is unconfirmed (no thread-spawn subagents exercised).

Summary: 10 of 14 events confirmed live; 2 (model-request) refuted at 0.163.0; 2 (subagent) unexercised. No undocumented fields observed; optional `agent_id`/`agent_type` correctly absent outside subagent context.

## Scope

Covers event availability and payload shape at the installed version only. Delivery/ordering/timing is KQ-3; state-machine meaning is KQ-5. Evidence: `evidences/` links added as produced.
