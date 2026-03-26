# passive-server-request-submission Specification

## Purpose
TBD - synced from change passive-server-requests-and-headless. Update Purpose after archive.

## Requirements

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

### Requirement: Passive server resolves server-managed headless agents through stable managed references
When the passive server launches a headless agent, later managed follow-up routes SHALL be able to resolve that agent through the server-owned managed authority rather than treating it as an unrelated discovered agent.

The passive server SHALL accept the managed `tracked_agent_id` and the published shared-registry `agent_id` as valid references for server-managed headless follow-up operations, including turn submission, interrupt, and stop.

#### Scenario: Custom published agent id still resolves to managed headless turn submission
- **WHEN** a caller launches a passive-server headless agent with an explicit `agent_id` different from `tracked_agent_id`
- **THEN** a later `POST /houmao/agents/{agent_ref}/turns` using that published `agent_id` succeeds through the server-managed headless path

#### Scenario: Managed tracked id still resolves after launch
- **WHEN** a caller uses the returned `tracked_agent_id` from `POST /houmao/agents/headless/launches`
- **THEN** later `POST /houmao/agents/{agent_ref}/interrupt` and `POST /houmao/agents/{agent_ref}/stop` calls resolve the same server-managed headless authority

### Requirement: Passive server accepts interrupt requests
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/interrupt`.

For agents launched by this passive server instance, the endpoint SHALL resolve the authoritative managed-headless authority first and signal the interrupt through the managed `RuntimeSessionController` before falling back to generic discovered-agent behavior.

For agents that are not server-managed headless agents but do have an attached gateway, the endpoint SHALL forward the interrupt via the gateway client.

If the agent has no gateway and is not managed by this server, the endpoint SHALL return HTTP 502.

#### Scenario: Interrupt forwarded through gateway
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/interrupt` and the agent has an attached gateway
- **THEN** the response status code is 200
- **AND THEN** the response body indicates the interrupt was accepted

#### Scenario: Interrupt for server-managed headless agent
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/interrupt` for a headless agent managed by this server
- **THEN** the response status code is 200
- **AND THEN** the active turn is interrupted

#### Scenario: Managed interrupt does not fall back to gateway-only handling
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/interrupt` for a passive-server-launched headless agent
- **THEN** the passive server signals the managed headless runtime controller directly
- **AND THEN** the request does not fail with the generic "not managed" or "no gateway" behavior

#### Scenario: No gateway and not managed returns 502
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/interrupt` for an agent with no gateway that is not managed by this server
- **THEN** the response status code is 502

### Requirement: Passive server can stop agents by killing tmux sessions
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/stop`.

For agents launched by this passive server instance, the endpoint SHALL resolve the authoritative managed-headless authority first, stop the managed session, clear the agent's shared registry record, clean up the `ManagedHeadlessStore` authority record, and remove the in-memory handle before falling back to generic discovered-agent behavior.

For discovered agents that are not managed by this server, the endpoint SHALL terminate the agent's tmux session via `kill_tmux_session()` and clear the agent's shared registry record.

#### Scenario: Stop kills tmux session and clears registry
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/stop` for a discovered agent
- **THEN** the response status code is 200
- **AND THEN** the agent's tmux session is terminated
- **AND THEN** the agent's shared registry record is removed

#### Scenario: Stop cleans up managed headless state
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/stop` for a headless agent managed by this server
- **THEN** the authoritative managed headless session is stopped
- **AND THEN** the `ManagedHeadlessStore` authority record is deleted
- **AND THEN** the in-memory handle is removed

#### Scenario: Managed stop prefers server-owned control
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/stop` for a passive-server-launched headless agent
- **THEN** the passive server uses the authoritative managed headless control path before any generic gateway or tmux-only fallback
- **AND THEN** the server-owned managed state is cleaned up

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
