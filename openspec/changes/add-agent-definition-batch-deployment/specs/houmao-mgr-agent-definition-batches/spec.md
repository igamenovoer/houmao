## ADDED Requirements

### Requirement: Batch Requests bind one exact definition and bounded count
A Batch Deployment Request SHALL name one exact definition revision, one target project, a positive count within a maintained limit, shared inputs, optional valid member overrides, and explicit delegation categories.

#### Scenario: Plural count has no delegation
- **WHEN** a human requests four deployments without delegating names, tools, or credentials
- **THEN** the operator SHALL not choose those fields and SHALL request any missing required selections

#### Scenario: Definition changes after request
- **WHEN** the definition digest no longer matches the Batch Request
- **THEN** batch planning SHALL reject the request

### Requirement: Delegated selections remain field-limited
The operator SHALL select only unique names, compatible registered tools, and existing compatible credential references for categories the human explicitly delegates.

#### Scenario: Credential delegation is present
- **WHEN** the human delegates credentials
- **THEN** the operator MAY select an existing compatible credential reference and SHALL NOT create or expose a secret

#### Scenario: Human fixed one member name
- **WHEN** the Batch Request contains a user-selected member name
- **THEN** name delegation SHALL not replace that selection

### Requirement: Batch Plans contain complete ordinary member plans
A Batch Deployment Plan SHALL contain one ordered, individually valid Deployment Plan per member and complete cross-member validation.

#### Scenario: One member is invalid
- **WHEN** any member has an unresolved input, incompatible selection, or project collision
- **THEN** planning SHALL reject the complete batch before mutation

#### Scenario: Two generated names collide
- **WHEN** member plans resolve to the same project name or managed path
- **THEN** cross-member validation SHALL reject the batch

### Requirement: Batch apply gives all-or-nothing catalog visibility
Batch apply SHALL stage all member content and use one catalog transaction so no member becomes visible unless every member is ready.

#### Scenario: Apply stops during preparation
- **WHEN** a later member fails before catalog commit
- **THEN** no Agent Deployment member SHALL be catalog-visible and operation-owned staging SHALL remain recoverable

#### Scenario: Apply succeeds
- **WHEN** every staged member and catalog relationship remains valid
- **THEN** all ordinary Agent Deployments SHALL become visible in one catalog commit

### Requirement: Batch interruption is recoverable
The batch operation journal SHALL record `planned`, `preparing`, `prepared`, `committing`, `applied`, or `failed` and SHALL support deterministic doctor recovery.

#### Scenario: Process crashes after catalog commit
- **WHEN** final path publication is incomplete
- **THEN** doctor SHALL finish publication or report a precise unrecoverable ownership conflict

### Requirement: Batch provenance does not create a batch lifecycle
Each successful member SHALL store one batch operation id and ordinal. Houmao SHALL not create a durable Agent Deployment Batch domain object.

#### Scenario: One member is later removed
- **WHEN** an operator removes one ordinary deployment
- **THEN** its peers SHALL remain independent and SHALL retain their original operation provenance

### Requirement: Batch deployment remains pre-launch
Batch apply SHALL return one maintained launch handoff per member and SHALL start no managed-agent process.

#### Scenario: Four members apply
- **WHEN** batch apply succeeds
- **THEN** Houmao SHALL print four launch handoffs without running any of them
