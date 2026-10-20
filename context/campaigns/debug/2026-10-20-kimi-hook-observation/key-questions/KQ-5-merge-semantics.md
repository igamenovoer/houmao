# KQ-5: Merge Semantics

Status: answered (replay phase complete, 2026-10-20). Owner: iteration 1 (replay phase, after captures). Campaign: [debug-intent.md](../debug-intent.md).

## Question

Do the archived merged hook + TUI state-transition rules (from `openspec/changes/archive/2026-10-20-add-cli-hook-observation-channel/design/state-transitions.md`, as amended by the Codex adapter change) survive replay against real kimi hook streams paired with kimi 2.1.x-detector pane recordings — and where the rules assume Claude/Codex event shapes, what kimi-specific rule variants are needed?

Source baseline: archived state-transition rules; kimi detector `KimiCodeSignalDetectorV2_1_X` at `src/houmao/shared_tui_tracking/apps/kimi_code/profile.py:335` (read-only for this campaign); captured streams from iteration 1.

## Propositions

### P5.1 Core turn lifecycle rules port

`TurnStarted`/`UserPromptSubmit` → busy, `Stop` → settle, `SessionStart`/`SessionEnd` generation boundaries, and clean-exit terminal settle all replay against S0/S1/S7 streams with zero or named mismatches. Kimi `turn_id` presence/absence per event (no `turn_id` on tool events) is handled by an explicit correlation rule. Test: replay reducer over the captures; every mismatch named.

### P5.2 Interrupted derivation from Interrupt, not TUI heuristics

