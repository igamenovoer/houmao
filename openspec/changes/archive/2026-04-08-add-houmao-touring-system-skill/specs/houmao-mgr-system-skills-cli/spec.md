## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the packaged `houmao-touring` skill and touring set
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-touring` as an installable packaged skill.

The reported named sets SHALL include the dedicated `touring` set.

When `system-skills install` resolves the packaged default set list for any supported tool home, the resolved installed skill names and later `system-skills status` output SHALL include `houmao-touring`.

Omitting both `--set` and `--skill` SHALL remain a supported path that resolves the packaged default set list including the touring set.

#### Scenario: List reports the touring skill and named set
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-touring` in the current Houmao-owned skill inventory
- **AND THEN** it reports the dedicated `touring` named set among the packaged named sets

#### Scenario: Default install and status report the touring skill
- **WHEN** an operator installs the packaged default system-skill selection into a target tool home
- **THEN** the install result reports `houmao-touring` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-touring` as installed when that selection completed successfully

#### Scenario: Explicit touring-set install resolves the guided-tour skill
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home --set touring`
- **THEN** the command resolves `houmao-touring` from the dedicated `touring` named set
- **AND THEN** it installs that packaged skill into the target tool home through the shared system-skill installer
