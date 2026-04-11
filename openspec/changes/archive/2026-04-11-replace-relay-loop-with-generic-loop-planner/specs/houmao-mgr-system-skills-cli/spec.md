## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the packaged generic loop planner
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-agent-loop-generic` as an installable packaged skill.

That current inventory SHALL NOT surface `houmao-agent-loop-relay` as an installable packaged skill after the generic replacement is introduced.

When `system-skills install` resolves a selection that includes `user-control`, the reported installed skill names and later `houmao-mgr system-skills status` output SHALL include `houmao-agent-loop-generic` whenever that installation completed successfully.

When `system-skills install` resolves a selection that includes `user-control`, the reported installed skill names and later `houmao-mgr system-skills status` output SHALL NOT include `houmao-agent-loop-relay` after the generic replacement is introduced.

#### Scenario: List reports packaged generic loop planner
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-agent-loop-generic` in the current Houmao-owned skill inventory
- **AND THEN** it reports that skill as part of the packaged `user-control` skill family

#### Scenario: List no longer reports relay loop planner
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command does not report `houmao-agent-loop-relay` as a current installable skill

#### Scenario: User-control install and status report generic loop planner
- **WHEN** an operator installs a system-skill selection that includes `user-control` into a target tool home
- **THEN** the install result reports `houmao-agent-loop-generic` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-agent-loop-generic` as installed when that selection completed successfully
