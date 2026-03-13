## Context

This repo already has strong building blocks for live agent sessions: tmux-backed agent identities, persisted session manifests, runtime-managed environment publication, and backend-specific control adapters. A separate mailbox protocol is being explored elsewhere in the repo, but that system is not mature enough to become a dependency of this change. What the repo still lacks is a per-agent control plane that can sit close to one live session, expose a stable HTTP endpoint, arbitrate competing requests, normalize backend status, schedule follow-up work, and record recovery decisions.

The design should treat the gateway like the stable frontend or session facade for one managed agent session, while the agent process or terminal surface behind it behaves like a replaceable upstream backend instance. That framing matters most when the managed agent fails unexpectedly: the gateway should keep its own control plane alive, report the upstream outage clearly, preserve safe durable state, and only resume automation when continuity is known again.

The key architectural change in this revision is to decouple gateway lifecycle from agent lifecycle. The gateway remains optional. A session may run with no gateway, may start with a gateway already attached, or may gain a gateway later after the managed TUI is already running. That change preserves rollout flexibility and unlocks a more powerful long-term story: runtime-owned sessions can gain gateway support after launch, and manually launched tmux-backed sessions can become gateway-attachable later if they publish the same attach contract.

The operator-facing UX constraint also shifts slightly in order to support that lifecycle. The system still must not create a second visible operator surface, but the gateway no longer needs to live in the same tmux window as the TUI. Instead, the gateway becomes an out-of-band companion process that discovers and controls the live session through tmux env pointers, backend metadata, and durable per-agent state. That makes "attach later" and "stop or restart independently" tractable without trying to inject a background shell into an already-running interactive TUI surface.

This revision keeps the gateway explicitly independent from the mailbox system. Mailbox-triggered enqueueing, mailbox-aware scheduling rules, mailbox-specific env bindings, and mailbox-specific request kinds are still deferred until the mailbox contract is mature enough to integrate cleanly.

```mermaid
flowchart LR
  A[Operator or tool] --> B[Resolve tmux session]
  B --> C[Read attach metadata]
  C --> D[Gateway attach/start]
  D --> E[Gateway HTTP API]
  E --> F[Backend adapter]
  F --> G[Managed agent TUI]
  G --> H[Human direct interaction]
  D --> I[Gateway root]
  I --> J[Queue]
  I --> K[State]
  I --> L[Events]
```

## Goals / Non-Goals

**Goals:**

- Keep the gateway optional and additive so non-gateway sessions remain valid and usable.
- Allow the gateway to start either together with the agent or later by attaching to a running tmux-backed session.
- Preserve the operator UX requirement that gateway support introduces no second visible tmux pane or window.
- Reuse existing tmux session env publication patterns for discovery and extend them into a stable gateway-attach contract.
- Separate "gateway-capable session" from "gateway-running session" so the gateway can be started, stopped, and restarted independently.
- Support runtime-owned attach first while designing the attach contract so manually launched sessions can participate later.
- Keep a durable per-agent queue and state root so gateway restart does not lose accepted work and later attach flows have somewhere to persist state.
- Keep the gateway itself readable and inspectable while the managed agent is recovering, unavailable, or rebound to a replacement instance.
- Keep the HTTP contract backend-extensible and independent from the mailbox protocol.

**Non-Goals:**

- Hard security isolation against a human with direct tmux access on the same host.
- Requiring the gateway to be co-started with every agent session.
- Requiring the gateway to share the same shell process or tmux window as the foreground TUI.
- Recovering a full tmux-session or tmux-server loss from inside the gateway process itself.
- Automatically attaching a gateway to arbitrary tmux sessions that expose no attach metadata at all.
- Integrating the gateway directly with the mailbox system in v1.
- Solving authentication, authorization, or network perimeter hardening for explicitly enabled all-interface HTTP exposure in v1.

## Decisions

### 1) The gateway is an optional independently managed companion process, not a launch prerequisite

