# Spec Delta

## ADDED Requirements

### Requirement: Codex app-server selection requires a qualified service launch

A fresh current-schema `(codex, service)` launch SHALL select the maintained app-server adapter. It SHALL reject retained incompatible manifests, other mode/backend pairs, and unqualified native builds with actionable diagnostics. It SHALL preserve the existing headless and terminal alternatives.

#### Scenario: Codex service is explicitly requested

- **WHEN** the operator selects service mode for a qualified Codex build
- **THEN** the runtime creates a new managed service owner and negotiates the app-server protocol before publishing readiness

#### Scenario: A retained incompatible app-server manifest is supplied

- **WHEN** a controller attempts to revive an old blocked adapter record as a current service
- **THEN** the runtime fails before provider start and directs the operator to a fresh launch

#### Scenario: A Codex build cannot support service

- **WHEN** the selection fails its version or protocol check
- **THEN** the error identifies the required service capability and the available headless and TUI modes

## REMOVED Requirements

### Requirement: `codex_app_server` is unmaintained and blocked at launch

**Reason**: The newly qualified adapter supports fresh, owner-bound `service` launches.

**Migration**: Use a fresh current-schema service launch after installing a qualified build. Older app-server authority records require a fresh launch.
