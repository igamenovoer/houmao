## ADDED Requirements

### Requirement: Houmao discovers, validates, and materializes Agent Definitions
`houmao-mgr` SHALL expose maintained commands to inspect and validate local or built-in revisions and to preview or write one approved authoring workspace result.

#### Scenario: Materialization preview is requested
- **WHEN** the operator previews an approved current authoring workspace
- **THEN** Houmao SHALL validate the exact source and derived digests and SHALL write no revision

### Requirement: Deployment Requests preserve operator-authored intent
A Deployment Request SHALL bind one exact definition revision to one target project and SHALL contain typed input values and explicit project selections without rendered output or secrets.

#### Scenario: Required input is missing
- **WHEN** a Deployment Request omits a required input without a default
- **THEN** validation SHALL reject the request before planning

#### Scenario: Definition changes after input collection
- **WHEN** the definition digest differs from the request's bound digest
- **THEN** planning SHALL reject the request and require fresh confirmation

### Requirement: Deployment Plans are deterministic apply inputs
Planning SHALL resolve every declared binding, validate collisions, render managed content, and produce a digest-protected Deployment Plan. Apply SHALL consume only the selected intact plan.

#### Scenario: Unresolved marker remains
- **WHEN** rendered content contains an unresolved `{{houmao.deploy.*}}` marker
- **THEN** planning SHALL fail and SHALL create no applicable plan

#### Scenario: Plan content is edited
- **WHEN** any rendered artifact differs from its recorded plan digest
- **THEN** apply SHALL reject the plan before catalog mutation

### Requirement: Apply uses recoverable catalog visibility
Apply SHALL stage operation-owned content and SHALL make one Agent Deployment catalog-visible only after every proposed artifact is ready. It SHALL journal recoverable operation state.

#### Scenario: Publication is interrupted
- **WHEN** the process stops after staging or catalog commit
- **THEN** doctor SHALL identify the operation state and SHALL finish publication or remove only operation-owned staging

#### Scenario: Apply succeeds
- **WHEN** the plan and target project remain valid through publication
- **THEN** the project SHALL contain one visible Agent Deployment with its complete specialist, profile, skill, content, request, and plan relationships

### Requirement: Deployment remains separate from launch
Successful apply SHALL return the maintained profile-backed launch command and SHALL NOT run it.

#### Scenario: Operator applies a deployment
- **WHEN** apply succeeds
- **THEN** no managed-agent process or mutable instance state SHALL be created

### Requirement: Doctor verifies ownership and provenance
Doctor SHALL verify definition, request, plan, catalog, managed-content, registered-skill, and output digests and SHALL distinguish source drift from output drift.

#### Scenario: Managed file is edited
- **WHEN** a deployment-owned rendered file changes after apply
- **THEN** doctor SHALL report output drift and update SHALL not overwrite it silently

### Requirement: Update blocks incompatible in-use instance contracts
Update SHALL use a new request and plan. It SHALL reject a changed instance-contract digest while a live or preserved managed-agent instance references the deployment.

#### Scenario: Preserved instance uses the old contract
- **WHEN** an update proposes a different instance-contract digest and a preserved instance references the deployment
- **THEN** update SHALL fail with guidance to create a new deployment

### Requirement: Removal respects ownership and instance references
Removal SHALL reject live or preserved instance references and SHALL delete only drift-free deployment-owned relationships and files.

#### Scenario: Deployment has no instance references
- **WHEN** removal targets a drift-free deployment with no live or preserved instances
- **THEN** Houmao SHALL remove its owned project content while preserving credentials and user-owned files
