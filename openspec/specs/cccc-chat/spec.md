# cccc-chat Specification

## Purpose

Define owner-bound CCCC chat operations and delivery observations exposed to an already-running Houmao agent through its selected gateway plugin.

## Requirements

### Requirement: Chat Operations Use the Selected Plugin Namespace

The integration SHALL expose chat send, reply, explicit delivery retry, bounded history, membership, capabilities, and delivery status under its host-assigned plugin namespace. The installed client SHALL use those operations in gateway mode, with the configured Actor credentials held by the gateway. Direct mode SHALL use the explicitly selected owner-bound Actor profile for the common operations that CCCC qualifies.

#### Scenario: Agent Sends Through Its Local Gateway

- **WHEN** an agent invokes the installed client through its verified local gateway and selected plugin instance
- **THEN** the operation uses the configured CCCC binding and the gateway retains control of provider credentials

#### Scenario: Two Plugin Instances Use the Same Relative Routes

- **WHEN** distinct CCCC instances expose their chat operations
- **THEN** host-assigned instance namespaces keep their URLs and state independent

#### Scenario: Agent Sends Directly Without a Running Gateway

- **WHEN** an agent invokes a qualified common chat operation using an explicitly selected direct profile
- **THEN** the client makes the operation against the exact CCCC origin and Actor configured in that profile
- **AND THEN** the result uses the common operation's delivery and reconciliation semantics

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

Send, reply, and retry SHALL use the authenticated Actor of the selected owner binding. Gateway sends SHALL verify a short connection token from recipient discovery. Gateway replies SHALL verify the handle's binding and receiver generation. Direct mutations SHALL use the selected profile's Actor authority and exact target. Stale targeting or a request-supplied sender override SHALL fail before provider mutation.

#### Scenario: Binding Changes Before Send

- **WHEN** a caller sends with a connection token obtained from recipient discovery before a binding or connection generation change
- **THEN** the operation fails as stale and leaves the replacement binding untouched

#### Scenario: Actor Attempts to Send as User

- **WHEN** a request attempts to replace its sender with CCCC's human `user`
- **THEN** the integration refuses the override before provider mutation

### Requirement: Chat Results Separate Storage From Recipient Handoff

A send or reply result SHALL preserve the native CCCC event ID and report provider storage acceptance separately from each recipient's delivery status. Pending work, confirmed ordinary handoff, acknowledged direct read, and task completion SHALL have distinct meanings. Unknown, partial, refused, failed, or uncertain delivery SHALL remain explicit.

#### Scenario: Message Is Stored but Recipient Is Busy

- **WHEN** CCCC commits a message and the recipient is busy before handoff starts
- **THEN** the result or subsequent receipt reports stored content and pending delivery separately
- **AND THEN** a later confirmed handoff updates the receipt for that same attempt

#### Scenario: Broadcast Has Different Recipient Outcomes

- **WHEN** a supported explicit broadcast produces accepted and unavailable recipients
- **THEN** the receipt preserves each concrete recipient outcome and reports partial delivery

#### Scenario: A Direct Result Is Acknowledged

- **WHEN** a direct client acknowledges the receipt for the retrieved chat
- **THEN** the provider records direct read for those deliveries as a distinct outcome from gateway handoff or task completion

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

Explicit chat and receipt results SHALL retain native event IDs and structured ancestry where qualified. Gateway notifications SHALL use short opaque per-message handles scoped to the gateway run, owner, instance, Actor binding, receiver generation, and a finite lifetime. Gateway detail and reply SHALL resolve the exact referenced event under that scope. A direct pull SHALL supply CCCC-issued references usable across CLI invocations by the same Actor registration.

#### Scenario: Agent Replies to an Incoming Event

- **WHEN** an agent submits text, an operation ID, and the valid handle for one message to `POST /v1/plugins/{instance}/chat/reply`
- **THEN** CCCC records that message's original native event as the structured reply parent
- **AND THEN** the reply sender remains the Actor bound to the gateway

