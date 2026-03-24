## ADDED Requirements

### Requirement: Houmao-owned control core is the native authority for CAO-compatible session and terminal lifecycle
The system SHALL provide a Houmao-owned control core that is the authoritative implementation for the CAO-compatible control slice preserved by the supported pair.

That control core SHALL own at minimum:

- session creation and deletion
- terminal creation and deletion
- terminal metadata lookup
- working-directory lookup
- terminal output retrieval
- prompt input delivery
- control-input delivery
- exit delivery
- compatibility-surface health checks

The supported pair SHALL NOT require a supervised child `cao-server` process or an installed `cao` executable in order to satisfy those operations.

#### Scenario: Pair creates a compatibility terminal without a child CAO process
- **WHEN** `houmao-server` receives a supported `POST /cao/sessions/{session_name}/terminals` request
- **THEN** it satisfies that request through the Houmao-owned control core
- **AND THEN** the request does not depend on starting or reaching a separate child `cao-server` process

#### Scenario: Pair control works without installed `cao`
- **WHEN** `houmao-srv-ctrl` executes a supported CAO-compatible pair command that creates, inspects, or mutates a session
- **THEN** the command succeeds through Houmao-owned control components
- **AND THEN** it does not require `cao` to be installed on `PATH`

### Requirement: Control core keeps internal control models separate from CAO compatibility projection
The control core SHALL expose Houmao-owned internal models for live control and provider state, and it SHALL project CAO-compatible HTTP and CLI payloads through explicit compatibility adapters rather than reusing CAO payload types as the internal authority model.

Compatibility-only fields, route naming, and CLI wording SHALL remain confined to those projection adapters so that future upstream CAO behavior can be imported at clear insertion points without redefining the native control core.

#### Scenario: Internal control state projects into CAO-compatible terminal payloads
- **WHEN** the control core returns terminal state that includes Houmao-owned internal metadata
- **THEN** the `/cao/terminals/{terminal_id}` compatibility response projects the CAO-compatible fields required by the pinned contract
- **AND THEN** Houmao-only internal fields do not become the required native control model for the compatibility route

#### Scenario: Upstream provider behavior has an explicit insertion point
- **WHEN** maintainers decide to import a useful upstream CAO provider quirk or launch behavior
- **THEN** they update the relevant Houmao provider adapter or compatibility projection seam
- **AND THEN** they do not need to restore CAO as a runtime framework dependency to add that behavior

### Requirement: Compatibility inbox queue remains terminal-scoped and separate from Houmao mailbox
If the system preserves the CAO-compatible inbox route family under `/cao/terminals/{terminal_id}/inbox/messages`, that behavior SHALL remain a terminal-scoped compatibility queue owned by the control core.

That compatibility inbox SHALL NOT become the Houmao mailbox transport, message store, unread-state model, or gateway notifier trigger.

#### Scenario: Compatibility inbox enqueue does not create a mailbox message
- **WHEN** a caller posts a CAO-compatible inbox message to `/cao/terminals/{terminal_id}/inbox/messages`
- **THEN** the control core records or delivers that message as terminal-scoped compatibility work
- **AND THEN** the Houmao mailbox store does not create a new mailbox message for that enqueue

#### Scenario: Mailbox unread state is unaffected by compatibility inbox traffic
- **WHEN** compatibility inbox traffic wakes or queues work for a terminal
- **THEN** Houmao mailbox unread counts and gateway notifier decisions continue to depend only on mailbox state
- **AND THEN** they do not treat compatibility inbox records as mailbox messages

### Requirement: Pinned CAO source remains the control-core parity oracle
The control core SHALL treat the pinned CAO checkout as the parity oracle for CAO-compatible behavior and as a reference source for selectively importing future upstream capability changes.

The control core SHALL NOT require that oracle to be live in the supported product path in order to serve the pair.

#### Scenario: Control-core verification compares behavior to pinned CAO
- **WHEN** maintainers verify CAO-compatible control behavior after changing the Houmao control core
- **THEN** they compare the Houmao behavior against the pinned CAO source or an oracle built from it
- **AND THEN** the supported pair runtime still runs without CAO as a required dependency
