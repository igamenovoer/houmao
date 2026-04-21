## Why

`houmao-mgr agents stop` currently removes the only registry target that `houmao-mgr agents relaunch --agent-name ...` can use, so an ordinary stop/relaunch workflow cannot continue the same provider chat even when the runtime manifest, home, memory, and identity still exist. The shared registry should represent managed-agent lifecycle, not only active tmux liveness, so stopped-but-relaunchable agents remain addressable until the operator explicitly cleans up or retires them.

## What Changes

- Replace the live-only registry record contract with a lifecycle-aware managed-agent registry record that can represent active, stopped, relaunching, and retired states.
- Change local launch publication to create an active lifecycle record rather than a live-only record.
- Change `agents stop` for relaunchable local tmux-backed agents to transition the registry record to `stopped` while preserving identity and runtime relaunch locators.
- Change `agents relaunch --agent-name/--agent-id` to resolve stopped relaunchable records and revive the stopped runtime session while preserving the existing runtime home and provider chat-continuation posture.
- Keep live command behavior explicit: ordinary state/prompt/interrupt/gateway operations must reject stopped records with actionable lifecycle guidance instead of treating them as live.
- Update cleanup behavior so cleanup is the destructive lifecycle action that removes stopped runtime artifacts and marks or purges the registry record.
- **BREAKING**: Registry record schema and helper names move from live-agent-only semantics to managed-agent lifecycle semantics; code that assumes every registry record is live must filter by lifecycle state.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-registry-discovery`: Registry-backed discovery must understand lifecycle state and preserve stopped relaunchable targets.
- `houmao-mgr-agents-launch`: Local launch must publish active lifecycle-aware managed-agent records instead of live-only records.
- `brain-launch-runtime`: Runtime stop and relaunch control must support stopped-session revival for relaunchable tmux-backed managed agents.
- `houmao-mgr-cleanup-cli`: Cleanup must become the explicit destructive path for stopped managed-agent records and runtime artifacts.

## Impact

- Affected code: shared registry models/schemas/storage, local managed-agent target resolution, `agents stop`, `agents relaunch`, runtime session controller stop/relaunch paths, local interactive/headless tmux container revival, cleanup commands, renderers, and tests.
- Affected APIs: registry JSON schema version, structured `agents list/state/stop/relaunch/cleanup` payloads, and CLI behavior for stopped managed-agent selectors.
- Dependencies: no new external dependencies expected.
- Documentation: CLI/reference docs and system skills that describe stop/relaunch/cleanup semantics need updates so agents do not reinterpret stopped relaunch as fresh launch.
