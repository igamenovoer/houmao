# Spec Delta

## MODIFIED Requirements

### Requirement: Live tracked-state reduction SHALL be implemented through the shared TUI tracking core
For supported parser-backed tmux TUI sessions, the active per-agent control plane SHALL derive tracker-owned `surface`, `turn`, `last_turn`, detector identity, and tracker-state stability semantics through the repo-owned shared TUI tracking core rather than through a package-local reducer or parser-owned reduction path.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Any reusable tracking ownership or supervision helpers needed by both the attached gateway and the direct `houmao-server` fallback SHALL live in neutral shared modules layered over the shared tracking core rather than requiring the gateway to import `houmao.server.tui` package-local ownership code.

The active per-agent control plane SHALL be:

- the attached per-agent gateway, when an eligible live gateway is attached for that managed agent, or
- the direct `houmao-server` fallback tracker, when no eligible live gateway is attached.

That active control plane SHALL remain responsible for live tmux or process observation for tracker authority, session identity, explicit prompt-submission capture, diagnostics, visible-stability metadata over the authoritative tracked response, and in-memory tracker authority for that agent.

`houmao-server` SHALL remain the public HTTP authority for managed-agent and terminal-facing route families, but it SHALL project gateway-owned tracked state for attached agents rather than duplicating tracker authority for those agents inside the central server.

The active control-plane adapter SHALL feed raw captured TUI snapshot text and any explicit prompt-submission evidence into the shared tracker. Parser-derived data MAY still exist as sidecar evidence, but it SHALL NOT replace raw snapshot text as tracker input and SHALL NOT arm tracker authority through parser-derived surface-inference heuristics.

When a `cli-hook-observation` channel is active for the session, the active control plane MAY additionally consume normalized provider-hook observation evidence and use it as the primary authority for provider lifecycle facts: turn start, turn end, terminal failure, permission waits, maintenance windows, and background work. Hook observation evidence SHALL NOT replace raw TUI snapshot text as the shared tracker's own input, SHALL NOT alter TUI-owned surface facts (`surface.*`, stability, pending or draft input, and modal rendering), and SHALL be ignored entirely while the channel is degraded, leaving the TUI-only reduction unchanged. Interrupt outcomes remain TUI-owned except where an active Codex or Kimi hook observation channel settles them from a provider interrupt event per the `cli-hook-observation` adapter rules.

#### Scenario: Attached gateway owns tracker reduction for an attached managed TUI agent
- **WHEN** a managed parser-backed TUI agent has an eligible attached live gateway and that gateway records one live tracking cycle
- **THEN** the gateway supplies the captured raw TUI snapshot and any explicit prompt-submission evidence to the shared tracking core for that agent
- **AND THEN** `houmao-server` projects that gateway-owned tracked state rather than running a second authoritative tracker for the same attached agent

#### Scenario: Direct server fallback remains the tracker owner when no gateway is attached
- **WHEN** a managed parser-backed TUI agent has no eligible live gateway attached
- **THEN** the direct `houmao-server` fallback tracker remains the active control plane for tracked-state reduction for that agent
- **AND THEN** the tracked-state contract exposed to callers remains the same even though no gateway is present

#### Scenario: Prompt submission still arms explicit-input tracking through the active control plane
- **WHEN** a caller submits prompt input through a server-owned managed-agent or terminal-facing route for a managed parser-backed TUI agent
- **THEN** the system forwards that explicit prompt-submission evidence to the active control plane for that agent
- **AND THEN** later tracked state can still report `last_turn.source=explicit_input`

#### Scenario: Provider-hook evidence informs lifecycle facts without replacing TUI input
- **WHEN** a managed session has an active hook observation channel and the provider emits a hook terminal event for the current turn
- **THEN** the tracked state settles that turn's terminal outcome from hook evidence while `surface.*` and stability remain TUI-derived
- **AND THEN** the shared tracking core still receives only raw TUI snapshot text and explicit prompt-submission evidence as its own inputs

### Requirement: Known tmux-backed sessions are tracked continuously
The system SHALL continuously track every known parser-backed tmux managed TUI session while its tmux session exists, independent of whether any client is currently querying state and independent of whether a prompt was recently submitted.

For server-managed sessions, `houmao-server` SHALL continue seeding known-session identity from authoritative registration or admission records and SHALL determine whether an eligible attached gateway exists for that agent.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

When an eligible attached gateway exists for a managed parser-backed TUI agent, the system SHALL assign continuous tracking authority for that agent to the gateway. When no eligible gateway exists, the direct `houmao-server` fallback tracker SHALL continue tracking that agent.

When tracking authority changes because a gateway attaches, detaches, or becomes unhealthy, the system SHALL maintain exactly one active authoritative tracking owner for that agent at a time.

In this phase, the system MAY serve last-known tracked state during a brief transition window while the next tracking owner becomes current, but it SHALL NOT require atomic cross-process state transfer for attach or detach handoff.

Shared live-agent registry records MAY be consulted as compatibility evidence or alias enrichment, but they SHALL NOT by themselves create an authoritative tracked-session entry for this capability.

#### Scenario: Attached gateway becomes the continuous tracking owner
- **WHEN** a managed parser-backed TUI agent already admitted by `houmao-server` later gains an eligible attached live gateway
- **THEN** the system assigns continuous tracked-state authority for that agent to the gateway
- **AND THEN** the central server no longer needs to remain the authoritative continuous tracker for that attached agent

#### Scenario: Direct fallback continues tracking when no gateway is attached
- **WHEN** a known managed parser-backed TUI session remains live and no eligible live gateway is attached for that agent
- **THEN** the direct `houmao-server` fallback tracker continues tracking that session in the background
- **AND THEN** callers can still query current tracked state without requiring a gateway sidecar

#### Scenario: Shared registry evidence alone does not admit a tracked session
- **WHEN** a shared live-agent registry record exists without authoritative server registration or admission for a managed parser-backed TUI session
- **THEN** that registry record alone does not create a primary tracked-session entry for this capability
- **AND THEN** the system does not start continuous tracking solely from that compatibility evidence

#### Scenario: Gateway attach uses single-owner handoff semantics
- **WHEN** a managed parser-backed TUI agent transitions from direct fallback tracking to an attached healthy gateway tracker
- **THEN** the system flips authoritative tracking ownership to the gateway without keeping both trackers authoritative at the same time
- **AND THEN** `houmao-server` may serve last-known tracked state briefly while the gateway-owned tracker becomes current

#### Scenario: Gateway detach or gateway health loss returns ownership to direct fallback
- **WHEN** a managed parser-backed TUI agent loses its healthy attached gateway and direct fallback tracking remains supported
- **THEN** the system returns authoritative tracking ownership to the direct `houmao-server` fallback tracker
- **AND THEN** the transition does not require atomic cross-process state transfer to preserve the v1 tracked-state contract

#### Scenario: Structured Hermes Terminal Is Discovered

- **WHEN** a Hermes TUI agent publishes an attachable tmux pane and qualified native control
- **THEN** the system observes its current activity through native control and does not create a terminal-text tracker for that pane
