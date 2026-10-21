# Kimi State Transition Rules

Date: 2026-10-20. Source: campaign-validated amendments in `context/campaigns/debug/2026-10-20-kimi-hook-observation/` (KQ-2 through KQ-5 answers, the payload catalog, and the synthesis report), replayed against 14 captured streams (113 events) with zero label mismatches by `scripts/explore/kimi-hook-observation/replay_reduce.py`. These rules amend the provider-neutral model from the archived `2026-10-20-add-cli-hook-observation-channel/design/state-transitions.md` for the Kimi adapter; sections not amended here continue to apply unchanged.

## 1. Axes and Correlation

The three-axis model (presence, turn phase, work) is unchanged. Correlation for Kimi is identifier-and-ordering based:

- **Session**: `session_id`. Continues across `--continue` resume generations; a new channel generation still resets turn state.
- **Turn epoch**: two-phase arm/bind. `UserPromptSubmit` arms a new epoch; the following `TurnStarted(origin_kind=user)` binds the integer `turn_id`. Kimi `turn_id` is session-scoped and **continues across resume** (generation 2 of a resumed session starts at 1, not 0). `turn_id` is absent on `UserPromptSubmit`, `Stop`, and all tool events — those attribute to the currently armed epoch by stream ordering.
- **Tool call**: `tool_call_id` pairs `PreToolUse`/`PostToolUse`/`PostToolUseFailure` and is also present on `PermissionRequest`/`PermissionResult`, so permission attribution is identifier-based with no pair-back heuristic.
- **Queued input**: `UserPromptQueued` (`prompt_id`, `queue_length`) records queue evidence only; steered input lands in the running turn without a second `UserPromptSubmit`, and the turn completes once.
- **Subagents**: `SubagentStart`/`SubagentStop` and nested `TurnStarted(origin_kind=system_trigger)` open and close nested scopes; subagent `turn_id` values collide with the parent's, so scope, not id, disambiguates.
- **Work axis**: no Kimi signal exists (`Stop` has no background-task payload; `SessionHeartbeat` is liveness only). `work` remains `unknown`; the channel never claims `settled` from hooks alone.

## 2. Turn Phase Transitions (hook authority)

- `UserPromptSubmit` → `turn.phase=active`, arms a new epoch.
- `TurnStarted(origin_kind=user)` → binds the epoch's `turn_id`.
- `PermissionRequest` → `turn.phase=blocked` (hooks-only entry; the provider is asking the operator for an action). Only fires under an ask permission policy; never-ask sessions never enter `blocked`.
- Blocked settles at `PermissionResult`: `approved` → `turn.phase=active`, the tool proceeds to `PostToolUse` (the result may arrive after it); `rejected` → `turn.phase=active`, the following `PostToolUseFailure` is non-terminal evidence and the turn continues to a normal `Stop`. Kimi has no deny-aborts-turn semantics.
- `PreCompact` opens a maintenance window; `PostCompact` closes it. Posture is held through the window and TUI idle heuristics are suppressed across it. Kimi emits no `SessionStart(source=compact)`; the post-compaction turn binds a fresh `turn_id`, so the window never extends an old epoch.
- `Stop` → terminal success (Section 3). `stop_hook_active=true` would mean a hook continued the turn; treat that `Stop` as non-terminal and stay `active` (defensive rule; never observed, no blocking hooks are installed).
- `Interrupt` → terminal interrupted (Section 3).
- `SessionEnd` → presence lost. With no open turn this is a clean close; with an open turn it is the terminal-gap class (Section 4). Headless `-p` sessions may omit `SessionEnd` after a completed `Stop`; that gap is diagnostic only (Section 4).

## 3. Last-Turn Settlement

