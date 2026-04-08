## ADDED Requirements

### Requirement: Filesystem self-addressed delivery starts unread for the recipient mailbox
When the filesystem mailbox transport delivers a message to one or more recipient mailboxes, initial mailbox-local unread or read state SHALL be determined by recipient membership for each mailbox rather than by sender role alone.

For one mailbox registration:

- if that mailbox registration is among the delivered recipients for the message, the initial mailbox-local state SHALL be unread,
- if that mailbox registration is not among the delivered recipients and only has the sender-side copy, the initial mailbox-local state SHALL be read.

When the sender and recipient resolve to the same active filesystem mailbox registration, the resulting mailbox-local state for that mailbox SHALL be unread until explicitly marked read.

Structural mailbox projections MAY still include both `sent/` and `inbox/` entries for that same mailbox. Those projection folders SHALL NOT override the mailbox-local unread state for the self-addressed message.

#### Scenario: Self-sent filesystem mail stays unread for the sender-recipient mailbox
- **WHEN** a filesystem mailbox participant sends one new message to its own mailbox address
- **THEN** the resulting message is projected structurally as mail for that same mailbox
- **AND THEN** that mailbox's mailbox-local actor state starts unread until the participant explicitly marks the message read

#### Scenario: Sender-only mailbox copy still starts read
- **WHEN** a filesystem mailbox participant sends one new message to some other mailbox address and does not include its own mailbox as a recipient
- **THEN** the sender mailbox keeps a sender-side copy for that message
- **AND THEN** that sender mailbox copy starts read by default

### Requirement: Filesystem mailbox state reconstruction preserves self-addressed unread defaults
Whenever the filesystem mailbox transport reconstructs, repairs, or lazily initializes mailbox-local message state for an already projected message, it SHALL preserve the same self-addressed unread semantics as fresh delivery.

That rule SHALL apply at minimum to:

- index or mailbox-local state repair from canonical message files,
- lazy insertion of mailbox-local message-state rows for an existing projected message,
- any other default mailbox-local read-state initialization path that recreates state without an explicit prior mailbox-local read record.

For a self-addressed message projected into the same mailbox as both sender and recipient, those reconstruction paths SHALL initialize that mailbox-local state as unread rather than deriving read state only from the existence of a `sent` projection.

#### Scenario: Repaired mailbox-local state keeps self-addressed mail unread
- **WHEN** the filesystem mailbox transport repairs or rebuilds mailbox-local state for a self-addressed message
- **THEN** the rebuilt mailbox-local state for that mailbox starts unread if no explicit prior mailbox-local read record exists
- **AND THEN** later actor-scoped unread checks continue to treat that self-addressed message as unread until explicitly marked read

