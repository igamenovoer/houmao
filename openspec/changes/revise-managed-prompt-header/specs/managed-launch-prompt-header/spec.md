# Spec Delta

## MODIFIED Requirements

### Requirement: Managed launches prepend a Houmao-owned prompt header by default
Houmao-managed launch surfaces SHALL render the managed prompt header as a Houmao-owned section of the effective launch prompt by default.

That effective launch prompt SHALL be rooted at `<houmao_system_prompt>`.

When managed-header policy resolves to enabled, the rendered prompt SHALL place the managed header in a `<managed_header>` section ahead of `<prompt_body>`.

#### Scenario: Managed launch renders header sections according to prompt policy

- **GIVEN** a managed launch builds its effective system prompt
- **THEN** the resolved header policy determines section placement, order, and content

That managed prompt header SHALL render deterministic named subsections in this order when the corresponding section policy resolves to enabled:

- `<identity>`
- `<memo_cue>`
- `<houmao_runtime_guidance>`
- `<automation_notice>`
- `<task_reminder>`
- `<mail_ack>`

The identity section SHALL identify the launched agent as Houmao-managed and include the resolved managed-agent name and id when those identities exist for the launch, formatted as explicit key-value lines.

The memo cue section SHALL be included by default whenever the whole managed header is enabled unless a stronger section-level policy disables it.

The memo cue section SHALL include the resolved absolute path to the launched managed agent's fixed `houmao-memo.md` file.

The memo cue section SHALL tell the agent to read that memo file at the start of each prompt turn before planning or acting.

The memo cue section SHALL tell the agent to treat the memo as durable operator/agent context for the current managed agent, apply its facts and rules directly without merely stating that the memo was read, and follow relevant authored `pages/` links when needed.

The memo cue section SHALL separate every-turn read rules from sparse write rules that limit updates to explicit requests or clearly outdated entries.

The Houmao runtime guidance section SHALL:

- state that ordinary non-Houmao project tasks proceed normally,
- instruct the agent that for Houmao-related actions it SHALL look for installed `houmao-*` skills, particularly entrypoint skills, for guidance first,
- state that `houmao-mgr` is the canonical direct CLI for interacting with the Houmao system,
- direct the agent toward supported Houmao manifests, runtime metadata, and service interfaces rather than unsupported ad hoc probing of `tmux` sessions or internal runtime files,
- remain general-purpose through the `houmao-*` skill pattern and entrypoint-skill category and SHALL NOT depend on naming individual packaged skill entries.

The automation notice section SHALL be included by default for all managed launches, including launches whose provider startup policy is `as_is`, unless a stronger whole-header or section-level policy disables it.

The automation notice section SHALL state, with uppercase emphasis on the prohibitions, that the agent is running in unattended mode without a human at the terminal, SHALL NOT call Claude's `AskUserQuestion` tool, SHALL NOT use an equivalent interactive question tool that blocks waiting for user input, and SHALL structure ambiguity handling into explicit branches for normal tasks, reply-enabled mailbox threads, and non-reply-enabled mailbox threads.

For mailbox-driven work, the automation notice section SHALL state that the agent SHALL NOT ask the interactive operator for clarification, SHALL use a focused reply to the relevant mailbox thread when that thread is reply-enabled, and SHALL decide on its own with available context when the thread is not reply-enabled. This mailbox rule SHALL apply both when the ambiguity is in the message itself and when it appears while carrying out work requested by that message.

The task reminder section SHALL be disabled by default unless a stronger section-level policy enables it.

When enabled, the task reminder section SHALL state that reminder creation is reserved for either:

- explicit operator-directed self-reminding or self-wakeup behavior, or
- concrete supervision or finalization checks whose completion would otherwise be easy to miss.

When enabled, the task reminder section SHALL give concrete examples of acceptable reminder targets such as sending a required reply, writing a required file, or verifying agent or loop health.

The task reminder section SHALL direct the agent to name the concrete check the reminder is guarding and to delete that reminder when the guarded check is satisfied.

The task reminder section SHALL direct the agent to keep using local todo, memo, or other working state instead of creating a reminder when no explicit or concrete reminder target exists.

The task reminder section SHALL NOT prescribe a fixed generic default reminder delay.

The mail acknowledgement section SHALL be disabled by default unless a stronger section-level policy enables it.

When enabled, the mail acknowledgement section SHALL state that, for reply-enabled mailbox-driven work, the agent SHALL send a concise acknowledgement before doing substantive work.

#### Scenario: Managed launch gets the default Houmao-owned header
- **WHEN** an operator launches a managed agent through a maintained Houmao launch surface without disabling the managed header or any managed-header section
- **THEN** the effective launch prompt is rooted at `<houmao_system_prompt>` and includes `<managed_header>` ahead of `<prompt_body>`
- **AND THEN** that header includes `<identity>`, `<memo_cue>`, `<houmao_runtime_guidance>`, and `<automation_notice>` sections in deterministic order
- **AND THEN** that header does not include `<task_reminder>` or `<mail_ack>` by default
- **AND THEN** the header identifies the agent as Houmao-managed, names the absolute memo file path, directs Houmao-related actions to `houmao-*` skills first, and names `houmao-mgr` as the canonical direct Houmao interface

#### Scenario: Runtime guidance directs Houmao-related actions to houmao-* entrypoint skills first
- **WHEN** an operator launches a managed agent with `houmao-runtime-guidance` enabled
- **THEN** `<houmao_runtime_guidance>` instructs the agent to look for installed `houmao-*` skills, particularly entrypoint skills, for guidance first when handling Houmao-related actions
- **AND THEN** `<houmao_runtime_guidance>` names `houmao-mgr` as the canonical direct CLI and tells the agent not to probe raw `tmux` sessions or internal runtime files when a supported Houmao skill or command exists
- **AND THEN** `<houmao_runtime_guidance>` does not depend on individual packaged skill names

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
- **AND THEN** the section tells the agent to keep using local working state when no concrete reminder target exists
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

## ADDED Requirements

### Requirement: Structured prompt blocks render with readable blank-line separation
When `<houmao_system_prompt>` renders container sections and sibling child sections, the renderer SHALL separate container tags and adjacent child blocks with blank lines while preserving `HOUMAO_SYSTEM_PROMPT_LAYOUT_VERSION = 1` and all existing XML tag names.

#### Scenario: Adjacent managed-header and prompt-body blocks are separated by blank lines
- **WHEN** a managed launch renders `<houmao_system_prompt version="1">` with `<managed_header>` and `<prompt_body>`
- **THEN** blank lines separate container opening tags, adjacent child sections, and container closing tags
- **AND THEN** `render_managed_prompt_header()` also separates enabled header subsections with blank lines

### Requirement: Revised managed prompt header increments header metadata version
Manifest-persisted `managed_prompt_header` metadata SHALL record `version: 2` for builds produced with the revised header prose and spacing while keeping `houmao_system_prompt_layout.version` at `1`.

#### Scenario: Build metadata records header version 2 and layout version 1
- **WHEN** a managed launch constructs `managed_prompt_header` metadata and `houmao_system_prompt_layout` metadata
- **THEN** `managed_prompt_header["version"]` equals `2`
- **AND THEN** `houmao_system_prompt_layout["version"]` equals `1`
