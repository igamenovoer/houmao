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

### Requirement: Headless detailed state treats tmux liveness as auxiliary diagnostics
For managed headless agents, `GET /houmao/agents/{agent_ref}/state/detail` SHALL describe active-turn and last-turn posture from controller-owned execution state and durable turn records.

The headless detail payload MAY expose tmux liveness fields for inspectability or degradation reporting, but those tmux fields SHALL NOT by themselves redefine active-turn status, last-turn result, or the durability of a terminal turn outcome.

For managed headless agents, detail payloads SHALL surface the reconciled controller-owned terminal status even when execution evidence was missing or legacy metadata was insufficient; callers SHALL receive failed-with-diagnostic semantics rather than a tmux-driven `unknown` fallback.

#### Scenario: Detail preserves reconciled last-turn result when tmux session is gone
- **WHEN** a managed headless turn has already reconciled to a terminal failed or interrupted result
- **AND WHEN** the bound tmux session is no longer live
- **THEN** `GET /houmao/agents/{agent_ref}/state/detail` returns that reconciled last-turn result together with its execution evidence
- **AND THEN** tmux liveness appears only as additional diagnostic or inspectability posture

#### Scenario: Detail reports active headless turn from server-owned turn authority
- **WHEN** a managed headless agent currently has an accepted active turn
- **AND WHEN** no terminal execution evidence exists yet for that turn
- **THEN** `GET /houmao/agents/{agent_ref}/state/detail` reports that turn as active from server-owned turn authority
- **AND THEN** the caller does not need tmux watch semantics to determine that the agent is still busy

#### Scenario: Detail preserves failed-with-diagnostic status for degraded evidence
- **WHEN** a managed headless turn has already been reconciled to failed because execution evidence was missing or insufficient
- **AND WHEN** tmux liveness is absent or no longer inspectable
- **THEN** `GET /houmao/agents/{agent_ref}/state/detail` returns the failed terminal status together with available diagnostic context
- **AND THEN** the caller does not need to interpret a separate tmux-derived `unknown` state
