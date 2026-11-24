# passive-server-request-submission Specification

## Purpose
Define how clients address agents through the passive server to submit prompts, interrupt work, or stop sessions. Cover gateway forwarding, stable references for server-managed headless agents, and the access rules that guard state changes.

## Requirements

### Requirement: Passive server accepts gateway-mediated prompt requests

The passive server SHALL expose `POST /houmao/agents/{agent_ref}/requests` for forwarding prompts to the agent's live gateway. The request body SHALL accept a JSON object with a non-empty `prompt` string.

For a configured agent, the server SHALL apply the target's live admin access rule before forwarding or handling gateway availability. If an admitted caller's target has no attached gateway, the endpoint SHALL return HTTP 502 with a detail explaining that prompt delivery requires a gateway.

#### Scenario: Prompt forwarded through gateway

- **WHEN** an admitted caller sends `POST /houmao/agents/{agent_ref}/requests` with a valid prompt and the agent has an attached gateway
- **THEN** the response status code is 200
- **AND THEN** the response body indicates acceptance with a request ID and status

#### Scenario: No gateway returns 502

- **WHEN** an admitted caller sends a prompt request for an agent with no attached gateway
- **THEN** the response status code is 502
- **AND THEN** the response explains that delivery requires a gateway

#### Scenario: Agent not found returns 404

- **WHEN** a caller sends a prompt request for a nonexistent agent
- **THEN** the response status code is 404

#### Scenario: Self cannot use the passive prompt route for admin control

- **WHEN** a caller presents only self proof to this route for a target with a nonempty admin list
- **THEN** the response is HTTP 403 before forwarding a request

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

The passive server SHALL expose `POST /houmao/agents/{agent_ref}/interrupt`. A configured target SHALL apply its current admin access rule before interruption or handling gateway availability.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

For server-managed headless agents, the endpoint SHALL resolve the authoritative headless match first and signal interruption through the managed `RuntimeSessionController` after admission. For a target that the server does not manage directly, it SHALL forward the admitted interrupt to its live gateway. When an admitted target has neither a managed headless path nor a live gateway, the endpoint SHALL return HTTP 502.

#### Scenario: Interrupt forwarded through gateway

- **WHEN** an admitted caller sends an interrupt for a discovered agent that has an attached gateway
- **THEN** the response status code is 200
- **AND THEN** the response indicates interrupt acceptance

#### Scenario: Interrupt for server-managed headless agent

- **WHEN** an admitted caller sends an interrupt to a headless agent managed by this server
- **THEN** the response status code is 200
- **AND THEN** the active turn is interrupted

#### Scenario: Managed interrupt does not fall back to gateway-only handling

- **WHEN** an admitted caller sends an interrupt for a passive-server-launched headless agent
- **THEN** the passive server signals the managed headless controller directly

#### Scenario: No gateway and not managed returns 502

- **WHEN** an admitted caller sends an interrupt for a target with neither a managed headless path nor a gateway
- **THEN** the response status code is 502

### Requirement: Passive server can stop agents by killing tmux sessions

The passive server SHALL expose `POST /houmao/agents/{agent_ref}/stop`. A configured target SHALL apply its current admin access rule before effects.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

For agents launched by this passive server, the endpoint SHALL resolve managed-headless authority first. After admission it SHALL stop the managed session, clear the shared registry record, clean up the active `ManagedHeadlessStore` record, and remove the in-memory handle. For a discovered-only agent, it SHALL terminate its tmux session and clear its registry record after admission. Retained owner access settings SHALL survive live-record cleanup.

#### Scenario: Stop kills tmux session and clears registry

- **WHEN** an admitted caller sends a stop request for a discovered agent
- **THEN** the response status code is 200
- **AND THEN** the server terminates the target's tmux session and clears its shared registry record

#### Scenario: Stop cleans up managed headless state

- **WHEN** an admitted caller sends a stop request for a managed headless agent
- **THEN** the authoritative managed session stops
- **AND THEN** the active managed record and in-memory handle are removed

#### Scenario: Managed stop prefers server-owned control

- **WHEN** an admitted caller sends a stop request for a passive-server-launched headless agent
- **THEN** the passive server uses the server-owned managed-headless control path and cleans up its live state

#### Scenario: Agent not found returns 404

- **WHEN** a caller sends a stop request for a nonexistent agent
- **THEN** the response status code is 404

### Requirement: Gateway attach and detach return 501 directing to houmao-mgr

The passive server SHALL expose `POST /houmao/agents/{agent_ref}/gateway/attach` and `POST /houmao/agents/{agent_ref}/gateway/detach`. It SHALL apply retained admin admission for configured targets first. After admission it SHALL return HTTP 501 with a detail directing the caller to the scoped `houmao-mgr agents single ... gateway attach` or `gateway detach` command.

#### Scenario: Gateway attach returns 501

- **WHEN** an admitted caller sends a gateway attach request
- **THEN** the response status code is 501
- **AND THEN** the response detail points to `houmao-mgr`

#### Scenario: Gateway detach returns 501

- **WHEN** an admitted caller sends a gateway detach request
- **THEN** the response status code is 501
- **AND THEN** the response detail points to `houmao-mgr`

#### Scenario: A detached gateway still has retained protection

- **WHEN** a caller requests gateway lifecycle without signed proof after detach and the retained admin list has entries
- **THEN** the server returns the target admission failure before lifecycle handling
