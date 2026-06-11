## ADDED Requirements

### Requirement: Workbench has no dedicated operator tab
The workbench SHALL NOT create a dedicated `operator` pane by default.

The workbench SHALL NOT treat `operator` as a first-class pane kind for new panes.

An empty workbench MAY show the normal empty workspace state until the user opens an agent pane, Debug Agent pane, or tmux tab.

Legacy persisted `operator` pane records SHALL NOT force the dedicated Operator tab to reappear.

#### Scenario: Fresh workbench does not create operator tab
- **WHEN** a developer opens a fresh workbench with no saved docked layout
- **THEN** the workbench does not create an Operator tab
- **AND THEN** the developer can open agent, Debug Agent, or tmux tabs from explicit workbench controls

#### Scenario: Empty workspace does not recreate operator tab
- **WHEN** a developer closes the last visible pane in the workbench
- **THEN** the workbench does not automatically create an Operator tab
- **AND THEN** the workbench remains usable through explicit tab-opening controls

#### Scenario: Legacy operator pane does not reappear
- **WHEN** localStorage contains a legacy persisted operator pane record
- **AND WHEN** the workbench loads the saved state
- **THEN** the workbench does not force a dedicated Operator tab to appear

### Requirement: Operator role is an agent-pane designation
The workbench SHALL allow the user to designate at most one ordinary Houmao agent pane as the operator pane.

The operator designation SHALL be UI metadata only in this change.

The operator designation SHALL NOT change AG-UI request bodies, target resolution, watched-target behavior, gateway routing, prompt delivery, event caching, tmux attachment, or managed-agent lifecycle behavior.

Only panes targeting a discovered Houmao agent SHALL be eligible for the operator designation.

If the designated pane is closed or retargeted away from a discovered Houmao agent, the workbench SHALL clear the operator designation.

#### Scenario: User marks a Houmao agent pane as operator
- **WHEN** a developer has an ordinary agent pane targeting a discovered Houmao agent
- **AND WHEN** the developer activates the operator-designation control for that pane
- **THEN** the workbench marks that pane as the operator pane
- **AND THEN** no other pane is marked as operator

#### Scenario: Operator marker does not change AG-UI requests
- **WHEN** an operator-marked agent pane submits an AG-UI run or opens an AG-UI connect stream
- **THEN** the workbench sends the same protocol-minimal request shape used by an ordinary agent pane
- **AND THEN** the request does not include an operator role, operator flag, pane kind, or operator-specific forwarded props

#### Scenario: Operator marker clears when pane becomes ineligible
- **WHEN** a pane is marked as operator
- **AND WHEN** the pane is closed or retargeted to a manual/non-discovered target
- **THEN** the workbench clears the operator designation

### Requirement: Workbench binds the actively viewed AG-UI thread
The workbench SHALL set the target gateway's last-bound AG-UI thread when a discovered Houmao agent pane becomes the actively viewed foreground GUI target.

The workbench SHALL set the target gateway's last-bound AG-UI thread when the user changes the viewed thread for the actively viewed foreground agent pane.

The workbench SHALL NOT update the gateway's last-bound AG-UI thread merely because a background watcher, hidden pane, client event-cache listener, or passive reconnect opens an AG-UI stream.

When the active bound pane is closed or retargeted and no replacement foreground agent thread is active for that gateway, the workbench SHALL clear the gateway's last-bound AG-UI thread on a best-effort basis.

The workbench SHALL treat last-bound-thread updates as Houmao gateway extension calls, not as fields in standard AG-UI run or connect request bodies.

The workbench SHALL NOT set or clear the gateway's last-sent-thread state; that state is maintained by the gateway publish path.

#### Scenario: Foreground agent pane binds its thread
- **WHEN** a developer activates a discovered Houmao agent pane connected to a gateway
- **AND WHEN** the pane has a viewed AG-UI thread id
- **THEN** the workbench sends the gateway a last-bound-thread update for that thread id
- **AND THEN** a tmux-controlled agent using that gateway can publish AG-UI events without being given the thread id in prompt context

#### Scenario: Viewing another thread updates the binding
- **WHEN** a developer changes the viewed thread in the active foreground agent pane
- **THEN** the workbench updates the target gateway's last-bound-thread state to the newly viewed thread id

#### Scenario: Background listeners do not steal the binding
- **WHEN** the workbench has an active foreground agent pane bound to one thread
- **AND WHEN** a hidden pane, watched target, or cache listener reconnects to another thread on the same gateway
- **THEN** the gateway's last-bound-thread remains the foreground pane's viewed thread

