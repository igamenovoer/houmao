## ADDED Requirements

### Requirement: Managed headless turn reconciliation is execution-owned
For accepted managed headless turns, `houmao-server` SHALL treat server-owned execution evidence as the primary authority for turn lifecycle and terminal result.

Execution evidence SHALL include, at minimum:

- durable turn artifacts produced by the headless turn runner,
- runner-owned durable process metadata sufficient for post-restart liveness checks,
- the underlying CLI exit or return status,
- parsed machine-readable CLI output when available, and
- explicit server-owned interrupt intent when an interrupt was requested.

tmux session, window, or pane visibility MAY be used for best-effort control, cleanup, or diagnostics, but SHALL NOT by itself finalize, downgrade, or reinterpret a managed headless turn outcome.

For managed headless turns, `unknown` SHALL NOT be used as a normal reconciliation or finalization outcome. When execution evidence is missing or legacy metadata is insufficient, `houmao-server` SHALL fail closed to `failed` and attach explicit diagnostics rather than preserving tmux-watch-era ambiguity.

#### Scenario: Successful headless turn finalizes from durable CLI result
- **WHEN** an accepted managed headless turn later produces a durable terminal result with successful CLI completion evidence
- **THEN** `houmao-server` reports that turn as completed from that execution evidence
- **AND THEN** callers do not need tmux topology to determine that the turn finished successfully

#### Scenario: Unexpected execution loss becomes normal failed turn
- **WHEN** an accepted managed headless turn no longer has live execution evidence
- **AND WHEN** `houmao-server` never recorded an interrupt request for that turn
- **THEN** `houmao-server` reconciles that turn to a terminal failed state
- **AND THEN** the server does not require or expose a special tmux-observed intervention classification to explain the loss

#### Scenario: Interrupt intent controls interrupted outcome
- **WHEN** `houmao-server` previously recorded an interrupt request for an active managed headless turn
- **AND WHEN** the underlying headless execution later ends without a successful completion result
- **THEN** `houmao-server` reconciles that turn as interrupted
- **AND THEN** interrupted outcome comes from server-owned control intent plus execution end rather than tmux window observation alone

#### Scenario: Missing finalization marker still fails closed
- **WHEN** a managed headless worker reaches terminal reconciliation for an accepted turn
- **AND WHEN** no durable terminal result marker exists
- **AND WHEN** the server has no live execution evidence and never recorded an interrupt request for that turn
- **THEN** `houmao-server` finalizes that turn as failed with diagnostic context
- **AND THEN** the server does not emit `unknown` as a normal managed-headless finalization result

### Requirement: Managed headless restart recovery does not depend on tmux watch semantics
When `houmao-server` restarts while a managed headless turn is still recorded as active, later reconciliation SHALL use durable runner artifacts and execution-liveness evidence to determine whether the turn is still active or has already ended.

The server SHALL NOT require the presence of a specific tmux window or pane name in order to preserve or finalize managed headless turn state after restart.

#### Scenario: Restart preserves active turn while execution remains live
- **WHEN** `houmao-server` restarts while a managed headless turn is recorded as active
- **AND WHEN** durable completion artifacts are not yet present but execution evidence still indicates that the underlying CLI turn is live
- **THEN** `houmao-server` continues reporting that turn as active
- **AND THEN** later prompt admission remains blocked until the turn reaches a terminal state

#### Scenario: Restart finalizes active turn from durable artifacts without tmux window matching
- **WHEN** `houmao-server` restarts while a managed headless turn is recorded as active
- **AND WHEN** durable turn artifacts later show a terminal CLI result
- **THEN** `houmao-server` finalizes the turn from those artifacts
- **AND THEN** the server does not need a matching tmux window identity to trust that terminal result

#### Scenario: Restart fails closed when execution is dead and no exit marker exists
- **WHEN** `houmao-server` restarts while a managed headless turn is recorded as active
- **AND WHEN** durable completion artifacts are not present
- **AND WHEN** durable execution-liveness evidence shows the underlying CLI process is no longer live
- **AND WHEN** the server never recorded an interrupt request for that turn
- **THEN** `houmao-server` finalizes that turn as failed with diagnostic context
- **AND THEN** the server does not require tmux window matching to determine that the execution died before completion

#### Scenario: Restarted legacy active turn without process metadata fails closed
- **WHEN** `houmao-server` restarts while a pre-change managed headless turn is still recorded as active
- **AND WHEN** durable completion artifacts are not present
- **AND WHEN** the persisted active-turn record lacks the new execution-liveness metadata needed for restart recovery
- **THEN** `houmao-server` finalizes that turn as failed with explicit diagnostic context
- **AND THEN** the server does not preserve `unknown` as a migration-only recovery bucket
