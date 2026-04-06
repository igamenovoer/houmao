## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the renamed specialist-management skill in current inventory
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory when reporting, installing, and inspecting Houmao-owned skills.

For the project-easy skill set, that current inventory SHALL surface `houmao-manage-specialist` rather than `houmao-create-specialist`.

When `system-skills install` resolves the default or project-easy selection, the reported installed skill names and subsequent `system-skills status` output SHALL use `houmao-manage-specialist` as the current specialist-management skill name.

#### Scenario: List reports the renamed specialist-management skill
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-manage-specialist` in the current Houmao-owned skill inventory
- **AND THEN** the `project-easy` set resolves the renamed skill instead of `houmao-create-specialist`

#### Scenario: Default install and status report the renamed skill
- **WHEN** an operator installs the CLI default system-skill selection into a target tool home
- **THEN** the install result reports `houmao-manage-specialist` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-manage-specialist` as the installed specialist-management skill
