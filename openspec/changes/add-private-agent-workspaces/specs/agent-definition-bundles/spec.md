## ADDED Requirements

### Requirement: Instance contracts preserve private workspace policy
An Agent Definition instance contract SHALL preserve the optional Private Agent Workspace Contract, activation mode, default deployment selection, and independent workdir mode.

#### Scenario: Private storage uses project workdir
- **WHEN** a definition declares private storage with project-root workdir
- **THEN** validation SHALL preserve those as independent settings