#### Scenario: Agent Requests the Details of One Batched Message

- **WHEN** an authorized agent calls `GET /v1/plugins/{instance}/messages/{handle}` with a live handle from a multi-message notification
- **THEN** the result displays that exact Actor-visible event's sender, timestamp, mode, text, and any authorized reply-parent context without signed provider references
- **AND THEN** each other message in the notification retains its own independent handle

#### Scenario: A Gateway Handle Expires or Crosses Its Scope

- **WHEN** a detail or reply call uses an expired handle, a handle from before restart or reconnect, or a handle for a different owner, instance, or Actor binding
- **THEN** the gateway returns a typed HTTP 409 conflict before reading or mutating chat through that handle
- **AND THEN** it guides the caller to authorized history lookup

#### Scenario: Caller Selects a History Event After Its Handle Expires

- **WHEN** an authorized caller explicitly selects one exact Actor-visible history event
- **THEN** the gateway issues a fresh handle for that event under the current scope
- **AND THEN** repeating a reply with the same operation ID, native parent, and normalized text reconciles the original provider result even if it uses the fresh handle

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

Membership inspection SHALL report only the selected Group's Actor-visible public membership and receive status. It SHALL NOT expose private runtime homes, execution credentials, or service administration operations. Unverified Houmao identities SHALL remain CCCC participants without synthesized agent IDs. `members --group` SHALL assert equality with the selected binding's Group before membership is read.

#### Scenario: Member Has No Houmao Identity Mapping

- **WHEN** a CCCC member is visible without a verified Houmao association
- **THEN** membership reports its CCCC Actor identity without hashing a name or address into an agent ID

#### Scenario: Agent Requests Private Member Configuration

- **WHEN** a caller requests another member's credentials or runtime environment
- **THEN** the integration reports an unsupported or forbidden operation without disclosing them

#### Scenario: The Expected Group Matches the Selected Binding

- **WHEN** an authorized gateway or direct caller runs `members` with a `--group` value equal to the selected Group
- **THEN** the result has the same visibility and shape as a `members` request with no assertion

#### Scenario: The Expected Group Differs From the Selected Binding

- **WHEN** an authorized caller asserts another Group through `members --group`
- **THEN** the CLI reports `group_conflict` and explains how to select the intended gateway instance or direct Actor profile
- **AND THEN** the integration returns no membership and issues no provider membership request

### Requirement: Capability Inspection Reflects Qualified Support

Capabilities SHALL report effective provider and plugin support, recipient scope, modes, page/content limits, and receipt semantics. An unavailable or unqualified operation SHALL remain unavailable rather than be emulated through another channel or privileged endpoint.

#### Scenario: Initial Chat Plugin Is Queried for Mail

- **WHEN** change 01 is installed without the deferred Mail implementation
- **THEN** capabilities report Mail operations unavailable even if native CCCC documentation describes them

#### Scenario: Provider Does Not Support a Recipient Scope

- **WHEN** a caller selects unsupported cross-Group or external-email delivery
- **THEN** the integration reports that limitation without translating the address or choosing another transport

### Requirement: Incoming Content Remains Ordinary Chat

Incoming chat SHALL use the configured CCCC service binding and current receiver lease for intake, and the immediate ordinary-event contract at handoff. The sender field SHALL be CCCC attribution. The host SHALL present each delivery as a request the agent evaluates under its current rules and tool permissions. Message text, sender role, CCCC request-reply mode, and service metadata SHALL NOT grant interrupt, raw-input, reset, compaction, lifecycle, or admission-bypass authority.

#### Scenario: Peer Sends Control-Looking Text

- **WHEN** an incoming event contains `/new`, `/compact`, or terminal control-looking text
- **THEN** the gateway delivers it as quoted content inside the request fence when ready
- **AND THEN** it does not invoke a privileged control operation

#### Scenario: Reply Request Arrives During an Active Turn

