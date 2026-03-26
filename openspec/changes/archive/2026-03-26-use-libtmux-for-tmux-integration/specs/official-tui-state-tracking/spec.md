## ADDED Requirements

### Requirement: Multi-window tracked TUI sessions resolve an explicit observation surface
For tmux-backed tracked TUI sessions, when the active control plane has explicit pane or window identity for the intended observed surface, it SHALL resolve capture and process inspection from that explicit tmux surface rather than from current-window or current-pane heuristics.

Session-scoped tmux pane discovery used by the active control plane SHALL span all panes in the tracked session, including panes in non-current windows.

When multiple candidate panes exist and the tracked contract does not include explicit pane or window identity for the intended surface, the active control plane SHALL fail explicitly or surface non-authoritative diagnostics rather than silently rebinding to the current active window.

#### Scenario: Tracked local interactive session stays bound to the agent surface
- **WHEN** a tracked runtime-owned `local_interactive` session gains an auxiliary gateway window in the same tmux session
- **AND WHEN** the active control plane knows the contractual agent surface identity
- **THEN** live capture and process inspection continue targeting the agent surface
- **AND THEN** the tracking owner does not silently switch to the auxiliary gateway window because it became current

#### Scenario: Ambiguous tracked multi-window session does not guess from current focus
- **WHEN** a tracked tmux session has multiple candidate panes across multiple windows
- **AND WHEN** the tracked identity lacks explicit pane or window metadata for the intended observed surface
- **THEN** the active control plane reports an explicit targeting problem or remains non-authoritative for that cycle
- **AND THEN** it does not silently choose the current active window as the observed TUI surface
