## ADDED Requirements

### Requirement: Deployment selects policy without creating a workspace
A Deployment Request MAY select a definition-valid private workspace and workdir mode. Planning and apply SHALL preserve policy and SHALL create no instance workspace content.

#### Scenario: Private mode deployment succeeds
- **WHEN** the definition permits the selected mode
- **THEN** the Agent Deployment SHALL record the contract digest and selection for later launch

#### Scenario: Unknown feature requests private mode
- **WHEN** no declared deployment binding activates private mode
- **THEN** planning SHALL reject the selection
