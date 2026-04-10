## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the packaged `houmao-agent-inspect` skill and named set
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-agent-inspect` as an installable packaged skill.

The reported named sets SHALL include the dedicated `agent-inspect` set containing `houmao-agent-inspect`.

When `system-skills install` resolves the packaged default set list for a supported tool home, the resolved installed skill names and later `system-skills status` output SHALL include `houmao-agent-inspect`.

Omitting both `--set` and `--skill` SHALL remain a supported path that resolves the packaged default set list including the `agent-inspect` set.

#### Scenario: List reports the packaged inspect skill and named set
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-agent-inspect` in the current Houmao-owned skill inventory
- **AND THEN** it reports the dedicated `agent-inspect` named set in the current packaged set inventory

#### Scenario: Omitted-selection install and status report the inspect skill
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home`
- **AND WHEN** no `--set` or `--skill` is supplied
- **THEN** the install result reports `houmao-agent-inspect` in the resolved current skill list when the packaged default set list includes `agent-inspect`
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-agent-inspect` as installed when the default install completed successfully
