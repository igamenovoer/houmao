# passive-server-gateway-proxy Specification

## Purpose
Expose a common passive-server entry point for managed-agent gateway control, mail, usage, memory, and inspection. Resolve each agent reference to the owning source and preserve operation semantics, caller authority, and upstream errors.
## Requirements

### Requirement: Passive server provides a gateway status proxy endpoint
The passive server SHALL expose `GET /houmao/agents/{agent_ref}/gateway` that resolves the agent, creates a `GatewayClient` from the registry record's gateway coordinates, and forwards the response from `GET /v1/status`.

The response body SHALL be a `GatewayStatusV1` payload from the live gateway.

If the agent is not found, the endpoint SHALL return 404. If the agent name is ambiguous, it SHALL return 409. If the agent has no live gateway attached, it SHALL return 502 with a descriptive message.

#### Scenario: Gateway status returns the live gateway's status
- **WHEN** the discovery index contains agent `abc123` with a live gateway at `127.0.0.1:9901`
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway`
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayStatusV1` payload from the gateway's `/v1/status`

#### Scenario: Gateway status returns 404 for unknown agent
- **WHEN** the discovery index contains no agent matching `unknown`
- **AND WHEN** a caller sends `GET /houmao/agents/unknown/gateway`
- **THEN** the response status code is 404

#### Scenario: Gateway status returns 502 when no gateway is attached
- **WHEN** the discovery index contains agent `abc123` with no live gateway (gateway field is None or host/port are None)
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway`
- **THEN** the response status code is 502
- **AND THEN** the response body contains a diagnostic message about the gateway not being attached

#### Scenario: Gateway status returns 502 when gateway is unreachable
- **WHEN** the discovery index contains agent `abc123` with gateway coordinates that are unreachable
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway`
- **THEN** the response status code is 502
- **AND THEN** the response body contains the error detail from the failed gateway connection

### Requirement: Passive server provides a gateway request submission proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/gateway/requests` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayRequestCreateV1` payload to `POST /v1/requests`.

The response body SHALL be a `GatewayAcceptedRequestV1` payload from the live gateway.

Agent-not-found (404), ambiguous (409), and no-gateway (502) error handling SHALL follow the same pattern as the gateway status endpoint.

#### Scenario: Request submission forwards to the gateway and returns the accepted response
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/requests` with a valid `GatewayRequestCreateV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayAcceptedRequestV1` payload from the gateway

#### Scenario: Request submission returns 502 when no gateway is attached
- **WHEN** the discovery index contains agent `abc123` with no live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/requests` with a valid body
- **THEN** the response status code is 502

### Requirement: Passive server provides a gateway raw control-input proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/gateway/control/send-keys` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayControlInputRequestV1` payload to `POST /v1/control/send-keys`.

The response body SHALL be a `GatewayControlInputResultV1` payload from the live gateway.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Agent-not-found (404), ambiguous (409), and no-gateway (502) error handling SHALL follow the same pattern as the existing passive gateway status and request-submission endpoints.

#### Scenario: Raw control-input proxy forwards to the gateway and returns the action result
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/send-keys` with a valid `GatewayControlInputRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayControlInputResultV1` payload from the gateway

#### Scenario: Raw control-input proxy returns 502 when no gateway is attached
- **WHEN** the discovery index contains agent `abc123` with no live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/send-keys` with a valid body
- **THEN** the response status code is 502

### Requirement: Passive server provides a gateway direct prompt-control proxy endpoint

The passive server SHALL expose `POST /houmao/agents/{agent_ref}/gateway/control/prompt` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayPromptControlRequestV1` payload to `POST /v1/control/prompt`.

For headless targets, the proxied request body MAY include optional structured `chat_session` with the same semantics as the direct gateway route:

- `mode = auto | new | current | tool_last_or_new | exact`
- `id` required only when `mode = exact`

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The response body SHALL be a `GatewayPromptControlResultV1` payload from the live gateway.

Agent-not-found (404), ambiguous (409), and no-gateway (502) error handling SHALL follow the same pattern as the passive gateway status endpoint. If the live gateway itself refuses prompt control explicitly, including validation rejection of unsupported `chat_session` modes for a TUI target, the passive server SHALL return that refusal explicitly rather than converting it into queued acceptance.

#### Scenario: Direct prompt-control proxy forwards to the gateway and returns the live result
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/prompt` with a valid `GatewayPromptControlRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayPromptControlResultV1` payload from the gateway

#### Scenario: Direct prompt-control proxy returns 502 when no gateway is attached
- **WHEN** the discovery index contains agent `abc123` with no live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/prompt` with a valid body
- **THEN** the response status code is 502

#### Scenario: Direct prompt-control refusal is forwarded explicitly
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/prompt`
- **AND WHEN** the live gateway refuses that prompt-control request explicitly
- **THEN** the passive server returns that refusal explicitly
- **AND THEN** it does not claim that the prompt was accepted for later queued execution

