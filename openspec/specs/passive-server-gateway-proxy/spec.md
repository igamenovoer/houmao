# passive-server-gateway-proxy Specification

## Purpose
TBD - created by archiving change passive-server-gateway-proxy. Update Purpose after archive.
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

- `GET /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `PUT /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier`

Those routes SHALL resolve the agent, create a `GatewayClient`, and proxy the corresponding direct gateway mail-notifier calls.

The response body for each route SHALL be a `GatewayMailNotifierStatusV1` payload from the live gateway.

Agent-not-found (404), ambiguous (409), and no-gateway (502) error handling SHALL follow the same pattern as the existing passive gateway status and request-submission endpoints.

#### Scenario: Mail-notifier status returns the live gateway notifier payload
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway/mail-notifier`
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailNotifierStatusV1` payload from the gateway

#### Scenario: Mail-notifier enable forwards through the passive proxy
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `PUT /houmao/agents/abc123/gateway/mail-notifier` with a valid `GatewayMailNotifierPutV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the updated `GatewayMailNotifierStatusV1` payload from the gateway

#### Scenario: Mail-notifier disable returns 502 when no gateway is attached
- **WHEN** the discovery index contains agent `abc123` with no live gateway
- **AND WHEN** a caller sends `DELETE /houmao/agents/abc123/gateway/mail-notifier`
- **THEN** the response status code is 502

### Requirement: Passive server provides gateway TUI tracking proxy endpoints
The passive server SHALL expose managed-agent gateway TUI tracking proxy routes for:

- `GET /houmao/agents/{agent_ref}/gateway/tui/state`
- `GET /houmao/agents/{agent_ref}/gateway/tui/history`
- `POST /houmao/agents/{agent_ref}/gateway/tui/note-prompt`

Those routes SHALL resolve the agent, create a `GatewayClient`, and proxy the corresponding direct gateway TUI tracking calls.

The TUI state response body SHALL match the live gateway's TUI state payload.

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

#### Scenario: Mail status returns the gateway's mailbox status
- **WHEN** the discovery index contains agent `abc123` with a live gateway that has mailbox bindings
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/mail/status`
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailStatusV1` payload

#### Scenario: Mail status returns 502 when no gateway is attached
- **WHEN** the discovery index contains agent `abc123` with no live gateway
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/mail/status`
- **THEN** the response status code is 502

### Requirement: Passive server provides a mail check proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/mail/check` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayMailCheckRequestV1` payload to `POST /v1/mail/check`.

The response body SHALL be a `GatewayMailCheckResponseV1` payload.

#### Scenario: Mail check forwards to the gateway and returns messages
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/mail/check` with a valid `GatewayMailCheckRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailCheckResponseV1` payload from the gateway

### Requirement: Passive server provides a mail send proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/mail/send` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayMailSendRequestV1` payload to `POST /v1/mail/send`.

The response body SHALL be a `GatewayMailActionResponseV1` payload.

#### Scenario: Mail send forwards to the gateway and returns the action response
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/mail/send` with a valid `GatewayMailSendRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailActionResponseV1` payload from the gateway

### Requirement: Passive server provides a mail post proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/mail/post` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayMailPostRequestV1` payload to `POST /v1/mail/post`.

The response body SHALL be a `GatewayMailActionResponseV1` payload.

#### Scenario: Mail post forwards to the gateway and returns the action response
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/mail/post` with a valid `GatewayMailPostRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailActionResponseV1` payload from the gateway

### Requirement: Passive server provides a mail reply proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/mail/reply` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayMailReplyRequestV1` payload to `POST /v1/mail/reply`.

The response body SHALL be a `GatewayMailActionResponseV1` payload.

#### Scenario: Mail reply forwards to the gateway and returns the action response
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/mail/reply` with a valid `GatewayMailReplyRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailActionResponseV1` payload from the gateway

### Requirement: All gateway proxy endpoints use consistent agent resolution and error handling
All gateway proxy endpoints SHALL resolve the `{agent_ref}` path parameter using the same logic as `GET /houmao/agents/{agent_ref}`:
1. Try direct lookup by `agent_id`.
2. Fall back to canonical `agent_name` lookup.
3. Return 404 if not found, 409 if ambiguous.

When the resolved agent has no live gateway (gateway is None or host/port are None), all proxy endpoints SHALL return 502 with `detail` describing that the gateway is not attached.

When the `GatewayClient` call fails with a connection or HTTP error, all proxy endpoints SHALL return 502 with the upstream error detail forwarded.

#### Scenario: All proxy endpoints return 409 for ambiguous agent name
- **WHEN** the discovery index contains two agents both named `AGENTSYS-alpha` with different agent_id values
- **AND WHEN** a caller sends any gateway proxy request to `/houmao/agents/alpha/gateway`
- **THEN** the response status code is 409
- **AND THEN** the response body contains the ambiguous agent IDs

### Requirement: Passive server proxies managed memory gateway endpoints
The passive server SHALL expose pair-server routes that proxy live gateway memory endpoints for one resolved managed agent.

The proxy routes SHALL mirror the gateway memory summary, memo read, memo replace, memo append, page tree, page read, page write, page append, page delete, and page path-resolution operations under the managed-agent gateway route family.

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

When a caller enables the notifier through `PUT /houmao/agents/{agent_ref}/gateway/mail-notifier`, the proxy SHALL forward the request body to the live gateway without reinterpreting or dropping `mode`.

When a caller reads notifier status through `GET /houmao/agents/{agent_ref}/gateway/mail-notifier`, the proxy SHALL return the live gateway's `mode` field as part of the `GatewayMailNotifierStatusV1` payload.

#### Scenario: Proxy enable forwards explicit mode
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `PUT /houmao/agents/abc123/gateway/mail-notifier` with `mode=unread_only`
- **THEN** the proxy forwards `mode=unread_only` to the live gateway
- **AND THEN** the response body preserves the live gateway's notifier status payload

#### Scenario: Proxy status returns notifier mode
- **WHEN** the discovery index contains agent `abc123` with a live gateway whose notifier status reports `mode=any_inbox`
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway/mail-notifier`
- **THEN** the response body reports `mode=any_inbox`
- **AND THEN** the proxy does not synthesize or omit the mode field
