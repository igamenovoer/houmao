# Spec Delta

## Purpose

Define explicit CCCC deferred Mail operations and authoritative ordered-batch consumption without changing Houmao email identities, introducing gateway message retention, or hiding uncertain outcomes.

## ADDED Requirements

### Requirement: Mail Extends the Qualified CCCC Binding

Deferred Mail SHALL reuse the owner, Actor registration, credentials, references, and connection authority established by the CCCC chat integration. It SHALL be enabled only when provider and plugin advertise the complete qualified Mail operations, limits, cursor, and read-reconciliation contract.

#### Scenario: Chat Works but Provider Lacks Read Reconciliation

- **WHEN** a compatible chat service lacks the required consuming-read receipts
- **THEN** chat remains available and Mail read is reported unsupported
- **AND THEN** the integration does not fall back to unsafe native consuming reads

#### Scenario: Mail Package Upgrade Preserves Owner

- **WHEN** an operator upgrades the plugin and restarts only the gateway with the same binding
- **THEN** the agent ID, Actor, body PID, and conversation remain unchanged

### Requirement: CCCC Mail Is Explicitly Selected Outside Email Slots

Mail requests SHALL explicitly select the CCCC plugin instance and current binding. CCCC Mail SHALL NOT occupy or replace offline or online email, determine canonical mail identity, or become an implicit email transport. Neither successful operation nor provider outage SHALL bridge these channels.

#### Scenario: All Communication Systems Coexist

- **WHEN** an agent has offline email, online Stalwart email, and CCCC Mail
- **THEN** all remain separately selectable and canonical mail identity follows the configured email slots only

#### Scenario: Stalwart Is Unavailable

- **WHEN** the caller explicitly selects CCCC Mail during a Stalwart outage
- **THEN** supported CCCC operations remain usable without contacting Stalwart or changing canonical identity

#### Scenario: Email Send Has an Uncertain Outcome

- **WHEN** an email send might have succeeded before its connection failed
- **THEN** the integration does not mirror or retry that message through CCCC

### Requirement: Mail Recipients Are Qualified CCCC Actors

Mail send SHALL require explicit recipients in the binding's advertised Actor scope and derive the sender from the owner grant. Human-user audiences, arbitrary email addresses, offline principals, and unsupported cross-Group recipients SHALL fail before mutation without address translation.

#### Scenario: Sender Uses an Actor Recipient

- **WHEN** the caller selects an authorized Actor in the bound Group
- **THEN** CCCC stores deferred Mail under the owner's Actor identity

#### Scenario: Recipient Is an Email Address or Human User

- **WHEN** a Mail request targets an external email address, offline principal, or CCCC `user`
- **THEN** it returns a structured unsupported-recipient error without creating mail in any backend

### Requirement: Mail Send and Reply Remain Deferred

The Mail send and reply operations SHALL use native `mail` mode, preserve event IDs and structured reply ancestry, and use scoped caller operation IDs. They SHALL report storage acceptance separately from consumption or task completion and SHALL NOT promote correspondence into direct chat delivery.

#### Scenario: Agent Replies Through the Mail Surface

- **WHEN** an agent replies to a scoped CCCC event through Mail
- **THEN** the new event uses `mail` mode and the original native event remains its reply parent
- **AND THEN** neither a direct prompt nor an email-provider mutation is implied

#### Scenario: Send Response Is Lost

- **WHEN** CCCC may have committed a Mail send or reply before the response is lost
- **THEN** the result is uncertain and exposes its operation identity for explicit reconciliation
- **AND THEN** the plugin does not automatically resend or switch providers

### Requirement: Inspection Does Not Consume Mail

Mail status, peek, cursor inspection, receipt lookup, and chat history SHALL NOT advance the deferred-inbox cursor. Peek SHALL return a bounded next-batch view and current scoped cursor. Status SHALL distinguish unknown, stale, sampled, or capped counts from authoritative complete counts.

#### Scenario: Agent Peeks Repeatedly

- **WHEN** an agent repeats peek and status against an unchanged pending batch
- **THEN** the same messages remain eligible and no Mail-read fact is created

#### Scenario: Cached Status Is Stale During an Outage

- **WHEN** the provider is unavailable after a previous Mail observation
- **THEN** status identifies the observation's age and unavailable current truth instead of reporting an empty inbox

### Requirement: Read Consumes the Next Ordered Batch

An explicit Mail read SHALL consume only the next Actor-visible deferred batch in provider append order. It SHALL accept the expected current cursor, operation ID, count bound, and byte bound, and return the committed boundary with its result. Direct chat traffic SHALL NOT be consumed or replayed as Mail.

