## ADDED Requirements

### Requirement: Definitions declare typed runtime variables
The Agent Definition instance contract SHALL declare each runtime variable's stable key, scalar type or maintained enum, required posture, optional default, validation bounds, and consumers.

#### Scenario: Invalid declaration is materialized
- **WHEN** a variable has no valid type or references an unknown consumer
- **THEN** definition validation SHALL reject the instance contract

### Requirement: Managed launch instantiates one revisioned value set
Fresh managed launch SHALL combine declaration defaults with explicit per-instance values and store revision one in the canonical instance-state database.

#### Scenario: Two peers use different values
- **WHEN** two agents launch from one deployment with different valid values
- **THEN** each agent SHALL own an independent value set

#### Scenario: Required value is missing
- **WHEN** neither the declaration nor launch request supplies a required value
- **THEN** launch preparation SHALL fail before process start

### Requirement: Launch consumers use one immutable snapshot
Prompt and memo rendering SHALL use one runtime-variable revision selected during launch preparation.

#### Scenario: Value changes after startup
- **WHEN** an operator updates a value after prompt and memo preparation
- **THEN** Houmao SHALL not rewrite submitted prompt context or overwrite live memo content

### Requirement: Static skills read current values without rewriting
Static skills SHALL use verified-self read commands for declared live consumers. Value mutation SHALL not compose or rewrite a skill directory.

#### Scenario: Skill reads a revised value
- **WHEN** an operator commits a new variable revision
- **THEN** the next verified-self read SHALL return that revision while the skill remains byte-stable

### Requirement: Operators mutate one explicit instance
Runtime-variable mutation SHALL require an explicit managed-agent target and expected prior revision. Managed self SHALL remain read-only.

#### Scenario: Concurrent update is stale
- **WHEN** an operator supplies an expected revision that is not current
- **THEN** mutation SHALL fail without changing the existing value set

#### Scenario: Update succeeds
- **WHEN** an explicit admin target, key, value, and expected revision are valid
- **THEN** Houmao SHALL write the next revision atomically and SHALL not prompt or wake the agent

### Requirement: Runtime-variable state follows preserved instance identity
A compatible preserved instance SHALL retain its current values. A fresh instance SHALL start from defaults and its own explicit launch values.

#### Scenario: Preserved instance relaunches
- **WHEN** the same instance relaunches with the same instance-contract digest
- **THEN** launch SHALL revalidate and reuse its current runtime-variable revision

### Requirement: Runtime variables remain non-secret behavior data
Runtime-variable declarations and mutations SHALL reject secret-marked values and SHALL direct credentials to Houmao credential mechanisms.

#### Scenario: Secret value is submitted
- **WHEN** an operator attempts to store a credential secret as a runtime variable
- **THEN** mutation SHALL reject it without replacing the previous revision
