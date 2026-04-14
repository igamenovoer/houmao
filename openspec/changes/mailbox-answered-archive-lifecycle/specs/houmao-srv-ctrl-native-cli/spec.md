## ADDED Requirements

### Requirement: `houmao-mgr agents mail` exposes mailbox lifecycle commands
`houmao-mgr agents mail` SHALL expose a mailbox lifecycle command family for managed-agent mailbox work.

At minimum, that family SHALL include:

- `resolve-live`,
- `status`,
- `list`,
- `peek`,
- `read`,
- `send`,
- `post`,
- `reply`,
- `mark`,
- `move`,
- `archive`.

`list` SHALL support selecting a mailbox box and SHALL default to the inbox when omitted.

`peek` SHALL retrieve one message without marking it read.

`read` SHALL retrieve one message and mark it read.

`reply` SHALL mark the replied message answered after a successful reply.

`mark` SHALL allow explicit manual marking of supported lifecycle fields such as `read` and `answered`.

`move` SHALL move selected messages among supported mailbox boxes.

`archive` SHALL archive selected messages and remain a shortcut for the common processed-mail completion operation.

The CLI SHALL keep the existing authority-aware result contract for verified execution versus non-authoritative fallback submission.

#### Scenario: Operator archives selected mail from the CLI
- **WHEN** an operator runs `houmao-mgr agents mail archive` with one or more message refs
- **THEN** the command resolves the target mailbox binding through the supported managed-agent selector contract
- **AND THEN** it archives the selected messages through the live gateway or manager-owned fallback surface

#### Scenario: CLI peek does not mark a message read
- **WHEN** an operator runs `houmao-mgr agents mail peek --message-ref <ref>`
- **THEN** the command returns the selected message content
- **AND THEN** the selected message is not marked read merely because of that peek operation

#### Scenario: CLI read marks a message read
- **WHEN** an operator runs `houmao-mgr agents mail read --message-ref <ref>`
- **THEN** the command returns the selected message content
- **AND THEN** the selected message is marked read for the target mailbox principal
