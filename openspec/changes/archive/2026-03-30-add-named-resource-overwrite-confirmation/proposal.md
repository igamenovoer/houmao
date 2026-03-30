## Why

Several `houmao-mgr` create and register workflows fail immediately when a durable named resource already exists, but the CLI does not offer a consistent operator contract for confirming replacement. This is now causing friction in mailbox registration and project-easy authoring flows where the system already has enough context to replace managed state safely after explicit operator confirmation.

## What Changes

- Add a shared CLI overwrite-confirmation contract for selected `houmao-mgr` create and register commands that manage durable named resources.
- Prompt interactively before replacing conflicting managed mailbox registrations or project-easy specialist definitions.
- Add `--yes` support for those flows so operators can accept overwrite prompts non-interactively.
- Preserve existing mailbox registration modes such as `safe`, `force`, and `stash` instead of collapsing them into a single overwrite behavior.
- Keep live runtime session launch conflicts out of scope for this change; `agents launch` and `project easy instance launch` will continue to use their existing launch and relaunch semantics.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-mailbox-cli`: change mailbox registration requirements to support interactive overwrite confirmation and `--yes` for conflicting durable registrations.
- `houmao-mgr-project-mailbox-cli`: change project-scoped mailbox registration requirements to mirror the generic mailbox overwrite-confirmation contract.
- `managed-agent-mailbox-registration`: change late managed-agent mailbox registration requirements to support the same overwrite-confirmation behavior before replacing conflicting durable mailbox state.
- `houmao-mgr-project-easy-cli`: change `project easy specialist create` requirements to support replacing an existing specialist definition after explicit confirmation or `--yes`.

## Impact

- Affected CLI code under `src/houmao/srv_ctrl/commands/mailbox.py`, `src/houmao/srv_ctrl/commands/agents/mailbox.py`, and `src/houmao/srv_ctrl/commands/project.py`.
- Affected mailbox lifecycle helpers under `src/houmao/srv_ctrl/commands/mailbox_support.py` and `src/houmao/mailbox/managed.py`.
- Affected project catalog-backed specialist authoring flow under `src/houmao/project/catalog.py`.
- Affected CLI help, tests, and command documentation for the modified command families.
