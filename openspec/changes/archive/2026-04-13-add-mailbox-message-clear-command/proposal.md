## Why

Operators sometimes need to reset a filesystem mailbox root's delivered mail content during demos, local testing, or workflow recovery while keeping mailbox accounts registered for later reuse. The current `houmao-mgr mailbox cleanup` surface intentionally preserves canonical message history, so there is no maintained command for this narrower destructive reset.

## What Changes

- Add a destructive `houmao-mgr mailbox clear-messages` command that removes delivered mailbox message content from one resolved filesystem mailbox root while preserving mailbox registrations and account directories.
- Add a matching `houmao-mgr project mailbox clear-messages` wrapper for the selected project overlay mailbox root.
- Require explicit destructive confirmation for apply mode, with `--dry-run` support for previewing affected message, projection, mailbox-local state, and managed attachment artifacts.
- Keep existing `mailbox cleanup` semantics unchanged: it continues to remove inactive or stashed registrations without deleting canonical mail.
- Update mailbox-admin skill guidance and mailbox reference docs so agents and operators route message-reset work to the new command instead of ad hoc filesystem edits or registration cleanup.

## Capabilities

### New Capabilities

### Modified Capabilities

- `houmao-mgr-mailbox-cli`: Add the generic filesystem mailbox `clear-messages` command and define its destructive reset semantics.
- `houmao-mgr-project-mailbox-cli`: Add the project-scoped `clear-messages` wrapper over the selected project mailbox root.
- `houmao-mailbox-mgr-skill`: Teach the packaged mailbox-admin skill to route message-clear requests to the new maintained command.
- `mailbox-reference-docs`: Document the supported mailbox message-clear workflow and its boundary from registration cleanup and mailbox account lifecycle.

## Impact

- Affected CLI modules: `src/houmao/srv_ctrl/commands/mailbox.py`, `src/houmao/srv_ctrl/commands/project_mailbox.py`, and shared mailbox command helpers.
- Affected mailbox runtime logic: `src/houmao/mailbox/managed.py` and its filesystem mailbox state reset helpers.
- Affected docs and skills: mailbox CLI/reference docs and `src/houmao/agents/assets/system_skills/houmao-mailbox-mgr/`.
- Tests should cover mailbox-level behavior, top-level CLI behavior, project wrapper behavior, dry-run/confirmation safety, and preservation of mailbox registrations.
