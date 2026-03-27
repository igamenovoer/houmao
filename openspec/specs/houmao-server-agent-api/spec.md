## Purpose
Define the Houmao-owned managed-agent API for shared managed-agent discovery, transport-neutral read surfaces, and native headless lifecycle control.
## Requirements
### Requirement: `houmao-server` exposes a transport-neutral managed-agent read API
`houmao-server` SHALL expose Houmao-owned managed-agent routes in addition to the CAO-compatible core API and the existing terminal-keyed Houmao routes.

The managed-agent read surface SHALL include at minimum:

- `GET /houmao/agents`
- `GET /houmao/agents/{agent_ref}`
- `GET /houmao/agents/{agent_ref}/state`
- `GET /houmao/agents/{agent_ref}/history`

Those routes SHALL work for both TUI-backed agents and headless agents admitted into server authority.

The managed-agent identity returned by those routes SHALL include a transport discriminator plus a server-owned stable tracked-agent identity.

The managed-agent state returned by those routes SHALL use a transport-neutral contract for coarse availability and turn posture, and SHALL NOT require callers to interpret TUI-only parsed-surface fields or headless-only raw artifact files.

`GET /houmao/agents/{agent_ref}/history` SHALL expose bounded coarse recent managed-agent history across both transports rather than a durable per-turn log surface.

#### Scenario: Shared discovery lists both TUI and headless managed agents
- **WHEN** `houmao-server` is managing one TUI-backed agent and one headless Claude agent
- **THEN** `GET /houmao/agents` returns both managed agents
- **AND THEN** each returned entry identifies its transport kind without requiring a caller to infer it from route shape alone

#### Scenario: Shared state is readable without terminal scraping
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state` for a managed agent
- **THEN** `houmao-server` returns a transport-neutral coarse state payload for that agent
- **AND THEN** the caller does not need to reconstruct that coarse state by scraping raw terminal output or headless artifact files directly

#### Scenario: Shared history stays bounded and coarse
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/history` for a managed headless or TUI agent
- **THEN** `houmao-server` returns bounded coarse recent managed-agent history for that agent
- **AND THEN** the route does not redefine itself as the durable per-turn history surface

### Requirement: `houmao-server` exposes a native headless launch and stop API
For Houmao-managed headless agents, `houmao-server` SHALL expose Houmao-owned lifecycle routes that do not depend on CAO session or terminal creation.

At minimum, the native headless lifecycle surface SHALL include:

- `POST /houmao/agents/headless/launches`
- `POST /houmao/agents/{agent_ref}/stop`

`POST /houmao/agents/headless/launches` SHALL accept a resolved runtime launch request for a native headless agent.

In v1, that launch request SHALL require at minimum:

- `tool`
- `working_directory`
- `agent_def_dir`
- `brain_manifest_path`

That request MAY include optional identity and prompt-provenance hints such as:

- `role_name`
- `agent_name`
- `agent_id`

When `role_name` is omitted, `null`, or otherwise intentionally absent, `houmao-server` SHALL treat that launch as a valid brain-only launch and SHALL use an empty system prompt.

The raw HTTP launch contract SHALL NOT rely on pair-style convenience fields such as `provider`, `agent_source`, or installed profile name as its normative launch shape.

Validation failures such as missing required resolved launch fields or conflicting launch-input combinations SHALL return HTTP `422`.

When a headless launch succeeds, `houmao-server` SHALL return the managed-agent identity plus server-owned manifest and session-root pointers for the launched headless agent.

Native headless launch SHALL NOT require or depend on creating a child-CAO session or terminal first.

`POST /houmao/agents/{agent_ref}/stop` SHALL stop a managed headless agent through the Houmao-owned headless lifecycle rather than through CAO terminal-stop semantics.

#### Scenario: Native headless launch creates a managed agent without CAO terminal identity
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` for a Claude headless agent
- **THEN** `houmao-server` launches that headless agent through a Houmao-owned headless path
- **AND THEN** the returned managed-agent identity does not require a CAO `terminal_id`

#### Scenario: Native headless launch accepts resolved runtime inputs with optional role metadata
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` with `tool`, `working_directory`, `agent_def_dir`, and `brain_manifest_path`
- **THEN** `houmao-server` validates that request as a native headless launch request
- **AND THEN** a successful response returns the tracked-agent identity plus manifest and session-root pointers for the launched headless agent

#### Scenario: Brain-only native headless launch uses an empty system prompt
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` without `role_name`
- **THEN** `houmao-server` accepts that launch as a brain-only launch
- **AND THEN** the launched agent uses an empty system prompt instead of failing role validation

#### Scenario: Convenience-only launch shape is rejected with validation semantics
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` using only convenience fields such as `provider` or `agent_source` without the required resolved runtime inputs
- **THEN** `houmao-server` rejects that request with HTTP `422`
- **AND THEN** the raw server launch contract remains native and explicit rather than convenience-shaped

