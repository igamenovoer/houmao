## ADDED Requirements

### Requirement: Agent entrypoint routes verified-self semantic path reads
The agent entrypoint SHALL route semantic path lookup through verified-self authority and SHALL not expose workspace mutation.

#### Scenario: Project-root agent asks for a private path
- **WHEN** the verified agent has no active private workspace
- **THEN** the route SHALL report that the semantic path is unavailable without creating it

#### Scenario: Private agent asks for a declared path
- **WHEN** its manifest and SQLite identity validate
- **THEN** the route SHALL return the current confined path
