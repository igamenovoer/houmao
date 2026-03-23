# project-cli-identity Specification

## Purpose
TBD - created by archiving change rename-project-cli-and-runtime-to-houmao. Update Purpose after archive.
## Requirements
### Requirement: Repository-facing project identity uses Houmao
The repository SHALL present the project and distribution-facing identity as `Houmao` across packaging metadata and active repository guidance instead of `gig-agents`.

Active repository guidance includes README and docs content, contributor guidance, active context materials outside preserved logs, and active OpenSpec-facing reference text that describes the current public surface.

#### Scenario: Project branding surfaces use the new identity
- **WHEN** a maintainer inspects packaging metadata or active repository guidance
- **THEN** the project and distribution name presented to readers is `Houmao`
- **AND THEN** active guidance does not present `gig-agents` as the canonical project name

### Requirement: Primary operator CLI is `houmao-cli`
The repository SHALL expose its primary runtime-management CLI as `houmao-cli`.

The existing runtime subcommands and their meanings SHALL remain unchanged during this rebrand.

#### Scenario: CLI examples use the renamed top-level command
- **WHEN** an operator follows README, docs, or help examples for runtime management
- **THEN** those examples invoke `houmao-cli`
- **AND THEN** the supported command vocabulary still includes `build-brain`, `start-session`, `send-prompt`, `send-keys`, `mail`, and `stop-session`

### Requirement: Rebrand scope preserves non-targeted public surfaces
This rebrand SHALL NOT rename the Python import root `gig_agents`, the secondary CAO launcher `gig-cao-server`, or the existing `AGENTSYS_*` runtime identity and environment namespaces.

#### Scenario: Non-targeted surfaces remain stable
- **WHEN** a developer inspects source imports, CAO launcher guidance, or runtime identity contracts after the rebrand
- **THEN** Python imports continue to use `gig_agents`
- **AND THEN** the CAO launcher surface remains `gig-cao-server`
- **AND THEN** runtime identity and environment contracts remain in the `AGENTSYS_*` namespace