- `Stop` latches `last_turn.result=success` with `last_turn.source=hook_observation` (unless explicit-input evidence correlates the same turn, per the provider-neutral rule).
- `Interrupt(reason=cancelled)` settles `last_turn.result=interrupted` from hook evidence — the Kimi adapter's carve-out from the TUI-derived-interrupted rule, shared with the Codex adapter. The hook event follows the Esc cause within ~50 ms; the TUI repaint is corroboration, not authority.
- Terminal latch: a latched outcome stands for the epoch; `Interrupt` is the only event allowed to override a not-yet-latched active epoch, and nothing overrides a latched outcome within the same epoch.
- `last_turn` is never settled by `SessionEnd`, stream end, heartbeat cessation, or collector silence.

## 4. Staleness and Terminal Gaps

- Stream end (provider exit) without `Stop`/`Interrupt`/`SessionEnd` for an open turn: `presence=lost`, `turn.phase=unknown`, `last_turn=none` for that turn, diagnostic `terminal_gap`. Collector-heartbeat liveness attributes the gap to the provider; kimi `SessionHeartbeat` cessation is supplementary liveness evidence at 60 s cadence granularity.
- `SessionEnd` with an open turn: same outcome, diagnostic `session_end_with_open_turn`.
- Headless `-p` runs that exit cleanly (rc 0) after a latched `Stop` but without `SessionEnd` are terminal-settled with diagnostic `headless_session_end_gap` (measured at 2.2.0: no `SessionEnd` within 30 s of exit).
- Presence loss is never turn success.

## 5. Generation and Resume

- Every provider start opens a new channel generation; `SessionStart(source=startup|resume)` establishes presence for the generation. Old-generation events never arm or complete turns in the new generation (provider-neutral rule, unchanged).
- Kimi TUI sessions are created lazily on the first message: `SessionStart(source=startup)` arrives after the first prompt, not at process launch. On resume it arrives before the first prompt. Startup event silence is therefore judged after the first prompt, never at launch.
- `session_id` and the integer `turn_id` counter continue across resume generations, but turn STATE does not: a resumed session starts with no open turn and `last_turn=none` until new hook evidence arrives.

## 6. Degraded Channel

While the channel is `unavailable` or `degraded` (install/validation failure, collector death, startup event silence after the first prompt), every hook-owned fact reverts to TUI-only reduction exactly as the Claude lane specifies: no `blocked`, no hook terminal settlement, `work=unknown`, and TUI idle heuristics resume their normal authority.

## 7. Amendments Registered Against the Archived Provider-Neutral Rules

1. Turn correlation is two-phase arm/bind (`UserPromptSubmit` arms, `TurnStarted` binds the integer `turn_id`); tool events, `Stop`, and `UserPromptSubmit` carry no `turn_id` and attribute by ordering within the armed epoch.
2. `Interrupt` is a hook event that settles `interrupted` (extends the Codex carve-out to Kimi; Claude interrupted stays TUI-derived).
3. Permission denial is non-terminal for Kimi: `PermissionResult(rejected)` settles `blocked`, `PostToolUseFailure` records the denied call, and the turn continues to `Stop` (contrast the Codex deny-aborts-turn rule).
4. The permission window settles at `PermissionResult`; on the allow path the result may arrive after `PostToolUse`. Permission events carry both `tool_call_id` and `turn_id`, so no pair-back heuristic is needed.
5. Permission events exist only under an ask permission policy; never-ask sessions produce none, which is normal absence, not a channel fault.
6. Compaction holds posture across the window; the post-compaction turn binds a fresh `turn_id`; Kimi emits no `SessionStart(source=compact)`.
7. Queued/steered input surfaces as `UserPromptQueued` only; no second `UserPromptSubmit` arrives and the running turn completes once.
8. Subagent activity opens nested scopes (`SubagentStart`/`SubagentStop`, nested `TurnStarted`); `turn_id` collides across scopes and does not disambiguate them.
9. `SessionHeartbeat` is presence/liveness evidence only (60 s cadence, only while subscribed); the `work` axis stays `unknown`.
10. Headless `-p` sessions may omit `SessionEnd` after a completed `Stop` (`headless_session_end_gap`).
11. `SessionStart` timing is lazy in the TUI (awaited at first-message session creation) and immediate on resume; the integer `turn_id` counter continues across resume generations.