#### Scenario: Native headless stop does not use terminal-stop compatibility routes
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/stop` for a managed headless agent
- **THEN** `houmao-server` stops that agent through the Houmao-owned headless lifecycle
- **AND THEN** the caller does not need to treat the headless agent as a fake CAO terminal to stop it

### Requirement: Managed-agent stop supports TUI-backed agents
`POST /houmao/agents/{agent_ref}/stop` SHALL support both managed headless agents and managed TUI-backed agents.

For managed headless agents, the route SHALL continue using the native headless lifecycle stop path.

For managed TUI-backed agents, the route SHALL resolve the addressed managed agent to its pair-owned CAO session and stop it through the existing pair-managed session-delete lifecycle rather than requiring the caller to resolve and delete a raw CAO session separately.

The route SHALL keep using managed-agent alias resolution rather than forcing callers to switch from managed-agent references to raw session identifiers.

#### Scenario: TUI-backed managed agent stops through the shared managed-agent route
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/stop` for a managed TUI-backed agent
- **THEN** `houmao-server` stops that managed agent through the pair-owned TUI lifecycle
- **AND THEN** the caller does not need to issue a separate raw `/cao/sessions/{session_name}` delete request to stop that agent

### Requirement: Managed-agent lookup resolves through explicit aliases
`houmao-server` SHALL resolve `/houmao/agents/{agent_ref}` lookups through a server-owned tracked-agent identity plus explicit aliases.

At minimum, supported aliases SHALL include:

- the server-owned tracked-agent id
- `terminal_id` and `session_name` for TUI-backed agents
- runtime-owned manifest-backed identity such as runtime session id when present
- `agent_id` and `agent_name` when present

When more than one managed agent matches the supplied alias, `houmao-server` SHALL reject the lookup as ambiguous rather than silently selecting one match.

#### Scenario: TUI terminal alias resolves to the shared managed-agent surface
- **WHEN** a caller looks up `/houmao/agents/{agent_ref}` using the `terminal_id` alias of a managed TUI agent
- **THEN** `houmao-server` resolves that alias to the corresponding managed-agent identity
- **AND THEN** the caller can inspect shared managed-agent state without switching to a different identity namespace first

#### Scenario: Ambiguous alias is rejected explicitly
- **WHEN** more than one managed agent matches the supplied `/houmao/agents/{agent_ref}` alias
- **THEN** `houmao-server` rejects the lookup as ambiguous
- **AND THEN** it does not silently choose one managed agent and hide the identity conflict

### Requirement: Headless prompt control is modeled as turn resources
For server-launched managed headless agents, `houmao-server` SHALL expose Houmao-owned turn-control and turn-inspection routes under `/houmao/agents/{agent_ref}`.

At minimum, the headless route surface SHALL include:

- `POST /houmao/agents/{agent_ref}/turns`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stderr`
- `POST /houmao/agents/{agent_ref}/interrupt`

`POST /houmao/agents/{agent_ref}/turns` SHALL accept one prompt submission for a headless managed agent and SHALL return a server-owned durable turn identity that callers can use for later status and artifact inspection.

When an eligible attached live gateway exists for that headless agent, `houmao-server` SHALL route live prompt admission and active-execution control for that headless turn through the gateway-owned per-agent control plane while preserving the same public route and durable turn-inspection contract.

For gateway-backed headless turn admission, `houmao-server` SHALL create the durable turn identity and active-turn record before forwarding live admission to the gateway, and SHALL reconcile later execution results back into the same server-owned turn store.

If gateway-backed live admission fails after provisional server-side turn creation, `houmao-server` SHALL reject that submission and SHALL NOT leave an active managed headless turn recorded for that rejected work.

When no eligible attached live gateway exists for that headless agent, `houmao-server` SHALL continue serving this headless turn route through its direct fallback control path.

The system SHALL allow at most one active managed headless execution per managed agent at a time in v1, regardless of whether the active control owner is the attached gateway or the direct fallback path. If a later prompt submission arrives while a previous managed execution is still active for that agent, the system SHALL reject the later submission explicitly.

Headless turn routes SHALL reject TUI-backed agents explicitly rather than pretending they share the same turn-execution contract.

#### Scenario: Attached gateway-backed headless turn submission still returns a durable turn handle
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/turns` for a server-launched managed headless agent with an eligible attached live gateway and no active managed execution
- **THEN** `houmao-server` accepts that prompt submission through the same headless turn route
- **AND THEN** the response includes a server-owned durable `turn_id` that callers can use for later status and artifact inspection because the server created that durable turn before handing live admission to the gateway

