## MODIFIED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the unified mailbox skill inventory
`houmao-mgr system-skills` SHALL use the current packaged system-skill inventory and named sets when reporting, installing, and inspecting Houmao-owned mailbox skills.

That current mailbox inventory SHALL surface:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`
- `houmao-mailbox-mgr`

That current mailbox inventory SHALL NOT surface the removed top-level mailbox skill names:

- `houmao-email-via-agent-gateway`
- `houmao-email-via-filesystem`
- `houmao-email-via-stalwart`

If the packaged catalog reports both `mailbox-core` and `mailbox-full`, `mailbox-core` SHALL resolve to the current mailbox worker pair built from `houmao-process-emails-via-gateway` and `houmao-agent-email-comms`, while `mailbox-full` SHALL resolve to that worker pair plus `houmao-mailbox-mgr`.

When `system-skills install` resolves a selection that includes mailbox skills, the reported installed skill names and later `system-skills status` output SHALL use only the current mailbox skill names.

#### Scenario: List reports the unified mailbox worker and mailbox-admin skills with current mailbox sets
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-process-emails-via-gateway`, `houmao-agent-email-comms`, and `houmao-mailbox-mgr` in the current Houmao-owned skill inventory
- **AND THEN** it does not report `houmao-email-via-agent-gateway`, `houmao-email-via-filesystem`, or `houmao-email-via-stalwart` as current installable skills
- **AND THEN** `mailbox-core` and `mailbox-full` are reported with distinct current membership

#### Scenario: Mailbox-full install and status report the mailbox-admin skill
- **WHEN** an operator installs a system-skill selection that includes `mailbox-full` into a target tool home
- **THEN** the install result reports `houmao-process-emails-via-gateway`, `houmao-agent-email-comms`, and `houmao-mailbox-mgr` as the current mailbox skill names for that selection
- **AND THEN** a later `houmao-mgr system-skills status` for that home reports those same current mailbox skill names as installed when that selection completed successfully

#### Scenario: Mailbox-core remains the narrow worker pair
- **WHEN** an operator installs a system-skill selection that includes `mailbox-core` and no broader mailbox set
- **THEN** the resolved mailbox skill list includes `houmao-process-emails-via-gateway` and `houmao-agent-email-comms`
- **AND THEN** it does not automatically add `houmao-mailbox-mgr` through the narrower mailbox-core selection
