## MODIFIED Requirements

### Requirement: Passive server provides a single-agent resolution endpoint
The passive server SHALL expose `GET /houmao/agents/{agent_ref}` that resolves one agent by `agent_id` or `agent_name`.

The `{agent_ref}` path parameter SHALL be interpreted as follows:
1. First, attempt direct lookup by `agent_id` in the discovery index.
2. If no match, canonicalize the input as an agent name by applying `HOUMAO-` prefix normalization and search the index for agents matching that canonical name.
3. If exactly one match is found, return it.
4. If no match is found, return 404.
5. If the name matches multiple agents, return 409 Conflict with a diagnostic message listing the ambiguous agent IDs.

#### Scenario: Resolution by agent_name returns a unique HOUMAO match
- **WHEN** the discovery index contains exactly one agent with name `HOUMAO-alpha`
- **AND WHEN** a caller sends `GET /houmao/agents/alpha`
- **THEN** the response status code is 200
- **AND THEN** the response body contains the agent summary for the matching agent

#### Scenario: Resolution by canonical HOUMAO agent_name is accepted
- **WHEN** the discovery index contains exactly one agent with name `HOUMAO-alpha`
- **AND WHEN** a caller sends `GET /houmao/agents/HOUMAO-alpha`
- **THEN** the response status code is 200
- **AND THEN** the response body contains the agent summary for the matching agent

