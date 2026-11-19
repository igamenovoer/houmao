# Spec Delta

## ADDED Requirements

### Requirement: DSH headless executes the native one-shot profile

For each accepted headless prompt Houmao SHALL start exactly one qualified `dsh --profile headless --json` worker in the selected home and workspace, parse its newline-delimited JSON stdout, and preserve diagnostics separately. A malformed stream, unsupported build, or unexpected exit SHALL produce a bounded failure or uncertain outcome.

#### Scenario: A new prompt starts

- **WHEN** the verified headless owner admits input for a new conversation
- **THEN** one native CLI worker starts and its session record binds the attempt to the reported native ID
- **AND** a session record alone does not establish native prompt admission

#### Scenario: A stream ends without settlement

- **WHEN** the native worker emits partial events and exits without a recognized terminal outcome
- **THEN** the owner preserves private artifacts and partial evidence and does not mark the turn complete

### Requirement: Interruption targets the verified one-shot attempt

Houmao SHALL interrupt and reap only the captured process tree of the active one-shot attempt. The owner SHALL fence replacement processes and preserve partial native evidence. A signal or a controller timeout alone SHALL NOT count as provider-confirmed interruption or release an unresolved slot.

#### Scenario: Native CLI worker is still active

- **WHEN** an operator targets the current attempt for interruption
- **THEN** the owner verifies its identity, applies bounded process interruption, and records native or owner-observed termination and its evidence source

#### Scenario: A stale interrupt arrives

- **WHEN** the requested attempt has exited and the next attempt owns the slot
- **THEN** the interrupt leaves the replacement worker untouched

### Requirement: DSH CLI home discovery preserves exact one-shot continuity

CLI-qualified next-invocation discovery for skills or MCP SHALL preserve exact native conversation, dispatch, credential-isolation, and usage contracts. Refresh SHALL neither replay input nor restart an active attempt. Common limitations SHALL remain explicit; unrelated pending native-special-plugin changes SHALL NOT invalidate confirmed common discovery.

#### Scenario: Skills Are Added Updated and Removed Between Workers
- **WHEN** a caller adds, edits, or removes skills in one DSH native home and requests qualified automatic refresh
- **THEN** the next ordinary invocation discovers that home's current skill state in the same selected conversation
- **AND** the refresh itself launches no worker and changes no other agent's home

#### Scenario: Current CLI Attempt Is Still Running
- **WHEN** home refresh is requested while a one-shot CLI attempt is active
- **THEN** a qualified automatic result refers only to its later native boundary, or an unsupported live action is refused explicitly
- **AND** the active attempt is not interrupted, restarted, replayed, or replaced

#### Scenario: Explicit Invocation Overrides Are Present
- **WHEN** a subsequent ordinary DSH invocation has supported request-scoped model controls
- **THEN** those controls retain their documented temporary precedence without rewriting persistent home files
- **AND** exact continuation, dispatch fencing, and accounting remain bound to the original managed authority

### Requirement: DSH CLI headless observation reports verified freshness

DSH headless observation SHALL identify common coverage, evidence, and native boundaries independently of Houmao update receipts. Between workers it SHALL report qualified future behavior and unavailable live evidence explicitly. Automatic native updates SHALL be accepted, while unknown coverage SHALL NOT justify an already-current no-op.

#### Scenario: No CLI Worker Is Live
- **WHEN** a valid headless envelope is inspected between invocations
- **THEN** the result distinguishes current-input evidence from qualified next-turn discovery and unavailable live-worker observations
- **AND** no worker is started to manufacture evidence

#### Scenario: Native Update Has No Houmao Receipt
- **WHEN** external or native tooling changes DSH skills/MCP outside Houmao
- **THEN** observation evaluates available effective-input/runtime evidence without requiring a Houmao update record

#### Scenario: Launch Overlay Masks a Common Edit
- **WHEN** a retained invocation override prevents an edited common input from taking effect
- **THEN** the result exposes that precedence limitation or unknown coverage
- **AND** it does not infer current common state merely from the edited file's presence

#### Scenario: A Read Would Require Forced Native Work
- **WHEN** complete freshness would require starting a new CLI invocation or issuing a mutating refresh request
- **THEN** the read-only observation preserves the evidence limitation instead of performing that work

### Requirement: DSH CLI failures expose bounded redacted native diagnostics

