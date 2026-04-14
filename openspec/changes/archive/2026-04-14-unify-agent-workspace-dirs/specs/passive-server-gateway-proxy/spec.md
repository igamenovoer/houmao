## ADDED Requirements

### Requirement: Passive server proxies managed workspace gateway endpoints
The passive server SHALL expose pair-server routes that proxy live gateway workspace endpoints for one resolved managed agent.

The proxy routes SHALL mirror the gateway workspace summary, memo read, memo replace, memo append, lane tree, lane file read, lane file write, lane append, lane delete, and lane clear operations under the managed-agent gateway route family.

The proxy SHALL preserve the gateway's lane validation, containment errors, disabled-persist errors, and unavailable-gateway errors in structured responses.

#### Scenario: Pair server proxies workspace summary
- **WHEN** an operator requests `/houmao/agents/researcher/gateway/workspace`
- **AND WHEN** the passive server resolves `researcher` to a live gateway
- **THEN** the passive server returns the gateway workspace summary response

#### Scenario: Pair server preserves disabled persist error
- **WHEN** managed agent `researcher` has persistence disabled
- **AND WHEN** an operator requests a persist-lane file through the pair-server gateway proxy
- **THEN** the passive server returns the gateway's disabled-persist error
- **AND THEN** the passive server does not create a persist directory

#### Scenario: Pair server proxies memo append
- **WHEN** an operator appends initialization rules through the pair-server gateway workspace memo route
- **AND WHEN** the passive server resolves the agent to a live gateway
- **THEN** the passive server forwards the append to the gateway memo endpoint
- **AND THEN** the gateway writes to the fixed `houmao-memo.md` file
