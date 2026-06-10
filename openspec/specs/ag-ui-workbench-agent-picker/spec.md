# ag-ui-workbench-agent-picker Specification

## Purpose
TBD - created by archiving change add-ag-ui-workbench-agent-picker. Update Purpose after archive.
## Requirements
### Requirement: Workbench configures passive-server discovery
The AG-UI workbench SHALL allow a tester to configure a Houmao passive-server base URL for discovered-agent lookup without requiring changes to individual AG-UI pane URLs.

The workbench SHALL fetch `GET /houmao/agents` from that configured passive server and display the returned discovered-agent summaries.

The displayed summary for each agent SHALL include, when present in the response, agent ID, agent name, generation ID, tool, backend, tmux session name, gateway availability, mailbox availability, published timestamp, and lease expiry timestamp.

#### Scenario: Tester lists discovered Houmao agents
- **WHEN** a tester configures a passive-server base URL and refreshes discovery
- **AND WHEN** the passive server returns two discovered agents from `GET /houmao/agents`
- **THEN** the workbench displays both agents in the picker
- **AND THEN** each row shows the agent identity and gateway availability from the response

#### Scenario: Discovery errors are visible
- **WHEN** the configured passive server is unreachable or returns an error for `GET /houmao/agents`
- **THEN** the workbench shows a deterministic discovery error in the picker
- **AND THEN** existing pane target configuration remains unchanged

### Requirement: Agent picker supports filtering and contextual actions
The workbench SHALL provide an agent picker that can be opened from the global toolbar and from any pane target form.

The picker SHALL support filtering by visible agent identity fields, including agent ID, agent name, tool, and backend.

When opened from a pane, the picker SHALL default to retargeting that pane. When opened from the toolbar, the picker SHALL default to creating a new docked agent pane and SHALL also provide a way to choose an existing pane as the retarget destination.

#### Scenario: Pane picker defaults to retargeting that pane
- **WHEN** a tester opens the agent picker from pane `agent-1`
- **AND WHEN** the tester double-clicks a resolved agent row
- **THEN** the workbench retargets pane `agent-1` to the selected agent

#### Scenario: Toolbar picker defaults to new pane creation
- **WHEN** a tester opens the agent picker from the global toolbar
- **AND WHEN** the tester double-clicks a resolved agent row
- **THEN** the workbench creates a new docked agent pane for the selected agent

#### Scenario: Tester filters discovered agents
- **WHEN** the picker contains agents named `HOUMAO-alpha` and `HOUMAO-beta`
- **AND WHEN** the tester filters the picker by `alpha`
- **THEN** the picker keeps `HOUMAO-alpha` visible
- **AND THEN** the picker hides `HOUMAO-beta`

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

### Requirement: Existing pane retargeting resets protocol state without controlling the agent
When an existing pane is retargeted to a selected discovered agent, the workbench SHALL abort that pane's active browser stream, perform AG-UI detach when a connection ID is known, clear the pane's capabilities, run status, transcript, raw event timeline, state snapshot, activity records, tool-call records, and errors, and then apply the new target metadata.

Retargeting SHALL keep the Dockview panel ID, group, and split position unchanged.

Retargeting SHALL NOT send Houmao lifecycle stop, restart, shutdown, interrupt, launch, registry cleanup, or prompt-control requests.

#### Scenario: Retargeting clears old agent evidence
- **WHEN** pane `agent-1` displays transcript and raw events from agent `alpha`
- **AND WHEN** a tester retargets `agent-1` to discovered agent `beta`
- **THEN** pane `agent-1` uses the selected `beta` AG-UI target metadata
- **AND THEN** the old `alpha` transcript and raw events are no longer visible in that pane

#### Scenario: Retargeting detaches GUI only
- **WHEN** pane `agent-1` has an active AG-UI connection with a known connection ID
- **AND WHEN** a tester retargets the pane through the picker
- **THEN** the workbench aborts the active browser stream and sends AG-UI detach for that connection
- **AND THEN** the workbench does not send any Houmao interrupt, stop, restart, shutdown, or launch request

### Requirement: Picker can open a new docked pane from a discovered agent
The workbench SHALL allow a tester to create a new docked agent pane from a resolved discovered-agent row.

The new pane SHALL receive its own pane ID, target label, AG-UI URL, thread ID, source metadata, event state, and connection lifecycle independent from all existing panes.

