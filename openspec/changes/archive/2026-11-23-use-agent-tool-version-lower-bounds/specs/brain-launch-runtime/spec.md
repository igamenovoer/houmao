# Spec Delta

## ADDED Requirements

### Requirement: Native provider startup applies its executable minimum

On each provider start, Houmao SHALL apply the backend's inclusive minimum where native startup requires a version. It SHALL use the actual selected executable and apply the minimum independently of prompt policy or strategy override. Compatibility errors SHALL identify the tool, mode, and unmet version requirement.

#### Scenario: As-is launch starts a newer eligible native build

- **WHEN** an `as_is` launch selects a valid Kimi Web or native service executable above the applicable minimum
- **THEN** it passes version validation and proceeds to native startup without applying unattended policy

#### Scenario: A backend requires a later minimum than another mode of the same tool

- **WHEN** DSH Web accepts the selected release candidate but managed DSH service requires a later release candidate
- **THEN** service preflight reports its own minimum before starting the provider

#### Scenario: Relaunch probes the executable available for the new incarnation

- **WHEN** an explicit relaunch selects an executable updated since the previous incarnation
- **THEN** version eligibility uses the newly detected version

## MODIFIED Requirements

### Requirement: Codex app-server selection requires a qualified service launch

A fresh current-schema `(codex, service)` launch SHALL select the maintained app-server adapter. It SHALL reject retained incompatible manifests and other mode/backend pairs. The selected executable SHALL meet the service minimum and pass native startup verification. The runtime SHALL preserve the headless and terminal alternatives.

#### Scenario: Codex service is explicitly requested

- **WHEN** the operator selects service mode for a Codex build at or above the service minimum
- **THEN** the runtime creates a new managed service owner and verifies the app-server protocol before publishing readiness

#### Scenario: A retained incompatible app-server manifest is supplied

- **WHEN** a controller attempts to revive an old blocked adapter record as a current service
- **THEN** the runtime fails before provider start and directs the operator to a fresh launch

#### Scenario: A Codex build cannot support service

- **WHEN** the selection fails its version minimum or a native startup check
- **THEN** the error identifies the failed check and the available headless and TUI modes
