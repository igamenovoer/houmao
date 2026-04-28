## ADDED Requirements

### Requirement: Joined tmux sessions persist primary surface handles without changing adoption authority
`houmao-mgr agents join` SHALL continue to treat tmux window `0`, pane `0` as the canonical adopted agent surface for both TUI and headless joins.

On successful join, the command SHALL persist the live tmux window id and pane id for the adopted primary surface so later managed-agent operations can target the adopted pane by object handle.

The join workflow SHALL NOT silently move, rename, or reindex operator-owned tmux windows or panes to satisfy the adoption contract.

#### Scenario: TUI join stores handles for the adopted primary pane
- **WHEN** an operator runs `houmao-mgr agents join --agent-name coder` inside a tmux session whose window `0`, pane `0` hosts a supported provider TUI
- **THEN** the command adopts that surface without restarting the provider process
- **AND THEN** the resulting manifest records the adopted primary window id and pane id
- **AND THEN** later managed-agent operations prefer the recorded pane id over current tmux focus

#### Scenario: Join still fails when the canonical adopted pane is missing
- **WHEN** an operator runs `houmao-mgr agents join --agent-name coder` inside a tmux session that has no window `0`, pane `0`
- **THEN** the command fails with an explicit adoption-authority error
- **AND THEN** it does not move another window or pane into the primary slot as part of join
