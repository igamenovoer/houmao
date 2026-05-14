## Why

Operators can clear every delivered message in a mailbox root, and they can inspect messages for a single registered address, but there is no maintained `houmao-mgr` path for clearing only one account's visible messages. This forces a destructive all-root reset or unsafe manual mailbox-root editing when only one account needs a message reset.

## What Changes

- Add account-scoped delivered-message clearing to the generic mailbox message surface:
  `houmao-mgr mailbox messages clear --address <full-address> [--mailbox-root <path>] [--dry-run] [--yes]`.
- Add the project-scoped wrapper:
  `houmao-mgr project mailbox messages clear --address <full-address> [--dry-run] [--yes]`.
- Preserve mailbox registrations and other accounts' message visibility while removing the selected account's projections and mailbox-local message state.
- Delete shared canonical message artifacts only when the selected account was the last remaining projection for that message.
- Preserve external `path_ref` attachment targets and report any unsafe paths as blocked cleanup actions.
- Keep the existing root-wide `clear-messages` commands as the all-account mailbox-root reset path.
- Update the packaged mailbox manager skill so single-account message clear requests route to the new account-scoped command.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-mailbox-cli`: add the account-scoped `mailbox messages clear` command and its safety semantics.
- `houmao-mgr-project-mailbox-cli`: mirror the account-scoped message clear command under selected project overlay mailbox roots.
- `filesystem-mailbox-managed-scripts`: define account-scoped managed mailbox clear semantics for projections, local state, shared canonical artifacts, and attachments.
- `houmao-mailbox-mgr-skill`: route single-account message reset work to the new account-scoped command while keeping all-account resets on `clear-messages`.

## Impact

- CLI: `src/houmao/srv_ctrl/commands/mailbox.py`, `src/houmao/srv_ctrl/commands/project_mailbox.py`, and `src/houmao/srv_ctrl/commands/mailbox_support.py`.
- Mailbox runtime: `src/houmao/mailbox/managed.py` plus any compatibility script exposure needed by the managed mailbox rule assets.
- Skill assets: `src/houmao/agents/assets/system_skills/houmao-mailbox-mgr/`.
- Tests: unit coverage for generic and project CLI command parity, destructive confirmation, dry-run payloads, shared-message preservation, last-projection cleanup, managed-copy attachment cleanup, and external attachment preservation.
