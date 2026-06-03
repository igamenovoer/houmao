## ADDED Requirements

### Requirement: Removed LLM Wiki system skill is outside Houmao-owned inventory
The packaged system-skill catalog SHALL NOT include `houmao-utils-llm-wiki` as a current skill, set member, auto-install selection member, or retired Houmao-owned skill name.

System-skill install, sync, status, and uninstall workflows SHALL NOT treat `skills/houmao-utils-llm-wiki/` or equivalent tool-native projection paths as current or retired Houmao-owned projections.

#### Scenario: Catalog omits the removed LLM Wiki skill
- **WHEN** the packaged system-skill catalog is loaded
- **THEN** `houmao-utils-llm-wiki` is absent from the current skill inventory
- **AND THEN** `houmao-utils-llm-wiki` is absent from every named set and auto-install selection
- **AND THEN** `houmao-utils-llm-wiki` is absent from `retired_skill_names`

#### Scenario: Stale LLM Wiki projection is outside automatic cleanup
- **WHEN** a target tool home contains `skills/houmao-utils-llm-wiki/`
- **AND WHEN** Houmao installs, syncs, inspects, or uninstalls Houmao-owned system skills for that home
- **THEN** the stale LLM Wiki path is not reported as a current or retired Houmao-owned skill
- **AND THEN** the stale LLM Wiki path is not removed by Houmao-owned system-skill cleanup

## MODIFIED Requirements

### Requirement: Packaged utility skills are available through all
The packaged current-system-skill catalog SHALL include `houmao-utils-workspace-mgr` as a current installable utility skill.

The `all` set SHALL include the current utility skill.

The `core` set SHALL exclude utility skills unless a future change explicitly promotes a utility into the managed core surface.

The packaged catalog's fixed `cli_default_sets` selection SHALL include `all`, so omitted-selection explicit CLI installs include the current utility skill by default.

The packaged catalog's fixed `managed_launch_sets` and `managed_join_sets` selections SHALL include `core`, so managed launch and join do not install utility skills by default.

#### Scenario: CLI default includes current utility skills
- **WHEN** an operator installs system skills into an external tool home without selecting `--skill-set` or `--skill`
- **THEN** the installer resolves `cli_default_sets = ["all"]`
- **AND THEN** the resolved skill list includes `houmao-utils-workspace-mgr`
- **AND THEN** the resolved skill list does not include `houmao-utils-llm-wiki`

#### Scenario: Managed auto-install excludes utility skills
- **WHEN** Houmao installs system skills into a managed launch or join home
- **THEN** the installer resolves `core`
- **AND THEN** the resolved skill list excludes `houmao-utils-workspace-mgr`
- **AND THEN** the resolved skill list excludes `houmao-utils-llm-wiki`

### Requirement: Managed launch system-skill installation accepts resolved source policy
The managed-home system-skill installer SHALL support a resolved managed-launch selection policy derived from stored specialist, recipe, and launch-profile configuration.

When no stored policy is supplied, managed launch installation SHALL preserve the existing default behavior by resolving the packaged catalog's `auto_install.managed_launch_sets`.

The policy SHALL support additive, exact replacement, and disabled installation modes while continuing to validate all named set and explicit skill selectors against the packaged current system-skill catalog.

For reused managed homes, applying an exact replacement or disabled selection SHALL remove exact catalog-known current Houmao-owned system-skill projection paths that are not in the resolved selection, and SHALL preserve unrelated user skill paths.

#### Scenario: Omitted managed policy preserves core default
- **WHEN** Houmao constructs a managed home without a stored system-skill policy
- **THEN** it installs the skill list resolved from the packaged catalog's `managed_launch_sets`
- **AND THEN** existing managed-launch defaults remain unchanged

#### Scenario: Additive managed policy installs one current utility skill
- **WHEN** managed launch resolves an additive system-skill policy containing explicit skill `houmao-utils-workspace-mgr`
- **THEN** the installer resolves the packaged managed-launch default selection
- **AND THEN** it appends `houmao-utils-workspace-mgr` to the installed skill list without duplicating any skill name

#### Scenario: Replacement managed policy installs exact all set
- **WHEN** managed launch resolves an exact replacement system-skill policy containing set `all`
- **THEN** the installer installs the skills resolved from `all`
- **AND THEN** it does not implicitly add the packaged `managed_launch_sets` selection a second time

#### Scenario: Disabled managed policy removes stale current Houmao-owned system skills
- **WHEN** a reused Codex managed home contains `skills/houmao-agent-definition/` from an earlier launch
- **AND WHEN** managed launch resolves disabled system-skill installation for that home
- **THEN** the managed-home sync removes exact current Houmao-owned system-skill paths from the home
- **AND THEN** it preserves unrelated non-Houmao skill paths under the tool skill root

#### Scenario: Unknown managed policy selector fails before mutation
- **WHEN** managed launch resolves a system-skill policy containing unknown set `utilities`
- **THEN** validation fails before mutating the managed home
- **AND THEN** the error identifies the unknown system-skill set selector

#### Scenario: Removed LLM Wiki policy selector fails before mutation
- **WHEN** managed launch resolves a system-skill policy containing explicit skill `houmao-utils-llm-wiki`
- **THEN** validation fails before mutating the managed home
- **AND THEN** the error identifies `houmao-utils-llm-wiki` as an unknown system skill

## REMOVED Requirements

### Requirement: LLM Wiki utility skill ships the all-in-one payload
**Reason**: `houmao-utils-llm-wiki` is removed completely from Houmao's packaged system-skill surface.

**Migration**: Remove the packaged asset tree and stop installing or documenting the skill through Houmao system-skill workflows. Operators clean any external copies or symlinks manually.
