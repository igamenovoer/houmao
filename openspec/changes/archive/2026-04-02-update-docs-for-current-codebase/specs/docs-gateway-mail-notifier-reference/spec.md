## ADDED Requirements

### Requirement: Gateway mail-notifier reference page exists

The gateway reference SHALL include a page at `docs/reference/gateway/operations/mail-notifier.md` documenting the gateway mail-notifier subsystem. The page SHALL explain:

- What the mail-notifier is: a gateway-owned background loop that periodically checks the agent's mailbox and notifies the agent of new mail by injecting a prompt through the gateway request queue.
- Configuration: `enable` with optional `--interval-seconds`, `disable`, and `status` commands.
- Email processing flow: how the notifier detects new messages, formats a notification prompt, and submits it through the gateway's request pipeline.
- Integration with the gateway lifecycle: when the notifier starts/stops relative to gateway attach/detach, and how it interacts with the gateway's request queue and TUI state tracking.

The page SHALL be derived from `gateway_service.py` mail-notifier methods and `mail_commands.py`.

#### Scenario: Reader understands mail-notifier purpose

- **WHEN** a reader opens the mail-notifier reference page
- **THEN** they find a clear explanation of the notifier's role as a background polling loop within the gateway that bridges the mailbox subsystem to the agent's prompt input

#### Scenario: Reader can configure the mail-notifier

- **WHEN** a reader needs to enable or tune the mail-notifier
- **THEN** the page documents `houmao-mgr agents gateway mail-notifier enable`, `disable`, and `status` commands with their options
- **AND THEN** the page explains that `--interval-seconds` controls the polling frequency

#### Scenario: Reader understands email processing prompt flow

- **WHEN** a reader wants to understand how mail becomes agent prompts
- **THEN** the page explains the flow: mailbox check → new message detection → notification prompt formatting → gateway request queue submission
- **AND THEN** the page references the email processing prompt template used by the notifier

### Requirement: Gateway index links to mail-notifier page

The gateway reference index at `docs/reference/gateway/index.md` SHALL include a link to the mail-notifier operations page under its operations section.

#### Scenario: Mail-notifier discoverable from gateway index

- **WHEN** a reader navigates to the gateway reference index
- **THEN** they find a link to `operations/mail-notifier.md` with a brief description
