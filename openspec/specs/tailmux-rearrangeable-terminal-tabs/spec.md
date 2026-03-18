# tailmux-rearrangeable-terminal-tabs Specification

## Purpose
Define the Dockview-based browser tab workspace for Tailmux, including reorder behavior, session continuity, action targeting, reload restore, and layout reset behavior.

## Requirements

### Requirement: Browser terminal tabs are freely rearrangeable within one workspace group
Tailmux SHALL expose browser terminal tabs through a workspace that allows users to reorder tabs by drag and drop, activate any tab directly from the workspace, and close tabs from the workspace surface.

During this change, the workspace SHALL remain limited to a single visible tab group and SHALL NOT create split views, floating groups, or other multi-panel layouts.

#### Scenario: User reorders terminal tabs
- **WHEN** a user drags one terminal tab to a different position in the workspace tab strip
- **THEN** the workspace updates the tab order to match the drop position
- **AND THEN** the reordered tab remains part of the same visible tab group

#### Scenario: Split-style docking is deferred in this change
- **WHEN** a user attempts a drag/drop operation that would create a split or separate visible workspace group
- **THEN** Tailmux does not create a multi-panel layout
- **AND THEN** the workspace remains a single visible tab group

### Requirement: Reordering and activation preserve terminal session continuity
Tailmux SHALL preserve the underlying terminal session, terminal buffer, and browser-side terminal state when a tab is reordered or when the active workspace tab changes.

Reordering or activating a tab SHALL NOT recreate the session transport solely because of the workspace move.

#### Scenario: Dragging a connected tab does not reconnect it
- **WHEN** a connected terminal tab is reordered within the workspace
- **THEN** the terminal session remains associated with the same session identity
- **AND THEN** Tailmux does not create a replacement session solely because of the reorder

#### Scenario: Activating a different tab preserves the previously hidden terminal
- **WHEN** a user switches from one terminal tab to another and later returns to the first tab
- **THEN** the original tab still shows its existing terminal state
- **AND THEN** Tailmux does not treat the visibility change as a session close/recreate cycle

### Requirement: Workspace-scoped actions target the active terminal tab
Tailmux SHALL derive the active browser terminal session from the active workspace tab and SHALL route tab-scoped actions through that active session.

Tab-scoped actions include header buttons, dashboard switch/close behavior, and mobile keyboard or tmux controls.

#### Scenario: Header tmux action follows the active workspace tab
- **WHEN** a user activates a tmux-backed tab in the workspace and triggers a header tmux action
- **THEN** Tailmux applies that action to the active tmux-backed tab
- **AND THEN** it does not apply the action to a previously active browser tab

#### Scenario: Dashboard switch activates the requested workspace tab
- **WHEN** a user chooses a session from the dashboard
- **THEN** the corresponding workspace tab becomes active
- **AND THEN** subsequent tab-scoped actions target that activated session

### Requirement: Restorable workspace tabs and ordering survive browser reload
Tailmux SHALL persist workspace ordering and active-tab metadata together with enough session metadata to restore restorable workspace tabs after a browser reload.

For this change, tmux-backed tabs created in `tmux` or `attach` mode SHALL be restorable by session metadata. Ephemeral shell tabs created in `new` mode SHALL NOT be required to restore after reload.

#### Scenario: tmux-backed tabs restore in their prior order
- **WHEN** a user has multiple tmux-backed tabs arranged in a custom order and reloads the browser
- **THEN** Tailmux restores those tabs in the persisted workspace order
- **AND THEN** the persisted active tab becomes active again when its session can be restored

#### Scenario: Non-restorable shell tab does not block workspace recovery
- **WHEN** a persisted workspace includes a non-restorable shell tab and the browser reloads
- **THEN** Tailmux restores the restorable tabs that remain recoverable
- **AND THEN** it surfaces one summary notification that the shell tab or tabs were not restored instead of failing the entire workspace restore

### Requirement: Users can reset persisted workspace layout state
Tailmux SHALL provide a user-visible reset-layout action that clears the persisted workspace layout and restore metadata used by browser reload recovery.

Using that action SHALL reset future reload recovery to the default non-restored workspace behavior for the current browser storage context.

#### Scenario: Reset layout clears persisted workspace state
- **WHEN** a user triggers the reset-layout action from the Tailmux UI
- **THEN** Tailmux clears the persisted workspace layout and restore metadata for that browser storage context
- **AND THEN** the workspace reloads or reopens without reusing the cleared persisted layout state
