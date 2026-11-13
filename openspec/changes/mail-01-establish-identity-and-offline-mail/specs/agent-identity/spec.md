# Spec Delta

## ADDED Requirements

### Requirement: Agent IDs are immutable globally unique logical identities
`agent_id` SHALL be opaque and globally unique by contract. Identical IDs SHALL denote the same logical agent. Houmao SHALL NOT detect or repair accidental identity collisions. Names, mail addresses, hosts, sessions, and process generations SHALL remain separate from this identity and SHALL NOT change an existing ID.

#### Scenario: Same ID is observed from another host
- **WHEN** Houmao observes the same `agent_id` through another host or registry connection
- **THEN** it interprets that value as the same logical agent
- **AND THEN** it does not attempt to distinguish accidental ID reuse from intentional identity continuity

#### Scenario: Identity survives operational changes
- **WHEN** an agent restarts, is renamed or relocated, or changes mailbox bindings
- **THEN** its persisted `agent_id` remains unchanged

### Requirement: New agents use UUID generation unless explicitly configured otherwise
Creation of a new agent without a supplied ID or explicit generation mode SHALL generate a UUID. An explicit `name-hash` mode SHALL retain deterministic name-derived IDs and place name-uniqueness responsibility on the caller. A supplied ID SHALL be used as the opaque identity. Selecting both a supplied ID and a generation mode SHALL fail as ambiguous input.

#### Scenario: UUID is the creation default
- **WHEN** two new agents are created with the same friendly name and default ID selection
- **THEN** each receives a separately generated UUID
- **AND THEN** friendly-name lookup can report ambiguity instead of merging those agents

#### Scenario: Caller opts into name-derived identity
- **WHEN** creation explicitly selects `name-hash` for the same normalized name on two runs
- **THEN** it yields the same deterministic ID
- **AND THEN** Houmao treats the runs as addressing the same agent identity

#### Scenario: Supplied hash-like IDs remain valid identities
- **WHEN** an authorized creation input supplies an ID accepted by the opaque ID syntax
- **THEN** Houmao preserves it without requiring UUID formatting or deriving a replacement from mail

### Requirement: Identity selection occurs only at creation boundaries
Creation SHALL resolve and persist the chosen agent ID before publishing runtime or mailbox state. Resume, relaunch, discovery, manifest serialization, and registry refresh SHALL reuse the stored identity rather than generate one. A durable agent record missing its required ID SHALL fail validation instead of inventing an identity during a read or update.

#### Scenario: Manifest persistence does not generate another UUID
- **WHEN** an existing agent persists updated backend or mailbox state
- **THEN** the resulting manifest contains the same stored ID

#### Scenario: Missing durable identity is explicit
- **WHEN** a resume operation loads a current-format agent record with no `agent_id`
- **THEN** it fails with an identity-validation error
- **AND THEN** it does not silently hash the name or generate a new UUID
