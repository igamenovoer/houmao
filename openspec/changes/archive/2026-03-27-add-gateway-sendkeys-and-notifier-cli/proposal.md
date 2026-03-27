## Why

Operators can already attach a live gateway and use gateway-mediated prompt and interrupt flows through `houmao-mgr`, but raw control input and gateway mail-notifier control still require direct HTTP access or ad hoc tooling. That leaves the native CLI incomplete for the most operator-facing live-gateway controls, especially when the operator is already inside the owning tmux session and Houmao has enough manifest-backed discovery metadata to infer the target.

## What Changes

- Add `houmao-mgr agents gateway send-keys` as the native raw control-input command for a managed agent's live gateway.
- Add `houmao-mgr agents gateway mail-notifier status`, `enable`, and `disable` as native mail-notifier control commands.
- Extend gateway command targeting so these commands can be called either with explicit managed-agent selectors or from inside the owning tmux session through manifest-first current-session discovery.
- Add a pair-managed server route for gateway raw control input so `houmao-mgr` can reach the live gateway through `houmao-server` without direct listener discovery.
- Add passive-server proxy support for gateway raw control input and gateway mail-notifier routes so pair behavior stays consistent across supported pair authorities.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-srv-ctrl-native-cli`: expand `houmao-mgr agents gateway` with native send-keys and mail-notifier commands, and define current-session target inference for supported gateway commands.
- `houmao-server-agent-api`: add managed-agent gateway raw control-input routes alongside the existing lifecycle, request, and mail-notifier routes.
- `passive-server-gateway-proxy`: proxy gateway raw control input and mail-notifier routes through `houmao-passive-server` with the same agent resolution and error behavior as the existing gateway proxy surface.

## Impact

- CLI code under `src/houmao/srv_ctrl/commands/agents/`
- Managed-agent resolution and current-session discovery helpers used by gateway commands
- `houmao-server` managed-agent gateway API and client bindings
- `houmao-passive-server` proxy API and client bindings
- Gateway command and proxy contract tests, plus native CLI docs