#### Scenario: Inbox Contains Interleaved Chat and Mail

- **WHEN** the caller consumes its next Mail batch from interleaved ledger traffic
- **THEN** only eligible Mail events are returned in append order and the cursor commits through the returned batch boundary

#### Scenario: More Mail Remains

- **WHEN** the inbox contains more eligible Mail than one bounded batch
- **THEN** read advances only through that batch and reports remaining work without claiming all Mail was consumed

### Requirement: Limits Are Applied Before Cursor Advancement

The provider SHALL choose a complete leading batch within negotiated count and byte budgets before committing a read. It SHALL NOT consume messages later omitted or silently truncated by the plugin. If the first eligible message cannot fit, read SHALL fail visibly without advancing its cursor.

#### Scenario: Count Limit Splits a Batch

- **WHEN** the caller requests fewer messages than are pending
- **THEN** only that leading subset is consumed and later messages remain pending

#### Scenario: First Message Exceeds the Supported Byte Limit

- **WHEN** the first eligible message cannot fit the allowed complete-read budget
- **THEN** the operation reports an explicit content-limit error without skipping or consuming it

### Requirement: Cursor Preconditions Serialize Consumption

Mail consumption SHALL compare the expected authoritative cursor while serializing the Actor's read mutation. Competing reads from the same cursor SHALL not independently consume successive batches. A mismatched cursor SHALL return a conflict without changing consumption state.

#### Scenario: Two Callers Read From the Same Cursor

- **WHEN** two distinct read operations race using one expected cursor
- **THEN** at most one consumes a batch and the other receives a cursor conflict

#### Scenario: Gateway Has an Old Cursor After Reconnect

- **WHEN** a read presents a cursor superseded by another confirmed consumer
- **THEN** it fails without consuming the next batch and the caller can inspect the current cursor explicitly

### Requirement: Read Operation Receipts Are Authoritative and Durable

The provider SHALL commit a read operation identity and its exact before/after boundary, bounded event references, and outcome with consumption. Matching reuse SHALL resolve that original operation without consuming another batch; conflicting reuse SHALL fail. Empty reads SHALL also retain a stable completed outcome.

#### Scenario: Matching Read Operation Is Repeated

- **WHEN** a caller explicitly repeats a completed read operation with the same request
- **THEN** it receives the original operation receipt without consuming later Mail
- **AND THEN** an already-completed result is distinguishable from a newly read empty inbox

#### Scenario: New Mail Arrives After an Empty Read

- **WHEN** an empty read completed and new Mail arrives before its operation ID is repeated
- **THEN** repeating that operation remains an empty completed result and leaves the new Mail pending

#### Scenario: Read ID Is Reused With Another Request

- **WHEN** a read operation ID is reused with another cursor, count, or byte limit
- **THEN** the provider returns a conflict without another consumption

### Requirement: Lost Read Responses Have Explicit Reconciliation

A lost or interrupted consuming-read response SHALL be reported as uncertain without automatic mutation retry. The caller SHALL be able to inspect its scoped operation receipt and current cursor without consumption, then retrieve consumed event content through non-consuming history. Reconciliation SHALL NOT infer a failed read merely from a missing response.

#### Scenario: Response Is Lost After Commit

- **WHEN** CCCC commits the read but the gateway cannot return its batch
- **THEN** receipt lookup identifies the consumed event references and boundary
- **AND THEN** inspecting those events through history leaves the following batch untouched

#### Scenario: Provider Outcome Cannot Yet Be Established

- **WHEN** a read times out and reconciliation cannot determine whether it committed
- **THEN** the caller receives an unknown outcome rather than a fabricated failure or new read

### Requirement: Provider Restart Preserves Read Decisions

Provider crash recovery SHALL preserve committed read receipts and their effective cursor boundary, including interruption between the read fact and cursor persistence. Receipt retention or archival SHALL NOT silently make a completed operation ID eligible to consume again within the same Actor registration.

#### Scenario: CCCC Restarts Between Read Fact and Cursor Save

- **WHEN** CCCC restarts after committing a read fact but before publishing its cursor file
- **THEN** recovery exposes the committed boundary and receipt without returning that batch as unread

#### Scenario: Old Read Receipt Was Archived

- **WHEN** a caller repeats a previously completed operation whose receipt was archived or aged out of an active index
- **THEN** the provider resolves its original receipt or explicitly rejects it as expired
- **AND THEN** it never treats the operation ID as a fresh consuming read

### Requirement: Mail References Are Owner and Generation Scoped

Mail message, cursor, and read-operation references SHALL carry verifiable owner, binding, and Actor-registration scope. References from another owner, endpoint, Actor generation, or email channel SHALL fail before retrieval or mutation. Native CCCC event IDs SHALL remain available as provenance.

