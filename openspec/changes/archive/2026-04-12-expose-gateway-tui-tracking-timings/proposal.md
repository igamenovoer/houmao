## Why

Gateway-owned TUI tracking currently uses fixed timing defaults even though the same tracking windows are already operator-tunable on the `houmao-server` launch path. Operators need the gateway launch and attach surfaces to expose those knobs so gateway-readiness behavior can be adjusted for slow, noisy, or provider-specific TUI sessions without code edits.

## What Changes

- Add gateway TUI tracking timing overrides to the managed gateway attach path, including poll interval, readiness stability, completion stability, unknown-to-stalled timeout, and stale-active recovery.
- Propagate those overrides through pair-owned attach requests, local runtime attach, the gateway service process CLI, and gateway-owned `SingleSessionTrackingRuntime`.
- Persist the chosen gateway TUI tracking timing values in gateway desired configuration so later attach/restart flows reuse the selected behavior unless a stronger override is supplied.
- Expose the same timing overrides on launch-time auto-attach from `houmao-mgr project easy instance launch`.
- Keep gateway reset-context wait constants out of scope; this change only covers continuous TUI state tracking and stale-active recovery timings.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: Gateway attach and restart shall accept, apply, and persist gateway-owned TUI tracking timing configuration.
- `houmao-server-agent-api`: Managed-agent gateway attach requests shall accept the same timing overrides when attaching through pair-owned server routes.
- `houmao-mgr-project-easy-cli`: Easy instance launch shall expose one-shot gateway TUI tracking timing overrides for launch-time auto-attach.

## Impact

- Affected code: `src/houmao/shared_tui_tracking/ownership.py`, `src/houmao/server/tui/tracking.py`, `src/houmao/agents/realm_controller/gateway_service.py`, `src/houmao/agents/realm_controller/runtime.py`, `src/houmao/agents/realm_controller/gateway_models.py`, `src/houmao/agents/realm_controller/gateway_storage.py`, `src/houmao/server/models.py`, `src/houmao/server/service.py`, and `src/houmao/srv_ctrl/commands/**`.
- Affected CLI/API surfaces: `houmao-mgr agents gateway attach`, `houmao-mgr project easy instance launch`, `POST /houmao/agents/{agent_ref}/gateway/attach`, and the internal gateway service CLI.
- Affected persistence: `<session-root>/gateway/desired-config.json` gains optional gateway TUI tracking timing fields.
- Affected tests/docs: unit coverage for CLI option plumbing, gateway desired config persistence, server attach request forwarding, gateway process argument parsing, and reference/system-skill docs that describe gateway launch/attach options.
