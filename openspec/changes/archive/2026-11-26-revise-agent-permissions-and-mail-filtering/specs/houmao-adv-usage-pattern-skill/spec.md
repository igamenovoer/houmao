# Houmao Advanced Usage Pattern Skill Delta

## MODIFIED Requirements

### Requirement: Advanced usage pattern fixes v2 mail contract examples and covers CCCC and work requests
`houmao-adv-usage-pattern` SHALL use schema v3 lifecycle examples in `commands/notifier-prompt-driven-mail-loop.md` and limit ordinary archive examples to bindings that authorize filing. The skill SHALL retain `houmao-cccc` push, pull, and queue patterns as an explicit coordination option and cover `agents single request` in `pairwise-edge-loop`.

#### Scenario: Notifier mail loop example uses valid schema v3 without include_body
- **WHEN** an agent copies or adapts the `/v1/mail/{channel}/list|read|reply|archive` curl examples in `notifier-prompt-driven-mail-loop.md`
- **THEN** every request body uses `"schema_version": 3` and omits the rejected `"include_body"` field
- **AND THEN** the example directs protected Inbox work to independently authorized owner filing
- **AND THEN** pairwise and relay patterns distinguish `houmao-cccc` chat/queue coordination and attributed `request` from direct `prompt` and mail turns

### Requirement: `houmao-adv-usage-pattern` self-wakeup guidance composes existing Houmao skills

The packaged `houmao-adv-usage-pattern` skill SHALL compare live gateway reminders through `/v1/reminders` and self-mail reminders that re-enter through unread Inbox work.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The self-notification guidance SHALL compose maintained routines. It SHALL use `houmao-agent-gateway` for live reminder creation, inspection, update, and deletion. It SHALL use `houmao-agent-email-comms` for ordinary self-mail send, list, read, reply, and authorized filing. It SHALL use `houmao-process-emails-via-gateway` for bounded notifier-driven unread-mail rounds.

The pattern SHALL prefer live reminders when work has high priority, needs focus ahead of unrelated mail, or benefits from one-off timing, repeating reminders, ranking, or pause. It SHALL prefer self-mail when Inbox delivery is available and the reminder must survive gateway shutdown or be triaged with other unread mail.

For multi-step work, the pattern SHALL direct the agent to keep the detailed checklist in local todo or scratch state and use one reminder or self-mail item per major work chunk.

#### Scenario: Focused high-priority self-notification selects gateway reminders

- **WHEN** a managed agent needs to remind itself about high-priority work that should be handled before unrelated new incoming mail
- **THEN** the advanced-usage skill directs that agent to the live gateway reminder mode through `houmao-agent-gateway`
- **AND THEN** it describes that mode as the focus-first self-notification path

#### Scenario: Durable or inbox-integrated self-notification selects self-mail

- **WHEN** a managed agent needs a reminder backlog that should survive gateway shutdown or that may be reprioritized together with other unread mail later
- **THEN** the advanced-usage skill directs that agent to the self-mail mode through `houmao-agent-email-comms` plus notifier-driven unread-mail rounds where the backend delivers self-mail to Inbox
- **AND THEN** it describes that mode as the durable or inbox-integrated self-notification path

#### Scenario: Multi-step work uses local todo state plus one major-chunk reminder

- **WHEN** a managed agent needs to continue a multi-step task later
- **THEN** the advanced-usage skill directs the agent to keep the detailed checklist in local todo or scratch state
- **AND THEN** it recommends one reminder or self-mail item per major work chunk

## ADDED Requirements

### Requirement: Advanced Mail Patterns Use the Binding's Authorized Filing Path

The notifier-driven mail loop, self-mail wake-up, and shared loop ledger guidance SHALL delegate ordinary mailbox authority to `houmao-agent-email-comms` and round execution to `houmao-process-emails-via-gateway`. They SHALL use the backend's authoritative Inbox and the binding's authorized filing path for completed mail.

#### Scenario: The Notifier Loop Shows a Bounded Round

- **WHEN** a reader follows `commands/notifier-prompt-driven-mail-loop.md`
- **THEN** the HTTP examples pin the explicit channel and `expected_binding_id`, use `schema_version: 3`, and start with one bounded metadata-only Inbox page without `include_body`
- **AND THEN** the round inspects selected content, reconciles any required reply on the same binding, and ends without polling

#### Scenario: A Completed Mail Item Uses the Authorized Filing Path

- **WHEN** a reader follows the notifier loop, `commands/self-wakeup-via-self-mail.md`, or `references/shared-loop-ledger-and-resend.md` for a completed item
- **THEN** the guidance offers ordinary archive only when the binding and caller permit it and the work and any required reply have succeeded
- **AND THEN** on a protected binding it reports the completed item for independently authorized owner filing and leaves unfinished mail in place
- **AND THEN** the examples do not use move, delete, or archived-state marking to bypass a placement restriction

#### Scenario: A Transport Acceptance Does Not Confirm a Self-Mail Wake-Up

- **WHEN** a self-mail send is accepted but the backend files the message directly into Archive under a block rule
- **THEN** the guidance treats that message as outside Inbox reminder work
- **AND THEN** the transport receipt retains its normal meaning and exposes no filing decision
