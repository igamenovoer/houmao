# Spec Delta

## ADDED Requirements

### Requirement: Normal Gateway Launches Restore Explicit Plugin Selections

The gateway SHALL accept typed plugin configuration through supported Python launch/attach interfaces and a configuration-file option on maintained gateway attach commands. It SHALL persist resolved selections and credential references, preserving them through foreground and detached launches, capability refresh, and restart.

#### Scenario: Python Caller Configures Plugins at Launch

- **WHEN** a library caller supplies valid plugin selections with gateway auto-attach enabled
- **THEN** the launched gateway resolves those selections in its own interpreter environment
- **AND THEN** the caller does not need process-local registration side effects or source modifications

#### Scenario: Operator Adds Plugins to an Already-Running Agent

- **WHEN** an operator attaches a gateway using `--plugins-config PATH` through a maintained scoped manager command
- **THEN** the selected plugin instances are persisted and loaded by that gateway
- **AND THEN** attaching does not restart or rebuild the agent body

#### Scenario: Later Attach Omits a Plugin Override

- **WHEN** gateway capability is refreshed or a stopped gateway is attached without a plugin selection override
- **THEN** previously persisted selections and references are preserved
- **AND THEN** both same-session foreground and detached execution modes restore them

#### Scenario: Explicit Empty Selection Clears Plugins

- **WHEN** a stopped gateway is attached with an explicit empty plugin mapping
- **THEN** the persisted selection becomes empty and no plugin implementation activates
- **AND THEN** omission remains distinct from an explicit empty selection

#### Scenario: Live Gateway Receives a Different Immutable Configuration

- **WHEN** an attach operation supplies plugin configuration different from a live gateway's active configuration
- **THEN** it returns an explicit restart-required conflict without changing active or persisted selections
- **AND THEN** an equivalent configuration can reuse the live gateway

### Requirement: Plugin Activation Follows Core Listener Initialization

The gateway SHALL coordinate plugin lifecycle with resolved listener binding and core runtime initialization. Core readiness SHALL NOT wait for external plugin service availability. Plugin routes SHALL remain gated until their instance is active, and the same lifecycle contract SHALL apply to normal service execution and supported embedded application construction.

#### Scenario: System-Assigned Listener Is Resolved Before Activation

- **WHEN** a gateway starts on a system-assigned port with configured plugins
- **THEN** core initialization resolves and publishes the actual listener before plugin resources activate
- **AND THEN** plugins receive the resolved listener context when they need it

#### Scenario: External Service Does Not Respond During Startup

- **WHEN** a configured plugin's service is unavailable or its startup deadline expires
- **THEN** core health and operator control remain available
- **AND THEN** the affected instance reports starting, degraded, or failed status as appropriate while custom-route admission remains explicit

#### Scenario: Embedded Host Enters and Exits the Gateway Lifecycle

- **WHEN** a supported embedded host or ASGI test starts and stops the gateway application
- **THEN** configured plugin lifespans enter and exit exactly once under the same lifecycle coordinator
- **AND THEN** workers are not dependent on an otherwise unexecuted CLI-only startup path

### Requirement: Plugin Failure Does Not Replace Core Gateway Health

The gateway SHALL keep core health, status, usage, operator-control, mailbox, and AG-UI surfaces independent of individual plugin health. Missing packages, incompatible definitions, route conflicts, failed initialization, and worker failures SHALL remain visible through host-owned plugin status while unrelated plugins and core facilities continue.

#### Scenario: One Plugin Fails While Another Is Healthy

- **WHEN** one configured plugin fails registration or execution and another configured instance is healthy
- **THEN** the healthy instance continues serving its routes
- **AND THEN** core health, status, usage, and available operator-control operations remain accessible

#### Scenario: Failed Namespace Receives a Custom Request

- **WHEN** a caller addresses a custom endpoint within a known failed instance's namespace
- **THEN** the host returns a safe HTTP 503 without calling failed plugin code
- **AND THEN** the instance's host-owned status remains readable

### Requirement: Plugin Service Operations Preserve Loopback Listener Policy

Until an authenticated remote contract exists, plugin custom routes, credential resolution, workers, and event intake SHALL be enabled only for loopback gateway listeners. A broader listener SHALL report configured instances as disabled by listener policy before importing their code. Sanitized host-owned status SHALL remain readable.

#### Scenario: All-Interface Listener Has Configured Plugins

- **WHEN** a gateway starts with host `0.0.0.0` and plugin selections
- **THEN** plugin status reports disabled-by-listener-policy
- **AND THEN** implementation modules are not imported, credentials are not resolved, and plugin workers do not start
- **AND THEN** custom plugin requests fail explicitly while core plugin-status reads remain available

### Requirement: Ordinary Plugin Event Refusals Are Immediate

The gateway SHALL attempt plugin-event dispatch only with ready gateway/plugin state, open core admission, idle available body, and applicable readiness, pending-input, and active-hook guards. A failed readiness check SHALL return a retryable error without waiting, caching, queueing, or scheduling the message for later delivery.

