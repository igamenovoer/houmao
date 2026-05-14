## ADDED Requirements

### Requirement: Pro remains the heavyweight maintained loop skill
The packaged `houmao-agent-loop-pro` skill SHALL remain the maintained Houmao-owned loop skill for schema-rich generated execplans, topology-aware contracts, generated harnesses, generated docs, validation-heavy workflows, and complex tree-loop or generic-loop operation.

The pro skill SHALL NOT claim to be the only maintained Houmao loop skill after `houmao-agent-loop-lite` is added.

The pro skill SHALL distinguish its generated execplan workflow from the lite Markdown/direct-SQL workflow when current loop-skill choice matters.

#### Scenario: User needs generated harness and schemas
- **WHEN** a user explicitly wants generated harness commands, schema-backed mail families, or validation-heavy topology contracts
- **THEN** `houmao-agent-loop-pro` remains the current maintained loop skill for that work
- **AND THEN** the guidance does not route that work to lite

#### Scenario: Pro no longer says it is sole current loop skill
- **WHEN** a user reads current pro skill guidance
- **THEN** the guidance does not state that pro is the only maintained loop system skill
- **AND THEN** it may identify lite as the separate Markdown/direct-SQL loop path when relevant
