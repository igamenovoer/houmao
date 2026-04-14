## ADDED Requirements

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