- **WHEN** a `request_reply` event reaches a busy body
- **THEN** its delivery follows the selected waiting and batching policy used for ordinary chat
- **AND THEN** the body receives it through ordinary ready-only admission

#### Scenario: A Valid Offer Carries a CCCC Sender Label

- **WHEN** a valid chat offer reaches the configured Actor under its current receiver lease with its CCCC sender label
- **THEN** the gateway treats the sender label as attribution and applies ordinary delivery admission using the configured service binding
- **AND THEN** the agent decides whether and how to act under its current rules and permissions

### Requirement: Chat Acceptance Requires Two Real Coding Agents

Issue #77 and issue #100 acceptance SHALL require successful chat receive and reply with two real managed coding agents using distinct Actors against compatible actual CCCC. The smoke SHALL supplement deterministic stand-in, installed-package, and actual-provider tests. Missing model credentials or unsuccessful execution SHALL leave real-agent acceptance pending.

#### Scenario: Real Agent Receives Chat and Replies

- **WHEN** one real managed coding agent sends chat and the second receives its ordinary gateway notification
- **THEN** the second agent replies through its own gateway with verified native reply ancestry
- **AND THEN** the evidence identifies both real clients and Actor bindings without exposing credentials or changing body MCP configuration

#### Scenario: Real Agent Receives a Compact Ordered Batch

- **WHEN** messages from a real managed sender reach a real managed receiver as one timed push batch or one scheduled pull batch
- **THEN** the receiver sees one prompt with ordered sender and timestamp fields and uses individual handles to reply to the intended messages
- **AND THEN** the acceptance evidence verifies native ancestry and exact per-message handoff receipts

#### Scenario: Stand-In Tests Pass but Real-Agent Smoke Has Not Passed

- **WHEN** deterministic and actual-service tests pass but model credentials are unavailable or the required real-agent smoke fails
- **THEN** the affected issue's acceptance remains pending and the live check is reported as blocked or unsuccessful

### Requirement: CCCC CLI Diagnoses Gateway Endpoint and Managed-Self Selection

`houmao-cccc` SHALL support verified managed self and explicit authorized gateway selection. Explicit selection SHALL use `--gateway-url` for the base URL and `--instance` for the plugin namespace. Direct mode SHALL require a selected private profile. Invalid gateway URLs and unavailable managed-self authority SHALL return distinct actionable JSON errors before HTTP access. Gateway authorization failures and uncertain mutations SHALL stay bound to the original request.

#### Scenario: Agent Supplies the Advertised Plugin URL

- **WHEN** an agent passes `http://127.0.0.1:PORT/v1/plugins/INSTANCE` as `--gateway-url`
- **THEN** the CLI returns a nonzero exit with `invalid_gateway_url` and guidance to use the gateway base URL with `--instance` to select the plugin

#### Scenario: Gateway URL Contains Invalid or Private Input

- **WHEN** the supplied gateway URL is malformed or contains credentials
- **THEN** the CLI returns `invalid_gateway_url` and emits only safe diagnostics that exclude the input URL and raw exception text

#### Scenario: Current Managed Self Authority Cannot Be Selected

- **WHEN** a well-formed gateway base URL is supplied and the selected managed-self authority cannot be verified for it
- **THEN** the CLI returns a nonzero exit with `managed_self_authority_unavailable` and guidance to verify the current owning gateway and generation
- **AND THEN** the call ends under the selected caller identity before any signing or HTTP request

#### Scenario: Enrolled Caller Selects a Prefixed HTTPS Gateway

- **WHEN** an enrolled caller supplies the exact HTTPS base URL from its signer binding, including a configured proxy prefix
- **THEN** the CLI uses the shared gateway client's endpoint and signer checks and appends the selected plugin route under that prefix

#### Scenario: A Gateway Mutation Has an Authorization Failure or Uncertain Result

- **WHEN** the CLI receives an authorization error or cannot establish the outcome of a gateway mutation
- **THEN** it reports that gateway result and the applicable operation identity for reconciliation
- **AND THEN** the CLI makes no replacement provider call using a direct profile