#### Scenario: Closing the bound pane clears when no replacement is active
- **WHEN** the active foreground pane owns the gateway's last-bound thread
- **AND WHEN** the developer closes that pane without activating another agent pane for the same gateway
- **THEN** the workbench sends a best-effort request to clear the gateway's last-bound-thread state
- **AND THEN** the workbench does not mutate the gateway's last-sent-thread state

### Requirement: Workbench supports docked tmux tabs
The workbench SHALL provide a docked `tmux` pane kind for direct attachment to local tmux sessions.

Tmux tabs SHALL use the same Dockview workspace as agent and Debug Agent panes.

Tmux tabs SHALL be distinct from AG-UI panes and SHALL NOT send AG-UI connect, run, detach, stop, restart, shutdown, interrupt, or agent-memory-clear requests as part of tmux attachment.

#### Scenario: User can open a tmux tab
- **WHEN** a developer activates the workbench control for opening a tmux tab
- **THEN** the workbench creates a docked pane with kind `tmux`
- **AND THEN** the pane shows a tmux session picker when no session is attached

#### Scenario: Tmux tab stays inside docked workspace
- **WHEN** a developer moves a tmux tab within the workbench
- **THEN** the pane can be moved into an in-app tab group or split
- **AND THEN** the pane remains inside the main workbench browser page without Dockview floating groups or popout windows

#### Scenario: Tmux tab does not use AG-UI lifecycle
- **WHEN** a developer opens, attaches, detaches, or closes a tmux tab
- **THEN** the workbench does not send AG-UI run, AG-UI detach, Houmao stop, Houmao restart, Houmao shutdown, Houmao interrupt, or agent-memory-clear requests

### Requirement: Workbench lists and searches tmux sessions
The workbench SHALL provide a local tmux session picker for tmux tabs.

The picker SHALL list local tmux sessions available to the host running the workbench development server.

The picker SHALL support quick fuzzy search using Fuse.js.

The searchable fields SHALL include tmux session name and matched Houmao agent metadata when available, including agent name, agent id, tool, backend, and generation id.

The picker SHALL provide a checkbox filter that shows only tmux sessions matched to Houmao managed agents.

#### Scenario: Picker lists local tmux sessions
- **WHEN** tmux is available and the host has local tmux sessions
- **THEN** the tmux picker displays those sessions with at least session name, window count, attached status, and created time

#### Scenario: Picker degrades when tmux is unavailable
- **WHEN** tmux is unavailable on the host running the workbench development server
- **THEN** the tmux picker shows a deterministic unavailable or empty state
- **AND THEN** the workbench does not crash

#### Scenario: Search matches tmux and Houmao fields
- **WHEN** a developer enters a search query matching a session name or matched Houmao agent metadata
- **THEN** the tmux picker filters the visible sessions using Fuse.js fuzzy search
- **AND THEN** non-matching sessions are hidden while the query is active

#### Scenario: Houmao-only filter hides non-agent sessions
- **WHEN** the tmux picker has the Houmao-only checkbox enabled
- **THEN** the picker shows only tmux sessions whose session name matches a discovered Houmao agent `tmux_session_name`
- **AND THEN** tmux sessions without a matched Houmao agent are hidden

#### Scenario: Houmao-only filter handles discovery outage
- **WHEN** passive-server agent discovery is unavailable
- **AND WHEN** the Houmao-only checkbox is enabled
- **THEN** the picker shows a deterministic no-matched-Houmao-sessions or discovery-error state
- **AND THEN** disabling the checkbox still allows raw tmux sessions to be listed when tmux itself is available

### Requirement: Tmux tabs attach read-write or read-only
Tmux tabs SHALL attach to one selected local tmux session.

Read-write attachment SHALL be the default mode.

Read-only attachment SHALL be available through an explicit checkbox or equivalent binary control before attachment.

Read-only mode SHALL be enforced by both the browser terminal and the host tmux bridge.

#### Scenario: Default attachment is read-write
- **WHEN** a developer selects a tmux session and attaches without enabling read-only mode
- **THEN** the tmux tab attaches in read-write mode
- **AND THEN** keyboard input in the terminal is forwarded to the attached tmux session

#### Scenario: Read-only attachment does not forward input
- **WHEN** a developer enables read-only mode and attaches to a tmux session
- **THEN** the tmux tab displays terminal output from the session
- **AND THEN** keyboard input is not forwarded to the attached tmux session
- **AND THEN** crafted browser input messages for that read-only attachment are rejected or ignored by the host tmux bridge

#### Scenario: Attachment failure is visible
- **WHEN** the selected tmux session disappears before or during attachment
- **THEN** the tmux tab shows a deterministic attachment error
- **AND THEN** the rest of the workbench remains usable