The gateway is an independently managed per-agent companion process. It may be absent, may be attached immediately after session startup, or may be attached later to an already-running session. The gateway must not create a visible tmux pane or window of its own, but it does not need to share the same shell lifecycle as the managed TUI.

There are two primary activation paths:

- launch-attached: the runtime starts the agent session, then immediately resolves attach metadata and starts the gateway companion for that live session
- attach-later: a lifecycle command resolves an already-running tmux session, reads its attach metadata, and starts the gateway companion without restarting the agent

Conceptually:

```text
launch-attached
  start agent session
  -> publish attach metadata
  -> start gateway daemon
  -> publish live gateway bindings

attach-later
  resolve live tmux session
  -> read attach metadata
  -> start gateway daemon
  -> publish live gateway bindings
```

This design is intentionally different from the earlier same-window wrapper model. A co-start wrapper remains an optional implementation strategy for some backends later, but it is no longer the defining lifecycle contract. The gateway must not depend on being injected before the TUI `exec`s, because that would make post-launch attach and independent stop or restart awkward or impossible.

Rationale: independent lifecycle is the cleanest way to keep the gateway optional while still making it usable later for already-running agents and future manual sessions.

Alternatives considered:

- Mandatory same-window sidecar wrapper. Rejected because it over-couples gateway availability to backend launch and blocks later attach flows.
- Separate visible tmux pane or window. Rejected because it violates the operator UX constraint.
- In-process gateway inside the agent TUI process. Rejected because it ties lifecycle and recovery to tool-specific internals.

### 2) Attach discovery is tmux-env-driven and unified by a secret-free attach contract

The gateway attaches to a running session by resolving tmux session identity and reading secret-free discovery metadata from that session's tmux environment.

Existing runtime-owned env pointers remain foundational:

- `AGENTSYS_MANIFEST_PATH`
- `AGENTSYS_AGENT_DEF_DIR`

For runtime-owned sessions, those existing pointers already provide enough information to discover the persisted session manifest and the agent definition root. This revision proposes standardizing that into one uniform attach contract file plus an explicit gateway-root pointer:

- `AGENTSYS_GATEWAY_ATTACH_PATH`
- `AGENTSYS_GATEWAY_ROOT`

For runtime-owned sessions in v1, the canonical storage unit is the session directory itself:

```text
<runtime_root>/sessions/<backend>/<session_id>/
  manifest.json
  gateway/
    attach.json
    ...
```

Within that layout, `AGENTSYS_GATEWAY_ROOT` points to `<session-root>/gateway`, and `AGENTSYS_GATEWAY_ATTACH_PATH` points to `<session-root>/gateway/attach.json`.

That file should be a secret-free strict JSON payload describing how a gateway can attach to the addressed session. Runtime-owned sessions can materialize it from their manifest and launch metadata. Manual launchers can create and publish the same file directly even when no gig-agents session manifest exists.

In v1, that contract should use one versioned schema with:

- required shared core:
  `schema_version`, `attach_identity`, `backend`, `tmux_session_name`, `working_directory`, and backend metadata needed for observation or control
- optional runtime-owned fields:
  `manifest_path`, `agent_def_dir`, `runtime_session_id`, `desired_host`, and `desired_port` when those values exist

The same contract should be validated strictly rather than treated as an ad hoc bag of optional fields. Runtime-owned sessions are the only implemented publishers in v1, but the schema shape should already leave room for manual sessions to omit runtime-only pointers without inventing a second contract later.

The important distinction is that attach metadata describes how to attach a gateway to a live session, not whether a gateway is currently running.

Rationale: this keeps discovery grounded in existing tmux env patterns while giving runtime-owned and manual sessions one future-proof attachability contract.

Alternatives considered:

