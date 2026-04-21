# managed-launch-prompt-header Specification

## Purpose
TBD - created by archiving change add-managed-prompt-header. Update Purpose after archive.
## Requirements
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

### Requirement: Managed-header policy resolves through launch override, profile policy, and default
The whole managed prompt header SHALL resolve through this precedence order:

1. explicit one-shot launch override,
2. stored launch-profile policy when present,
3. system default.

The system default for this capability SHALL be enabled.

Stored launch-profile policy SHALL support the three states:

- inherit,
- enabled,
- disabled.

When whole managed-header policy resolves to disabled, no managed-header subsections SHALL render, even if a section-level policy would otherwise resolve to enabled.

#### Scenario: Direct disable wins over stored enabled policy
- **WHEN** a reusable launch profile stores managed-header policy `enabled`
- **AND WHEN** an operator launches from that profile with an explicit one-shot disable override
- **THEN** the resulting managed launch does not prepend the managed prompt header
- **AND THEN** the stored launch profile still records policy `enabled`

#### Scenario: Stored disabled policy wins when no direct override is supplied
- **WHEN** a reusable launch profile stores managed-header policy `disabled`
- **AND WHEN** an operator launches from that profile without any direct managed-header override
- **THEN** the resulting managed launch does not prepend the managed prompt header
- **AND THEN** the launch does not silently fall back to the default enabled behavior

#### Scenario: Whole-header disable suppresses enabled section policy
- **WHEN** a reusable launch profile stores managed-header policy `disabled`
- **AND WHEN** that profile also stores automation notice section policy `enabled`
- **AND WHEN** an operator launches from that profile without any direct managed-header override
- **THEN** the resulting managed launch does not prepend `<managed_header>`
- **AND THEN** the automation notice does not render because the whole header is disabled

### Requirement: Managed header participates in effective launch-prompt composition
When managed-header policy resolves to enabled, the system SHALL treat the managed prompt header as part of the effective launch prompt rather than as a separate bootstrap-only prompt.

Prompt composition order SHALL be:

1. source role prompt,
2. launch-profile prompt overlay resolution,
3. launch appendix append,
4. structured prompt rendering into `<houmao_system_prompt>`,
5. backend-specific prompt injection.

Within `<houmao_system_prompt>`, section order SHALL be:

1. `<managed_header>` when enabled and at least one managed-header subsection is enabled,
2. `<prompt_body>` when body content exists.

Within `<managed_header>`, section order SHALL be:

1. `<identity>` when enabled,
2. `<memo_cue>` when enabled,
3. `<houmao_runtime_guidance>` when enabled,
4. `<automation_notice>` when enabled,
5. `<task_reminder>` when enabled,
6. `<mail_ack>` when enabled.

Within `<prompt_body>`, section order SHALL be:

1. `<role_prompt>` when the source role prompt participates,
2. `<launch_profile_overlay>` when present,
3. `<launch_appendix>` when present.

When launch-profile overlay mode is `replace`, the renderer SHALL omit `<role_prompt>` from `<prompt_body>`.

For launches created after this capability is implemented, the system SHALL persist the resulting effective launch prompt together with managed-header decision metadata, managed-header section decision metadata, and structured prompt-layout metadata so later relaunch and resume can reuse one coherent launch-prompt contract.

For older managed manifests that do not already persist the structured layout metadata, managed relaunch SHALL recompute managed-header behavior using the current managed identity, current managed memory paths when available, the default-enabled whole-header policy, and current section defaults unless a stronger persisted whole-header disable decision exists.

#### Scenario: Managed header renders ahead of the structured prompt body
- **WHEN** a managed launch uses a source role prompt, a launch-profile-owned prompt overlay, and a launch-owned appendix
- **AND WHEN** managed-header policy resolves to enabled
- **AND WHEN** all managed-header sections resolve to enabled
- **THEN** the effective launch prompt renders as `<houmao_system_prompt>` with `<managed_header>` before `<prompt_body>`
- **AND THEN** `<managed_header>` contains `<identity>`, `<memo_cue>`, `<houmao_runtime_guidance>`, `<automation_notice>`, `<task_reminder>`, and `<mail_ack>` before backend-specific prompt injection receives one composed prompt

