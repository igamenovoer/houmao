# managed-agent-detailed-state Specification

## Purpose
TBD - created by archiving change server-managed-agent-gateway-state. Update Purpose after archive.
## Requirements
### Requirement: Managed agents expose a transport-specific detailed state route
The system SHALL expose `GET /houmao/agents/{agent_ref}/state/detail` as the transport-specific inspection route for managed agents.

That route SHALL use the same managed-agent alias resolution contract as the rest of `/houmao/agents/{agent_ref}`.

The response SHALL include:

- the managed-agent identity,
- the current coarse summary state for that managed agent, and
- a transport-discriminated detail payload.

For TUI-backed managed agents, the detail payload SHALL expose a curated projection of key TUI state together with a reference to the canonical terminal-keyed TUI inspection route rather than defining a second incompatible TUI state model.

For headless managed agents, the detail payload SHALL use a headless-specific detail model rather than fabricating TUI parser or prompt-surface fields.

#### Scenario: Caller inspects TUI detail through the managed-agent namespace
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state/detail` for a managed TUI agent
- **THEN** the server returns a transport-specific detail payload for that TUI agent
- **AND THEN** that payload provides a curated TUI projection plus a reference to the canonical TUI terminal-state route rather than redefining parser semantics under a new incompatible model

#### Scenario: Caller inspects headless detail through the managed-agent namespace
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state/detail` for a managed headless agent
- **THEN** the server returns a transport-specific detail payload for that headless agent
- **AND THEN** the caller does not need to switch to raw turn artifacts merely to understand current runtime posture

### Requirement: Headless detailed state is execution-centric and queryable without raw artifact scraping
For managed headless agents, the detailed state model SHALL describe execution posture rather than parsed UI posture.

At minimum, the headless detail payload SHALL expose:

- whether authoritative runtime control is resumable,
- whether the bound tmux session is live,
- whether the agent can accept a new managed prompt now,
- active turn metadata when a turn is in flight,
- last-turn detail including turn identity and terminal result evidence when present,
- redacted mailbox summary when mailbox support is enabled,
- gateway summary when gateway capability exists, and
- structured diagnostics for degraded or unavailable conditions.

The headless detail payload SHALL reuse the same coarse turn and last-turn concepts exposed on summary managed-agent state and extend them with headless-specific timestamps, execution posture, and result evidence when present.

Structured diagnostics in the headless detail payload SHALL reuse the same diagnostics family exposed on summary managed-agent state rather than introducing a second incompatible diagnostic shape.

The headless detail route SHALL NOT require the caller to inspect raw stdout, stderr, or status artifacts merely to determine whether the managed headless agent is idle, active, unavailable, or blocked by explicit diagnostics.

#### Scenario: Active headless turn appears in detailed state
- **WHEN** a managed headless agent currently has one active server-managed turn
- **THEN** `GET /houmao/agents/{agent_ref}/state/detail` reports that active execution posture explicitly
- **AND THEN** the payload reuses the shared turn posture concepts and includes the active turn identity and start metadata without requiring the caller to discover it indirectly from raw artifacts

#### Scenario: Degraded headless runtime reports explicit diagnostics
- **WHEN** a managed headless authority record exists but the runtime cannot be resumed or its tmux session is no longer live
- **THEN** `GET /houmao/agents/{agent_ref}/state/detail` reports that degraded availability explicitly
- **AND THEN** the payload includes structured diagnostics from the same diagnostics family used by summary managed-agent state to describe why the headless agent is not currently operable

### Requirement: Detailed state preserves TUI canonicality while giving headless parity
The managed-agent detail route SHALL make TUI and headless agents equally queryable under one namespace without forcing them into the same internal observation model.

The system SHALL preserve the existing terminal-keyed TUI detail surface as the canonical raw TUI inspection contract.

The system SHALL treat the headless detailed state route as the canonical rich inspection surface for managed headless agents.

#### Scenario: TUI detail remains canonical while managed-agent detail stays discoverable
- **WHEN** a caller needs raw TUI-specific observation for a managed TUI agent
- **THEN** the existing terminal-keyed TUI state route remains the canonical detailed source
- **AND THEN** the managed-agent detail route still provides a discoverable transport-aware entry point with a curated projection and canonical-route reference for that same agent

#### Scenario: Headless rich state is available without a fake terminal route
- **WHEN** a caller needs rich state for a managed headless agent
- **THEN** the managed-agent detail route is sufficient to inspect that headless agent
- **AND THEN** the caller is not required to treat the headless agent as though it had a terminal-keyed TUI inspection surface

