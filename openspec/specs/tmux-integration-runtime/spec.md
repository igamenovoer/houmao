## Purpose
Define the repo-owned tmux integration boundary for libtmux-backed discovery, explicit surface resolution, and bounded fallback command usage.
## Requirements
### Requirement: Repo-owned tmux integration is libtmux-first
The repository SHALL use a repo-owned libtmux-backed integration layer as the primary interface for tmux session, window, and pane discovery, lookup, capture, and control.

When a repo-owned tmux-facing flow needs tmux data or commands not exposed directly by libtmux's higher-level object API, it SHALL issue that fallback through libtmux-owned command dispatch such as `Server.cmd()` or object-bound `Session.cmd()`, `Window.cmd()`, or `Pane.cmd()` rather than introducing unrelated raw tmux subprocess call sites when practical.

#### Scenario: Session lookup uses libtmux objects
- **WHEN** repo-owned runtime code needs to resolve a live tmux session and enumerate its panes
- **THEN** it uses the repo-owned libtmux-backed integration layer rather than composing raw `tmux list-*` subprocess calls ad hoc

#### Scenario: Missing high-level field falls back through libtmux command dispatch
- **WHEN** repo-owned code needs tmux data such as a format field that libtmux does not expose directly as a first-class property
- **THEN** it issues the fallback query through libtmux-owned command dispatch bound to the relevant server, session, window, or pane object
- **AND THEN** the fallback does not require inventing a separate raw subprocess-based tmux integration path

### Requirement: Session-scoped pane enumeration spans the full session
When a repo-owned tmux-facing flow asks for panes in a tmux session, that enumeration SHALL span all panes in the addressed session, including panes in non-current windows.

The system SHALL NOT treat a bare session target as permission to inspect only the current tmux window when the workflow contract is session-scoped pane discovery.

#### Scenario: Auxiliary pane in a non-current window remains discoverable
- **WHEN** tmux session `S` has current window `0` and another live pane in auxiliary window `1`
- **THEN** a session-scoped pane enumeration for `S` returns panes from both windows
- **AND THEN** the pane in window `1` is not hidden merely because window `0` is current

### Requirement: Explicit tmux surface identity outranks current-focus heuristics
When a repo-owned tmux-facing flow must observe or control a specific tmux surface, it SHALL resolve that surface from explicit pane or window identity before considering current active-window or active-pane state.

Current-focus heuristics MAY be used only when the workflow contract explicitly means the current operator focus or when the session has exactly one unambiguous candidate pane.

#### Scenario: Stored window identity wins over current focus
- **WHEN** a tmux-backed workflow stores the contractual target as pane `%1` or window `1`
- **AND WHEN** another window in the same session becomes current
- **THEN** the workflow continues observing or controlling the stored target surface
- **AND THEN** it does not silently rebind to the current active window

#### Scenario: Ambiguous multi-pane session does not guess from current focus
- **WHEN** a tmux-backed workflow needs one specific surface in a session that has multiple candidate panes
- **AND WHEN** the workflow has no explicit pane or window identity for that contract
- **THEN** the workflow fails explicitly or remains in a non-authoritative diagnostic posture
- **AND THEN** it does not silently guess from the current active pane

### Requirement: Operator-facing tmux handoff is interactivity-aware and libtmux-backed
When repo-owned Houmao code needs to hand an operator terminal off to a tmux session after a successful managed launch, it SHALL resolve the session through the repo-owned libtmux-backed tmux integration layer rather than composing an ad hoc raw `tmux attach-session` subprocess call.

If libtmux does not expose a first-class attach helper for the needed session handoff, the implementation SHALL use libtmux-owned command dispatch bound to the resolved tmux server or session object rather than introducing a separate unrelated raw tmux subprocess path.

Before attempting tmux attach, the handoff flow SHALL determine whether the caller provides a usable interactive terminal. When the caller is non-interactive, the handoff flow SHALL skip the attach attempt and return or report tmux session coordinates for manual follow-up instead of surfacing raw tmux `not a terminal` output as a launch failure.

#### Scenario: Interactive caller uses libtmux-backed session handoff
- **WHEN** a repo-owned managed launch flow needs to attach an interactive caller to tmux session `S`
- **AND WHEN** the caller provides a usable interactive terminal
- **THEN** the flow resolves session `S` through the repo-owned libtmux integration layer
- **AND THEN** any resulting attach command is issued through libtmux-owned command dispatch rather than through an unrelated raw tmux subprocess helper

#### Scenario: Non-interactive caller skips attach and reports follow-up coordinates
- **WHEN** a repo-owned managed launch flow finishes starting tmux session `S`
- **AND WHEN** the caller does not provide a usable interactive terminal
- **THEN** the flow does not attempt a tmux attach that would fail only because the caller is non-interactive
- **AND THEN** it reports the tmux session coordinates needed for a later manual attach

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