#### Scenario: Replace overlay removes the role section from the structured prompt body
- **WHEN** a managed launch uses launch-profile overlay mode `replace`
- **AND WHEN** the operator supplies a launch-owned appendix
- **THEN** `<prompt_body>` contains `<launch_profile_overlay>` followed by `<launch_appendix>`
- **AND THEN** the rendered effective launch prompt does not also include `<role_prompt>`

#### Scenario: Relaunch of an older manifest adopts the default managed header
- **WHEN** a managed relaunch targets a pre-change manifest that lacks persisted managed-header metadata
- **AND WHEN** the relaunch does not have a stronger explicit disable override
- **THEN** the relaunched effective launch prompt is recomputed with the default managed prompt header enabled
- **AND THEN** the relaunched effective launch prompt includes default-enabled managed-header sections and omits default-disabled sections
- **AND THEN** the relaunch does not remain permanently exempt only because the original manifest predates this capability

### Requirement: Compatibility-generated launch prompts share the managed-header composition contract
When Houmao generates provider-facing launch prompts or compatibility profiles for managed launch, it SHALL derive those prompts from the same effective `<houmao_system_prompt>` composition contract used by local managed launch.

#### Scenario: Compatibility-generated profile uses the same managed header as local launch
- **WHEN** Houmao generates a provider-facing compatibility profile for a managed launch context whose managed-header policy resolves to enabled
- **AND WHEN** that launch context also includes a launch-owned appendix
- **THEN** the generated provider-facing system prompt includes the same `<houmao_system_prompt>` structure, including `<managed_header>` and `<launch_appendix>`, that local managed launch would use
- **AND THEN** compatibility launch prompt generation does not drift to a raw role-only prompt contract

### Requirement: Managed-header sections resolve through launch override, profile policy, and default
Each managed-header section SHALL resolve through this precedence order:

1. explicit one-shot launch section override,
2. stored launch-profile section policy when present,
3. system default.

The system default for each defined managed-header section SHALL be:

- `identity`: enabled
- `memo-cue`: enabled
- `houmao-runtime-guidance`: enabled
- `automation-notice`: enabled
- `task-reminder`: disabled
- `mail-ack`: disabled

Stored and one-shot section policy SHALL support the states:

- enabled,
- disabled.

The system SHALL reject unknown managed-header section names and unknown section policy states before launch or profile mutation succeeds.

Missing section policy SHALL mean the section's default. Existing stored launch profiles without section policy SHALL therefore render default-enabled sections and omit default-disabled sections when the whole managed header resolves to enabled.

#### Scenario: Stored section disable suppresses only that section
- **WHEN** a reusable launch profile stores automation notice section policy `disabled`
- **AND WHEN** the whole managed header resolves to enabled
- **AND WHEN** an operator launches from that profile without any direct section override
- **THEN** the resulting managed launch includes `<identity>`, `<memo_cue>`, and `<houmao_runtime_guidance>`
- **AND THEN** the resulting managed launch does not include `<automation_notice>`

#### Scenario: Direct section override wins for one launch
- **WHEN** a reusable launch profile stores automation notice section policy `disabled`
- **AND WHEN** an operator launches from that profile with a one-shot automation notice section policy `enabled`
- **THEN** the resulting managed launch includes `<automation_notice>`
- **AND THEN** the stored launch profile still records automation notice section policy `disabled`

#### Scenario: Existing profile uses section defaults
- **WHEN** a stored launch profile has no managed-header section policy
- **AND WHEN** the whole managed header resolves to enabled
- **THEN** the resulting managed launch includes the default-enabled `<identity>`, `<memo_cue>`, `<houmao_runtime_guidance>`, and `<automation_notice>` sections
- **AND THEN** the resulting managed launch omits the default-disabled `<task_reminder>` and `<mail_ack>` sections
- **AND THEN** the missing section policy does not behave like a stored disable

