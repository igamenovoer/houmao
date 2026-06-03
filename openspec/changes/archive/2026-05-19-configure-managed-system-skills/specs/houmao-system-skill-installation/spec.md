## ADDED Requirements

### Requirement: Managed launch system-skill installation accepts resolved source policy
The managed-home system-skill installer SHALL support a resolved managed-launch selection policy derived from stored specialist, recipe, and launch-profile configuration.

When no stored policy is supplied, managed launch installation SHALL preserve the existing default behavior by resolving the packaged catalog's `auto_install.managed_launch_sets`.

The policy SHALL support additive, exact replacement, and disabled installation modes while continuing to validate all named set and explicit skill selectors against the packaged current system-skill catalog.

For reused managed homes, applying an exact replacement or disabled selection SHALL remove exact catalog-known current Houmao-owned system-skill projection paths that are not in the resolved selection, and SHALL preserve unrelated user skill paths.

#### Scenario: Omitted managed policy preserves core default
- **WHEN** Houmao constructs a managed home without a stored system-skill policy
- **THEN** it installs the skill list resolved from the packaged catalog's `managed_launch_sets`
- **AND THEN** existing managed-launch defaults remain unchanged

#### Scenario: Additive managed policy installs one utility skill
- **WHEN** managed launch resolves an additive system-skill policy containing explicit skill `houmao-utils-llm-wiki`
- **THEN** the installer resolves the packaged managed-launch default selection
- **AND THEN** it appends `houmao-utils-llm-wiki` to the installed skill list without duplicating any skill name

#### Scenario: Replacement managed policy installs exact all set
- **WHEN** managed launch resolves an exact replacement system-skill policy containing set `all`
- **THEN** the installer installs the skills resolved from `all`
- **AND THEN** it does not implicitly add the packaged `managed_launch_sets` selection a second time

#### Scenario: Disabled managed policy removes stale Houmao-owned system skills
- **WHEN** a reused Codex managed home contains `skills/houmao-utils-llm-wiki/` from an earlier launch
- **AND WHEN** managed launch resolves disabled system-skill installation for that home
- **THEN** the managed-home sync removes exact current Houmao-owned system-skill paths from the home
- **AND THEN** it preserves unrelated non-Houmao skill paths under the tool skill root

#### Scenario: Unknown managed policy selector fails before mutation
- **WHEN** managed launch resolves a system-skill policy containing unknown set `utilities`
- **THEN** validation fails before mutating the managed home
- **AND THEN** the error identifies the unknown system-skill set selector
