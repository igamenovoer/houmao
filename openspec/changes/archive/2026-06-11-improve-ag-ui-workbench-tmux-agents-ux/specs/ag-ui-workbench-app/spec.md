## ADDED Requirements

### Requirement: Tmux tabs fill available workspace height
Tmux tabs SHALL make the terminal attachment area consume the remaining vertical space inside the Dockview panel after fixed tmux controls are laid out.

Tmux tabs SHALL refit the visible xterm terminal when the browser viewport, Dockview panel, or terminal host size changes.

Session discovery controls and lists SHALL remain usable without causing the attached terminal to shrink below the available panel area.

#### Scenario: Browser resize refits tmux terminal
- **WHEN** a tmux tab is attached to a session
- **AND WHEN** the browser window or Dockview panel is resized
- **THEN** the tmux tab refits the terminal to the new visible terminal host size
- **AND THEN** the runtime receives the updated terminal columns and rows for the active attachment

#### Scenario: Tmux terminal consumes remaining panel height
- **WHEN** a developer opens a tmux tab in a tall Dockview panel
- **THEN** the terminal attachment area expands to use the vertical space not needed by the header, picker, and fixed controls
- **AND THEN** the tmux tab does not leave an unused footer area that prevents the terminal from filling the pane

### Requirement: Tmux session lists remove dead sessions
The workbench SHALL remove a tmux session from visible tmux session lists after the host tmux bridge reports that the session no longer exists.

The workbench SHALL refresh tmux session inventory after a tmux attachment exits or disconnects and while any tmux tab remains open.

If an attached session exits, the tmux tab SHALL mark the attachment disconnected, preserve any terminal output already written to the xterm instance, and update the session list without sending a Houmao agent lifecycle command or tmux kill command.

#### Scenario: Session closed from attached terminal disappears from list
- **WHEN** a user is attached to tmux session `HOUMAO-alpha` in a workbench tmux tab
- **AND WHEN** the user exits the session from inside the terminal
- **THEN** the tab marks the attachment disconnected
- **AND THEN** the next tmux session list shown by the workbench does not include `HOUMAO-alpha`
- **AND THEN** the workbench does not send any Houmao stop, restart, shutdown, interrupt, launch, registry cleanup, or prompt-control request

#### Scenario: Externally killed tmux session disappears from list
- **WHEN** the tmux session picker lists tmux session `HOUMAO-beta`
- **AND WHEN** that session is killed outside the browser
- **THEN** the workbench removes `HOUMAO-beta` from the visible session list after the next automatic or manual inventory refresh

### Requirement: Toolbar agent creation is consolidated into Agents
The workbench SHALL expose one top-level Agents control for discovered-agent selection, watch actions, retargeting, and blank agent-pane creation.

The workbench SHALL NOT expose a separate top-level `Agent Pane` toolbar control when blank agent-pane creation is available through the Agents picker.

#### Scenario: Top-level toolbar has a single Agents entry point
- **WHEN** a developer views the workbench top toolbar
- **THEN** the toolbar shows the Agents entry point
- **AND THEN** it does not show a separate `Agent Pane` entry point for creating a blank agent pane

#### Scenario: Blank agent pane is created from Agents picker
- **WHEN** a developer opens the Agents picker from the toolbar
- **AND WHEN** the developer activates the picker New action
- **THEN** the workbench creates a new docked blank agent pane with manual target configuration
- **AND THEN** the picker row actions for discovered agents remain available

### Requirement: Workbench tests cover tmux and Agents UX updates
The deterministic workbench browser coverage SHALL exercise tmux terminal resize, tmux dead-session removal, Agents picker auto-refresh, and blank agent-pane creation from the Agents picker.

#### Scenario: E2E validates responsive tmux tab
- **WHEN** the workbench E2E suite attaches a tmux tab through the deterministic tmux bridge fixture
- **AND WHEN** the test resizes the browser viewport or Dockview panel
- **THEN** the test verifies that the terminal area remains visible and reports updated dimensions

#### Scenario: E2E validates dead-session removal
- **WHEN** the workbench E2E suite lists a fixture tmux session
- **AND WHEN** the fixture session exits or is removed
- **THEN** the test verifies that the workbench removes that session from the visible list

#### Scenario: E2E validates consolidated Agents creation
- **WHEN** the workbench E2E suite opens the Agents picker from the toolbar
- **THEN** the test verifies discovery refresh evidence
- **AND THEN** the test creates a blank manual agent pane through the picker New action
