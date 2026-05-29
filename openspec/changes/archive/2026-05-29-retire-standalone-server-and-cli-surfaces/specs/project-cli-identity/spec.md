## MODIFIED Requirements

### Requirement: Primary supported operator workflow uses `houmao-mgr` and `houmao-passive-server`
The repository SHALL expose its primary supported operator workflow through `houmao-mgr` together with `houmao-passive-server`.

Repo-owned README, docs, and help examples for current workflows SHALL use `houmao-mgr` for local project and managed-agent operations and `houmao-passive-server` for maintained API-based discovery, observation, and management rather than `houmao-cli` or standalone `houmao-server`.

#### Scenario: Current operator examples use the supported manager and passive-server commands
- **WHEN** an operator follows active README, docs, or help examples for current runtime management
- **THEN** those examples invoke `houmao-mgr` or `houmao-passive-server`
- **AND THEN** they do not present `houmao-cli` or standalone `houmao-server` as primary active operator commands

#### Scenario: Standalone old-server references are historical or internal only
- **WHEN** active repository guidance needs to mention retained modules under `houmao.server`
- **THEN** that guidance frames them as internal/shared implementation modules
- **AND THEN** it does not instruct users to launch a packaged `houmao-server` executable
