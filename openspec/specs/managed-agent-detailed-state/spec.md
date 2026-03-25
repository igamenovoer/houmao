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

### Requirement: Headless detailed state anchors tmux inspectability to the stable primary surface
For managed headless agents, the detailed state payload SHALL keep any tmux inspectability metadata anchored to the stable primary agent surface.

When such inspectability metadata is exposed, it SHALL anchor that metadata to the stable primary agent surface in window 0 rather than to transient per-turn windows.

When that metadata includes a window name, it SHALL use the stable value `agent` for managed-headless sessions created under this contract.

Auxiliary tmux windows MAY exist in the same session, but the detailed state payload SHALL NOT imply that active-turn identity, last-turn identity, or operator attach guidance depends on those auxiliary windows.

#### Scenario: Detailed state keeps attach guidance on the primary agent surface
- **WHEN** a caller requests detailed state for a managed headless agent that is currently active
- **THEN** any tmux-facing inspectability information in that payload refers to the stable primary agent surface in window 0
- **AND THEN** the caller does not need to discover a transient per-turn tmux window in order to watch the active agent output

#### Scenario: Auxiliary windows do not change detailed-state tmux guidance
- **WHEN** a managed headless session contains both its stable agent window and one or more auxiliary windows
- **THEN** the detailed state payload continues anchoring tmux inspectability to the stable primary agent surface
- **AND THEN** active-turn and last-turn posture remain controller-owned rather than inferred from auxiliary window topology

#### Scenario: Detailed state keeps stable window naming without adding a new attach-target field
- **WHEN** a caller requests detailed state for a managed headless agent created under this contract
- **THEN** any exposed tmux window metadata uses the stable name `agent`
- **AND THEN** the payload does not require a separate new attach-target field in order to describe the stable primary surface

### Requirement: Managed-agent detailed state preserves one public shape while switching live backing source
`GET /houmao/agents/{agent_ref}/state/detail` SHALL preserve one public detail-route envelope and one transport-discriminated detail payload family regardless of whether the addressed managed agent is currently backed by an attached gateway or by the direct fallback path.

When an eligible live gateway is attached for the addressed managed agent, `houmao-server` SHALL prefer the gateway-owned per-agent live state for current detail projection.

When no eligible live gateway is attached, `houmao-server` SHALL continue serving the detail route through its direct fallback detail path for that managed agent.

When the attached gateway is unhealthy or unreachable, `houmao-server` SHALL prefer direct fallback detail projection when that fallback remains supported and safe for the addressed agent. Otherwise it SHALL return unavailable semantics rather than treating stale gateway-backed snapshots as indefinitely authoritative.

This backing-source switch SHALL remain caller-transparent in this phase: the detail route SHALL NOT require callers to choose different route shapes or route keys based on whether the agent currently has an attached gateway.

#### Scenario: Attached TUI agent detail is projected from gateway-owned state
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state/detail` for a managed TUI agent with an eligible attached live gateway
- **THEN** `houmao-server` returns the existing managed-agent detail envelope for that agent
- **AND THEN** the TUI-specific detail payload is projected from the gateway-owned live state for that agent rather than requiring the caller to query the gateway directly

#### Scenario: Attached headless agent detail is projected from gateway-owned live posture
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state/detail` for a managed headless agent with an eligible attached live gateway
- **THEN** `houmao-server` returns the existing managed-agent detail envelope for that agent
- **AND THEN** current live execution posture in that detail response is projected from the gateway-backed per-agent control state while preserving the existing headless detail shape

#### Scenario: No-gateway fallback detail remains available
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state/detail` for a managed agent with no eligible attached live gateway
- **THEN** `houmao-server` continues serving the same managed-agent detail route through its direct fallback state path
- **AND THEN** the caller does not need a gateway sidecar to use the supported detail route

#### Scenario: Unhealthy attached gateway does not make stale detail authoritative
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state/detail` for a managed agent whose gateway is attached but unhealthy or unreachable
- **THEN** `houmao-server` uses direct fallback detail when that fallback is still supported and safe for that agent
- **AND THEN** otherwise it returns unavailable semantics instead of treating stale gateway-backed detail as indefinitely authoritative