#### Scenario: Concurrent headless turn submission is rejected across control modes
- **WHEN** a managed headless agent already has one active managed execution
- **AND WHEN** a caller submits another `POST /houmao/agents/{agent_ref}/turns` for that same agent
- **THEN** `houmao-server` rejects the later submission explicitly
- **AND THEN** it does not start overlapping managed headless executions whether the active control owner is an attached gateway or the direct fallback path

#### Scenario: Restart preserves active-turn conflict handling
- **WHEN** `houmao-server` restarts while a previously accepted headless turn for one managed agent remains active
- **AND WHEN** a caller submits a new `POST /houmao/agents/{agent_ref}/turns` for that same agent after restart
- **THEN** `houmao-server` continues rejecting the later submission until the recorded earlier turn reconciles to a terminal state
- **AND THEN** single-active-execution semantics remain stable across restart

#### Scenario: Gateway-backed headless admission rejection does not leave an active turn behind
- **WHEN** `houmao-server` provisionally creates a durable headless turn for an attached gateway-backed agent
- **AND WHEN** the attached gateway rejects or cannot start live admission for that turn
- **THEN** `houmao-server` rejects the submission instead of leaving that provisionally created turn recorded as active managed work
- **AND THEN** later prompt submissions are not blocked by a ghost active turn

#### Scenario: TUI agent rejects headless turn submission
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/turns` for a TUI-backed managed agent
- **THEN** `houmao-server` rejects that request explicitly
- **AND THEN** the caller must continue using the transport-appropriate TUI control surface instead of the headless turn API

### Requirement: Headless turn inspection exposes structured events and durable artifacts
For accepted headless turns, `houmao-server` SHALL expose both structured event inspection and raw durable artifact inspection.

`GET /houmao/agents/{agent_ref}/turns/{turn_id}` SHALL report the current or terminal status of the referenced turn using manifest and artifact-backed evidence.

`GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` SHALL expose structured event records derived from machine-readable headless turn output rather than requiring callers to parse raw `stdout.jsonl` themselves.

The artifact routes SHALL expose the durable turn artifacts for that accepted headless turn without requiring direct filesystem access from the caller.

`POST /houmao/agents/{agent_ref}/interrupt` SHALL provide best-effort interruption for the active headless turn of that agent.

#### Scenario: Caller inspects structured headless turn events
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` for an accepted headless turn
- **THEN** `houmao-server` returns structured event records derived from the machine-readable turn output
- **AND THEN** the caller does not need to read or parse `stdout.jsonl` directly from the filesystem

#### Scenario: Caller inspects durable stderr artifact
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stderr` for an accepted headless turn
- **THEN** `houmao-server` returns the durable stderr artifact for that turn
- **AND THEN** the caller does not need direct filesystem access to the headless session root to inspect it

#### Scenario: Interrupt targets the active headless turn only
- **WHEN** a managed headless agent has one active server-managed turn
- **AND WHEN** a caller submits `POST /houmao/agents/{agent_ref}/interrupt`
- **THEN** `houmao-server` delivers a best-effort interrupt to that active headless turn
- **AND THEN** the interrupt request does not fabricate interruption for already-completed turns

### Requirement: Durable headless detail stays on per-turn resources rather than shared `/history`
For managed headless agents, durable post-turn inspection SHALL live on the per-turn route family rather than on the shared `/houmao/agents/{agent_ref}/history` route.

`GET /houmao/agents/{agent_ref}/history` MAY be empty or truncated after restart even when earlier headless turns remain inspectable through their per-turn status, event, and artifact routes.

#### Scenario: Headless caller uses per-turn routes for durable inspection
- **WHEN** a caller needs durable detail for a previously completed headless turn
- **THEN** the caller can inspect that turn through `/houmao/agents/{agent_ref}/turns/{turn_id}` and its nested `events` or `artifacts` routes
- **AND THEN** the shared `/history` route does not need to duplicate that durable turn detail

### Requirement: Managed-agent summary state exposes gateway and mailbox posture and includes a detailed state route
In addition to the existing managed-agent summary state route, `houmao-server` SHALL expose `GET /houmao/agents/{agent_ref}/state/detail` for transport-specific inspection.

`GET /houmao/agents/{agent_ref}/state` SHALL remain the coarse shared state surface, and SHALL include redacted mailbox and gateway summary fields when those capabilities are known for the addressed managed agent.

The detailed route SHALL use the same managed-agent alias resolution rules as the rest of the managed-agent API.

When an eligible live gateway is attached and healthy enough to serve current live state for the addressed managed agent, `houmao-server` SHALL project current gateway-backed live state and detailed posture for that agent through the same summary and detail route shapes rather than forcing the caller onto a different route family.

When no eligible live gateway is attached, `houmao-server` SHALL continue serving those routes through its direct fallback state path for that agent.

When an attached gateway is unhealthy or unreachable, `houmao-server` SHALL either serve the route through direct fallback when direct fallback is supported and safe for that agent, or reject the route with HTTP `503`. It SHALL NOT treat stale gateway-backed state as indefinitely authoritative.

The public route family SHALL remain caller-transparent in this phase: callers SHALL NOT need to know whether the current state projection comes from an attached gateway or from the direct fallback path in order to use the managed-agent summary and detail routes.

#### Scenario: Summary state shows mailbox and gateway posture
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state` for a mailbox-enabled managed agent whose gateway capability is published
- **THEN** the returned coarse state includes redacted mailbox and gateway summary information
- **AND THEN** the caller can tell that the agent is mailbox-enabled and gateway-capable without reading manifests directly

