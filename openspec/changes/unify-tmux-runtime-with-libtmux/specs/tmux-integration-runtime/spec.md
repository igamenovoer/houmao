# Tmux Integration Runtime Delta

## MODIFIED Requirements

### Requirement: Repo-owned tmux integration is libtmux-first
The repository SHALL use one shared libtmux-backed integration layer for Python tmux discovery, lookup, capture, control, and lifecycle operations. The layer SHALL use libtmux's object API when it preserves the operation's contract and libtmux command dispatch for missing fields, flags, or checked results. Direct tmux processes SHALL be limited to documented cases that require process behavior libtmux cannot provide.

#### Scenario: Acceptance criteria

- **GIVEN** a repo-owned Python flow performs a tmux operation
- **THEN** the shared integration layer binds the operation to the selected tmux server
- **AND THEN** a direct tmux process is used only for a documented capability gap

#### Scenario: Session lookup uses libtmux objects
- **WHEN** repo-owned runtime code needs to resolve a live tmux session and enumerate its panes
- **THEN** it uses the shared libtmux-backed integration layer
- **AND THEN** the layer uses checked libtmux command dispatch if the object API loses information needed to verify the result

#### Scenario: Missing high-level field falls back through libtmux command dispatch
- **WHEN** repo-owned code needs tmux data such as a format field that libtmux does not expose directly as a first-class property
- **THEN** it issues the fallback query through libtmux-owned command dispatch bound to the relevant server, session, window, or pane object

#### Scenario: Prompt buffer load requires process stdin
- **WHEN** the runtime loads a prompt as tmux buffer data from standard input
- **THEN** the shared layer can invoke the native buffer loader on the selected server
- **AND THEN** the prompt text is carried through standard input and stays out of command arguments

### Requirement: Primary managed-agent surface keeps window zero contract and persists tmux object handles
The runtime SHALL treat window index `0` as the primary window of a Houmao-owned managed-agent session. The session manifest's `tmux` section SHALL provide the authoritative socket, session, and primary window and pane handles. Serialized copies of those coordinates SHALL be derived from that binding.

#### Scenario: Acceptance criteria

- **GIVEN** a valid binding to the managed primary pane or window
- **THEN** runtime control, capture, prompt submission, interruption, and health checks target that pane or window by its tmux id

#### Scenario: Fresh launch under one-based tmux defaults records primary handles
- **WHEN** tmux is configured so a newly created session starts with window index `1` and pane index `1`
- **AND WHEN** Houmao creates a tmux-backed managed-agent session
- **THEN** the runtime establishes the managed-agent primary window at index `0`
- **AND THEN** it records the owner socket and session with the live primary window and pane ids for later operations

#### Scenario: Runtime operation targets the persisted pane id
- **WHEN** a managed-agent manifest contains primary pane id `%7` for tmux session `HOUMAO-worker`
- **AND WHEN** Houmao sends prompt text, capture requests, or interrupt control to the primary managed-agent surface
- **THEN** the tmux operation targets `%7` on the manifest's socket
- **AND THEN** the operation does not depend on reconstructing `HOUMAO-worker:0.0`

#### Scenario: The manifest binds the operation to one server
- **WHEN** two tmux servers have sessions with the same name and overlapping window and pane ids
- **AND WHEN** the caller runs inside the server that does not own the managed agent
- **THEN** the runtime observes and addresses only the manifest's server for that agent

#### Scenario: Publishing terminal coordinates uses one binding
- **WHEN** the runtime writes a managed manifest or publishes registry terminal coordinates
- **THEN** the corresponding provider and registry projections use the same authoritative binding

### Requirement: Primary tmux handles are validated against the window zero authority before use
The runtime SHALL validate saved primary handles against a checked observation of the owning socket, session, and window `0`. Read-only observations SHALL leave saved bindings unchanged. An owner-authorized operation MAY repair absent or stale handles before continuing, provided the replacement pane is unique and actionable and the expected binding and generation are still current.

#### Scenario: Acceptance criteria

- **GIVEN** the primary window authority is absent or ambiguous or has no actionable primary pane
- **THEN** the requested primary-pane operation fails explicitly and leaves the saved binding unchanged

#### Scenario: Stale pane id is refreshed from primary window zero
- **WHEN** a managed-agent manifest contains stale primary pane id `%7`
- **AND WHEN** the owner requests a control operation that allows repair and observes a single actionable managed-agent pane in window index `0`
- **THEN** the runtime refreshes the saved primary window and pane ids together
- **AND THEN** the requested operation continues against the refreshed pane id

#### Scenario: Missing primary window fails closed
- **WHEN** a managed-agent manifest references tmux session `HOUMAO-worker`
- **AND WHEN** the tmux session exists but has no window index `0`
- **THEN** the runtime reports degraded or stale primary tmux authority
- **AND THEN** it does not choose another window only because that window is current or active

#### Scenario: Read-only inspection reports a stale binding
- **WHEN** a read-only operation observes a replacement pane in the primary window
- **THEN** it can report the observed pane and the stale saved binding
- **AND THEN** the manifest and registry are unchanged

#### Scenario: A newer generation or binding wins a repair race
- **WHEN** an owner-authorized repair has observed a replacement pane
- **AND WHEN** the manifest generation or primary binding changes before the repair is committed
- **THEN** the repair based on the old observation cannot overwrite the current binding or act through the proposed replacement pane

## ADDED Requirements

### Requirement: Tmux failures remain distinguishable from target absence
The shared runtime SHALL report target absence only when the result confirms it. Socket access failures, command failures without conclusive evidence, and invalid observations SHALL remain distinguishable from absence. A failed observation SHALL prevent implicit repair or retargeting.

#### Scenario: An inaccessible socket gives no evidence that the target is missing
- **WHEN** a query against the owning socket fails without confirming target absence, including a nonzero exit with empty output
- **THEN** the runtime reports a failed observation and retains the saved binding

#### Scenario: A checked observation confirms an absent target
- **WHEN** a successful observation of the relevant session or server confirms the requested target is absent
- **THEN** the runtime reports the target as missing

#### Scenario: A checked mutation fails without stderr
- **WHEN** a tmux mutation returns a nonzero status with empty stderr
- **THEN** the runtime reports the mutation failure and does not treat it as successful or replay it against another target
