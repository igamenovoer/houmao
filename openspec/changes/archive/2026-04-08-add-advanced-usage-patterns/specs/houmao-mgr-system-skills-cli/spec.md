## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the packaged advanced-usage skill
`houmao-mgr system-skills` SHALL use the packaged current-system-skill inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-adv-usage-pattern` as an installable packaged skill.

The reported named sets SHALL include the dedicated advanced-usage set for that skill.

When `system-skills install` resolves the packaged managed-home or CLI-default selection that includes the advanced-usage set, the reported installed skill names and later `system-skills status` output SHALL include `houmao-adv-usage-pattern` whenever that install completed successfully.

#### Scenario: List reports the advanced-usage skill and set
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-adv-usage-pattern` in the current Houmao-owned skill inventory
- **AND THEN** it reports the dedicated advanced-usage named set in the current packaged set inventory

#### Scenario: Default install and status report the advanced-usage skill
- **WHEN** an operator installs a packaged default system-skill selection into a target tool home
- **THEN** the install result reports `houmao-adv-usage-pattern` in the resolved current skill list when the default set list includes the advanced-usage set
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-adv-usage-pattern` as installed when that selection completed successfully

