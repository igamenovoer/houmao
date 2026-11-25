# CLI Reference Delta

## MODIFIED Requirements

### Requirement: CLI reference documents revised scoped `agents ... mail` lifecycle commands

The CLI reference SHALL document scoped mail discovery, processing, completion, and result authority. It SHALL describe lifecycle commands according to the selected mailbox binding's capabilities and the caller's authority. On protected bindings it SHALL direct readers to independently authorized owner archive for successfully processed mail.

#### Scenario: Reader Finds Scoped Mail Commands

- **WHEN** a reader opens the `agents single ... mail` or `agents self mail` reference
- **THEN** the page covers `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive` and identifies the applicable binding and authority for each
- **AND THEN** it explains explicit selection and current-session selection inside the owning managed tmux session
- **AND THEN** it describes `resolve-live` structured output with a mailbox binding and optional `gateway.base_url`, without mailbox-specific shell exports

#### Scenario: Reader Processes Mail

- **WHEN** a reader follows the current mailbox lifecycle
- **THEN** the page distinguishes listing, peeking, and reading, and explains that replying or acknowledging marks mail answered while leaving it open
- **AND THEN** it describes archive as the completion action through the applicable authorized path and omits `check` and `mark-read` as current lifecycle steps
- **AND THEN** it distinguishes verified execution from non-authoritative TUI submission fallback

#### Scenario: Reader can find archive and move commands

- **WHEN** a reader looks up `houmao-mgr agents single ... mail` or `houmao-mgr agents self mail`
- **THEN** the CLI reference documents `archive` and `move` for bindings and callers that authorize them
- **AND THEN** the reader can tell that successfully processed mail on a protected binding needs independently authorized owner archive through the backend

#### Scenario: Reader understands peek versus read

- **WHEN** a reader looks up mailbox message inspection commands
- **THEN** the CLI reference explains that `peek` leaves read state unchanged
- **AND THEN** it explains that `read` returns the message and marks it read

### Requirement: CLI reference documents gateway mail-notifier mode

The CLI reference for scoped `houmao-mgr agents single ... gateway` and `houmao-mgr agents self gateway` SHALL document the mode option on `mail-notifier enable`. It SHALL list `any_inbox` and `unread_only`, identify `any_inbox` as the default, and explain that both modes observe the selected transport's authoritative Inbox. `unread_only` wakes only for unread, unarchived Inbox mail.

#### Scenario: Reader finds mail-notifier mode option

- **WHEN** a reader opens the scoped `agents single ... gateway mail-notifier enable` or `agents self gateway mail-notifier enable` CLI reference
- **THEN** the option table documents the notifier mode option and its allowed values
- **AND THEN** the prose states that `any_inbox` is the default

#### Scenario: Reader understands unread-only trade-off

- **WHEN** a reader studies the `unread_only` mode documentation
- **THEN** the CLI reference explains that only unread, unarchived mail in the selected backend's Inbox triggers notifications in that mode
- **AND THEN** it does not imply that read-but-unarchived mail will continue to wake the agent in `unread_only` mode

#### Scenario: Reader Understands Reminders While Owner Archive Is Pending

- **WHEN** a reader uses mail notification on a protected binding
- **THEN** the CLI reference explains that `any_inbox` can continue to remind for eligible processed mail until independently authorized owner archive files it
- **AND THEN** it explains that `unread_only` still requires unread Inbox mail

#### Scenario: Reader Understands Delivery-Time Archive

- **WHEN** a reader checks how an applied block rule affects either notifier mode
- **THEN** the CLI reference explains that the backend files matching new arrivals directly to Archive and that both modes use the same authoritative Inbox
- **AND THEN** it explains that applying a rule leaves existing Inbox mail in place and that removing the rule leaves previously archived mail in Archive