#### Scenario: Attached gateway-backed detail keeps the same route shape
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state/detail` for a managed agent with an eligible attached live gateway
- **THEN** `houmao-server` returns the same managed-agent detail route shape for that agent
- **AND THEN** the live detail payload is projected from gateway-backed per-agent state rather than requiring the caller to contact the gateway directly

#### Scenario: No-gateway fallback detail remains available through the same route
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state/detail` for a managed agent with no eligible attached live gateway
- **THEN** `houmao-server` continues serving that managed-agent detail route through its direct fallback state path
- **AND THEN** the caller does not need a gateway sidecar to inspect the managed agent through the supported server route

#### Scenario: Attached but unhealthy gateway uses fallback or unavailable semantics for detail
- **WHEN** a caller requests managed-agent summary or detail for an agent whose gateway is attached but currently unhealthy or unreachable
- **THEN** `houmao-server` serves direct fallback state when that fallback remains supported and safe for that agent
- **AND THEN** otherwise it rejects the route with HTTP `503` rather than projecting indefinitely stale gateway state

### Requirement: Managed-agent control accepts transport-neutral request submission
`houmao-server` SHALL expose `POST /houmao/agents/{agent_ref}/requests` as a transport-neutral managed-agent request-submission route.

In this change, that request surface SHALL accept at minimum:

- `submit_prompt`
- `interrupt`

The request body SHALL use a typed request-kind contract rather than a transport-private prompt or terminal-input payload shape.

Accepted requests SHALL return one transport-neutral accepted-request response shape for both `submit_prompt` and `interrupt`.

That accepted response SHALL identify the accepted request and MAY include explicit no-op detail when the request required no transport mutation.

For managed agents with an eligible attached live gateway, accepted request submission through that route SHALL be backed by the gateway-owned per-agent control plane for that agent only when that gateway is healthy and admissible for the current request.

For managed agents without an eligible attached live gateway, accepted request submission through that route SHALL use the direct fallback control path for that agent.

If an attached gateway is unhealthy or unreachable at request-submission time, `houmao-server` SHALL use direct fallback control only when that fallback is supported and safe for the addressed agent. Otherwise it SHALL preserve the current `409` or `503` semantics according to the blocking condition rather than pretending the gateway-backed request was accepted.

For managed headless agents, the accepted response SHALL include enough metadata to relate the accepted request to the created headless turn when a new durable headless turn was created for that prompt.

This change SHALL NOT require a durable `/houmao/agents/{agent_ref}/requests/{request_id}` follow-up route.

The existing headless `/turns` route family SHALL remain the durable headless per-turn detail surface.

Request-validation failures on `POST /houmao/agents/{agent_ref}/requests` SHALL return HTTP `422`.

Admission conflicts such as an already-active headless turn or reconciliation-required execution blocking SHALL return HTTP `409`.

Managed-agent unavailable or recovery-blocked admission failures SHALL return HTTP `503`.

Interrupt requests that target a managed agent with no active interruptible work SHALL return an explicit transport-neutral no-op response rather than pretending that an interrupt was delivered.

#### Scenario: Attached TUI prompt request uses the same server route through gateway-backed control
- **WHEN** a caller submits a `submit_prompt` managed-agent request for a managed TUI agent with an eligible attached live gateway
- **THEN** `houmao-server` accepts that request through the same managed-agent request route family
- **AND THEN** live queueing and prompt delivery for that request are handled through the attached gateway rather than through a separate caller-visible route family

#### Scenario: No-gateway headless prompt request still returns turn linkage
- **WHEN** a caller submits a `submit_prompt` managed-agent request for a managed headless agent that can accept a new prompt and has no eligible attached live gateway
- **THEN** `houmao-server` accepts that request through its direct fallback control path
- **AND THEN** the accepted response uses the transport-neutral request envelope and identifies the corresponding durable headless turn created for that prompt

