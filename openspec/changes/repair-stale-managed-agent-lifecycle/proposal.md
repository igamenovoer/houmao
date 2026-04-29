## Why

Local tmux-backed managed agents can get stuck when the shared registry still holds a fresh `active` generation but the recorded tmux authority is stale or degraded. In that state, `houmao-mgr agents stop` and `houmao-mgr agents relaunch` already try recovery paths, but those paths can hit shared-registry ownership conflicts and leave operators without clear Houmao-native next steps.

## What Changes

- Repair stale/degraded active local lifecycle recovery so `agents stop` can reconcile verified broken local authority into stopped or retired registry state without ownership-conflict dead ends.
- Repair `agents relaunch` so verified stale/degraded active local authority can be revived under the same logical managed-agent identity when preserved relaunch metadata remains usable.
- Add stop-failure guidance that reports what Houmao could confirm, what failed, and the exact supported follow-up command for dry-run cleanup, retry, or recovery.
- Keep destructive cleanup/reaping guarded by local authority checks and explicit operator intent; do not kill tmux sessions or purge registry records based only on friendly-name prefixes.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-srv-ctrl-native-cli`: strengthen managed-agent stop/relaunch recovery requirements and require actionable stop-failure guidance for unexpected lifecycle errors.

## Impact

- Affects `houmao-mgr agents stop`, `houmao-mgr agents relaunch`, and related local cleanup guidance for tmux-backed managed agents.
- Affects shared registry publish/takeover semantics for verified broken local active records.
- Adds focused unit/integration coverage around registry ownership conflicts, stale tmux authority, degraded primary tmux surfaces, and stop error messaging.
