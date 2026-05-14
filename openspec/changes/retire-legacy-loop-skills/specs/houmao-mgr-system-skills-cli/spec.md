## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces pro as the current loop skill
`houmao-mgr system-skills list`, `install`, and `status` SHALL surface `houmao-agent-loop-pro` as the current packaged Houmao-owned loop skill.

Those commands SHALL NOT surface retired pairwise or generic loop skill names as current installable skills.

#### Scenario: List reports pro and omits retired loop packages
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the current skill inventory includes `houmao-agent-loop-pro`
- **AND THEN** the current skill inventory omits retired pairwise and generic loop package names

### Requirement: `houmao-mgr system-skills status` reports retired loop leftovers
`houmao-mgr system-skills status` SHALL detect known retired loop skill projections in the resolved target home and report them separately from current installed skills.

The JSON status output SHALL identify retired loop leftovers by skill name and projection path.

#### Scenario: Status reports stale retired loop skill
- **WHEN** one target tool home contains a stale `skills/houmao-agent-loop-pairwise-v2/`
- **AND WHEN** an operator runs `houmao-mgr system-skills status` for that home
- **THEN** the status output reports `houmao-agent-loop-pairwise-v2` as a retired leftover
- **AND THEN** it does not report that skill as a current installed skill

### Requirement: `houmao-mgr system-skills install` reports retired cleanup
When installation removes known retired loop skill projections, `houmao-mgr system-skills install` SHALL include those removals in structured command output.

#### Scenario: Install output includes retired removals
- **WHEN** installing current system skills removes stale retired loop projections
- **THEN** the command output lists the removed retired skill paths
- **AND THEN** the command output lists `houmao-agent-loop-pro` as installed when selected
