# Spec Delta

## MODIFIED Requirements

### Requirement: Gateway attach supports explicit tmux-session targeting outside the owning session
`houmao-mgr agents single --target-tmux-session <session> gateway attach` SHALL select a unique fresh local registry record. Attach SHALL verify that the manifest matches the selected agent, generation, and owning tmux binding.

#### Scenario: Acceptance criteria

- **WHEN** an operator attaches a gateway with a tmux session alias
- **THEN** the runtime uses the current selected owner's authority

#### Scenario: Outside-tmux attach resolves authority from the addressed tmux session manifest

- **WHEN** a caller selects a fresh registry alias for a peer on another socket
- **THEN** the manager uses the peer's verified manifest and owner socket to attach the gateway
- **AND THEN** the caller's enclosing tmux session is unaffected

#### Scenario: Outside-tmux attach falls back to shared-registry tmux alias recovery

- **WHEN** one fresh registry alias identifies the intended local agent
- **AND WHEN** the caller cannot read the enclosing tmux environment
- **THEN** the manager resolves the owner manifest directly from the registry

#### Scenario: Pair-managed attach uses manifest-derived pair authority after tmux-session resolution

- **WHEN** a local registry alias refers to a retired pair-managed backend
- **THEN** the manager reports that the backend is retired
- **AND THEN** pair selection uses an explicit agent ID or name

#### Scenario: Conflicting registry alias fails closed

- **WHEN** multiple fresh records claim the same tmux alias
- **THEN** the manager reports the candidate agent IDs and requests an explicit selector
