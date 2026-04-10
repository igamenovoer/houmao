## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces both packaged pairwise skill variants
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` as installable packaged skills.

When `system-skills install` resolves a selection that includes `user-control`, the reported installed skill names and later `houmao-mgr system-skills status` output SHALL include both pairwise variants whenever that installation completed successfully.

#### Scenario: List reports both packaged pairwise skill variants
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` in the current Houmao-owned skill inventory
- **AND THEN** it reports both skills as part of the packaged `user-control` skill family

#### Scenario: User-control install and status report both pairwise variants
- **WHEN** an operator installs a system-skill selection that includes `user-control` into a target tool home
- **THEN** the install result reports both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports both pairwise variants as installed when that selection completed successfully
