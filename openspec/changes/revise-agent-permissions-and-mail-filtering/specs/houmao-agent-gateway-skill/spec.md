# Gateway Agent Skill Delta

## MODIFIED Requirements

### Requirement: Gateway system skill documents notifier notification mode

The packaged `houmao-agent-gateway` system skill SHALL describe `mail-notifier` as mailbox-driven notification control for mailbox-enabled sessions. Its guidance SHALL explain that `any_inbox` is the default and includes unarchived mail in the backend's authoritative Inbox. The opt-in `unread_only` mode limits this eligible set to unread mail.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The guidance SHALL mention that `unread_only` is a lower-noise mode and that read-but-unarchived mail will not by itself trigger future notifier prompts in that mode.

#### Scenario: Gateway skill shows default notifier mode

- **WHEN** a caller reads the `houmao-agent-gateway` mail-notifier guidance
- **THEN** the guidance states that `any_inbox` is the default notifier mode
- **AND THEN** it describes that default as notification for unarchived Inbox mail regardless of read or answered state, subject to ordinary readiness and admission rules

#### Scenario: Gateway skill shows unread-only opt-in mode

- **WHEN** a caller reads the `houmao-agent-gateway` mail-notifier guidance
- **THEN** the guidance documents `unread_only` as an opt-in notifier mode
- **AND THEN** it explains that read-but-unarchived mail is not notifier-eligible in that mode

#### Scenario: Gateway skill stays mail-specific

- **WHEN** a caller reads the notifier guidance in the packaged gateway skill
- **THEN** the skill presents `mail-notifier` as mailbox-driven notification control
- **AND THEN** it does not describe notifier mode as a generic unfinished-job persistence mechanism

#### Scenario: Gateway Skill Explains Backend-Owned Inbox Placement

- **WHEN** a caller asks how sender blocking affects Inbox reminders
- **THEN** the guidance explains that the backend files matching new mail directly into Archive and that both modes observe open work in the authoritative Inbox
- **AND THEN** it explains that rule changes leave existing Inbox placement in effect and that unblocking leaves archived messages in Archive
