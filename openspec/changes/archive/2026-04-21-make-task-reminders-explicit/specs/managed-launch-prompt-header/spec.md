## MODIFIED Requirements

### Requirement: Managed launches prepend a Houmao-owned prompt header by default
Houmao-managed launch surfaces SHALL render the managed prompt header as a Houmao-owned section of the effective launch prompt by default.

That effective launch prompt SHALL be rooted at `<houmao_system_prompt>`.

When managed-header policy resolves to enabled, the rendered prompt SHALL place the managed header in a `<managed_header>` section ahead of `<prompt_body>`.

That managed prompt header SHALL render deterministic named subsections in this order when the corresponding section policy resolves to enabled:

- `<identity>`
- `<memo_cue>`
- `<houmao_runtime_guidance>`
- `<automation_notice>`
- `<task_reminder>`
- `<mail_ack>`

The identity section SHALL identify the launched agent as Houmao-managed and include the resolved managed-agent name and id when those identities exist for the launch.

The memo cue section SHALL be included by default whenever the whole managed header is enabled unless a stronger section-level policy disables it.

The memo cue section SHALL include the resolved absolute path to the launched managed agent's fixed `houmao-memo.md` file.

The memo cue section SHALL tell the agent to read that memo file at the start of each prompt turn before planning or acting.

The memo cue section SHALL tell the agent to treat the memo as durable operator/agent context for the current managed agent and to follow relevant authored `pages/` links when needed.

The Houmao runtime guidance section SHALL:

- state that `houmao-mgr` is the canonical direct interface for interacting with the Houmao system,
- tell the agent to prefer bundled Houmao guidance and supported Houmao system interfaces for Houmao-related work,
- direct the agent toward supported manifests, runtime metadata, and service interfaces rather than unsupported ad hoc probing,
- remain general-purpose and SHALL NOT depend on naming individual packaged guidance entries.

The automation notice section SHALL be included by default for all managed launches, including launches whose provider startup policy is `as_is`, unless a stronger whole-header or section-level policy disables it.

The automation notice section SHALL state, with uppercase emphasis on the prohibitions, that the agent is running in fully automated mode, SHALL NOT call Claude's `AskUserQuestion` tool, SHALL NOT use an equivalent interactive user-question tool that would open or focus an operator TUI panel, and SHALL make decisions on its own with available context, including when clarification is unavailable.

For mailbox-driven work, the automation notice section SHALL state that the agent SHALL NOT ask the interactive operator for clarification, SHALL use a focused reply to the relevant mailbox thread when that thread is reply-enabled, and SHALL decide on its own with available context when the thread is not reply-enabled. This mailbox rule SHALL apply both when the ambiguity is in the message itself and when it appears while carrying out work requested by that message.

The task reminder section SHALL be disabled by default unless a stronger section-level policy enables it.

When enabled, the task reminder section SHALL state that reminder creation is reserved for either:

- explicit operator-directed self-reminding or self-wakeup behavior, or
- concrete supervision or finalization checks whose completion would otherwise be easy to miss.

When enabled, the task reminder section SHALL give concrete examples of acceptable reminder targets such as sending a required reply, writing a required file, or verifying agent or loop health.

The task reminder section SHALL direct the agent to name the concrete obligation the reminder is guarding and to delete or otherwise turn off that reminder when the guarded obligation is satisfied.

The task reminder section SHALL direct the agent to keep using local todo, memo, or other working state instead of creating a reminder when no explicit or concrete reminder target exists.

The task reminder section SHALL NOT prescribe a fixed generic default reminder delay.

The mail acknowledgement section SHALL be disabled by default unless a stronger section-level policy enables it.

When enabled, the mail acknowledgement section SHALL state that, for mailbox-driven work, the agent SHALL always send a concise acknowledgement to the reply-enabled address before doing substantive work.

#### Scenario: Managed launch gets the default Houmao-owned header
- **WHEN** an operator launches a managed agent through a maintained Houmao launch surface without disabling the managed header or any managed-header section
- **THEN** the effective launch prompt is rooted at `<houmao_system_prompt>` and includes `<managed_header>` ahead of `<prompt_body>`
- **AND THEN** that header includes `<identity>`, `<memo_cue>`, `<houmao_runtime_guidance>`, and `<automation_notice>` sections in deterministic order
- **AND THEN** that header does not include `<task_reminder>` or `<mail_ack>` by default
- **AND THEN** the header identifies the agent as Houmao-managed, names the absolute memo file path, and names `houmao-mgr` as the canonical direct Houmao interface

#### Scenario: Memo cue can be disabled independently
- **WHEN** an operator launches a managed agent with managed-header section policy `memo-cue=disabled`
- **AND WHEN** the whole managed header resolves to enabled
- **THEN** the effective launch prompt does not include the `<memo_cue>` section
- **AND THEN** other default-enabled sections still render unless their own policy disables them

#### Scenario: Task reminder is default-off but can be enabled for concrete reminder work
- **WHEN** an operator launches a managed agent with managed-header section policy `task-reminder=enabled`
- **AND WHEN** the whole managed header resolves to enabled
- **THEN** the effective launch prompt includes the `<task_reminder>` section
- **AND THEN** the section tells the agent to use reminders only for explicit self-reminding requests or concrete supervision/finalization obligations
- **AND THEN** the section tells the agent to avoid ceremonial reminders and to keep using local working state when no concrete reminder target exists
- **AND THEN** the section does not prescribe a fixed generic default reminder delay

#### Scenario: Mail acknowledgement is default-off but can be enabled
- **WHEN** an operator launches a managed agent with managed-header section policy `mail-ack=enabled`
- **AND WHEN** the whole managed header resolves to enabled
- **THEN** the effective launch prompt includes the `<mail_ack>` section
- **AND THEN** the section tells the agent to send a concise acknowledgement to the reply-enabled address for mailbox-driven work before doing substantive work

#### Scenario: Automation notice is default-on for as-is startup policy
- **WHEN** an operator launches a managed agent whose resolved provider startup policy is `as_is`
- **AND WHEN** the managed header is not disabled
- **AND WHEN** the automation notice section is not disabled
- **THEN** the effective launch prompt still includes the `<automation_notice>` section
- **AND THEN** `as_is` does not suppress agent-facing automation guidance

#### Scenario: Automation notice handles mailbox ambiguity without interactive operator questions
- **WHEN** a managed launch renders the default automation notice
- **THEN** the notice tells the agent not to call Claude's `AskUserQuestion` tool or equivalent interactive user-question tools
- **AND THEN** the notice tells the agent to use a focused mailbox-thread reply for mailbox-driven clarification when the thread is reply-enabled
- **AND THEN** the notice tells the agent to decide on its own with available context when the mailbox thread is not reply-enabled
