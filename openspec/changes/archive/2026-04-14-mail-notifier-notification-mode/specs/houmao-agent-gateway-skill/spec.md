## ADDED Requirements

### Requirement: Gateway system skill documents notifier notification mode
The packaged `houmao-agent-gateway` system skill SHALL describe gateway `mail-notifier` as mailbox-driven notification control for mailbox-enabled sessions rather than as a generic reminder service.

The skill's mail-notifier guidance SHALL state that the default notifier mode is `any_inbox`, where any unarchived inbox mail remains notification-eligible.

The guidance SHALL document the opt-in `unread_only` mode, where only unread unarchived inbox mail is notification-eligible.

The guidance SHALL mention that `unread_only` is a lower-noise mode and that read-but-unarchived mail will not by itself trigger future notifier prompts in that mode.

#### Scenario: Gateway skill shows default notifier mode
- **WHEN** a caller reads the `houmao-agent-gateway` mail-notifier guidance
- **THEN** the guidance states that `any_inbox` is the default notifier mode
- **AND THEN** it describes that default as notification for unarchived inbox mail regardless of read or answered state

#### Scenario: Gateway skill shows unread-only opt-in mode
- **WHEN** a caller reads the `houmao-agent-gateway` mail-notifier guidance
- **THEN** the guidance documents `unread_only` as an opt-in notifier mode
- **AND THEN** it explains that read-but-unarchived mail is not notifier-eligible in that mode

#### Scenario: Gateway skill stays mail-specific
- **WHEN** a caller reads the notifier guidance in the packaged gateway skill
- **THEN** the skill presents `mail-notifier` as mailbox-driven notification control
- **AND THEN** it does not describe notifier mode as a generic unfinished-job persistence mechanism
