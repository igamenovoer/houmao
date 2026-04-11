# docs-managed-launch-prompt-header-reference Specification

## Purpose

Define the reference-page requirements for documenting the Houmao-owned managed launch prompt header — what it contains, when it is prepended, how it interacts with role injection, and how operators opt out through per-launch flags or stored launch-profile policy.
## Requirements
### Requirement: Reference page documents the managed launch prompt header

The docs site SHALL include a reference page at `docs/reference/run-phase/managed-prompt-header.md` describing the Houmao-owned prompt header that is prepended to managed launches by default.

That page SHALL explain:

- what the header is (a Houmao-owned, deterministic block of text prepended to the operator-supplied or role-supplied system prompt before backend role injection runs),
- why it exists (to give every managed agent a small, reliable preamble that identifies the managed lifecycle and points to the packaged system skills),
- the prompt composition order: source role prompt → prompt-overlay resolution (when present) → managed header prepend (when enabled) → backend-specific role injection,
- the default-on policy and the `--managed-header` / `--no-managed-header` opt-out flags on the relevant launch and launch-profile commands,
- where the header policy is persisted in stored launch profiles and how `--clear-managed-header` returns that field to inherit behavior,
- which launch surfaces honor the policy: `houmao-mgr agents launch`, `houmao-mgr project easy instance launch`, and any launch-profile-backed flow built on top of those.

That page SHALL link to:

- `docs/getting-started/launch-profiles.md` for the shared launch-profile conceptual model and persistence rules,
- `docs/reference/run-phase/role-injection.md` for the per-backend role injection mechanism that runs after the header is prepended,
- the `houmao-mgr` CLI reference for the flag-level documentation of `--managed-header` and `--no-managed-header`.

That page SHALL state that the managed header is part of the prompt body delivered to the underlying CLI tool and is not a separate transport channel.

The docs site index entry for that reference page (`docs/index.md`) SHALL mention per-section control in its one-line description, alongside composition, opt-out, and stored-profile policy.

#### Scenario: Docs index entry reflects per-section control

- **WHEN** a reader scans `docs/index.md` looking for the managed-header reference
- **THEN** the index entry mentions per-section control or independently controllable sections
- **AND THEN** the entry links to `docs/reference/run-phase/managed-prompt-header.md`

#### Scenario: Reader can find a dedicated reference for the managed prompt header

- **WHEN** a reader navigates the docs site looking for what the managed prompt header contains and when it is added
- **THEN** they find a single reference page under `docs/reference/run-phase/managed-prompt-header.md`
- **AND THEN** the page explains what the header is, why it exists, and when it is prepended

#### Scenario: Reader sees the prompt composition order

- **WHEN** a reader opens the managed prompt header reference page
- **THEN** the page documents the composition order as source role prompt → prompt-overlay resolution → managed header prepend → backend role injection
- **AND THEN** the page explains that the header is prepended before backend role injection rather than appended after it

#### Scenario: Reader sees the opt-out flags and default-on policy

- **WHEN** a reader looks up how to disable the managed header on a launch
- **THEN** the page documents `--no-managed-header` as the per-launch opt-out
- **AND THEN** the page documents `--managed-header` as the explicit opt-in
- **AND THEN** the page states that omitted policy falls back to default-on behavior

#### Scenario: Reader can navigate from header reference to launch-profiles guide and CLI reference

- **WHEN** a reader follows cross-reference links from the managed prompt header reference page
- **THEN** they reach `docs/getting-started/launch-profiles.md` for the shared profile model
- **AND THEN** they reach `docs/reference/cli/houmao-mgr.md` for the flag-level CLI coverage
- **AND THEN** they reach `docs/reference/run-phase/role-injection.md` for the per-backend role injection mechanism

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
- that the task reminder section tells agents to create a one-off live gateway reminder with a 10 second default notification check delay when beginning potentially long-running work and to turn that reminder off when the task is done,
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
- **AND THEN** the page documents that the section tells agents to create a one-off live gateway reminder with a 10 second default notification check delay when beginning potentially long-running work
- **AND THEN** the page documents that the section tells agents to turn off that reminder when the task is done

#### Scenario: Reader sees the mail acknowledgement rule
- **WHEN** a reader opens the managed prompt header reference page
- **THEN** the page documents that `mail-ack` is default-disabled
- **AND THEN** the page documents that enabling `mail-ack` tells agents to send a concise acknowledgement to the reply-enabled address before doing substantive work

#### Scenario: Reader sees section-level opt-out behavior
- **WHEN** a reader looks up how to suppress one part of the managed header
- **THEN** the page documents the section-level policy controls
- **AND THEN** the page distinguishes section-level controls from the whole-header `--managed-header` and `--no-managed-header` controls
