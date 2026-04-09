## MODIFIED Requirements

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

Interrupt requests that target a managed TUI agent SHALL deliver one best-effort `Escape` interrupt signal whenever the resolved TUI control path is reachable, even when coarse tracked TUI state does not currently report active interruptible work.

Interrupt requests that target a managed headless agent with no active interruptible work SHALL return an explicit transport-neutral no-op response rather than pretending that an interrupt was delivered.

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

#### Scenario: TUI interrupt ignores delayed idle tracking
- **WHEN** a caller submits an `interrupt` managed-agent request for a managed TUI agent
- **AND WHEN** the resolved TUI control path is reachable
- **AND WHEN** coarse tracked TUI state currently reports `idle` or another non-active phase
- **THEN** `houmao-server` still dispatches one best-effort `Escape` interrupt signal
- **AND THEN** the server does not convert that request into a transport-neutral no-op solely because tracked TUI state lagged the visible live surface

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

#### Scenario: Headless interrupt with no active work returns explicit no-op detail
- **WHEN** a caller submits an `interrupt` managed-agent request for a managed headless agent with no active interruptible work
- **THEN** `houmao-server` returns the same transport-neutral accepted response family with explicit no-op detail
- **AND THEN** the caller is not forced to guess whether the interrupt request was delivered or ignored

#### Scenario: Invalid managed-agent request payload returns validation semantics
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/requests` with an invalid typed request payload
- **THEN** `houmao-server` rejects that request with HTTP `422`
- **AND THEN** the managed-agent request route does not reinterpret that invalid payload as a transport-private prompt submission
