## ADDED Requirements

### Requirement: CLI reference documents revised `agents mail` lifecycle commands
When the CLI reference documents `agents mail`, that coverage SHALL include the current subcommands `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`.

That coverage SHALL explain:

- the selector rules for explicit targeting versus current-session targeting inside the owning managed tmux session,
- the structured `resolve-live` result contract for current mailbox discovery, including the returned mailbox binding and optional `gateway.base_url`,
- that mailbox-specific shell export is not part of the supported `resolve-live` contract,
- the difference between listing, peeking, and reading mail,
- that reply or acknowledgement marks a message answered but does not close it,
- that archive is the normal completion action for processed mail,
- the authority-aware result semantics that distinguish verified execution from non-authoritative TUI submission fallback.

The CLI reference SHALL NOT present `check` or `mark-read` as the current mailbox lifecycle workflow for processed mail after this change.

#### Scenario: Reader can find archive and move commands
- **WHEN** a reader looks up `houmao-mgr agents mail`
- **THEN** the CLI reference documents `archive` and `move` as supported mailbox lifecycle commands
- **AND THEN** the reader can tell that archive is the common processed-mail completion command

#### Scenario: Reader understands peek versus read
- **WHEN** a reader looks up mailbox message inspection commands
- **THEN** the CLI reference explains that `peek` does not mark a message read
- **AND THEN** it explains that `read` returns the message and marks it read
