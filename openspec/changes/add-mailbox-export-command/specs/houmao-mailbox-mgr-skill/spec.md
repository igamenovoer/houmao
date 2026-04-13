## MODIFIED Requirements

### Requirement: Houmao provides a packaged `houmao-mailbox-mgr` system skill
The system SHALL package a Houmao-owned system skill named `houmao-mailbox-mgr` under the maintained system-skill asset root.

That skill SHALL instruct agents and operators to handle mailbox-administration work through these maintained command surfaces:

- `houmao-mgr mailbox init|status|register|unregister|repair|cleanup|clear-messages|export`
- `houmao-mgr mailbox accounts list|get`
- `houmao-mgr mailbox messages list|get`
- `houmao-mgr project mailbox init|status|register|unregister|repair|cleanup|clear-messages|export`
- `houmao-mgr project mailbox accounts list|get`
- `houmao-mgr project mailbox messages list|get`
- `houmao-mgr agents mailbox status|register|unregister`

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects local action-specific documents rather than flattening the entire workflow into one page.

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `houmao-mgr agents mail ...`
- shared gateway `/v1/mail/*` operations
- `houmao-mgr agents gateway mail-notifier ...`
- direct gateway `/v1/mail-notifier` or `/v1/wakeups`
- ad hoc filesystem editing inside mailbox roots

#### Scenario: Installed skill points the caller at maintained mailbox-admin surfaces
- **WHEN** an agent or operator opens the installed `houmao-mailbox-mgr` skill
- **THEN** the skill directs the caller to the maintained mailbox-root, project-mailbox, and late agent-binding command surfaces
- **AND THEN** it does not redirect the caller to unrelated actor-scoped mail, gateway reminder, or direct filesystem mutation paths

#### Scenario: Installed skill routes through action-specific local guidance
- **WHEN** an agent reads the installed `houmao-mailbox-mgr` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for mailbox-admin actions
- **AND THEN** the detailed workflow lives in local action-specific documents rather than one flattened entry page

## ADDED Requirements

### Requirement: `houmao-mailbox-mgr` routes mailbox export work to the maintained export command
The packaged `houmao-mailbox-mgr` skill SHALL route requests to archive or export filesystem mailbox state to the maintained mailbox export command for the selected mailbox scope.

When the task targets an arbitrary filesystem mailbox root, the skill SHALL use `houmao-mgr mailbox export`.

When the task targets the selected project overlay mailbox root, the skill SHALL use `houmao-mgr project mailbox export`.

The skill SHALL explain that default mailbox export materializes symlinks so the archive can be used on filesystems that do not support symlinks.

The skill SHALL expose the optional `--symlink-mode preserve` choice only when the user explicitly wants symlink preservation.

The skill SHALL NOT recommend ad hoc recursive mailbox-root copying when the maintained export command covers the request.

#### Scenario: Skill routes project mailbox archive request to project export
- **WHEN** the user asks to archive the active project mailbox root
- **THEN** the skill directs the caller to `houmao-mgr project mailbox export --output-dir <dir> --all-accounts`
- **AND THEN** it explains that default export materializes symlinks

#### Scenario: Skill routes explicit mailbox-root archive request to generic export
- **WHEN** the user asks to export an explicit filesystem mailbox root at `/tmp/shared-mail`
- **THEN** the skill directs the caller to `houmao-mgr mailbox export --mailbox-root /tmp/shared-mail --output-dir <dir> --all-accounts`
- **AND THEN** it does not recommend direct filesystem copying inside the mailbox root

#### Scenario: Skill preserves selected-account export intent
- **WHEN** the user asks to export only `alice@houmao.localhost`
- **THEN** the skill preserves that account selection in the chosen command using `--address alice@houmao.localhost`
- **AND THEN** it does not replace the selected-account request with an all-account export
