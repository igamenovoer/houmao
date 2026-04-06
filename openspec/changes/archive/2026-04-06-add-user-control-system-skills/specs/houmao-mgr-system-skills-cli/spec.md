## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the user-control named set and credential-management skill
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-manage-credentials` as an installable packaged skill.

The reported named sets SHALL include `user-control` as the packaged non-mailbox user-controlled-agent skill set.

When `system-skills install` resolves a selection that includes `user-control`, the reported installed skill names and later `system-skills status` output SHALL include `houmao-manage-credentials` whenever that install completed successfully.

#### Scenario: List reports the user-control set and credential-management skill
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-manage-credentials` in the current Houmao-owned skill inventory
- **AND THEN** it reports `user-control` as the named set that groups the packaged user-controlled-agent skills

#### Scenario: User-control install and status report the credential-management skill
- **WHEN** an operator installs a system-skill selection that includes `user-control` into a target tool home
- **THEN** the install result reports `houmao-manage-credentials` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-manage-credentials` as installed when that selection completed successfully

## MODIFIED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the renamed specialist-management skill in current inventory
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory when reporting, installing, and inspecting Houmao-owned skills.

For the user-control skill set, that current inventory SHALL surface `houmao-manage-specialist` rather than `houmao-create-specialist`.

When `system-skills install` resolves the default or `user-control` selection, the reported installed skill names and subsequent `system-skills status` output SHALL use `houmao-manage-specialist` as the current specialist-management skill name.

#### Scenario: List reports the renamed specialist-management skill
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-manage-specialist` in the current Houmao-owned skill inventory
- **AND THEN** the `user-control` set resolves the renamed skill instead of `houmao-create-specialist`

#### Scenario: Default install and status report the renamed skill
- **WHEN** an operator installs the default system-skill selection into a target tool home
- **THEN** the install result reports `houmao-manage-specialist` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-manage-specialist` as the installed specialist-management skill

### Requirement: `houmao-mgr system-skills` surfaces the packaged agent-instance lifecycle skill and updated CLI-default selection
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and fixed set lists when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-manage-agent-instance` as an installable packaged skill.

The reported named sets SHALL include the dedicated agent-instance lifecycle set for that skill.

When `system-skills install --default` resolves the packaged CLI-default set list, the resolved installed skill names and later `system-skills status` output SHALL include:

- `houmao-manage-specialist`
- `houmao-manage-credentials`
- `houmao-manage-agent-instance`

#### Scenario: List reports the packaged agent-instance lifecycle skill and set
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-manage-agent-instance` in the current Houmao-owned skill inventory
- **AND THEN** it reports the dedicated named set that resolves that lifecycle skill

#### Scenario: Default install reports the packaged non-mailbox Houmao skills
- **WHEN** an operator installs the CLI-default system-skill selection into a target tool home
- **THEN** the install result reports `houmao-manage-specialist`, `houmao-manage-credentials`, and `houmao-manage-agent-instance` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports those skills as installed when the CLI-default install completed successfully
