## ADDED Requirements

### Requirement: Touring presents lite and pro as current loop branches
The `houmao-touring` skill SHALL present `houmao-agent-loop-lite` and `houmao-agent-loop-pro` as the current maintained loop-authoring branches.

Touring SHALL route lightweight Markdown/direct-SQL/no-harness loop requests to `houmao-agent-loop-lite`.

Touring SHALL route schema-rich, topology-heavy, harness-backed, validation-heavy, or complex generated-execplan requests to `houmao-agent-loop-pro`.

Touring SHALL NOT route current loop planning or generated loop run-control requests to retired pairwise or generic loop packages.

#### Scenario: Touring user asks for the simplest loop system
- **WHEN** a touring user asks for a simple loop definition with Markdown and direct SQLite
- **THEN** touring identifies `houmao-agent-loop-lite` as the current branch
- **AND THEN** it explains that lite omits generated harness and docs layers

#### Scenario: Touring user asks for complex generated execplans
- **WHEN** a touring user asks for generated topology contracts, harness validation, or schema-typed mail
- **THEN** touring identifies `houmao-agent-loop-pro` as the current branch
- **AND THEN** it does not present lite as equivalent for that work
