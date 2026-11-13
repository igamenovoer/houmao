# Spec Delta

## MODIFIED Requirements

### Requirement: Passive server provides a mail status proxy endpoint
The passive server SHALL expose `GET /houmao/agents/{agent_ref}/mail/status` that resolves the agent, creates a `GatewayClient`, and forwards the response from `GET /v1/mail/status`.

The response body SHALL be a `GatewayMailStatusV1` payload.

Agent-not-found (404), ambiguous (409), and no-gateway (502) error handling SHALL follow the same pattern.

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

The channel SHALL be explicit, validated as `offline` or `online`, and forwarded unchanged. The proxy SHALL preserve scoped references and structured binding/scope failures without selecting a canonical-address fallback or keeping a second mailbox state store.

#### Scenario: Mail list forwards to the gateway and returns messages
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/mail/{channel}/list` with a valid `GatewayMailListRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailListResponseV1` payload from the gateway

### Requirement: Passive server provides a mail send proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/mail/{channel}/send` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayMailSendRequestV1` payload to `POST /v1/mail/{channel}/send`.

The response body SHALL be a `GatewayMailActionResponseV1` payload.

The channel SHALL be explicit, validated as `offline` or `online`, and forwarded unchanged. The proxy SHALL preserve scoped references and structured binding/scope failures without selecting a canonical-address fallback or keeping a second mailbox state store.

#### Scenario: Mail send forwards to the gateway and returns the action response
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/mail/{channel}/send` with a valid `GatewayMailSendRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailActionResponseV1` payload from the gateway

### Requirement: Passive server provides a mail post proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/mail/{channel}/post` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayMailPostRequestV1` payload to `POST /v1/mail/{channel}/post`.

The response body SHALL be a `GatewayMailActionResponseV1` payload.

The channel SHALL be explicit, validated as `offline` or `online`, and forwarded unchanged. The proxy SHALL preserve scoped references and structured binding/scope failures without selecting a canonical-address fallback or keeping a second mailbox state store.

#### Scenario: Mail post forwards to the gateway and returns the action response
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/mail/{channel}/post` with a valid `GatewayMailPostRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailActionResponseV1` payload from the gateway

### Requirement: Passive server provides a mail reply proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/mail/{channel}/reply` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayMailReplyRequestV1` payload to `POST /v1/mail/{channel}/reply`.

The response body SHALL be a `GatewayMailActionResponseV1` payload.

The channel SHALL be explicit, validated as `offline` or `online`, and forwarded unchanged. The proxy SHALL preserve scoped references and structured binding/scope failures without selecting a canonical-address fallback or keeping a second mailbox state store.

#### Scenario: Mail reply forwards to the gateway and returns the action response
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/mail/{channel}/reply` with a valid `GatewayMailReplyRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailActionResponseV1` payload from the gateway

### Requirement: Passive server provides gateway mail-notifier proxy endpoints
The passive server SHALL expose proxy routes for the gateway mail-notifier control surface:

- `GET /houmao/agents/{agent_ref}/gateway/mail-notifier/{channel}`
- `PUT /houmao/agents/{agent_ref}/gateway/mail-notifier/{channel}`
- `DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier/{channel}`

Those routes SHALL resolve the agent, create a `GatewayClient`, and proxy the corresponding direct gateway mail-notifier calls.

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

### Requirement: Gateway mail-notifier proxy preserves notification mode
Managed-agent gateway mail-notifier proxy routes SHALL preserve the notifier mode field from the shared gateway notifier request and status models.

When a caller enables the notifier through `PUT /houmao/agents/{agent_ref}/gateway/mail-notifier/{channel}`, the proxy SHALL forward the request body to the live gateway without reinterpreting or dropping `mode`.

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

## ADDED Requirements

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
