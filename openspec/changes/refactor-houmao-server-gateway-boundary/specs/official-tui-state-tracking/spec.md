## MODIFIED Requirements

### Requirement: Live tracked-state reduction SHALL be implemented through the shared TUI tracking core
For supported tmux-backed TUI sessions, the active per-agent control plane SHALL derive tracker-owned `surface`, `turn`, `last_turn`, detector identity, and tracker-state stability semantics through the repo-owned shared TUI tracking core rather than through a package-local reducer or parser-owned reduction path.

The active per-agent control plane SHALL be:

- the attached per-agent gateway, when an eligible live gateway is attached for that managed agent, or
- the direct `houmao-server` fallback tracker, when no eligible live gateway is attached.

That active control plane SHALL remain responsible for live tmux or process observation for tracker authority, session identity, explicit prompt-submission capture, diagnostics, visible-stability metadata over the authoritative tracked response, and in-memory tracker authority for that agent.

`houmao-server` SHALL remain the public HTTP authority for managed-agent and terminal-facing route families, but it SHALL project gateway-owned tracked state for attached agents rather than duplicating tracker authority for those agents inside the central server.

The active control-plane adapter SHALL feed raw captured TUI snapshot text and any explicit prompt-submission evidence into the shared tracker. Parser-derived data MAY still exist as sidecar evidence, but it SHALL NOT replace raw snapshot text as tracker input and SHALL NOT arm tracker authority through parser-derived surface-inference heuristics.

#### Scenario: Attached gateway owns tracker reduction for an attached managed TUI agent
- **WHEN** a managed TUI agent has an eligible attached live gateway and that gateway records one live tracking cycle
- **THEN** the gateway supplies the captured raw TUI snapshot and any explicit prompt-submission evidence to the shared tracking core for that agent
- **AND THEN** `houmao-server` projects that gateway-owned tracked state rather than running a second authoritative tracker for the same attached agent

#### Scenario: Direct server fallback remains the tracker owner when no gateway is attached
- **WHEN** a managed TUI agent has no eligible live gateway attached
- **THEN** the direct `houmao-server` fallback tracker remains the active control plane for tracked-state reduction for that agent
- **AND THEN** the tracked-state contract exposed to callers remains the same even though no gateway is present

#### Scenario: Prompt submission still arms explicit-input tracking through the active control plane
- **WHEN** a caller submits prompt input through a server-owned managed-agent or terminal-facing route for a managed TUI agent
- **THEN** the system forwards that explicit prompt-submission evidence to the active control plane for that agent
- **AND THEN** later tracked state can still report `last_turn.source=explicit_input`

### Requirement: Known tmux-backed sessions are tracked continuously
The system SHALL continuously track every known tmux-backed managed TUI session while its tmux session exists, independent of whether any client is currently querying state and independent of whether a prompt was recently submitted.

For server-managed sessions, `houmao-server` SHALL continue seeding known-session identity from authoritative registration or admission records and SHALL determine whether an eligible attached gateway exists for that agent.

When an eligible attached gateway exists for a managed TUI agent, the system SHALL assign continuous tracking authority for that agent to the gateway. When no eligible gateway exists, the direct `houmao-server` fallback tracker SHALL continue tracking that agent.

Shared live-agent registry records MAY be consulted as compatibility evidence or alias enrichment, but they SHALL NOT by themselves create an authoritative tracked-session entry for this capability.

#### Scenario: Attached gateway becomes the continuous tracking owner
- **WHEN** a managed TUI agent already admitted by `houmao-server` later gains an eligible attached live gateway
- **THEN** the system assigns continuous tracked-state authority for that agent to the gateway
- **AND THEN** the central server no longer needs to remain the authoritative continuous tracker for that attached agent

#### Scenario: Direct fallback continues tracking when no gateway is attached
- **WHEN** a known managed TUI session remains live and no eligible live gateway is attached for that agent
- **THEN** the direct `houmao-server` fallback tracker continues tracking that session in the background
- **AND THEN** callers can still query current tracked state without requiring a gateway sidecar

#### Scenario: Shared registry evidence alone does not admit a tracked session
- **WHEN** a shared live-agent registry record exists without authoritative server registration or admission for a managed TUI session
- **THEN** that registry record alone does not create a primary tracked-session entry for this capability
- **AND THEN** the system does not start continuous tracking solely from that compatibility evidence

### Requirement: Live tracked state is authoritative in memory
The authoritative live tracked state for this capability SHALL live in memory of the active per-agent control plane.

For an attached managed TUI agent, that authoritative in-memory tracked state SHALL live in the attached gateway for that agent.

For a managed TUI agent with no eligible attached gateway, that authoritative in-memory tracked state SHALL live in the direct `houmao-server` fallback tracker.

The system SHALL NOT require per-session watch snapshot files or append-only watch logs as part of the authoritative tracked-state contract for this capability.

`houmao-server` MAY project gateway-owned tracked state through its public routes, but those route responses SHALL read from the active control plane's current in-memory authority rather than reconstructing authoritative tracked state from persisted watch artifacts.

#### Scenario: Server projects gateway-owned in-memory tracked state
- **WHEN** a caller requests tracked managed-agent or terminal state for a TUI agent whose eligible live gateway is attached
- **THEN** `houmao-server` serves that request from the gateway-owned current tracked state for that agent
- **AND THEN** the public response does not depend on a separate server-owned persisted watch snapshot

#### Scenario: No-gateway fallback reads direct server memory
- **WHEN** a caller requests tracked state for a managed TUI agent with no eligible live gateway attached
- **THEN** the direct `houmao-server` fallback tracker returns the latest state held in its own memory
- **AND THEN** that result does not require persisted watch artifacts to become authoritative
