# dsh-headless-control Specification

## Purpose

Define structured control of managed DeepSeek Harness headless agents through ACP, preserving exact conversation continuity and truthful execution outcomes.

## Requirements

### Requirement: DSH Headless Control Uses a Qualified ACP Connection

Managed DSH headless execution SHALL use ACP over stdio with a qualified executable and negotiated capabilities. Protocol traffic and diagnostics SHALL remain separate. Missing required capabilities or malformed protocol input SHALL fail explicitly before unsupported operations are attempted.

#### Scenario: Required Resume Capability Is Missing
- **WHEN** continuation targets a saved native session but initialization does not advertise supported resume
- **THEN** the attempt fails with an unsupported-operation diagnostic
- **AND THEN** no replacement conversation or prompt is created

#### Scenario: Provider Emits Invalid Protocol Output
- **WHEN** DSH emits malformed stdout or the connection closes unexpectedly
- **THEN** the attempt reports a protocol or execution failure and preserves safe diagnostics
- **AND THEN** rendered terminal text is not used to infer successful execution

### Requirement: DSH Continuation Selects an Exact Native Session

The adapter SHALL create a native session only for an explicit new-conversation selection. Subsequent managed turns SHALL resume the saved exact native session in its recorded workspace. Missing, incompatible, occupied, or mismatched sessions SHALL fail without falling back to a new or latest conversation.

#### Scenario: A Later Process Continues the Conversation
- **WHEN** a completed turn's ACP process has exited and the caller submits another prompt to the same managed conversation
- **THEN** the new process resumes the saved native session and preserves its history

#### Scenario: Saved Session Cannot Be Resumed
- **WHEN** the saved native session is missing or belongs to a different workspace
- **THEN** continuation fails before prompt submission and preserves the saved identity for diagnosis

### Requirement: ACP Updates and Client Requests Remain Serviceable During a Prompt

The connection SHALL consume session updates, correlate responses, and answer supported permission requests while a prompt is pending. Assistant messages, thoughts, tool lifecycle, configuration changes, and terminal outcomes SHALL retain their distinct semantic kinds. Unsupported interaction requests SHALL terminate or fail safely without an unattended hang.

#### Scenario: Permission Arrives Before Completion
- **WHEN** DSH asks for a permission decision during a pending prompt
- **THEN** the qualified unattended policy answers without blocking the protocol reader
- **AND THEN** native hard-deny rules remain enforceable

#### Scenario: An Update Belongs to Another Session
- **WHEN** an ACP update identifies a session other than the one bound to the managed attempt
- **THEN** it does not become output or handoff evidence for that attempt

### Requirement: Prompt Dispatch and Completion Have Distinct Evidence

A sent request SHALL NOT by itself establish native admission or completion. Confirmed handoff SHALL require bound native admission or turn evidence, or successful correlated prompt settlement. A prompt response SHALL produce a terminal result from its stop reason, and incomplete or failed work SHALL NOT be reported as successful completion.

#### Scenario: Driver Starts Before Native Admission
- **WHEN** the Houmao driver process starts but DSH fails initialization or prompt admission
- **THEN** the request fails without a successful semantic-handoff claim

#### Scenario: Provider Stops at an Output Limit
- **WHEN** a prompt settles with a stop reason indicating a limit or other incomplete outcome
- **THEN** the managed result retains that reason and is not reported as normally completed

### Requirement: DSH Interruption Uses Native Cancellation Before Forced Exit

Interruption SHALL target the active attempt's native session through ACP cancellation while continuing to consume its response and updates. A bounded cancellation failure SHALL permit terminating and reaping that attempt's process tree. Cancellation acknowledgement alone SHALL NOT imply completed work or authorize a retry.

#### Scenario: Native Cancellation Settles
- **WHEN** an operator interrupts active DSH work and ACP returns a cancelled outcome
- **THEN** the turn is finalized as interrupted and its partial output and usage remain available

#### Scenario: Native Cancellation Stalls
- **WHEN** cancellation fails to settle within its configured bound
- **THEN** Houmao terminates only the captured attempt's process tree and records the fallback
- **AND THEN** an unrelated or replacement process is not signalled

### Requirement: Turn Closure Preserves Native Persistence and Process Ownership

Each headless turn SHALL close and flush its native session and reap its ACP process before relinquishing owned execution resources. Cleanup failure SHALL remain explicit. A controller timeout with execution still active SHALL preserve a pending attempt rather than falsely finalizing it or starting an overlapping process.

#### Scenario: Prompt Completes Before Persistence Flush Fails
- **WHEN** ACP reports a terminal prompt outcome but session closure cannot confirm its persistence flush
- **THEN** the managed result exposes that failure separately from the observed native outcome
- **AND THEN** a later attempt is not silently substituted for the failed closure

#### Scenario: Controller Times Out During Active Execution
- **WHEN** a controller stops waiting while the owned ACP attempt is still running
- **THEN** recovery retains that attempt's identity and active or uncertain posture until terminal evidence exists

### Requirement: DSH Operation Support Is Explicit

DSH headless capability inspection SHALL identify supported creation, exact resume, prompting, cancellation, closure, native prompt, skills, accounting sources, common-plugin observation, and home refresh. Qualified skills/MCP discovery SHALL remain distinct from ACP wire reload. Unsupported load, transcript replay, deletion, fork, additional-workspace, raw-key, or ACP reload SHALL fail explicitly without emulation through ordinary chat.