The hook `Interrupt` event settles the turn as interrupted without consulting TUI Esc heuristics (the Codex adapter's precedent: hook-derived `interrupted` for the adapter only, `src/houmao/server/tui/tracking.py`). Test: S5 replay; record whether the TUI detector's own interrupt signals agree or conflict.

### P5.3 Terminal-gap fallback holds on kill

F1 (SIGKILL mid-turn): no `Stop`/`Interrupt`/`SessionEnd` arrives; heartbeat ceases; the reducer's terminal-gap fallback produces the same terminal posture as the pane's final frames allow. Test: F1 replay; record gap-detection latency against heartbeat cadence (a 60 s heartbeat makes heartbeat-loss a slow liveness signal — quantify).

### P5.4 Compaction rules use real PreCompact/PostCompact

Posture holds through `PreCompact`/`PostCompact(trigger="manual")` without the TUI repaint heuristics the pre-hook detectors needed; the post-compact turn correlation is recorded (fresh `turn_id` vs continuity — kimi's behavior is undetermined by source). Test: S4 replay.

### P5.5 Blocked posture merges cleanly in ask mode

The S3 `PermissionRequest`→`PermissionResult` window maps to the merged `blocked` state with TUI modal frames agreeing; under `--auto` the merged state never asserts blocked. Test: S3 + S1 replays.

## Answer

(2026-10-20, replay phase complete. Reducer: [`scripts/explore/kimi-hook-observation/replay_reduce.py`](../../../../../scripts/explore/kimi-hook-observation/replay_reduce.py). Evidence: [payload catalog](../evidences/2026-10-20-kimi-hook-payload-catalog.md), [S0 gate smoke](../evidences/2026-10-20-s0-gate-smoke.md), [S1 normal](../evidences/2026-10-20-s1-normal-multiturn.md), [S3 permission lane](../evidences/2026-10-20-s3-permission-lane.md), [S4 compaction](../evidences/2026-10-20-s4-compaction.md), [S5 interrupt](../evidences/2026-10-20-s5-interrupt.md), [S6 queue/steer](../evidences/2026-10-20-s6-queue-steer.md), [S7 resume](../evidences/2026-10-20-s7-resume-hot-reload.md), [S8 headless](../evidences/2026-10-20-s8-headless.md), [S9 subagent](../evidences/2026-10-20-s9-subagent.md), [F1 terminal gap](../evidences/2026-10-20-f1-sigkill-terminal-gap.md), [D1 transport fault](../evidences/2026-10-20-d1-transport-fault.md), [T1 slow lifecycle](../evidences/2026-10-20-t1-slow-lifecycle.md).)

Replay basis: `--all` reduced **18 campaign run roots** (14 with hook streams, 4 empty controls) and **113 events** with **21 label checks OK, 20 n/a, 0 mismatches**; the 17 harness G0 roots under `tmp/kimi-hook-capture/self-test/` are detected as non-campaign streams and named as skipped. `--self-test` passed **12/12** synthetic checks (normal, blocked-allow, blocked-deny, compaction, interrupt, terminal gap, resume-generation, headless-no-session-end, queue/steer, subagent scope, fallback ordering, fallback loader). The first replay surfaced exactly one expectation mismatch, which was a **catalog error, not a reducer error**: S7 generation 2 starts at `turn_id=1`, not `0` (corrected in the [payload catalog](../evidences/2026-10-20-kimi-hook-payload-catalog.md) and [S7 evidence](../evidences/2026-10-20-s7-resume-hot-reload.md)).

### P5.1 Core turn lifecycle rules port — confirmed, with one named correction

S0 (`SS → UPS → TurnStarted(0) → Stop → SessionEnd`), S1 (`3` epochs, `turn_id` 0/1/2, one Bash pair, heartbeat, clean `SessionEnd`), and S7 (two generations, same `session_id`, `SessionStart(startup)` then `SessionStart(resume)`, two epochs) all replay to `presence=lost`, `turn.phase=ready`, `last_turn=success` with no lifecycle mismatch. The archived generation rule holds: a new channel generation resets turn-scoped state, and a resumed session starts with no open turn.

Correlation rule validated: `UserPromptSubmit` arms the epoch; the following `TurnStarted(origin_kind=user)` binds `turn_id`; `Stop`/`Interrupt` settle without carrying a turn id. **No tool event carried `turn_id`** in any of the 113 replayed events (the reducer would emit `tool_event_turn_id_present`; it never fired), so tool events are attributed by stream order. Tool pairing by `tool_call_id` reproduced S1 (1 pair), S3 (2 pairs), S4 (1 pair), and S9 (1 pair). `PermissionRequest`/`PermissionResult`/`Interrupt` supplied `turn_id` as documented.

Named correction: S7's resumed generation starts at **`turn_id=1`**, not 0; the session-scoped counter continues across `--continue`. The source-derived "restarts at 0 after resume" claim is **refuted**; the reducer now expects `(0, 1)` for S7. This does not weaken the generation rule — the new generation still has no open turn and its first `TurnStarted` is a fresh epoch — but correlation must not assume `turn_id` restarts.

Named limitations: the S1 labels were left with `turn_phase=unknown`, so per-window label agreement there is `n/a` (n/a, not a mismatch); S1's stream shape and final posture are checked directly. Fresh TUI `SessionStart` is lazy (it follows the creating prompt), so a generation boundary is anchored on the `SessionStart` event, not on process launch.

### P5.2 Interrupted derivation from Interrupt, not TUI heuristics — confirmed

S5 replays `SS → UPS → TurnStarted(0) → Interrupt(0, cancelled) → SessionEnd` to `last_turn=interrupted`, `interrupts=1`, with **zero `Stop` rows**. The hook event is sufficient and immediate; no TUI Esc heuristic is needed for the posture.

TUI agreement: the pane renders `Interrupted by user` from sample `s000027` at 13:38:10, the same second as the hook `Interrupt` at 13:38:10.626. The maintained detector (`KimiCodeSignalDetectorV2_1_X`, `src/houmao/shared_tui_tracking/apps/kimi_code/profile.py:415,675-679`) matches that notice (`interrupted by user`) and suppresses it only when concurrent activity is visible. A read-only spot check with the maintained detector over those frames returns `interrupted=False, active_evidence=True` at `s000026`, then `interrupted=True, active_evidence=False` from `s000027` through `s000060`; the detector's own interrupt signal agrees with the hook settle within the 5 fps sample interval. The reducer itself does not import the detector. The archived provider-neutral rule 5 ("Hook events never settle `interrupted`") must be **amended for kimi**, exactly as the Codex adapter carved out hook-derived `interrupted`; `hook_success_tui_interrupted` remains the conflict note if a Stop had already latched (not observed).

### P5.3 Terminal-gap fallback holds on kill — confirmed

F1 canonical (`SS → UPS → TurnStarted(0)`, then silence) replays to `presence=lost`, `turn.phase=unknown`, `last_turn=none`, `terminal_gaps=1`, diagnostic `terminal_gap:stream_end:open_turn`. No `Stop`, `Interrupt`, or `SessionEnd` exists in the stream, and the pane recording ends at 7.25 s when the pane dies. The prior F1 run (12 s window) produces the same gap.

Quantified liveness: the reducer measures **73.560 s** from the last event (`TurnStarted`) to run end; the post-kill observation window alone was 70 s. **Zero heartbeats** fired — the session was killed before its first 60 s tick, so heartbeat-loss cannot be the signal for this session; the reducer names `heartbeat_liveness_unavailable`. For a session that has reached a heartbeat, the cadence is 60 s, so the earliest heartbeat-derived loss signal is one missed tick (≥60 s after the last beat); pane death / stream end is the immediate signal. Terminal-gap semantics port unchanged; presence loss is never success.

### P5.4 Compaction rules use real PreCompact/PostCompact — confirmed (idle-window case; active-turn hold unexercised)

S4 replays the real pair: `PreCompact(trigger=manual, token_count=28513)` at 13:37:32.551 and `PostCompact(trigger=manual, estimated_token_count=29056)` at 13:37:39.775 (7.224 s). The reducer holds the `ready` posture through the window (`maintenance_active` true, no epoch change) and the post-compact `UPS → TurnStarted` mints epoch 2 with **`turn_id=1`**, diagnostic `post_compaction_fresh_turn_id:0->1`; `Stop` then latches success. The source-undetermined question is settled: kimi mints a **fresh `turn_id`** for the post-compact turn.

Kimi-specific amendment: unlike Codex, kimi emits **no `SessionStart(source=compact)`** at the next turn; `PreCompact`/`PostCompact` are the only compaction signals and the post-compact prompt arrives as a normal `UserPromptSubmit`. The archived maintenance-window rule (hold posture, suppress idle heuristics) ports; the Codex amendment that a compact `SessionStart` marks the boundary does **not** apply. Named limitation: the manual `/compact` ran from an idle `ready` posture, so the "hold an armed/active turn through compaction" branch was not exercised; a budget/overflow compaction mid-turn is the missing evidence.

### P5.5 Blocked posture merges cleanly in ask mode — confirmed

S3 allow replays `PreToolUse → PermissionRequest → PostToolUse → PermissionResult(approved) → Stop`: `PermissionRequest` enters `blocked`; the intervening `PostToolUse` **does not settle** it (diagnostic `post_tool_use_during_blocked`); `PermissionResult(approved)` returns to `active` and increments `allow_settles`; `Stop` latches success. S3 deny replays `PreToolUse → PermissionRequest → PermissionResult(rejected) → PostToolUseFailure → Stop`: the result settles `blocked` to `active`, the failure is non-terminal, and the turn continues to a normal `Stop` with `last_turn=success`. Both label checks pass.

Kimi-specific amendment: **the blocked window settles at `PermissionResult`, not `PostToolUse`** (allow: result after tool execution; deny: result before `PostToolUseFailure`), and **deny is not a turn-abort** — there is no `Interrupt` and the turn continues. This differs directly from the Codex rule (deny aborts the turn). Under `--auto` the merged state never asserts blocked: the replay found **2 permission requests, both in S3**, and zero in S0/S1/S4-S9/F1/D1/T1/S2/S8. TUI agreement: the `Write this file?` panel paints at sample `s000042` (13:36:32) and `s000089` (13:36:42), the same seconds as the hook requests (32.192 and 42.637); a read-only detector spot check returns `active_evidence=True` with reasons `approval_panel, modal_blocked` and `interrupted=False` at both frames, and never `blocked` — so the hooks-only blocked entry rule is preserved.

### Unresolved (missing evidence named)

- `StopFailure`: never forced; the reducer's `known_failure` terminal rule is defensive and untested.
- `TaskStarted(kind=agent)` / `Notification(task.*)`: never emitted; the reducer counts them as unavailable diagnostics and makes no posture claim.
- `is_steer=true` and an overlapping `UserPromptSubmit`: the Ctrl-S path produced `UserPromptQueued` with no second UPS, so the FIFO armed-prompt drain in the reducer is defensive only. A queued prompt that drains as a separate turn was never observed.
- `PermissionResult(decision=cancelled|error)`: unexercised; the reducer settles blocked to active and emits `permission_result_unexercised_decision`.
- Compaction during an armed/active turn (budget/overflow trigger): unexercised.
- Background subagent outliving the parent turn, and `SubagentStop` without a nested `Stop`: the nested-scope counter handles the observed order but the alternative orders were not captured.
- `SessionStart(source=clear|fork|compact)` and `SessionEnd` reasons other than `exit`: unexercised.
- Heartbeat-derived liveness for short sessions: F1 never reached a first heartbeat; the 60 s granularity is quantified but a reducer cannot use heartbeat loss as a fast signal.
- Pane-cause-to-collector latency: bounded by the 5 fps recorder and 1 s label stamps, not measured to the millisecond (capture-phase limitation, not a merge-rule gap).
- P1.4 reverse-order config write (launch-policy field written after the `[[hooks]]` block): config-phase leftover, unrelated to the merge rules.

## Scope

Covers merged state semantics only. Payload ground truth is KQ-2; delivery gaps are KQ-3. Production tracker changes are out of scope (future OpenSpec change). Evidence: `evidences/` links added as produced.
