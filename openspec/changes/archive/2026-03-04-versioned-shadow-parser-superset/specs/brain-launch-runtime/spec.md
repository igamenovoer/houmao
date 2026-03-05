## MODIFIED Requirements

### Requirement: CAO parsing mode is explicit and constrained
For CAO-backed sessions, the system SHALL resolve a parsing mode at session start from configuration.

Allowed values are exactly:
- `cao_only`
- `shadow_only`

The selected mode SHALL be persisted in session runtime state so resumed operations use the same parsing mode.

Default mapping SHALL be:
- `tool=claude` -> `shadow_only`
- `tool=codex` -> `shadow_only`

#### Scenario: Session start resolves parsing mode from tool default (Claude)
- **WHEN** a caller starts a CAO-backed session without explicitly specifying parsing mode
- **AND WHEN** the tool is `claude`
- **THEN** the resolved parsing mode is `shadow_only`

#### Scenario: Session start resolves parsing mode from tool default (Codex)
- **WHEN** a caller starts a CAO-backed session without explicitly specifying parsing mode
- **AND WHEN** the tool is `codex`
- **THEN** the resolved parsing mode is `shadow_only`

#### Scenario: Session start fails when parsing mode cannot be resolved
- **WHEN** a caller starts a CAO-backed session and configuration does not provide an explicit parsing mode or a valid tool default
- **THEN** the system rejects the start request with an explicit validation error

#### Scenario: Unknown parsing mode is rejected
- **WHEN** a caller requests a parsing mode other than `cao_only` or `shadow_only`
- **THEN** the system rejects the request with an explicit unsupported-mode error

