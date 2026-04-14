## ADDED Requirements

### Requirement: CLI reference documents gateway mail-notifier mode
The CLI reference page for `houmao-mgr agents gateway` SHALL document the mail-notifier notification mode option on `mail-notifier enable`.

That documentation SHALL list supported mode values `any_inbox` and `unread_only`, SHALL state that omitted mode defaults to `any_inbox`, and SHALL explain that `unread_only` only wakes for unread unarchived inbox mail.

#### Scenario: Reader finds mail-notifier mode option
- **WHEN** a reader opens the `agents gateway mail-notifier enable` CLI reference
- **THEN** the option table documents the notifier mode option and its allowed values
- **AND THEN** the prose states that `any_inbox` is the default

#### Scenario: Reader understands unread-only trade-off
- **WHEN** a reader studies the `unread_only` mode documentation
- **THEN** the CLI reference explains that only unread unarchived inbox mail triggers notifications in that mode
- **AND THEN** it does not imply that read-but-unarchived mail will continue to wake the agent in `unread_only` mode
