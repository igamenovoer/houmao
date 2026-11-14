# Spec Delta

## Purpose

Define owner-bound CCCC chat operations and delivery observations exposed to an already-running Houmao agent through its selected gateway plugin.

## ADDED Requirements

### Requirement: Chat Operations Use the Selected Plugin Namespace

The integration SHALL expose chat send, reply, explicit delivery retry, bounded history, membership, capabilities, and delivery status under its host-assigned plugin namespace. A thin installed client SHALL use these HTTP operations without requiring CCCC tools or credentials inside the body.

#### Scenario: Agent Sends Through Its Local Gateway

- **WHEN** an agent calls the installed client with its gateway URL and selected plugin instance
- **THEN** the operation uses the configured CCCC binding without discovering provider credentials in the body

#### Scenario: Two Plugin Instances Use the Same Relative Routes

- **WHEN** distinct CCCC instances expose their chat operations
- **THEN** host-assigned instance namespaces keep their URLs and state independent

### Requirement: Chat Recipients and Modes Are Explicit

Chat send SHALL require an explicit recipient selection within the binding's advertised CCCC scope and mode `send` or `request_reply`. Unsupported aliases, mixed audience domains, or recipients SHALL fail before mutation. Deferred `mail` mode SHALL require the separate Mail capability and operation.

#### Scenario: Sender Omits Recipients

- **WHEN** a send request omits its recipient selection
- **THEN** it fails instead of selecting an implicit foreman, email address, or broadcast target

#### Scenario: Human and Agent Audiences Are Mixed

- **WHEN** a request mixes the CCCC human user and agent recipients in one audience
- **THEN** it is rejected without committing a message

#### Scenario: Chat Caller Requests Deferred Mail

- **WHEN** a caller selects `mail` through the chat send operation
- **THEN** the integration rejects the mode and identifies the separate Mail capability when available

### Requirement: Sender Identity Is Never Caller-Selected

Send, reply, and retry SHALL use the authenticated Actor associated with the gateway owner. Each mutation SHALL require the current expected binding identity. A stale binding or request-supplied sender override SHALL fail before contacting another Actor or service account.

#### Scenario: Binding Changes Before Send

- **WHEN** a caller submits a send using the binding identity from before operator reconfiguration
- **THEN** the operation fails as stale without sending through the replacement

#### Scenario: Actor Attempts to Send as User

- **WHEN** a request attempts to replace its sender with CCCC's human `user`
- **THEN** the integration refuses the override rather than using the human Web API

### Requirement: Chat Results Separate Storage From Recipient Handoff

A send or reply result SHALL preserve the native CCCC event ID and expose provider storage acceptance separately from per-recipient handoff outcomes. Unknown, partial, refused, or uncertain delivery SHALL remain explicit. An accepted ledger write SHALL NOT be described as a completed recipient task.

#### Scenario: Message Is Stored but Recipient Is Busy

- **WHEN** CCCC commits a message and its recipient refuses immediate handoff
- **THEN** the result or subsequent receipt reports stored content and refused delivery separately
- **AND THEN** the integration does not replace the outcome with generic delivered success

#### Scenario: Broadcast Has Different Recipient Outcomes

- **WHEN** a supported explicit broadcast produces accepted and unavailable recipients
- **THEN** the receipt preserves each concrete recipient outcome and reports partial delivery

### Requirement: Outbound Correlation Supports Safe Caller Reconciliation

Send and reply SHALL accept a caller operation ID scoped to the owner, binding, and operation. The provider SHALL preserve the original event for an accepted operation ID and reject conflicting reuse. Lost mutation responses SHALL be reported as uncertain without automatic resend or backend switching.

#### Scenario: Caller Repeats an Accepted Send Operation

- **WHEN** a caller explicitly repeats the same operation ID with the same normalized request
- **THEN** the provider returns the original event without appending another message or initiating another delivery attempt

#### Scenario: Operation ID Is Reused With Different Content

- **WHEN** an accepted operation ID is reused with a different recipient, mode, body, or reply target
- **THEN** the provider reports a conflict without a second message

#### Scenario: Provider Response Is Lost

- **WHEN** the service may have accepted a send but its response cannot be obtained
- **THEN** the integration exposes uncertainty and the operation ID for explicit reconciliation
- **AND THEN** it does not retry the mutation through CCCC or an email provider automatically

### Requirement: Event References Preserve Native Reply Ancestry

Chat results SHALL retain native event IDs and structured reply references while supplying opaque owner- and binding-scoped targeting handles. Reply and receipt lookup SHALL reject handles from another owner, endpoint, Group, or Actor generation before mutation or private retrieval.

#### Scenario: Agent Replies to an Incoming Event