#### Scenario: Structured headless session selector is forwarded unchanged through the proxy
- **WHEN** the discovery index contains agent `abc123` with a live headless gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/prompt` with `chat_session.mode = tool_last_or_new`
- **THEN** the passive server forwards that selector unchanged to the live gateway
- **AND THEN** the passive server does not reinterpret the selector as a passive-server-local session choice

#### Scenario: TUI new-session reset selector is forwarded unchanged through the proxy
- **WHEN** the discovery index contains agent `abc123` with a live TUI gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/prompt` with `chat_session.mode = new`
- **THEN** the passive server forwards that selector unchanged to the live gateway
- **AND THEN** the passive server does not reinterpret the selector as passive-server-local TUI control logic

### Requirement: Passive server provides gateway headless chat-session state and next-prompt override proxy endpoints
The passive server SHALL expose proxy routes for the gateway headless chat-session control surface:

- `GET /houmao/agents/{agent_ref}/gateway/control/headless/state`
- `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session`

Those routes SHALL resolve the agent, create a `GatewayClient`, and proxy the corresponding direct gateway headless control calls.

The response body for each route SHALL be the live gateway headless control-state payload.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Agent-not-found (`404`), ambiguous (`409`), and no-gateway (`502`) error handling SHALL follow the same pattern as the existing passive gateway status and request-submission endpoints.

If the live gateway rejects the request because the addressed target is not headless, the passive server SHALL forward that validation failure explicitly rather than pretending that a headless proxy surface exists.

#### Scenario: Headless control state returns the live gateway payload
- **WHEN** the discovery index contains agent `abc123` with a live headless gateway
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway/control/headless/state`
- **THEN** the response status code is `200`
- **AND THEN** the response body is the live gateway headless control-state payload

#### Scenario: Next-prompt override proxy returns the updated headless control state
- **WHEN** the discovery index contains agent `abc123` with a live headless gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/headless/next-prompt-session` with `mode = new`
- **THEN** the response status code is `200`
- **AND THEN** the response body reports a pending one-shot next-prompt override

#### Scenario: TUI-backed gateway target returns validation failure through the proxy
- **WHEN** the discovery index contains agent `abc123` with a live TUI gateway
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway/control/headless/state` or `POST /houmao/agents/abc123/gateway/control/headless/next-prompt-session`
- **THEN** the passive server forwards the live gateway validation failure explicitly
- **AND THEN** it does not pretend that a headless proxy surface exists for that target

### Requirement: Passive server provides gateway reminder proxy endpoints
The passive server SHALL expose proxy routes for the managed-agent gateway reminder surface:

- `GET /houmao/agents/{agent_ref}/gateway/reminders`
- `POST /houmao/agents/{agent_ref}/gateway/reminders`
- `GET /houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}`
- `PUT /houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}`
- `DELETE /houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}`

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Those routes SHALL resolve the managed agent, create a `GatewayClient`, and proxy the corresponding direct gateway reminder calls.

The response bodies SHALL match the direct gateway reminder models:

- `GatewayReminderListV1` for list,
- `GatewayReminderCreateResultV1` for create,
- `GatewayReminderV1` for get and update,
- `GatewayReminderDeleteResultV1` for delete.

Agent-not-found (404), ambiguous (409), and no-gateway (502) error handling SHALL follow the same pattern as the existing passive gateway proxy endpoints.

#### Scenario: Passive server lists live reminders for a gateway-attached agent
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway/reminders`
- **THEN** the response status code is 200
- **AND THEN** the response body is the live gateway's `GatewayReminderListV1` payload

#### Scenario: Passive server creates one reminder through the managed-agent proxy
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/reminders` with a valid `GatewayReminderCreateBatchV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the live gateway's `GatewayReminderCreateResultV1` payload

#### Scenario: Passive server returns 502 for reminder proxy calls when no gateway is attached
- **WHEN** the discovery index contains agent `abc123` with no live gateway
- **AND WHEN** a caller sends `DELETE /houmao/agents/abc123/gateway/reminders/greminder-123`
- **THEN** the response status code is 502
- **AND THEN** the response explains that the managed agent does not currently have a live gateway attached

### Requirement: Passive server provides gateway mail-notifier proxy endpoints
The passive server SHALL expose proxy routes for the gateway mail-notifier control surface:

- `GET /houmao/agents/{agent_ref}/gateway/mail-notifier/{channel}`
- `PUT /houmao/agents/{agent_ref}/gateway/mail-notifier/{channel}`
- `DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier/{channel}`

Those routes SHALL resolve the agent, create a `GatewayClient`, and proxy the corresponding direct gateway mail-notifier calls.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The response body for each route SHALL be a `GatewayMailNotifierStatusV1` payload from the live gateway.

The passive server SHALL preserve notifier `appendix_text` unchanged in both directions:

- status reads SHALL return the live gateway's effective appendix text,
- `PUT` requests with omitted `appendix_text` SHALL remain omitted when forwarded,
- `PUT` requests with non-empty or empty-string `appendix_text` SHALL forward that exact value unchanged.

