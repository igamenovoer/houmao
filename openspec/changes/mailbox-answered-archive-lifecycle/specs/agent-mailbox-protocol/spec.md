## ADDED Requirements

### Requirement: Shared mailbox lifecycle state separates read, answered, and archived semantics
The shared mailbox protocol SHALL distinguish message visibility from task completion.

Per-recipient mailbox state exposed through runtime-owned and gateway-owned mailbox surfaces SHALL include at minimum:

- `read`, meaning the recipient consumed the message body through a mutating read workflow or explicitly marked it read,
- `answered`, meaning the recipient replied to or acknowledged the message,
- `archived`, meaning the recipient moved the message out of the open inbox workflow into archive,
- the current mailbox box or boxes for that recipient.

The shared protocol SHALL NOT treat `read=true` or `answered=true` as completion. A message remains open work while it is in the recipient inbox and is not archived or otherwise closed.

#### Scenario: Acknowledged mail remains open until archived
- **WHEN** an agent replies to a mailbox message with an acknowledgement before completing the requested work
- **THEN** the parent message is marked `answered=true`
- **AND THEN** the parent message remains open inbox work until the agent archives it

#### Scenario: Reading mail does not close it
- **WHEN** a recipient reads a mailbox message body
- **THEN** the recipient-local state records `read=true`
- **AND THEN** the message remains open inbox work unless it has also been archived or moved out of the inbox workflow

### Requirement: Shared mailbox operations support list, peek, read, mark, move, and archive
The shared mailbox operation contract exposed through runtime-owned and gateway-owned mailbox surfaces SHALL include transport-neutral operations for:

- listing messages from a named mailbox box,
- peeking a message body without mutating read state,
- reading a message body while marking it read,
- manually marking supported recipient-local state fields,
- moving messages among supported mailbox boxes,
- archiving selected messages as a shortcut for moving them to the archive box.

All operations that target existing messages SHALL use opaque plain-string `message_ref` values. Callers SHALL treat the entire value as opaque and SHALL NOT derive behavior from transport-specific prefixes, paths, encodings, or storage identifiers.

The shared archive operation SHALL accept one or more opaque message references, SHALL move those messages to the recipient archive box, SHALL mark them archived, and SHALL mark them read by default. It SHALL NOT mark them answered unless a separate reply or mark operation did so.

#### Scenario: Peek returns content without marking read
- **WHEN** a caller peeks a mailbox message through the shared mailbox operation contract
- **THEN** the operation returns the selected message body and metadata
- **AND THEN** recipient-local `read` state for that message does not change

#### Scenario: Read returns content and marks read
- **WHEN** a caller reads a mailbox message through the shared mailbox operation contract
- **THEN** the operation returns the selected message body and metadata
- **AND THEN** recipient-local `read` state for that message is set to `true`

#### Scenario: Archive closes selected inbox work
- **WHEN** a caller archives selected inbox messages by opaque `message_ref`
- **THEN** the messages are moved to the recipient archive box
- **AND THEN** recipient-local state records those messages as archived and no longer open inbox work

### Requirement: Replies automatically mark the replied message answered
When a recipient successfully sends a reply to a mailbox message through the shared mailbox operation contract, the system SHALL mark the replied message `answered=true` for that recipient.

The reply transition SHALL also mark the replied message read for that recipient. It SHALL NOT archive the replied message.

This requirement applies to substantive replies and acknowledgement replies alike.

#### Scenario: Reply marks parent answered without archiving it
- **WHEN** an agent replies to an existing mailbox message
- **THEN** the replied message is marked `answered=true` and `read=true` for that agent
- **AND THEN** the replied message remains in its current box until an explicit move or archive operation succeeds

## REMOVED Requirements

### Requirement: Shared mailbox read-state updates target opaque message references
**Reason**: Single-message read-only mutation conflates mailbox consumption with task completion and cannot represent acknowledgement or archive lifecycle state.
**Migration**: No compatibility migration is required. Callers and tests must use the new shared `read`, `mark`, `move`, and `archive` mailbox operation contract.
