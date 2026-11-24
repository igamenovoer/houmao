# managed-agent-detailed-state Specification

## Purpose
TBD - created by archiving change server-managed-agent-gateway-state. Update Purpose after archive.
## Requirements

### Requirement: Managed agents expose a transport-specific detailed state route
The system SHALL expose `GET /houmao/agents/{agent_ref}/state/detail` as the transport-specific inspection route for managed agents.

The maintained passive server SHALL retain canonical raw TUI detail at `/houmao/agents/{agent_ref}/state/detail` for verified terminal agents. Its curated transport-specific managed response SHALL use `/houmao/agents/{agent_ref}/managed-state/detail` and reference that canonical raw route for TUI. Other modes SHALL receive structured detail in both route families.

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

### Requirement: Headless detailed state treats tmux liveness as auxiliary diagnostics
For managed headless agents, `GET /houmao/agents/{agent_ref}/state/detail` SHALL describe active-turn and last-turn posture from controller-owned execution state and durable turn records.

For managed headless agents, terminal last-turn status SHALL reconcile from authoritative active-turn state plus durable per-turn artifact evidence. When a durable terminal artifact such as the exit-status artifact exists for the latest turn and no authoritative active turn remains, that terminal artifact evidence SHALL take precedence over stale tmux or live-posture observations for that same turn.

The headless detail payload MAY expose tmux liveness fields for inspectability or degradation reporting, but those tmux fields SHALL NOT by themselves redefine active-turn status, last-turn result, or the durability of a terminal turn outcome.

For managed headless agents, detail payloads SHALL surface the reconciled controller-owned terminal status even when execution evidence was missing or legacy metadata was insufficient; callers SHALL receive failed-with-diagnostic semantics rather than a tmux-driven `unknown` fallback.

For managed headless agents, `can_accept_prompt_now` SHALL become true whenever no authoritative active turn remains and the latest turn has reconciled terminal evidence, even when the tmux surface has not yet redrawn a visibly idle shell.

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
- **WHEN** the latest managed headless turn has a durable exit-status artifact
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

### Requirement: Managed-agent state reports memo-pages memory
Managed-agent state and detailed-state payloads SHALL report memory root, memo file, and pages directory when available.

Managed-agent state SHALL NOT report `scratch_dir`, `persist_binding`, or `persist_dir` as current managed memory fields.

#### Scenario: State reports memory pages
- **WHEN** managed agent `researcher` has memory root `/repo/.houmao/memory/agents/researcher-id`
- **THEN** managed-agent state reports the memory root
- **AND THEN** it reports the memo file
- **AND THEN** it reports the pages directory

#### Scenario: State omits retired lane fields
- **WHEN** managed agent `researcher` exposes managed memory metadata
- **THEN** managed-agent state does not report `scratch_dir`
- **AND THEN** it does not report `persist_binding`
- **AND THEN** it does not report `persist_dir`

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

### Requirement: Manager state retains recorded facts during observation failure

Manager `state` and detailed inspection SHALL return authorized recorded identity and mailbox summaries separately from live evidence. Recorded lifecycle and lease freshness SHALL describe publication. Readiness and current activity SHALL require qualified observation. If observation is unavailable, the response SHALL keep its known facts and report the unavailable or unknown fields with a reason.

#### Scenario: TUI peer is known but its terminal cannot be inspected

- **WHEN** the manager can resolve the selected TUI peer's saved records but cannot inspect its live terminal
- **THEN** the state response includes the peer's known identity and recorded contact data
- **AND THEN** the live terminal posture is unavailable and prompt readiness is unconfirmed

#### Scenario: A published active record does not establish readiness

- **WHEN** the registry reports an active agent and the manager lacks a current observation for that generation
- **THEN** the response distinguishes recorded lifecycle from observed control availability
- **AND THEN** the response does not infer idle, ready, or stopped state from the missing observation

### Requirement: Manager state uses evidence appropriate to the native mode

Manager state and detailed inspection SHALL use current verified native or gateway observations for Web and service state, and runtime execution records and saved turns for headless state. For current TUI state, the manager SHALL use eligible tracker observations or perform targeted terminal observation when required. Observation SHALL preserve source and freshness.

#### Scenario: Native observation remains available across sockets

- **WHEN** an authorized caller inspects a Web or service agent with a reachable native owner and an inaccessible supervisor socket
- **THEN** the manager reports the verified native state without probing the supervisor's terminal
- **AND THEN** the response identifies the native evidence and its freshness

#### Scenario: Completed headless turn does not depend on tmux

- **WHEN** saved execution records establish the terminal outcome of the selected agent's latest headless turn
- **THEN** the manager reports that outcome even if the supervisor cannot be inspected
- **AND THEN** the response distinguishes turn completion from whether a new turn can be admitted

#### Scenario: Current TUI state requires terminal evidence

- **WHEN** the caller requests current TUI detail and no eligible current tracker observation is available through the gateway
- **THEN** the manager can obtain a fresh observation from the authorized owner's recorded terminal
- **AND THEN** it reports unavailability if that observation cannot be obtained