#### Scenario: Busy Headless Agent Refuses an Event

- **WHEN** a plugin event arrives while a headless turn is active
- **THEN** the gateway returns HTTP 409 with a retryable readiness error
- **AND THEN** it starts no overlapping turn and stores no pending plugin message

#### Scenario: Ready TUI Still Has Provider Pending Input

- **WHEN** an event targets a TUI whose tracked pending input is `yes` or `unknown`
- **THEN** the gateway returns a retryable readiness error even if the surface otherwise looks ready
- **AND THEN** it does not enqueue the event through the durable request queue

#### Scenario: Active Hook Posture Blocks a Visually Ready TUI

- **WHEN** a TUI surface is stable and ready with no pending input but an active hook channel reports active or blocked work
- **THEN** the event request fails immediately instead of waiting for a different hook posture
- **AND THEN** stale, unavailable, or disabled hook channels add no gates beyond the established TUI-only rules

#### Scenario: Existing Accepted Work Conflicts With Immediate Dispatch

- **WHEN** existing gateway work prevents immediate plugin-event dispatch
- **THEN** the event request returns a retryable conflict and existing work retains its normal scheduling
- **AND THEN** the plugin request does not join that queue or hold the execution lock while waiting

#### Scenario: Readiness Changes Before Dispatch

- **WHEN** initial checks pass but the body becomes inadmissible before dispatch
- **THEN** the original request returns an error and relinquishes its attempt
- **AND THEN** later readiness does not resume that request in the background

#### Scenario: Plugin Dispatch Does Not Add a Queued Request Kind

- **WHEN** a plugin event is dispatched through the immediate semantic path
- **THEN** no queued plugin-event request is created
- **AND THEN** the public request kinds remain `submit_prompt` and `interrupt`

### Requirement: Body Loss During Plugin Dispatch Fails the Original Request

The gateway SHALL keep a plugin event request in flight until dispatch confirmation to its captured body incarnation. Observed body death, restart, replacement, or unconfirmed handoff before response finalization SHALL fail that request. It SHALL NOT return success from a queued acknowledgement or worker start, retain a resend payload, or continue the attempt against a replacement body.

#### Scenario: Body Dies After Gateway Admission but Before Handoff

- **WHEN** an event passes gateway admission and the addressed body dies before confirmed handoff
- **THEN** the original request returns HTTP 503 with a retryable body-unavailable error
- **AND THEN** its payload is discarded rather than cached for the next body

#### Scenario: Body Restarts Under the Same Logical Agent Name

- **WHEN** the body changes execution incarnation during dispatch while its logical agent/session identity remains the same
- **THEN** the original request fails with a retryable target-changed error
- **AND THEN** no surviving callback forwards its message to the replacement body

#### Scenario: Body Loss Is Observed After Handoff but Before Response

- **WHEN** handoff may have occurred but body death or replacement is observed before successful response finalization
- **THEN** the request returns a retryable error with uncertain dispatch outcome
- **AND THEN** the gateway does not claim a known unsent message or perform another attempt

#### Scenario: Headless Worker Starts Before Its Client Handoff

- **WHEN** a local headless worker thread starts but client dispatch has not yet been confirmed
- **THEN** the event request remains in flight within its finite deadline
- **AND THEN** a failed launch or missing confirmation returns an error instead of an early success

#### Scenario: Dispatch Confirmation Times Out

- **WHEN** a live request cannot confirm handoff within its finite deadline
- **THEN** it returns an explicit failure and revokes not-yet-dispatched request work
- **AND THEN** a later callback cannot resume delivery after body recovery

### Requirement: Gateway Recovery Does Not Resend Plugin Messages

Gateway restart SHALL restore plugin selections and service resources without restoring notification payloads or initiating resend. Sender retry SHALL be a new request evaluated against current readiness. A success response SHALL mean confirmed dispatch only; a body failure occurring after that completed response SHALL NOT create a retroactive response or automatic redelivery.

#### Scenario: Body Becomes Ready After a Rejection

- **WHEN** a rejected message's body becomes ready without another sender request
- **THEN** the gateway performs no delivery of that message
- **AND THEN** only an explicit new sender request can start another attempt

#### Scenario: Gateway Restarts After an Interrupted Request

- **WHEN** the gateway restarts after a message request failed or lost its connection
- **THEN** it restores no cached event, pending notification, or resend job
- **AND THEN** the sender retains responsibility for any new attempt

#### Scenario: Sender Retries After Recovery

- **WHEN** the sender retries a failed message after the gateway and current body become ready
- **THEN** the new request independently evaluates readiness and can dispatch
- **AND THEN** the gateway does not combine it with a cached earlier attempt

#### Scenario: Body Dies After a Completed Success Response

- **WHEN** a successful dispatch response has already completed and the body subsequently dies
- **THEN** that completed response cannot be changed retroactively
- **AND THEN** the gateway neither infers completed agent processing nor automatically resends the message
