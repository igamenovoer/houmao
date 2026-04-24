## ADDED Requirements

### Requirement: Shared-registry cleanup mutates only lexical registry entries
Shared-registry record removal and stale-record cleanup SHALL treat `live_agents/<agent_id>/` entries as lexical registry-owned artifacts.

Registry cleanup SHALL NOT follow a symlinked record directory to choose the recursive deletion target.

#### Scenario: Removing a symlink-backed registry entry preserves the external target
- **WHEN** one shared-registry `live_agents/<agent_id>` entry exists as a symlink to a directory outside the registry root
- **AND WHEN** Houmao removes or cleans up that registry entry
- **THEN** Houmao removes only the lexical registry entry under `live_agents/`
- **AND THEN** it does not delete or rewrite the symlink target directory

#### Scenario: Malformed registry state does not widen cleanup authority
- **WHEN** shared-registry cleanup encounters one malformed or stale live-agent entry
- **THEN** cleanup stays confined to registry-owned lexical paths
- **AND THEN** malformed metadata does not authorize deletion outside the registry root
