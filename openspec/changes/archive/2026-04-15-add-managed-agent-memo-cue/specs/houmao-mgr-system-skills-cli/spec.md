## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces managed-memory guidance
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and fixed set lists when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-memory-mgr` as an installable packaged skill.

The reported named sets SHALL include the dedicated managed-memory set that resolves `houmao-memory-mgr`.

When `system-skills install` resolves the packaged CLI-default set list, the resolved installed skill names and later `system-skills status` output SHALL include `houmao-memory-mgr`.

#### Scenario: List reports the packaged memory-management skill and set
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-memory-mgr` in the current Houmao-owned skill inventory
- **AND THEN** it reports the dedicated named set that resolves that skill

#### Scenario: Omitted-selection install and status report memory-management guidance
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home`
- **AND WHEN** no `--set` or `--skill` is supplied
- **THEN** the install result reports `houmao-memory-mgr` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-memory-mgr` as installed when the CLI-default install completed successfully

