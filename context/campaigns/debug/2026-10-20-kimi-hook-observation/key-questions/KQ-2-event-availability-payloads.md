# KQ-2: Event Availability and Payload Catalog

Status: answered (2026-10-20); named unresolved items remain where marked. Owner: iteration 1. Campaign: [debug-intent.md](../debug-intent.md).

## Question

Which of the 20 kimi hook events actually fire at the installed version (2.2.0) in each mode houmao uses (unattended `--auto` TUI, ask-mode TUI, headless `-p`), and what are the exact observed payloads per event — confirming or correcting the source-derived catalog?

Source baseline: event list `HOOK_EVENT_TYPES` at `extern/orphan/kimi-code/packages/agent-core-v2/src/features/externalHooks/internal/types.ts:3-24` (@ `67325c1`); per-event payload assembly at `agent/agentExternalHooksService.ts` and `session/sessionExternalHooksService.ts`; base fields at `internal/matchHooks.ts:60-65,124-134`.

## Propositions

### P2.1 Lifecycle events fire awaited, at create/close

`SessionStart(source=startup)` fires during session creation (awaited, before any prompt — unlike Codex 0.163's lazy first-turn dispatch) with `model` and `profile`; `SessionEnd(reason=exit)` fires awaited at clean close. Test: S0/S1 timing against pane frames and launch wall clock; record whether `SessionStart` precedes the ready composer.

### P2.2 Prompt and turn events carry the documented shapes

`UserPromptSubmit` carries `prompt` as a raw ContentPart[] array plus `is_steer`; `TurnStarted` carries `turn_id`, `origin_kind`, optional `origin_name`/`prompt`; `Stop` fires at normal turn end with `stop_hook_active` always `false`. Test: S1 two-turn session, S6 steer; diff observed fields against the source-derived schema and record every absent/extra/null field.

### P2.3 Tool events pair by tool_call_id

`PreToolUse`/`PostToolUse` fire for the forced `Bash` call with identical `tool_call_id`, raw `tool_input` object, and `tool_output` truncated to 2000 chars; `PostToolUseFailure` carries `error` (`{code, message, name?, details?, retryable, cause?}`). Note: source says `turn_id` is NOT present on tool events — correlation to turns must go through event ordering. Test: S1; verify pairing and record the `tool_input`/`tool_output` shapes verbatim (structure only).

### P2.4 Permission events fire only under ask policy

`PermissionRequest`/`PermissionResult` never fire under `--auto` (S0/S1/S4-S8 control), and fire in ask-mode S3 with `decision` in {`approved`, `rejected`, `cancelled`, `error`}, `tool_call_id`, `agent_id`, `turn_id`, `action`, `display`, and on the result optionally `scope`/`feedback`/`selected_label`. Test: S3 approve-then-deny; record both decisions and the deny path's follow-up events.

### P2.5 Compaction, interrupt, and heartbeat signals confirmed

Manual `/compact` emits `PreCompact`/`PostCompact(trigger="manual")` with `token_count`/`estimated_token_count`; Esc mid-turn emits `Interrupt(turn_id, reason="cancelled")` and no `Stop`; `SessionHeartbeat` fires every ~60 s with `uptime_ms` only because a heartbeat hook is configured. Test: S4, S5, and the ≥65 s hold in S1; record cadence jitter on the heartbeat.

### P2.6 Queue, resume, headless, subagent, notification

`UserPromptQueued` on busy-turn input carries `prompt_id`, `prompt` (ContentPart[]), `queue_length`; resume emits `SessionStart(source="resume")`; hooks fire identically under `kimi -p`; a Task-tool subagent emits `SubagentStart`/`SubagentStop` and `TaskStarted(kind="agent")`; a background task status change emits `Notification(task.<status>)`. Test: S6, S7, S8, and optional S9; any event family not exercised is named as a leftover.

## Answer

(2026-10-20, full capture matrix executed. Evidence: [payload catalog](../evidences/2026-10-20-kimi-hook-payload-catalog.md), [S0 gate smoke](../evidences/2026-10-20-s0-gate-smoke.md), [S1 normal](../evidences/2026-10-20-s1-normal-multiturn.md), [S3 permission lane](../evidences/2026-10-20-s3-permission-lane.md), [S4 compaction](../evidences/2026-10-20-s4-compaction.md), [S5 interrupt](../evidences/2026-10-20-s5-interrupt.md), [S6 queue/steer](../evidences/2026-10-20-s6-queue-steer.md), [S7 resume](../evidences/2026-10-20-s7-resume-hot-reload.md), [S8 headless](../evidences/2026-10-20-s8-headless.md), [S9 subagent](../evidences/2026-10-20-s9-subagent.md).)

- **P2.1 — confirmed with a corrected timing anchor.** `SessionStart(source=startup)` fires awaited at session creation: 0.226–0.266 s after the creating prompt in every fresh TUI arm, before `UserPromptSubmit` and `Stop`. It does **not** fire at process launch: 2.2.0's TUI is session-less until the first message. Resume is the exception: `--continue` restores the session at launch and emitted `SessionStart(source=resume)` 0.796 s after the resume launch, before the post-resume prompt. `model` (`kimi-code/k3-256k`) and `profile` (`agent`) are present; a fresh `SessionStart` has no `session_title` (it does not exist yet), while the resume event carries the restored title.
- **P2.2 — confirmed with shape corrections.** `UserPromptSubmit.prompt` is a raw `ContentPart[]`; `is_steer` is present (`false` in every observed UPS). `TurnStarted` carries `turn_id` (0-based **integer**), `origin_kind` (`user` / `system_trigger`), optional `origin_name`, and `prompt` as a plain string. `Stop` has `stop_hook_active=false` but **no `turn_id` and no `prompt_id`**; correlation is by event order. `session_title` is fixed at the first prompt and repeated. A Ctrl-S steered message produced `UserPromptQueued` but **no** UPS, so `is_steer=true` is unconfirmed. Dated correction (2026-10-20, replay): the session-scoped counter **continues across resume** (S7 gen 2 starts at `turn_id=1`); the earlier "restarts at 0" note is refuted by `raw-provider-payloads.ndjson`.
- **P2.3 — confirmed.** `PreToolUse`/`PostToolUse` pair by identical `tool_call_id` for Bash, Write, Read, and Agent; neither carries `turn_id`. `tool_input` is a raw object (`{command}`, `{content,path}`, `{path}`, `{description,prompt}`); `tool_output` is a **string**. `PostToolUseFailure` exists only on S3's deny path and carries `error={code,message,retryable}`; `name`/`details`/`cause` were absent.
- **P2.4 — confirmed.** Permission events never fired under `--auto` or print mode. In ask mode S3 captured `PermissionRequest`/`PermissionResult` with `decision=approved` and `rejected`, pairing by `tool_call_id` and approval `id`; the payload also carries `agent_id`, `action`, and `display`. `scope`/`feedback`/`selected_label` were absent. The deny path settles with `PermissionResult` then `PostToolUseFailure`, then `Stop`.
- **P2.5 — confirmed.** `/compact` emitted `PreCompact(trigger=manual, token_count=28513)` and `PostCompact(trigger=manual, estimated_token_count=29056)` across a 7.224 s window; the post-compact turn used a fresh `turn_id=1`. Esc emitted `Interrupt(turn_id=0, reason=cancelled)` with no `Stop`. `SessionHeartbeat` fired on the 60 s timer with `uptime_ms` 60001/120000/180001/240001/300000.
- **P2.6 — partially confirmed.** Queue: Ctrl-S produced `UserPromptQueued(prompt_id, queue_length=1)`; the steered message was injected into the running turn with no second UPS and one `Stop`. Resume: `SessionStart(source=resume)` with the same `session_id`. Headless: all four turn events fire, but **no `SessionEnd`**. Subagent: `SubagentStart`/`SubagentStop(agent_name=explore, response=OK)` fire, but **`TaskStarted` did not** and `Notification` was not exercised. `StopFailure` was never forced.

Unresolved payload families: `StopFailure` (no forcing arm), `TaskStarted(kind=agent)` (Agent tool produced none), `Notification` (no background task), `is_steer=true` (Ctrl-S path has no UPS), and `PermissionResult` values `cancelled`/`error`. The complete field inventory and the diff against the source-derived catalog are in the [payload catalog](../evidences/2026-10-20-kimi-hook-payload-catalog.md).

## Scope

Covers event availability and payload shape at the installed version only. Delivery/ordering/timing is KQ-3; state-machine meaning is KQ-5. Evidence: `evidences/` links added as produced.
