## MODIFIED Requirements

### Requirement: Passive server provides gateway mail-notifier proxy endpoints
The passive server SHALL expose proxy routes for the gateway mail-notifier control surface:

- `GET /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `PUT /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier`

Those routes SHALL resolve the agent, create a `GatewayClient`, and proxy the corresponding direct gateway mail-notifier calls.

The response body for each route SHALL be a `GatewayMailNotifierStatusV1` payload from the live gateway.

The passive server SHALL preserve notifier `appendix_text` unchanged in both directions:

- status reads SHALL return the live gateway's effective appendix text,
- `PUT` requests with omitted `appendix_text` SHALL remain omitted when forwarded,
- `PUT` requests with non-empty or empty-string `appendix_text` SHALL forward that exact value unchanged.

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

#### Scenario: Mail-notifier status includes live appendix text
- **WHEN** the discovery index contains agent `abc123` with a live gateway whose notifier state stores non-empty `appendix_text`
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway/mail-notifier`
- **THEN** the response body includes that exact `appendix_text`
- **AND THEN** the passive server does not rewrite or suppress the field

#### Scenario: Passive proxy forwards non-empty appendix text unchanged
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `PUT /houmao/agents/abc123/gateway/mail-notifier` with non-empty `appendix_text`
- **THEN** the passive server forwards that exact string to the live gateway
- **AND THEN** the returned status includes the gateway's effective `appendix_text`

#### Scenario: Passive proxy forwards empty appendix text unchanged
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `PUT /houmao/agents/abc123/gateway/mail-notifier` with `appendix_text=""`
- **THEN** the passive server forwards the empty string unchanged
- **AND THEN** it does not reinterpret that request as field omission
