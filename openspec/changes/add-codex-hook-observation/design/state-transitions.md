# Codex State Transition Rules

Date: 2026-10-20. Source: campaign-validated amendments in `context/campaigns/debug/2026-10-20-codex-hook-observation/` (KQ-4, KQ-5 answers and the iteration-1 report), replayed against 13 captured streams with zero label mismatches by `scripts/explore/codex-hook-observation/replay_reduce.py`. These rules amend the provider-neutral model from the archived `2026-10-20-add-cli-hook-observation-channel/design/state-transitions.md` for the Codex adapter; sections not amended here continue to apply unchanged.

## 1. Axes and Correlation

The three-axis model (presence, turn phase, work) is unchanged. Correlation for Codex is identifier-based, not time-window-based:

- **Session**: `session_id` (thread UUIDv7). Preserved across resume generations; a new channel generation still resets turn state.
- **Turn epoch**: `turn_id`. Absent on `SessionStart`/`SessionEnd`. A second `UserPromptSubmit` with the running turn's `turn_id` is a **steer**: it stays in the same epoch, records prompt-input evidence, and does not arm a new turn. There is no queued-second-turn semantics at the supported floor.
- **Tool call**: `tool_use_id` pairs `PreToolUse`/`PostToolUse`. `PermissionRequest` carries no `tool_use_id`; pair it to the immediately preceding `PreToolUse` in the same `turn_id` with equal `tool_name`, verified by `tool_input.command` equality when more than one candidate exists.
- **Work axis**: no Codex signal exists (`Stop` has no `background_tasks`). `work` remains `unknown`; the channel never claims `settled` from hooks alone.

## 2. Turn Phase Transitions (hook authority)

- `UserPromptSubmit` → `turn.phase=active`, epoch = its `turn_id`.
- `PermissionRequest` → `turn.phase=blocked` (hooks-only entry; the provider is asking the operator for an action). Record the paired tool from the `PreToolUse` pair-back.
- Blocked settles on the paired `PostToolUse` (allow path) → `turn.phase=active`; or on `Interrupt` (deny path) → terminal interrupted (Section 3). At the supported floor, modal deny aborts the whole turn — there is no deny-and-continue path.
- `PreCompact` opens a maintenance window; `PostCompact` closes it. Posture is held through the window and TUI idle heuristics are suppressed across it. `SessionStart(source=compact)` arrives at the NEXT turn start and marks the compaction boundary; the post-compact turn gets a fresh `turn_id`, so the window never extends an old epoch.
- `Stop` → terminal success (Section 3). `stop_hook_active=true` would mean a hook continued the turn; treat that `Stop` as non-terminal and stay `active` (defensive rule; never observed, no blocking hooks are installed).
- `Interrupt` → terminal interrupted (Section 3).
- `SessionEnd` → presence lost. With no open turn this is a clean close; with an open turn it is the terminal-gap class (Section 4).

## 3. Last-Turn Settlement

- `Stop` latches `last_turn.result=success` with `last_turn.source=hook_observation` (unless explicit-input evidence correlates the same turn, per the provider-neutral rule).
- `Interrupt` settles `last_turn.result=interrupted` from hook evidence — the Codex adapter's carve-out from the TUI-derived-interrupted rule, covering Esc mid-turn and approval-modal deny alike. The hook event follows the cause within ~50-65 ms; the TUI repaint is corroboration, not authority.
- Terminal latch: a latched outcome stands for the epoch; `Interrupt` is the only event allowed to override a not-yet-latched active epoch, and nothing overrides a latched outcome within the same epoch.
- `last_turn` is never settled by `SessionEnd`, stream end, or collector silence.

## 4. Staleness and Terminal Gaps

- Stream end (provider exit) without `Stop`/`Interrupt`/`SessionEnd` for an open turn: `presence=lost`, `turn.phase=unknown`, `last_turn=none` for that turn, diagnostic `terminal_gap`. Collector-heartbeat liveness attributes the gap to the provider.
- `SessionEnd` with an open turn: same outcome, diagnostic `session_end_with_open_turn` (observed live on a provider 402).
- Presence loss is never turn success.

## 5. Generation and Resume

- Every provider start opens a new channel generation; `SessionStart(source=startup|resume)` establishes presence for the generation. Old-generation events never arm or complete turns in the new generation (provider-neutral rule, unchanged).
- `session_id` continuity across resume does NOT preserve turn state: a resumed session starts with no open turn and `last_turn=none` until new hook evidence arrives.

## 6. Degraded Channel

While the channel is `unavailable` or `degraded` (install failure, collector death, startup event silence), every hook-owned fact reverts to TUI-only reduction exactly as the Claude lane specifies: no `blocked`, no hook terminal settlement, `work=unknown`, and TUI idle heuristics resume their normal authority.

## 7. Amendments Registered Against the Archived Provider-Neutral Rules

1. `turn_id` replaces time-window correlation; steer stays in the same epoch (no queued turns).
2. `Interrupt` is a hook event that settles `interrupted` (Claude has no such event; its interrupted stays TUI-derived).
3. Deny at the Codex approval modal aborts the whole turn; blocked settles on `PostToolUse` (allow) or `Interrupt` (deny).
4. `PermissionRequest` pairs back to the preceding `PreToolUse` (no `tool_use_id` on the request); `tool_input` adds a `description` field.
5. Compaction mints a new turn epoch; `SessionStart(compact)` is dispatched at the next turn start.
6. `PreModelRequest`/`PostModelRequest` are unavailable at the supported floor; token usage has no hook source.
7. The `work` axis has no Codex signal; it stays `unknown`.
8. Terminal-gap and `session_end_with_open_turn` fallbacks land on truthful `unknown`, never success.
9. `stop_hook_active=true` marks a non-terminal `Stop` (defensive).
10. `SessionStart` is lazy: dispatched at first turn start (and at the next turn after compaction), not at process launch.
