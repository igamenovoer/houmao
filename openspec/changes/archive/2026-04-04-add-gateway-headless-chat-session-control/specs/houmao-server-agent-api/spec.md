## ADDED Requirements

### Requirement: `houmao-server` exposes managed-agent gateway headless chat-session state and next-prompt override routes
`houmao-server` SHALL expose managed-agent gateway headless control routes so callers can inspect headless chat-session state and request a one-shot next-prompt override without directly addressing gateway listener ports.

At minimum, that route family SHALL include:

- `GET /houmao/agents/{agent_ref}/gateway/control/headless/state`
- `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session`

Those routes SHALL operate only through an eligible live gateway attached to the addressed managed agent.

`GET /houmao/agents/{agent_ref}/gateway/control/headless/state` SHALL return the same headless control-state payload shape exposed by the direct gateway route.

`POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session` SHALL proxy the same one-shot next-prompt override behavior exposed by the direct gateway route and SHALL return the updated headless control-state payload from that live gateway.

If the addressed managed agent does not have an eligible live gateway attached, the routes SHALL reject the request explicitly rather than silently falling back to another transport path.

If the addressed managed agent is not headless, the routes SHALL reject the request with validation semantics rather than pretending that a headless control surface exists.

#### Scenario: Caller reads headless control state through the managed-agent API
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/gateway/control/headless/state`
- **AND WHEN** the addressed managed agent has an eligible attached live headless gateway
- **THEN** `houmao-server` returns the live gateway's headless control-state payload for that agent
- **AND THEN** the caller does not need direct knowledge of the gateway host or port

#### Scenario: Caller requests next-prompt override through the managed-agent API
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session` with `mode = new`
- **AND WHEN** the addressed managed agent has an eligible attached live headless gateway
- **THEN** `houmao-server` returns the updated headless control-state payload from that live gateway
- **AND THEN** the response reports a pending one-shot next-prompt override for auto prompt selection

#### Scenario: TUI managed agent rejects headless control routes
- **WHEN** a caller requests `/houmao/agents/{agent_ref}/gateway/control/headless/state` or `/houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session` for a TUI-backed managed agent
- **THEN** `houmao-server` rejects that request with validation semantics
- **AND THEN** it does not pretend that a headless control surface exists for that managed agent

## MODIFIED Requirements

### Requirement: `houmao-server` exposes a native headless prompt-turn API with one active execution per managed agent
For Houmao-managed headless agents, `houmao-server` SHALL expose native Houmao-owned prompt-turn routes:

- `POST /houmao/agents/{agent_ref}/turns`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stderr`
- `POST /houmao/agents/{agent_ref}/interrupt`

`POST /houmao/agents/{agent_ref}/turns` SHALL accept one prompt submission for a headless managed agent and SHALL return a server-owned durable turn identity that callers can use for later status and artifact inspection.

The headless turn request MAY include optional structured `chat_session` with the same semantics used by direct gateway headless prompt control:

- `mode = auto | new | current | tool_last_or_new | exact`
- `id` required only when `mode = exact`

When `chat_session` is omitted, `houmao-server` SHALL treat the request as `mode = auto`.

When an eligible attached live gateway exists for that headless agent, `houmao-server` SHALL route live prompt admission and active-execution control for that headless turn through the gateway-owned per-agent control plane while preserving the same public route and durable turn-inspection contract.

For gateway-backed headless turn admission, `houmao-server` SHALL create the durable turn identity and active-turn record before forwarding live admission to the gateway, SHALL preserve the normalized `chat_session` selector intent for that admission, and SHALL reconcile later execution results back into the same server-owned turn store.

If gateway-backed live admission fails after provisional server-side turn creation, `houmao-server` SHALL reject that submission and SHALL NOT leave an active managed headless turn recorded for that rejected work.

When no eligible attached live gateway exists for that headless agent, `houmao-server` SHALL continue serving this headless turn route through its direct fallback control path and SHALL apply the same `chat_session` semantics there.

The system SHALL allow at most one active managed headless execution per managed agent at a time in v1, regardless of whether the active control owner is the attached gateway or the direct fallback path. If a later prompt submission arrives while a previous managed execution is still active for that agent, the system SHALL reject the later submission explicitly.

Headless turn routes SHALL reject TUI-backed agents explicitly rather than pretending they share the same turn-execution contract.

Malformed `chat_session` values, including missing `id` for `exact` or unexpected `id` for other modes, SHALL be rejected with HTTP `422`.

When `chat_session.mode = current` and the managed headless agent has no pinned current session, the route SHALL fail explicitly rather than silently falling back.

#### Scenario: Attached gateway-backed headless turn submission still returns a durable turn handle
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/turns` for a server-launched managed headless agent with an eligible attached live gateway and no active managed execution
- **THEN** `houmao-server` accepts that prompt submission through the same headless turn route
- **AND THEN** the response includes a server-owned durable `turn_id` that callers can use for later status and artifact inspection because the server created that durable turn before handing live admission to the gateway

