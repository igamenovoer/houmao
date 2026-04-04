## ADDED Requirements

### Requirement: `houmao-mgr mailbox messages` reports structural mailbox message inspection

The native `houmao-mgr mailbox messages list` and `houmao-mgr mailbox messages get` commands SHALL act as structural inspection over one filesystem mailbox root and one selected mailbox address.

Those commands MAY return canonical message metadata and address-scoped projection metadata for the selected address, including message identity, thread identity, projection folder, projection path, canonical path, sender metadata, recipient metadata, body content, headers, and attachments.

Those commands SHALL NOT report participant-local mutable mailbox view-state fields such as `read`, `starred`, `archived`, or `deleted`.

When an operator needs participant-local read or unread follow-up state, the supported surface SHALL be actor-scoped mail commands such as `houmao-mgr agents mail ...` or a future explicitly address-scoped state surface rather than mailbox-root administration commands.

#### Scenario: Root mailbox message list omits participant-local view-state flags

- **WHEN** an operator runs `houmao-mgr mailbox messages list --mailbox-root /tmp/shared-mail --address alice@agents.localhost`
- **THEN** the command returns structural message summaries for the selected address projection
- **AND THEN** each message summary may include fields such as `message_id`, `thread_id`, `subject`, `sender_address`, `folder`, `projection_path`, and `canonical_path`
- **AND THEN** the payload does not include `read`, `starred`, `archived`, or `deleted`

#### Scenario: Root mailbox message get omits participant-local view-state flags

- **WHEN** an operator runs `houmao-mgr mailbox messages get --mailbox-root /tmp/shared-mail --address alice@agents.localhost --message-id msg-123`
- **THEN** the command returns canonical message details together with the selected address projection metadata
- **AND THEN** the payload may include sender, recipients, headers, body content, attachments, `folder`, and `projection_path`
- **AND THEN** the payload does not claim a single authoritative participant-local read, starred, archived, or deleted state

### Requirement: `houmao-mgr project mailbox messages` reuses the structural mailbox inspection contract

The native `houmao-mgr project mailbox messages list` and `houmao-mgr project mailbox messages get` commands SHALL expose the same structural-only message inspection contract as `houmao-mgr mailbox messages list|get`, but fixed to the current project's `.houmao/mailbox` root.

Those project-scoped wrappers SHALL NOT add or reintroduce participant-local mutable mailbox view-state fields removed from the root-level mailbox command family.

#### Scenario: Project mailbox message list matches the structural inspection contract

- **WHEN** an operator runs `houmao-mgr project mailbox messages list --address alice@agents.localhost`
- **THEN** the command returns structural message summaries for the selected project-local address projection
- **AND THEN** the payload shape matches the root-level structural mailbox message summary contract
- **AND THEN** the payload does not include `read`, `starred`, `archived`, or `deleted`

#### Scenario: Project mailbox message get matches the structural inspection contract

- **WHEN** an operator runs `houmao-mgr project mailbox messages get --address alice@agents.localhost --message-id msg-123`
- **THEN** the command returns canonical message details together with the selected project-local address projection metadata
- **AND THEN** the payload shape matches the root-level structural mailbox message detail contract
- **AND THEN** the payload does not claim a single authoritative participant-local read, starred, archived, or deleted state
