# Spec Delta

## ADDED Requirements

### Requirement: Online binding controls proxy the owning gateway authority
Authorized maintained operator surfaces SHALL proxy online binding status, attach/replace, refresh, reconnect, and detach under the selected agent's online mail family. They SHALL preserve expected revisions, replacement intent, protected credential references, and structured outcomes. The proxy SHALL not provision accounts or maintain a second binding store.

#### Scenario: Refresh through the passive server preserves scope
- **WHEN** an authorized operator refreshes an online binding through the maintained proxy
- **THEN** the request targets the resolved owner and expected revision unchanged
- **AND THEN** its response reflects the gateway's committed binding revision

#### Scenario: Binding changed before proxy reaches the gateway
- **WHEN** the gateway refuses a proxied stale-revision update
- **THEN** the proxy preserves that structured conflict
- **AND THEN** it does not retry against the replacement account

### Requirement: Mail proxies preserve page and synchronization information
Channel-selected mail list proxies SHALL forward limit, cursor, filters, and expected binding ID unchanged. Responses SHALL preserve continuation, page-count meaning, completeness, and explicit backend limitations. Cursor validation, stale-state, and content-limit errors SHALL remain distinguishable from gateway connection failure.

#### Scenario: Continued page passes through unchanged
- **WHEN** the gateway returns another bounded metadata page and continuation
- **THEN** the proxy returns those scoped values without fetching additional pages or bodies

#### Scenario: Stale cursor is not a connectivity error
- **WHEN** the gateway rejects an expired or mismatched continuation
- **THEN** the proxy preserves the pagination failure instead of reporting empty mail or generic success

### Requirement: Registry-only service mode exposes no online binding management
Offline member credentials and registry-only route inventories SHALL not expose online account attachment, credential-source selection, or remote agent body control. Online binding management SHALL retain its operator boundary and gateway listener policy.

#### Scenario: Offline member attempts online replacement
- **WHEN** an offline member presents its registry credential to replace an agent's online binding
- **THEN** the registry-only service does not authorize or forward that operation
