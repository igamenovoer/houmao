## ADDED Requirements

### Requirement: Operator messaging skill exposes a manual concise control surface
The system SHALL package a `houmao-operator-messaging` system skill for manual operator-to-agent messaging workflows.

The skill SHALL be invoked only when the user explicitly selects `houmao-operator-messaging` or explicitly names one of its supported operator messaging operations.

The skill entrypoint SHALL use concise structured Markdown and SHALL expose these subcommands:

- `help`
- `clarify`
- `dispatch`

The skill SHALL NOT expose separate single-agent and multi-agent dispatch subcommands; target count SHALL be resolved from the user's dispatch task.

The `help` subcommand SHALL be read-only and SHALL explain purpose, subcommands, common prompts, record modes, routing boundaries, and related skills without dispatching messages or mutating Houmao runtime state.

When the skill is invoked without a subcommand or actionable operator-messaging prompt, it SHALL explain the supported subcommands or ask for the intended operation without dispatching messages.

#### Scenario: Operator asks for help
- **WHEN** the user asks for `houmao-operator-messaging help`
- **THEN** the skill reports the supported subcommands and boundaries
- **AND THEN** it does not send prompts, write mailbox messages, mutate files, or change managed-agent lifecycle state

#### Scenario: Generic messaging request does not auto-route
- **WHEN** the user asks a generic agent messaging question without explicitly selecting `houmao-operator-messaging`
- **THEN** the operator messaging skill is not selected automatically
- **AND THEN** direct messaging can remain owned by the lower-level messaging workflow

#### Scenario: No subcommand is supplied
- **WHEN** the user invokes `houmao-operator-messaging` without a subcommand or actionable prompt
- **THEN** the skill explains or asks for one of `help`, `clarify`, or `dispatch`
- **AND THEN** it does not default to dispatch

### Requirement: Clarify resolves operator intent without dispatching
The `clarify` subcommand SHALL resolve operator intent before dispatch and SHALL NOT send any direct prompt, mailbox message, gateway request, lifecycle command, or other runtime mutation.

Clarification SHALL build an internal coverage map that includes:

- objective and desired outcome,
- target agent or target-selection rule,
- intended message content,
- relevant context or artifact references,
- constraints and prohibited actions,
- success criteria,
- default prompt route, mailbox route request, or target-specific route preference,
- ordering or priority when multiple targets are possible,
- expected reply or evidence,
- record mode,
- any authorization or safety boundary that affects dispatch.

The clarification protocol SHALL ask bounded, high-impact questions one at a time and SHALL stop when the intent is dispatch-ready or when remaining ambiguity is explicitly accepted.

The clarification protocol SHALL NOT ask wording-only questions while target selection, transport, safety, success criteria, or record mode remains materially unclear.

By default, the clarified intent SHALL be kept in chat memory and summarized back to the user.

When the user requests an external Markdown clarification record, the skill SHALL require a user-specified path and SHALL create, update, or append that file with the accepted clarification record.

The skill SHALL NOT invent a default external Markdown path.

#### Scenario: Clarify records intent in chat memory by default
- **WHEN** the user invokes `clarify` without requesting an external record file
- **THEN** the skill asks only necessary high-impact questions
- **AND THEN** it summarizes the accepted operator intent in chat memory
- **AND THEN** it does not dispatch any message

#### Scenario: Clarify requires an explicit external record path
- **WHEN** the user invokes `clarify` and asks to save the clarification in Markdown
- **AND WHEN** the user has not provided a path
- **THEN** the skill asks for the Markdown path before writing a clarification record
- **AND THEN** it does not invent a path under the repository, home directory, workspace, or current directory

#### Scenario: Clarify updates the supplied Markdown record
- **WHEN** the user invokes `clarify` with an explicit Markdown path
- **THEN** the skill records the accepted intent at that path
- **AND THEN** the record identifies target-selection facts, routing preferences, reply expectations, and unresolved accepted ambiguity
- **AND THEN** it still does not dispatch any message

### Requirement: Dispatch converts clarified intent into routed command packets
The `dispatch` subcommand SHALL dispatch operator messages to one or more Houmao-managed agents from a clarified operator intent, an explicit dispatch prompt, or a user-specified external Markdown intent record.

By default, `dispatch` SHALL route packets by prompt delivery.

`dispatch` SHALL choose mailbox delivery only when the operator prompt or chat context indicates mail, inbox, thread, asynchronous mailbox note, reply-reference, or mailbox sender-identity intent.

`dispatch` SHALL NOT choose mailbox delivery merely because the target has a mailbox.

Before sending, `dispatch` SHALL prepare a command packet plan that identifies for each packet:

- target agent or mailbox,
- prompt or mailbox route,
- message body or prompt content,
- ordering or priority if multiple packets are sent,
- expected reply or evidence,
- record update responsibility when an external record is used.

The dispatch task SHALL determine whether one packet or multiple packets are needed; the skill SHALL NOT require a separate user-selected mode for single-agent versus multi-agent dispatch.