#### Scenario: Interrupt request remains transport-neutral across both control modes
- **WHEN** a caller submits an `interrupt` managed-agent request for a managed TUI or headless agent
- **THEN** `houmao-server` accepts that request through the same managed-agent request surface
- **AND THEN** whether the interrupt is delivered through an attached gateway or a direct fallback path remains an implementation detail rather than a caller-visible API split

#### Scenario: Busy headless prompt admission returns conflict semantics
- **WHEN** a caller submits a `submit_prompt` managed-agent request for a managed headless agent that already has one active managed execution
- **THEN** `houmao-server` rejects that admission with HTTP `409`
- **AND THEN** the request route does not silently overlap a second managed headless execution for that agent

#### Scenario: Recovery-blocked managed agent returns unavailable semantics
- **WHEN** a caller submits a managed-agent request for an agent whose authority record exists but whose active control path cannot currently admit work
- **THEN** `houmao-server` rejects that request with HTTP `503`
- **AND THEN** the response does not pretend that the request was accepted for later execution

#### Scenario: Unhealthy attached gateway does not force unsafe request routing
- **WHEN** a caller submits a managed-agent request for an agent whose gateway is attached but unhealthy or unreachable
- **THEN** `houmao-server` uses direct fallback only when that fallback is still supported and safe for that agent
- **AND THEN** otherwise the request is rejected with the existing `409` or `503` semantics rather than being silently accepted against an inoperable gateway

#### Scenario: Interrupt with no active work returns explicit no-op detail
- **WHEN** a caller submits an `interrupt` managed-agent request for a managed agent with no active interruptible work
- **THEN** `houmao-server` returns the same transport-neutral accepted response family with explicit no-op detail
- **AND THEN** the caller is not forced to guess whether the interrupt request was delivered or ignored

#### Scenario: Invalid managed-agent request payload returns validation semantics
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/requests` with an invalid typed request payload
- **THEN** `houmao-server` rejects that request with HTTP `422`
- **AND THEN** the managed-agent request route does not reinterpret that invalid payload as a transport-private prompt submission

### Requirement: `houmao-server` exposes gateway-mediated managed-agent request routes
`houmao-server` SHALL expose server-owned gateway-mediated managed-agent request routes in addition to the existing transport-neutral managed-agent request route.

At minimum, that route family SHALL include:

- `POST /houmao/agents/{agent_ref}/gateway/requests`

That route SHALL accept gateway request kinds compatible with the live gateway request surface, including at minimum:

- `submit_prompt`
- `interrupt`

The server SHALL resolve the managed agent, verify that an eligible live gateway is attached, and proxy the accepted request through the live gateway authority without requiring the caller to discover the gateway listener endpoint.

If no eligible live gateway is attached, the route SHALL reject the request explicitly rather than silently falling back to another transport path.

#### Scenario: Gateway-mediated prompt request is accepted through `houmao-server`
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/requests` with gateway request kind `submit_prompt`
- **AND WHEN** the addressed managed agent has an eligible live gateway attached
- **THEN** `houmao-server` accepts that request through the managed agent's live gateway authority
- **AND THEN** the caller does not need direct knowledge of the gateway host or port

#### Scenario: Missing live gateway rejects gateway-mediated request explicitly
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/requests`
- **AND WHEN** the addressed managed agent does not have an eligible live gateway attached
- **THEN** `houmao-server` rejects that request explicitly
- **AND THEN** it does not pretend that the gateway-mediated request was accepted for later execution

### Requirement: `houmao-server` exposes managed-agent gateway raw control-input routes
`houmao-server` SHALL expose a managed-agent gateway raw control-input route so callers can deliver live gateway `send-keys` operations without addressing gateway listener ports directly.

At minimum, that route family SHALL include:

- `POST /houmao/agents/{agent_ref}/gateway/control/send-keys`

That route SHALL accept the same `GatewayControlInputRequestV1` payload shape used by the direct gateway route `POST /v1/control/send-keys` and SHALL return the same `GatewayControlInputResultV1` response shape.

The server SHALL satisfy that route by proxying an eligible attached live gateway rather than by introducing a second direct tmux-control-input path inside `houmao-server`.

If the addressed managed agent does not have an eligible live gateway attached, or if live gateway admission is blocked for that control-input request, the route SHALL reject the request explicitly rather than silently fabricating success.

The route SHALL remain distinct from `POST /houmao/agents/{agent_ref}/gateway/requests`; raw control input SHALL NOT be redefined as a queued semantic gateway request kind.

#### Scenario: Caller sends raw control input through the managed-agent API
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/control/send-keys` with a valid `GatewayControlInputRequestV1` body
- **AND WHEN** the addressed managed agent has an eligible live gateway attached
- **THEN** `houmao-server` returns the `GatewayControlInputResultV1` payload from that live gateway
- **AND THEN** the caller does not need to contact the gateway listener endpoint directly to deliver the control input

