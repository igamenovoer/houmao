# Spec Delta

## MODIFIED Requirements

### Requirement: Codex service completes the native handshake

The adapter SHALL admit eligible Codex versions at or above 0.169.0 and start an owner-private app-server over stdio. It SHALL complete `initialize` and `initialized`, verify the selected private home, protocol, and executable identity, and record the actual peer version before reporting ready. A managed agent SHALL own its provider instance and logical thread.

#### Scenario: The peer fails initialization

- **WHEN** a Codex build rejects the handshake or lacks the required protocol shape
- **THEN** launch identifies the failed check and cleans up owned resources without submitting application traffic

#### Scenario: Another app-server is already running

- **WHEN** an unrelated daemon or listener exists in the selected environment
- **THEN** a new managed launch cannot bind to it as the agent's authority

#### Scenario: A newer Codex peer passes startup verification

- **WHEN** a Codex version above 0.169.0 completes the required handshake and verifies its home and thread binding
- **THEN** the service becomes ready and records the newer version

#### Scenario: An eligible peer reports a different home or build

- **WHEN** the peer's private home or reported version does not match the launch identity
- **THEN** launch reports the mismatch and withholds readiness
