## ADDED Requirements

### Requirement: Packaged catalog exposes pro and lite as current loop skills
The packaged current-system-skill catalog SHALL include both `houmao-agent-loop-pro` and `houmao-agent-loop-lite` as current Houmao-owned loop skills.

The packaged current-system-skill catalog SHALL continue to exclude retired loop skill package names such as `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-pairwise-v3`, `houmao-agent-loop-pairwise-v4`, `houmao-agent-loop-pairwise-v5`, and `houmao-agent-loop-generic`.

The `core` and `all` install sets SHALL include both `houmao-agent-loop-pro` and `houmao-agent-loop-lite`.

#### Scenario: Catalog lists both maintained loop skills
- **WHEN** the packaged system-skill catalog is loaded
- **THEN** the current skill inventory includes `houmao-agent-loop-pro`
- **AND THEN** the current skill inventory includes `houmao-agent-loop-lite`
- **AND THEN** the current skill inventory does not include retired pairwise or generic loop package names

#### Scenario: Auto-install sets include both loop skills
- **WHEN** managed launch, managed join, or CLI-default install selection resolves packaged skill sets
- **THEN** the resolved current skill list includes `houmao-agent-loop-pro`
- **AND THEN** the resolved current skill list includes `houmao-agent-loop-lite`

### Requirement: Shared installer projects the lite skill as a normal current system skill
The shared system-skill installer SHALL project `houmao-agent-loop-lite` into target tool homes using the same current-skill projection rules as other catalog-known Houmao system skills.

The status and uninstall workflows SHALL treat `houmao-agent-loop-lite` as a current catalog-known skill.

Retired loop cleanup behavior SHALL remain limited to the known retired loop names and SHALL NOT treat `houmao-agent-loop-lite` as retired.

#### Scenario: Install projects lite into a Codex home
- **WHEN** an operator installs the current `core` set into a Codex home
- **THEN** the installer projects `skills/houmao-agent-loop-lite/`
- **AND THEN** status reports `houmao-agent-loop-lite` as a current installed skill

#### Scenario: Uninstall removes lite as current
- **WHEN** a resolved target home contains `houmao-agent-loop-lite`
- **AND WHEN** the operator uninstalls Houmao system skills for that home
- **THEN** the uninstall workflow removes the `houmao-agent-loop-lite` projection
