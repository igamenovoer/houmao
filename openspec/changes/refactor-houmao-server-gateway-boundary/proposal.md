## Why

`houmao-server` and the per-agent gateway already coexist, but their ownership boundary is still blurred. The server still owns too much per-agent execution and live-state behavior, while the gateway is already the natural place for queueing, TUI tracking, and other session-local control work. That makes the distributed agent model harder to reason about and keeps the gateway optional in implementation detail rather than optional in architecture.

We need to make the split explicit now so the system supports both modes cleanly: `houmao-server + tmux sessions` continues to work on its own, and adding an agent gateway upgrades one agent with queueing, tracking, and richer lifecycle behavior without moving shared coordination into the sidecar.

## What Changes

- Recast `houmao-server` as the shared coordination plane for managed-agent naming, alias resolution, shared-registry ownership, mailbox-root ownership, and capability-aware request routing.
- Recast the optional per-agent gateway as the per-agent control plane for TUI state tracking, prompt queueing, prompt relay, readiness gating, interrupt sequencing, and per-agent lifecycle actions such as restart or kill.
- Move server-managed headless execution authority behind the per-agent gateway when a gateway is attached, while keeping a direct no-gateway fallback path so `houmao-server` plus tmux-hosted agents still works without a sidecar.
- Keep the managed-agent HTTP route shapes and response contracts as stable as possible in this phase, but allow their backing source to switch between gateway-backed and direct fallback implementations.
- Make `houmao-server` the shared-registry writer for agents it creates or admits through server-owned launch authority, while keeping the registry pointer-oriented rather than turning it into per-agent runtime state.
- Update runtime and attach contracts so gateway capability is published independently from live gateway attachment and server-managed agents can advertise optional gateway support without making gateway startup mandatory.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `agent-gateway`: redefine the gateway as the optional per-agent control plane for tracking, queueing, relay, and per-agent lifecycle authority.
- `houmao-server-agent-api`: keep the public managed-agent routes stable while shifting them to capability-aware gateway-backed or direct fallback execution paths.
- `managed-agent-detailed-state`: preserve the existing detail-route shape while allowing detailed state to come from gateway-owned per-agent state when a gateway is attached.
- `official-tui-state-tracking`: move continuous per-agent TUI tracking authority out of the central server and into the per-agent gateway when present, with direct fallback when no gateway is attached.
- `agent-discovery-registry`: clarify that `houmao-server` writes shared-registry records for agents created through server-owned authority while the registry remains a secret-free pointer layer.
- `brain-launch-runtime`: update runtime publication rules so stable gateway capability and attach metadata remain available for optional post-launch gateway attachment in both server-managed and direct-runtime topologies.

## Impact

- Affected code:
  - `src/houmao/server/`
  - `src/houmao/agents/realm_controller/gateway_*`
  - `src/houmao/agents/realm_controller/runtime.py`
  - `src/houmao/agents/realm_controller/registry_*`
  - `src/houmao/server/tui/`
- Affected APIs:
  - `/houmao/agents/*`
  - managed-agent gateway routes
  - gateway status and request contracts
- Affected systems:
  - server-managed TUI agents
  - server-managed headless agents
  - shared-registry publication for server-created agents
  - optional gateway-attached mailbox and notifier workflows