#### Scenario: Another Gateway Presents a Mail Cursor

- **WHEN** a gateway submits a cursor or receipt handle belonging to another Actor binding
- **THEN** it fails without inspecting or advancing either Actor's inbox

#### Scenario: Actor Identifier Is Reused

- **WHEN** a former Actor's reference is presented after recreation under the same identifier
- **THEN** the reference is stale and cannot target the new registration's Mail

### Requirement: Mail Does Not Emulate Email Lifecycle Operations

Capabilities SHALL expose deferred-batch consumption and its supported native operations explicitly. Unsupported per-message mark-unread, move, archive, email submission, or attachment operations SHALL fail without fake success. Replying or receiving a notice SHALL NOT implicitly advance the Mail cursor.

#### Scenario: Caller Requests Email Archive Semantics

- **WHEN** a caller tries to archive CCCC Mail through an unsupported operation
- **THEN** it receives a structured unsupported-operation result without consuming the batch

#### Scenario: Agent Replies Without Reading the Batch

- **WHEN** an agent sends a Mail reply using a visible event reference without a consuming read
- **THEN** the reply is recorded while the deferred-inbox cursor remains unchanged

### Requirement: Mail Notices Remain Deferred and Ordinary

CCCC Mail notices SHALL follow the provider's qualified bounded, content-free policy and immediate ordinary gateway admission. Inspection or synchronization SHALL NOT consume Mail or schedule body work. Refused notices SHALL not be retained by the plugin, and notice delivery SHALL not execute email reset, compaction, or archive workflows.

#### Scenario: Notice Arrives While Body Is Busy

- **WHEN** a CCCC Mail notice reaches a busy body
- **THEN** it reports the ordinary readiness refusal without queueing or reading the batch
- **AND THEN** later body readiness alone does not replay that notice

#### Scenario: Notice Reaches a Ready Body

- **WHEN** a valid content-free notice is handed to a ready body
- **THEN** it identifies CCCC Mail and its selected binding without advancing the Mail cursor

### Requirement: Existing Email Reminders Stay Independent

CCCC Mail SHALL preserve offline and online email reminder intervals, eligibility, and compaction state. CCCC's native notice policy SHALL NOT replace periodic email reminders or import their queue and archive semantics into plugin delivery.

#### Scenario: Unchanged Email Work Remains Eligible

- **WHEN** unchanged offline or Stalwart inbox work spans reminder intervals while CCCC Mail is enabled
- **THEN** its existing periodic reminders remain eligible under the email contract
- **AND THEN** CCCC notice or cursor activity does not reset email compaction history

### Requirement: Mail Qualification Covers Actual Cursor and Outage Boundaries

Qualification SHALL exercise the compatible provider's real consuming-read, receipt, and crash-recovery interfaces through independently installed plugin and Houmao packages. Evidence SHALL distinguish executed runtime checks from model smoke tests and unexecuted workloads, and SHALL exclude private credentials and message content by default.

#### Scenario: Two Actors Exchange Deferred Mail During Email Failure

- **WHEN** two qualified gateways exchange and consume CCCC Mail while their Stalwart endpoint is unavailable
- **THEN** native event IDs, ordered cursor advancement, reply ancestry, and independent canonical email identities are verified

#### Scenario: Qualification Uses Only a Fake Consuming Read

- **WHEN** only deterministic fake-provider tests have executed
- **THEN** the report does not claim live CCCC Mail compatibility or completed issue acceptance

### Requirement: Mail Acceptance Requires Two Real Coding Agents

Issue #78 acceptance SHALL require a successful deferred Mail send/read/reply smoke with two real managed coding agents using distinct gateways and Actors against compatible actual CCCC. It SHALL supplement deterministic stand-in and provider tests. A passed chat smoke alone SHALL NOT satisfy this gate; missing model credentials or unsuccessful execution SHALL leave Mail acceptance pending.

#### Scenario: Real Agents Exchange and Consume Deferred Mail

- **WHEN** one real managed coding agent sends deferred Mail and the other explicitly reads its next batch and replies through Mail
- **THEN** evidence verifies deferred mode, committed cursor advancement, and native reply ancestry under their distinct bindings
- **AND THEN** client/profile/result evidence excludes credentials and identifies the actual agent workflow

#### Scenario: Chat Smoke Passes but Real-Agent Mail Smoke Does Not

- **WHEN** chat qualification and deterministic Mail tests pass but the two-real-agent Mail smoke is unexecuted or unsuccessful
- **THEN** issue #78 acceptance remains pending without waiving or substituting the required Mail workflow
