## ADDED Requirements

### Requirement: Packaged catalog exposes pro as the only current loop skill
The packaged current-system-skill catalog SHALL include `houmao-agent-loop-pro` as the only current Houmao-owned loop authoring and generated-loop execution skill.

The packaged current-system-skill catalog SHALL NOT include `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-pairwise-v3`, `houmao-agent-loop-pairwise-v4`, `houmao-agent-loop-pairwise-v5`, or `houmao-agent-loop-generic` as current installable skills.

The `core` and `all` install sets SHALL include `houmao-agent-loop-pro` and SHALL NOT include retired loop skill names.

#### Scenario: Catalog lists only pro for loop authoring
- **WHEN** the packaged system-skill catalog is loaded
- **THEN** the current skill inventory includes `houmao-agent-loop-pro`
- **AND THEN** the current skill inventory does not include any retired pairwise or generic loop skill package

#### Scenario: Auto-install sets include pro
- **WHEN** managed launch, managed join, or CLI-default install selection resolves packaged skill sets
- **THEN** the resolved current skill list includes `houmao-agent-loop-pro`
- **AND THEN** it does not include retired loop skill names

### Requirement: Shared installer cleans known retired loop skill projections
The shared system-skill installer SHALL treat the retired loop skill names as known Houmao-owned retired projections:

- `houmao-agent-loop-pairwise`
- `houmao-agent-loop-pairwise-v2`
- `houmao-agent-loop-pairwise-v3`
- `houmao-agent-loop-pairwise-v4`
- `houmao-agent-loop-pairwise-v5`
- `houmao-agent-loop-generic`

For a selected target tool home, install and reinstall workflows SHALL remove exact projection paths for known retired loop skills while installing selected current skills.

The cleanup SHALL be limited to the exact tool-native projection paths for known retired Houmao-owned skill names.

#### Scenario: Reinstall removes stale retired loop skills
- **WHEN** one target tool home contains `skills/houmao-agent-loop-pairwise-v3/`
- **AND WHEN** the operator installs the current default Houmao system-skill set into that home
- **THEN** the installer removes the retired `houmao-agent-loop-pairwise-v3` projection
- **AND THEN** the installer creates or refreshes `houmao-agent-loop-pro`

#### Scenario: Cleanup does not remove unrelated user skills
- **WHEN** one target tool home contains an unrelated user skill
- **AND WHEN** current Houmao system skills are installed
- **THEN** the installer does not remove the unrelated user skill

### Requirement: Shared removal includes known retired loop projections
The shared system-skill uninstall workflow SHALL remove current catalog-known Houmao skill projections and known retired loop skill projections from the selected target tool home.

#### Scenario: Uninstall removes current and retired Houmao loop paths
- **WHEN** one target tool home contains `houmao-agent-loop-pro` and a stale `houmao-agent-loop-pairwise-v5`
- **AND WHEN** the operator uninstalls Houmao system skills for that home
- **THEN** both exact Houmao-owned loop projection paths are removed

### Requirement: Retired loop skill sources are preserved only as source legacy references
The repository SHALL preserve retired loop skill source trees under a source-only legacy reference directory below `src/`.

The packaged system-skill catalog, named install sets, auto-install selections, project-scope skill symlinks, and generated managed homes SHALL NOT reference retired loop skill source trees from that legacy directory.

The supported system-skill installer SHALL NOT install retired loop skills from the legacy directory.

#### Scenario: Retired source exists but is not packaged
- **WHEN** the repository contains a retired loop skill under the source-only legacy directory
- **THEN** the packaged current system-skill catalog does not include that retired skill name
- **AND THEN** install-set resolution does not project that legacy skill into target tool homes

#### Scenario: User manually handles legacy source
- **WHEN** a user intentionally copies or symlinks retired legacy skill source outside the supported Houmao installer path
- **THEN** that manual usage is outside current system-skill catalog support
- **AND THEN** current Houmao docs and routing guidance still identify `houmao-agent-loop-pro` as the maintained loop skill
