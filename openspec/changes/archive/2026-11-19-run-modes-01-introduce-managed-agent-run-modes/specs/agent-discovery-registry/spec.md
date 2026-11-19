# Spec Delta

## ADDED Requirements

### Requirement: Managed presence identifies the run mode and native surface

A current local managed presence record SHALL identify the selected tool, run mode, concrete backend, managed generation, and optional native human surface consistently with the current manifest. Public Web location metadata SHALL contain only a token-free origin and the bound session identity. A service control socket, stdio handle, or supervisor pane SHALL confer no human interface.

#### Scenario: Web presence survives gateway detach

- **WHEN** an operator detaches the gateway from a live owned Web host
- **THEN** the record retains its safe browser reference and mode and omits any discarded gateway endpoint

#### Scenario: A joined terminal publishes its identity

- **WHEN** a supported current-session TUI is adopted with verified terminal authority
- **THEN** its new record reports tui and the verified terminal surface

#### Scenario: A record disagrees with the manifest

- **WHEN** a service record claims a terminal UI or names a backend belonging to another mode
- **THEN** the reader reports unusable authority before routing an operation