### Requirement: The Installed CCCC CLI Explains Common Commands

`houmao-cccc --version` SHALL print the installed CLI distribution version and exit successfully. Top-level and command-specific help SHALL explain mode-specific usage. Help and version SHALL work without resolving a caller identity, opening a binding or profile, or connecting to a gateway or CCCC.

#### Scenario: Operator Checks an Installed Build

- **WHEN** an operator runs `houmao-cccc --version` from the installed distribution without a subcommand or connection configuration
- **THEN** the CLI reports the installed `houmao-cccc` distribution version and exits zero

#### Scenario: Agent Looks Up Common Gateway Commands

- **WHEN** an agent runs `houmao-cccc --help`
- **THEN** help gives exact gateway examples for `binding`, `members`, `chat send`, `chat reply`, `chat history`, and `chat deliveries`
- **AND THEN** it explains that the gateway instance selects the Group, that a gateway send takes the token from `members`, and where to find the handle for reply and receipt lookup
- **AND THEN** it shows direct-profile examples separately, with the target forms that apply to direct mode

#### Scenario: Agent Checks Which Receipt Target to Supply

- **WHEN** an agent runs `houmao-cccc chat deliveries --help`
- **THEN** help identifies `--handle` and `--event-ref` as gateway targets and `--event-id` as the direct target

### Requirement: CCCC CLI Reports Safe Usage Errors

The CLI SHALL report unsupported options and inapplicable delivery targets as actionable typed usage errors. Usage diagnostics SHALL identify the offending option where it can be safely named and omit user-supplied option values, credentials, private paths, message content, and raw exceptions.

#### Scenario: A Gateway Receipt Lookup Uses a Native Event ID

- **WHEN** a gateway-mode caller supplies `chat deliveries --event-id`
- **THEN** the CLI reports `gateway_delivery_requires_event_ref_or_handle` and points to `--handle` or `--event-ref` before contacting the gateway

#### Scenario: A Direct Receipt Lookup Uses a Gateway Target

- **WHEN** a direct-profile caller supplies `chat deliveries --handle` or `chat deliveries --event-ref`
- **THEN** the CLI reports `direct_delivery_requires_event_id` and points to `--event-id` before opening the profile or contacting CCCC

#### Scenario: A Command Receives an Unsupported Flag

- **WHEN** a caller supplies an unsupported option with a sensitive value in either separate or `--option=value` form
- **THEN** the CLI returns `unsupported_option`, names the safe option identifier, and directs the caller to help
- **AND THEN** the value is absent from the output

### Requirement: Incoming Chat Identifies CLI Reply Inputs

A CCCC chat notification SHALL have one host-written header above one request fence. The header SHALL identify the receiving CCCC Group and Actor, show the resolved owner-local gateway base URL once, and list relative paths for binding inspection, message details, and reply. The fence SHALL contain each message's sender, original CCCC timestamp, mode, body, and reply handle in CCCC delivery order. Each handle SHALL carry local instance selection for the verified managed CLI.

#### Scenario: The Header Identifies the Recipient and Its Gateway APIs

- **WHEN** the host renders chat for the selected CCCC instance on its live gateway
- **THEN** the header above the fence states the bound receiving Group and Actor and the resolved gateway base URL once
- **AND THEN** it lists `GET /v1/plugins/{instance}/binding`, `GET /v1/plugins/{instance}/messages/{handle}`, and `POST /v1/plugins/{instance}/chat/reply` for the selected instance as paths relative to that base URL
- **AND THEN** it names `handle`, `operation_id`, and `text` as the reply fields

#### Scenario: Agent Replies Through a Nondefault Instance

- **WHEN** the gateway hands off chat received through a plugin instance other than `cccc`
- **THEN** the agent can pass the message's handle and its operation ID and reply text to `houmao-cccc`
- **AND THEN** the CLI resolves the verified owning gateway and the local instance selected by the handle

