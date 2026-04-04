## MODIFIED Requirements

### Requirement: `houmao-mgr mailbox` exposes local filesystem mailbox administration commands
`houmao-mgr` SHALL expose a top-level `mailbox` command family for local filesystem mailbox administration that does not require `houmao-server`.

At minimum, that family SHALL include:

- `init`
- `status`
- `register`
- `unregister`
- `repair`
- `cleanup`
- `accounts`
- `messages`

The family SHALL target the filesystem mailbox transport only in v1.

#### Scenario: Operator sees the local mailbox administration commands
- **WHEN** an operator runs `houmao-mgr mailbox --help`
- **THEN** the help output lists `init`, `status`, `register`, `unregister`, `repair`, `cleanup`, `accounts`, and `messages`
- **AND THEN** the command family is presented as a local mailbox administration surface rather than a server-backed API surface

## ADDED Requirements

### Requirement: `houmao-mgr mailbox accounts` inspects mailbox registrations as operator-facing accounts
`houmao-mgr mailbox accounts` SHALL expose inspection commands over mailbox registrations under one resolved mailbox root.

At minimum, `accounts` SHALL expose:

- `list`
- `get`

`accounts list` SHALL enumerate registered mailbox addresses together with their registration state.

`accounts get --address <full-address>` SHALL report one mailbox registration, including the selected address, owner principal id when available, registration state, and mailbox path metadata.

#### Scenario: Accounts list reports registered mailbox addresses
- **WHEN** an operator runs `houmao-mgr mailbox accounts list --mailbox-root /tmp/shared-mail`
- **AND WHEN** that root contains active and inactive registrations
- **THEN** the command returns those registered mailbox addresses with their lifecycle state
- **AND THEN** the operator does not need to inspect mailbox root files manually to discover registered addresses

#### Scenario: Accounts get reports one selected mailbox registration
- **WHEN** `/tmp/shared-mail` contains an active registration for `AGENTSYS-alice@agents.localhost`
- **AND WHEN** an operator runs `houmao-mgr mailbox accounts get --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost`
- **THEN** the command reports the selected address and its registration metadata
- **AND THEN** the result identifies the mailbox path for that registration

### Requirement: `houmao-mgr mailbox messages` lists and gets mailbox content for one registered address
`houmao-mgr mailbox messages` SHALL expose direct read-only mailbox content inspection for one selected registered mailbox address under one resolved mailbox root.

At minimum, `messages` SHALL expose:

- `list`
- `get`

`messages list --address <full-address>` SHALL return message summaries for the selected mailbox address.

`messages get --address <full-address> --message-id <message-id>` SHALL return the content and metadata for one selected message visible to that mailbox address.

The summary payload for `messages list` SHALL include enough metadata to select one message for `messages get`, including `message_id`.

#### Scenario: Messages list returns mailbox-visible summaries for one address
- **WHEN** `/tmp/shared-mail` contains an active mailbox registration for `AGENTSYS-alice@agents.localhost`
- **AND WHEN** mailbox-visible messages exist for that address
- **AND WHEN** an operator runs `houmao-mgr mailbox messages list --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost`
- **THEN** the command returns message summaries for that selected address
- **AND THEN** each summary includes a `message_id` suitable for later message retrieval

#### Scenario: Messages get returns the selected message content
- **WHEN** `/tmp/shared-mail` contains mailbox-visible message `msg-123` for `AGENTSYS-alice@agents.localhost`
- **AND WHEN** an operator runs `houmao-mgr mailbox messages get --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost --message-id msg-123`
- **THEN** the command returns the content and metadata for `msg-123`
- **AND THEN** the operator does not need to inspect the canonical mailbox document directly on disk
