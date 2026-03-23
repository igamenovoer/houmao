## Why

`houmao-server` already has a transport-neutral managed-agent read surface and native headless lifecycle control, but the official server contract still stops at coarse headless state and does not treat gateway or mailbox wake-up as first-class managed-agent capabilities. That gap makes the most important asynchronous usage pattern in Houmao harder to inspect, automate, and explain, especially for headless agents that should be queryable without pretending they have a TUI surface.

We need to turn the current partial implementation into an official server-owned contract: users should be able to query headless agent state, submit managed-agent work through a stable API, and inspect or control gateway-driven mailbox wake-up through `houmao-server` rather than through ad hoc manifest or runtime internals. Gateway lifecycle should remain a post-launch concern, because a gateway can be started later against the same tmux-backed agent session by using the published session environment and manifest-backed attach metadata.

## What Changes

- Extend `houmao-server` managed-agent APIs so managed agents expose both coarse shared state and richer transport-specific detail state.
- Add an official detailed headless state model focused on execution posture, last-turn evidence, mailbox bindings, gateway status, and diagnostics rather than parsed TUI surface.
- Add a transport-neutral managed-agent request submission contract under `houmao-server` with one accepted-request envelope, explicit validation and admission semantics, optional headless turn linkage, and no new durable request-status resource in this change.
- Keep the native headless launch contract focused on resolved launch inputs plus optional mailbox overrides, while treating gateway lifecycle as a separate post-launch attach operation.
- Add server-owned managed-agent routes for gateway lifecycle, gateway status, and gateway mail-notifier control, including idempotent attach behavior when a healthy gateway is already attached.
- Extend the gateway execution model so a live gateway can target server-managed agents, including native headless agents, without bypassing server-owned turn authority and persistence.
- Extend runtime gateway attach support so tmux-backed headless sessions can publish and attach live gateways through the same durable gateway subsystem as other gateway-capable sessions.
- Keep async ping-pong mail conversation logic in agents and demo code, but make the server and gateway contracts sufficient for that workflow to become an official supported usage pattern.

## Capabilities

### New Capabilities
- `managed-agent-detailed-state`: Rich transport-specific managed-agent inspection, including an official detailed headless state model and a managed-agent detail route distinct from TUI-only tracked-terminal state.

### Modified Capabilities
- `houmao-server-agent-api`: Expand the managed-agent API with transport-neutral request submission, mailbox-aware headless launch inputs, detailed state inspection, and server-owned gateway control surfaces.
- `agent-gateway`: Expand the gateway contract so live gateways can execute requests against server-managed agents, including native headless agents, while preserving durable queueing and status semantics.
- `agent-gateway-mail-notifier`: Extend notifier control and inspection so server-owned managed-agent surfaces can configure and observe notifier behavior without changing unread-set semantics.
- `brain-launch-runtime`: Extend runtime-owned gateway attach support beyond the current REST-backed subset so tmux-backed headless sessions can attach live gateways through the official runtime gateway path.

## Impact

- Affected APIs:
  - `houmao-server` managed-agent routes under `/houmao/agents/...`
  - gateway HTTP and execution contracts
  - native headless launch request and response models
- Affected code areas:
  - `src/houmao/server/`
  - `src/houmao/agents/realm_controller/runtime.py`
  - `src/houmao/agents/realm_controller/gateway_*`
- Affected systems:
  - server-managed native headless agents
  - gateway-owned mailbox wake-up flows
  - demo packs that should rely on official server APIs rather than runtime-private control seams
- Expected follow-on:
  - a dual-agent async mailbox ping-pong demo under `scripts/demo/` can be implemented on top of this official contract without introducing demo-specific server behavior or requiring gateway startup to be baked into the original agent launch
