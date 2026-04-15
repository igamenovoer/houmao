## REMOVED Requirements

### Requirement: Passive server proxies managed workspace gateway endpoints
**Reason**: The passive server no longer proxies managed workspace lane endpoints.

**Migration**: Proxy live gateway managed memory memo and page endpoints.

## ADDED Requirements

### Requirement: Passive server proxies managed memory gateway endpoints
The passive server SHALL expose pair-server routes that proxy live gateway managed memory endpoints for one resolved managed agent.

The proxy routes SHALL mirror the gateway memory summary, memo read, memo replace, memo append, page list, page read, page write, page append, page delete, and page reindex operations under the managed-agent gateway route family.

The proxy SHALL preserve the gateway's page validation, containment errors, memo target validation, and unavailable-gateway errors in structured responses.

#### Scenario: Pair server proxies memory summary
- **WHEN** an operator requests the pair-server managed memory summary for `researcher`
- **AND WHEN** the passive server resolves `researcher` to a live gateway
- **THEN** the passive server returns the gateway memory summary response

#### Scenario: Pair server proxies page write
- **WHEN** an operator writes memory page `operator-rules.md` through the pair-server gateway proxy
- **AND WHEN** the passive server resolves the agent to a live gateway
- **THEN** the passive server forwards the write to the gateway memory page endpoint
- **AND THEN** the gateway enforces pages-directory containment

#### Scenario: Pair server proxies memo append
- **WHEN** an operator appends initialization rules through the pair-server gateway memory memo route
- **AND WHEN** the passive server resolves the agent to a live gateway
- **THEN** the passive server forwards the append to the gateway memo endpoint
- **AND THEN** the gateway writes to the fixed `houmao-memo.md` file
