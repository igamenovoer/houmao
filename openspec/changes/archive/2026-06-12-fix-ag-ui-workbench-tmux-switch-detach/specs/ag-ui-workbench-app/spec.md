## ADDED Requirements

### Requirement: Tmux pane session selection replaces the active attachment
The workbench tmux pane SHALL treat selecting a different tmux session as replacing the active attachment.

Before attaching to the selected session, the pane SHALL request detach for the previous attachment and remove the previous xterm surface from the pane.

The runtime SHALL maintain only one current tmux attachment per pane and SHALL route input, resize, and scroll actions only through that current attachment.

The runtime SHALL ignore output, close, exit, error, and attached events from an older attachment after a newer attachment has become current for the same pane.

#### Scenario: Switching sessions routes commands to the new attachment
- **WHEN** a tmux pane is attached to session `houmao-alpha`
- **AND WHEN** the user selects session `utility-shell` from the session picker in the same pane
- **THEN** the pane detaches the `houmao-alpha` attachment before requesting the `utility-shell` attachment
- **AND THEN** subsequent keyboard input, resize, and scroll actions are sent only through the `utility-shell` attachment

#### Scenario: Stale old attachment events do not overwrite the new attachment
- **WHEN** a tmux pane starts replacing session `houmao-alpha` with session `utility-shell`
- **AND WHEN** the old `houmao-alpha` socket later emits output, close, exit, error, or attached messages
- **THEN** the runtime ignores those old socket events for pane state and terminal output
- **AND THEN** the pane continues showing the `utility-shell` attachment state

#### Scenario: Wheel scroll after switch targets the selected session
- **WHEN** a tmux pane has switched from session `houmao-alpha` to session `utility-shell`
- **AND WHEN** the user scrolls inside the attached terminal host with the mouse wheel
- **THEN** the workbench sends the scroll request through the current `utility-shell` attachment
- **AND THEN** no scroll request is sent through the old `houmao-alpha` attachment
