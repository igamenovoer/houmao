## ADDED Requirements

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
