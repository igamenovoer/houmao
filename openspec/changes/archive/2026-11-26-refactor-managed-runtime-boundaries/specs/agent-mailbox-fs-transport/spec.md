# Spec Delta

## ADDED Requirements

### Requirement: Mailbox-local unread summaries reflect committed message state
For each message changed by filesystem mailbox mark, move, or archive, Houmao SHALL commit recipient-local message flags and the affected unread thread summary together. The unread count SHALL reflect the current unread rows for that thread in the same mailbox-local database.

#### Scenario: Archive marks an unread message and refreshes its thread
- **WHEN** an operator archives the only unread message in a filesystem mailbox thread by message reference
- **THEN** the message is archived and read under the existing archive contract
- **AND THEN** its mailbox-local thread has an unread count of zero at successful completion

#### Scenario: Repeating a move to archive preserves the summary
- **WHEN** a caller repeats a supported move of a recipient message to archive
- **THEN** the message state and thread count agree after the move
- **AND THEN** the move preserves other recipient-local flags and other mailboxes' state

#### Scenario: Ordinary mark updates the same derived summary
- **WHEN** a caller marks a filesystem message read or unread in a box that supports that transition
- **THEN** the unread count reflects the successful mark in the same committed state
