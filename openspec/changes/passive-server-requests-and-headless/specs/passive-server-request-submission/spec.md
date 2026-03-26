## ADDED Requirements

### Requirement: Passive server accepts gateway-mediated prompt requests
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/requests` that accepts a prompt request envelope and forwards it to the agent's live gateway.

If the resolved agent has no attached gateway, the endpoint SHALL return HTTP 502 with a detail message explaining that the agent requires a gateway for remote prompt delivery.

The request body SHALL accept a JSON object with a `prompt` field (non-empty string).

#### Scenario: Prompt forwarded through gateway
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/requests` with `{"prompt": "hello"}` and the agent has an attached gateway
- **THEN** the response status code is 200
- **AND THEN** the response body contains `request_id` and `status` fields indicating acceptance

#### Scenario: No gateway returns 502
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/requests` with `{"prompt": "hello"}` and the agent has no attached gateway
- **THEN** the response status code is 502
- **AND THEN** the response body contains a detail message mentioning gateway requirement

#### Scenario: Agent not found returns 404
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/requests` for a nonexistent agent
- **THEN** the response status code is 404

### Requirement: Passive server accepts interrupt requests
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/interrupt`.

For agents with an attached gateway, the endpoint SHALL forward the interrupt via the gateway client.

For headless agents managed by this passive server instance, the endpoint SHALL signal the interrupt through the in-memory `RuntimeSessionController` handle.

If the agent has no gateway and is not managed by this server, the endpoint SHALL return HTTP 502.

#### Scenario: Interrupt forwarded through gateway
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/interrupt` and the agent has an attached gateway
- **THEN** the response status code is 200
- **AND THEN** the response body indicates the interrupt was accepted

#### Scenario: Interrupt for server-managed headless agent
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/interrupt` for a headless agent managed by this server
- **THEN** the response status code is 200
- **AND THEN** the active turn is interrupted

#### Scenario: No gateway and not managed returns 502
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/interrupt` for an agent with no gateway that is not managed by this server
- **THEN** the response status code is 502

### Requirement: Passive server can stop agents by killing tmux sessions
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/stop`.

The endpoint SHALL terminate the agent's tmux session via `kill_tmux_session()` and clear the agent's shared registry record.

For headless agents managed by this server, the endpoint SHALL also clean up the `ManagedHeadlessStore` authority record and remove the in-memory handle.

#### Scenario: Stop kills tmux session and clears registry
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/stop` for a discovered agent
- **THEN** the response status code is 200
- **AND THEN** the agent's tmux session is terminated
- **AND THEN** the agent's shared registry record is removed

#### Scenario: Stop cleans up managed headless state
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/stop` for a headless agent managed by this server
- **THEN** the `ManagedHeadlessStore` authority record is deleted
- **AND THEN** the in-memory handle is removed

#### Scenario: Agent not found returns 404
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/stop` for a nonexistent agent
- **THEN** the response status code is 404

### Requirement: Gateway attach and detach return 501 directing to houmao-mgr
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/gateway/attach` and `POST /houmao/agents/{agent_ref}/gateway/detach`.

Both endpoints SHALL return HTTP 501 Not Implemented with a detail message directing the caller to use `houmao-mgr agents gateway attach <agent-ref>` or `houmao-mgr agents gateway detach <agent-ref>` respectively.

#### Scenario: Gateway attach returns 501
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/gateway/attach`
- **THEN** the response status code is 501
- **AND THEN** the response body contains a detail message mentioning `houmao-mgr`

#### Scenario: Gateway detach returns 501
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/gateway/detach`
- **THEN** the response status code is 501
- **AND THEN** the response body contains a detail message mentioning `houmao-mgr`
