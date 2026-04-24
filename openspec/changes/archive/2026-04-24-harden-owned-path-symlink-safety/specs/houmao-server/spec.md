## ADDED Requirements

### Requirement: `houmao-server` headless authority cleanup stays within the server-owned state tree
When `houmao-server` deletes or refreshes native headless authority artifacts under its managed-agent state tree, the server SHALL mutate only lexical artifact paths under the server-owned managed-agent root.

The server SHALL NOT follow a symlinked managed-agent artifact path in order to choose the recursive deletion target.

#### Scenario: Removing a symlink-backed managed-agent root preserves the target
- **WHEN** one server-owned managed-agent artifact path under `state/managed_agents/<tracked_agent_id>/` currently exists as a symlink to a directory outside the server-owned state tree
- **AND WHEN** `houmao-server` deletes that managed-agent authority artifact during cleanup or recovery
- **THEN** the server removes only the lexical artifact path under the managed-agent state tree
- **AND THEN** it does not recursively delete the symlink target directory

#### Scenario: Invalid headless authority key does not escape the managed-agent root
- **WHEN** `houmao-server` is asked to delete or clear one headless authority artifact selected by tracked-agent identity
- **THEN** the resulting mutation target remains contained to the server-owned managed-agent root
- **AND THEN** the server does not mutate paths outside that root
