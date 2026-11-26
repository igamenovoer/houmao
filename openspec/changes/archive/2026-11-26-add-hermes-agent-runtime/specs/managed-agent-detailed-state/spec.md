# Spec Delta

## MODIFIED Requirements

### Requirement: Managed agents expose a transport-specific detailed state route
The system SHALL expose `GET /houmao/agents/{agent_ref}/state/detail` as the transport-specific inspection route for managed agents.

For verified parser-backed terminals, the passive server SHALL retain raw detail on that route. Their curated state SHALL use `/houmao/agents/{agent_ref}/managed-state/detail` and reference raw detail. Structured TUI and other modes SHALL receive structured detail in both route families.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

That route SHALL use the same managed-agent alias resolution contract as the rest of `/houmao/agents/{agent_ref}`.

The response SHALL include:

- the managed-agent identity,
- the current coarse summary state for that managed agent, and
- a detail payload discriminated by the recorded run mode and its actual observation source. For service mode the payload SHALL identify owner and native connection readiness, the bound logical session when available, and current correlated work.

For parser-backed TUI agents, the detail payload SHALL expose a curated projection of key TUI state together with a reference to the canonical terminal-keyed TUI inspection route rather than defining a second incompatible TUI state model.

For headless managed agents, the detail payload SHALL use a headless-specific detail model rather than fabricating TUI parser or prompt-surface fields.

For Web-backed interactive managed agents, the detail payload SHALL expose structured native Web control state and the non-secret browser/session reference. It SHALL NOT fabricate a terminal-keyed canonical route or parser projection.

