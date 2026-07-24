## ADDED Requirements

### Requirement: The existing Agent Definition routine owns authoring and deployment
`houmao-shared-routines->houmao-agent-definition` SHALL provide one command family for initialization, derivation, clarification, approval, materialization, validation, planning, apply, inspection, doctor, update, and removal.

#### Scenario: Human starts from requirements
- **WHEN** an admin invokes the routine with prose for a new reusable agent
- **THEN** it SHALL initialize or update `agent-def-overview.md` and SHALL stop at each requested review boundary

#### Scenario: Human starts from a materialized revision
- **WHEN** an admin asks to deploy an existing revision
- **THEN** the routine SHALL skip authoring and SHALL collect only the revision's declared deployment inputs

### Requirement: The routine delegates durable work to maintained commands
The routine SHALL use maintained `houmao-mgr` commands for validation, materialization, planning, apply, doctor, update, and removal.

#### Scenario: Deployment is confirmed
- **WHEN** the human approves a Deployment Plan
- **THEN** the routine SHALL invoke maintained apply and SHALL not reproduce filesystem or catalog mutation in skill instructions

### Requirement: The routine does not invent semantic edit authority
The routine SHALL bind only declared deployment inputs. It SHALL route undeclared content changes back to authoring and rematerialization.

#### Scenario: Task requires changing core behavior
- **WHEN** a request cannot fit declared bindings
- **THEN** the routine SHALL explain the conflict and SHALL not patch the revision during deployment

### Requirement: Definition administration remains admin-only and pre-launch
The routine SHALL reject managed-agent posture for authoring and deployment. Successful deployment SHALL report but SHALL not execute the launch command.

#### Scenario: Managed agent invokes definition deployment
- **WHEN** verified actor posture is managed agent
- **THEN** the routine SHALL reject the operation
