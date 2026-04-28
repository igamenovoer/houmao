## ADDED Requirements

### Requirement: Managed-session cleanup can purge broken active local authority
`houmao-mgr agents cleanup session` SHALL continue treating stopped-session cleanup as the default contract.

However, when the operator explicitly passes `--purge-registry`, the command SHALL allow cleanup of a resolved local managed-agent record that still claims lifecycle state `active` when local tmux-authority inspection proves that the selected session no longer has a usable contractual primary surface.

For this explicit purge path:

- a usable local primary surface requires the contractual primary window `0` and pane `0`
- a leftover tmux session remnant without that primary surface SHALL NOT be treated as healthy live session authority
- if such a tmux session remnant still exists, cleanup SHALL terminate it before removing the session root
- cleanup SHALL then remove the session root and purge or retire the registry record according to the selected cleanup mode

Without `--purge-registry`, cleanup SHALL remain conservative and MAY still block when lifecycle state remains `active`.

#### Scenario: Purge cleanup removes a gateway-only tmux remnant for an active degraded record
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-id agent-123 --purge-registry`
- **AND WHEN** the selected registry record still claims lifecycle state `active`
- **AND WHEN** local tmux inspection shows that the tmux session still exists but the contractual primary surface is missing
- **THEN** cleanup treats that target as broken local authority rather than as healthy live session authority
- **AND THEN** cleanup terminates the leftover tmux session remnant before removing the session root
- **AND THEN** the registry record is purged or retired according to the requested cleanup mode

#### Scenario: Purge cleanup removes session artifacts for a stale active record with no tmux session
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-name reviewer --purge-registry`
- **AND WHEN** the selected registry record still claims lifecycle state `active`
- **AND WHEN** local tmux inspection shows that the recorded tmux session no longer exists
- **THEN** cleanup treats that target as broken local authority eligible for explicit purge cleanup
- **AND THEN** cleanup removes the session root without requiring a prior successful `agents stop`
- **AND THEN** the registry record is purged or retired according to the requested cleanup mode
