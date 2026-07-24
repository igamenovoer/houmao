## ADDED Requirements

### Requirement: Agent Definition documentation uses the current lifecycle
Documentation SHALL describe source intent, derived interpretation, immutable Agent Definition Revisions, Deployment Requests, Deployment Plans, project Agent Deployments, and separate managed-agent launch.

#### Scenario: Reader follows the authoring guide
- **WHEN** a reader creates a reusable individual agent
- **THEN** the guide SHALL start from `agent-def-overview.md` and SHALL not direct the reader to the retired native-agent `blueprints/` layout

#### Scenario: Reader follows the deployment guide
- **WHEN** a reader deploys a materialized revision
- **THEN** the guide SHALL distinguish deployment input collection, planning, apply, and later launch
