## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the user-control project-management skill
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory and named sets when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-project-mgr` as an installable packaged skill.

When `system-skills install` resolves a selection that includes `user-control`, the reported installed skill names and later `houmao-mgr system-skills status` output SHALL include `houmao-project-mgr` whenever that install completed successfully.

#### Scenario: List reports the user-control project-management skill
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-project-mgr` in the current Houmao-owned skill inventory
- **AND THEN** it reports that skill as part of the packaged `user-control` skill family

#### Scenario: User-control install and status report the project-management skill
- **WHEN** an operator installs a system-skill selection that includes `user-control` into a target tool home
- **THEN** the install result reports `houmao-project-mgr` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports `houmao-project-mgr` as installed when that selection completed successfully

## MODIFIED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the packaged agent-instance lifecycle skill and updated CLI-default selection
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and fixed set lists when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway` as installable packaged skills.

The reported named sets SHALL include the dedicated agent-instance lifecycle set, the dedicated agent-messaging set, and the dedicated agent-gateway set.

When `system-skills install` resolves the packaged CLI-default set list, the resolved installed skill names and later `system-skills status` output SHALL include:

- `houmao-project-mgr`
- `houmao-specialist-mgr`
- `houmao-credential-mgr`
- `houmao-agent-definition`
- `houmao-agent-instance`
- `houmao-agent-messaging`
- `houmao-agent-gateway`

Omitting both `--set` and `--skill` SHALL remain one supported path that resolves the packaged CLI-default set list.

#### Scenario: List reports the packaged lifecycle, messaging, and gateway skills with their sets
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway` in the current Houmao-owned skill inventory
- **AND THEN** it reports the dedicated named sets that resolve those skills

#### Scenario: Omitted-selection install reports the packaged non-mailbox Houmao skills
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home`
- **AND WHEN** no `--set` or `--skill` is supplied
- **THEN** the install result reports `houmao-project-mgr`, `houmao-specialist-mgr`, `houmao-credential-mgr`, `houmao-agent-definition`, `houmao-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports those skills as installed when the CLI-default install completed successfully