Agent-not-found (404), ambiguous (409), and no-gateway (502) error handling SHALL follow the same pattern as the existing passive gateway status and request-submission endpoints.

The channel SHALL be explicit, validated as `offline` or `online`, and forwarded unchanged. The proxy SHALL preserve scoped references and structured binding/scope failures without selecting a canonical-address fallback or keeping a second mailbox state store.

#### Scenario: Mail-notifier status returns the live gateway notifier payload
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway/mail-notifier/{channel}`
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailNotifierStatusV1` payload from the gateway

#### Scenario: Mail-notifier enable forwards through the passive proxy
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `PUT /houmao/agents/abc123/gateway/mail-notifier/{channel}` with a valid `GatewayMailNotifierPutV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the updated `GatewayMailNotifierStatusV1` payload from the gateway

#### Scenario: Mail-notifier disable returns 502 when no gateway is attached
- **WHEN** the discovery index contains agent `abc123` with no live gateway
- **AND WHEN** a caller sends `DELETE /houmao/agents/abc123/gateway/mail-notifier/{channel}`
- **THEN** the response status code is 502

#### Scenario: Mail-notifier status includes live appendix text
- **WHEN** the discovery index contains agent `abc123` with a live gateway whose notifier state stores non-empty `appendix_text`
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway/mail-notifier/{channel}`
- **THEN** the response body includes that exact `appendix_text`
- **AND THEN** the passive server does not rewrite or suppress the field

#### Scenario: Passive proxy forwards non-empty appendix text unchanged
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `PUT /houmao/agents/abc123/gateway/mail-notifier/{channel}` with non-empty `appendix_text`
- **THEN** the passive server forwards that exact string to the live gateway
- **AND THEN** the returned status includes the gateway's effective `appendix_text`

#### Scenario: Passive proxy forwards empty appendix text unchanged
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `PUT /houmao/agents/abc123/gateway/mail-notifier/{channel}` with `appendix_text=""`
- **THEN** the passive server forwards the empty string unchanged
- **AND THEN** it does not reinterpret that request as field omission

### Requirement: Passive server provides gateway TUI tracking proxy endpoints
The passive server SHALL expose managed-agent gateway TUI tracking proxy routes for:

- `GET /houmao/agents/{agent_ref}/gateway/tui/state`
- `GET /houmao/agents/{agent_ref}/gateway/tui/history`
- `POST /houmao/agents/{agent_ref}/gateway/tui/note-prompt`

Those routes SHALL resolve the agent, create a `GatewayClient`, and proxy the corresponding direct gateway TUI tracking calls.

The TUI state response body SHALL match the live gateway's TUI state payload.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The TUI history response body SHALL match the live gateway's bounded recent TUI snapshot-history payload.

The prompt-note response body SHALL match the live gateway's updated TUI state payload after prompt-note recording.

Agent-not-found (404), ambiguous (409), and no-gateway (502) error handling SHALL follow the same pattern as the existing passive gateway proxy endpoints.

#### Scenario: Passive server returns live gateway-owned TUI state
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway/tui/state`
- **THEN** the response status code is 200
- **AND THEN** the response body is the live gateway's TUI state payload

#### Scenario: Passive server returns live gateway-owned bounded TUI snapshot history
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway/tui/history`
- **THEN** the response status code is 200
- **AND THEN** the response body is the live gateway's bounded recent TUI snapshot-history payload

#### Scenario: Passive server forwards gateway prompt-note tracking
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/tui/note-prompt` with valid prompt-note input
- **THEN** the response status code is 200
- **AND THEN** the response body is the updated TUI state payload returned by the live gateway

### Requirement: Passive server provides a mail status proxy endpoint
The passive server SHALL expose `GET /houmao/agents/{agent_ref}/mail/status` that resolves the agent, creates a `GatewayClient`, and forwards the response from `GET /v1/mail/status`.

The response body SHALL be a `GatewayMailStatusV1` payload.

Agent-not-found (404), ambiguous (409), and no-gateway (502) error handling SHALL follow the same pattern.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The forwarded summary SHALL preserve both optional bindings, canonical mail identity, binding revisions, and independent health. A gateway summary with neither channel configured SHALL remain a normal summary.

#### Scenario: Mail status returns the gateway's mailbox status
- **WHEN** the discovery index contains agent `abc123` with a live gateway that has mailbox bindings
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/mail/status`
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailStatusV1` payload

#### Scenario: Mail status returns 502 when no gateway is attached
- **WHEN** the discovery index contains agent `abc123` with no live gateway
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/mail/status`
- **THEN** the response status code is 502

### Requirement: Passive server provides a mail list proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/mail/{channel}/list` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayMailListRequestV1` payload to `POST /v1/mail/{channel}/list`.

The response body SHALL be a `GatewayMailListResponseV1` payload.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The channel SHALL be explicit, validated as `offline` or `online`, and forwarded unchanged. The proxy SHALL preserve scoped references and structured binding/scope failures without selecting a canonical-address fallback or keeping a second mailbox state store.

