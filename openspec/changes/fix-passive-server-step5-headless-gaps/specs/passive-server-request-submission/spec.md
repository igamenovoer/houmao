## ADDED Requirements

### Requirement: Passive server resolves server-managed headless agents through stable managed references
When the passive server launches a headless agent, later managed routes SHALL be able to resolve that agent through the server-owned managed authority rather than treating it as an unrelated discovered agent.

The passive server SHALL accept the managed `tracked_agent_id` and the published shared-registry `agent_id` as valid references for server-managed headless follow-up operations.

#### Scenario: Custom published agent id still resolves to managed headless turn submission
- **WHEN** a caller launches a passive-server headless agent with an explicit `agent_id` different from `tracked_agent_id`
- **THEN** a later `POST /houmao/agents/{agent_ref}/turns` using that published `agent_id` succeeds through the server-managed headless path

#### Scenario: Managed tracked id still resolves after launch
- **WHEN** a caller uses the returned `tracked_agent_id` from `POST /houmao/agents/headless/launches`
- **THEN** later `POST /houmao/agents/{agent_ref}/interrupt` and `POST /houmao/agents/{agent_ref}/stop` calls resolve the same server-managed headless authority

### Requirement: Interrupt and stop prefer authoritative managed-headless control for server-owned agents
For an agent launched by the passive server, `POST /houmao/agents/{agent_ref}/interrupt` and `POST /houmao/agents/{agent_ref}/stop` SHALL use the server-managed headless control path before falling back to generic discovered-agent gateway or tmux-only behavior.

#### Scenario: Managed interrupt does not fall back to gateway-only handling
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/interrupt` for a passive-server-launched headless agent
- **THEN** the passive server signals the managed headless runtime controller directly
- **AND THEN** the request does not fail with the generic "not managed" or "no gateway" behavior

#### Scenario: Managed stop cleans up server-owned state
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/stop` for a passive-server-launched headless agent
- **THEN** the passive server stops the authoritative managed headless session
- **AND THEN** the `ManagedHeadlessStore` authority is removed
- **AND THEN** the in-memory managed handle is removed
