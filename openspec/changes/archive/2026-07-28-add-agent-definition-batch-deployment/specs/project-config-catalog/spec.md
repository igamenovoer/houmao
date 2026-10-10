## ADDED Requirements

### Requirement: Catalog correlates deployments by batch operation
Each Agent Deployment created by one batch apply SHALL store the same opaque batch operation id and a unique member ordinal.

#### Scenario: Batch members are inspected
- **WHEN** an operator inspects any successful member
- **THEN** the catalog SHALL report its operation id and ordinal without requiring a batch entity

### Requirement: Failed batches leave no visible member rows
The project catalog SHALL insert every member through one transaction after all staged content is ready.

#### Scenario: Precommit failure occurs
- **WHEN** any member cannot be prepared
- **THEN** the catalog SHALL contain no member Agent Deployment or partial batch relationship
