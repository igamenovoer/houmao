## ADDED Requirements

### Requirement: Agent Definition authoring separates source, interpretation, and materialization
An Agent Definition Workspace SHALL keep human-owned source intent, operator-derived interpretation, and immutable materialized output in distinct directories.

#### Scenario: Workspace stages remain distinct
- **WHEN** an operator initializes an Agent Definition Workspace
- **THEN** source SHALL live under `intent/src`, derived interpretation SHALL live under `intent/derived`, and materialized output SHALL live under `agent-definition`

### Requirement: Source intent has one freeform entrypoint
The authoring workflow SHALL locate `intent/src/agent-def-overview.md` as the only required source file. It SHALL read an optional supporting source file only when the overview references it through a confined relative path.

#### Scenario: Initialization preserves the user's requirements
- **WHEN** the operator initializes authoring from a user's prose requirements
- **THEN** it SHALL create only `agent-def-overview.md` and SHALL preserve unresolved information as unresolved source intent

#### Scenario: Unreferenced sibling is excluded
- **WHEN** `intent/src` contains a sibling file that the overview does not reference
- **THEN** derivation SHALL exclude that file from the source set and source digest

### Requirement: Derived intent has one machine authority
The derived layer SHALL contain `interpretation.md`, `materialization.toml`, `materials/`, `validation.json`, and `approval.toml`. `materialization.toml` SHALL be the only machine input to materialization.

#### Scenario: Interpretation remains reviewable
- **WHEN** the operator derives an authoring workspace
- **THEN** the human SHALL be able to review assumptions, mappings, unresolved authoring questions, and proposed output before approval

#### Scenario: Parallel reports do not become authorities
- **WHEN** the workflow generates an optional human-readable report
- **THEN** materialization SHALL continue to consume only the approved `materialization.toml` and copied materials

### Requirement: Derived freshness is digest-backed
Derivation SHALL record the digest of the overview and every referenced source file. Any changed source digest SHALL invalidate validation and approval.

#### Scenario: Referenced source changes after approval
- **WHEN** the overview or a referenced source file changes after approval
- **THEN** materialization SHALL stop until derivation, validation, and approval run again

### Requirement: Source skills become portable definition materials
Authoring SHALL validate and copy every selected Agent Skill directory into `intent/derived/materials/` before approval.

#### Scenario: Original skill path disappears
- **WHEN** a materialized definition is used after its original source skill directory has been removed
- **THEN** validation and deployment SHALL use the bundle-owned skill copy without reading the original path

### Requirement: Approval binds the exact derived result
Materialization SHALL require explicit human approval bound to the current derived digest and validation result.

#### Scenario: Stale approval cannot materialize
- **WHEN** derived interpretation or copied material changes after approval
- **THEN** materialization SHALL reject the stale approval and SHALL write no Agent Definition Revision
