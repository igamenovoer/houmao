## Why

CAO-backed launches currently leave a bootstrap shell window in the tmux session before the actual agent window is created. This causes users to attach into an empty shell first, creating confusion and easy accidental teardown (`Ctrl+D`) in interactive workflows.

## What Changes

- Update CAO-backed session startup behavior so the bootstrap tmux window is pruned after CAO creates the real agent terminal window.
- Record the bootstrap tmux `window_id` and use `window_id`-targeted tmux operations (no index assumptions) to safely select/prune windows.
- Best-effort resolve the CAO terminal window id from `create_terminal(...).name` (bounded retry) and select it as the tmux session's current window so first attach lands on the agent window even if pruning fails.
- Preserve current tmux env propagation and canonical `AGENTSYS-...` identity behavior.
- Make bootstrap-window cleanup best-effort: launch succeeds even if pruning fails, while surfacing actionable diagnostics (stderr `warning:` for the CLI path).
- Add coverage for post-launch tmux window hygiene and non-regression checks for CAO launch contracts.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `brain-launch-runtime`: CAO-backed `start-session` should not leave a user-visible bootstrap shell window when an agent terminal window is successfully created (best-effort; warns on cleanup failure).

## Impact

- Affected runtime backend code: `src/gig_agents/agents/brain_launch_runtime/backends/cao_rest.py`.
- Affected tests: CAO backend session startup/unit tests under `tests/unit/agents/brain_launch_runtime/`.
- Affected runtime behavior for manual tmux attach workflows (first attach should land directly on agent window).