#### Scenario: A Batch Contains Messages With Different Senders and Times

- **WHEN** the gateway delivers messages that CCCC has ordered for one Actor
- **THEN** it sends one notification with one request fence containing the complete ordered list of senders, original timestamps, modes, text, and distinct handles
- **AND THEN** neither the displayed timestamp nor the reply mode changes that ordering

#### Scenario: The Gateway Delivers a Single Message

- **WHEN** a push or scheduled pull delivery contains one chat message
- **THEN** the gateway renders its one entry within one request fence

#### Scenario: The Notification Bounds Its Agent-Facing Projection

- **WHEN** CCCC offers a message with internal service and gateway correlation fields
- **THEN** the host renders the explicit compact message fields as quoted ordinary request content
- **AND THEN** provider event IDs, signed provider references, full binding and runtime IDs, and credentials remain outside the agent-visible prompt

### Requirement: Delivery Lookup Returns Newest Attempts First

Gateway chat delivery lookup and the corresponding CLI command SHALL accept exactly one current message handle or scoped event reference. Direct CLI lookup SHALL accept exactly one native event ID and apply the selected Actor profile's visibility. Lookup SHALL report the retained attempts in reverse creation order, use the requested limit to select the newest matches, and set `has_more` when older matches were omitted.

#### Scenario: Sender Inspects a Refused Attempt and Its Accepted Retry

- **WHEN** the sender reads receipts for an event whose initial handoff was refused and whose explicit retry was accepted
- **THEN** the result lists the accepted retry before the refused original, with distinct provider attempt IDs for the same event
- **AND THEN** a limit of one returns the retry with `has_more` set to true

#### Scenario: Agent Reads Receipts by Message Handle

- **WHEN** an authorized gateway caller selects its incoming message by the handle in the request fence or its outgoing event by `event.handle` from a send or reply result
- **THEN** `GET /v1/plugins/{instance}/chat/deliveries?handle=HANDLE` and `houmao-cccc chat deliveries --handle HANDLE` return the same exact Actor-visible receipt projection as a valid reference for that event
- **AND THEN** the lookup submits no delivery claim, acknowledgement, or retry

#### Scenario: The Handle Belongs to a Nondefault Instance

- **WHEN** a CLI caller uses a valid handle without `--instance`
- **THEN** the CLI uses the handle's instance on the verified gateway
- **AND THEN** an explicit conflicting `--instance` fails before making the request

#### Scenario: Gateway Receives an Invalid Target Combination

- **WHEN** the gateway receives no receipt selector, both selector forms, a repeated selector, or a native event ID as the selector
- **THEN** it rejects the lookup with a typed usage error before requesting any provider receipts

#### Scenario: A Receipt Target Is Stale or Outside Its Scope

- **WHEN** a caller authorized for the selected receipt route submits a handle from an earlier gateway run or receiver generation, an expired handle, or a handle scoped to a different owner, instance, Actor binding, or Group
- **THEN** the gateway reports `message_handle_stale` with HTTP 409 before issuing a provider receipt lookup
- **AND THEN** the CLI guides the caller to select the event from authorized chat history

#### Scenario: A Receipt Reference Is Invalid or Outside Its Scope

- **WHEN** a caller submits a mistyped or out-of-scope gateway event reference
- **THEN** the gateway reports `reference_scope_error` with HTTP 422
- **AND THEN** the CLI guides the caller to select the event from authorized chat history

### Requirement: Scheduled Pull Defines One Batch per Snapshot

In gateway pull mode, each scheduled pull with staging capacity SHALL select one bounded CCCC snapshot. Each non-empty result SHALL define exactly one notification batch. The gateway SHALL dispatch that batch when the current body can receive an ordinary prompt.

#### Scenario: A Scheduled Pull Finds Several Messages

- **WHEN** a scheduled pull returns several pending messages at its snapshot boundary
- **THEN** the gateway prepares one notification containing the complete ordered result
- **AND THEN** each later pull defines its own batch regardless of how close together the pulls occur

