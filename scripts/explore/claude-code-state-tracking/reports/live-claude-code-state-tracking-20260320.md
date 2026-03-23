# Live Claude Code State Tracking Report (2026-03-20)

## Scope

This report covers live tmux-backed runs of the external Claude Code state-tracking harness under `scripts/explore/claude-code-state-tracking/`, using `claude-yunwu` as the launcher.

The goal was to validate the simplified turn-state model against real Claude TUI behavior, independent of `houmao-server`.

Primary final artifacts:

- `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/`
- `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/batch-summary.json`
- `tmp/explore/claude-code-state-tracking/live-settle-reset-verify-20260320d/`

## Problems Found

### 1. Live scenario waiters were still too brittle

The full rerun initially stalled in `interrupt-after-active` because the scenario still waited for the literal footer text `esc to interrupt`, while the live Claude footer was truncated to `esc to…`.

The same family of brittleness also applied to interruption matching, where live Claude can render non-breaking whitespace in the `Interrupted · What should Claude do instead?` line.

Fix applied:

- broaden live active wait patterns to accept `esc to` or spinner-style `...ing…` surfaces
- make the interruption wait regex whitespace-tolerant

Relevant files:

- `scripts/explore/claude-code-state-tracking/scenarios/interrupt-after-active.json`
- `scripts/explore/claude-code-state-tracking/scenarios/slash-noise-during-active.json`

### 2. The detector could falsely settle success while Claude was still visibly interruptable

The live `settle-reset-before-success` run exposed a real detector bug.

At samples `s000050` and `s000051` in:

- `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/settle-reset-before-success/terminal-record-settle-reset-before-success/pane_snapshots.ndjson`

the pane showed:

- a ready prompt
- a visible partial response block
- the footer `esc to…`

That surface is still active. The footer is Claude’s own interrupt affordance, so it is sufficient active evidence.

Before the fix, the detector only recognized the full footer text `esc to interrupt`. Because the truncated footer was missed, replay treated the partial response as a success candidate and emitted an early false `success`.

Fix applied:

- treat truncated interrupt footers such as `esc to…` as `footer_interruptable`
- keep such surfaces in `active`, not `success_candidate`
- add a focused unit test for that exact footer form

Relevant files:

- `src/houmao/explore/claude_code_state_tracking/detectors/claude_code_v2_1_x.py`
- `tests/unit/explore/test_claude_code_state_tracking.py`

Verification:

- `pixi run pytest tests/unit/explore/test_claude_code_state_tracking.py`
- result: `16 passed`
- replaying the exact previously failing capture now produces:
  - `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/settle-reset-before-success/analysis/comparison.json`
  - `mismatch_count = 0`

### 3. Injected network faults still do not produce a stable Claude-visible known-failure surface

The injected-failure scenarios ran successfully as harness executions, but they still did not exercise the intended public `known_failure` path.

Observed final paths:

- `current-known-failure`: `unknown -> ready`, result `none`
- `startup-network-failure-injected`: `unknown -> ready`, result `none`
- `mid-turn-network-failure-injected`: `unknown -> ready -> active`, result `none`

Relevant evidence:

- `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/current-known-failure/analysis/groundtruth_timeline.ndjson`
- `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/startup-network-failure-injected/analysis/groundtruth_timeline.ndjson`
- `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/mid-turn-network-failure-injected/analysis/groundtruth_timeline.ndjson`

Conclusion:

- syscall fault injection is happening
- on this wrapper/version path, those faults still do not deterministically manifest as a stable Claude-visible known-failure frame
- the harness does already implement the fallback known-failure detector from `openspec/changes/simplify-houmao-server-state-model/tui-signals/claude-code-colored-l-shaped-error.md`, so the remaining gap is live error generation, not missing color-based error detection logic

### 4. `stale-known-failure-before-later-success` is still a placeholder, not a real stale-failure test

This scenario timed out waiting for `^● RECOVERED$`:

- `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/stale-known-failure-before-later-success.log`

That is not a reducer bug. The scenario never seeded a real visible failure surface first, so it is not actually testing stale-failure suppression yet.

Current status:

- command exit code: `1`
- no `analysis/comparison.json`

### 5. No dense logging injection was needed

I did not add dense tracing into the harness state-tracking code for this pass.

The failures were concrete and diagnosable from:

- `pane_snapshots.ndjson`
- `drive_events.ndjson`
- `groundtruth_timeline.ndjson`
- `replay_timeline.ndjson`
- `replay_events.ndjson`
- `comparison.json`

That was sufficient to identify both the brittle live waiters and the truncated-footer false-success bug without guessing.

## Final Results

