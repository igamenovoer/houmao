## MODIFIED Requirements

### Requirement: `houmao-mgr system-skills list` reports the current installable Houmao-owned skill inventory and named sets
`houmao-mgr system-skills list` SHALL report the current installable Houmao-owned skill inventory and the current named skill sets from the packaged catalog.

The reported current named skill sets SHALL be `core` and `all`.

That output SHALL identify the configured CLI default set list and the fixed internal auto-install set lists.

#### Scenario: List reports core and all with default set markers
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports the current installable Houmao-owned skill names
- **AND THEN** it reports `core` and `all` as the current named skill sets
- **AND THEN** it identifies `managed_launch_sets = ["core"]`, `managed_join_sets = ["core"]`, and `cli_default_sets = ["all"]`

### Requirement: `houmao-mgr system-skills install` targets an explicit tool home and set-based selection
`houmao-mgr system-skills install` SHALL require a supported tool identifier or a comma-separated list of supported tool identifiers through `--tool`.

The command SHALL support these selection inputs:

- repeatable `--skill-set <name>` for current named system-skill set selection,
- repeatable `--skill <name>` for explicit current-skill selection.

The current named system-skill sets accepted by `--skill-set` SHALL be `core` and `all`.

When neither `--skill-set` nor `--skill` is provided, the command SHALL use the CLI default set list from the packaged catalog, which resolves `all` in this change.

The command SHALL NOT expose `--set` or `--default` as part of the supported public install surface.

For multi-tool installs, the command SHALL apply the same selected sets, explicit skills, and resolved projection mode to every selected tool.

#### Scenario: Omitted-selection install uses all
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home`
- **AND WHEN** no `--skill-set` or `--skill` is supplied
- **THEN** the command installs the current Houmao-owned skill list resolved from `cli_default_sets = ["all"]`
- **AND THEN** the resolved list includes current utility skills

#### Scenario: Explicit core install is accepted
- **WHEN** an operator runs `houmao-mgr system-skills install --tool gemini --home /tmp/gemini-home --skill-set core`
- **THEN** the command installs the current Houmao-owned skill list resolved from `core`
- **AND THEN** the resolved list excludes utility skills that are only in `all`

#### Scenario: Removed granular set names are rejected
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --skill-set user-control`
- **THEN** the command fails explicitly before installing any selected skill
- **AND THEN** the error treats `user-control` as an unknown set rather than mapping it to `core`

## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces utility skills through all
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and fixed set lists when reporting, installing, and inspecting Houmao-owned utility skills.

That current inventory SHALL surface `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr` as installable packaged skills.

The reported named sets SHALL include `all` as the set that contains the utility skills and SHALL NOT report `utils` as a current installable set.

When `system-skills install` resolves the packaged CLI-default set list, the resolved installed skill names and later `system-skills status` output SHALL include `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr`.

#### Scenario: List reports utility skills and all
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr` in the current Houmao-owned skill inventory
- **AND THEN** it reports `all` as the named set that includes those utility skills
- **AND THEN** it does not report `utils` as a current named set

#### Scenario: Omitted-selection install and status report utility skills
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home`
- **AND WHEN** no `--skill-set` or `--skill` is supplied
- **THEN** the install result reports `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports those utility skills as installed when the CLI-default install completed successfully
