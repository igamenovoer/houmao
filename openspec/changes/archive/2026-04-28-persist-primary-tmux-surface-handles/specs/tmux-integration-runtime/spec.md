## ADDED Requirements

### Requirement: Primary managed-agent surface keeps window zero contract and persists tmux object handles
For Houmao-owned tmux-backed managed-agent sessions, the runtime SHALL treat tmux window index `0` as the contractual primary managed-agent window.

The runtime SHALL persist the live tmux object handles for the primary surface when they are known, including the primary window id and primary pane id.

Runtime control, capture, prompt submission, interruption, and health checks SHALL prefer the persisted primary pane id or window id over reconstructed textual targets such as `session:0.0` when the persisted handle is valid.

#### Scenario: Fresh launch under one-based tmux defaults records primary handles
- **WHEN** tmux is configured so a newly created session starts with window index `1` and pane index `1`
- **AND WHEN** Houmao creates a tmux-backed managed-agent session
- **THEN** the runtime establishes the managed-agent primary window at index `0`
- **AND THEN** it records the live primary tmux window id and primary tmux pane id for later operations

#### Scenario: Runtime operation targets the persisted pane id
- **WHEN** a managed-agent manifest contains primary pane id `%7` for tmux session `HOUMAO-worker`
- **AND WHEN** Houmao sends prompt text, capture requests, or interrupt control to the primary managed-agent surface
- **THEN** the tmux operation targets `%7`
- **AND THEN** the operation does not depend on reconstructing `HOUMAO-worker:0.0`

### Requirement: Primary tmux handles are validated against the window zero authority before use
Before using persisted primary tmux handles, the runtime SHALL verify that the referenced pane or window still exists in the expected tmux session and still belongs to the contractual primary window index `0`.

If persisted handles are absent or stale, the runtime SHALL attempt to resolve a replacement from the contractual primary window authority. When that replacement is found unambiguously, the runtime SHALL refresh the persisted handles before continuing.

If the primary window authority is missing, ambiguous, or does not contain an actionable primary pane, the runtime SHALL fail explicitly rather than rebinding to the current tmux focus.

#### Scenario: Stale pane id is refreshed from primary window zero
- **WHEN** a managed-agent manifest contains stale primary pane id `%7`
- **AND WHEN** tmux session `HOUMAO-worker` still contains a single actionable managed-agent pane in window index `0`
- **THEN** the runtime refreshes the persisted primary pane id from the live window `0` surface
- **AND THEN** the requested operation continues against the refreshed pane id

#### Scenario: Missing primary window fails closed
- **WHEN** a managed-agent manifest references tmux session `HOUMAO-worker`
- **AND WHEN** the tmux session exists but has no window index `0`
- **THEN** the runtime reports degraded or stale primary tmux authority
- **AND THEN** it does not choose another window only because that window is current or active