- Derive everything only from `AGENTSYS_MANIFEST_PATH`. Rejected because manually launched sessions may have no runtime manifest at all.
- Encode all attach metadata directly in tmux env vars. Rejected because the contract will grow and is easier to evolve as a versioned file path.
- Require every attach-later flow to be fully hand-configured from CLI flags. Rejected because it is too error-prone for routine operator use.

### 3) Stable attachability metadata and live gateway bindings are separate concepts

This revision separates stable "this session can have a gateway" metadata from ephemeral "a gateway is running right now" metadata.

A per-agent gateway root remains useful, but for runtime-owned sessions it should live under the agent session's own runtime directory. That makes the agent session the primary instance root and the gateway a nested optional control surface attached to that session rather than a peer top-level storage tree. A representative runtime-owned layout is:

```text
<runtime_root>/sessions/<backend>/<session_id>/
  manifest.json
  gateway/
    protocol-version.txt
    attach.json
    desired-config.json
    state.json
    queue.sqlite
    events.jsonl
    logs/
      gateway.log
    run/
      current-instance.json
      gateway.pid
```

For runtime-owned sessions in v1, `<session_id>` is the runtime-generated session id already used to key the session manifest, and the gateway root is the fixed `gateway/` subdirectory under that same session root. Future manual sessions can still publish a different gateway root through their attach contract once manual-session support is defined.

This layout is intentionally instance-centric:

- `<session-root>/`
  is the canonical runtime-owned agent instance directory
- `<session-root>/manifest.json`
  is the runtime-owned session record and remains the backend-facing source of truth for resume, backend reconstruction, and agent identity recovery
- `<session-root>/gateway/`
  is the optional attached control-surface directory for that same agent instance

In other words, the agent session is the "backend" and the gateway is the optional "frontend" or control companion attached to it. The storage layout should reflect that ownership:

- the session root exists because the agent exists
- the nested `gateway/` directory exists only because that same agent instance is gateway-capable
- removing or restarting the gateway does not change the identity of the parent session directory

The files inside `gateway/` are separated by responsibility:

- `attach.json`
  stable discovery and attach contract for later gateway lifecycle actions
- `protocol-version.txt`
  version marker for the gateway-local file and HTTP contract
- `desired-config.json`
  persisted desired listener and lifecycle configuration for later restart or re-attach
- `state.json`
  read-optimized current status snapshot aligned with `GET /v1/status`
- `queue.sqlite`
  durable internal request queue storage
- `events.jsonl`
  append-only gateway event history
- `logs/`
  gateway-process log output, kept out of the operator-facing TUI
- `run/`
  ephemeral current-instance runtime state such as pid or live-instance metadata

This is also why `state.json` stays under `gateway/` rather than next to `manifest.json`: both belong to the same agent instance, but they have different owners. `manifest.json` is the runtime's session record; `gateway/state.json` is the gateway control plane's current status contract.

The main split is:

- stable attachability pointers, `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`
- live gateway bindings, such as `AGENTSYS_AGENT_GATEWAY_HOST`, `AGENTSYS_AGENT_GATEWAY_PORT`, `AGENTSYS_GATEWAY_STATE_PATH`, and `AGENTSYS_GATEWAY_PROTOCOL_VERSION`

Stable attachability metadata may exist even when no gateway process is running. Live bindings only describe the currently active gateway instance and may disappear or change across restart.

Because the gateway can be stopped and started independently, listener host and port are no longer part of immutable session identity. They become current-instance metadata. Desired defaults may persist, but the active listener is valid only while the corresponding gateway instance is alive.

When no explicit gateway port is configured, the runtime should let the gateway server request a system-assigned port during bind rather than pre-probing a free port in the parent runtime process. The parent runtime can then observe the actual bound listener from gateway-owned run state after startup succeeds.

Capability publication for runtime-owned sessions creates or materializes the session-owned `gateway/` directory, writes `protocol-version.txt` plus `attach.json`, and seeds `state.json` with a protocol-versioned offline or not-attached snapshot even before the first live gateway attach. Graceful detach rewrites `state.json` back to that offline or not-attached condition while clearing live bindings.

