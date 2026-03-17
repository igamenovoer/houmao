## ADDED Requirements

### Requirement: Agent-discovery registry specs do not describe current canonicalization in terms of retired `agent_key`
The shared agent discovery registry specification SHALL describe current canonicalization, publication, and lookup behavior in terms of canonical agent names and authoritative `agent_id`, and SHALL NOT describe retired `agent_key` derivation as part of the live post-cutover flow.

Historical references to legacy `agent_key` directories may remain only when they are explicitly marked as pre-cutover cleanup context rather than as the active contract.

#### Scenario: Canonical name input is normalized without implying a current `agent_key` lookup path
- **WHEN** a caller resolves shared-registry agent input `gpu`
- **THEN** the spec describes that input as canonicalized to `AGENTSYS-gpu` before publication, duplicate detection, lookup, or record comparison
- **AND THEN** it does not describe the live canonicalization flow as deriving a current `agent_key`

#### Scenario: Legacy agent-key references remain clearly historical
- **WHEN** the spec mentions a legacy `live_agents/<agent-key>/` directory
- **THEN** that mention is explicitly framed as pre-cutover cleanup or historical context
- **AND THEN** readers are not left to infer that `agent_key` still participates in the active registry identity contract
