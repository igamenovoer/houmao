## Why

The interactive Claude watch workflow under `scripts/explore/claude-code-state-tracking/` creates three tmux-backed resources per run: the Claude session, the dashboard session, and the passive `HMREC-*` recorder session. Today, cleanup is only guaranteed if the operator later runs the explicit `stop` flow. When startup fails after some resources are already live, or the operator interrupts startup mid-flight, the workflow can leave orphaned tmux sessions behind and make it hard to distinguish an intentionally running watch from a leaked partial run.

This needs to be fixed now because the interactive-watch tool is used specifically for debugging state-tracking behavior. Lifecycle leaks undermine that workflow, waste tmux state, and make recorder/session evidence harder to trust during investigation.

## What Changes

- Make interactive-watch startup transactional: if any step after tmux or recorder creation fails, the workflow performs best-effort cleanup of every resource it created for that run before surfacing the error.
- Add interrupt-safe cleanup around startup so operator cancellation during launch does not leave partial `cc-track-watch-*`, `cc-track-dashboard-*`, or `HMREC-*` sessions behind.
- Tighten the stop/finalization contract so the interactive-watch workflow reaps its owned tmux sessions even when the dashboard never reached steady state.
- Clarify the operator lifecycle for interactive watch so successful `start` runs are explicitly understood as long-lived until `stop`, while failed or interrupted startup must not leave lingering sessions.
- Add focused tests covering startup failure, startup interruption, and idempotent cleanup behavior.

## Capabilities

### New Capabilities
<!-- No new capabilities. -->

### Modified Capabilities
- `claude-code-state-tracking-interactive-watch`: Startup and shutdown requirements will change so partially started runs must clean up all workflow-owned tmux and recorder resources before returning failure.

## Impact

- Affected code: [`src/houmao/explore/claude_code_state_tracking/interactive_watch.py`](/data1/huangzhe/code/houmao/src/houmao/explore/claude_code_state_tracking/interactive_watch.py), plus any shared helpers needed for cleanup orchestration.
- Affected tests: [`tests/unit/explore/test_claude_code_state_tracking_interactive_watch.py`](/data1/huangzhe/code/houmao/tests/unit/explore/test_claude_code_state_tracking_interactive_watch.py) and any integration coverage around tmux-backed startup/stop behavior.
- Affected docs/specs: the interactive-watch delta spec and developer-facing usage docs for the manual `start` / `inspect` / `stop` lifecycle.
- No planned breaking API change for the stable CLI surface; the change is behavioral and defensive.
