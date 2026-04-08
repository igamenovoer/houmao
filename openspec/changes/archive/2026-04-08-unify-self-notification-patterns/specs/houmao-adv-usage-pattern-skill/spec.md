## MODIFIED Requirements

### Requirement: `houmao-adv-usage-pattern` self-wakeup guidance composes existing Houmao skills
The packaged `houmao-adv-usage-pattern` skill SHALL include a self-notification pattern family that compares two supported ways for a managed agent to notify itself about later work:

- live gateway reminders through `/v1/reminders`,
- self-mail reminders that re-enter through unread mailbox work.

That pattern family SHALL describe self-notification as a composition over the maintained direct-operation skills:

- `houmao-agent-gateway` for live gateway reminder creation, inspection, update, and deletion through `/v1/reminders`,
- `houmao-agent-email-comms` for mailbox send, check, read, reply, and mailbox-state follow-up work around self-mail reminders,
- `houmao-process-emails-via-gateway` for notifier-driven unread-mail rounds when the self-notification mode is self-mail.

The pattern family SHALL explain that gateway reminders are the preferred mode when the task is high-priority, should stay focused ahead of unrelated new incoming mail, or benefits from one-off, repeating, ranking, or pause behavior.

The pattern family SHALL explain that self-mail reminders are the preferred mode when the reminder must survive gateway shutdown or restart, or when the later round should be allowed to re-triage that reminder together with newly arrived unread mail.

For multi-step work, the pattern family SHALL direct the agent to keep the detailed substep list in local todo or scratch state and use one reminder or self-mail item per major work chunk rather than one mailbox reminder per tiny substep.

#### Scenario: Focused high-priority self-notification selects gateway reminders
- **WHEN** a managed agent needs to remind itself about high-priority work that should be handled before unrelated new incoming mail
- **THEN** the advanced-usage skill directs that agent to the live gateway reminder mode through `houmao-agent-gateway`
- **AND THEN** it describes that mode as the focus-first self-notification path rather than routing the agent through mailbox backlog first

#### Scenario: Durable or inbox-integrated self-notification selects self-mail
- **WHEN** a managed agent needs a reminder backlog that should survive gateway shutdown or that may be reprioritized together with other unread mail later
- **THEN** the advanced-usage skill directs that agent to the self-mail mode through `houmao-agent-email-comms` plus notifier-driven unread-mail rounds
- **AND THEN** it describes that mode as the durable or inbox-integrated self-notification path

#### Scenario: Multi-step work uses local todo state plus one major-chunk reminder
- **WHEN** a managed agent needs to continue a multi-step task later
- **THEN** the advanced-usage skill directs the agent to keep the detailed checklist in local todo or scratch state
- **AND THEN** it does not describe one mailbox reminder per tiny substep as the default pattern

### Requirement: `houmao-adv-usage-pattern` states self-wakeup durability boundaries honestly
The self-notification pattern family in `houmao-adv-usage-pattern` SHALL describe the focus, scheduling, and durability boundaries of gateway reminders and self-mail honestly.

For live gateway reminders, the pattern family SHALL state that:

- `/v1/reminders` is live gateway state rather than durable recovery state,
- reminder entries do not survive gateway shutdown or restart,
- reminder delivery does not mix with newly arrived unread mailbox traffic,
- the mode supports richer live behavior such as one-off timing, repeating cadence, ranking, and pause semantics.

For self-mail reminders, the pattern family SHALL state that:

- unread self-mail is the durable backlog for that mode,
- that durable backlog can survive gateway loss because it is mailbox state rather than gateway process state,
- later notifier-driven rounds inspect that backlog through ordinary unread-mail flow and therefore may encounter self-reminders together with unrelated new incoming mail.

When the caller is unsure and durable recovery is not an explicit requirement, the pattern family SHALL recommend `/v1/reminders` as the default self-notification mode because it provides the richer live reminder feature set.

The pattern family SHALL NOT claim guaranteed unfinished-work recovery beyond the actual mailbox unread state and live gateway contracts.

#### Scenario: Reminder mode supports focus-first work without mixing with new mail
- **WHEN** an agent or operator reads the reminder mode guidance in the advanced-usage self-notification family
- **THEN** the page states that live gateway reminders do not mix with newly arrived unread mailbox traffic
- **AND THEN** it describes that mode as the better fit for "work on this first" behavior

#### Scenario: Self-mail mode stays durable but mixes with unread mailbox triage
- **WHEN** an agent or operator reads the self-mail mode guidance in the advanced-usage self-notification family
- **THEN** the page states that unread self-mail is the durable backlog for that mode
- **AND THEN** it states that later unread-mail rounds may mix those self-reminders with unrelated new incoming mail

#### Scenario: Default recommendation prefers reminders when durability is not required
- **WHEN** an agent or operator needs self-notification guidance without an explicit durability requirement
- **THEN** the advanced-usage skill recommends live gateway reminders as the default mode
- **AND THEN** it still states that self-mail is the correct choice when gateway-surviving durability is required
