## Why

Managed gateway attach currently defaults runtime-owned tmux-backed sessions to detached background execution, while the same codebase already supports a better operator-facing topology: a dedicated auxiliary tmux window in the managed session with window `0` still reserved for the agent. That default mismatch makes auto-attached gateways harder to inspect, hides the live console by default, and creates an inconsistent experience between pair-managed `houmao_server_rest` sessions and ordinary `houmao-mgr` managed sessions.

## What Changes

- **BREAKING** Change the default managed gateway execution posture for tmux-backed managed sessions from background detached execution to foreground same-session auxiliary-window execution.
- **BREAKING** Change `houmao-mgr agents gateway attach` so foreground becomes the default behavior and `--background` becomes the explicit opt-out for detached execution.
- Change `houmao-mgr project easy instance launch` auto-attached gateways to default to foreground same-session auxiliary-window execution instead of detached execution.
- Add explicit per-command background overrides so operators can still request detached gateway execution when needed.
- Preserve the existing surface contract that tmux window `0` remains the managed agent surface and the gateway window must use a non-zero authoritative window index.
- Ensure attach/status outputs surface the execution mode and authoritative gateway tmux window index when foreground execution is active by default.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: change the default gateway execution posture for tmux-backed managed sessions, keep window `0` reserved for the agent surface, and define explicit background opt-out behavior.
- `houmao-srv-ctrl-native-cli`: change `agents gateway attach` from explicit `--foreground` opt-in to foreground-by-default with `--background` opt-out, and keep status/attach reporting aligned with the foreground default.
- `houmao-mgr-project-easy-cli`: change easy-launch gateway auto-attach to default to foreground auxiliary-window execution and expose an explicit per-launch background override.

## Impact

- Affects gateway attach resolution, launch-time auto-attach defaults, and any pair-managed attach flow that currently lacks an explicit execution-mode selection input.
- Touches managed gateway CLI surfaces, runtime gateway execution-mode selection, gateway status rendering, server/client attach plumbing, docs, and tmux-focused tests.
- Changes the default operator experience for managed gateways and therefore requires clear CLI help, docs, and regression coverage for both foreground and background paths.