If a gateway instance starts successfully with a system-assigned port, that resolved host and port become the desired listener persisted in `desired-config.json` for later restarts until a caller explicitly overrides them.

On graceful shutdown, the gateway lifecycle should clear live gateway bindings from the tmux session while preserving stable attachability metadata. On crash, stale live bindings are possible, so clients must treat tmux env as hints, validate live bindings structurally, and then use `GET /health` as the authoritative liveness check rather than trusting tmux env or run-state files alone. Local run-state files remain useful for diagnostics after health failure, but they are supporting evidence rather than the primary liveness contract.

Rationale: independent lifecycle only works cleanly if discovery of attachability is more stable than discovery of the currently running gateway process.

Alternatives considered:

- Treat host and port as permanent session identity. Rejected because independent stop or restart makes them instance-level facts, not timeless identity.
- Publish only live host and port bindings. Rejected because attach-later becomes impossible when the gateway is not already running.
- Store runtime-owned gateways in a separate top-level `<runtime_root>/gateways/<id>/...` tree. Rejected because it treats the gateway as the primary storage anchor rather than an attached companion to the agent session, and it scatters one session's runtime state across multiple top-level roots.

### 4) The HTTP API remains package-owned, but gateway lifecycle control is a separate concern

The gateway still exposes a local HTTP API for health inspection, status inspection, and gateway-managed request submission. The current v1 API shape remains directionally good:

- `GET /health`
- `GET /v1/status`
- `POST /v1/requests`

The important refinement is that gateway lifecycle is not part of that per-agent request API. Starting, attaching, detaching, or stopping a gateway is a lifecycle-control action that happens before a caller can use the HTTP surface.

`GET /health` should answer the gateway-local question, "is the gateway control plane alive enough to serve its contract?" It should not collapse managed-agent availability into gateway death. If the gateway process, local state, and HTTP listener are healthy but the managed agent is down, recovering, or awaiting rebind, `/health` should still answer successfully while `/v1/status` and `state.json` carry the upstream failure state.

That means gateway-aware callers now have two phases:

1. ensure a gateway is attached and healthy for the target session
2. use the HTTP API for status or queued work submission

The queue remains durable and gateway-owned. External callers still do not mutate SQLite directly.

Rationale: separating lifecycle control from request submission keeps the HTTP contract small and lets gateway activation evolve independently from per-request semantics.

### 5) Initial gateway state is snapshot-based, and `offline` includes "not currently attached"

Because the gateway may attach after the agent has already been running, the gateway cannot assume it observed the entire session from launch. When attaching to an already-running session, it initializes from:

- the current live observation of the backend or tmux surface
- any previously persisted session-owned gateway state when one exists
- the attach contract

It does not attempt to reconstruct every pre-attach operator action or backend transition that occurred before the gateway existed.

The status model remains useful, but `gateway_state=offline` now has a broader meaning: the gateway may simply not be attached right now, not necessarily that it crashed unexpectedly. `state.json` remains a stable local read contract, but it may describe last-known status plus current gateway absence rather than continuous full-session observation from the original agent launch.

Rationale: later attach is only viable if the gateway is allowed to seed itself from current state instead of pretending it has launch-time omniscience.

### 6) The gateway is the stable session facade; the managed agent is a replaceable upstream instance

When a gateway is attached, the gateway becomes the stable control-plane identity for that logical session. The managed agent process or terminal surface behind it is the current upstream instance for that session, and that upstream instance may fail, reconnect, or be replaced while the session root and nested gateway root remain unchanged.

That means the design should distinguish:

- stable session identity
- current managed-agent instance epoch or generation
- gateway health state
- managed-agent connectivity state
- recovery state
- request-admission state
- terminal-surface eligibility state
- active execution state

Conceptually, the gateway should behave more like a frontend staying up while the backend recovers than like a wrapper that becomes meaningless as soon as the first backend process dies.

