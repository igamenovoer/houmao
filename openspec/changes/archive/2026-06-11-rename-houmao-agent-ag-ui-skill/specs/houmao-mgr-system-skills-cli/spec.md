## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the renamed AG-UI interop skill
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-interop-ag-ui` as the installable AG-UI interop skill.

The command output SHALL NOT report `houmao-agent-ag-ui` as a current installable skill after the rename.

When `system-skills install` resolves a selection that includes the renamed skill, the reported installed skill names and later `system-skills status` output SHALL use `houmao-interop-ag-ui`.

If a target tool home contains a stale retired `houmao-agent-ag-ui` projection, install output SHALL report that retired projection removal through the existing retired-skill reporting fields.

#### Scenario: List reports the renamed AG-UI interop skill
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-interop-ag-ui` in the current Houmao-owned skill inventory
- **AND THEN** it does not report `houmao-agent-ag-ui` as a current installable skill
- **AND THEN** it reports `houmao-agent-ag-ui` only as a retired skill name when retired names are included in the output

#### Scenario: Install and status report the renamed skill
- **WHEN** an operator installs the CLI default system-skill selection into a target Codex home
- **THEN** the install result reports `houmao-interop-ag-ui` in the resolved current skill list
- **AND THEN** the target home contains `skills/houmao-interop-ag-ui/SKILL.md`
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-interop-ag-ui` as installed

#### Scenario: Install reports stale old-name removal
- **WHEN** an operator installs current system skills into a tool home that already contains `houmao-agent-ag-ui`
- **THEN** the install result reports `houmao-agent-ag-ui` as a removed retired skill
- **AND THEN** the target home no longer contains the old `houmao-agent-ag-ui` projection
