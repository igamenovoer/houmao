## MODIFIED Requirements

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

Admission conflicts such as an already-active managed headless execution or reconciliation-required execution blocking SHALL return HTTP `409`.

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
- **THEN** `houmao-server` continues rejecting the later submission until the recorded earlier execution reconciles to a terminal state
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
