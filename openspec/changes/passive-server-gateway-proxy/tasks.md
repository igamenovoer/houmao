## 1. Service-Level Gateway Proxy Logic

- [x] 1.1 Add a `_resolve_agent_or_error(agent_ref)` helper to `PassiveServerService` that returns the `DiscoveredAgent` or a tuple of `(status_code, response_body)` for 404/409 cases, to share resolution logic across gateway and existing endpoints
- [x] 1.2 Add a `_gateway_client_for_agent(agent)` helper that reads `gateway.host` and `gateway.port` from the agent's registry record and returns a `GatewayClient`, or `None` if the gateway is not attached
- [x] 1.3 Add `gateway_status(agent_ref)` method that resolves the agent, builds a `GatewayClient`, calls `client.status()`, and returns the result or an error response
- [x] 1.4 Add `gateway_create_request(agent_ref, payload)` method that forwards a `GatewayRequestCreateV1` to the gateway
- [x] 1.5 Add `gateway_mail_status(agent_ref)` method that forwards to `client.mail_status()`
- [x] 1.6 Add `gateway_mail_check(agent_ref, payload)` method that forwards a `GatewayMailCheckRequestV1` to the gateway
- [x] 1.7 Add `gateway_mail_send(agent_ref, payload)` method that forwards a `GatewayMailSendRequestV1` to the gateway
- [x] 1.8 Add `gateway_mail_reply(agent_ref, payload)` method that forwards a `GatewayMailReplyRequestV1` to the gateway

## 2. HTTP Routes

- [x] 2.1 Add `GET /houmao/agents/{agent_ref}/gateway` route returning `GatewayStatusV1` (200), 404, 409, or 502
- [x] 2.2 Add `POST /houmao/agents/{agent_ref}/gateway/requests` route accepting `GatewayRequestCreateV1` and returning `GatewayAcceptedRequestV1` (200), 404, 409, or 502
- [x] 2.3 Add `GET /houmao/agents/{agent_ref}/mail/status` route returning `GatewayMailStatusV1` (200), 404, 409, or 502
- [x] 2.4 Add `POST /houmao/agents/{agent_ref}/mail/check` route accepting `GatewayMailCheckRequestV1` and returning `GatewayMailCheckResponseV1`
- [x] 2.5 Add `POST /houmao/agents/{agent_ref}/mail/send` route accepting `GatewayMailSendRequestV1` and returning `GatewayMailActionResponseV1`
- [x] 2.6 Add `POST /houmao/agents/{agent_ref}/mail/reply` route accepting `GatewayMailReplyRequestV1` and returning `GatewayMailActionResponseV1`

## 3. Tests

- [x] 3.1 Add unit tests for `_gateway_client_for_agent` (live gateway returns client, no gateway returns None)
- [x] 3.2 Add unit tests for `gateway_status` (success, agent not found, no gateway, gateway error)
- [x] 3.3 Add HTTP contract tests for all six proxy endpoints: 200 success with mocked GatewayClient, 404 not found, 409 ambiguous, 502 no gateway