#### Scenario: Mail list forwards to the gateway and returns messages
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/mail/{channel}/list` with a valid `GatewayMailListRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailListResponseV1` payload from the gateway

### Requirement: Passive server provides a mail send proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/mail/{channel}/send` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayMailSendRequestV1` payload to `POST /v1/mail/{channel}/send`.

The response body SHALL be a `GatewayMailActionResponseV1` payload.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The channel SHALL be explicit, validated as `offline` or `online`, and forwarded unchanged. The proxy SHALL preserve scoped references and structured binding/scope failures without selecting a canonical-address fallback or keeping a second mailbox state store.

#### Scenario: Mail send forwards to the gateway and returns the action response
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/mail/{channel}/send` with a valid `GatewayMailSendRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailActionResponseV1` payload from the gateway

### Requirement: Passive server provides a mail post proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/mail/{channel}/post` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayMailPostRequestV1` payload to `POST /v1/mail/{channel}/post`.

The response body SHALL be a `GatewayMailActionResponseV1` payload.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The channel SHALL be explicit, validated as `offline` or `online`, and forwarded unchanged. The proxy SHALL preserve scoped references and structured binding/scope failures without selecting a canonical-address fallback or keeping a second mailbox state store.

#### Scenario: Mail post forwards to the gateway and returns the action response
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/mail/{channel}/post` with a valid `GatewayMailPostRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailActionResponseV1` payload from the gateway

### Requirement: Passive server provides a mail reply proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/mail/{channel}/reply` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayMailReplyRequestV1` payload to `POST /v1/mail/{channel}/reply`.

The response body SHALL be a `GatewayMailActionResponseV1` payload.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The channel SHALL be explicit, validated as `offline` or `online`, and forwarded unchanged. The proxy SHALL preserve scoped references and structured binding/scope failures without selecting a canonical-address fallback or keeping a second mailbox state store.

#### Scenario: Mail reply forwards to the gateway and returns the action response
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/mail/{channel}/reply` with a valid `GatewayMailReplyRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailActionResponseV1` payload from the gateway

### Requirement: All gateway proxy endpoints use consistent agent resolution and error handling
All gateway proxy endpoints SHALL resolve the `{agent_ref}` path parameter using the same logic as `GET /houmao/agents/{agent_ref}`:
1. Try direct lookup by `agent_id`.
2. Fall back to canonical `agent_name` lookup.
3. Return 404 if not found, 409 if ambiguous.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The proxy SHALL enforce target access before handling gateway availability. If an admitted caller's target has no live gateway (gateway is None or host/port are None), the proxy SHALL return 502 with `detail` describing that the gateway is not attached.

When the `GatewayClient` call returns HTTP 401 or 403, all proxy endpoints SHALL preserve that admission failure with safe detail and challenge information for the caller's ingress on 401. Target policy failure SHALL return safe HTTP 503. Admission failure SHALL end the request. Other connection or HTTP errors SHALL return 502 with safe upstream error detail, except that native-home and native-refresh routes SHALL preserve typed upstream observation, capability, validation, admission, and execution outcomes with their native HTTP status and safe response body. A connection failure without such an upstream result SHALL remain 502 and SHALL NOT authorize a retry or relaunch.

#### Scenario: All proxy endpoints return 409 for ambiguous agent name
- **WHEN** the discovery index contains two agents both named `AGENTSYS-alpha` with different agent_id values
- **AND WHEN** a caller sends any gateway proxy request to `/houmao/agents/alpha/gateway`
- **THEN** the response status code is 409
- **AND THEN** the response body contains the ambiguous agent IDs

#### Scenario: Native Refresh Refusal Is Not a Connectivity Error
- **WHEN** the owning gateway returns a typed busy or restart-required result with HTTP 409 for a proxied native refresh
- **THEN** the proxy preserves HTTP 409 and the typed safe outcome
- **AND** it does not collapse the result into HTTP 502 or retry the operation

#### Scenario: Native Refresh Connection Is Lost
- **WHEN** a gateway refresh request loses its connection before the proxy obtains a typed native outcome
- **THEN** the proxy returns HTTP 502 with safe connection-failure information
- **AND** it does not claim that refresh succeeded, infer that no native effects occurred, or initiate another attempt

#### Scenario: Gateway rejects a missing credential

- **WHEN** a gateway returns HTTP 401 for a proxied operation
- **THEN** the passive server preserves HTTP 401 with safe detail and challenge information applicable to the passive endpoint
- **AND** it does not convert rejection into a connectivity fallback

#### Scenario: Gateway rejects self authority for admin control

- **WHEN** the gateway returns HTTP 403 for a self caller's admin request
- **THEN** the passive server preserves HTTP 403 without replacing the caller's credential or using direct control

### Requirement: Passive server proxies managed memory gateway endpoints
The passive server SHALL expose pair-server routes that proxy live gateway memory endpoints for one resolved managed agent.

