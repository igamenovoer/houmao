## MODIFIED Requirements

### Requirement: Managed prompt header reference documents section controls and automation notice
The managed prompt header reference page SHALL document the named managed-header section model, the default-enabled automation notice, and the default-disabled task reminder and mail acknowledgement sections.

At minimum, the page SHALL explain:

- the defined section names `identity`, `houmao-runtime-guidance`, `automation-notice`, `task-reminder`, and `mail-ack`,
- that `identity`, `houmao-runtime-guidance`, and `automation-notice` default to enabled whenever the whole managed header is enabled,
- that `task-reminder` and `mail-ack` default to disabled unless explicitly enabled,
- that `operator_prompt_mode = as_is` controls provider startup behavior only and does not disable the automation notice,
- that whole-header `--no-managed-header` disables every managed-header section,
- that section-level policy can disable individual sections without disabling the whole managed header,
- that section-level policy can enable default-disabled sections such as `task-reminder` and `mail-ack`,
- that the automation notice tells agents not to call Claude's `AskUserQuestion` tool or equivalent interactive user-question tools that would open or focus an operator TUI panel,
- that mailbox-driven clarification should be sent by replying to the relevant mailbox thread when that thread is reply-enabled rather than by asking the interactive operator,
- that mailbox-driven ambiguity on non-reply-enabled threads should be resolved by the agent making its own decision with available context,
- that the task reminder section is for explicit self-reminding requests or concrete supervision/finalization checks rather than generic long-running work,
- that the task reminder section uses examples such as required replies, required files, or health checks to define acceptable reminder targets,
- that the task reminder section tells agents to keep using local working state when no concrete reminder target exists,
- that the task reminder section does not prescribe a fixed generic default reminder delay,
- that the mail acknowledgement section tells agents to send a concise acknowledgement to the reply-enabled address before doing substantive work.

#### Scenario: Reader sees section default behavior
- **WHEN** a reader opens the managed prompt header reference page
- **THEN** the page states that identity, Houmao runtime guidance, and automation notice default to enabled
- **AND THEN** the page states that task reminder and mail acknowledgement default to disabled unless explicitly enabled
- **AND THEN** the page states that `as_is` provider startup policy does not disable the automation notice

#### Scenario: Reader sees the automation notice rule
- **WHEN** a reader opens the managed prompt header reference page
- **THEN** the page documents that managed agents are instructed not to call Claude's `AskUserQuestion` tool or equivalent interactive user-question tools
- **AND THEN** the page documents that mailbox-driven ambiguity should be clarified by replying to the relevant mailbox thread when the thread is reply-enabled
- **AND THEN** the page documents that mailbox-driven ambiguity on non-reply-enabled threads should be resolved by the agent making its own decision with available context

#### Scenario: Reader sees the task reminder rule
- **WHEN** a reader opens the managed prompt header reference page
- **THEN** the page documents that `task-reminder` is default-disabled
- **AND THEN** the page documents that enabling it narrows reminder use to explicit self-reminding requests or concrete supervision/finalization checks
- **AND THEN** the page documents that it does not prescribe a fixed generic default reminder delay
- **AND THEN** the page documents that it tells agents to avoid ceremonial reminders and keep using local working state when no concrete reminder target exists

#### Scenario: Reader sees the mail acknowledgement rule
- **WHEN** a reader opens the managed prompt header reference page
- **THEN** the page documents that `mail-ack` is default-disabled
- **AND THEN** the page documents that enabling `mail-ack` tells agents to send a concise acknowledgement to the reply-enabled address before doing substantive work

#### Scenario: Reader sees section-level opt-out behavior
- **WHEN** a reader looks up how to suppress one part of the managed header
- **THEN** the page documents the section-level policy controls
- **AND THEN** the page distinguishes section-level controls from the whole-header `--managed-header` and `--no-managed-header` controls
