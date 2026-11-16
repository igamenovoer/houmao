# Spec Delta

## MODIFIED Requirements

### Requirement: Managed agents expose a transport-specific detailed state route
The system SHALL expose `GET /houmao/agents/{agent_ref}/state/detail` as the transport-specific inspection route for managed agents.

That route SHALL use the same managed-agent alias resolution contract as the rest of `/houmao/agents/{agent_ref}`.

The response SHALL include:

- the managed-agent identity,
- the current coarse summary state for that managed agent, and
- a transport-discriminated detail payload.

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
- **WHEN** a caller requests managed detail for an agent launched with DSH's `tui` posture
- **THEN** detail identifies a Web native surface and its structured control state
- **AND THEN** terminal-parser fields and canonical terminal-route references are not invented


### Requirement: Detailed state preserves TUI canonicality while giving headless parity

The managed-agent detail route SHALL query terminal TUI, Web interactive, and headless agents under one namespace with distinct observation models. Terminal-keyed TUI detail SHALL remain canonical for raw terminal inspection; managed detail SHALL be canonical for rich headless and Web inspection. Web state SHALL use native control/observation evidence and report transport-specific unavailability when no safe live source exists.

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


## ADDED Requirements

### Requirement: Web Detail Exposes Native Execution and Interaction Facts

Web managed detail SHALL expose host/agent incarnation, native session, control availability, current and last turn, pending inbox, interaction waits, and prompt-admission eligibility with freshness diagnostics. Shared identity, mailbox, gateway, and usage references SHALL remain available. Browser-local drafts and unknown native facts SHALL not be fabricated as terminal signals.

#### Scenario: Human Approval Is Pending
- **WHEN** the bound DSH session has a native approval or user-question wait
- **THEN** compact and detailed state expose the blocked native posture and closed ordinary admission
- **AND THEN** the response does not depend on a browser screenshot or terminal capture

#### Scenario: Human Has an Unsubmitted Browser Draft
- **WHEN** the server has no evidence of text still local to a browser editor
- **THEN** observation does not claim that draft is native pending input or expose invented editing-input facts

#### Scenario: Gateway Observation Falls Behind
- **WHEN** a live gateway's Web observation is stale or unreachable
- **THEN** the detail route uses a safely verified direct native observation when available or reports unavailable state
- **AND THEN** stale idle state does not keep prompt admission open
