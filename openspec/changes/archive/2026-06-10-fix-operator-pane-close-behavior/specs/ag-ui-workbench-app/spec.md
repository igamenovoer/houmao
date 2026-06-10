## MODIFIED Requirements

### Requirement: Operator input panel
The workbench SHALL provide an operator input panel that connects to one configured Houmao operator agent through AG-UI run and connection semantics.

The workbench SHALL create the operator panel by default when a fresh or otherwise empty workbench opens.

The workbench SHALL respect an explicit user close of the operator panel when other docked panes remain available, and SHALL NOT immediately re-create the operator panel after that close.

Closing the operator panel SHALL NOT erase the persisted operator target configuration.

#### Scenario: Operator target can be configured
- **WHEN** a developer opens the operator panel
- **THEN** the panel allows configuring a label, AG-UI base URL or run URL, and thread identifier for the operator Houmao agent

#### Scenario: Operator prompt submits one AG-UI run
- **WHEN** the operator panel is connected and the user submits a text prompt
- **THEN** the workbench sends one AG-UI `RunAgentInput` request to the configured operator target
- **AND THEN** the request includes a stable `threadId`, generated `runId`, text user message, empty tools list unless tools are explicitly supported, context array, state object, and forwarded props object

#### Scenario: Operator input does not fan out by default
- **WHEN** multiple agent panes are open and the user submits text through the operator panel
- **THEN** only the configured operator target receives the submitted AG-UI run
- **AND THEN** other panes continue only their own configured connections and runs

#### Scenario: Fresh workbench opens with operator panel
- **WHEN** a developer opens a fresh workbench with no saved docked layout
- **THEN** the workbench creates the operator panel
- **AND THEN** the operator panel uses the persisted or default operator target configuration

#### Scenario: Closing operator pane is respected while other panes remain
- **WHEN** a developer has at least one agent or Debug Agent pane open
- **AND WHEN** the developer closes the operator pane
- **THEN** the workbench does not immediately re-create the operator pane
- **AND THEN** the remaining panes stay open and usable

#### Scenario: Operator close does not erase target metadata
- **WHEN** a developer configures the operator target and then closes the operator pane while another pane remains open
- **THEN** the persisted workbench state retains the operator target metadata
- **AND THEN** the persisted layout does not force the operator pane to reappear on reload

## ADDED Requirements

### Requirement: Workbench tests cover operator close persistence
The repository SHALL include deterministic browser coverage for operator pane close behavior.

The coverage SHALL verify that closing the operator pane while another pane exists does not trigger automatic operator pane re-creation.

The coverage SHALL verify that the closed operator visual pane remains absent after reload while other panes and non-sensitive persisted metadata remain valid.

#### Scenario: E2E closes operator without respawn
- **WHEN** the workbench E2E suite opens another pane and closes the operator pane
- **THEN** the test verifies that the operator panel remains absent
- **AND THEN** the test verifies that the other pane remains visible

#### Scenario: E2E reload preserves operator absence
- **WHEN** the operator pane was explicitly closed while another pane remained open
- **AND WHEN** the workbench reloads
- **THEN** the test verifies that the operator pane is not restored by layout persistence
- **AND THEN** the test verifies that persisted operator target metadata is not erased