#### Scenario: A Scheduled Pull Finds No Messages

- **WHEN** the scheduled pull returns an empty snapshot
- **THEN** the gateway sends no prompt for that pull
- **AND THEN** a later arrival is eligible at the next scheduled pull with available capacity

#### Scenario: Pull Runs During a Busy Turn

- **WHEN** a pull returns pending messages while the body is executing a turn
- **THEN** the batch keeps its original membership and waits for readiness
- **AND THEN** the gateway dispatches waiting batches in order

### Requirement: Push ASAP Delivers Individual Messages in Order

With push set to `asap`, each newly staged message SHALL form one single-message batch. The gateway SHALL promptly deliver the oldest batch when the current body can receive ordinary input. Messages arriving during an active turn SHALL wait in CCCC delivery order.

#### Scenario: A Push Arrives While the Body Is Idle

- **WHEN** an offer reaches a ready body with no earlier message waiting
- **THEN** the gateway hands it off as one ordinary prompt without a batching delay

#### Scenario: More Push Messages Arrive While the Body Is Busy

- **WHEN** subsequent messages arrive during an active turn
- **THEN** those messages remain pending
- **AND THEN** the gateway hands them off individually in CCCC delivery order as the body becomes ready

### Requirement: Push Batching Uses Quiet and Maximum Wait Deadlines

With push set to `batch`, the first staged message SHALL start a batch. The batch SHALL close at the earlier of the quiet interval after the last newly staged message and the maximum wait after the first. If the body is busy at closure, the closed batch SHALL wait for ordinary readiness.

#### Scenario: A Short Burst Ends Before the Maximum Wait

- **WHEN** messages arrive before the open batch's deadline and then no new message arrives for the configured quiet interval
- **THEN** those messages appear together in one batch that closes when the quiet interval expires

#### Scenario: A Continuous Burst Reaches the Maximum Wait

- **WHEN** new messages keep arriving before the quiet interval expires
- **THEN** the batch closes at the maximum wait measured from its first arrival
- **AND THEN** an offer arriving at or after that deadline belongs to a later batch

#### Scenario: An Offer Arrives When the Quiet Deadline Is Due

- **WHEN** a new offer arrives exactly at the open batch's quiet deadline
- **THEN** the gateway closes the existing batch first and admits the offer to a new batch
- **AND THEN** repeated offers for the same staged message do not advance either deadline

#### Scenario: A Timed Batch Closes During a Busy Turn

- **WHEN** the batch reaches its deadline while the body cannot receive a prompt
- **THEN** the closed batch keeps its membership and waits for readiness
- **AND THEN** later arrivals form later batches and the gateway hands off closed batches in order

### Requirement: Direct CLI Pull Returns One Ordered Chat Result

Direct `houmao-cccc` SHALL provide an on-demand pull under its selected Actor profile. A non-empty pull SHALL return one ordered result, with sender, original timestamp, mode, body, and a scoped message reference for each entry. It SHALL include a receipt the agent can acknowledge separately. The direct client SHALL support pull only.

#### Scenario: An Agent Pulls Chat Without a Running Gateway

- **WHEN** an agent selects a valid direct profile and requests chat for which it can acquire the Actor's pull lease
- **THEN** the CLI returns one bounded CCCC delivery snapshot in CCCC delivery order
- **AND THEN** the agent receives it as a CLI tool result without a gateway prompt

#### Scenario: An Agent Acknowledges or Replies to a Direct Pull

- **WHEN** the same Actor uses a subsequent direct invocation to present its unexpired batch receipt or a scoped message reference
- **THEN** CCCC records a direct read for that exact batch or a reply to that exact message, respectively
- **AND THEN** acknowledgment remains distinct from a confirmed gateway handoff

#### Scenario: A Gateway Still Holds the Actor Lease

- **WHEN** a direct invocation attempts a pull while that Actor has a current gateway receiver lease
- **THEN** the CLI reports the provider's lease conflict without taking over intake
