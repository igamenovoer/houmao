## Why

Managed agents can end up in a half-dead local state where the shared registry still says `active`, the tmux session still exists, but the primary agent surface on window `0` is gone and only an auxiliary gateway window remains. In that shape, ordinary Houmao lifecycle commands get trapped between "too active to clean" and "too broken to stop or relaunch", forcing operators into manual tmux cleanup and separate admin maintenance.

We need one supported recovery contract for degraded active tmux-backed managed agents so ordinary lifecycle commands can retire, rebuild, or clean these sessions without manual tmux surgery or prior registry scrubbing.

## What Changes

- Define a derived local tmux-authority health model for tmux-backed managed agents that distinguishes healthy live authority from degraded or stale local authority without expanding the persisted shared lifecycle-state enum.
- Change tmux-backed runtime resume and relaunch semantics so active lifecycle commands can inspect and recover degraded local authority instead of always failing when the stable primary surface is missing.
- Make `houmao-mgr agents stop` able to retire degraded or stale local active records into supported stopped lifecycle continuity when manifest authority still exists.
- Make `houmao-mgr agents relaunch` recover a degraded active tmux session by rebuilding the stable primary surface instead of requiring the operator to fall back to manual tmux cleanup first.
- Let `houmao-mgr agents cleanup session --purge-registry` proceed when local liveness inspection proves that the selected active record no longer has usable local tmux authority, rather than blocking solely because a stale active record remains.
- Keep the newer stopped-only `--reuse-home` contract unchanged; this change fixes degraded active-session recovery through stop, relaunch, and cleanup rather than by reopening live-owner reused-home takeover.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: add derived local tmux-authority health classification and define runtime stop/relaunch recovery behavior for degraded active tmux-backed managed sessions.
- `houmao-mgr-registry-discovery`: change local stop/relaunch discovery so an `active` registry record with degraded or stale tmux authority remains recoverable through supported lifecycle commands instead of collapsing into a generic unusable-target error.
- `houmao-mgr-cleanup-cli`: change managed-session cleanup liveness rules so local cleanup can distinguish healthy active tmux authority from degraded or stale session remnants, especially when `--purge-registry` is requested.
- `houmao-srv-ctrl-native-cli`: change native `houmao-mgr agents stop` and `houmao-mgr agents relaunch` behavior so degraded active tmux-backed sessions are recoverable through those supported CLI surfaces.

## Impact

- Affected runtime and tmux integration behavior in `src/houmao/agents/realm_controller/backends/tmux_runtime.py`, `src/houmao/agents/realm_controller/backends/headless_base.py`, and `src/houmao/agents/realm_controller/runtime.py`.
- Affected registry-backed target resolution and lifecycle command handling in `src/houmao/srv_ctrl/commands/managed_agents.py` and related registry helpers.
- Affected cleanup planning and purge behavior in `src/houmao/srv_ctrl/commands/runtime_cleanup.py`.
- Affected tests around degraded active tmux sessions, stop/relaunch recovery, and cleanup of stale active records.
- Affected specs for `brain-launch-runtime`, `houmao-mgr-registry-discovery`, `houmao-mgr-cleanup-cli`, and `houmao-srv-ctrl-native-cli`.