#### Scenario: Raw control input fails clearly when no live gateway is attached
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/control/send-keys`
- **AND WHEN** the addressed managed agent does not have an eligible live gateway attached
- **THEN** `houmao-server` rejects that request explicitly
- **AND THEN** the response does not claim that the control input was delivered

#### Scenario: Raw control input remains separate from queued gateway requests
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/control/send-keys`
- **THEN** `houmao-server` proxies that request to the live gateway raw control-input route
- **AND THEN** it does not rewrite the request into `POST /houmao/agents/{agent_ref}/gateway/requests`

### Requirement: `houmao-server` exposes pair-owned managed-agent mail routes
`houmao-server` SHALL expose pair-owned managed-agent mail follow-up routes so callers can perform mailbox operations through the managed-agent API without directly addressing gateway listener ports.

At minimum, that route family SHALL include:

- `GET /houmao/agents/{agent_ref}/mail/status`
- `POST /houmao/agents/{agent_ref}/mail/check`
- `POST /houmao/agents/{agent_ref}/mail/send`
- `POST /houmao/agents/{agent_ref}/mail/reply`

In v1, the server SHALL satisfy those routes by proxying an attached eligible live gateway rather than by introducing a separate direct runtime-backed mailbox path.

Those routes SHALL coexist with the existing `/houmao/agents/{agent_ref}/gateway/mail-notifier` configuration routes rather than replacing them. The `gateway/mail-notifier` routes remain background notifier-configuration surfaces, while `mail/*` is the foreground mailbox-operation surface.

If the addressed managed agent does not expose pair-owned mailbox follow-up capability or does not have an eligible live gateway attached, the routes SHALL reject the request explicitly rather than silently fabricating success.

#### Scenario: Caller checks mail through the managed-agent API
- **WHEN** a caller requests `POST /houmao/agents/{agent_ref}/mail/check` for a managed agent that exposes pair-owned mailbox follow-up capability
- **AND WHEN** the addressed managed agent has an eligible live gateway attached
- **THEN** `houmao-server` returns the managed-agent mail-check result through its own API
- **AND THEN** the caller does not need to contact the gateway listener endpoint directly to perform that check

#### Scenario: Mail follow-up fails clearly when mailbox capability or live gateway access is unavailable
- **WHEN** a caller submits one of the managed-agent mail routes for an addressed agent that does not expose pair-owned mailbox follow-up capability or does not have an eligible live gateway attached
- **THEN** `houmao-server` rejects that request explicitly
- **AND THEN** the response does not claim that the mailbox action succeeded

### Requirement: `houmao-server` exposes managed-agent gateway operational routes
For managed agents whose sessions are gateway-capable, `houmao-server` SHALL expose managed-agent gateway lifecycle and inspection routes.

At minimum, that route family SHALL include:

- `POST /houmao/agents/{agent_ref}/gateway/attach`
- `POST /houmao/agents/{agent_ref}/gateway/detach`
- `GET /houmao/agents/{agent_ref}/gateway`
- `GET /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `PUT /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier`

Those routes SHALL operate against the same underlying gateway capability and durable gateway state used by the gateway sidecar itself.

Those routes SHALL NOT redefine the gateway mailbox facade as part of this change; direct mailbox operations remain on the gateway HTTP surface.

If a healthy live gateway is already attached for the addressed managed agent, `POST /houmao/agents/{agent_ref}/gateway/attach` SHALL behave idempotently and return the current attachment or status rather than starting a second gateway instance.

If persisted and live gateway state disagree or require reconciliation before safe reuse, `POST /houmao/agents/{agent_ref}/gateway/attach` SHALL fail explicitly with HTTP `409` rather than silently replacing the existing live gateway state.

#### Scenario: Server attaches a gateway for a managed headless agent
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/attach` for a gateway-capable managed headless agent
- **THEN** `houmao-server` attaches a live gateway for that managed agent through the official managed-agent route family
- **AND THEN** the caller does not need to resume manifests or invoke runtime-private attach logic directly

#### Scenario: Gateway status remains readable through the managed-agent API
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/gateway` for a managed agent whose gateway is detached or not yet attached
- **THEN** `houmao-server` still returns the current gateway capability or offline status for that managed agent
- **AND THEN** the caller does not need direct filesystem access to inspect stable gateway state

#### Scenario: Gateway attach is idempotent when a healthy gateway is already attached
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/attach` for a managed agent that already has a healthy live gateway attached
- **THEN** `houmao-server` returns the current gateway attachment or status rather than starting a second gateway process
- **AND THEN** the attach route remains safe for retry-oriented automation

