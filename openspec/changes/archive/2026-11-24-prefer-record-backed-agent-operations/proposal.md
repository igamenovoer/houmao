# Proposal

## Why

Houmao resolves an agent from the shared registry, then probes tmux and opens a live controller even for commands that can answer from saved records. In the two-agent mail run, Kimi's fixture shim denied that probe and Houmao called a healthy DSH peer stale despite having the peer's mailbox binding. [GitHub issue #95](https://github.com/igamenovoer/houmao/issues/95)

## What Changes

- Resolve agent identity and execution ownership before acquiring a live controller. Use the shared registry for discovery and verified manifests for authoritative runtime bindings. Use live terminal checks only when the requested operation needs terminal evidence or control.
- Let selected-agent `mail resolve-live`, `gateway status`, and saved headless turn reads use their existing records directly. Report published contact and recorded lifecycle separately from verified live availability. Use the sender's own mailbox binding for mail delivery.
- Resolve live state from the selected backend's evidence. Preserve direct prompts and live inspection with the gateway detached. Route operations that need tmux to the recipient's recorded socket and exact terminal handles.
- Report an inaccessible terminal probe as unavailable. Require confirmed absence or degradation before stale-session recovery or destructive cleanup.
- Qualify cross-agent discovery and mail with peer socket access blocked. Exercise an authorized direct prompt across two isolated sockets with both gateways detached.

## Capabilities

### New Capabilities

### Modified Capabilities

- `houmao-mgr-registry-discovery` defines when selected-agent commands use registry and manifest records and when they acquire live authority.
- `houmao-mgr-agents-scope-cli` and `houmao-srv-ctrl-native-cli` expose the registry tmux alias on the selected-agent gateway scope.
- `agent-gateway` and `agent-gateway-reference-docs` define the alias authority for gateway attachment and document the scoped command.
- `managed-agent-detailed-state` specifies how manager state retains recorded facts and reports current observations for each run mode.
- `houmao-agent-messaging-skill` distinguishes recipient discovery, sender-owned mail, and gateway-optional direct prompting.
- `agent-execution-contexts` constrains terminal operations to the verified owner socket and handles.
- `houmao-mgr-error-diagnostics` covers unavailable terminal inspection, confirmed stale authority, and cleanup eligibility.
- `docs-degraded-stale-recovery` documents the evidence required for recovery.
- `test-agent-launch-fixtures` covers peer communication across isolated tmux servers.

## Impact

- `src/houmao/srv_ctrl/commands/` and the realm controller's manifest, gateway, tmux, and registry helpers.
- Existing `houmao-mgr agents` commands, packaged inspection and messaging guidance, and the CLI and recovery references.
- Unit and integration coverage using synthetic inputs, shared registry and mail authority, and isolated tmux servers.