```mermaid
stateDiagram-v2
  [*] --> Connected
  Connected --> Recovering: agent crash detected
  Recovering --> Connected: same upstream instance restored
  Recovering --> ReconciliationRequired: replacement upstream instance bound
  Recovering --> AwaitingRebind: retry budget exhausted or tmux lost
  ReconciliationRequired --> Connected: continuity re-established
  AwaitingRebind --> Connected: runtime rebinds session
```

This framing changes how request handling should work during failure. If the managed agent dies unexpectedly while the gateway remains alive:

- the gateway should stay readable through `/health`, `/v1/status`, and `state.json`
- already accepted but not yet started work should remain durable but paused while recovery is in progress
- an active terminal-mutating request should become an explicit failed or outcome-unknown record rather than being silently replayed
- new terminal-mutating requests should be admitted only when the request-admission state says continuity is safe enough to do so

The most important safety rule is that the gateway must not blindly replay prompts across a replacement upstream instance when conversational continuity is uncertain. If bounded recovery reconnects to the same live upstream instance, automation can reopen normally. If recovery rebinds the logical session to a replacement upstream instance, the gateway should surface a reconciliation-required state until the runtime or operator confirms that continued automation is safe.

Rationale: the gateway only behaves gracefully through unexpected agent failure if it has its own stable identity and can model upstream replacement explicitly instead of collapsing everything into one generic offline state.

### 7) The scheduler still owns single-writer automation, but only while a gateway is attached

The queueing and single-writer scheduling model still holds. When a gateway is attached, terminal-mutating work flows through one durable execution slot and human interaction remains a first-class scheduling signal.

The key difference is that this control plane is active only while a gateway is attached. Direct runtime or operator interaction remains possible when no gateway is running. That means the design should distinguish:

- gateway-capable session: attach metadata exists and a gateway could be attached
- gateway-running session: a live gateway instance is attached and currently owns the automation queue

In v1, public terminal-mutating request kinds can still remain narrow, such as `submit_prompt` and `interrupt`, while timer-driven or wakeup-oriented work remains internal scheduler behavior.

Rationale: keeping the single-writer automation semantics limited to active gateway periods avoids pretending the system always has a control plane when it explicitly does not.

### 8) Gateway restart and later attach both recover from stable roots, but they mean different things

Gateway restart and later attach are related but not identical:

- restart: the same logical session-owned gateway root already existed, accepted queued work may already exist, and the new process must recover it
- first attach to an ungatewayed running session: for runtime-owned sessions in v1 the session root and nested gateway directory already exist from capability publication, while future manual sessions may still materialize that root lazily; in either case, no prior queue may exist and the initial status is seeded from a current observation snapshot

This distinction should be explicit in the design because it changes what "recovery" means. Restart is recovery of prior gateway-owned state. First attach is establishment of gateway-owned state for a session that previously had none.

Independent stop or restart should not require stopping the agent itself. Conversely, runtime-owned agent-session teardown should stop any live attached gateway as part of the same authoritative cleanup path, rewrite `state.json` back to offline or not-attached state, and clear live gateway bindings before the logical session is considered fully stopped.

Rationale: treating first attach and restart as the same event would blur lifecycle edges and make state semantics harder to reason about.

### 9) Runtime integration splits into capability publication, optional auto-attach, gateway-aware control, and bounded upstream recovery

Runtime integration now has four layers instead of one:

1. capability publication:
   new runtime-owned tmux-backed sessions publish attach metadata by default in v1, making them gateway-capable even when no gateway is running
2. optional auto-attach:
   a start-time flag may request immediate gateway attach after session startup, but that is a convenience path rather than the only path
3. gateway-aware control:
   when a live gateway exists, gateway-aware tools validate the live bindings structurally, use `GET /health` as the authoritative liveness check, and then use the gateway for managed request submission and status reads
