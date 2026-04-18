## MODIFIED Requirements

### Requirement: Gateway mail-notifier reference page exists
The gateway reference SHALL include a page at `docs/reference/gateway/operations/mail-notifier.md` documenting the gateway mail-notifier subsystem. The page SHALL explain:

- What the mail-notifier is: a gateway-owned background loop that periodically checks the agent's mailbox and notifies the agent of open inbox work by injecting a prompt through the gateway request queue.
- Configuration: `enable` with optional `--interval-seconds`, `disable`, and `status` commands.
- Appendix configuration: notifier state includes queryable `appendix_text`, `PUT` preserves the stored appendix when the field is omitted, replaces it when a non-empty string is sent, and clears it when an empty string is sent.
- Email processing flow: how the notifier polls open inbox work through the mailbox adapter, computes a digest from the current open message references for notifier state or audit purposes, checks whether gateway prompt delivery is currently blocked, formats a notification prompt, and submits that prompt through the gateway request pipeline when the gateway is ready.
- Current repeat-notification behavior: the current implementation does not suppress later notifications merely because the open-work digest is unchanged, so the same open inbox snapshot MAY be enqueued again on later polling cycles while those messages remain unarchived.
- Native mailbox-skill guidance: notifier prompts tell supported agents to use installed runtime-home Houmao mailbox skills through native invocation or explicit skill names rather than by opening `skills/.../SKILL.md` paths.
- Archive-after-processing guidance: notifier prompts instruct agents to archive successfully processed mail and do not present mark-read as the completion action.
- Integration with the gateway lifecycle: when the notifier starts or stops relative to gateway attach and gateway shutdown, and how it interacts with the gateway's request queue and TUI state tracking.

The page SHALL be derived from `gateway_service.py` mail-notifier methods and `gateway_storage.py` notifier record and audit models.

#### Scenario: Reader understands mail-notifier purpose
- **WHEN** a reader opens the mail-notifier reference page
- **THEN** they find a clear explanation of the notifier's role as a background polling loop within the gateway that bridges open mailbox work to the agent's prompt input

#### Scenario: Reader can configure the mail-notifier
- **WHEN** a reader needs to enable or tune the mail-notifier
- **THEN** the page documents `houmao-mgr agents gateway mail-notifier enable`, `disable`, and `status` commands with their options
- **AND THEN** the page explains that `--interval-seconds` controls the polling frequency

#### Scenario: Reader understands the current prompt-enqueue flow
- **WHEN** a reader wants to understand how mail becomes agent prompts
- **THEN** the page explains the flow: open-work poll through the mailbox adapter, open-work digest computation for notifier state or audit, gateway readiness check, notification prompt formatting, and internal gateway queue submission
- **AND THEN** the page references the email processing prompt template used by the notifier

#### Scenario: Reader does not learn nonexistent digest-based suppression
- **WHEN** a reader studies the notifier reference to understand repeat wake behavior for unchanged open inbox work
- **THEN** the page states that the current implementation may enqueue repeated notifier prompts for the same unchanged open-work snapshot while those messages remain unarchived
- **AND THEN** it does not claim that open-work digest computation currently prevents those repeated notifications

#### Scenario: Reader does not learn a path-based skill contract from the reference page
- **WHEN** a reader studies the notifier reference to understand how the wake-up prompt uses mailbox skills
- **THEN** the page explains native installed-skill invocation guidance for supported tools
- **AND THEN** it does not describe `SKILL.md` paths as the ordinary operational contract for notifier-driven mailbox rounds

#### Scenario: Reader understands archive as the notifier workflow completion action
- **WHEN** a reader studies the notifier reference to understand how agents finish notified mailbox work
- **THEN** the page explains that successfully processed mail should be archived
- **AND THEN** it does not present mark-read as the completion action for the notifier workflow

#### Scenario: Reader understands appendix update semantics
- **WHEN** a reader studies the notifier reference to understand appendix behavior
- **THEN** the page explains that omitted `appendix_text` preserves the stored appendix, non-empty text replaces it, and the empty string clears it
- **AND THEN** the page states that notifier status returns the effective appendix text