If dispatch intent is materially unclear, `dispatch` SHALL ask only blocking questions or recommend using `clarify`; it SHALL NOT run a full clarification workflow inside `dispatch` unless the user changes the request to clarification.

Prompt packets SHALL delegate last-mile delivery to `houmao-agent-messaging`.

Prompt packets SHALL use gateway-backed prompt delivery when the target has a live gateway, and SHALL use direct managed-agent prompt fallback when the target has no live gateway.

When the selected prompt surface supports a forced prompt flag, direct fallback prompting SHALL include `--force` or the equivalent forced prompt behavior.

Mailbox packets SHALL delegate last-mile delivery to `houmao-agent-email-comms` or the supported mailbox CLI/API surface owned by that skill.

After dispatch, the skill SHALL report a concise dispatch summary that includes target count, route used, blocked packets if any, and where any external record was updated.

The skill SHALL NOT provide durable scheduling, retry orchestration, topology validation, or generated loop recovery; when requested behavior needs those properties, it SHALL recommend `houmao-agent-loop-pro` or `houmao-agent-loop-lite`.

#### Scenario: Dispatch sends to multiple targets from one task
- **WHEN** the user asks `dispatch` to send related instructions to several named managed agents
- **THEN** the skill prepares one command packet per required target
- **AND THEN** it sends those packets in the task-appropriate order without requiring a multi-dispatch subcommand
- **AND THEN** it summarizes which targets and routes were used

#### Scenario: Dispatch blocks on material ambiguity
- **WHEN** the user invokes `dispatch` but the target agent or required transport is unclear
- **THEN** the skill asks a blocking question or recommends `clarify`
- **AND THEN** it does not send partial messages that could reach the wrong target or route

#### Scenario: Dispatch delegates direct prompt delivery
- **WHEN** a command packet requires a direct prompt to a live managed agent
- **THEN** the skill uses `houmao-agent-messaging` for last-mile prompt delivery
- **AND THEN** it does not duplicate direct messaging command details in the operator messaging skill

#### Scenario: Dispatch defaults to gateway-preferred prompting
- **WHEN** the user invokes `dispatch` without asking for mailbox delivery
- **THEN** the skill plans prompt delivery for each packet
- **AND THEN** targets with live gateways are prompted through the gateway-backed prompt route
- **AND THEN** targets without live gateways use direct managed-agent prompt fallback with forced prompt behavior when the selected prompt surface supports it

#### Scenario: Dispatch delegates mailbox delivery
- **WHEN** the operator prompt or chat context asks for mailbox delivery
- **THEN** the skill uses `houmao-agent-email-comms` or its owned mailbox CLI/API surface for last-mile delivery
- **AND THEN** it does not duplicate mailbox operation details in the operator messaging skill

### Requirement: Dispatch applies managed-operator and operator-origin mailbox identity rules
For mailbox dispatch, the skill SHALL determine whether the current operator is a Houmao-managed agent with a usable mailbox binding.

When the current operator is Houmao-managed and has a usable mailbox binding, mailbox dispatch SHALL use that operator agent's own mailbox address for ordinary mailbox sends.

When the current operator is not Houmao-managed, or the current operator does not have a usable own mailbox binding, mailbox dispatch SHALL use the supported operator-origin mailbox post path where available.

The skill SHALL treat the reserved operator-origin sender as the external-operator route and SHALL NOT invent per-operator mailbox identities.

If the user requires mailbox delivery and the target lacks a usable mailbox or the supported mailbox transport is unavailable, the skill SHALL report the blocker or ask for an alternate acceptable route before sending.

If the user requires direct prompt delivery and the target does not have a usable direct messaging surface, the skill SHALL report the blocker or ask for an alternate acceptable route before sending.

The skill SHALL NOT invent target agents, gateway URLs, mailbox addresses, mailbox roots, or operator-origin paths; it SHALL discover them through maintained Houmao surfaces or ask for the missing Houmao runtime input.

#### Scenario: Managed operator uses own mailbox
- **WHEN** mailbox dispatch is requested by an operator agent that is itself Houmao-managed
- **AND WHEN** that operator agent has a usable mailbox binding
- **THEN** the skill uses the operator agent's own mailbox identity for ordinary mailbox send semantics
- **AND THEN** it does not replace that identity with the external operator-origin sender

#### Scenario: External operator uses operator-origin post
- **WHEN** mailbox dispatch is requested from outside a Houmao-managed agent runtime
- **THEN** the skill uses the supported operator-origin mailbox post path where available
- **AND THEN** the sender identity follows the reserved operator-origin mailbox semantics

#### Scenario: Required mailbox route is unavailable
- **WHEN** mailbox delivery is required
- **AND WHEN** the target mailbox or supported mailbox transport cannot be resolved
- **THEN** the skill reports the blocker or asks whether an alternate route is acceptable
- **AND THEN** it does not silently switch to direct prompt delivery
