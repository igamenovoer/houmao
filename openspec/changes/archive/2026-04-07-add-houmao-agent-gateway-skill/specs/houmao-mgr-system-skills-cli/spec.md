## MODIFIED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the packaged agent-instance lifecycle skill and updated CLI-default selection
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and fixed set lists when reporting, installing, and inspecting Houmao-owned skills.

That current inventory SHALL surface `houmao-manage-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway` as installable packaged skills.

The reported named sets SHALL include the dedicated agent-instance lifecycle set, the dedicated agent-messaging set, and the dedicated agent-gateway set.

When `system-skills install` resolves the packaged CLI-default set list, the resolved installed skill names and later `system-skills status` output SHALL include:

- `houmao-manage-specialist`
- `houmao-manage-credentials`
- `houmao-manage-agent-definition`
- `houmao-manage-agent-instance`
- `houmao-agent-messaging`
- `houmao-agent-gateway`

Omitting both `--set` and `--skill` SHALL remain one supported path that resolves the packaged CLI-default set list.

#### Scenario: List reports the packaged lifecycle, messaging, and gateway skills with their sets
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-manage-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway` in the current Houmao-owned skill inventory
- **AND THEN** it reports the dedicated named sets that resolve those skills

#### Scenario: Omitted-selection install reports the packaged non-mailbox Houmao skills
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --home /tmp/codex-home`
- **AND WHEN** no `--set` or `--skill` is supplied
- **THEN** the install result reports `houmao-manage-specialist`, `houmao-manage-credentials`, `houmao-manage-agent-definition`, `houmao-manage-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway` in the resolved current skill list
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports those skills as installed when the CLI-default install completed successfully