### Requirement: Tmux tab close is browser-detach only
Closing or disconnecting a tmux tab SHALL close only the browser attachment to the tmux session.

The host tmux bridge SHALL clean up the spawned browser-client attach process for that tab.

Closing or disconnecting a tmux tab SHALL NOT kill the tmux session, detach unrelated tmux clients, mutate the shared registry, or control the managed Houmao agent lifecycle.

#### Scenario: Closing tab keeps tmux session alive
- **WHEN** a developer closes a tmux tab attached to a tmux session
- **THEN** the workbench closes the tab's browser attachment
- **AND THEN** the underlying tmux session remains alive

#### Scenario: Closing tab does not detach other clients
- **WHEN** a tmux session has another tmux client outside the workbench
- **AND WHEN** a developer closes the workbench tmux tab for that session
- **THEN** the other tmux client remains attached

#### Scenario: Closing Houmao agent tmux tab does not control agent
- **WHEN** a tmux tab is attached to a tmux session matched to a Houmao managed agent
- **AND WHEN** the developer closes or disconnects the tmux tab
- **THEN** the workbench does not stop, restart, shut down, interrupt, or clear memory for the matched Houmao agent
- **AND THEN** the workbench does not mutate the agent's shared-registry record

### Requirement: Tmux terminal content is not persisted
The workbench SHALL persist tmux tab layout and non-sensitive tmux tab configuration in the same browser configuration boundary as other pane metadata.

The workbench SHALL NOT persist raw tmux terminal output, terminal input, terminal scrollback, WebSocket payloads, credentials, cookies, bearer tokens, or authorization headers in localStorage or IndexedDB.

Restored tmux tab metadata MAY remember the selected session name and attachment mode, but restored visible terminal scrollback SHALL start from a fresh attachment stream.

#### Scenario: Tmux pane metadata can persist
- **WHEN** a developer creates a tmux tab, selects a session, chooses an attachment mode, and reloads the workbench
- **THEN** the workbench may restore the docked tmux pane and non-sensitive selected-session metadata
- **AND THEN** restored layout state contains only docked grid groups, not floating groups or popout groups

#### Scenario: Terminal bytes are not stored in browser persistence
- **WHEN** a tmux tab receives terminal output or forwards read-write terminal input
- **THEN** the workbench does not write that terminal content to localStorage
- **AND THEN** the workbench does not write that terminal content to the AG-UI client event cache

#### Scenario: Reload starts with fresh terminal evidence
- **WHEN** a tmux tab is restored after page reload
- **THEN** the restored visible terminal scrollback is not replayed from browser persistence
- **AND THEN** any visible terminal content comes from a new live attachment stream after attachment

### Requirement: Workbench tests cover tmux tabs
The repository SHALL include deterministic browser coverage for tmux tab behavior.

The coverage SHALL verify tmux session listing, Fuse-powered search, Houmao-only filtering, read-write attachment, read-only input suppression, close lifecycle boundaries, and persistence boundaries.

#### Scenario: E2E validates tmux picker
- **WHEN** the workbench E2E suite runs with a deterministic tmux bridge fixture
- **THEN** the test verifies that the tmux picker lists sessions
- **AND THEN** the test verifies search and Houmao-only filtering behavior

#### Scenario: E2E validates read-only and read-write attachment
- **WHEN** the workbench E2E suite attaches tmux tabs in read-write and read-only modes
- **THEN** the read-write tab forwards terminal input to the fixture
- **AND THEN** the read-only tab suppresses or rejects terminal input

#### Scenario: E2E validates close and persistence boundaries
- **WHEN** the workbench E2E suite closes an attached tmux tab
- **THEN** the test verifies the fixture tmux session remains alive
- **AND THEN** the test verifies no lifecycle-control request was sent
- **AND THEN** the test verifies browser persistence does not contain terminal content

#### Scenario: E2E validates no dedicated operator tab
- **WHEN** the workbench E2E suite opens a fresh workbench
- **THEN** the test verifies no dedicated Operator tab is created by default
- **AND THEN** the test verifies a Houmao agent pane can be marked as operator without changing AG-UI request bodies

## REMOVED Requirements

### Requirement: Operator input panel
**Reason**: The dedicated Operator tab is a stub with no protocol behavior beyond ordinary Houmao agent panes. Users can act as operator by directly controlling any tmux session through a tmux tab, or by designating an ordinary Houmao agent pane as the operator pane for UI orientation.

**Migration**: Use a `tmux` tab for direct TUI control. Use an ordinary Houmao agent pane for AG-UI interaction, and optionally mark that pane as operator. Existing dedicated Operator tab storage should not force the Operator tab to reappear.
