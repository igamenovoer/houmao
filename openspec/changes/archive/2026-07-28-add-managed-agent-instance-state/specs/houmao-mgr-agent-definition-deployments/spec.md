## ADDED Requirements

### Requirement: Deployment preserves immutable instance-state declarations
Agent Deployment planning and apply SHALL preserve the exact instance contract and SHALL create no mutable per-instance state.

#### Scenario: Deployment with runtime and mindset declarations succeeds
- **WHEN** the definition and Deployment Request are valid
- **THEN** the applied deployment SHALL record the instance-contract digest for later managed launch

### Requirement: In-use instance contracts cannot change implicitly
Deployment update SHALL reject a changed instance-contract digest while a live or preserved managed-agent instance references the deployment.

#### Scenario: Preserved instance references the deployment
- **WHEN** update proposes changed runtime-variable or mindset declarations
- **THEN** update SHALL fail with guidance to create a new deployment