The proxy routes SHALL mirror the gateway memory summary, memo read, memo replace, memo append, page tree, page read, page write, page append, page delete, and page path-resolution operations under the managed-agent gateway route family.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The proxy SHALL preserve the gateway's page containment errors, memo-targeting errors, path-resolution errors, and unavailable-gateway errors in structured responses.

The passive server SHALL NOT expose a memory reindex proxy route.

#### Scenario: Pair server proxies memory summary
- **WHEN** an operator requests `/houmao/agents/researcher/gateway/memory`
- **AND WHEN** the passive server resolves `researcher` to a live gateway
- **THEN** the passive server returns the gateway memory summary response

#### Scenario: Pair server proxies page path resolution
- **WHEN** an operator resolves page `notes/run.md` through the pair-server gateway memory proxy
- **AND WHEN** the passive server resolves the agent to a live gateway
- **THEN** the proxy returns the gateway's absolute page path
- **AND THEN** it returns a memo-relative link such as `pages/notes/run.md`

#### Scenario: Pair server does not proxy reindex
- **WHEN** an operator inspects supported pair-server gateway memory routes
- **THEN** there is no route that rebuilds a memo page index

#### Scenario: Pair server proxies memo append
- **WHEN** an operator appends initialization rules through the pair-server gateway memory memo route
- **AND WHEN** the passive server resolves the agent to a live gateway
- **THEN** the passive server forwards the append to the gateway memo endpoint
- **AND THEN** the gateway writes to the fixed `houmao-memo.md` file

### Requirement: Gateway mail-notifier proxy preserves notification mode
Managed-agent gateway mail-notifier proxy routes SHALL preserve the notifier mode field from the shared gateway notifier request and status models.

When a caller enables the notifier through `PUT /houmao/agents/{agent_ref}/gateway/mail-notifier/{channel}`, the proxy SHALL forward the request body to the live gateway without reinterpreting or dropping `mode`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

When a caller reads notifier status through `GET /houmao/agents/{agent_ref}/gateway/mail-notifier/{channel}`, the proxy SHALL return the live gateway's `mode` field as part of the `GatewayMailNotifierStatusV1` payload.

The channel SHALL be explicit, validated as `offline` or `online`, and forwarded unchanged. The proxy SHALL preserve scoped references and structured binding/scope failures without selecting a canonical-address fallback or keeping a second mailbox state store.

#### Scenario: Proxy enable forwards explicit mode
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `PUT /houmao/agents/abc123/gateway/mail-notifier/{channel}` with `mode=unread_only`
- **THEN** the proxy forwards `mode=unread_only` to the live gateway
- **AND THEN** the response body preserves the live gateway's notifier status payload