#### Scenario: Reconciliation-required gateway attach fails explicitly
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/attach` and the persisted gateway state indicates a stale or reconciliation-required condition
- **THEN** `houmao-server` rejects that attach request with HTTP `409`
- **AND THEN** the route does not silently detach or replace the existing gateway state

#### Scenario: Server route controls notifier without redefining the gateway mail facade
- **WHEN** a caller enables or inspects notifier behavior through `/houmao/agents/{agent_ref}/gateway/mail-notifier`
- **THEN** `houmao-server` operates on the same notifier state used by the gateway sidecar
- **AND THEN** mailbox send, check, and reply remain on the gateway HTTP surface rather than being silently redefined under the server route family

### Requirement: Native headless launch accepts official mailbox options while gateway lifecycle remains separate
`POST /houmao/agents/headless/launches` SHALL accept optional structured mailbox configuration in addition to the existing required resolved launch inputs.

Mailbox configuration MAY override or refine the effective mailbox transport and redacted mailbox identity resolved for that managed headless launch.

Gateway lifecycle for the launched managed agent SHALL remain a separate post-launch action under the managed-agent gateway route family and SHALL NOT be coupled to the headless launch request in this change.

Persisted blueprint or manifest-backed gateway defaults MAY still influence a later attach action, but those defaults are not caller-supplied launch inputs for `POST /houmao/agents/headless/launches`.

Notifier configuration SHALL remain a separate operational control action rather than a launch-time identity field.

Validation failures for invalid mailbox launch options or unexpected launch-time gateway fields SHALL return HTTP `422`.

#### Scenario: Native headless launch requests mailbox override
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` with valid required launch inputs and an optional mailbox override block
- **THEN** `houmao-server` validates and applies that mailbox configuration through the official launch contract
- **AND THEN** the launched managed headless agent exposes the resulting mailbox posture through the managed-agent state surfaces

#### Scenario: Native headless launch remains decoupled from gateway attach
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` with valid required launch inputs and later requests `POST /houmao/agents/{agent_ref}/gateway/attach`
- **THEN** `houmao-server` treats the launch and attach steps as separate managed-agent lifecycle actions
- **AND THEN** the managed agent does not need to be re-launched or reconfigured through manifest-private inputs solely to attach a gateway later

#### Scenario: Launch-time gateway fields are rejected explicitly
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` with gateway-specific launch fields that are not part of the official launch contract
- **THEN** `houmao-server` rejects that request with HTTP `422`
- **AND THEN** callers are directed to the managed-agent gateway route family for later attach or detach behavior

### Requirement: Managed headless turn reconciliation is execution-owned
For accepted managed headless turns, `houmao-server` SHALL treat server-owned execution evidence as the primary authority for turn lifecycle and terminal result.

Execution evidence SHALL include, at minimum:

- durable turn artifacts produced by the headless turn runner,
- runner-owned durable process metadata sufficient for post-restart liveness checks,
- the underlying CLI exit or return status,
- parsed machine-readable CLI output when available, and
- explicit server-owned interrupt intent when an interrupt was requested.

tmux session, window, or pane visibility MAY be used for best-effort control, cleanup, or diagnostics, but SHALL NOT by itself finalize, downgrade, or reinterpret a managed headless turn outcome.

For managed headless turns, `unknown` SHALL NOT be used as a normal reconciliation or finalization outcome. When execution evidence is missing or legacy metadata is insufficient, `houmao-server` SHALL fail closed to `failed` and attach explicit diagnostics rather than preserving tmux-watch-era ambiguity.

#### Scenario: Successful headless turn finalizes from durable CLI result
- **WHEN** an accepted managed headless turn later produces a durable terminal result with successful CLI completion evidence
- **THEN** `houmao-server` reports that turn as completed from that execution evidence
- **AND THEN** callers do not need tmux topology to determine that the turn finished successfully

#### Scenario: Unexpected execution loss becomes normal failed turn
- **WHEN** an accepted managed headless turn no longer has live execution evidence
- **AND WHEN** `houmao-server` never recorded an interrupt request for that turn
- **THEN** `houmao-server` reconciles that turn to a terminal failed state
- **AND THEN** the server does not require or expose a special tmux-observed intervention classification to explain the loss

#### Scenario: Interrupt intent controls interrupted outcome
- **WHEN** `houmao-server` previously recorded an interrupt request for an active managed headless turn
- **AND WHEN** the underlying headless execution later ends without a successful completion result
- **THEN** `houmao-server` reconciles that turn as interrupted
- **AND THEN** interrupted outcome comes from server-owned control intent plus execution end rather than tmux window observation alone

