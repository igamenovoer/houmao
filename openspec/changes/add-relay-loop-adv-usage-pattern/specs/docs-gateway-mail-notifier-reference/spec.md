## MODIFIED Requirements

### Requirement: Gateway mail-notifier reference page exists

The gateway reference SHALL include a page at `docs/reference/gateway/operations/mail-notifier.md` documenting the gateway mail-notifier subsystem. The page SHALL explain:

- What the mail-notifier is: a gateway-owned background loop that periodically checks the agent's mailbox and notifies the agent of unread mail by injecting a prompt through the gateway request queue.
- Configuration: `enable` with optional `--interval-seconds`, `disable`, and `status` commands.
- Email processing flow: how the notifier polls unread mail through the mailbox adapter, computes a digest from the current unread message references for notifier state or audit purposes, checks whether gateway prompt delivery is currently blocked, formats a notification prompt, and submits that prompt through the gateway request pipeline when the gateway is ready.
- Current repeat-notification behavior: the current implementation does not suppress later notifications merely because the unread digest is unchanged, so the same unread snapshot MAY be enqueued again on later polling cycles while those messages remain unread.
- Native mailbox-skill guidance: notifier prompts tell supported agents to use installed runtime-home Houmao mailbox skills through native invocation or explicit skill names rather than by opening `skills/.../SKILL.md` paths.
- Integration with the gateway lifecycle: when the notifier starts or stops relative to gateway attach and gateway shutdown, and how it interacts with the gateway's request queue and TUI state tracking.

The page SHALL be derived from `gateway_service.py` mail-notifier methods and `gateway_storage.py` notifier record and audit models.

#### Scenario: Reader understands mail-notifier purpose

- **WHEN** a reader opens the mail-notifier reference page
- **THEN** they find a clear explanation of the notifier's role as a background polling loop within the gateway that bridges the mailbox subsystem to the agent's prompt input

#### Scenario: Reader can configure the mail-notifier

- **WHEN** a reader needs to enable or tune the mail-notifier
- **THEN** the page documents `houmao-mgr agents gateway mail-notifier enable`, `disable`, and `status` commands with their options
- **AND THEN** the page explains that `--interval-seconds` controls the polling frequency

#### Scenario: Reader understands the current prompt-enqueue flow

- **WHEN** a reader wants to understand how mail becomes agent prompts
- **THEN** the page explains the flow: unread poll through the mailbox adapter, unread digest computation for notifier state or audit, gateway readiness check, notification prompt formatting, and internal gateway queue submission
- **AND THEN** the page references the email processing prompt template used by the notifier

#### Scenario: Reader does not learn nonexistent digest-based suppression

- **WHEN** a reader studies the notifier reference to understand repeat wake behavior for unchanged unread mail
- **THEN** the page states that the current implementation may enqueue repeated notifier prompts for the same unchanged unread snapshot while those messages remain unread
- **AND THEN** it does not claim that unread-digest computation currently prevents those repeated notifications

#### Scenario: Reader does not learn a path-based skill contract from the reference page

- **WHEN** a reader studies the notifier reference to understand how the wake-up prompt uses mailbox skills
- **THEN** the page explains native installed-skill invocation guidance for supported tools
- **AND THEN** it does not describe `SKILL.md` paths as the ordinary operational contract for notifier-driven mailbox rounds
