## ADDED Requirements

### Requirement: Shared mailbox read-state updates target opaque message references
The shared mailbox operation contract exposed through runtime-owned and gateway-owned mailbox surfaces SHALL include `check`, `send`, `reply`, and explicit per-recipient read-state update by opaque `message_ref`.

Callers SHALL treat that `message_ref` as the entire targeting contract and SHALL NOT derive transport-local message identifiers from embedded prefixes, encodings, or storage details.

For this change, the shared read-state update contract SHALL support setting `read=true` for one processed message after successful mailbox handling and SHALL NOT expand to broader mailbox-state flag editing.

Applying a shared read-state update SHALL mutate recipient-local mailbox state without rewriting immutable canonical message content.

#### Scenario: Filesystem shared read-state update uses opaque target
- **WHEN** a caller marks one filesystem-backed message read through a shared mailbox surface using `message_ref`
- **THEN** the mailbox system resolves that opaque target without requiring the caller to supply the underlying filesystem `message_id`
- **AND THEN** the recipient-local read state changes while the canonical message document remains unchanged

#### Scenario: Stalwart shared read-state update uses the same opaque target shape
- **WHEN** a caller marks one `stalwart`-backed message read through a shared mailbox surface using `message_ref`
- **THEN** the caller uses the same opaque shared targeting contract as the filesystem transport
- **AND THEN** transport-owned identifiers remain hidden behind that shared mailbox operation contract
