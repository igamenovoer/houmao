## MODIFIED Requirements

### Requirement: Picker resolves selected agents to direct AG-UI targets
For a selected discovered or resolved agent, the workbench SHALL create target metadata whose durable address is the authoritative `agent_id` when available, or an unambiguous `agent_name` before canonical id resolution is known.

When the passive server reports current gateway host and port, the workbench MAY cache a latest observed AG-UI target URL in the form `http://{gateway_host}:{gateway_port}/v1/ag-ui`, with wildcard gateway hosts normalized to a browser-reachable host derived from the passive-server URL.

The cached gateway URL SHALL be treated as volatile. A discovered-agent pane SHALL resolve the agent address again before reconnecting after gateway failure, browser reload, or explicit reconnect.

When the selected agent is known but offline or live without a gateway, the workbench SHALL allow the pane to target that agent address and display a waiting or gateway-unavailable state instead of requiring a current gateway URL at selection time.

When the selected agent is unknown, ambiguous, rejected by proxy policy, or cannot be safely resolved as an agent address, the workbench SHALL leave the current pane target unchanged and show the resolution error.

#### Scenario: Selected live agent stores durable address and latest URL
- **WHEN** a discovered agent row resolves to `agent_id=abc123`
- **AND WHEN** the passive server reports `gateway_host = "127.0.0.1"` and `gateway_port = 9012`
- **THEN** the workbench stores `abc123` as the durable target address
- **AND THEN** it may cache `http://127.0.0.1:9012/v1/ag-ui` as the latest observed AG-UI URL

#### Scenario: Selected known offline agent can become a waiting pane
- **WHEN** a tester selects an agent address that the passive server reports as known but offline
- **THEN** the workbench can retarget the pane to that agent address
- **AND THEN** the pane displays a waiting or offline state rather than failing because no gateway URL exists

#### Scenario: Ambiguous agent name does not retarget pane
- **WHEN** a tester selects or enters an agent name that matches multiple known agent ids
- **THEN** the workbench shows an ambiguity error
- **AND THEN** the currently configured pane target remains unchanged

## ADDED Requirements

### Requirement: Workbench persists agent-address metadata for discovered targets
For discovered-agent targets, the workbench SHALL persist the passive-server base URL, durable agent address, canonical `agent_id` when known, canonical `agent_name` when known, thread id, target label, and safe display metadata.

The workbench SHALL NOT rely on a persisted gateway URL as the durable target for discovered-agent panes.

Persisted discovered-agent metadata SHALL NOT include gateway status bodies, streamed AG-UI events, transcript content, component payloads, mailbox content, memory content, raw terminal content, credentials, cookies, bearer tokens, or authorization headers.

#### Scenario: Browser reload restores agent-address target
- **WHEN** a tester selects agent `abc123` for pane `agent-1`
- **AND WHEN** the browser reloads the workbench
- **THEN** pane `agent-1` restores the durable `agent_id` target metadata
- **AND THEN** it resolves the current gateway from the passive server before connecting

#### Scenario: Persisted latest URL is not authoritative
- **WHEN** a discovered-agent pane has a cached latest gateway URL
- **AND WHEN** the agent restarts on a different gateway port
- **THEN** the workbench resolves the agent address again instead of treating the cached URL as authoritative
