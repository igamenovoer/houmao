## ADDED Requirements

### Requirement: Attached gateway becomes the authoritative per-agent control plane
When an eligible live gateway is attached to a gateway-capable managed agent session, that gateway SHALL become the authoritative per-agent control plane for live session-local control behavior for that agent.

For an attached agent, gateway-owned control behavior SHALL include at minimum:

- prompt queueing,
- readiness gating before prompt delivery,
- prompt relay to the addressed agent surface,
- interrupt sequencing,
- per-agent live execution posture, and
- per-agent lifecycle control needed to restart, stop, or kill attached work without promoting those responsibilities to the central shared server.

For attached TUI agents, this control-plane ownership SHALL apply to prompt delivery against the live TUI surface.

For attached server-managed headless agents, this control-plane ownership SHALL apply to live prompt admission and interrupt or lifecycle control for that agent even though `houmao-server` remains the durable public HTTP authority and the durable turn-inspection surface.

When no eligible live gateway is attached, this requirement does not prevent the system from using a separate direct fallback path outside the gateway capability.

#### Scenario: Attached TUI agent prompt work is admitted through the gateway
- **WHEN** a managed TUI agent has an eligible attached live gateway
- **AND WHEN** the system accepts a prompt for that agent through the public managed-agent server surface
- **THEN** live prompt queueing, readiness gating, and prompt relay for that prompt are owned by the attached gateway
- **AND THEN** the central server does not need to own a second authoritative per-agent prompt queue for that attached agent

#### Scenario: Attached server-managed headless agent uses gateway-owned live admission
- **WHEN** a server-managed headless agent has an eligible attached live gateway
- **AND WHEN** the system accepts prompt work for that agent through the public managed-agent server surface
- **THEN** live admission, queueing, and interrupt sequencing for that work are owned by the attached gateway
- **AND THEN** the central server remains the public facade and durable projection layer rather than the sole live per-agent admission owner for that attached agent

### Requirement: Gateway control roots publish read-optimized per-agent live control state
For an attached managed agent, the gateway control root SHALL publish read-optimized per-agent live control state sufficient for `houmao-server` and other pair-owned consumers to project current gateway-backed posture without reconstructing it from queue internals or raw tmux probing.

For attached TUI agents, that published live control state SHALL include:

- the current tracked-state snapshot for that agent, and
- bounded recent tracked-state history for that agent.

For attached headless agents, that published live control state SHALL include:

- current execution or admission posture for that agent, and
- current queue-backed request posture for that agent.

Those read-optimized gateway-backed state artifacts or equivalent gateway-owned read surfaces SHALL remain distinct from:

- the durable request queue itself,
- raw runtime session artifacts,
- and shared-registry publication.

#### Scenario: Attached TUI gateway publishes tracked-state snapshot and history
- **WHEN** an eligible live gateway is attached to a managed TUI agent
- **THEN** the gateway control root publishes a read-optimized current tracked-state snapshot and bounded recent tracked-state history for that agent
- **AND THEN** pair-owned consumers do not need to reconstruct authoritative tracked state for that attached agent by replaying raw queue or event internals

#### Scenario: Server projects gateway-backed state without duplicating authority
- **WHEN** `houmao-server` serves managed-agent or terminal-facing state for an attached agent
- **THEN** it may consume the gateway-owned read-optimized live control state for that agent
- **AND THEN** it does not need to create a second conflicting per-agent live-state authority for the same attached agent inside the central server
