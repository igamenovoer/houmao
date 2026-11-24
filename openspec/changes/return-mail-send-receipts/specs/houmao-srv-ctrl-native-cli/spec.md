# Spec Delta

## ADDED Requirements

### Requirement: Scoped mail creation commands report a write receipt

Scoped `mail send`, `reply`, and `post` SHALL return an authoritative CLI version-1 receipt for each verified write. It SHALL include the opaque `message_ref`, the binding that owns it, and the actual envelope fields. It SHALL omit the nested message and its contents.

#### Scenario: A gateway-backed send reports confirmation

- **WHEN** a scoped send returns a confirmed action response through the pair API or the current gateway
- **THEN** the receipt reports `operation: send`, `status: verified`, `authoritative: true`, and `execution_path: gateway_backed`
- **AND THEN** the CLI exposes `schema_version`, `channel`, `binding_id`, `transport`, `principal_id`, and `address` as top-level fields
- **AND THEN** it exposes the returned `sender_address`, `to`, `cc`, `subject`, `created_at_utc`, and exact `message_ref` as top-level fields

#### Scenario: A manager-direct send uses the same contract

- **WHEN** a manager-direct send succeeds through the selected mailbox binding
- **THEN** the receipt reports `execution_path: manager_direct` and the same verified fields as a gateway-backed send

#### Scenario: Reply distinguishes the new message and its parent

- **WHEN** a scoped reply creates a message
- **THEN** the receipt exposes the replying agent's binding and the returned envelope of the new reply
- **AND THEN** it supplies the input reference as `parent_message_ref` and the new reference as `message_ref`

#### Scenario: Operator post identifies the target binding

- **WHEN** a supported operator post creates a message
- **THEN** the receipt identifies the selected recipient's mailbox through `principal_id`, `address`, `channel`, and `binding_id`
- **AND THEN** it identifies the operator separately through `sender_address`

#### Scenario: Text and JSON give the same confirmation

- **WHEN** a caller selects plain, fancy, or JSON output for a send, reply, or post
- **THEN** that mode displays the same receipt fields and values, including actual recipient addresses and the entire reference
- **AND THEN** the command performs one write without a detail lookup to render that result

### Requirement: Scoped mail receipts preserve submission and confirmation evidence

A TUI-mediated send or reply SHALL report its request lifecycle status and request ID with `authoritative: false`. Only a verified write SHALL expose a confirmed `message_ref`. Each invocation SHALL dispatch at most one write and preserve the available evidence when the outcome is unresolved.

#### Scenario: A TUI submission has only preview evidence

- **WHEN** the TUI reports a prompt submission and emits text that resembles a successful mail result
- **THEN** the receipt reports `status: submitted`, `execution_path: tui_submission`, and the request ID
- **AND THEN** the receipt omits a confirmed reference and nested preview content
- **AND THEN** it retains the original channel and binding and directs the caller to check the sent box when authoritative lookup is available

#### Scenario: TUI reply has only the parent reference

- **WHEN** a scoped reply produces a TUI submission-only result
- **THEN** it includes the request ID and input `parent_message_ref`
- **AND THEN** it omits any unverified new reference, recipients, and subject

#### Scenario: Operator post requires verified write authority

- **WHEN** operator post would require submitting a mail request through the target TUI
- **THEN** it fails with the existing authority error and performs no TUI submission

#### Scenario: A TUI request reports an admission or execution problem

- **WHEN** the underlying TUI request reports rejection, busy, interruption, or an error
- **THEN** the receipt retains that status without claiming a verified write or a queued delivery

#### Scenario: Verification fails after a write may have committed

- **WHEN** a mail write reports a transport error with uncertainty or evidence of a prior commit
- **THEN** the CLI preserves the outcome and available reconciliation identifiers in its error
- **AND THEN** the invocation concludes without a second dispatch

### Requirement: A mail receipt supports read-only inspection

The verified receipt's `message_ref` SHALL identify the created message for authorized `mail peek` on the original channel and binding. Peeking SHALL preserve mailbox state.

#### Scenario: Read-only details follow a single send

- **WHEN** the sender peeks using the receipt's reference and original channel and binding
- **THEN** the CLI returns the selected sent message details
- **AND THEN** the message state stays unchanged and the recipient still has one copy from that send

#### Scenario: Reply and post use the binding that owns the receipt

- **WHEN** a caller needs the details of a verified reply or operator post
- **THEN** the reply reference resolves through the replying agent's binding
- **AND THEN** the post reference resolves through the selected recipient's binding, including if the message has since moved to archive

#### Scenario: A binding changes before the follow-up

- **WHEN** a caller uses a receipt reference against another agent, channel, or binding
- **THEN** the scoped lookup rejects the request before returning message content

### Requirement: Memo writes report a compact receipt

Scoped `memory memo set` and `append` SHALL report `success`, the memo write action, and `memo_file` in each output mode. `memo show` SHALL provide the current contents.

#### Scenario: Replacing or appending a memo produces one receipt

- **WHEN** the selected memo is successfully replaced or appended through a scoped command
- **THEN** it reports `success: true`, action `write_memo` or `append_memo`, and the resolved memo path
- **AND THEN** the result contains no memo text

#### Scenario: Inspecting a memo after appending preserves its contents

- **WHEN** a caller runs `memo show` after one successful append
- **THEN** the result contains the original memo followed by one copy of the addition

### Requirement: Reminder updates acknowledge the completed write

Scoped `gateway reminders set` SHALL report `status: updated`, `reminder_id`, `ranking`, `paused`, and `next_due_at_utc` from the accepted update in each output mode. The command SHALL obtain this receipt without a later read of the reminder set.

#### Scenario: A reminder update succeeds when a later read would fail

