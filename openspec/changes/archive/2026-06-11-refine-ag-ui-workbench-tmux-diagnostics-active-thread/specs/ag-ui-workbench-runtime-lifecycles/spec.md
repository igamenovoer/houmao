## MODIFIED Requirements

### Requirement: Runtime owns shared tmux inventory freshness
The workbench runtime SHALL maintain tmux status, session list, and tmux-related discovered-agent data as a shared runtime-owned inventory for tmux panes.

Runtime effects SHALL refresh tmux inventory when one or more tmux panes explicitly need current inventory, including when the user opens a tmux session combobox, when the user requests refresh, and when a tmux attachment exits, closes, or errors.

Runtime effects SHALL NOT keep a recurring tmux inventory poller active solely because a tmux pane is open.

The runtime SHALL avoid overlapping tmux inventory requests by canceling, coalescing, or ignoring obsolete requests.

#### Scenario: One inventory state serves multiple tmux panes
- **WHEN** two tmux panes exist in one workbench runtime
- **AND WHEN** either pane opens or refreshes the tmux session combobox
- **THEN** runtime effects refresh one shared tmux inventory
- **AND THEN** both panes render tmux status, sessions, discovered agents, loading state, and errors from runtime-derived inventory state

#### Scenario: No poller runs for closed dropdowns
- **WHEN** a tmux pane is open but no tmux session combobox is open and no tmux attachment exit is pending
- **THEN** runtime effects do not keep a recurring tmux inventory timer solely for that pane

#### Scenario: Open and manual refresh update inventory
- **WHEN** at least one tmux pane exists
- **AND WHEN** the user opens the tmux session combobox or activates manual tmux refresh
- **THEN** the runtime requests current tmux inventory from the tmux service

#### Scenario: Attach exit refreshes inventory on demand
- **WHEN** a tmux attachment exits, closes, or errors
- **THEN** runtime effects request current tmux inventory
- **AND THEN** selectors expose the refreshed sessions when the next tmux session picker is shown

## ADDED Requirements

### Requirement: Runtime models unsupported active-thread gateways
The workbench runtime SHALL distinguish unsupported active-thread gateways from transient active-thread request failures.

When an active-thread read returns a deterministic unsupported-route response such as `404` or `405`, the runtime SHALL mark that gateway active-thread state as unsupported.

Unsupported active-thread state SHALL stop further active-thread polling for the affected gateway until the target or normalized gateway key changes.

Runtime selectors SHALL expose unsupported active-thread state separately from inactive, active, polling, and transient error states.

The runtime SHALL NOT dispatch active-thread set or clear mutations for a gateway while that gateway is known to be unsupported.

#### Scenario: Unsupported active-thread response stops lifecycle
- **WHEN** active-thread polling for a discovered gateway receives a `404` or `405` response from `/active-thread`
- **THEN** the runtime records unsupported active-thread state for that gateway
- **AND THEN** the runtime stops that gateway's active-thread poll lifecycle until a new target or gateway key is registered

#### Scenario: Unsupported state is visible through selectors
- **WHEN** a pane targets a gateway whose active-thread state is unsupported
- **THEN** runtime selectors expose an unsupported active-thread presentation state for that pane
- **AND THEN** the selector does not report the pane as inactive due only to unsupported active-thread routing

#### Scenario: Target change clears unsupported classification
- **WHEN** a pane retargets from an unsupported active-thread gateway to a different normalized gateway key
- **THEN** the runtime treats the new gateway key as a fresh active-thread lifecycle
- **AND THEN** prior unsupported state does not suppress polling for the new gateway key
