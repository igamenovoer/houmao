## ADDED Requirements

### Requirement: Canonical mailbox protocol maps cleanly to standard email semantics
The canonical mailbox protocol SHALL preserve semantics that can be mapped onto standard email surfaces in a follow-up true-email adapter without changing canonical message meaning.

At minimum, the compatibility mapping SHALL preserve:

- `message_id`
- `in_reply_to`
- `references`
- sender and recipient identities
- `subject`
- `thread_id`
- Markdown body semantics
- attachment reference metadata

#### Scenario: Reply ancestry maps to standard email headers
- **WHEN** a canonical mailbox reply message is adapted to a future true-email transport
- **THEN** the adapter can map reply ancestry onto standard email threading headers such as `Message-ID`, `In-Reply-To`, and `References`
- **AND THEN** the canonical thread meaning remains unchanged by that adaptation

#### Scenario: Canonical thread id remains representable in email-compatible metadata
- **WHEN** a canonical mailbox thread is adapted to a future true-email transport
- **THEN** the adapter can preserve the canonical `thread_id` in compatible protocol metadata
- **AND THEN** subject text alone is not required to reconstruct canonical thread identity

### Requirement: True-email transport implementation is out of scope for this change
This change SHALL NOT require implementation of a localhost mail server, SMTP/IMAP runtime adapter, or true-email mailbox runtime operations.

#### Scenario: Filesystem implementation does not require a mail service
- **WHEN** the filesystem mailbox transport is implemented for this change
- **THEN** the implementation succeeds without starting or depending on a localhost mail service
- **AND THEN** the change still preserves documented compatibility with future true-email adaptation

#### Scenario: Compatibility documentation does not imply runtime support
- **WHEN** this change documents email-compatible headers or reserved mail-system env names
- **THEN** those compatibility documents do not require the current runtime to populate or use a true-email transport
- **AND THEN** a follow-up change can implement that transport without changing the canonical mailbox protocol