#### Scenario: Proxy status returns notifier mode
- **WHEN** the discovery index contains agent `abc123` with a live gateway whose notifier status reports `mode=any_inbox`
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway/mail-notifier/{channel}`
- **THEN** the response body reports `mode=any_inbox`
- **AND THEN** the proxy does not synthesize or omit the mode field

### Requirement: Passive-server prompt proxy preserves admission-policy semantics

The maintained passive-server route `POST /houmao/agents/{agent_ref}/gateway/control/prompt` SHALL accept the schema-version-2 gateway prompt request, forward `admission_policy` unchanged to the live gateway, and return the live result or structured refusal without re-evaluating TUI readiness or pending input locally.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The proxy request SHALL NOT accept the removed `force` field, and its success and error projections SHALL expose the selected `admission_policy` instead of a boolean `forced` field.

#### Scenario: Managed-agent proxy forwards if-no-pending unchanged

- **WHEN** a caller sends a valid managed-agent gateway prompt request with `admission_policy=if_no_pending`
- **THEN** the passive server forwards that policy unchanged to the resolved live gateway
- **AND THEN** it returns the live gateway's admission result without applying a second local decision

#### Scenario: Pending refusal remains explicit through the proxy

- **WHEN** the live gateway refuses a proxied `if_no_pending` request because `surface.pending_input=yes`
- **THEN** the passive server returns the structured `pending_input` refusal explicitly
- **AND THEN** it does not convert the refusal into queued acceptance or a generic connectivity error

#### Scenario: Legacy force shape fails at the maintained proxy

- **WHEN** a caller submits the removed `force` field or prompt-control schema version 1 to the managed-agent proxy
- **THEN** strict request validation rejects the payload
- **AND THEN** the passive server does not translate the old shape before forwarding

### Requirement: Maintained usage query selects the authoritative agent source

For `GET /houmao/agents/{agent_ref}/usage`, the passive server SHALL use authoritative server-managed headless history when present and otherwise proxy the resolved live gateway's usage route. The query SHALL NOT create a second accounting history or independently ingest the gateway's provider logs.

#### Scenario: Server-managed authority takes precedence

- **WHEN** an agent has server-managed headless authority and an attached gateway
- **THEN** its usage query reads the authoritative shared ledger rather than a second gateway-derived history

#### Scenario: Gateway-attached agent uses its live projection

- **WHEN** an agent has no server-managed authority and has a live attached gateway
- **THEN** the passive server forwards pagination inputs and returns the gateway's versioned usage page

### Requirement: Usage proxy preserves capabilities and stream cursors

The passive server SHALL preserve gateway-reported source capability, limitations, stream identity, record identities, resumable cursor, and page-continuation state. Qualified TUI records and unavailable-accounting responses SHALL remain normal usage responses.

#### Scenario: Qualified TUI usage passes through

- **WHEN** a gateway returns finalized native-observed TUI records
- **THEN** the maintained route returns those records with unchanged accounting identities and cursor semantics

#### Scenario: Unsupported source remains a capability response

- **WHEN** a gateway reports unavailable accounting because no validated structured source exists
- **THEN** the passive server preserves that response without fabricating records or converting it into a connectivity failure

#### Scenario: Degraded collection preserves prior history

- **WHEN** a gateway returns finalized history with degraded collection capability
- **THEN** the passive server preserves both the history and its limitation reasons

#### Scenario: Empty-page cursor passes through

- **WHEN** a gateway returns a resumable cursor with an empty page and no further current records
- **THEN** the passive server preserves that cursor for later polling

### Requirement: Usage proxy preserves resolution and storage errors

The usage query SHALL preserve existing resolution behavior: 404 for unknown agents, 409 for ambiguous references, and 502 for missing or unreachable gateways. Upstream pagination validation and usage-storage failures SHALL remain explicit.

#### Scenario: Missing gateway returns 502

- **WHEN** a query targets a non-server-managed agent without a live attached gateway
- **THEN** the passive server returns HTTP 502 explaining the required gateway connection

#### Scenario: Ambiguous reference returns 409

- **WHEN** an agent reference matches multiple managed identities
- **THEN** the passive server returns HTTP 409 without choosing arbitrary history

#### Scenario: Wrong-stream cursor remains invalid

- **WHEN** the gateway rejects a cursor from another usage stream
- **THEN** the passive server preserves the HTTP 422 validation failure

#### Scenario: Unreadable ledger remains a storage failure

- **WHEN** the gateway cannot read its usage ledger and returns HTTP 503
- **THEN** the passive server preserves the explicit safe storage failure rather than returning empty history

### Requirement: Channel-selected lifecycle proxies cover the complete shared operation set
The passive server SHALL proxy channel-selected list, peek, read, send, post, reply, mark, move, and archive under `/houmao/agents/{agent_ref}/mail/{channel}/`. Existing agent resolution and missing-gateway handling SHALL remain explicit. Registry-host offline APIs SHALL be separate from these live-gateway projections and SHALL not require a recipient body or gateway.

#### Scenario: Wrong-channel reference remains an error
- **WHEN** a caller forwards an online message reference to an offline lifecycle route
- **THEN** the passive server preserves the gateway's scope rejection
- **AND THEN** it does not retry the operation on the online channel

#### Scenario: Registry inbox is available without a body gateway
- **WHEN** a stopped member has no live gateway
- **THEN** its live-gateway proxy reports the missing gateway
- **AND THEN** authorized registry-host offline mail access remains independently available

### Requirement: Online binding controls proxy the owning gateway authority
Authorized maintained operator surfaces SHALL proxy online binding status, attach/replace, refresh, reconnect, and detach under the selected agent's online mail family. They SHALL preserve expected revisions, replacement intent, protected credential references, and structured outcomes. The proxy SHALL not provision accounts or maintain a second binding store.

#### Scenario: Refresh through the passive server preserves scope
- **WHEN** an authorized operator refreshes an online binding through the maintained proxy
- **THEN** the request targets the resolved owner and expected revision unchanged
- **AND THEN** its response reflects the gateway's committed binding revision

#### Scenario: Binding changed before proxy reaches the gateway
- **WHEN** the gateway refuses a proxied stale-revision update
- **THEN** the proxy preserves that structured conflict
- **AND THEN** it does not retry against the replacement account

### Requirement: Mail proxies preserve page and synchronization information
Channel-selected mail list proxies SHALL forward limit, cursor, filters, and expected binding ID unchanged. Responses SHALL preserve continuation, page-count meaning, completeness, and explicit backend limitations. Cursor validation, stale-state, and content-limit errors SHALL remain distinguishable from gateway connection failure.

#### Scenario: Continued page passes through unchanged
- **WHEN** the gateway returns another bounded metadata page and continuation
- **THEN** the proxy returns those scoped values without fetching additional pages or bodies

#### Scenario: Stale cursor is not a connectivity error
- **WHEN** the gateway rejects an expired or mismatched continuation
- **THEN** the proxy preserves the pagination failure instead of reporting empty mail or generic success

### Requirement: Registry-only service mode exposes no online binding management
Offline member credentials and registry-only route inventories SHALL not expose online account attachment, credential-source selection, or remote agent body control. Online binding management SHALL retain its operator boundary and gateway listener policy.

#### Scenario: Offline member attempts online replacement
- **WHEN** an offline member presents its registry credential to replace an agent's online binding
- **THEN** the registry-only service does not authorize or forward that operation

### Requirement: Passive Server Proxies Native Home and Common State Inspection

The passive server SHALL expose `GET /houmao/agents/{agent_ref}/gateway/native-home` and `GET /houmao/agents/{agent_ref}/gateway/control/refresh`. They SHALL forward typed home or common-plugin observation/capability results, including freshness, inventory coverage, health, boundaries, and evidence. Resolution and missing-gateway errors SHALL remain explicit without starting execution.

#### Scenario: Native Home Comes From the Owning Gateway
- **WHEN** an operator reads `/houmao/agents/agent-123/gateway/native-home` for an active gateway-attached agent
- **THEN** the response preserves the gateway's selected native home and bound agent identity
- **AND** it does not substitute a passive-server-local directory or expose configuration contents

#### Scenario: Common State Preserves Native Limitations
- **WHEN** a caller reads `/houmao/agents/agent-123/gateway/control/refresh`
- **THEN** the response preserves backend/version/profile capabilities, common freshness, scope, health, boundaries, and limitations from the gateway
- **AND** the proxy does not infer freshness from its installed tools or a previous Houmao receipt

#### Scenario: Unknown Freshness Is a Normal Observation
- **WHEN** the owning gateway returns HTTP 200 with pending or unknown common freshness
- **THEN** the proxy preserves that typed observation and HTTP 200
- **AND** it does not initiate reload, convert the state to a connection error, or invent a native-special-plugin inventory

#### Scenario: Agent Has No Live Gateway
- **WHEN** either native-home or common-state proxy read targets an agent without a live attached gateway
- **THEN** the proxy returns HTTP 502 with the missing-gateway diagnostic
- **AND** it does not attach a gateway or invoke manifest-backed launch recovery

### Requirement: Passive Server Proxies Native Refresh Without Owning Activation

The passive server SHALL expose `POST /houmao/agents/{agent_ref}/gateway/control/refresh` with strict shared models. It SHALL preserve common observations, method, outcome, native boundaries, identity, and safe partial-effect diagnostics. It SHALL NOT queue, retry, re-evaluate freshness/readiness, restrict allowed broader native effects, regenerate home material, or invoke relaunch.

#### Scenario: Native Reload Result Passes Through
- **WHEN** a gateway confirms native refresh for a valid proxied request
- **THEN** the proxy returns the typed common/native results with unchanged evidence, scope, and effective boundaries
- **AND** the passive server maintains no second refresh execution or content-generation store

#### Scenario: Already Current Passes Through Without Work
- **WHEN** the gateway returns `method=noop` and `outcome=already_current` after observing a native automatic update
- **THEN** the proxy preserves the result without initiating its own activation or requiring a Houmao update receipt

#### Scenario: Automatic Discovery Result Passes Through
- **WHEN** the gateway reports automatic discovery effective on the next step, turn, or load
- **THEN** the proxy preserves that future-boundary result
- **AND** it does not submit a prompt to make the future boundary happen

#### Scenario: Partial Common Restart Requirement Passes Through
- **WHEN** the gateway reports applied common changes and a remaining common resource requiring restart
- **THEN** the proxy preserves `restart_required`, the applied observations, and partial effects without calling relaunch
- **AND** the selected process and conversation remain under their existing authority

#### Scenario: Native Extension Remains Pending
- **WHEN** the gateway confirms current common-plugin state and readiness while a native extension remains pending
- **THEN** the proxy preserves that common result and any safe native diagnostic
- **AND** it does not promote an unrelated native pending reason into common restart-required

#### Scenario: Force or Replacement Content Is Supplied
- **WHEN** a caller submits restart, force, installation, home-override, or replacement-configuration fields to the refresh proxy
- **THEN** strict validation rejects the request before native effects
- **AND** the proxy does not translate it into another lifecycle operation

### Requirement: Native Home Proxy Controls Retain Managed Owner Boundaries

Native-home and refresh proxy routes SHALL use existing local managed-agent and control-exposure boundaries. They SHALL NOT turn an external communication-only reference or registry-only mailbox credential into body-control authority. Safe diagnostics SHALL exclude credentials and raw native configuration, and resource paths SHALL remain bound to the selected execution.

#### Scenario: Name Is Ambiguous
- **WHEN** a home or refresh proxy request names multiple managed agents
- **THEN** resolution returns HTTP 409 without selecting or mutating any agent

#### Scenario: Reference Is Communication Only
- **WHEN** a caller targets an external communication-only record through native-home or refresh control
- **THEN** the operation fails explicitly without adopting or controlling the external runtime

#### Scenario: Gateway Reports Private Native Failure
- **WHEN** a gateway returns a safe failed or uncertain refresh result after a native error
- **THEN** the proxy preserves the safe outcome and effect evidence
- **AND** it does not add raw provider exceptions, home-file contents, or credential-bearing diagnostics

### Requirement: Protected target proxy calls retain caller authority

A passive proxy SHALL enforce the selected target's route class and current key state. An admitted anonymous private or admin call SHALL be forwarded unsigned to the selected gateway for current admission. Discovery and source addresses SHALL serve as connection information.

#### Scenario: Unauthenticated caller requests privileged proxy control

- **WHEN** an unauthenticated caller invokes a target's prompt, raw-key, refresh, or mailbox-binding proxy while its admin list has entries
- **THEN** the request is rejected before any downstream operation
- **AND** owner-client credentials stay unused

#### Scenario: First enrollment races an anonymous admin proxy call

- **WHEN** a proxy admits an open private or admin call and a key is registered before the receiving gateway admits the downstream request
- **THEN** the downstream operation is refused under the key-required rule

#### Scenario: A private proxy call is anonymous in open mode

- **WHEN** an unsigned caller selects a private proxy operation on a target with a valid empty roster
- **THEN** both ingress and the receiving gateway apply the current open policy
- **AND THEN** the resulting operation preserves anonymous caller provenance

### Requirement: Signed proxy requests carry only admitted caller authority

The passive ingress SHALL consume signed self or admin proof at admission. It SHALL relay the verified principal, role, and current key through explicit owner-local authority using a short-lived, single-use record for the exact downstream request. The gateway SHALL verify that record, current grant, and target before effects.

#### Scenario: Request path or body changes across the proxy

- **WHEN** the passive ingress authorizes a signed request whose downstream path or body differs
- **THEN** the gateway uses a verified record for the exact transformed operation and preserves the caller's identity and role

#### Scenario: Admitted self caller is forwarded

- **WHEN** a proxy admits a self signature for a private operation
- **THEN** the downstream record retains its self role and current generation binding
- **AND** the original signature stays bound to the passive ingress

#### Scenario: The generation changes during a signed self relay

- **WHEN** the managed generation changes before the gateway admits the downstream private request
- **THEN** the receiving gateway refuses the relay before effects

#### Scenario: Relayed authority is replayed or the key has been removed

- **WHEN** a downstream request reuses a relay record or its admitted grant ceased to be current before gateway admission
- **THEN** the gateway refuses the request without using open access or a substitute credential

### Requirement: The passive server issues scoped proof challenges

The passive server SHALL expose public `POST /houmao/agents/{agent_ref}/auth/challenge` for self and admin proof on selected-agent routes. It SHALL bind the challenge to the resolved owner target and intended passive request. The challenge SHALL convey no authority until the passive ingress verifies the signature.

#### Scenario: Admin requests a challenge while the gateway is detached

- **WHEN** a detached agent's retained owner state identifies a key-required target for a supported direct operation
- **THEN** the passive ingress can issue and verify a challenge scoped to that operation

### Requirement: Direct passive paths cannot bypass protected agent access

Direct selected-agent operations SHALL enforce retained owner policy before effects. Routine protected reads SHALL use private access. A valid empty roster permits anonymous admission to private and admin operations. Direct turns, native observation and artifacts, interruption, stop, and gateway lifecycle SHALL use admin admission. The passive ingress SHALL issue and verify challenges for its own signed operations independently of live discovery.

#### Scenario: Direct stop would otherwise kill tmux

- **WHEN** an unauthenticated caller invokes direct stop for a discovered agent with a nonempty admin list
- **THEN** it is rejected before tmux termination or registry cleanup

#### Scenario: Direct headless match has no discovery record

- **WHEN** a protected managed-headless target is found through its retained control state without a live discovery record
- **THEN** prompt, interrupt, stop, private state, and artifact requests require their declared target access

#### Scenario: Gateway detachment removes its live record

- **WHEN** a protected target has no live gateway record after detachment
- **THEN** direct private and admin operations still use the recorded open or key-required state

#### Scenario: Enrollment races a direct anonymous operation

- **WHEN** a direct operation's anonymous grant has ceased to be current before its effect boundary
- **THEN** the operation is refused before accessing or changing the target

### Requirement: Necessary owner backing calls are explicitly authenticated

Server-managed backing calls SHALL authenticate with a separate owner-service binding scoped to the required target and backing operations. This service binding SHALL be independent of admin enrollment. The backing authority SHALL check proof and target on loopback and preserve the existing generation and operation guards.

#### Scenario: Gateway inspects or dispatches through its managed backing authority

- **WHEN** a protected server-managed gateway needs a maintained backing operation
- **THEN** it presents its selected owner-service credential for that target and operation
- **AND** the backing authority evaluates it before execution

#### Scenario: First enrollment occurs on a server-managed gateway

- **WHEN** a running server-managed gateway acquires its first admin key
- **THEN** its existing scoped service binding continues authorizing its required backing operations

#### Scenario: Caller impersonates a backing gateway

- **WHEN** an unauthenticated caller sets gateway-looking headers or uses the backing loopback endpoint
- **THEN** the request is refused before runtime access