The new pane SHALL be placed inside the Dockview workbench and SHALL NOT create a floating group, popout window, or browser window.

#### Scenario: New pane opens from discovered agent
- **WHEN** the toolbar picker is open
- **AND WHEN** the tester chooses a resolved discovered agent
- **THEN** the workbench creates a new docked agent pane for that agent
- **AND THEN** the pane target URL is the resolved AG-UI URL

#### Scenario: New discovered-agent pane is isolated
- **WHEN** a newly created discovered-agent pane connects to agent `alpha`
- **AND WHEN** another pane connects to agent `beta`
- **THEN** events received by `alpha` appear only in the `alpha` pane
- **AND THEN** events received by `beta` appear only in the `beta` pane

### Requirement: Manual AG-UI target entry remains first-class
The workbench SHALL keep the manual label, AG-UI URL, and thread ID fields available for operator and agent panes.

Manual AG-UI URL entry SHALL work without configuring passive-server discovery. Editing a discovered target's AG-UI URL manually SHALL switch that target to manual source metadata while preserving the typed URL and thread ID.

Manual non-loopback AG-UI or passive-server URLs SHALL use the existing workbench proxy allowlist behavior and SHALL surface deterministic policy errors when rejected.

#### Scenario: Tester uses explicit gateway address without discovery
- **WHEN** no passive-server base URL is configured
- **AND WHEN** a tester enters `http://127.0.0.1:8765/v1/ag-ui` in a pane's AG-UI URL field
- **THEN** the pane can fetch capabilities, connect, and run against that explicit target

#### Scenario: Manual edit switches discovered target to manual
- **WHEN** a pane is targeted at a discovered agent
- **AND WHEN** the tester edits the AG-UI URL field directly
- **THEN** the workbench preserves the typed URL
- **AND THEN** the pane source metadata becomes manual rather than discovered

### Requirement: Workbench persists only safe discovery and target metadata
The workbench SHALL persist the configured passive-server base URL and pane target metadata needed to restore labels, URLs, thread IDs, and selected discovered-agent identity.

The workbench SHALL NOT persist discovered-agent list responses, gateway-status response bodies, prompt text, streamed transcript content, raw AG-UI events, state snapshots, activity records, tool-call payloads, mailbox content, memory content, raw terminal content, credentials, cookies, bearer tokens, or authorization headers by default.

#### Scenario: Selected target metadata persists after reload
- **WHEN** a tester selects a discovered agent for pane `agent-1`
- **AND WHEN** the browser reloads the workbench
- **THEN** pane `agent-1` restores its label, AG-UI URL, thread ID, and selected discovered-agent identity metadata
- **AND THEN** the persisted state does not include the last discovered-agent list response

#### Scenario: Stream data is not persisted after reload
- **WHEN** a pane receives transcript messages, state snapshots, tool calls, and raw events
- **AND WHEN** the browser reloads the workbench
- **THEN** those stream contents are not restored from local storage

### Requirement: Proxy policy covers discovery and gateway resolution
The workbench local proxy SHALL support passive-server discovery and gateway-status requests as well as AG-UI requests, while preserving the existing target policy that allows loopback by default and rejects non-loopback hosts unless configured.

The proxy SHALL preserve upstream status code and JSON response body for passive-server discovery and gateway-status responses.

#### Scenario: Discovery uses local proxy
- **WHEN** the workbench fetches `GET /houmao/agents` for a configured passive-server URL
- **THEN** the browser request goes through the workbench proxy
- **AND THEN** the proxy forwards the upstream status and JSON body when the target passes policy

#### Scenario: Disallowed passive-server host is rejected
- **WHEN** a tester configures a passive-server URL whose host is not loopback and not allowlisted
- **AND WHEN** the workbench refreshes discovery
- **THEN** the proxy rejects the request before contacting the passive server
- **AND THEN** the picker displays a target-policy error

### Requirement: Deterministic E2E coverage exercises the agent picker
The repository SHALL include deterministic Playwright coverage for the workbench agent picker using fake passive-server discovery and fake AG-UI targets.

The tests SHALL run with the existing Bun-global Playwright workflow documented for the workbench.

#### Scenario: E2E retargets existing pane from list
- **WHEN** the E2E fake passive server returns agents `alpha` and `beta`
- **AND WHEN** the test opens the picker from an existing pane and selects `alpha`
- **THEN** the pane target is updated to the resolved `alpha` AG-UI URL
- **AND THEN** connecting the pane shows fake `alpha` evidence

