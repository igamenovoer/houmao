## MODIFIED Requirements

### Requirement: `houmao-mgr system-skills list` reports the current installable Houmao-owned skill inventory and named sets
`houmao-mgr system-skills list` SHALL report the current installable Houmao-owned skill inventory and the current named skill sets from the packaged catalog.

The reported current named skill sets SHALL be `core`, `extensions`, and `all`.

That output SHALL identify the configured CLI default set list and the fixed internal auto-install set lists.

#### Scenario: List reports core, extensions, and all with default set markers
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports the current installable Houmao-owned skill names
- **AND THEN** it reports `core`, `extensions`, and `all` as the current named skill sets
- **AND THEN** it identifies `managed_launch_sets = ["core", "extensions"]`, `managed_join_sets = ["core", "extensions"]`, and `cli_default_sets = ["all"]`

### Requirement: `houmao-mgr system-skills install` targets an explicit tool home and set-based selection
`houmao-mgr system-skills install` SHALL require a supported tool identifier or a comma-separated list of supported tool identifiers through `--tool`.

The command SHALL support these selection inputs:

- repeatable `--skill-set <name>` for current named system-skill set selection,
- repeatable `--skill <name>` for explicit current-skill selection.

The current named system-skill sets accepted by `--skill-set` SHALL be `core`, `extensions`, and `all`.

When neither `--skill-set` nor `--skill` is provided, the command SHALL use the CLI default set list from the packaged catalog, which resolves `all` in this change.

The command SHALL NOT expose `--set` or `--default` as part of the supported public install surface.

For multi-tool installs, the command SHALL apply the same selected sets, explicit skills, and resolved projection mode to every selected tool.

#### Scenario: Omitted-selection install uses all
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home`
- **AND WHEN** no `--skill-set` or `--skill` is supplied
- **THEN** the command installs the current Houmao-owned skill list resolved from `cli_default_sets = ["all"]`
- **AND THEN** the resolved list includes current extension skills

#### Scenario: Explicit core install is accepted
- **WHEN** an operator runs `houmao-mgr system-skills install --tool gemini --home /tmp/gemini-home --skill-set core`
- **THEN** the command installs the current Houmao-owned skill list resolved from `core`
- **AND THEN** the resolved list excludes extension skills that are only in `extensions` or `all`

#### Scenario: Explicit extensions install is accepted
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home --skill-set extensions`
- **THEN** the command installs the current Houmao-owned skill list resolved from `extensions`
- **AND THEN** the resolved list includes `houmao-ext-graphing`

#### Scenario: Removed granular set names are rejected
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --skill-set user-control`
- **THEN** the command fails explicitly before installing any selected skill
- **AND THEN** the error treats `user-control` as an unknown set rather than mapping it to `core`

## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the graphing extension skill
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-ext-graphing` as the installable graphing extension skill.

The command output SHALL NOT report `houmao-utils-graphing` as a current installable skill after the rename.

When `system-skills install` resolves a selection that includes the graphing extension, the reported installed skill names and later `system-skills status` output SHALL use `houmao-ext-graphing`.

If a target tool home contains a stale retired `houmao-utils-graphing` projection, install output SHALL report that retired projection removal through the existing retired-skill reporting fields.

#### Scenario: List reports the graphing extension skill
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-ext-graphing` in the current Houmao-owned skill inventory
- **AND THEN** it does not report `houmao-utils-graphing` as a current installable skill
- **AND THEN** it reports `houmao-utils-graphing` only as a retired skill name when retired names are included in the output

#### Scenario: Install and status report the graphing extension
- **WHEN** an operator installs a selection that includes the graphing extension into a target Codex home
- **THEN** the install result reports `houmao-ext-graphing` in the resolved current skill list
- **AND THEN** the target home contains `skills/houmao-ext-graphing/SKILL.md`
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-ext-graphing` as installed

#### Scenario: Install reports stale graphing utility removal
- **WHEN** an operator installs current system skills into a tool home that already contains `houmao-utils-graphing`
- **THEN** the install result reports `houmao-utils-graphing` as a removed retired skill
- **AND THEN** the target home no longer contains the old `houmao-utils-graphing` projection
