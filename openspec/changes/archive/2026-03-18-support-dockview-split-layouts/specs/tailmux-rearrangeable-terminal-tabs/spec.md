## MODIFIED Requirements

### Requirement: Browser terminal tabs are freely rearrangeable across workspace groups
Tailmux SHALL expose browser terminal tabs through a workspace that allows users to reorder tabs by drag and drop, create vertical or horizontal split layouts by docking tabs into edge positions, move tabs between visible groups, activate any tab directly from the workspace, and close tabs from the workspace surface.

The workspace SHALL allow multiple visible Dockview groups and SHALL NOT collapse a valid split layout back into a single visible group. The workspace SHALL NOT create floating groups or pop-out groups in this change.

#### Scenario: User reorders terminal tabs inside a group
- **WHEN** a user drags one terminal tab to a different position in the same workspace tab strip
- **THEN** the workspace updates the tab order to match the drop position
- **AND THEN** the reordered tab remains in that visible workspace group

#### Scenario: User creates a side-by-side split
- **WHEN** a user drags a terminal tab to the left, right, top, or bottom docking region of another visible group
- **THEN** Tailmux creates a new visible workspace group in the requested split direction
- **AND THEN** both groups remain visible at the same time

#### Scenario: User moves a tab between existing groups
- **WHEN** a user drags a terminal tab from one visible workspace group into another existing group
- **THEN** the tab becomes part of the destination group
- **AND THEN** the source and destination groups remain otherwise intact

#### Scenario: Moving the last tab out of a group does not leave an empty visible group
- **WHEN** a user drags the last remaining tab out of a visible workspace group into a different split position
- **THEN** Tailmux does not leave behind an empty visible workspace group
- **AND THEN** only occupied workspace groups remain visible after the move

#### Scenario: Split creation remains docked within the workspace
- **WHEN** a user rearranges terminal tabs to create additional visible panes
- **THEN** Tailmux creates only docked workspace groups inside the current workspace
- **AND THEN** it does not create floating or pop-out layouts

### Requirement: Reordering and activation preserve terminal session continuity
Tailmux SHALL preserve the underlying terminal session, terminal buffer, and browser-side terminal state when a tab is reordered within a group, moved between groups, docked into a split, or when the active workspace pane changes.

Reordering, moving, or activating a tab SHALL NOT recreate the session transport solely because of the workspace layout change.

#### Scenario: Dragging a connected tab into a split does not reconnect it
- **WHEN** a connected terminal tab is moved into a new split group
- **THEN** the terminal session remains associated with the same session identity
- **AND THEN** Tailmux does not create a replacement session solely because of the move

#### Scenario: Moving a tab between groups preserves terminal state
- **WHEN** a user moves a terminal tab from one visible group to another and later interacts with it again
- **THEN** the tab still shows its existing terminal state
- **AND THEN** Tailmux does not treat the group change as a session close or recreate cycle

#### Scenario: Switching focus between visible panes preserves both sessions
- **WHEN** two or more terminal panes are visible and a user changes focus from one pane to another
- **THEN** the newly focused pane becomes active for interaction
- **AND THEN** the previously focused pane remains connected unless its own session ends

### Requirement: Workspace-scoped actions target the active terminal tab
Tailmux SHALL derive the active browser terminal session from the currently focused workspace panel and SHALL route tab-scoped actions through that active session even when multiple terminal panes are visible at the same time.

Tab-scoped actions include header buttons, dashboard switch and close behavior, and mobile keyboard or tmux controls. For this change, the dashboard SHALL remain a flat session list even when sessions are distributed across multiple visible groups.

#### Scenario: Header tmux action follows the focused split pane
- **WHEN** a user focuses a tmux-backed terminal pane in a split layout and triggers a header tmux action
- **THEN** Tailmux applies that action to the focused tmux-backed pane
- **AND THEN** it does not apply the action to a different visible pane

#### Scenario: Clicking inside a visible pane updates the action target
- **WHEN** multiple terminal panes are visible and a user clicks or focuses one pane's terminal content
- **THEN** that pane becomes the active session target for workspace-scoped actions
- **AND THEN** subsequent keyboard and toolbar actions use that pane's session

#### Scenario: Dashboard switch activates a tab in another visible group
- **WHEN** a user chooses a session from the flat dashboard list and that session belongs to a different visible workspace group
- **THEN** the corresponding workspace tab becomes active in its group
- **AND THEN** subsequent tab-scoped actions target that activated session

### Requirement: Restorable workspace tabs and ordering survive browser reload
Tailmux SHALL persist workspace layout metadata together with enough session metadata to restore restorable workspace tabs after a browser reload, including their split-group arrangement and previously focused session when recoverable.

For this change, tmux-backed tabs created in `tmux` or `attach` mode SHALL be restorable by session metadata and layout position. Ephemeral shell tabs created in `new` mode SHALL NOT be required to restore after reload.

#### Scenario: tmux-backed tabs restore in their prior split layout
- **WHEN** a user has multiple tmux-backed tabs arranged across visible split groups and reloads the browser
- **THEN** Tailmux restores those tabs into the persisted workspace layout
- **AND THEN** the previously focused restored tab becomes active again when its session can be restored

#### Scenario: Non-restorable shell tab does not block split layout recovery
- **WHEN** a persisted split workspace includes a non-restorable shell tab and the browser reloads
- **THEN** Tailmux restores the restorable tabs that remain recoverable into the remaining layout structure
- **AND THEN** it surfaces one summary notification that the shell tab or tabs were not restored instead of failing the workspace restore

### Requirement: Users can reset persisted workspace layout state
Tailmux SHALL provide a user-visible reset-layout action that clears the persisted workspace layout and restore metadata used by browser reload recovery, including any saved split-group arrangement.

Using that action SHALL reset future reload recovery to the default non-restored workspace behavior for the current browser storage context.

#### Scenario: Reset layout clears persisted split workspace state
- **WHEN** a user triggers the reset-layout action from the Tailmux UI
- **THEN** Tailmux clears the persisted workspace layout and restore metadata for that browser storage context
- **AND THEN** the workspace reloads or reopens without reusing the cleared split layout state
