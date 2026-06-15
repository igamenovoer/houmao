## ADDED Requirements

### Requirement: Send-capable prompt editors submit with Shift+Enter
The workbench SHALL submit send-capable prompt editor contents when the focused editor receives `Shift+Enter`.

Send-capable prompt editors include normal agent pane prompt composers and Debug Agent editor panes that send text or JSON-like payloads through an adjacent Run or Send action.

The `Shift+Enter` shortcut SHALL use the same submission path as the editor's visible Run or Send button.

The shortcut SHALL NOT submit empty or whitespace-only prompt content.

Plain `Enter` in textarea-based send-capable editors SHALL remain available for multiline editing and SHALL NOT submit the prompt.

Read-only text areas, target configuration fields, search fields, filters, tmux terminal input, and non-send editor controls SHALL NOT submit prompt content through this shortcut.

#### Scenario: Agent prompt submits with Shift+Enter
- **WHEN** a user focuses a normal agent pane prompt editor and enters non-empty prompt text
- **AND WHEN** the user presses `Shift+Enter`
- **THEN** the workbench submits the same AG-UI run request that the pane Run button would submit
- **AND THEN** the prompt editor is cleared according to the existing Run button behavior

#### Scenario: Debug Agent editor sends with Shift+Enter
- **WHEN** a user focuses a Debug Agent editor containing a valid sendable payload
- **AND WHEN** the user presses `Shift+Enter`
- **THEN** the workbench sends the same debug publish request that the Send button would send
- **AND THEN** the Debug Agent display updates according to the existing Send button behavior

#### Scenario: Plain Enter keeps multiline editing
- **WHEN** a user focuses a textarea-based send-capable prompt editor
- **AND WHEN** the user presses `Enter` without `Shift`
- **THEN** the editor inserts or preserves a newline according to normal textarea behavior
- **AND THEN** the workbench does not submit the prompt

#### Scenario: Empty prompt shortcut is ignored
- **WHEN** a user focuses a send-capable prompt editor whose content is empty or whitespace-only
- **AND WHEN** the user presses `Shift+Enter`
- **THEN** the workbench does not send an AG-UI run request or debug publish request
- **AND THEN** no visible error is introduced solely because the empty shortcut was pressed
