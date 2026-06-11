## ADDED Requirements

### Requirement: Agent picker refreshes discovery when opened
The workbench agent picker SHALL request the current discovered-agent list from the configured passive-server base URL whenever the picker is opened.

The picker SHALL show loading and error states for the open-triggered refresh using the same visible discovery state as manual refresh.

The picker SHALL ignore stale auto-refresh responses after the picker closes, the passive-server base URL changes, or a newer discovery request supersedes the earlier one.

Manual refresh SHALL remain available after automatic refresh is added.

#### Scenario: Toolbar picker auto-refreshes agents
- **WHEN** a tester opens the agent picker from the global toolbar
- **THEN** the workbench requests discovered agents from the configured passive server
- **AND THEN** the picker displays the returned agents without requiring a separate refresh click

#### Scenario: Pane picker auto-refreshes agents
- **WHEN** a tester opens the agent picker from an existing pane target form
- **THEN** the workbench requests discovered agents from the configured passive server
- **AND THEN** the picker still defaults selection behavior to retargeting that pane

#### Scenario: Stale picker refresh is ignored
- **WHEN** the picker opens and starts a discovered-agent refresh
- **AND WHEN** the picker is closed or reopened with a different passive-server base URL before the response returns
- **THEN** the obsolete response does not replace the picker state for the newer request

### Requirement: Agent picker creates blank manual panes
The agent picker SHALL provide a New action for creating a blank docked agent pane with manual target configuration.

When the picker is opened from the toolbar, the New action SHALL create a new blank pane without requiring a discovered-agent row selection.

When the picker is opened from an existing pane for retargeting, the New action SHALL remain distinct from selecting a discovered row and SHALL NOT retarget the requesting pane.

#### Scenario: New creates blank pane from toolbar picker
- **WHEN** a tester opens the picker from the toolbar
- **AND WHEN** the tester activates New
- **THEN** the workbench creates a new docked agent pane
- **AND THEN** the pane uses manual target metadata rather than a selected discovered-agent target

#### Scenario: New does not retarget existing pane
- **WHEN** a tester opens the picker from pane `agent-1`
- **AND WHEN** the tester activates New
- **THEN** the workbench creates a separate new docked agent pane
- **AND THEN** pane `agent-1` keeps its current target configuration