- **WHEN** the gateway accepts an update and the live reminder set is unavailable afterward
- **THEN** the command emits its receipt and exits successfully
- **AND THEN** the receipt carries the saved due time and omits reminder-set fields and prompt payloads

#### Scenario: The caller inspects the updated reminder

- **WHEN** a caller needs the reminder definition or set-wide selection information
- **THEN** the caller can use `reminders get` for the selected reminder or `reminders list` for the set

### Requirement: Native browser opening reports a serializable outcome

The `agents single ... open-browser` command SHALL serialize a successful owner-local browser action as `status`, `action`, and `detail` in every output mode.

#### Scenario: JSON output succeeds after one browser dispatch

- **WHEN** a caller selects JSON and an eligible Kimi Web owner opens the browser
- **THEN** the command opens the browser once and returns `status: ok` and `action: open_browser` with a short detail
- **AND THEN** the result contains no private URL, credentials, or bootstrap path

#### Scenario: A stale browser owner is rejected

- **WHEN** the selected browser owner fails ownership verification
- **THEN** the command exits nonzero without opening a browser

### Requirement: Gateway prompt reports admission and handoff in every output mode

Scoped `gateway prompt` SHALL return the same admission and handoff evidence in plain, fancy, and JSON output. It SHALL report `status`, `action`, `admission_policy`, `sent`, and `detail` and expose `operation_id`, `outcome`, and `native_prompt_id` when present in the gateway response. A structured gateway refusal SHALL exit nonzero.

#### Scenario: A live gateway refusal retains structured diagnostics

- **WHEN** the gateway refuses because the target is not ready, busy, unavailable, or unsupported
- **THEN** the command reports the gateway refusal as a structured JSON error and exits nonzero

#### Scenario: Gateway handoff prints the available evidence

- **WHEN** a gateway reports successful handoff
- **THEN** the command exits successfully and displays `sent: true`, the selected policy, and any reported IDs and outcome

#### Scenario: Accepted queueing stays distinct from handoff

- **WHEN** a gateway reports `outcome: queued` with `sent: false`
- **THEN** the command exits successfully and displays both values and the operation ID
- **AND THEN** it exposes a native prompt ID when supplied and performs no additional submission

#### Scenario: A named policy drives admission

- **WHEN** a caller submits a prompt through `agents single` or `agents self` using `--admission-policy`
- **THEN** the command forwards the selected policy and reports it in the result
- **AND THEN** omitting the option uses `ready-only`

## MODIFIED Requirements

### Requirement: `houmao-mgr agents gateway` exposes gateway lifecycle and gateway-mediated request commands
`houmao-mgr` SHALL expose `agents gateway` for gateway lifecycle and operations against the live gateway. Ordinary pair-native prompts SHALL be documented through `houmao-mgr agents prompt`.

#### Scenario: Gateway operations are exposed
- **WHEN** a caller selects the native gateway family
- **THEN** the family provides `attach`, `detach`, `status`, `prompt`, `interrupt`, `send-keys`, and `mail-notifier status|enable|disable`

#### Scenario: Gateway prompt and interrupt select live routes
- **WHEN** a caller uses `agents gateway prompt` or `interrupt`
- **THEN** `prompt` uses direct live gateway prompt control instead of a transport-neutral or queued request
- **AND THEN** `interrupt` uses live gateway-mediated interruption
- **AND THEN** the documentation describes the direct prompt route and its named admission policies

#### Scenario: Gateway keys and notifier select dedicated controls
- **WHEN** a caller uses `agents gateway send-keys` or `mail-notifier`
- **THEN** `send-keys` uses live raw control input without queueing, prompt-readiness gating, or busy gating
- **AND THEN** `mail-notifier` uses the live gateway notifier control instead of foreground managed-agent mail

#### Scenario: Operator attaches a gateway through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway attach --agent-id abc123`
- **THEN** `houmao-mgr` resolves that managed agent through the supported authority for that target
- **AND THEN** the command attaches or reuses the live gateway for that managed agent

#### Scenario: Operator submits a gateway-controlled prompt through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway prompt --agent-id abc123 --prompt "..."`
- **THEN** `houmao-mgr` delivers that request through the managed agent's live gateway direct prompt-control path
- **AND THEN** the command does not require the operator to discover or address the gateway listener endpoint directly

#### Scenario: Operator submits raw control input through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway send-keys --agent-id abc123 --sequence "/model<[Enter]>"`
- **THEN** `houmao-mgr` delivers that request through the managed agent's dedicated live gateway raw control-input path
- **AND THEN** the command does not reinterpret that raw control input as a queued semantic prompt request

#### Scenario: Operator enables mail notifier through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway mail-notifier enable --agent-id abc123 --interval-seconds 60`
- **THEN** `houmao-mgr` delivers that request through the managed agent's live gateway mail-notifier control path
- **AND THEN** the command does not require the operator to discover or address the gateway listener endpoint directly

#### Scenario: Ordinary prompt guidance points operators to the transport-neutral path by default
- **WHEN** repo-owned help text or docs explain how to submit an ordinary prompt through the native pair CLI
- **THEN** they present `houmao-mgr agents prompt ...` as the default documented path
- **AND THEN** they present `houmao-mgr agents gateway prompt ...` as the explicit gateway-managed alternative rather than the default

## REMOVED Requirements

### Requirement: `houmao-mgr agents gateway prompt` returns structured JSON send results and refusal errors

**Reason**: The old requirement assumed JSON-only results and immediate dispatch. The new receipt requirement covers all output modes and carries the gateway's admission evidence.

**Migration**: Use `--print-json` for JSON and `--admission-policy` to select admission behavior. Read `sent` and `outcome` as separate receipt fields and handle queueing when reported.
