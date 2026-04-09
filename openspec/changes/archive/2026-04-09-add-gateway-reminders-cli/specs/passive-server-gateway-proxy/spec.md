## ADDED Requirements

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
