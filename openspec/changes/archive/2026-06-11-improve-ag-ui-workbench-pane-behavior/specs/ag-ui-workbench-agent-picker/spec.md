## ADDED Requirements

### Requirement: Discovered-agent selection auto-connects opened panes
When a tester selects a discovered agent from the agent picker to create a new agent pane, the workbench SHALL automatically connect the created pane to the selected target.

When a tester selects a discovered agent from the agent picker to retarget an existing agent pane, the workbench SHALL automatically connect the retargeted pane to the selected target after clearing obsolete pane state.

Auto-connect SHALL reuse the same watched-target registration and active-thread mutation semantics as the pane's explicit Connect action.

Auto-connect SHALL NOT send Houmao lifecycle start, stop, restart, shutdown, interrupt, launch, registry cleanup, or prompt-control requests.

#### Scenario: Selecting discovered agent opens connected pane
- **WHEN** the toolbar agent picker lists discovered agent `abc123` with a live gateway
- **AND WHEN** the tester selects `abc123` with the new-pane action
- **THEN** the workbench creates a docked agent pane targeted at `abc123`
- **AND THEN** the pane registers the target as watched and begins the AG-UI connect stream without requiring a separate Connect click
- **AND THEN** the pane requests the gateway active-thread mutation when active-thread routing is supported for that target

#### Scenario: Retargeting discovered agent reconnects pane
- **WHEN** pane `agent-1` is targeted at discovered agent `alpha`
- **AND WHEN** the tester opens the picker from `agent-1` and selects discovered agent `beta`
- **THEN** the workbench retargets `agent-1` to `beta` and clears obsolete `alpha` pane-local protocol state
- **AND THEN** the pane registers `beta` as watched and begins the AG-UI connect stream without requiring a separate Connect click
- **AND THEN** the workbench does not send any Houmao lifecycle command to `alpha` or `beta`

#### Scenario: Offline discovered agent becomes waiting pane
- **WHEN** the picker resolves a known discovered agent whose gateway is currently unavailable
- **AND WHEN** the tester selects that agent with the new-pane or retarget action
- **THEN** the resulting pane stores the durable discovered-agent target metadata
- **AND THEN** auto-connect enters the existing waiting, offline, or reconnecting watcher state instead of failing pane creation

### Requirement: Blank manual panes remain explicitly manual
Creating a blank manual agent pane from the agent picker SHALL NOT auto-connect, watch a target, resolve passive-server agent addresses, or mutate gateway active-thread state.

Blank manual panes SHALL continue to require explicit user target entry and explicit connect, watch, or run actions before network AG-UI activity begins.

#### Scenario: Picker New action does not auto-connect
- **WHEN** the tester opens the toolbar agent picker
- **AND WHEN** the tester activates the picker New action for a blank manual pane
- **THEN** the workbench creates a blank docked agent pane with manual target metadata
- **AND THEN** the workbench does not register a watched target for that blank pane
- **AND THEN** the workbench does not dispatch an active-thread mutation for that blank pane

### Requirement: Picker auto-connect has deterministic browser coverage
The repository SHALL include deterministic browser coverage proving that discovered-agent new-pane and retarget picker actions auto-connect the resulting pane.

The coverage SHALL also prove that blank manual pane creation through the picker remains non-connecting.

#### Scenario: E2E validates new-pane auto-connect
- **WHEN** the workbench E2E suite selects a live discovered agent from the toolbar picker
- **THEN** the created pane shows watched or connected status without the test clicking the pane Connect button
- **AND THEN** the active-thread marker reaches active, idle, or unsupported according to the fixture gateway behavior without crashing the pane

#### Scenario: E2E validates blank pane remains manual
- **WHEN** the workbench E2E suite creates a blank manual pane from the picker New action
- **THEN** no watched target is created for the blank pane
- **AND THEN** the pane does not open an AG-UI connect stream until the test performs an explicit connect or run action
