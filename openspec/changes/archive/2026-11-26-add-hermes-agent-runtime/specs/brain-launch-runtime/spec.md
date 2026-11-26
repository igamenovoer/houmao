# Spec Delta

## MODIFIED Requirements

### Requirement: Tmux-backed headless turns reuse the primary agent window
For one tmux-backed headless session, runtime-controlled prompt execution SHALL be serialized and SHALL NOT overlap.

The runtime SHALL execute each runtime-controlled headless turn on the stable primary agent surface in window 0 and SHALL NOT create a separate per-turn tmux window for normal turn execution.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The runtime SHALL launch each runtime-controlled headless turn through a same-pane fresh-process execution primitive on the stable primary surface rather than typing the command into a long-lived interactive shell.

The runtime SHALL persist the managed child process exit and its durable exit-status artifact. For backends where worker exit and the corresponding artifacts establish execution settlement, the turn SHALL then reach its terminal state. For a finite client of an independently executing daemon, terminal settlement SHALL require the backend's attributable outcome evidence.

The runtime SHALL reconcile terminal headless turn status, terminal timestamps, and next-turn readiness from the authoritative active-turn record plus durable turn artifacts rather than from tmux shell redraw or idle-prompt posture on window 0.

After a runtime-controlled headless turn reaches terminal state, the runtime SHALL leave the stable primary surface attachable as the idle `agent` window for the next controlled turn.

Turn identity, stdout, stderr, exit status, and process metadata SHALL remain per-turn durable artifacts on disk rather than being encoded through tmux window allocation.

#### Scenario: Active headless turn runs on the primary agent surface
- **WHEN** the runtime starts a controlled turn for a tmux-backed headless session
- **THEN** that turn executes on the stable window-0 agent surface
- **AND THEN** rolling output remains visible on that same primary surface
- **AND THEN** the runtime does not create a separate per-turn tmux window for that turn

#### Scenario: Process exit finalizes terminal headless turn state
- **WHEN** the managed child process for a runtime-controlled tmux-backed headless turn exits and the backend qualifies that exit and its terminal artifacts as execution settlement
- **THEN** the runtime writes the durable terminal artifact state for that turn, including the exit-status artifact
- **AND THEN** the runtime treats that turn as terminal from those artifacts without waiting for an idle shell redraw on window 0
- **AND THEN** later inspection can reconcile that turn as completed or failed from the durable artifacts

#### Scenario: Primary agent surface remains reusable after a controlled turn completes
- **WHEN** a runtime-controlled headless turn completes on the stable primary surface
- **THEN** the runtime leaves window 0 attachable as the `agent` surface
- **AND THEN** the next controlled turn can reuse that same primary surface without allocating a new tmux window

#### Scenario: Runtime-controlled headless turns do not overlap in one session
- **WHEN** one runtime-controlled headless turn is already active for a tmux-backed session
- **AND WHEN** another runtime-controlled prompt is addressed to that same live session before the first turn reaches terminal state
- **THEN** the runtime does not start a second overlapping CLI execution for that session
- **AND THEN** window 0 remains the only runtime-controlled execution surface for that headless agent

#### Scenario: Hermes Client Exits Before Native Settlement

- **WHEN** the finite Hermes CLI exits and the runtime cannot attribute a native terminal outcome
- **THEN** the runtime saves the CLI artifacts and retains the active or uncertain turn record
- **AND THEN** the next managed CLI does not start until the native work is settled or explicitly reconciled