- **WHEN** the agent submits a reply using the event reference delivered by its selected integration
- **THEN** CCCC records the original native event as the structured reply parent
- **AND THEN** the reply sender remains the gateway owner's Actor

#### Scenario: Old Reference Targets Recreated Actor

- **WHEN** an operation uses a reference issued before the Actor registration was replaced
- **THEN** it fails instead of interpreting the same native ID in the replacement scope

### Requirement: History Is Bounded and Non-Consuming

History SHALL expose Actor-visible messages with finite count and byte limits, scoped continuation, and explicit completeness. Reading chat history SHALL NOT advance the Mail cursor, acknowledge a delivery, or dispatch history into the body. Invalid or stale anchors SHALL fail explicitly.

#### Scenario: Agent Reads More Than One Page

- **WHEN** visible history exceeds the selected page size
- **THEN** the integration returns a bounded page with continuation and `has_more`
- **AND THEN** subsequent pages preserve the same owner, binding, and query scope

#### Scenario: History Contains Deferred Mail

- **WHEN** history includes a visible message in Mail mode
- **THEN** returning that history leaves its deferred-inbox cursor unchanged

#### Scenario: Content Exceeds the History Byte Budget

- **WHEN** visible history content exceeds the response budget
- **THEN** the response identifies its incomplete content or returns an explicit limit error
- **AND THEN** it does not silently label truncated content as complete

### Requirement: Membership Inspection Has Normal Actor Visibility

Membership inspection SHALL report only the selected Group's Actor-visible public membership and receive status. It SHALL NOT expose private runtime homes, execution credentials, or service administration operations. Unverified Houmao identities SHALL remain CCCC participants without synthesized agent IDs.

#### Scenario: Member Has No Houmao Identity Mapping

- **WHEN** a CCCC member is visible without a verified Houmao association
- **THEN** membership reports its CCCC Actor identity without hashing a name or address into an agent ID

#### Scenario: Agent Requests Private Member Configuration

- **WHEN** a caller requests another member's credentials or runtime environment
- **THEN** the integration reports an unsupported or forbidden operation without disclosing them

### Requirement: Capability Inspection Reflects Qualified Support

Capabilities SHALL report effective provider and plugin support, recipient scope, modes, page/content limits, and receipt semantics. An unavailable or unqualified operation SHALL remain unavailable rather than be emulated through another channel or privileged endpoint.

#### Scenario: Initial Chat Plugin Is Queried for Mail

- **WHEN** change 01 is installed without the deferred Mail implementation
- **THEN** capabilities report Mail operations unavailable even if native CCCC documentation describes them

#### Scenario: Provider Does Not Support a Recipient Scope

- **WHEN** a caller selects unsupported cross-Group or external-email delivery
- **THEN** the integration reports that limitation without translating the address or choosing another transport

### Requirement: Incoming Content Remains Ordinary Chat

Incoming chat and reply requests SHALL use the generic immediate ordinary-event contract. Message text, sender role, CCCC request-reply mode, and service metadata SHALL NOT grant interrupt, raw-input, reset, compaction, lifecycle, or admission-bypass authority.

#### Scenario: Peer Sends Control-Looking Text

- **WHEN** an incoming event contains `/new`, `/compact`, or terminal control-looking text
- **THEN** the gateway delivers it only inside an ordinary message envelope when ready
- **AND THEN** it does not invoke a privileged control operation

#### Scenario: Reply Request Arrives During an Active Turn

- **WHEN** a `request_reply` event reaches a busy body
- **THEN** it receives the same readiness refusal as ordinary chat
- **AND THEN** the reply obligation does not justify interruption or delayed local delivery

### Requirement: Chat Acceptance Requires Two Real Coding Agents

Issue #77 acceptance SHALL require a successful chat receive/reply smoke with two real managed coding agents using distinct gateways and Actors against compatible actual CCCC. It SHALL supplement deterministic stand-in and installed-package tests. Missing model credentials or unsuccessful execution SHALL leave acceptance pending, not waive the real-agent check.

#### Scenario: Real Agent Receives Chat and Replies

- **WHEN** one real managed coding agent sends chat and the second receives its ordinary gateway notification
- **THEN** the second agent replies through its own gateway with verified native reply ancestry
- **AND THEN** the evidence identifies both real clients and Actor bindings without exposing credentials or changing body MCP configuration

#### Scenario: Stand-In Tests Pass but Real-Agent Smoke Has Not Passed

- **WHEN** deterministic and actual-service tests pass but model credentials are unavailable or the required real-agent smoke fails
- **THEN** issue #77 acceptance remains pending and the live check is reported as blocked or unsuccessful
