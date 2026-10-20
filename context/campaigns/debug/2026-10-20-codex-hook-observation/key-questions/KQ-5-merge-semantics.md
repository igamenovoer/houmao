# KQ-5: Merge Semantics with TUI Tracking

Status: resolved (iteration 1 replay, 2026-10-20; all 11 primary runs plus two auxiliary runs replayed, label checks pass). Owner: iteration 1 (replay). Campaign: [debug-intent.md](../debug-intent.md). Replay tool: `scripts/explore/codex-hook-observation/replay_reduce.py`. Evidence: [merge replay report](../reports/2026-10-20-iteration-1-merge-replay.md).

## Question

Do the merged-state transition rules designed for Claude (archived at `openspec/changes/archive/2026-10-20-add-cli-hook-observation-channel/design/state-transitions.md`) reproduce against real paired Codex hook + TUI streams, and what Codex-specific amendments are required?

Baseline rules under test: three-axis model (presence, prompt, work) with the hooks-only `blocked` phase; terminal latch with interrupt-only override; supersede-on-overlap; correction-after-staleness; turn-epoch scoping of TUI idle heuristics (the fix from the Claude lane's live smoke, where compaction repaints falsely flipped `success` to `interrupted`).

## Propositions

### P5.1 Hook authority ports with turn_id

The reducer maps `UserPromptSubmit` -> busy, `Stop` -> turn terminal success, `Interrupt` -> interrupted, `PermissionRequest` -> blocked, `SessionStart`/`SessionEnd` -> presence, using `turn_id` for correlation instead of the Claude lane's time-window heuristic, with equal or better label agreement against the paired TUI stream. Test: replay S1/S5/S6 streams; measure agreement against manual labels.

### P5.2 Compaction no longer needs TUI repaint heuristics

With `PreCompact`/`PostCompact` observed (KQ-2 P2.4), the reducer holds posture through compaction without the `silent_abort_idle` failure class that required turn-epoch scoping in the Claude lane. Test: replay S4; verify no false `interrupted` flip and posture continuity.

### P5.3 Terminal gaps have named fallbacks

For terminations with no hook event (kill, crash, `Replaced`/`BudgetLimited` abort reasons per source reading), the reducer's fallback (collector-heartbeat loss, TUI staleness, or explicit unknown) is demonstrated by fault injection. Test: replay the P2.5 kill arm; record which signal lands first and whether the resulting state is truthful.

### P5.4 Background and queued work semantics are documented

Codex behavior analogous to Claude's background-task lane (control returned to the user while work continues, queued follow-up steered mid-turn) is captured and the `work` axis behavior on `Stop` with pending/queued work is recorded. Test: replay S6; if Codex exposes a background-task feature in TUI at 0.163.0, add a fault arm exercising it; otherwise record the gap as out-of-scope with evidence.

### P5.5 Rule amendments are dated and minimal

Every divergence from the archived rules found in P5.1-P5.4 is recorded as a dated amendment proposal for the future OpenSpec change, not silently patched into the reducer. Test: campaign report contains the full amendment list with evidence links.

## Answer

Iteration 1 replay, 2026-10-20, codex-cli 0.163.0, openlux-auto lane. Tool: `scripts/explore/codex-hook-observation/replay_reduce.py` (stdlib only, deterministic from the stream's own `received_at_monotonic`). It replayed S0, S1, S2-interactive, S3, S4, S5, S6, S7, F1, T1, T2 plus the S2-control (empty stream) and S0-GAC (402, superseded) cases. Every stream-shape/final-state expectation passed, and every hook-observable label window passed; pre-channel and TUI-only trust labels are reported as n/a because hooks cannot see them. Full output: `tmp/codex-hook-capture/replay-all.log`; per-event timelines: `tmp/codex-hook-capture/replay-all-timeline.log`; report: [2026-10-20-iteration-1-merge-replay.md](../reports/2026-10-20-iteration-1-merge-replay.md).

- **P5.1 confirmed, with `turn_id` as the correlation key.** S1 produced two epochs, with all events of each turn sharing one `turn_id`, and two `Stop` successes; S5 settled `interrupted` with no `Stop`; S6's mid-turn second `UserPromptSubmit` stayed in the same epoch (one `Stop`, no queued turn); S3's allow and deny cycles paired one-to-one; S7 resumed with the same `session_id`, a new generation, and a new turn epoch. No time-window heuristic was needed. Label agreement: all turn-boundary, blocked, interrupt, and kill windows matched the replay, with a ±3 s terminal lookahead because the hook terminal can arrive after the visible TUI frame.
- **P5.2 confirmed: compaction needs no TUI repaint heuristic.** S4 replayed as `Stop(success)` → `PreCompact(maintenance)` → `PostCompact` → `SessionStart(compact)` → new epoch → `Stop(success)`. Posture was held through the 11.57 s compaction window, the compaction events carried a separate `turn_id` that never became an active turn epoch, and there was no false `interrupted` flip (the `silent_abort_idle` failure class did not occur). Label `s4-compact` agreed.
- **P5.3 confirmed: terminal gaps have a truthful fallback.** F1's stream ended after `UserPromptSubmit` with no `Stop`/`Interrupt`/`SessionEnd`. `finish()` emitted `terminal_gap`, set presence `lost`, turn phase `unknown`, and `last_turn=none`; the collector heartbeat remained alive (`last_heartbeat` 04:26:00.897) and the pane recorder failed to resolve the vanished pane, so the gap is attributable to the agent, not the collector. The auxiliary S0-GAC case (provider 402, then `SessionEnd` with an open turn) produced the same truthful unknown result with `session_end_with_open_turn`. Presence loss is never treated as turn success.
- **P5.4 recorded as a provider gap, with steer semantics confirmed.** S6's second prompt is a steer in the running turn (`UserPromptSubmit` before the single `Stop`, same `turn_id`), not a queued turn. Codex 0.163.0 `Stop` has no `background_tasks` field, so the reducer keeps `work=unknown` and `settled` is not derivable from hooks alone; no background-task feature was exercised. The amendment list below proposes the capability decision for the future adapter.

### P5.5 Amendment list (dated 2026-10-20)

1. **Correlation:** replace the Claude time-window fallback with `turn_id` as the turn epoch. A second `UserPromptSubmit` with the same `turn_id` is a steer in the same epoch and does not mint a turn; no FIFO queued-turn model is needed at 0.163.0. Evidence: S1, S6, S7; [S6 evidence](../evidences/2026-10-20-s6-queue-steer.md).
2. **Blocked settle:** pair `PermissionRequest` with the immediately preceding `PreToolUse` in the same `turn_id`/`tool_name` with equal `tool_input.command`; `PermissionRequest` has no `tool_use_id`. Allow settles on `PostToolUse` carrying that `PreToolUse`'s `tool_use_id`; deny settles on `Interrupt` and aborts the whole turn, with no `PostToolUse` and no `Stop`. The archived "PreToolUse after allow" wording is wrong for Codex. Evidence: [S3 evidence](../evidences/2026-10-20-s3-permission-lane.md), [KQ-4](KQ-4-blocked-state-permission.md).
3. **Compaction:** `PreCompact`/`PostCompact` open and close a maintenance window that holds posture; the compaction operation carries its own `turn_id`; `SessionStart(source="compact")` is dispatched at the next turn start and marks the boundary; the post-compact turn receives a fresh `turn_id`. TUI idle/repaint heuristics must be suppressed across the window, but the `silent_abort_idle` workaround is not needed when these events are present. Evidence: [S4 evidence](../evidences/2026-10-20-s4-compaction.md).
4. **Model-request events:** `PreModelRequest`/`PostModelRequest` are unavailable at 0.163.0 (zero events in every run; not in the 12-handler review set). The adapter must count them as unsupported/no-op and must not claim token usage or model-request timing. Evidence: [payload catalog](../evidences/2026-10-20-codex-hook-payload-catalog.md).
5. **Work axis:** Codex `Stop` has no `background_tasks`; the reducer must keep `work=unknown` unless a future provider capability says otherwise. Either add a "no background-work feature" capability that lets `Stop` set `clear`, or make `settled` unavailable for Codex. S6's steer is not background work. Evidence: S1/S6, catalog.
6. **Terminal gap:** stream end with an open turn sets presence `lost`/turn `unknown`/`last_turn=none` and emits `terminal_gap`; `SessionEnd` with an open turn is the same class (`session_end_with_open_turn`). The collector heartbeat distinguishes agent death from collector failure. Never infer success from a missing terminal. Evidence: [F1 evidence](../evidences/2026-10-20-f1-kill-fault.md), S0-GAC.
7. **`stop_hook_active` continuation:** a `Stop` with `stop_hook_active=true` must not latch success; keep the turn active. Never observed live at 0.163.0, so this is a defensive rule (covered by the replay self-test).
8. **Generation/resume:** a new collector generation resets generation-scoped turn state; `SessionStart(source="resume")` re-establishes presence and keeps `session_id`; the resumed turn gets a new `turn_id`. Evidence: [S7 evidence](../evidences/2026-10-20-s7-resume.md).
9. **Channel unavailable before trust/startup:** with an untrusted or unanswered trust surface there are no hook events (S2 control), and `SessionStart` is first-turn scoped, so presence is `unknown`, not `ready` or `lost`. Pre-channel TUI labels are TUI-only and cannot be asserted from hooks. Evidence: S2 control/interactive, KQ-1.
10. **Permission payload detail:** `PermissionRequest.tool_input` carries an extra `description` justification not present on `PreToolUse.tool_input`; matchers/hash logic must not assume identical `tool_input` shapes. Evidence: S3.

## Scope

Covers merge/reducer behavior only; raw payload truth is KQ-2. Evidence: `evidences/` links added as produced.
