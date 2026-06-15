## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the graphing utility skill
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-utils-graphing` as the installable graphing utility skill.

When `system-skills install` resolves a selection that includes the graphing utility skill, the reported installed skill names and later `system-skills status` output SHALL use `houmao-utils-graphing`.

When the default managed or CLI selections include both `houmao-interop-ag-ui` and `houmao-utils-graphing`, their resolved installed skill names SHALL be reported as distinct current skills.

#### Scenario: List reports the graphing utility skill
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-utils-graphing` in the current Houmao-owned skill inventory
- **AND THEN** its description identifies graphing utility guidance rather than AG-UI gateway delivery

#### Scenario: Install and status report the graphing utility skill
- **WHEN** an operator installs a system-skill selection that includes `houmao-utils-graphing` into a target Codex home
- **THEN** the install result reports `houmao-utils-graphing` in the resolved current skill list
- **AND THEN** the target home contains `skills/houmao-utils-graphing/SKILL.md`
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-utils-graphing` as installed

#### Scenario: AG-UI interop and graphing utility remain distinct
- **WHEN** an operator lists or installs a selection containing both AG-UI-related skills
- **THEN** the output includes `houmao-interop-ag-ui`
- **AND THEN** the output includes `houmao-utils-graphing`
- **AND THEN** neither skill name is used as an alias for the other
