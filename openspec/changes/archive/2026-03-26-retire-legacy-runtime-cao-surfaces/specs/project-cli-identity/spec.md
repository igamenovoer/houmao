## REMOVED Requirements

### Requirement: Primary operator CLI is `houmao-cli`
**Reason**: Supported operator workflows now center on `houmao-mgr` and `houmao-server`, while `houmao-cli` is being retired as an active first-class runtime-management surface.
**Migration**: Use `houmao-mgr` for managed-agent and pair-native operations and `houmao-server` for supported service workflows. Keep `houmao-cli` only in explicit migration, legacy, or retirement guidance while it still exists in the repository.

## MODIFIED Requirements

### Requirement: Rebrand scope preserves non-targeted public surfaces
The repository SHALL preserve the `Houmao` project and distribution identity and SHALL keep the `AGENTSYS_*` runtime identity and environment namespaces stable across CLI-surface retirement.

This change SHALL NOT require another package-namespace rename or another runtime env-namespace rename just because legacy standalone CLI surfaces are being retired.

The repository MAY retire standalone runtime or launcher CLIs from the active supported surface without redefining the `houmao` package identity or the `AGENTSYS_*` runtime namespace.

#### Scenario: Legacy CLI retirement does not rename runtime namespaces
- **WHEN** a maintainer inspects runtime env contracts and package identity after the CLI-surface retirement
- **THEN** the project remains `Houmao`
- **AND THEN** runtime identity and environment contracts remain in the `AGENTSYS_*` namespace
- **AND THEN** the retirement of `houmao-cli` or `houmao-cao-server` does not imply another rename of those namespaces

## ADDED Requirements

### Requirement: Primary supported operator workflow uses `houmao-mgr` and `houmao-server`
The repository SHALL expose its primary supported operator workflow through `houmao-mgr` together with `houmao-server`.

Repo-owned README, docs, and help examples for current workflows SHALL use `houmao-mgr` and `houmao-server` rather than `houmao-cli`.

#### Scenario: Current operator examples use the supported pair-native commands
- **WHEN** an operator follows active README, docs, or help examples for current runtime management
- **THEN** those examples invoke `houmao-mgr` or `houmao-server`
- **AND THEN** they do not present `houmao-cli` as the primary active operator command
