# docs-degraded-stale-recovery Specification

## Purpose
Define the documentation requirements for the degraded and stale active tmux-backed managed agent recovery reference page.

## Requirements

### Requirement: Degraded and stale recovery documented

The run-phase reference SHALL include a page documenting degraded and stale active tmux-backed managed agent recovery. The page SHALL explain that recovery is triggered when a managed agent's registry record claims `active` but the underlying tmux session is broken or degraded.

#### Scenario: Reader understands when recovery triggers

- **WHEN** a reader opens the degraded-stale recovery page
- **THEN** they find an explanation that recovery runs when `agents stop`, `agents relaunch`, or `agents cleanup` targets a local tmux-backed agent whose registry record is `active` but whose tmux session is missing or degraded

### Requirement: Probe classification documented

The recovery page SHALL document the three probe classifications returned by `probe_tmux_backed_authority()`:

- `healthy` — tmux session exists and is reachable.
- `degraded_missing_primary` — tmux session exists but the primary pane is missing or unresponsive (gateway remnant may survive).
- `stale_missing_session` — tmux session is entirely missing.

#### Scenario: Reader understands probe outcomes

- **WHEN** a reader examines the probe-classification section
- **THEN** they see the three classes with distinguishing symptoms and how each class maps to a recovery path

### Requirement: Recovery paths documented

The recovery page SHALL document the recovery behavior for each classification:

- **Degraded** (`degraded_missing_primary`):
  - `agents stop`: kills the surviving gateway remnant, retires the registry record.
  - `agents relaunch`: kills the gateway remnant, then uses stopped-session revival to rebuild the primary surface and reprovision the gateway through the normal startup path.
- **Stale** (`stale_missing_session`):
  - `agents stop`: retires the registry record without continuity.
  - `agents relaunch`: falls back to retirement with an explicit failure pointing the operator to fresh `agents launch` when preserved manifest authority is unreadable.

#### Scenario: Reader understands degraded recovery

- **WHEN** a reader reads the degraded recovery section
- **THEN** they understand that stop kills the gateway remnant and retires the record, while relaunch rebuilds the primary surface and reprovisions the gateway

#### Scenario: Reader understands stale recovery

- **WHEN** a reader reads the stale recovery section
- **THEN** they understand that both stop and relaunch retire the record, and relaunch explicitly directs the operator to `agents launch` when manifest authority is unreadable

### Requirement: Cleanup purge-registry documented

The recovery page SHALL document the `agents cleanup session --purge-registry` flag as the destructive lifecycle step for confirmed broken active local authority. It SHALL explain that `--purge-registry` is only safe after `probe_tmux_backed_authority()` confirms the session is degraded or stale, and that it deletes the lifecycle record entirely rather than retiring it.

#### Scenario: Reader understands purge-registry semantics

- **WHEN** a reader reads the cleanup integration section
- **THEN** they understand that `--purge-registry` deletes the lifecycle record, that it requires confirmation by tmux inspection, and that it is distinct from the default retire behavior
