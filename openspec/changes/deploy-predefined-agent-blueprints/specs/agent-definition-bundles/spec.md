## ADDED Requirements

### Requirement: Agent Definition Revisions use a portable versioned contract
A materialized Agent Definition Revision SHALL contain `definition.toml`, `deploy-contract.toml`, `instance-contract.toml`, `assets/`, and `provenance/materialization.json`. Its identity and digest SHALL be immutable.

#### Scenario: Valid revision is inspected
- **WHEN** an operator inspects a supported revision
- **THEN** Houmao SHALL report its definition identity, revision identity, schema versions, component references, and verified digest

#### Scenario: Revision content changes
- **WHEN** any file inside an immutable revision changes
- **THEN** validation SHALL report digest drift and deployment SHALL reject the revision

### Requirement: Deploy contracts declare typed inputs and bindings
`deploy-contract.toml` SHALL declare every deployment input, its scalar type or maintained enum, required posture, default, validation bounds, and typed target bindings.

#### Scenario: One input feeds multiple targets
- **WHEN** a task objective binds to a prompt overlay and memo seed
- **THEN** the planner SHALL validate the value once and render both declared targets

#### Scenario: Input has no declared effect
- **WHEN** a deploy contract declares an input with no target binding
- **THEN** definition validation SHALL reject the contract

### Requirement: Deployment rendering is non-executable and context-safe
Text bindings SHALL use exact `{{houmao.deploy.<key>}}` markers and context-specific escaping. Structured bindings SHALL assign typed fields without string evaluation.

#### Scenario: Expression-like marker is present
- **WHEN** definition content contains a marker that is not an exact declared deployment key
- **THEN** validation SHALL reject it without evaluating the expression

#### Scenario: Freeform text reaches TOML
- **WHEN** a text input binds to a TOML string field
- **THEN** rendering SHALL escape it for TOML rather than concatenate raw syntax

### Requirement: V1 revisions do not authorize freeform semantic adaptation
Deployment SHALL change only declared binding targets. A requested change outside those targets SHALL require a new Agent Definition Revision.

#### Scenario: User requests an undeclared prompt rewrite
- **WHEN** the deployment instruction asks the operator to rewrite immutable role behavior
- **THEN** deployment SHALL stop and direct the human to revise and rematerialize the definition

### Requirement: Instance contracts form a stable extension boundary
`instance-contract.toml` SHALL have its own schema and digest. This foundational change SHALL preserve it without creating mutable instance state.

#### Scenario: Project deployment preserves the instance contract
- **WHEN** a definition is deployed
- **THEN** the Agent Deployment SHALL record the exact instance-contract digest and SHALL create no runtime-variable, mindset, or workspace state

### Requirement: Definition skills are complete static Agent Skills
Every bundled Agent Skill SHALL be a complete installable static skill and SHALL not depend on runtime skill composition.

#### Scenario: Reserved system skill name is used
- **WHEN** a definition bundles a private skill whose name collides with a Houmao system skill
- **THEN** validation SHALL reject the definition

### Requirement: Definition content excludes secrets and runtime truth
Definition revisions SHALL contain credential references and declarations only. They SHALL NOT contain credential secrets or mutable per-instance values.

#### Scenario: Credential secret is found
- **WHEN** validation detects a credential secret field in a revision
- **THEN** it SHALL reject the revision and report the offending path