### Live scenarios that passed and exercised the intended path

These runs completed with `command_exit_code = 0` and `mismatch_count = 0`, and they exercised the intended public path.

1. `ambiguous-surface-unknown-and-recovery`
   Evidence: `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/batch-summary.json`
   Final path: `unknown -> ready -> unknown -> ready`

2. `interrupt-after-active`
   Evidence: `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/batch-summary.json`
   Final path: `unknown -> ready -> active -> ready`
   Final result sequence: `none -> interrupted`

3. `ready-noise-without-submit`
   Evidence: `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/batch-summary.json`
   Final path: `unknown -> ready -> unknown -> ready`

4. `simple-success`
   Evidence: `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/batch-summary.json`
   Final path: `unknown -> ready -> active -> ready`
   Final result sequence: `none -> success`

5. `slash-noise-during-active`
   Evidence: `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/batch-summary.json`
   Final path: `unknown -> ready -> active`
   Meaning: slash-menu noise did not knock the turn out of `active`

6. `process-killed-tmux-still-alive`
   Evidence: `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/batch-summary.json`
   Diagnostics sequence: `available -> tui_down -> available -> tui_down -> ...`
   Meaning: the process-loss diagnostics path was observed and replay matched it

7. `target-disappeared-unavailable`
   Evidence: `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/batch-summary.json`
   Diagnostics sequence: `available -> unavailable`

### Cases that matched replay-vs-groundtruth but did not cover the intended semantic path

These runs had zero replay mismatch, but the live Claude surface never exercised the scenario’s intended public outcome.

1. `current-known-failure`
   Evidence: `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/batch-summary.json`
   Observed path: `unknown -> ready`
   Reason: no visible known-failure frame appeared

2. `startup-network-failure-injected`
   Evidence: `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/batch-summary.json`
   Observed path: `unknown -> ready`
   Reason: injected startup faults still stabilized to a normal ready surface

3. `mid-turn-network-failure-injected`
   Evidence: `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/batch-summary.json`
   Observed path: `unknown -> ready -> active`
   Reason: active processing was observed, but no visible failure or recovery frame appeared during the capture

### Settle-reset status after the footer fix

This case is now technically correct, but the evidence is split across two artifacts:

1. The original full-success capture:
   - `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/settle-reset-before-success/terminal-record-settle-reset-before-success/`
   - after replaying that exact capture with the detector fix, `analysis/comparison.json` now reports `mismatch_count = 0`

2. The focused post-fix live rerun:
   - `tmp/explore/claude-code-state-tracking/live-settle-reset-verify-20260320d/`
   - this rerun stayed on `unknown -> ready -> active` with result `none`

Interpretation:

- the false-success bug is fixed
- the exact earlier failing capture now replays correctly
- the new rerun did not progress far enough to re-exercise a final settled success within the scenario window

### Cases that are still not valid tests

1. `stale-known-failure-before-later-success`
   Evidence: `tmp/explore/claude-code-state-tracking/live-all-cases-20260320/stale-known-failure-before-later-success.log`
   Status: timed out
   Reason: this is still a placeholder scenario and does not inject or preserve a real stale failure surface

## Final Assessment

The live testing is successful for the important ready/active/success/interrupted/noise/process-loss paths:

- ready / unknown recovery
- active-turn detection
- interruption detection
- simple success detection
- slash-menu noise during active work
- process-loss diagnostics (`tui_down`, `unavailable`)

The live testing is not complete for the known-failure family:

- no reliable live Claude-visible `known_failure` generator yet
- no valid stale-known-failure scenario yet

That does not mean the harness lacks a known-failure detector. The current Claude detector already uses the color-based L-shaped error rule from:

- `openspec/changes/simplify-houmao-server-state-model/tui-signals/claude-code-colored-l-shaped-error.md`

The missing part is a repeatable live run that actually produces that surface.

The most important real state-tracking bug found during this pass was the truncated-footer false-success bug in the detector. That bug is fixed, unit-tested, and verified by replaying the exact previously failing settle-reset capture to zero mismatches.

So the final judgment is:

- the live harness and state transition model now pass the core public paths
- the remaining gaps are failure-surface generation gaps, not unexplained reducer mismatches

## Recommended Next Step

Do not expand `known_failure` logic first. Build a deterministic visible-failure generator first, then formalize the resulting Claude signal.

Promising next paths:

- more aggressive `strace --inject` combinations on `recvmsg`, `read`, and `connect`
- a proxy-owned disruption path that can sever or corrupt Claude’s live network stream after startup
- a scenario that deliberately seeds a real visible failure, keeps it in scrollback, then drives a later success to exercise stale-failure suppression for real
