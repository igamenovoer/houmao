# Proposal

## Why

Operators can open an agent's native Web UI through its gateway, but they need a separate terminal to inspect or operate an agent's live tmux session. The gateway can serve that terminal through the browser using its existing listener and authorization policy.

## What Changes

- Add a browser terminal to the running gateway for any active Houmao-managed agent with a verified live tmux session. A TUI shows its interactive terminal. Service, headless, and Web agents with tmux supervision can show their supervisor console.
- Add **View tmux terminal** and **Interact with tmux** to the gateway dashboard. Grant `terminal.view` to anonymous callers on the owner-local gateway and require a current enrolled administrator for `admin.terminal.interact` on the dedicated admin endpoint. Evaluate the provider-native Web action independently.
- Add `houmao-mgr agents single --agent-id <id> gateway terminal-entry` to request a viewer link from the running gateway. An explicit `--interact` requests an administrator link. Gateway attachment remains an explicit lifecycle operation.
- Bundle xterm.js and FitAddon in the Houmao wheel and source distribution. Serve the page, assets, and WebSocket on the gateway's existing owner-local origin and port, with Python providing the PTY bridge to the installed tmux.

## Capabilities

### New Capabilities

- `gateway-tmux-terminal` covers browser viewing and admin interaction with the gateway's verified live tmux session, transport, packaging, and attachment lifetime.

### Modified Capabilities

- `gateway-dashboard` shows tmux availability independently and offers the two terminal entry actions.
- `authenticated-gateway-access` defines proof requirements and continuing authorization for the two terminal access modes.
- `houmao-srv-ctrl-native-cli` exposes a scoped command to request a terminal link from an already-running gateway.
- `managed-agent-run-modes` defines the explicit tmux console handoff for any live tmux-backed mode and preserves the distinction from native Web mode.

## Impact

Gateway routing, dashboard, authorization, and attach-client cleanup gain tmux terminal support. The scoped manager command uses the gateway's current owner-bound endpoint. Python distributions include prebuilt browser assets and their notices. The runtime uses the existing Python web stack, tmux, and a browser. Provider-native Web entry retains `/v1/web/enter` and its provider redirect.
