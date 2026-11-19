# Spec Delta

## MODIFIED Requirements

### Requirement: Managed agents expose a transport-specific detailed state route
The system SHALL expose `GET /houmao/agents/{agent_ref}/state/detail` as the transport-specific inspection route for managed agents.

That route SHALL use the same managed-agent alias resolution contract as the rest of `/houmao/agents/{agent_ref}`.

The response SHALL include:

- the managed-agent identity,
- the current coarse summary state for that managed agent, and
- a detail payload discriminated by the recorded run mode and its actual observation source. For service mode the payload SHALL identify owner and native connection readiness, the bound logical session when available, and current correlated work.

For terminal TUI-backed managed agents, the detail payload SHALL expose a curated projection of key TUI state together with a reference to the canonical terminal-keyed TUI inspection route rather than defining a second incompatible TUI state model.

For headless managed agents, the detail payload SHALL use a headless-specific detail model rather than fabricating TUI parser or prompt-surface fields.

For Web-backed interactive managed agents, the detail payload SHALL expose structured native Web control state and the non-secret browser/session reference. It SHALL NOT fabricate a terminal-keyed canonical route or parser projection.

#### Scenario: Caller inspects TUI detail through the managed-agent namespace
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state/detail` for a managed TUI agent
- **THEN** the server returns a transport-specific detail payload for that TUI agent
- **AND THEN** that payload provides a curated TUI projection plus a reference to the canonical TUI terminal-state route rather than redefining parser semantics under a new incompatible model

#### Scenario: Caller inspects headless detail through the managed-agent namespace
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state/detail` for a managed headless agent
- **THEN** the server returns a transport-specific detail payload for that headless agent
- **AND THEN** the caller does not need to switch to raw turn artifacts merely to understand current runtime posture

#### Scenario: Caller Inspects a DSH Interactive Web Agent
- **WHEN** a caller requests managed detail for an agent launched with DSH's `web` mode
- **THEN** detail identifies a Web native surface and its structured control state
- **AND THEN** terminal-parser fields and canonical terminal-route references are not invented

#### Scenario: Caller inspects service state

- **WHEN** the selected owner reports a connected native service
- **THEN** detail exposes its service readiness and active request evidence without terminal-parser fields

### Requirement: Detailed state preserves TUI canonicality while giving headless parity

The managed-agent detail route SHALL query TUI, Web, headless, and service agents under one namespace with distinct observation models. Terminal-keyed TUI detail SHALL remain canonical for raw terminal inspection; managed detail SHALL be canonical for rich headless, Web, and service inspection. Web state SHALL use native control/observation evidence and report transport-specific unavailability when no safe live source exists.

#### Scenario: TUI detail remains canonical while managed-agent detail stays discoverable
- **WHEN** a caller needs raw TUI-specific observation for a managed TUI agent
- **THEN** the existing terminal-keyed TUI state route remains the canonical detailed source
- **AND THEN** the managed-agent detail route still provides a discoverable transport-aware entry point with a curated projection and canonical-route reference for that same agent

#### Scenario: Headless rich state is available without a fake terminal route
- **WHEN** a caller needs rich state for a managed headless agent
- **THEN** the managed-agent detail route is sufficient to inspect that headless agent
- **AND THEN** the caller is not required to treat the headless agent as though it had a terminal-keyed TUI inspection surface

#### Scenario: Web Transport Fails Independently of Its Supervisor
- **WHEN** the supervisor remains alive but verified Web control is unavailable
- **THEN** detail reports Web control as unavailable without treating the supervisor pane as a replacement observation source

#### Scenario: Provider connection is unverified

- **WHEN** the service owner is live but cannot verify its native connection
- **THEN** managed detail distinguishes owner liveness from provider readiness and reports the source and freshness of its last evidence
