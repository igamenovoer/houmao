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
### Requirement: Rebrand scope preserves non-targeted public surfaces
The repository SHALL preserve the `Houmao` project and distribution identity and SHALL standardize the active runtime identity and environment namespace on `HOUMAO_*`.

Legacy standalone CLI retirement or other operator-surface cleanup SHALL NOT require another package-namespace rename after this change, because the supported live runtime namespace is already unified on `HOUMAO_*`.

The repository MAY continue to retire deprecated surfaces without redefining the `houmao` package identity away from `Houmao`.

#### Scenario: Active runtime namespace is Houmao-named after the rename
- **WHEN** a maintainer inspects active runtime env contracts and package identity after the namespace rename
- **THEN** the project remains `Houmao`
- **AND THEN** active runtime identity and environment contracts use the `HOUMAO_*` namespace
- **AND THEN** supported-surface cleanup does not preserve `AGENTSYS_*` as the stable live namespace
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
