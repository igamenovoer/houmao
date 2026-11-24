# Spec Delta

## MODIFIED Requirements

### Requirement: Gateway operational docs explain outside-tmux tmux-session targeting
Gateway operations docs SHALL distinguish the local registry alias from verified self and explicit agent selectors. They SHALL explain the fresh registry lookup and how to disambiguate it.

#### Scenario: Reader can choose between current-session and tmux-session targeting

- **WHEN** a reader wants to attach a gateway outside the owning tmux session
- **THEN** the docs show `agents single --target-tmux-session <session> gateway attach`
- **AND THEN** the docs show `agents self gateway attach` for current-session authority

#### Scenario: Reader understands tmux-session targeting authority and limits

- **WHEN** multiple fresh local records share one tmux session alias
- **THEN** the docs direct the reader to the candidate agent IDs
- **AND THEN** the docs explain that aliases apply to the local registry

#### Scenario: Reader can distinguish pair-authority port selection from gateway listener port selection

- **WHEN** a reader needs a different pair authority or listener
- **THEN** the docs distinguish `--pair-port` with explicit agent selectors from the lower-level gateway listener port
