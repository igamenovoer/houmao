## ADDED Requirements

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
