## ADDED Requirements

### Requirement: Houmao provides a packaged `houmao-adv-usage-pattern` system skill
The system SHALL package a Houmao-owned system skill named `houmao-adv-usage-pattern` under the maintained system-skill asset root.

The top-level `SKILL.md` for that packaged skill SHALL serve as an entry index for advanced supported workflow compositions rather than as a flattened direct-operation document.

That skill SHALL organize its guidance through local pattern pages beneath the same packaged skill directory.

That skill SHALL remain distinct from the direct-operation skills that own the supported mailbox, gateway, messaging, and lifecycle surfaces.

#### Scenario: Installed advanced skill exposes an index and local pattern pages
- **WHEN** an agent or operator opens the installed `houmao-adv-usage-pattern` skill
- **THEN** the top-level `SKILL.md` acts as an index of supported advanced workflow compositions
- **AND THEN** the detailed workflow guidance lives in local pattern pages under the same packaged skill directory

### Requirement: `houmao-adv-usage-pattern` self-wakeup guidance composes existing Houmao skills
The packaged `houmao-adv-usage-pattern` skill SHALL include a local pattern page for self-wakeup through gateway-mediated self-mail.

That pattern page SHALL describe self-wakeup as a composition over the maintained direct-operation skills:

- `houmao-agent-email-comms` for mailbox send, check, read, reply, and mark-read work,
- `houmao-agent-gateway` for gateway mail-notifier control and optional direct wakeup control,
- `houmao-process-emails-via-gateway` for the actual notifier-driven unread-mail round.

That pattern page SHALL allow the managed agent to send one or more follow-up emails to its own mailbox address, where each unread self-mail item can represent a wake-up reminder, a continuation prompt, or one planned major step.

When later notifier-driven rounds occur, the pattern page SHALL direct the agent to inspect the unread set, process the relevant self-mail item or items for that round, mark only the successfully completed self-mail items read, and leave unfinished or deferred self-mail items unread.

#### Scenario: Self-wakeup pattern stages follow-up work through self-mail
- **WHEN** a mailbox-enabled managed agent with a live gateway needs to defer follow-up work for itself
- **THEN** the advanced skill directs that agent to send one or more follow-up emails to its own mailbox through the ordinary mailbox skill
- **AND THEN** later notifier-driven rounds can select those unread self-mail items as actionable work backlog

#### Scenario: Self-wakeup pattern processes only completed self-mail items
- **WHEN** a notifier-driven round finds several unread self-mail items for the same managed agent
- **THEN** the advanced skill directs the agent to complete the relevant work for the current round
- **AND THEN** it marks only the successfully completed self-mail items read while leaving unfinished or deferred self-mail items unread

### Requirement: `houmao-adv-usage-pattern` states self-wakeup durability boundaries honestly
The self-wakeup pattern in `houmao-adv-usage-pattern` SHALL describe unread self-mail as the durable work backlog for that pattern.

The pattern SHALL describe gateway mail-notifier polling as the live re-entry trigger that prompts the agent when unread self-mail exists.

The pattern MAY describe direct gateway `/v1/wakeups` as optional timing assistance for a live attached gateway, but it SHALL NOT describe direct wakeups as the durable backlog for the pattern.

The pattern SHALL NOT claim guaranteed unfinished-work recovery across gateway shutdown, gateway restart, or upstream managed-agent instance replacement.

#### Scenario: Pattern distinguishes unread backlog from live notifier and wakeups
- **WHEN** an agent or operator reads the self-wakeup pattern page
- **THEN** the page states that unread self-mail is the durable work backlog for the pattern
- **AND THEN** it states that gateway notifier polling is the live trigger and direct wakeups are optional live-gateway timing behavior rather than durable backlog state

