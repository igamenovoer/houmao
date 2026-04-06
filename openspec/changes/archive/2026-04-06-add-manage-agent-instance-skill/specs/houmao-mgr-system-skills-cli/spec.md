## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the packaged agent-instance lifecycle skill and updated CLI-default selection
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and fixed set lists when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-manage-agent-instance` as an installable packaged skill.

The reported named sets SHALL include the dedicated agent-instance lifecycle set for that skill.

When `system-skills install --default` resolves the packaged CLI-default set list, the resolved installed skill names and later `system-skills status` output SHALL include both:

- `houmao-manage-specialist`
- `houmao-manage-agent-instance`

#### Scenario: List reports the packaged agent-instance lifecycle skill and set
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-manage-agent-instance` in the current Houmao-owned skill inventory
- **AND THEN** it reports the dedicated named set that resolves that lifecycle skill

#### Scenario: Default install reports both packaged non-mailbox Houmao skills
- **WHEN** an operator installs the CLI-default system-skill selection into a target tool home
- **THEN** the install result reports both `houmao-manage-specialist` and `houmao-manage-agent-instance` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports both skills as installed when the CLI-default install completed successfully
