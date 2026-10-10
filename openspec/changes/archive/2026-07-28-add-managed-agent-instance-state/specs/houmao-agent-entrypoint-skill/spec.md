## ADDED Requirements

### Requirement: Agent entrypoint routes verified-self runtime-variable reads
The agent entrypoint SHALL route declared runtime-variable lookup through verified-self commands and SHALL expose no self mutation.

#### Scenario: Static skill requests current value
- **WHEN** a managed agent invokes the maintained lookup from a current supported runtime
- **THEN** the route SHALL return the verified agent's current value revision

### Requirement: Agent entrypoint routes verified-self mindset snapshots
The agent entrypoint SHALL route a required named mindset to one verified-self immutable snapshot and SHALL fail closed when it is unavailable.

#### Scenario: Prompt text claims a different identity
- **WHEN** the prompt names another agent while runtime authority identifies self
- **THEN** the route SHALL use runtime authority and SHALL not expose the other agent's record