#### Scenario: Caller Requests Unsupported Session Fork
- **WHEN** a caller requests a DSH operation that the qualified ACP implementation does not support
- **THEN** Houmao reports that operation as unsupported without creating another native session

#### Scenario: Profile Files Change During a Turn
- **WHEN** DSH profile files change while a managed headless turn is active
- **THEN** Houmao does not claim coordinated live activation merely because the files changed

#### Scenario: Qualified Home Refresh Needs No ACP Request
- **WHEN** an active DSH envelope has qualified next-invocation skills/MCP discovery and receives home refresh between workers
- **THEN** refresh reports an automatic future-boundary result without creating an ACP process or sending an ACP reload request
- **AND** it does not claim that a worker's live common state has already been inspected

#### Scenario: Unsupported Native Reload Remains Explicit
- **WHEN** a caller requests an ACP wire reload that the selected native implementation does not support
- **THEN** the operation remains unsupported even if Houmao can report automatic home discovery on the next invocation
- **AND** no ordinary chat message is used to emulate the missing wire operation

### Requirement: DSH Turn Preparation Preserves Current Materialized Home Inputs

Ordinary DSH ACP invocation SHALL consume current materialized native inputs, including skills/MCP, without regenerating profile, role, or persistent configuration from launch manifests. Per-attempt control and evidence SHALL remain private transient inputs. Native precedence SHALL remain explicit and launch/relaunch SHALL retain their separate materialization rules.

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
- **WHEN** a caller removes a required materialized native input before the next ACP invocation
- **THEN** native validation fails explicitly if that input is required
- **AND** the invocation does not repair it by regenerating launch material or creating a different conversation

### Requirement: DSH Automatic Home Discovery Preserves Native Continuity

Qualified next-invocation skills/MCP discovery SHALL preserve exact native conversation, dispatch, credential-isolation, and usage contracts. Refresh SHALL neither replay input nor restart an active attempt. Common limitations SHALL remain explicit; unrelated pending native-special-plugin changes SHALL NOT invalidate confirmed common discovery.

#### Scenario: Skills Are Added Updated and Removed Between Workers
- **WHEN** a caller adds, edits, or removes skills in one DSH native home and requests qualified automatic refresh
- **THEN** the next ordinary invocation discovers that home's current skill state in the same selected conversation
- **AND** the refresh itself launches no worker and changes no other agent's home

#### Scenario: Current ACP Attempt Is Still Running
- **WHEN** home refresh is requested while an ACP attempt is active
- **THEN** a qualified automatic result refers only to its later native boundary, or an unsupported live action is refused explicitly
- **AND** the active attempt is not interrupted, restarted, replayed, or replaced

#### Scenario: Explicit Invocation Overrides Are Present
- **WHEN** a subsequent ordinary DSH invocation has supported request-scoped model controls
- **THEN** those controls retain their documented temporary precedence without rewriting persistent home files
- **AND** exact continuation, dispatch fencing, and accounting remain bound to the original managed authority

### Requirement: DSH Headless Observation Does Not Fabricate Live Freshness

DSH headless observation SHALL identify common coverage, evidence, and native boundaries independently of Houmao update receipts. Between workers it SHALL report qualified future behavior and unavailable live evidence explicitly. Automatic native updates SHALL be accepted, while unknown coverage SHALL NOT justify an already-current no-op.

#### Scenario: No ACP Worker Is Live
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
- **WHEN** complete freshness would require starting ACP or issuing a mutating refresh request
- **THEN** the read-only observation preserves the evidence limitation instead of performing that work

### Requirement: DSH Headless Failures Surface Secret-Redacted Provider Diagnostics

When a managed DSH ACP request returns a JSON-RPC error or an ACP worker fails before completing initialization or prompt settlement, Houmao SHALL include a bounded, secret-redacted diagnostic summary of the remote error message or worker failure output in the surfaced execution error while preserving full raw diagnostics only in user-private turn artifacts. Resolved secret environment values and bearer or API-key tokens SHALL never appear in surfaced error text.

#### Scenario: Upstream HTTP Rejection Surfaces Redacted Detail
- **WHEN** an upstream model endpoint rejects a DSH ACP turn with an HTTP or provider validation message carried inside a JSON-RPC error response
- **THEN** the failed turn reports both the JSON-RPC error code and the sanitized error message across CLI stderr and gateway turn status
- **AND THEN** operators are not left with a bare `ACP request failed (-32603)` string

#### Scenario: Secret Values Are Redacted From Surfaced ACP Errors
- **WHEN** a JSON-RPC error payload or worker stderr output contains a resolved API key value or bearer token from the DSH private environment
- **THEN** Houmao replaces the secret value with `[REDACTED]` before surfacing the diagnostic in exceptions, gateway responses, or console logs

#### Scenario: Worker Startup Crash Surfaces Sanitized Stderr Summary
- **WHEN** the DSH ACP worker exits or closes stdout before answering initialization due to a configuration or plugin error written to stderr
- **THEN** the surfaced protocol failure includes a bounded, secret-redacted summary of the worker stderr output alongside the failure status