#### Scenario: E2E opens new pane from list
- **WHEN** the E2E test opens the toolbar picker and selects `beta`
- **THEN** the workbench creates a new docked pane for `beta`
- **AND THEN** connecting the new pane shows fake `beta` evidence

#### Scenario: E2E keeps manual URL fallback
- **WHEN** the E2E test enters an explicit manual AG-UI URL after using the picker
- **THEN** the pane uses the manual URL
- **AND THEN** the saved target source metadata is manual

#### Scenario: E2E covers unresolved gateway state
- **WHEN** the E2E fake passive server lists an agent with no resolvable gateway
- **AND WHEN** the test selects that row
- **THEN** the picker shows the gateway resolution error
- **AND THEN** no pane is retargeted to an invalid AG-UI URL

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

### Requirement: Agent picker can watch targets without opening panes
The workbench agent picker SHALL let a tester mark a discovered agent and thread as watched without creating a visible pane.

The picker SHALL also let a tester open a pane for an already watched target.

The picker SHALL expose unwatch as an explicit action distinct from closing a pane.

Watch and unwatch actions SHALL NOT send Houmao lifecycle start, stop, restart, shutdown, interrupt, launch, registry cleanup, or prompt-control requests.

#### Scenario: Watch discovered agent without pane
- **WHEN** the picker lists discovered agent `abc123`
- **AND WHEN** the tester chooses the watch action for `abc123` and thread `thread-1`
- **THEN** the workbench adds a watched target for `abc123` and `thread-1`
- **AND THEN** it does not create a Dockview pane unless the tester also chooses to open one

#### Scenario: Open pane for watched target
- **WHEN** discovered agent `abc123` is already watched
- **AND WHEN** the tester chooses to open a pane for `abc123`
- **THEN** the workbench creates a docked pane presenting the watched target
- **AND THEN** the pane renders any cached events already received for that target

#### Scenario: Unwatch is separate from pane close
- **WHEN** a pane presenting watched agent `abc123` is open
- **AND WHEN** the tester closes the pane
- **THEN** the watched target remains watched
- **AND WHEN** the tester chooses unwatch for `abc123`
- **THEN** the workbench closes the background watcher stream for that target

### Requirement: Picker displays watched-target state for discovered agents
The picker SHALL show whether a discovered agent/thread is watched, connected, reconnecting, offline, or unwatched.

The watched state SHALL be derived from the workbench watched-target registry and watcher status.

When a discovered agent is watched by durable `agent_id`, a later gateway host or port change SHALL NOT create a second watched target for the same agent/thread.

#### Scenario: Watched agent appears in picker
- **WHEN** agent `abc123` is watched
- **AND WHEN** the tester opens the picker
- **THEN** the picker shows `abc123` as watched
- **AND THEN** the picker exposes its watcher status

#### Scenario: Gateway change preserves watched identity
- **WHEN** watched agent `abc123` restarts on a different gateway port
- **AND WHEN** the passive server reports the new gateway for `abc123`
- **THEN** the picker still shows one watched entry for `abc123`
- **AND THEN** it does not duplicate the watched target by gateway URL

### Requirement: Picker persists watched target metadata safely
The workbench SHALL persist watched target metadata needed to restore background listeners after browser reload.

Persisted watched metadata SHALL include passive-server base URL when needed, durable agent address, canonical `agent_id` when known, canonical `agent_name` when known, thread id, target label, and safe display metadata.

Persisted watched metadata SHALL NOT include gateway status bodies, discovered-agent list responses, streamed AG-UI events, transcript content, component payloads, mailbox content, memory content, raw terminal content, credentials, cookies, bearer tokens, or authorization headers.

#### Scenario: Browser reload restores watched target
- **WHEN** a tester watches agent `abc123` and thread `thread-1`
- **AND WHEN** the browser reloads the workbench
- **THEN** the watched target metadata is restored
- **AND THEN** the watcher resolves the current gateway through the passive server before connecting

#### Scenario: Persisted watch metadata excludes stream payloads
- **WHEN** a watched target receives chart and table events
- **AND WHEN** the workbench persists watched target metadata
- **THEN** the metadata does not include the chart or table payloads
- **AND THEN** stream events are stored only in the client-owned event cache