When a managed DSH CLI emits a native error or its worker fails during startup, execution, or closure, Houmao SHALL include a bounded, secret-redacted diagnostic summary of the remote error message or worker failure output in the surfaced execution error while preserving full raw diagnostics only in user-private turn artifacts. Resolved secret environment values and bearer or API-key tokens SHALL never appear in surfaced error text.

#### Scenario: Upstream HTTP Rejection Surfaces Redacted Detail
- **WHEN** an upstream model endpoint rejects a DSH CLI turn with an HTTP or provider validation message in its native error or diagnostics
- **THEN** the failed turn reports the available native status and sanitized error message across CLI stderr and gateway turn status
- **AND THEN** the managed diagnostic preserves the available provider cause

#### Scenario: Secret Values Are Redacted From Surfaced CLI Errors
- **WHEN** a CLI error event or worker stderr output contains a resolved API key value or bearer token from the DSH private environment
- **THEN** Houmao replaces the secret value with `[REDACTED]` before surfacing the diagnostic in exceptions, gateway responses, or console logs

#### Scenario: Worker Startup Crash Surfaces Sanitized Stderr Summary
- **WHEN** the DSH CLI worker exits or closes stdout before producing a terminal result due to a configuration or plugin error written to stderr
- **THEN** the surfaced protocol failure includes a bounded, secret-redacted summary of the worker stderr output alongside the failure status

## MODIFIED Requirements

### Requirement: DSH Continuation Selects an Exact Native Session

The adapter SHALL create a native session only for an explicit new-conversation selection. Subsequent managed turns SHALL resume the saved exact native session in its recorded workspace. Missing, incompatible, occupied, or mismatched sessions SHALL fail without falling back to a new or latest conversation.

#### Scenario: A Later Process Continues the Conversation
- **WHEN** a completed turn's one-shot CLI process has exited and the caller submits another prompt to the same managed conversation
- **THEN** the new process passes `--session-id` with the exact saved ID and resumes that native session and preserves its history

#### Scenario: Saved Session Cannot Be Resumed
- **WHEN** the saved native session is missing or belongs to a different workspace
- **THEN** continuation fails before prompt submission and preserves the saved identity for diagnosis

#### Scenario: Native continuation fails its adoption checks

- **WHEN** the selected native session has an incompatible preset, is a subagent, or fails native workspace or continuity checks
- **THEN** the attempt reports the failure without retrying against any other session

### Requirement: Prompt Dispatch and Completion Have Distinct Evidence

A sent request SHALL NOT by itself establish native admission or completion. Confirmed handoff SHALL require bound native admission or turn evidence, or successful correlated prompt settlement. A native `final` event SHALL produce a result from its reported reason after worker exit and stream closure are reconciled, and incomplete or failed work SHALL NOT be reported as successful completion.

#### Scenario: Driver Starts Before Native Admission
- **WHEN** the Houmao driver process starts but DSH fails initialization or prompt admission
- **THEN** the request fails without a successful semantic-handoff claim

#### Scenario: Provider Stops at an Output Limit
- **WHEN** a native terminal event carries a reason indicating a limit or other incomplete outcome
- **THEN** the managed result retains that reason and is not reported as normally completed

#### Scenario: Only a native session ID is available

- **WHEN** the worker emits a session ID but dies before any bound input or turn evidence
- **THEN** the request preserves its actual dispatch uncertainty and does not claim a successful handoff

### Requirement: Turn Closure Preserves Native Persistence and Process Ownership

Each headless turn SHALL close and flush its native session and reap its one-shot CLI process before relinquishing owned execution resources. Cleanup failure SHALL remain explicit. A controller timeout with execution still active SHALL preserve a pending attempt rather than falsely finalizing it or starting an overlapping process.

#### Scenario: Prompt Completes Before Persistence Flush Fails
- **WHEN** native events or the journal show a turn outcome but a persistence failure or abnormal process exit prevents verified closure
- **THEN** the managed result exposes that failure separately from the observed native outcome
- **AND THEN** a later attempt is not silently substituted for the failed closure

#### Scenario: Controller Times Out During Active Execution
- **WHEN** a controller stops waiting while the owned one-shot attempt is still running
- **THEN** recovery retains that attempt's identity and active or uncertain posture until terminal evidence exists

### Requirement: DSH Operation Support Is Explicit