4. bounded upstream recovery:
   when a gateway remains alive but the managed agent fails, runtime-owned backend integration may reconnect to the same upstream instance or bind a replacement upstream instance for the same logical session without forcing a new gateway root

This suggests a semantic shift for launch flags:

- `--enable-gateway` is no longer best thought of as "this session may ever have a gateway"
- it becomes "auto-attach a gateway at launch if possible"

Runtime-owned direct control can remain available for non-gateway sessions and for sessions where no gateway is currently attached. In v1, gateway-aware control paths require an already-running gateway and fail explicitly if none is attached; a future explicit "ensure attached" mode can be considered later, but ordinary control commands do not auto-attach the gateway as a side effect.

If launch-time auto-attach fails after the managed agent has already started, the runtime should keep that session running and return a structured partial-start failure that includes the live session identity or manifest path plus the gateway-attach error. The gateway is optional enough that bind or startup failure should not destroy a successfully started agent session implicitly.

For runtime-owned recovery, preserving the stable session root matters more than preserving the first backend process. A replacement managed-agent instance should be publishable as "the next upstream incarnation of the same logical session" rather than forcing the gateway to look like it belongs to an entirely new session. The gateway should record that instance change explicitly in status and history.

For future manual sessions, the same idea applies: publish attach metadata first, then decide later whether or when to actually start the gateway.

Rationale: this keeps runtime launch simple while making attach-later and graceful upstream failure handling first-class design goals instead of special exceptions.

## Risks / Trade-offs

- [Gateway attach metadata is present but incomplete or stale] -> Version the attach contract, validate it strictly, and fail attach explicitly rather than guessing.
- [Clients trust stale live gateway env bindings after a crash] -> Treat tmux env bindings as hints and require health or run-state validation before use.
- [Later attach misses important earlier operator or backend events] -> Define the initial attach state as snapshot-based and do not promise full pre-attach history.
- [Independent lifecycle makes host and port less stable] -> Distinguish desired listener config from live instance bindings and avoid treating host or port as permanent session identity.
- [Manual session support becomes too magical] -> Require a documented attach contract for manual sessions instead of trying to infer arbitrary tmux layouts.
- [Runtime and gateway-aware control paths diverge] -> Keep gateway-aware behavior explicit and preserve direct control for sessions with no gateway attached.
- [Operator expectations become unclear about whether a session "has a gateway"] -> Use explicit language and status distinctions between gateway-capable and gateway-running.
- [Prompts are replayed blindly after the managed agent is rebound to a replacement instance] -> Separate stable session identity from current managed-agent instance epoch and require reconciliation before unsafe replay.
- [Gateway health and managed-agent availability get conflated] -> Keep `/health` gateway-local and carry upstream connectivity, recovery, and admission state through `state.json` and `GET /v1/status`.

## Migration Plan

1. Reframe the design from "same-window sidecar launched before the TUI" to "optional independently managed companion process with no visible operator surface."
2. Introduce a stable secret-free attach contract for runtime-owned tmux sessions and publish it through tmux envs alongside existing manifest and agent-definition pointers, using a session-root-first layout where the gateway lives under the session's own runtime directory.
3. Keep start-time gateway attachment as an optional convenience flow rather than a prerequisite for gateway capability.
4. Add explicit attach and detach lifecycle surfaces for runtime-owned sessions so the gateway can be started or stopped independently.
5. Extend the gateway status model so it keeps gateway health separate from upstream agent connectivity, recovery, request-admission state, and current managed-agent instance epoch.
6. Keep the HTTP request API stable and queue-backed while treating lifecycle control as a separate layer and keeping `/health` gateway-local even during upstream outage.
7. Extend the same attach contract to future manual launchers so manually started sessions can opt into gateway attachability later without requiring gig-agents to have launched them originally.

## Open Questions

- What is the minimal manual-session attach-contract profile and backend-metadata shape that stays compatible with the shared v1 `attach.json` schema without overcommitting unsupported backends yet?