#### Scenario: Headless turn submission accepts explicit fresh-session selection
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/turns` for a managed headless agent with `chat_session.mode = new`
- **THEN** `houmao-server` preserves that selector through the active control path for that turn
- **AND THEN** the turn does not reuse the previously pinned current provider session for that prompt

#### Scenario: Headless turn tool-native latest selection becomes current after success
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/turns` for a managed headless agent with `chat_session.mode = tool_last_or_new`
- **AND WHEN** the tool successfully resumes or creates a concrete provider session for that turn
- **THEN** `houmao-server` records that concrete provider session as the managed agent's current session
- **AND THEN** later auto turns continue from that pinned current session unless another selector changes it

#### Scenario: Current mode fails explicitly when no current session is pinned
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/turns` for a managed headless agent with `chat_session.mode = current`
- **AND WHEN** that managed agent has no pinned current provider session
- **THEN** `houmao-server` rejects that request explicitly
- **AND THEN** it does not silently fall back to auto or fresh bootstrap

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

### Requirement: `houmao-server` exposes managed-agent gateway direct prompt-control routes
`houmao-server` SHALL expose a managed-agent gateway direct prompt-control route so callers can require immediate live prompt dispatch semantics without directly addressing gateway listener ports.

At minimum, that route family SHALL include:

- `POST /houmao/agents/{agent_ref}/gateway/control/prompt`

That route SHALL accept the same `GatewayPromptControlRequestV1` payload shape used by the direct gateway route `POST /v1/control/prompt` and SHALL return the same `GatewayPromptControlResultV1` success payload shape.

For headless targets, that payload SHALL include the same optional structured `chat_session` field and semantics as the direct gateway route.

The server SHALL satisfy that route by proxying an eligible attached live gateway or by preserving the same selector semantics through the server-backed headless admission path rather than by introducing a second inconsistent prompt-control contract inside `houmao-server`.

If the addressed managed agent does not have an eligible live gateway attached, or if the live gateway rejects prompt control because the target is not ready, unavailable, unsupported, invalid, or otherwise refused, the route SHALL reject the request explicitly rather than fabricating queued acceptance.

For TUI-backed managed agents, `chat_session.mode = new` SHALL be accepted and preserved through the live gateway prompt-control path, while `chat_session.mode = auto | current | tool_last_or_new | exact` SHALL return validation semantics rather than being ignored.

The route SHALL remain distinct from `POST /houmao/agents/{agent_ref}/gateway/requests`; immediate prompt control SHALL NOT be redefined as queued semantic gateway request submission.

#### Scenario: Caller dispatches headless prompt with explicit current selector through the managed-agent API
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/control/prompt` with valid prompt text and `chat_session.mode = current`
- **AND WHEN** the addressed managed agent has an eligible attached live headless gateway and is prompt-ready
- **THEN** `houmao-server` preserves that selector through the managed agent's live prompt-control path
- **AND THEN** the caller does not need to contact the gateway listener endpoint directly to send the prompt

#### Scenario: Prompt-control refusal is propagated explicitly
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/control/prompt`
- **AND WHEN** the addressed live gateway refuses prompt control explicitly
- **THEN** `houmao-server` rejects that request explicitly
- **AND THEN** the response does not claim that the prompt was accepted for later queued execution

#### Scenario: TUI prompt control accepts explicit new-session reset selector
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/control/prompt` for a TUI-backed managed agent with `chat_session.mode = new`
- **AND WHEN** the addressed managed agent has an eligible attached live TUI gateway
- **THEN** `houmao-server` preserves that selector through the managed agent's live prompt-control path
- **AND THEN** the caller does not need to contact the gateway listener endpoint directly to request the reset-and-send workflow

#### Scenario: TUI prompt control rejects unsupported explicit session selector
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/control/prompt` for a TUI-backed managed agent with `chat_session.mode = current`
- **THEN** `houmao-server` rejects that request with validation semantics
- **AND THEN** it does not ignore the selector and pretend that prompt control succeeded

#### Scenario: Direct prompt control remains separate from queued gateway requests
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/control/prompt`
- **THEN** `houmao-server` proxies that request to the live gateway direct prompt-control route or equivalent selector-preserving headless path
- **AND THEN** it does not rewrite the request into `POST /houmao/agents/{agent_ref}/gateway/requests`