#### Scenario: Missing finalization marker still fails closed
- **WHEN** a managed headless worker reaches terminal reconciliation for an accepted turn
- **AND WHEN** no durable terminal result marker exists
- **AND WHEN** the server has no live execution evidence and never recorded an interrupt request for that turn
- **THEN** `houmao-server` finalizes that turn as failed with diagnostic context
- **AND THEN** the server does not emit `unknown` as a normal managed-headless finalization result

### Requirement: Managed headless restart recovery does not depend on tmux watch semantics
When `houmao-server` restarts while a managed headless turn is still recorded as active, later reconciliation SHALL use durable runner artifacts and execution-liveness evidence to determine whether the turn is still active or has already ended.

The server SHALL NOT require the presence of a specific tmux window or pane name in order to preserve or finalize managed headless turn state after restart.

#### Scenario: Restart preserves active turn while execution remains live
- **WHEN** `houmao-server` restarts while a managed headless turn is recorded as active
- **AND WHEN** durable completion artifacts are not yet present but execution evidence still indicates that the underlying CLI turn is live
- **THEN** `houmao-server` continues reporting that turn as active
- **AND THEN** later prompt admission remains blocked until the turn reaches a terminal state

#### Scenario: Restart finalizes active turn from durable artifacts without tmux window matching
- **WHEN** `houmao-server` restarts while a managed headless turn is recorded as active
- **AND WHEN** durable turn artifacts later show a terminal CLI result
- **THEN** `houmao-server` finalizes the turn from those artifacts
- **AND THEN** the server does not need a matching tmux window identity to trust that terminal result

#### Scenario: Restart fails closed when execution is dead and no exit marker exists
- **WHEN** `houmao-server` restarts while a managed headless turn is recorded as active
- **AND WHEN** durable completion artifacts are not present
- **AND WHEN** durable execution-liveness evidence shows the underlying CLI process is no longer live
- **AND WHEN** the server never recorded an interrupt request for that turn
- **THEN** `houmao-server` finalizes that turn as failed with diagnostic context
- **AND THEN** the server does not require tmux window matching to determine that the execution died before completion

#### Scenario: Restarted legacy active turn without process metadata fails closed
- **WHEN** `houmao-server` restarts while a pre-change managed headless turn is still recorded as active
- **AND WHEN** durable completion artifacts are not present
- **AND WHEN** the persisted active-turn record lacks the new execution-liveness metadata needed for restart recovery
- **THEN** `houmao-server` finalizes that turn as failed with explicit diagnostic context
- **AND THEN** the server does not preserve `unknown` as a migration-only recovery bucket

### Requirement: Managed headless tmux inspectability keeps the agent in window 0
For managed tmux-backed headless agents, `houmao-server` SHALL treat tmux window 0 of the bound session as the primary agent surface.

Managed headless turn execution SHALL reuse that stable primary surface and SHALL NOT allocate transient per-turn tmux windows as part of normal managed execution.

Additional windows MAY exist in the same tmux session for auxiliary processes or diagnostics, but `houmao-server` SHALL NOT treat those windows as the canonical agent surface and SHALL NOT require callers or demos to chase them in order to watch the agent itself.

Best-effort tmux-facing diagnostics or fallback control paths for managed headless agents SHALL target the stable primary agent surface rather than assuming that the active turn owns a disposable tmux window.

When managed-headless tmux metadata exposes a window name, `houmao-server` SHALL use the stable name `agent` rather than a per-turn `turn-N` value.

Normal managed-headless interrupt and terminate behavior SHALL NOT destroy the stable primary agent surface through `kill-window`; tmux-facing fallback control SHALL preserve the session and target the stable `agent` surface only as a last resort after process-identity signaling has been attempted.

#### Scenario: Managed active turn stays on the stable primary surface
- **WHEN** a caller submits a managed headless prompt that is accepted as the one active turn for that agent
- **THEN** the managed headless execution runs on the session's stable window-0 agent surface
- **AND THEN** `houmao-server` does not create a separate `turn-N` tmux window for that managed turn

#### Scenario: Auxiliary tmux windows do not redefine the managed agent surface
- **WHEN** the tmux session of a managed headless agent also contains another window for gateway, logs, or diagnostics
- **THEN** `houmao-server` continues treating window 0 as the canonical agent surface
- **AND THEN** auxiliary windows do not change managed inspectability or fallback-control targeting for that agent

#### Scenario: Managed interrupt preserves the stable primary surface
- **WHEN** `houmao-server` interrupts or terminates a managed headless turn whose process identity can no longer be controlled directly
- **THEN** any tmux-facing fallback targets the stable `agent` surface in window 0
- **AND THEN** `houmao-server` does not destroy that stable primary surface as normal turn control
