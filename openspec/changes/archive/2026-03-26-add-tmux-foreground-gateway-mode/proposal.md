## Why

`houmao-mgr` can attach a live gateway to a managed tmux-backed agent, but today local runtime-owned gateways run as detached processes with logs only in gateway-owned files. That makes live debugging and operator inspection clumsy even though the runtime already has same-session tmux-window machinery that can host a gateway in the foreground without touching the agent surface in window `0`.

## What Changes

- Add an explicit foreground attach mode for `houmao-mgr agents gateway attach` that runs the gateway in the managed agent's tmux session rather than as a detached background process.
- Define that foreground gateway mode uses an auxiliary tmux window with index `>=1`, while tmux window `0` remains reserved for the agent surface.
- Surface gateway execution mode and tmux window metadata in gateway status so operators can discover the live foreground gateway surface directly.
- Reuse the existing same-session tmux-window gateway lifecycle model for runtime-owned `houmao-mgr` sessions instead of inventing a separate foreground launcher path.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: extend the gateway execution contract so runtime-owned tmux-backed sessions can explicitly run the gateway in a foreground auxiliary tmux window, persist the authoritative tmux execution handle, and expose execution-mode/window metadata in status.
- `houmao-srv-ctrl-native-cli`: extend `houmao-mgr agents gateway` so operators can request foreground tmux-window attach mode and discover the resulting gateway tmux window from CLI status output.

## Impact

- Affected code: `src/houmao/agents/realm_controller/runtime.py`, `src/houmao/agents/realm_controller/gateway_models.py`, `src/houmao/agents/realm_controller/gateway_service.py`, and `src/houmao/srv_ctrl/commands/agents/gateway.py`
- Operator surface: `houmao-mgr agents gateway attach/status`
- Runtime artifacts: gateway desired-config and live current-instance metadata
- Validation: tmux-backed gateway attach/detach/status tests, plus CLI/help coverage for foreground mode
