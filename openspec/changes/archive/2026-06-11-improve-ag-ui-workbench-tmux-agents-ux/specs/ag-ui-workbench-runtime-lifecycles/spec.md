## ADDED Requirements

### Requirement: Runtime owns shared tmux inventory freshness
The workbench runtime SHALL maintain tmux status, session list, and tmux-related discovered-agent data as a shared runtime-owned inventory for open tmux panes.

Runtime effects SHALL keep at most one tmux inventory poller active per browser workbench runtime instance.

The inventory poller SHALL start when one or more tmux panes need tmux inventory and SHALL stop when no tmux panes need tmux inventory or when the runtime is disposed.

The runtime SHALL refresh tmux inventory immediately when a tmux pane opens, when a user requests refresh, when the browser regains focus while tmux panes are open, and when a tmux attachment exits or disconnects.

The runtime SHALL avoid overlapping tmux inventory requests by canceling, coalescing, or ignoring obsolete requests.

#### Scenario: One poller serves multiple tmux panes
- **WHEN** two tmux panes are open
- **THEN** runtime effects use one shared tmux inventory poller for both panes
- **AND THEN** both panes render tmux status, sessions, discovered agents, loading state, and errors from runtime-derived inventory state

#### Scenario: Poller stops after last tmux pane closes
- **WHEN** the last open tmux pane is closed
- **THEN** runtime effects stop tmux inventory polling
- **AND THEN** runtime teardown has no remaining tmux inventory timer for closed panes

#### Scenario: Focus and manual refresh update inventory
- **WHEN** at least one tmux pane is open
- **AND WHEN** the user requests refresh or the browser regains focus
- **THEN** the runtime requests current tmux inventory from the tmux service

### Requirement: Tmux attach exit refreshes inventory without controlling sessions
When a tmux attach WebSocket reports terminal process exit, closes, or errors, runtime effects SHALL close that attachment, update the pane attachment status, unregister or ignore obsolete output sinks, and request a tmux inventory refresh.

The runtime SHALL NOT send tmux kill-session, Houmao stop, restart, shutdown, interrupt, launch, registry cleanup, or prompt-control requests as part of attach-exit handling.

Raw terminal output SHALL continue to flow only through the registered ephemeral terminal sink and SHALL NOT be persisted in reduced runtime state.

#### Scenario: Attach exit removes dead session through inventory refresh
- **WHEN** a tmux attach WebSocket for session `HOUMAO-alpha` reports an exit
- **THEN** the runtime marks the pane attachment disconnected
- **AND THEN** the runtime requests tmux inventory refresh
- **AND THEN** if the refreshed inventory no longer contains `HOUMAO-alpha`, selectors no longer expose that session in tmux session lists

#### Scenario: Attach close does not kill session
- **WHEN** the browser tmux attachment socket closes for session `HOUMAO-beta`
- **THEN** runtime effects clean up the browser attachment resources
- **AND THEN** runtime effects do not issue a tmux or Houmao lifecycle command to kill or stop `HOUMAO-beta`
