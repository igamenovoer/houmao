# Spec Delta

## MODIFIED Requirements

### Requirement: Discovered-agent panes actively reconnect by agent address

For a pane whose target source is a discovered Houmao agent, the workbench SHALL actively resolve the pane's durable agent address through the configured passive server before opening an AG-UI stream.

If the agent is offline, live without a gateway, or temporarily unreachable, the pane SHALL show a deterministic waiting, offline, reconnecting, or gateway-unavailable state and SHALL retry resolution using bounded backoff.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

If an active AG-UI stream ends unexpectedly, the pane SHALL mark the stream disconnected and return to the agent-address resolution loop without requiring the user to reselect the agent.

If resolution later returns a different current gateway for the same authoritative agent ID, the pane SHALL connect to the new gateway after verifying the target binding required for the selected access mode.

The reconnect loop SHALL NOT send Houmao lifecycle start, stop, restart, shutdown, interrupt, or launch requests.

#### Scenario: GUI starts before agent gateway

- **WHEN** a pane targets known agent `abc123`
- **AND WHEN** the passive server reports that no current gateway is available
- **THEN** the pane displays a waiting or offline state
- **AND WHEN** the agent later publishes a live gateway for `abc123`
- **THEN** the pane resolves the current gateway and connects without requiring a new target selection

#### Scenario: Agent gateway restarts on a new port

- **WHEN** a discovered-agent pane is connected to agent `abc123`
- **AND WHEN** the gateway stream fails because the gateway process went offline
- **AND WHEN** passive-server resolution later reports a new gateway port for `abc123`
- **THEN** the pane reconnects after the workbench verifies the reported gateway under the selected access mode
- **AND THEN** the pane still treats `abc123` as the same durable target

#### Scenario: Reconnect does not control lifecycle

- **WHEN** a discovered-agent pane enters reconnecting state
- **THEN** the workbench performs only passive-server resolution and AG-UI connect attempts
- **AND THEN** it does not send start, stop, restart, shutdown, interrupt, launch, or prompt-control requests

#### Scenario: A protected connect is refused

- **WHEN** a discovered pane receives an explicit authentication or authorization refusal for its connect attempt
- **THEN** it displays the refusal and waits for an explicit reconnect
- **AND THEN** it does not switch signers or submit an unsigned retry