DSH headless capability inspection SHALL identify supported creation, exact resume, prompting, cancellation, closure, native prompt, skills, accounting sources, common-plugin observation, and home refresh. Skills and MCP discovery SHALL report only capabilities independently qualified for the native CLI. An input requiring ACP initialization or a wire request SHALL be refused before invocation. Unsupported load, transcript replay, deletion, fork, additional-workspace, raw-key, or ACP reload SHALL fail explicitly without emulation through ordinary chat.

#### Scenario: Caller Requests Unsupported Session Fork
- **WHEN** a caller requests a DSH operation that the qualified native CLI does not support
- **THEN** Houmao reports that operation as unsupported without creating another native session

#### Scenario: Profile Files Change During a Turn
- **WHEN** DSH profile files change while a managed headless turn is active
- **THEN** Houmao does not claim coordinated live activation merely because the files changed

#### Scenario: Qualified Home Refresh Needs No ACP Request
- **WHEN** an active DSH envelope has qualified next-invocation discovery for a requested resource and receives home refresh between workers
- **THEN** refresh reports an automatic future-boundary result without starting a CLI worker or sending a provider request
- **AND** it does not claim that a worker's live common state has already been inspected

#### Scenario: Unsupported Native Reload Remains Explicit
- **WHEN** a caller requests an ACP wire reload that the selected native implementation does not support
- **THEN** the operation remains unsupported even if Houmao can report automatic home discovery on the next invocation
- **AND** no ordinary chat message is used to emulate the missing wire operation

### Requirement: DSH Turn Preparation Preserves Current Materialized Home Inputs

Ordinary DSH CLI invocation SHALL consume current materialized native inputs, including independently qualified skills or MCP declarations, without regenerating profile, role, or persistent configuration from launch manifests. Per-attempt control and evidence SHALL remain private transient inputs. Native precedence SHALL remain explicit and launch/relaunch SHALL retain their separate materialization rules.

#### Scenario: Native Configuration Was Edited Before the Next Turn
- **WHEN** an operator edits the materialized DSH profile or supported MCP declarations and later submits an ordinary prompt after qualified automatic refresh
- **THEN** that invocation consumes the current native home according to native precedence
- **AND** turn preparation does not restore the preceding launch-generated profile or MCP declaration

#### Scenario: Launch Profile Changed Without Relaunch
- **WHEN** the stored Houmao launch profile changes after a DSH home has been materialized
- **AND** the caller invokes native-home refresh and then submits an ordinary prompt
- **THEN** refresh and turn preparation preserve the current materialized role and profile bytes
- **AND** they do not recompose a new system prompt from the edited launch profile

#### Scenario: Required Materialized Input Was Removed
- **WHEN** a caller removes a required materialized native input before the next CLI invocation
- **THEN** native validation fails explicitly if that input is required
- **AND** the invocation does not repair it by regenerating launch material or creating a different conversation

#### Scenario: A declaration requires ACP injection

- **WHEN** the selected MCP input is available only through ACP initialization and no qualified CLI projection exists
- **THEN** launch or turn preflight rejects that combination before provider invocation and identifies the declaration without exposing credentials

## REMOVED Requirements

### Requirement: DSH Headless Control Uses a Qualified ACP Connection

**Reason**: Headless selects a one-shot native CLI process.

**Migration**: Select `service` for the persistent DSH ACP contract in change 04.

### Requirement: ACP Updates and Client Requests Remain Serviceable During a Prompt

**Reason**: The native headless profile emits a JSON event stream and does not exchange ACP requests.

**Migration**: Use native CLI events for headless output and the DSH service adapter for negotiated reverse requests.

### Requirement: DSH Interruption Uses Native Cancellation Before Forced Exit

**Reason**: The one-shot CLI has a captured process tree and no ACP cancellation channel.

**Migration**: Interrupt only the verified active CLI attempt and reconcile its recorded outcome.

### Requirement: DSH Automatic Home Discovery Preserves Native Continuity

**Reason**: Worker boundaries and qualification now refer to the native headless CLI.

**Migration**: Qualify each resource against a new CLI invocation in the same native conversation.

### Requirement: DSH Headless Observation Does Not Fabricate Live Freshness

**Reason**: The old scenarios described an ACP worker and its read boundaries.

**Migration**: Report current native inputs and the CLI's next qualified read boundary.

### Requirement: DSH Headless Failures Surface Secret-Redacted Provider Diagnostics

**Reason**: JSON-RPC errors are specific to the service adapter.

**Migration**: Use the native headless event stream and worker stderr for bounded, redacted diagnostics.
