# docs-gateway-mail-notifier-reference Specification

## Purpose
Define the documentation requirements for the gateway mail-notifier reference page.
## Requirements
### Requirement: Gateway mail-notifier reference page exists
The gateway reference SHALL include a page at `docs/reference/gateway/operations/mail-notifier.md` documenting the gateway mail-notifier subsystem. The page SHALL explain:

- What the mail-notifier is: a gateway-owned background loop that periodically checks the agent's mailbox and notifies the agent of open inbox work by injecting a prompt through the gateway request queue.
- Configuration: `enable` with optional `--interval-seconds`, `disable`, and `status` commands.
- Appendix configuration: notifier state includes queryable `appendix_text`, `PUT` preserves the stored appendix when the field is omitted, replaces it when a non-empty string is sent, and clears it when an empty string is sent.
- Email processing flow: how the notifier polls open inbox work through the mailbox adapter, computes a digest from the current open message references for notifier state or audit purposes, checks whether gateway prompt delivery is currently blocked, optionally runs pre-notification compaction, formats a notification prompt, and submits that prompt through the gateway request pipeline when the gateway is ready.
- Current compaction behavior: when `pre_notification_context_action=compact` is enabled, the current implementation runs compaction at most once for a currently eligible mail item while that item remains eligible for the configured notifier mode.
- Current repeat-notification behavior: unchanged open inbox snapshots MAY still produce later notifier prompts on later polling cycles while those messages remain eligible, but repeated wake-up prompts do not imply repeated compaction for the same continuously eligible mail item.
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
- **THEN** the page explains the flow: open-work poll through the mailbox adapter, open-work digest computation for notifier state or audit, readiness checks, optional pre-notification compaction, notification prompt formatting, and internal gateway queue submission
- **AND THEN** the page references the email processing prompt template used by the notifier

#### Scenario: Reader understands one-shot compaction without prompt dedup claims
- **WHEN** a reader studies the notifier reference to understand repeat wake behavior for unchanged open inbox work
- **THEN** the page states that repeated notifier prompts may still occur for unchanged eligible mail
- **AND THEN** it explains that the same continuously eligible mail does not trigger repeated pre-notification compaction on those later cycles
- **AND THEN** it does not claim that digest computation alone suppresses all repeated wake-up prompts

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

### Requirement: Gateway index links to mail-notifier page

The gateway reference index at `docs/reference/gateway/index.md` SHALL include a link to the mail-notifier operations page under its operations section.

#### Scenario: Mail-notifier discoverable from gateway index

- **WHEN** a reader navigates to the gateway reference index
- **THEN** they find a link to `operations/mail-notifier.md` with a brief description

### Requirement: Gateway mail-notifier reference documents notification mode
The gateway mail-notifier reference page SHALL document notifier notification mode as part of notifier configuration and behavior.

The page SHALL explain:

- `any_inbox` is the default mode and wakes for any unarchived inbox mail, including read or answered mail.
- `unread_only` is an opt-in mode and wakes only for unread unarchived inbox mail.
- Archive remains the completion action for processed mailbox work in both modes.
- Read or answered state is not completion in `any_inbox` mode.
- Read-but-unarchived mail will not by itself trigger future notifier prompts in `unread_only` mode.

The page SHALL document that notifier status includes the effective mode.

#### Scenario: Reader understands default open inbox notification
- **WHEN** a reader opens the gateway mail-notifier reference
- **THEN** the page states that the default mode is `any_inbox`
- **AND THEN** it explains that read or answered unarchived inbox mail remains notifier-eligible in that mode

#### Scenario: Reader understands unread-only notification
- **WHEN** a reader opens the gateway mail-notifier reference
- **THEN** the page documents `unread_only` as an opt-in mode
- **AND THEN** it explains that only unread unarchived inbox mail is notifier-eligible in that mode

#### Scenario: Reader sees mode in status contract
- **WHEN** a reader studies the `/v1/mail-notifier` status fields
- **THEN** the page includes the effective notifier mode
- **AND THEN** it does not present read state as the workflow completion signal