#### Scenario: Caller inspects TUI detail through the managed-agent namespace
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state/detail` for a managed parser-backed TUI agent
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

#### Scenario: Caller Inspects Hermes TUI Detail

- **WHEN** a caller requests either managed detail route for a Hermes TUI agent
- **THEN** detail includes the verified terminal attachment, native readiness and freshness, the bound logical session, and any queued or active native admission
- **AND THEN** the detail omits parser fields and raw terminal tracker links

### Requirement: Detailed state preserves TUI canonicality while giving headless parity

The managed-agent detail route SHALL query TUI, Web, headless, and service agents under one namespace with distinct observation models. Terminal-keyed TUI detail SHALL remain canonical for parser-backed terminal inspection. Managed detail SHALL be canonical for rich structured TUI, headless, Web, and service inspection. Web state SHALL use native control/observation evidence and report transport-specific unavailability when no safe live source exists.

#### Scenario: TUI detail remains canonical while managed-agent detail stays discoverable
- **WHEN** a caller needs raw TUI-specific observation for a managed parser-backed TUI agent
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

### Requirement: Headless detailed state treats tmux liveness as auxiliary diagnostics
For managed headless agents, `GET /houmao/agents/{agent_ref}/state/detail` SHALL describe active-turn and last-turn posture from controller-owned execution state and durable turn records.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

For managed headless agents, terminal last-turn status SHALL reconcile from authoritative active-turn state plus durable per-turn artifact evidence. If no authoritative active turn remains, durable terminal evidence for the latest turn SHALL take precedence over stale tmux or live-posture observations for that turn. A child exit-status artifact SHALL qualify only when the backend establishes turn settlement that way.

The headless detail payload MAY expose tmux liveness fields for inspectability or degradation reporting, but those tmux fields SHALL NOT by themselves redefine active-turn status, last-turn result, or the durability of a terminal turn outcome.

For managed headless agents, detail payloads SHALL surface any established controller-owned terminal status. If missing execution evidence or insufficient legacy metadata has already been reconciled to failure, the payload SHALL report the failed result and diagnostic. An unresolved native outcome SHALL remain explicit.

For managed headless agents, `can_accept_prompt_now` SHALL become true when no authoritative active turn or unresolved native outcome remains, the latest turn has reconciled terminal evidence, and the selected runtime is otherwise ready, even when the tmux surface has not yet redrawn a visibly idle shell.

For managed headless agents, `completion_source` MAY remain present as diagnostic metadata when available, but its absence SHALL NOT prevent a turn from reconciling to `completed` or `failed` once durable terminal evidence exists.

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

#### Scenario: Detail reports terminal headless turn from durable exit artifact despite stale live posture
- **WHEN** the latest managed headless turn has a durable exit-status artifact from a backend whose turn settles on child exit
- **AND WHEN** no authoritative active turn remains for that agent
- **AND WHEN** stale tmux or live-posture data still suggests the prior turn is active
- **THEN** `GET /houmao/agents/{agent_ref}/state/detail` returns the reconciled terminal status for that turn
- **AND THEN** the payload reports that the agent can accept a new managed prompt now
- **AND THEN** the caller does not need to wait for tmux shell redraw or optional `completion_source` metadata to observe terminality

#### Scenario: Detail preserves failed-with-diagnostic status for degraded evidence
- **WHEN** a managed headless turn has already been reconciled to failed because execution evidence was missing or insufficient
- **AND WHEN** tmux liveness is absent or no longer inspectable
- **THEN** `GET /houmao/agents/{agent_ref}/state/detail` returns the failed terminal status together with available diagnostic context
- **AND THEN** the caller does not need to interpret a separate tmux-derived `unknown` state

#### Scenario: Hermes CLI Exit Leaves the Native Turn Unresolved

- **WHEN** a Hermes headless worker exits without proving a native terminal outcome
- **THEN** detailed state reports current native activity or uncertain settlement for that request
- **AND THEN** recorded CLI exit and idle tmux posture do not open another turn slot

### Requirement: Manager state uses evidence appropriate to the native mode

Manager state and detailed inspection SHALL use current verified native or gateway observations for Web and service state, and runtime execution records and saved turns for headless state. For current parser-backed TUI state, the manager SHALL use eligible tracker observations or perform targeted terminal observation when required. Structured TUI control state SHALL use verified native evidence, with terminal attachment reported separately. Observation SHALL preserve source and freshness.

#### Scenario: Native observation remains available across sockets

- **WHEN** an authorized caller inspects a Web or service agent with a reachable native owner and an inaccessible supervisor socket
- **THEN** the manager reports the verified native state without probing the supervisor's terminal
- **AND THEN** the response identifies the native evidence and its freshness

#### Scenario: Completed headless turn does not depend on tmux

- **WHEN** saved execution records establish the terminal outcome of the selected agent's latest headless turn
- **THEN** the manager reports that outcome even if the supervisor cannot be inspected
- **AND THEN** the response distinguishes turn completion from whether a new turn can be admitted

#### Scenario: Current TUI state requires terminal evidence

- **WHEN** the caller requests current parser-backed TUI detail and no eligible current tracker observation is available through the gateway
- **THEN** the manager can obtain a fresh observation from the authorized owner's recorded terminal
- **AND THEN** it reports unavailability if that observation cannot be obtained

### Requirement: Manager state retains recorded facts during observation failure

Manager `state` and detailed inspection SHALL return authorized recorded identity and mailbox summaries separately from live evidence. Recorded lifecycle and lease freshness SHALL describe publication. Readiness and current activity SHALL require qualified observation. If observation is unavailable, the response SHALL keep its known facts and report the unavailable or unknown fields with a reason.

#### Scenario: TUI peer is known but its terminal cannot be inspected

- **WHEN** the manager can resolve the selected parser-backed TUI peer's saved records but cannot inspect its live terminal
- **THEN** the state response includes the peer's known identity and recorded contact data
- **AND THEN** the live terminal posture is unavailable and prompt readiness is unconfirmed

#### Scenario: A published active record does not establish readiness

- **WHEN** the registry reports an active agent and the manager lacks a current observation for that generation
- **THEN** the response distinguishes recorded lifecycle from observed control availability
- **AND THEN** the response does not infer idle, ready, or stopped state from the missing observation

#### Scenario: Hermes Terminal Attachment Changes Independently

- **WHEN** the manager inspects a Hermes TUI agent whose terminal attachment is unavailable or displays another conversation
- **THEN** it reports that attachment state separately from the verified native state of the pinned logical session
