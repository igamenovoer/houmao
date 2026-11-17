# Spec Delta

## Purpose

Define structured control of managed DeepSeek Harness headless agents through ACP, preserving exact conversation continuity and truthful execution outcomes.

## ADDED Requirements

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

DSH headless capability inspection SHALL identify supported creation, exact resume, prompting, cancellation, closure, native prompt, skills, and accounting sources. Unsupported load, transcript replay, deletion, fork, additional-workspace, raw-key, or refresh operations SHALL return explicit capability errors without emulation through ordinary chat.

#### Scenario: Caller Requests Unsupported Session Fork
- **WHEN** a caller requests a DSH operation that the qualified ACP implementation does not support
- **THEN** Houmao reports that operation as unsupported without creating another native session

#### Scenario: Profile Files Change During a Turn
- **WHEN** DSH profile files change while a managed headless turn is active
- **THEN** Houmao does not claim coordinated live activation merely because the files changed
